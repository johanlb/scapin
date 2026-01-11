"""
V2 Email Processor — Workflow v2.1 Knowledge Extraction

Processeur d'emails utilisant le pipeline d'extraction de connaissances v2.1.

Ce processeur intègre :
1. EventAnalyzer pour l'analyse et l'extraction
2. PKMEnricher pour l'application au PKM
3. OmniFocusClient pour les tâches (optionnel)

Usage:
    processor = V2EmailProcessor()
    result = await processor.process_event(event, context_notes)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.core.config_manager import WorkflowV2Config, get_config
from src.core.events.universal_event import PerceivedEvent
from src.core.models.v2_models import (
    AnalysisResult,
    ContextNote,
    EmailAction,
    EnrichmentResult,
)
from src.integrations.apple.omnifocus import OmniFocusClient, create_omnifocus_client
from src.monitoring.logger import get_logger
from src.passepartout.context_engine import ContextEngine
from src.passepartout.enricher import PKMEnricher
from src.passepartout.note_manager import NoteManager
from src.sancho.analyzer import EventAnalyzer
from src.sancho.router import AIRouter, get_ai_router

logger = get_logger("v2_processor")


@dataclass
class V2ProcessingResult:
    """
    Résultat du traitement v2.1 d'un événement.

    Attributes:
        success: True si le traitement a réussi
        event_id: ID de l'événement traité
        analysis: Résultat de l'analyse (si réussie)
        enrichment: Résultat de l'enrichissement PKM (si applicable)
        email_action: Action recommandée sur l'email
        error: Message d'erreur (si échec)
        duration_ms: Durée totale en millisecondes
        auto_applied: True si les extractions ont été auto-appliquées
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


class V2EmailProcessor:
    """
    Processeur d'emails utilisant le Workflow v2.1.

    Pipeline:
    1. Récupération du contexte (notes pertinentes)
    2. Analyse avec EventAnalyzer (Haiku → Sonnet si besoin)
    3. Si confiance >= auto_apply_threshold : application automatique
    4. Sinon : mise en queue pour revue humaine

    Attributes:
        config: Configuration WorkflowV2Config
        analyzer: EventAnalyzer pour l'extraction
        enricher: PKMEnricher pour l'application
        context_engine: ContextEngine pour la récupération de contexte

    Example:
        >>> processor = V2EmailProcessor()
        >>> result = await processor.process_event(event)
        >>> if result.success and result.auto_applied:
        ...     print(f"Applied {result.extraction_count} extractions")
    """

    def __init__(
        self,
        config: Optional[WorkflowV2Config] = None,
        ai_router: Optional[AIRouter] = None,
        note_manager: Optional[NoteManager] = None,
        omnifocus_client: Optional[OmniFocusClient] = None,
    ):
        """
        Initialize the V2 processor.

        Args:
            config: WorkflowV2Config (uses defaults if None)
            ai_router: AIRouter instance (creates default if None)
            note_manager: NoteManager instance (creates default if None)
            omnifocus_client: OmniFocusClient (creates default if enabled)
        """
        self.config = config or WorkflowV2Config()

        # Initialize AI router
        if ai_router is None:
            app_config = get_config()
            ai_router = get_ai_router(app_config.ai)
        self.ai_router = ai_router

        # Initialize note manager
        if note_manager is None:
            app_config = get_config()
            note_manager = NoteManager(notes_dir=app_config.storage.notes_path)
        self.note_manager = note_manager

        # Initialize context engine
        self.context_engine = ContextEngine(note_manager=self.note_manager)

        # Initialize analyzer
        self.analyzer = EventAnalyzer(
            ai_router=self.ai_router,
            config=self.config,
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
            "V2EmailProcessor initialized",
            extra={
                "default_model": self.config.default_model,
                "escalation_model": self.config.escalation_model,
                "escalation_threshold": self.config.escalation_threshold,
                "auto_apply_threshold": self.config.auto_apply_threshold,
                "omnifocus_enabled": self.config.omnifocus_enabled,
            },
        )

    async def process_event(
        self,
        event: PerceivedEvent,
        context_notes: Optional[list[ContextNote]] = None,
        auto_apply: bool = True,
    ) -> V2ProcessingResult:
        """
        Process a single event through the v2.1 pipeline.

        Args:
            event: PerceivedEvent to process
            context_notes: Pre-fetched context notes (fetches if None)
            auto_apply: Whether to auto-apply high-confidence extractions

        Returns:
            V2ProcessingResult with analysis and enrichment results
        """
        import time

        start_time = time.time()

        try:
            # Step 1: Get context notes if not provided
            if context_notes is None:
                context_notes = await self._get_context_notes(event)

            logger.debug(
                f"Processing event {event.event_id} with {len(context_notes)} context notes"
            )

            # Step 2: Analyze event
            analysis = await self.analyzer.analyze(event, context_notes)

            logger.info(
                f"Analysis complete for {event.event_id}",
                extra={
                    "confidence": analysis.confidence,
                    "extractions": analysis.extraction_count,
                    "escalated": analysis.escalated,
                    "model": analysis.model_used,
                },
            )

            # Step 3: Determine if we should auto-apply
            should_apply = (
                auto_apply
                and analysis.high_confidence
                and analysis.confidence >= self.config.auto_apply_threshold
                and analysis.has_extractions
            )

            enrichment = None
            if should_apply:
                # Step 4: Apply extractions to PKM
                enrichment = await self.enricher.apply(analysis, event.event_id)

                logger.info(
                    f"Auto-applied extractions for {event.event_id}",
                    extra={
                        "notes_updated": len(enrichment.notes_updated),
                        "notes_created": len(enrichment.notes_created),
                        "tasks_created": len(enrichment.tasks_created),
                        "errors": len(enrichment.errors),
                    },
                )

            duration_ms = (time.time() - start_time) * 1000

            return V2ProcessingResult(
                success=True,
                event_id=event.event_id,
                analysis=analysis,
                enrichment=enrichment,
                email_action=analysis.action,
                auto_applied=should_apply and enrichment is not None,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"V2 processing failed for {event.event_id}: {e}")

            return V2ProcessingResult(
                success=False,
                event_id=event.event_id,
                error=str(e),
                duration_ms=duration_ms,
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
    Factory function to create a V2EmailProcessor.

    Args:
        config: Optional WorkflowV2Config

    Returns:
        Configured V2EmailProcessor instance
    """
    return V2EmailProcessor(config=config)
