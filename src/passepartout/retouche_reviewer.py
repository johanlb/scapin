"""
Retouche Reviewer — Memory Cycles (v2)

AI-powered automatic note improvement system.
Implements the Retouche cycle: automated quality enhancement of notes.

Actions:
1. enrich — Add missing information
2. structure — Reorganize sections
3. summarize — Generate summary header
4. score — Calculate quality score (0-100)
5. inject_questions — Add questions for Johan
6. restructure_graph — Suggest splitting/merging (high confidence only)

Phase 1 of Retouche implementation uses AnalysisEngine for AI calls.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import Note, NoteManager
from src.passepartout.note_metadata import (
    EnrichmentRecord,
    NoteMetadata,
    NoteMetadataStore,
)
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import CycleType
from src.sancho.analysis_engine import (
    AICallError,
    AICallResult,
    AnalysisEngine,
    JSONParseError,
    ModelTier,
)

if TYPE_CHECKING:
    from src.sancho.router import AIRouter

logger = get_logger("passepartout.retouche_reviewer")


class RetoucheAction(str, Enum):
    """Types of Retouche actions"""

    ENRICH = "enrich"  # Enrichir contenu
    STRUCTURE = "structure"  # Réorganiser sections
    SUMMARIZE = "summarize"  # Générer résumé
    SCORE = "score"  # Évaluer qualité
    INJECT_QUESTIONS = "inject_questions"  # Ajouter questions pour Johan
    RESTRUCTURE_GRAPH = "restructure_graph"  # Scinder/fusionner (suggestion)


@dataclass
class RetoucheActionResult:
    """Result of a single Retouche action"""

    action_type: RetoucheAction
    target: str  # Section or content being targeted
    content: Optional[str] = None  # New/modified content
    confidence: float = 0.5  # 0.0 - 1.0
    reasoning: str = ""
    applied: bool = False
    model_used: str = "haiku"  # Which model performed this action


@dataclass
class RetoucheResult:
    """Complete result of a Retouche cycle"""

    note_id: str
    success: bool
    quality_before: Optional[int]  # 0-100
    quality_after: int  # 0-100
    actions: list[RetoucheActionResult] = field(default_factory=list)
    questions_added: int = 0
    model_used: str = "haiku"  # Final model used
    escalated: bool = False  # Whether we escalated to a higher model
    reasoning: str = ""
    error: Optional[str] = None


@dataclass
class RetoucheContext:
    """Context collected for Retouche analysis"""

    note: Note
    metadata: NoteMetadata
    linked_notes: list[Note] = field(default_factory=list)
    linked_note_excerpts: dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    has_summary: bool = False
    section_count: int = 0
    question_count: int = 0


class RetoucheReviewer:
    """
    AI-powered automatic note improvement system.

    The Retouche cycle:
    1. Loads note + context (linked notes)
    2. Analyzes with Haiku (fast, cheap)
    3. Escalates to Sonnet if confidence < 0.7
    4. Escalates to Opus if confidence < 0.5
    5. Applies improvement actions
    6. Updates SM-2 retouche scheduling

    Uses AnalysisEngine for AI calls with automatic escalation and JSON parsing.
    """

    # Confidence thresholds for model escalation
    ESCALATE_TO_SONNET_THRESHOLD = 0.7
    ESCALATE_TO_OPUS_THRESHOLD = 0.5

    # Auto-apply thresholds
    AUTO_APPLY_THRESHOLD = 0.85
    RESTRUCTURE_THRESHOLD = 0.95  # Very high for destructive suggestions

    def __init__(
        self,
        note_manager: NoteManager,
        metadata_store: NoteMetadataStore,
        scheduler: NoteScheduler,
        ai_router: Optional["AIRouter"] = None,
    ):
        """
        Initialize Retouche reviewer

        Args:
            note_manager: Note manager for accessing notes
            metadata_store: Store for metadata
            scheduler: Scheduler for updating review times
            ai_router: AI router for analysis (Sancho)
        """
        self.notes = note_manager
        self.store = metadata_store
        self.scheduler = scheduler
        self.ai_router = ai_router

        # Initialize AnalysisEngine for AI calls if router available
        self._analysis_engine: Optional[AnalysisEngine] = None
        if ai_router:
            self._analysis_engine = _RetoucheAnalysisEngine(
                ai_router=ai_router,
                escalation_thresholds={
                    "sonnet": self.ESCALATE_TO_SONNET_THRESHOLD,
                    "opus": self.ESCALATE_TO_OPUS_THRESHOLD,
                },
            )

    async def review_note(self, note_id: str) -> RetoucheResult:
        """
        Perform a Retouche review of a note

        Args:
            note_id: Note to review

        Returns:
            RetoucheResult with actions taken
        """
        logger.info(f"Starting Retouche for note {note_id}")

        # Load note
        note = self.notes.get_note(note_id)
        if note is None:
            return RetoucheResult(
                note_id=note_id,
                success=False,
                quality_before=None,
                quality_after=0,
                error="Note not found",
            )

        # Load or create metadata
        metadata = self.store.get(note_id)
        if metadata is None:
            from src.passepartout.note_types import detect_note_type_from_path

            note_type = detect_note_type_from_path(str(note.file_path) if note.file_path else "")
            metadata = self.store.create_for_note(
                note_id=note_id,
                note_type=note_type,
                content=note.content,
            )

        quality_before = metadata.quality_score

        # Build context
        context = await self._load_context(note, metadata)

        # Analyze with progressive model escalation
        analysis_result = await self._analyze_with_escalation(context)

        # Process actions
        actions = []
        questions_added = 0
        updated_content = note.content

        for action in analysis_result.actions:
            if action.applied:
                actions.append(action)
                if action.action_type == RetoucheAction.INJECT_QUESTIONS:
                    questions_added += action.content.count("?") if action.content else 0

        # Apply content changes
        for action in actions:
            if action.content and action.action_type in (
                RetoucheAction.ENRICH,
                RetoucheAction.STRUCTURE,
                RetoucheAction.SUMMARIZE,
            ):
                updated_content = self._apply_action(updated_content, action)

        # Calculate new quality score
        quality_after = self._calculate_quality_score(context, analysis_result)

        # Save updated note if changes were made
        if updated_content != note.content:
            self.notes.update_note(
                note_id=note_id,
                content=updated_content,
            )

        # Update metadata with new quality score and questions
        metadata.quality_score = quality_after
        if questions_added > 0:
            metadata.questions_pending = True
            metadata.questions_count += questions_added

        # Record actions in enrichment_history
        now = datetime.now(timezone.utc)
        for action in actions:
            record = EnrichmentRecord(
                timestamp=now,
                action_type=action.action_type.value,
                target=action.target,
                content=action.content,
                confidence=action.confidence,
                applied=action.applied,
                reasoning=f"[{action.model_used}] {action.reasoning}",
            )
            metadata.enrichment_history.append(record)

        # Schedule Lecture after first successful Retouche
        if metadata.lecture_next is None and quality_after >= 50:
            # Schedule first Lecture for 24h from now
            metadata.lecture_next = datetime.now(timezone.utc) + timedelta(hours=24)

        # Record Retouche review (updates SM-2)
        self.scheduler.record_review(
            note_id=note_id,
            quality=self._quality_to_sm2(quality_after),
            metadata=metadata,
            cycle_type=CycleType.RETOUCHE,
        )

        logger.info(
            f"Retouche complete for {note_id}: "
            f"quality={quality_before or 0}→{quality_after}, "
            f"actions={len(actions)}, questions={questions_added}, "
            f"model={analysis_result.model_used}"
        )

        return RetoucheResult(
            note_id=note_id,
            success=True,
            quality_before=quality_before,
            quality_after=quality_after,
            actions=actions,
            questions_added=questions_added,
            model_used=analysis_result.model_used,
            escalated=analysis_result.escalated,
            reasoning=analysis_result.reasoning,
        )

    async def _load_context(
        self,
        note: Note,
        metadata: NoteMetadata,
    ) -> RetoucheContext:
        """Load context for Retouche analysis"""

        # Find linked notes via wikilinks
        wikilinks = self._extract_wikilinks(note.content)
        linked_notes = []
        linked_excerpts = {}

        for link in wikilinks[:10]:  # Limit to 10 linked notes
            linked_note_results = self.notes.search_notes(query=link, top_k=1)
            if linked_note_results:
                if isinstance(linked_note_results[0], tuple):
                    linked_note_obj = linked_note_results[0][0]
                else:
                    linked_note_obj = linked_note_results[0]
                linked_notes.append(linked_note_obj)
                linked_excerpts[link] = linked_note_obj.content[:500]

        # Calculate basic metrics
        word_count = len(note.content.split())
        has_summary = self._has_summary(note.content)
        section_count = len(re.findall(r"^##\s", note.content, re.MULTILINE))
        question_count = note.content.count("?")

        return RetoucheContext(
            note=note,
            metadata=metadata,
            linked_notes=linked_notes,
            linked_note_excerpts=linked_excerpts,
            word_count=word_count,
            has_summary=has_summary,
            section_count=section_count,
            question_count=question_count,
        )

    def _extract_wikilinks(self, content: str) -> list[str]:
        """Extract wikilinks from content"""
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        return re.findall(pattern, content)

    def _has_summary(self, content: str) -> bool:
        """Check if content has a summary section"""
        summary_patterns = [
            r"^##?\s*(Résumé|Summary|TL;DR|En bref)",
            r"^>\s*\*\*Résumé",
        ]
        for pattern in summary_patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return True
        return False

    async def _analyze_with_escalation(
        self,
        context: RetoucheContext,
    ) -> "AnalysisResult":
        """
        Analyze note with progressive model escalation

        Starts with Haiku, escalates to Sonnet then Opus if confidence is low.
        """
        # Start with Haiku
        result = await self._analyze_with_model(context, model="haiku")

        # Escalate to Sonnet if confidence too low
        if result.confidence < self.ESCALATE_TO_SONNET_THRESHOLD:
            logger.info(
                f"Escalating to Sonnet (confidence={result.confidence:.2f} < {self.ESCALATE_TO_SONNET_THRESHOLD})"
            )
            result = await self._analyze_with_model(context, model="sonnet")
            result.escalated = True

            # Escalate to Opus if still too low
            if result.confidence < self.ESCALATE_TO_OPUS_THRESHOLD:
                logger.info(
                    f"Escalating to Opus (confidence={result.confidence:.2f} < {self.ESCALATE_TO_OPUS_THRESHOLD})"
                )
                result = await self._analyze_with_model(context, model="opus")

        return result

    async def _analyze_with_model(
        self,
        context: RetoucheContext,
        model: str = "haiku",
    ) -> "AnalysisResult":
        """Analyze note with a specific model"""

        # If no AI router, use rule-based analysis
        if self.ai_router is None:
            return self._rule_based_analysis(context)

        try:
            # Build prompt for Retouche analysis
            prompt = self._build_retouche_prompt(context)

            # Call AI router with specified model
            response = await self._call_ai_router(prompt, model)

            # Parse response into actions
            actions = self._parse_ai_response(response, model)

            # Calculate overall confidence
            confidence = sum(a.confidence for a in actions) / len(actions) if actions else 0.8

            return AnalysisResult(
                actions=actions,
                confidence=confidence,
                model_used=model,
                escalated=False,
                reasoning=response.get("reasoning", "AI analysis complete"),
            )

        except Exception as e:
            logger.warning(f"AI analysis failed with {model}: {e}")
            return self._rule_based_analysis(context)

    def _rule_based_analysis(self, context: RetoucheContext) -> "AnalysisResult":
        """Fallback rule-based analysis when AI is unavailable"""
        actions = []

        # Check if summary is needed
        if not context.has_summary and context.word_count > 200:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.SUMMARIZE,
                    target="header",
                    confidence=0.9,
                    reasoning="Note has sufficient content but no summary",
                    applied=True,
                    model_used="rules",
                )
            )

        # Check if structure improvements are needed
        if context.word_count > 500 and context.section_count < 2:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.STRUCTURE,
                    target="content",
                    confidence=0.8,
                    reasoning="Long content with few sections",
                    applied=True,
                    model_used="rules",
                )
            )

        # Always include quality scoring
        actions.append(
            RetoucheActionResult(
                action_type=RetoucheAction.SCORE,
                target="quality",
                confidence=0.95,
                reasoning="Quality assessment",
                applied=True,
                model_used="rules",
            )
        )

        return AnalysisResult(
            actions=actions,
            confidence=0.75,
            model_used="rules",
            escalated=False,
            reasoning="Rule-based analysis (AI unavailable)",
        )

    def _build_retouche_prompt(self, context: RetoucheContext) -> str:
        """Build prompt for AI Retouche analysis"""
        linked_context = ""
        if context.linked_note_excerpts:
            linked_context = "\n\n## Notes liées:\n"
            for title, excerpt in list(context.linked_note_excerpts.items())[:5]:
                linked_context += f"\n### {title}\n{excerpt[:300]}...\n"

        return f"""Tu es Scapin, un assistant cognitif qui améliore les notes de Johan.

## Note à analyser:
**Titre**: {context.note.title}
**Type**: {context.metadata.note_type.value}
**Mots**: {context.word_count}
**Sections**: {context.section_count}
**Résumé présent**: {'Oui' if context.has_summary else 'Non'}

## Contenu:
{context.note.content[:3000]}

{linked_context}

## Ta mission:
Analyse cette note et propose des améliorations. Pour chaque action, indique:
- Type: enrich, structure, summarize, inject_questions
- Cible: quelle partie de la note
- Contenu: le nouveau contenu proposé
- Confiance: 0.0 à 1.0
- Raisonnement: pourquoi cette action

Réponds en JSON avec ce format:
{{
  "quality_score": 0-100,
  "reasoning": "...",
  "actions": [
    {{
      "type": "enrich|structure|summarize|inject_questions",
      "target": "...",
      "content": "...",
      "confidence": 0.0-1.0,
      "reasoning": "..."
    }}
  ]
}}
"""

    async def _call_ai_router(
        self,
        prompt: str,
        model: str,
    ) -> dict[str, Any]:
        """
        Call AI router with specified model using AnalysisEngine.

        Args:
            prompt: Rendered prompt for the analysis
            model: Model name ("haiku", "sonnet", "opus")

        Returns:
            Parsed JSON response dict

        Raises:
            Exception: If AI call fails (triggers rule-based fallback)
        """
        if self._analysis_engine is None:
            logger.warning("No analysis engine available, returning empty response")
            return {"reasoning": "AI unavailable", "actions": []}

        # Map model string to ModelTier
        model_map = {
            "haiku": ModelTier.HAIKU,
            "sonnet": ModelTier.SONNET,
            "opus": ModelTier.OPUS,
        }
        model_tier = model_map.get(model.lower(), ModelTier.HAIKU)

        try:
            # Call AI using AnalysisEngine
            result = await self._analysis_engine.call_ai(
                prompt=prompt,
                model=model_tier,
                max_tokens=2048,
            )

            # Parse JSON response
            data = self._analysis_engine.parse_json_response(result.response)

            logger.debug(
                f"Retouche AI call successful: model={model}, tokens={result.tokens_used}"
            )

            return data

        except (AICallError, JSONParseError) as e:
            logger.warning(f"Retouche AI call failed: {e}")
            raise

    def _parse_ai_response(
        self,
        response: dict[str, Any],
        model: str,
    ) -> list[RetoucheActionResult]:
        """Parse AI response into RetoucheActionResult list"""
        actions = []

        for action_data in response.get("actions", []):
            action_type_str = action_data.get("type", "score")
            try:
                action_type = RetoucheAction(action_type_str)
            except ValueError:
                action_type = RetoucheAction.SCORE

            confidence = float(action_data.get("confidence", 0.5))
            should_apply = confidence >= self.AUTO_APPLY_THRESHOLD

            # Restructure actions need very high confidence
            if action_type == RetoucheAction.RESTRUCTURE_GRAPH:
                should_apply = confidence >= self.RESTRUCTURE_THRESHOLD

            actions.append(
                RetoucheActionResult(
                    action_type=action_type,
                    target=action_data.get("target", ""),
                    content=action_data.get("content"),
                    confidence=confidence,
                    reasoning=action_data.get("reasoning", ""),
                    applied=should_apply,
                    model_used=model,
                )
            )

        return actions

    def _apply_action(self, content: str, action: RetoucheActionResult) -> str:
        """Apply a Retouche action to content"""

        if action.action_type == RetoucheAction.SUMMARIZE:
            # Add summary at the beginning after frontmatter
            summary = f"\n> **Résumé**: {action.content or 'À compléter'}\n"
            if content.startswith("---"):
                # Insert after frontmatter
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return f"---{parts[1]}---{summary}{parts[2]}"
            return summary + content

        if action.action_type == RetoucheAction.ENRICH:
            # Append enrichment content
            if action.content:
                return f"{content.rstrip()}\n\n{action.content}"
            return content

        if action.action_type == RetoucheAction.STRUCTURE:
            # For now, just log - full restructuring is complex
            logger.info(f"Structure suggestion: {action.reasoning}")
            return content

        if action.action_type == RetoucheAction.INJECT_QUESTIONS:
            # Add questions section
            if action.content:
                questions_section = f"\n\n## Questions pour Johan\n\n{action.content}\n"
                return f"{content.rstrip()}{questions_section}"
            return content

        return content

    def _calculate_quality_score(
        self,
        context: RetoucheContext,
        analysis: "AnalysisResult",
    ) -> int:
        """
        Calculate quality score (0-100)

        Factors:
        - Word count (10-1000+ words)
        - Has summary
        - Section structure
        - Links to other notes
        - Completeness
        """
        score = 50  # Base score

        # Word count bonus (up to +20)
        if context.word_count >= 100:
            score += min(20, context.word_count // 50)

        # Summary bonus (+15)
        if context.has_summary:
            score += 15

        # Section structure bonus (up to +10)
        score += min(10, context.section_count * 3)

        # Links bonus (up to +10)
        score += min(10, len(context.linked_notes) * 2)

        # Actions applied penalty (-5 per action needed)
        actions_needed = sum(1 for a in analysis.actions if a.applied)
        score -= actions_needed * 5

        # Ensure score is in valid range
        return max(0, min(100, score))

    def _quality_to_sm2(self, quality_score: int) -> int:
        """Convert quality score (0-100) to SM-2 quality (0-5)"""
        if quality_score >= 90:
            return 5
        if quality_score >= 75:
            return 4
        if quality_score >= 60:
            return 3
        if quality_score >= 40:
            return 2
        if quality_score >= 20:
            return 1
        return 0


@dataclass
class AnalysisResult:
    """Internal result of AI/rule-based analysis"""

    actions: list[RetoucheActionResult]
    confidence: float
    model_used: str
    escalated: bool
    reasoning: str


class _RetoucheAnalysisEngine(AnalysisEngine):
    """
    Internal AnalysisEngine implementation for Retouche.

    Provides AI call functionality with escalation and JSON parsing.
    This is a minimal implementation - the actual prompt building and
    result processing are handled by RetoucheReviewer.
    """

    def _build_prompt(self, context: Any) -> str:
        """Not used - prompts are built by RetoucheReviewer."""
        raise NotImplementedError("Use RetoucheReviewer._build_retouche_prompt()")

    def _process_result(self, result: dict[str, Any], call_result: AICallResult) -> Any:
        """Not used - results are processed by RetoucheReviewer."""
        raise NotImplementedError("Use RetoucheReviewer._parse_ai_response()")
