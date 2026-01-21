"""
V2 Email Processor — Workflow v2.2 Knowledge Extraction

Processeur d'emails utilisant le pipeline d'extraction de connaissances v2.2.

Ce processeur intègre :
1. EventAnalyzer pour l'analyse et l'extraction
2. PKMEnricher pour l'application au PKM
3. OmniFocusClient pour les tâches (optionnel)
4. CrossSourceEngine pour le contexte multi-source (v2.2)
5. PatternStore pour la validation par patterns appris (v2.2)
6. V2WorkingMemory pour le suivi de l'état cognitif (v2.2)

Usage:
    processor = V2EmailProcessor()
    result = await processor.process_event(event, context_notes)
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.config_manager import WorkflowV2Config, get_config
from src.core.events.universal_event import PerceivedEvent
from src.core.models.v2_models import (
    AnalysisResult,
    ClarificationQuestion,
    ContextNote,
    CrossSourceContext,
    EmailAction,
    EnrichmentResult,
    PatternMatch,
    V2MemoryState,
    V2WorkingMemory,
)
from src.integrations.apple.omnifocus import OmniFocusClient, create_omnifocus_client
from src.monitoring.logger import get_logger
from src.passepartout.context_engine import ContextEngine
from src.passepartout.cross_source.config import CrossSourceConfig
from src.passepartout.cross_source.engine import CrossSourceEngine
from src.passepartout.enricher import PKMEnricher
from src.passepartout.note_manager import NoteManager, get_note_manager
from src.sancho.context_searcher import ContextSearcher
from src.sancho.multi_pass_analyzer import MultiPassAnalyzer, MultiPassResult
from src.sancho.router import AIRouter, get_ai_router
from src.sganarelle.pattern_store import PatternStore

logger = get_logger("v2_processor")


@dataclass
class V2ProcessingResult:
    """
    Résultat du traitement v2.2 d'un événement.

    Attributes:
        success: True si le traitement a réussi
        event_id: ID de l'événement traité
        analysis: Résultat de l'analyse (si réussie)
        enrichment: Résultat de l'enrichissement PKM (si applicable)
        email_action: Action recommandée sur l'email
        error: Message d'erreur (si échec)
        duration_ms: Durée totale en millisecondes
        auto_applied: True si les extractions ont été auto-appliquées
        working_memory: Mémoire de travail V2 avec trace complète (v2.2)
        cross_source_context: Contexte récupéré des sources croisées (v2.2)
        pattern_matches: Patterns Sganarelle correspondants (v2.2)
        clarification_questions: Questions pour l'utilisateur si confiance basse (v2.2)
        needs_clarification: True si une clarification humaine est nécessaire (v2.2)
    """

    success: bool
    event_id: str
    analysis: Optional[AnalysisResult] = None
    enrichment: Optional[EnrichmentResult] = None
    email_action: EmailAction = EmailAction.RIEN
    error: Optional[str] = None
    duration_ms: float = 0.0
    auto_applied: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    # V2.2 additions
    working_memory: Optional[V2WorkingMemory] = None
    cross_source_context: list[CrossSourceContext] = field(default_factory=list)
    pattern_matches: list[PatternMatch] = field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = field(default_factory=list)
    needs_clarification: bool = False
    # v2.3: Multi-pass analysis transparency
    multi_pass_result: Optional["MultiPassResult"] = None

    @property
    def extraction_count(self) -> int:
        """Nombre d'extractions identifiées"""
        return self.analysis.extraction_count if self.analysis else 0

    @property
    def notes_affected(self) -> int:
        """Nombre de notes affectées"""
        return self.enrichment.total_notes_affected if self.enrichment else 0

    @property
    def tasks_created(self) -> int:
        """Nombre de tâches OmniFocus créées"""
        return len(self.enrichment.tasks_created) if self.enrichment else 0

    @property
    def effective_confidence(self) -> float:
        """Confiance effective incluant le boost des patterns (v2.2)"""
        if self.analysis:
            return self.analysis.effective_confidence
        return 0.0

    @property
    def pattern_validated(self) -> bool:
        """True si l'analyse a été validée par au moins un pattern (v2.2)"""
        return len(self.pattern_matches) > 0


class V2EmailProcessor:
    """
    Processeur d'emails utilisant le Workflow v2.2.

    Pipeline complet:
    1. Initialisation V2WorkingMemory pour traçabilité
    2. Récupération du contexte (notes pertinentes via ContextEngine)
    3. Récupération du contexte multi-source (CrossSourceEngine) [v2.2]
    4. Analyse avec EventAnalyzer (Haiku → Sonnet si besoin)
    5. Validation par patterns appris (PatternStore/Sganarelle) [v2.2]
    6. Si confiance effective >= auto_apply_threshold : application automatique
    7. Si confiance basse : génération de questions de clarification [v2.2]
    8. Sinon : mise en queue pour revue humaine

    Attributes:
        config: Configuration WorkflowV2Config
        analyzer: EventAnalyzer pour l'extraction
        enricher: PKMEnricher pour l'application
        context_engine: ContextEngine pour la récupération de contexte
        cross_source_engine: CrossSourceEngine pour le contexte multi-source (v2.2)
        pattern_store: PatternStore pour la validation par patterns (v2.2)

    Example:
        >>> processor = V2EmailProcessor()
        >>> result = await processor.process_event(event)
        >>> if result.success and result.auto_applied:
        ...     print(f"Applied {result.extraction_count} extractions")
        >>> if result.needs_clarification:
        ...     for q in result.clarification_questions:
        ...         print(f"Question: {q.question}")
    """

    def __init__(
        self,
        config: Optional[WorkflowV2Config] = None,
        ai_router: Optional[AIRouter] = None,
        note_manager: Optional[NoteManager] = None,
        omnifocus_client: Optional[OmniFocusClient] = None,
        cross_source_engine: Optional[CrossSourceEngine] = None,
        pattern_store: Optional[PatternStore] = None,
    ):
        """
        Initialize the V2 processor.

        Args:
            config: WorkflowV2Config (uses defaults if None)
            ai_router: AIRouter instance (creates default if None)
            note_manager: NoteManager instance (creates default if None)
            omnifocus_client: OmniFocusClient (creates default if enabled)
            cross_source_engine: CrossSourceEngine (creates default if None)
            pattern_store: PatternStore (creates default if None)
        """
        self.config = config or WorkflowV2Config()
        app_config = get_config()

        # Initialize AI router
        if ai_router is None:
            ai_router = get_ai_router(app_config.ai)
        self.ai_router = ai_router

        # Initialize note manager (use singleton for performance)
        if note_manager is None:
            note_manager = get_note_manager()
        self.note_manager = note_manager

        # Initialize context engine
        self.context_engine = ContextEngine(note_manager=self.note_manager)

        # Initialize CrossSourceEngine (v2.2)
        if cross_source_engine is None:
            cross_source_config = CrossSourceConfig(enabled=True)
            cross_source_engine = CrossSourceEngine(config=cross_source_config)
        self.cross_source_engine = cross_source_engine

        # Initialize PatternStore (v2.2)
        if pattern_store is None:
            # Use the same directory as the database for patterns
            patterns_path = Path(app_config.storage.database_path).parent / "patterns.json"
            pattern_store = PatternStore(storage_path=patterns_path, auto_save=True)
        self.pattern_store = pattern_store

        # Initialize MultiPassAnalyzer (Four Valets v3.0)
        self.context_searcher = ContextSearcher(
            note_manager=self.note_manager,
            cross_source_engine=self.cross_source_engine,
        )
        self.multi_pass_analyzer = MultiPassAnalyzer(
            ai_router=self.ai_router,
            context_searcher=self.context_searcher,
            note_manager=self.note_manager,
        )

        # Initialize OmniFocus client if enabled
        if omnifocus_client is None and self.config.omnifocus_enabled:
            omnifocus_client = create_omnifocus_client(
                default_project=self.config.omnifocus_default_project
            )
        self.omnifocus_client = omnifocus_client

        # Initialize enricher
        self.enricher = PKMEnricher(
            note_manager=self.note_manager,
            omnifocus_client=self.omnifocus_client,
            omnifocus_enabled=self.config.omnifocus_enabled,
        )

        logger.info(
            "V2EmailProcessor initialized (Four Valets v3.0)",
            extra={
                "default_model": self.config.default_model,
                "auto_apply_threshold": self.config.auto_apply_threshold,
                "omnifocus_enabled": self.config.omnifocus_enabled,
                "cross_source_enabled": self.cross_source_engine is not None,
                "pattern_store_enabled": self.pattern_store is not None,
            },
        )

    async def process_event(
        self,
        event: PerceivedEvent,
        context_notes: Optional[list[ContextNote]] = None,
        auto_apply: bool = True,
    ) -> V2ProcessingResult:
        """
        Process a single event through the v2.2 pipeline.

        Pipeline:
        1. Initialize V2WorkingMemory
        2. Get context notes from ContextEngine
        3. Get cross-source context from CrossSourceEngine [v2.2]
        4. Analyze with MultiPassAnalyzer (Four Valets)
        5. Validate with PatternStore [v2.2]
        6. Generate clarification questions if needed [v2.2]
        7. Auto-apply if high confidence, else queue for review

        Args:
            event: PerceivedEvent to process
            context_notes: Pre-fetched context notes (fetches if None)
            auto_apply: Whether to auto-apply high-confidence extractions

        Returns:
            V2ProcessingResult with analysis, enrichment, and v2.2 metadata
        """
        import time

        start_time = time.time()

        # Step 1: Initialize V2WorkingMemory for this event
        memory = V2WorkingMemory(event_id=event.event_id)
        memory.add_trace("Processing started", {"auto_apply": auto_apply})

        try:
            # Step 2: Get context notes if not provided
            if context_notes is None:
                context_notes = await self._get_context_notes(event)
            memory.context_notes = context_notes
            memory.add_trace("Context notes retrieved", {"count": len(context_notes)})
            memory.transition_to(V2MemoryState.CONTEXT_RETRIEVED)

            # Step 3: Get cross-source context (v2.2)
            cross_source_context = await self._get_cross_source_context(event)
            memory.cross_source_context = cross_source_context
            memory.add_trace("Cross-source context retrieved", {"count": len(cross_source_context)})

            logger.debug(
                f"Processing event {event.event_id} with "
                f"{len(context_notes)} notes + {len(cross_source_context)} cross-source items"
            )

            # Step 4: Analyze event using MultiPassAnalyzer (Four Valets)
            analysis, multi_pass_result = await self._analyze_with_multi_pass(event)
            memory.add_trace(
                "Multi-pass analysis complete",
                {
                    "confidence": analysis.confidence,
                    "extractions": analysis.extraction_count,
                    "escalated": analysis.escalated,
                    "model": analysis.model_used,
                    "passes_count": multi_pass_result.passes_count,
                    "stop_reason": multi_pass_result.stop_reason,
                    "high_stakes": multi_pass_result.high_stakes,
                },
            )

            memory.analysis = analysis

            # Step 5: Validate with patterns (v2.2)
            memory.transition_to(V2MemoryState.PATTERN_VALIDATING)
            pattern_matches = self._validate_with_patterns(event, analysis)
            memory.pattern_matches = pattern_matches

            # Apply pattern confidence boost to analysis
            if pattern_matches:
                analysis.pattern_matches = pattern_matches
                analysis.pattern_validated = True
                # Boost: 5% per matching pattern, max 15%
                boost = min(0.15, len(pattern_matches) * 0.05)
                analysis.pattern_confidence_boost = boost
                memory.add_trace(
                    "Pattern validation complete",
                    {
                        "patterns_matched": len(pattern_matches),
                        "confidence_boost": boost,
                        "effective_confidence": analysis.effective_confidence,
                    },
                )

            logger.info(
                f"Analysis complete for {event.event_id}",
                extra={
                    "confidence": analysis.confidence,
                    "effective_confidence": analysis.effective_confidence,
                    "extractions": analysis.extraction_count,
                    "escalated": analysis.escalated,
                    "model": analysis.model_used,
                    "patterns_matched": len(pattern_matches),
                },
            )

            # Step 6: Check if clarification needed (v2.2)
            clarification_questions: list[ClarificationQuestion] = []
            needs_clarification = False

            if analysis.effective_confidence < self.config.notify_threshold:
                memory.transition_to(V2MemoryState.NEEDS_CLARIFICATION)
                clarification_questions = self._generate_clarification_questions(event, analysis)
                needs_clarification = len(clarification_questions) > 0
                analysis.clarification_questions = clarification_questions
                analysis.needs_clarification = needs_clarification
                memory.clarification_questions = clarification_questions
                memory.add_trace(
                    "Clarification questions generated", {"count": len(clarification_questions)}
                )

            # Step 7: Determine if we should auto-apply
            # Use effective_confidence (includes pattern boost)
            should_apply = (
                auto_apply
                and analysis.effective_confidence >= self.config.auto_apply_threshold
                and analysis.has_extractions
                and not needs_clarification
            )

            enrichment = None
            if should_apply:
                memory.transition_to(V2MemoryState.APPLYING)
                # Apply extractions to PKM
                enrichment = await self.enricher.apply(analysis, event.event_id)
                memory.add_trace(
                    "Extractions applied",
                    {
                        "notes_updated": len(enrichment.notes_updated),
                        "notes_created": len(enrichment.notes_created),
                        "tasks_created": len(enrichment.tasks_created),
                        "errors": len(enrichment.errors),
                    },
                )

                logger.info(
                    f"Auto-applied extractions for {event.event_id}",
                    extra={
                        "notes_updated": len(enrichment.notes_updated),
                        "notes_created": len(enrichment.notes_created),
                        "tasks_created": len(enrichment.tasks_created),
                        "errors": len(enrichment.errors),
                    },
                )

            # Finalize
            memory.transition_to(V2MemoryState.COMPLETE)
            duration_ms = (time.time() - start_time) * 1000

            return V2ProcessingResult(
                success=True,
                event_id=event.event_id,
                analysis=analysis,
                enrichment=enrichment,
                email_action=analysis.action,
                auto_applied=should_apply and enrichment is not None,
                duration_ms=duration_ms,
                # V2.2 additions
                working_memory=memory,
                cross_source_context=cross_source_context,
                pattern_matches=pattern_matches,
                clarification_questions=clarification_questions,
                needs_clarification=needs_clarification,
                # v2.3: Multi-pass analysis transparency
                multi_pass_result=multi_pass_result,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            memory.add_error(str(e))
            memory.transition_to(V2MemoryState.FAILED)
            logger.error(f"V2 processing failed for {event.event_id}: {e}")

            return V2ProcessingResult(
                success=False,
                event_id=event.event_id,
                error=str(e),
                duration_ms=duration_ms,
                working_memory=memory,
            )

    async def _get_context_notes(
        self,
        event: PerceivedEvent,
    ) -> list[ContextNote]:
        """
        Retrieve relevant context notes for an event.

        Uses ContextEngine to find semantically similar notes.

        Args:
            event: Event to find context for

        Returns:
            List of ContextNote objects
        """
        try:
            # Get relevant context from context engine
            context_result = await self.context_engine.retrieve_context(
                event=event,
                top_k=self.config.context_notes_count,
                min_relevance=0.3,
            )

            # Convert ContextItem to ContextNote format
            context_notes = []
            for item in context_result.context_items:
                # Truncate content for context
                content_summary = item.content[: self.config.context_note_max_chars]
                if len(item.content) > self.config.context_note_max_chars:
                    content_summary += "..."

                context_notes.append(
                    ContextNote(
                        title=item.metadata.get("note_title", "Unknown"),
                        type=item.metadata.get("note_type", item.type),
                        content_summary=content_summary,
                        relevance=item.relevance_score,
                        note_id=item.metadata.get("note_id"),
                    )
                )

            return context_notes

        except Exception as e:
            logger.warning(f"Failed to get context notes: {e}")
            return []

    async def _get_cross_source_context(
        self,
        event: PerceivedEvent,
    ) -> list[CrossSourceContext]:
        """
        Retrieve context from cross-source search (v2.2).

        Searches across emails, calendar, Teams, WhatsApp, files, and web
        to find relevant context for the event.

        Args:
            event: Event to find context for

        Returns:
            List of CrossSourceContext objects
        """
        try:
            # Build search query from event
            query = self._build_cross_source_query(event)
            if not query:
                return []

            # Search across sources (exclude web by default for privacy)
            result = await self.cross_source_engine.search(
                query=query,
                include_web=False,
                max_results=5,
            )

            # Convert SourceItems to CrossSourceContext
            cross_source_items = []
            for item in result.items:
                cross_source_items.append(
                    CrossSourceContext(
                        source=item.source,
                        title=item.title,
                        content_summary=item.content[:300] + "..."
                        if len(item.content) > 300
                        else item.content,
                        relevance=item.final_score,
                        timestamp=item.timestamp,
                        metadata=item.metadata,
                    )
                )

            logger.debug(
                f"Cross-source search returned {len(cross_source_items)} items",
                extra={
                    "query": query[:50],
                    "sources_searched": result.sources_searched,
                },
            )

            return cross_source_items

        except Exception as e:
            logger.warning(f"Failed to get cross-source context: {e}")
            return []

    def _build_cross_source_query(self, event: PerceivedEvent) -> str:
        """
        Build a search query from event content.

        Extracts key terms from subject, sender, and content.

        Args:
            event: Event to build query from

        Returns:
            Search query string
        """
        parts = []

        # Add subject/title
        if event.title:
            parts.append(event.title)

        # Add sender info
        if event.from_person:
            parts.append(event.from_person)
        elif event.metadata.get("from_name"):
            parts.append(event.metadata["from_name"])

        # Add first 100 chars of content
        if event.content:
            content_preview = event.content[:100].strip()
            if content_preview:
                parts.append(content_preview)

        # Join and limit query length
        query = " ".join(parts)
        return query[:200] if query else ""

    def _validate_with_patterns(
        self,
        event: PerceivedEvent,
        analysis: AnalysisResult,
    ) -> list[PatternMatch]:
        """
        Validate analysis against learned patterns (v2.2).

        Uses PatternStore to find matching behavioral patterns that
        can boost confidence in the analysis.

        Args:
            event: Event being processed
            analysis: Analysis result to validate

        Returns:
            List of PatternMatch objects for matching patterns
        """
        try:
            # Build context for pattern matching
            context = {
                "action": analysis.action.value,
                "extraction_types": [e.type.value for e in analysis.extractions],
                "has_extractions": analysis.has_extractions,
                "confidence": analysis.confidence,
            }

            # Find matching patterns
            matching_patterns = self.pattern_store.find_matching_patterns(
                event=event,
                context=context,
                min_confidence=0.5,
            )

            # Convert to PatternMatch format
            pattern_matches = []
            for pattern in matching_patterns:
                pattern_matches.append(
                    PatternMatch(
                        pattern_id=pattern.pattern_id,
                        description=f"{pattern.pattern_type.value}: {pattern.conditions}",
                        confidence=pattern.confidence,
                        suggested_action=pattern.suggested_actions[0]
                        if pattern.suggested_actions
                        else "",
                        occurrences=pattern.occurrences,
                    )
                )

            if pattern_matches:
                logger.debug(f"Found {len(pattern_matches)} matching patterns for {event.event_id}")

            return pattern_matches

        except Exception as e:
            logger.warning(f"Failed to validate with patterns: {e}")
            return []

    def _generate_clarification_questions(
        self,
        event: PerceivedEvent,
        analysis: AnalysisResult,
    ) -> list[ClarificationQuestion]:
        """
        Generate clarification questions for low-confidence analysis (v2.2).

        When confidence is below the notification threshold, generate
        specific questions to help the user clarify the analysis.

        Args:
            event: Event being processed
            analysis: Low-confidence analysis result

        Returns:
            List of ClarificationQuestion objects
        """
        questions = []

        # Question about action if uncertain
        if analysis.confidence < 0.6:
            sender_name = event.metadata.get("from_name") or event.from_person or "l'expéditeur"
            questions.append(
                ClarificationQuestion(
                    question=f"Quelle action dois-je effectuer sur cet email de {sender_name} ?",
                    reason="La confiance dans l'action recommandée est basse",
                    options=[
                        "Archiver",
                        "Marquer pour suivi",
                        "Mettre en attente",
                        "Supprimer",
                        "Aucune action",
                    ],
                    priority="haute",
                )
            )

        # Question about extractions if any seem uncertain
        if analysis.has_extractions and analysis.confidence < 0.75:
            extraction_types = {e.type.value for e in analysis.extractions}
            questions.append(
                ClarificationQuestion(
                    question="Ces informations extraites sont-elles correctes ?",
                    reason=f"Extractions identifiées : {', '.join(extraction_types)}",
                    options=[
                        "Oui, toutes correctes",
                        "Partiellement correctes",
                        "Non, ignorer ces extractions",
                    ],
                    priority="moyenne",
                )
            )

        # Question about note target if creating new notes
        for extraction in analysis.extractions:
            if extraction.note_action.value == "creer":
                questions.append(
                    ClarificationQuestion(
                        question=f"Dois-je créer une nouvelle note '{extraction.note_cible}' ?",
                        reason=f"Information à stocker : {extraction.info[:50]}...",
                        options=[
                            "Oui, créer la note",
                            "Non, ajouter à une note existante",
                            "Ignorer cette extraction",
                        ],
                        priority="moyenne",
                    )
                )
                break  # Only ask once for note creation

        return questions

    def _convert_multi_pass_result(
        self,
        multi_pass_result: MultiPassResult,
    ) -> AnalysisResult:
        """
        Convert MultiPassResult to AnalysisResult for backward compatibility.

        Args:
            multi_pass_result: Result from MultiPassAnalyzer

        Returns:
            AnalysisResult in v2.1 format
        """
        from src.core.models.v2_models import (
            Extraction as V2Extraction,
        )
        from src.core.models.v2_models import (
            ExtractionType,
            ImportanceLevel,
            NoteAction,
        )

        # Convert extractions
        extractions = []
        for ext in multi_pass_result.extractions:
            try:
                ext_type = ExtractionType(ext.type)
            except ValueError:
                ext_type = ExtractionType.FAIT

            try:
                importance = ImportanceLevel(ext.importance)
            except ValueError:
                importance = ImportanceLevel.MOYENNE

            try:
                note_action = NoteAction(ext.note_action)
            except ValueError:
                note_action = NoteAction.ENRICHIR

            extractions.append(
                V2Extraction(
                    info=ext.info,
                    type=ext_type,
                    importance=importance,
                    note_cible=ext.note_cible or "",
                    note_action=note_action,
                    omnifocus=ext.omnifocus,
                    calendar=ext.calendar,
                    date=ext.date,
                    time=ext.time,
                    timezone=ext.timezone,
                    duration=ext.duration,
                )
            )

        # Convert action
        try:
            action = EmailAction(multi_pass_result.action)
        except ValueError:
            action = EmailAction.RIEN

        # Build AnalysisResult
        return AnalysisResult(
            extractions=extractions,
            action=action,
            confidence=multi_pass_result.confidence.overall,
            raisonnement=multi_pass_result.pass_history[-1].reasoning
            if multi_pass_result.pass_history
            else "",
            model_used=multi_pass_result.final_model,
            tokens_used=multi_pass_result.total_tokens,
            duration_ms=multi_pass_result.total_duration_ms,
            escalated=multi_pass_result.escalated,
            # V2.2 additional info stored in raisonnement
            draft_reply=multi_pass_result.draft_reply,
        )

    async def _analyze_with_multi_pass(
        self,
        event: PerceivedEvent,
    ) -> tuple[AnalysisResult, MultiPassResult]:
        """
        Analyze event using MultiPassAnalyzer (v2.2).

        Args:
            event: Event to analyze

        Returns:
            Tuple of (AnalysisResult for compatibility, original MultiPassResult)
        """
        if not self.multi_pass_analyzer:
            raise RuntimeError("MultiPassAnalyzer not initialized (use_multi_pass=False)")

        # Get sender importance from event
        sender_importance = "normal"
        if event.sender:
            # Could be enhanced with VIP detection from notes
            sender_importance = getattr(event.sender, "importance", "normal") or "normal"

        # Run multi-pass analysis
        multi_pass_result = await self.multi_pass_analyzer.analyze(
            event=event,
            sender_importance=sender_importance,
        )

        # Convert to AnalysisResult for backward compatibility
        analysis_result = self._convert_multi_pass_result(multi_pass_result)

        return analysis_result, multi_pass_result

    async def process_batch(
        self,
        events: list[PerceivedEvent],
        auto_apply: bool = True,
    ) -> list[V2ProcessingResult]:
        """
        Process multiple events sequentially.

        Args:
            events: List of events to process
            auto_apply: Whether to auto-apply high-confidence extractions

        Returns:
            List of V2ProcessingResult objects
        """
        results = []

        for i, event in enumerate(events):
            logger.debug(f"Processing event {i + 1}/{len(events)}: {event.event_id}")
            result = await self.process_event(event, auto_apply=auto_apply)
            results.append(result)

        # Log summary
        successful = sum(1 for r in results if r.success)
        auto_applied = sum(1 for r in results if r.auto_applied)
        total_extractions = sum(r.extraction_count for r in results)

        logger.info(
            "Batch processing complete",
            extra={
                "total": len(events),
                "successful": successful,
                "auto_applied": auto_applied,
                "total_extractions": total_extractions,
            },
        )

        return results


def create_v2_processor(
    config: Optional[WorkflowV2Config] = None,
) -> V2EmailProcessor:
    """
    Factory function to create a V2EmailProcessor using the Four Valets system.

    Args:
        config: Optional WorkflowV2Config

    Returns:
        Configured V2EmailProcessor instance
    """
    return V2EmailProcessor(config=config)
