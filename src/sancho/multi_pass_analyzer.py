"""
Multi-Pass Analyzer — Workflow v2.2

Analyseur d'événements avec architecture multi-passes et escalade intelligente
Haiku → Sonnet → Opus.

Ce module implémente la phase d'analyse du pipeline v2.2 :
1. Pass 1: Extraction aveugle (Haiku, sans contexte)
2. Pass 2-3: Raffinement contextuel (Haiku, avec ContextSearcher)
3. Pass 4: Raisonnement profond (Sonnet, si confidence < 80%)
4. Pass 5: Analyse expert (Opus, si confidence < 75% ou high-stakes)

Key innovations v2.2:
- Extraction → Contexte → Raffinement (inverted flow)
- DecomposedConfidence (entity, action, extraction, completeness)
- Convergence-based stopping (not fixed passes)
- Targeted model escalation

Usage:
    analyzer = MultiPassAnalyzer(ai_router, context_searcher)
    result = await analyzer.analyze(event)

Part of Sancho's multi-pass extraction system (v2.2).
See ADR-005 in MULTI_PASS_SPEC.md for design decisions.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from src.core.events.universal_event import PerceivedEvent
from src.monitoring.logger import get_logger
from src.sancho.context_searcher import ContextSearcher, StructuredContext
from src.sancho.convergence import (
    AnalysisContext,
    DecomposedConfidence,
    Extraction,
    ExtractionConfidence,
    MultiPassConfig,
    PassResult,
    PassType,
    get_pass_type,
    is_high_stakes,
    select_model,
    should_stop,
)
from src.sancho.model_selector import ModelTier
from src.sancho.router import AIModel, AIRouter, _repair_json_with_library, clean_json_string
from src.sancho.template_renderer import TemplateRenderer, get_template_renderer

if TYPE_CHECKING:
    from src.passepartout.entity_search import EntitySearcher
    from src.passepartout.note_manager import NoteManager
    from src.sancho.coherence_validator import CoherenceResult, CoherenceService

logger = get_logger("multi_pass_analyzer")

# Age thresholds for action adjustments
# Emails older than this get "flag" downgraded to "archive"
OLD_EMAIL_THRESHOLD_DAYS = 90  # 3 months
# Emails older than this don't get OmniFocus tasks created
VERY_OLD_EMAIL_THRESHOLD_DAYS = 365  # 1 year


class MultiPassAnalyzerError(Exception):
    """Base exception for multi-pass analyzer errors"""

    pass


class PromptRenderError(MultiPassAnalyzerError):
    """Error rendering the prompt template"""

    pass


class APICallError(MultiPassAnalyzerError):
    """Error calling the AI API"""

    pass


class ParseError(MultiPassAnalyzerError):
    """Error parsing the AI response"""

    pass


class MaxPassesReachedError(MultiPassAnalyzerError):
    """Maximum number of passes reached without convergence"""

    pass


@dataclass
class MultiPassResult:
    """Final result of multi-pass analysis"""

    # Final extraction result
    extractions: list[Extraction]
    action: str
    confidence: DecomposedConfidence
    entities_discovered: set[str]

    # Analysis metadata
    passes_count: int
    total_duration_ms: float
    total_tokens: int
    final_model: str
    escalated: bool

    # Pass history for transparency
    pass_history: list[PassResult] = field(default_factory=list)

    # Stop reason
    stop_reason: str = ""

    # High-stakes indicator
    high_stakes: bool = False

    # Draft reply (if action is reply)
    draft_reply: Optional[str] = None

    # Coherence validation metadata (v2.2+)
    coherence_validated: bool = False
    coherence_corrections: int = 0
    coherence_duplicates_detected: int = 0
    coherence_confidence: float = 1.0
    coherence_warnings: list[dict] = field(default_factory=list)

    @property
    def high_confidence(self) -> bool:
        """Check if result is high confidence (>= 90%)"""
        return self.confidence.overall >= 0.90

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "extractions": [
                {
                    "info": e.info,
                    "type": e.type,
                    "importance": e.importance,
                    "note_cible": e.note_cible,
                    "note_action": e.note_action,
                    "omnifocus": e.omnifocus,
                    "calendar": e.calendar,
                    "date": e.date,
                    "time": e.time,
                    "timezone": e.timezone,
                    "duration": e.duration,
                    "required": e.required,
                    "confidence": e.confidence,
                }
                for e in self.extractions
            ],
            "action": self.action,
            "confidence": self.confidence.to_dict(),
            "entities_discovered": list(self.entities_discovered),
            "passes_count": self.passes_count,
            "total_duration_ms": self.total_duration_ms,
            "total_tokens": self.total_tokens,
            "final_model": self.final_model,
            "escalated": self.escalated,
            "stop_reason": self.stop_reason,
            "high_stakes": self.high_stakes,
            "high_confidence": self.high_confidence,
            "pass_history": [p.to_dict() for p in self.pass_history],
            "draft_reply": self.draft_reply,
            # Coherence validation (v2.2+)
            "coherence_validated": self.coherence_validated,
            "coherence_corrections": self.coherence_corrections,
            "coherence_duplicates_detected": self.coherence_duplicates_detected,
            "coherence_confidence": self.coherence_confidence,
            "coherence_warnings": self.coherence_warnings,
        }


class MultiPassAnalyzer:
    """
    Multi-pass event analyzer with intelligent model escalation.

    Implements the v2.2 multi-pass architecture:
    - Pass 1: Blind extraction (no context)
    - Pass 2-3: Contextual refinement
    - Pass 4: Sonnet escalation
    - Pass 5: Opus expert analysis

    Attributes:
        ai_router: Router for Claude API calls
        context_searcher: Searcher for PKM context
        template_renderer: Jinja2 template renderer
        config: Multi-pass configuration

    Example:
        >>> analyzer = MultiPassAnalyzer(router, context_searcher)
        >>> result = await analyzer.analyze(event)
        >>> if result.high_confidence:
        ...     # Auto-apply extractions
        ...     pass
    """

    # Model tier mapping
    MODEL_MAP = {
        ModelTier.HAIKU: AIModel.CLAUDE_HAIKU,
        ModelTier.SONNET: AIModel.CLAUDE_SONNET,
        ModelTier.OPUS: AIModel.CLAUDE_OPUS,
    }

    def __init__(
        self,
        ai_router: AIRouter,
        context_searcher: Optional["ContextSearcher"] = None,
        template_renderer: Optional[TemplateRenderer] = None,
        config: Optional[MultiPassConfig] = None,
        note_manager: Optional["NoteManager"] = None,
        entity_searcher: Optional["EntitySearcher"] = None,
        enable_coherence_pass: bool = True,
    ):
        """
        Initialize the multi-pass analyzer.

        Args:
            ai_router: AIRouter instance for API calls
            context_searcher: ContextSearcher for PKM context (optional)
            template_renderer: TemplateRenderer for prompts (optional, uses singleton)
            config: MultiPassConfig (uses defaults if None)
            note_manager: NoteManager for coherence validation (optional, enables coherence pass)
            entity_searcher: EntitySearcher for finding similar notes (optional)
            enable_coherence_pass: Whether to run coherence validation (default: True)
        """
        self.ai_router = ai_router
        self._context_searcher = context_searcher
        self._template_renderer = template_renderer
        self.config = config or MultiPassConfig()
        self._note_manager = note_manager
        self._entity_searcher = entity_searcher
        self._enable_coherence_pass = enable_coherence_pass
        self._coherence_service: "CoherenceService | None" = None  # noqa: UP037

    @property
    def context_searcher(self) -> Optional["ContextSearcher"]:
        """Get context searcher (lazy load if needed)"""
        return self._context_searcher

    @property
    def template_renderer(self) -> TemplateRenderer:
        """Get template renderer (singleton if not provided)"""
        if self._template_renderer is None:
            self._template_renderer = get_template_renderer()
        return self._template_renderer

    @property
    def coherence_service(self) -> Optional["CoherenceService"]:
        """
        Get coherence service (lazy initialization).

        Returns None if note_manager is not configured or coherence pass is disabled.
        """
        if not self._enable_coherence_pass or self._note_manager is None:
            return None

        if self._coherence_service is None:
            from src.sancho.coherence_validator import CoherenceService

            self._coherence_service = CoherenceService(
                note_manager=self._note_manager,
                ai_router=self.ai_router,
                entity_searcher=self._entity_searcher,
                template_renderer=self.template_renderer,
            )
        return self._coherence_service

    async def analyze(
        self,
        event: PerceivedEvent,
        sender_importance: str = "normal",
    ) -> MultiPassResult:
        """
        Analyze an event using multi-pass extraction.

        1. Pass 1: Blind extraction (Haiku, no context)
        2. If not converged: search context, run Pass 2
        3. Continue until convergence or max passes
        4. Escalate to Sonnet/Opus if needed

        Args:
            event: Perceived event to analyze
            sender_importance: Sender importance level (normal, important, vip)

        Returns:
            MultiPassResult with extractions and metadata

        Raises:
            MultiPassAnalyzerError: If analysis fails
        """
        start_time = time.time()
        total_tokens = 0
        pass_history: list[PassResult] = []
        context: Optional[StructuredContext] = None
        escalated = False

        # Build analysis context
        analysis_context = AnalysisContext(
            sender_importance=sender_importance,
            has_attachments=bool(getattr(event, "attachments", None)),
            is_thread=bool(getattr(event, "thread_id", None)),
        )

        # Pass 1: Blind extraction
        logger.info(f"Starting multi-pass analysis for event {event.event_id}")
        current_result = await self._run_pass1(event)
        pass_history.append(current_result)
        total_tokens += current_result.tokens_used

        # Check for early stop
        stop, reason = should_stop(current_result, None, self.config)
        if stop:
            logger.info(f"Stopping after Pass 1: {reason}")
            return self._build_result(
                pass_history,
                start_time,
                total_tokens,
                reason,
                escalated,
                analysis_context,
                event,
            )

        # Get context for subsequent passes
        if self.context_searcher and current_result.entities_discovered:
            logger.debug(f"Searching context for entities: {current_result.entities_discovered}")
            context = await self.context_searcher.search_for_entities(
                list(current_result.entities_discovered),
                sender_email=getattr(event.sender, "email", None) if event.sender else None,
            )

            # Update analysis context with conflict info
            if context and context.conflicts:
                analysis_context.has_conflicting_info = True

        # Passes 2-5: Iterate until convergence
        for pass_num in range(2, self.config.max_passes + 1):
            previous_result = current_result

            # Select model for this pass
            model_tier, model_reason = select_model(
                pass_num,
                previous_result.confidence.overall,
                analysis_context,
                self.config,
            )

            # Track escalation
            if model_tier in (ModelTier.SONNET, ModelTier.OPUS):
                escalated = True

            # Run appropriate pass
            pass_type = get_pass_type(pass_num)

            if pass_type == PassType.CONTEXTUAL_REFINEMENT:
                current_result = await self._run_pass2(
                    event,
                    previous_result,
                    context,
                    pass_num,
                    model_tier,
                )
            else:  # DEEP_REASONING or EXPERT_ANALYSIS
                current_result = await self._run_pass4(
                    event,
                    pass_history,
                    context,
                    pass_num,
                    model_tier,
                )

            pass_history.append(current_result)
            total_tokens += current_result.tokens_used

            # Check convergence
            stop, reason = should_stop(current_result, previous_result, self.config)
            if stop:
                logger.info(f"Stopping after Pass {pass_num}: {reason}")
                return self._build_result(
                    pass_history,
                    start_time,
                    total_tokens,
                    reason,
                    escalated,
                    analysis_context,
                    event,
                )

            # Search for new entities discovered in this pass
            if self.context_searcher:
                new_entities = current_result.entities_discovered - set().union(
                    *[p.entities_discovered for p in pass_history[:-1]]
                )
                if new_entities:
                    logger.debug(f"Found new entities in Pass {pass_num}: {new_entities}")
                    additional_context = await self.context_searcher.search_for_entities(
                        list(new_entities)
                    )
                    if context and additional_context:
                        # Merge contexts
                        context.notes.extend(additional_context.notes)
                        context.entity_profiles.update(additional_context.entity_profiles)

        # Max passes reached
        logger.warning(f"Max passes ({self.config.max_passes}) reached without convergence")
        return self._build_result(
            pass_history,
            start_time,
            total_tokens,
            f"max_passes_reached ({self.config.max_passes})",
            escalated,
            analysis_context,
            event,
        )

    async def _run_pass1(self, event: PerceivedEvent) -> PassResult:
        """
        Run Pass 1: Blind extraction without context.

        Args:
            event: Event to analyze

        Returns:
            PassResult from blind extraction
        """
        prompt = self.template_renderer.render_pass1(
            event=event,
            max_content_chars=self.config.max_content_chars,
        )

        return await self._call_model(
            prompt=prompt,
            model_tier=ModelTier.HAIKU,
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
        )

    async def _run_pass2(
        self,
        event: PerceivedEvent,
        previous_result: PassResult,
        context: Optional["StructuredContext"],
        pass_number: int,
        model_tier: ModelTier,
    ) -> PassResult:
        """
        Run Pass 2-3: Contextual refinement.

        Args:
            event: Event to analyze
            previous_result: Result from previous pass
            context: Structured context from searcher
            pass_number: Current pass number (2 or 3)
            model_tier: Model to use

        Returns:
            PassResult from contextual refinement
        """
        # Convert previous result to dict for template
        previous_dict = previous_result.to_dict()

        prompt = self.template_renderer.render_pass2(
            event=event,
            previous_result=previous_dict,
            context=context,
            max_content_chars=self.config.max_content_chars,
            max_context_notes=self.config.max_context_notes,
        )

        pass_type = PassType.CONTEXTUAL_REFINEMENT

        return await self._call_model(
            prompt=prompt,
            model_tier=model_tier,
            pass_number=pass_number,
            pass_type=pass_type,
        )

    async def _run_pass4(
        self,
        event: PerceivedEvent,
        pass_history: list[PassResult],
        context: Optional["StructuredContext"],
        pass_number: int,
        model_tier: ModelTier,
    ) -> PassResult:
        """
        Run Pass 4-5: Deep reasoning with Sonnet/Opus.

        Args:
            event: Event to analyze
            pass_history: History of all previous passes
            context: Full structured context
            pass_number: Current pass number (4 or 5)
            model_tier: Model to use (Sonnet or Opus)

        Returns:
            PassResult from deep reasoning
        """
        # Convert pass history to dicts for template
        passes_dicts = [p.to_dict() for p in pass_history]

        # Identify unresolved issues
        unresolved_issues = self._identify_unresolved_issues(pass_history)

        prompt = self.template_renderer.render_pass4(
            event=event,
            passes=passes_dicts,
            full_context=context,
            unresolved_issues=unresolved_issues,
        )

        pass_type = (
            PassType.EXPERT_ANALYSIS if model_tier == ModelTier.OPUS else PassType.DEEP_REASONING
        )

        return await self._call_model(
            prompt=prompt,
            model_tier=model_tier,
            pass_number=pass_number,
            pass_type=pass_type,
        )

    def _run_coherence_pass(
        self,
        extractions: list[Extraction],
        event: PerceivedEvent,
    ) -> tuple[list[Extraction], Optional["CoherenceResult"]]:
        """
        Run the coherence validation pass on extractions.

        This pass:
        1. Loads FULL content of target notes (not snippets)
        2. Validates enrichir vs creer decisions
        3. Detects duplicates
        4. Suggests appropriate sections
        5. Corrects note targets when needed

        Args:
            extractions: Extractions to validate
            event: Original event for context

        Returns:
            Tuple of (validated_extractions, coherence_result)
            If coherence service is not available, returns original extractions
            and None for coherence_result.
        """
        if not self.coherence_service or not extractions:
            return extractions, None

        # Only validate extractions that have a note target
        extractions_with_targets = [e for e in extractions if e.note_cible]
        if not extractions_with_targets:
            return extractions, None

        logger.info(f"Running coherence pass on {len(extractions_with_targets)} extractions")

        try:
            # Run coherence validation (synchronous)
            coherence_result = self.coherence_service.validate_extractions(
                extractions_with_targets, event
            )

            # Convert validated extractions back to Extraction objects
            validated_extractions = self._apply_coherence_validations(extractions, coherence_result)

            logger.info(
                f"Coherence pass completed: {coherence_result.coherence_summary.corrected} corrected, "
                f"{coherence_result.coherence_summary.duplicates_detected} duplicates"
            )

            return validated_extractions, coherence_result

        except Exception as e:
            logger.error(f"Coherence pass failed: {e}", exc_info=True)
            # Return original extractions on failure
            return extractions, None

    def _apply_coherence_validations(
        self,
        original_extractions: list[Extraction],
        coherence_result: "CoherenceResult",
    ) -> list[Extraction]:
        """
        Apply coherence validations to create updated Extraction list.

        Maps validated extractions back to Extraction objects,
        updating note targets and filtering duplicates.

        Args:
            original_extractions: Original extraction list
            coherence_result: Result from coherence validation

        Returns:
            Updated list of Extraction objects
        """

        # Create a map of original extractions by info for matching
        original_map: dict[str, Extraction] = {e.info: e for e in original_extractions}

        validated_extractions = []
        validated_set = set()  # Track which originals were validated

        for ve in coherence_result.validated_extractions:
            # Skip duplicates
            if ve.is_duplicate:
                logger.debug(f"Skipping duplicate extraction: {ve.info[:50]}...")
                continue

            # Find the original extraction
            original = original_map.get(ve.info)
            if not original:
                # Try to find by fuzzy match if exact match fails
                for key, ext in original_map.items():
                    if key not in validated_set and ve.info[:30] in key:
                        original = ext
                        break

            if original:
                validated_set.add(original.info)

                # Create updated extraction with validated values
                updated = Extraction(
                    info=original.info,
                    type=original.type,
                    importance=original.importance,
                    note_cible=ve.validated_note_cible or original.note_cible,
                    note_action=ve.note_action or original.note_action,
                    omnifocus=original.omnifocus,
                    calendar=original.calendar,
                    date=original.date,
                    time=original.time,
                    timezone=original.timezone,
                    duration=original.duration,
                    required=original.required,
                    confidence=original.confidence,
                    # Add suggested section if available (store in generic_title field for now)
                    generic_title=original.generic_title,
                )
                validated_extractions.append(updated)
            else:
                logger.warning(f"Could not match validated extraction: {ve.info[:50]}...")

        # Add extractions that weren't part of coherence validation
        # (those without note targets)
        for ext in original_extractions:
            if ext.info not in validated_set and not ext.note_cible:
                validated_extractions.append(ext)

        return validated_extractions

    def _identify_unresolved_issues(self, pass_history: list[PassResult]) -> list[str]:
        """
        Identify issues that remain unresolved across passes.

        Args:
            pass_history: History of all passes

        Returns:
            List of unresolved issue descriptions
        """
        issues = []

        if not pass_history:
            return issues

        last_pass = pass_history[-1]

        # Check weak confidence dimensions
        weak_dims = last_pass.confidence.needs_improvement(threshold=0.85)
        for dim in weak_dims:
            issues.append(
                f"Low {dim} confidence ({getattr(last_pass.confidence, f'{dim}_confidence', 0):.0%})"
            )

        # Check for oscillating actions across passes
        if len(pass_history) >= 2:
            actions = [p.action for p in pass_history]
            if len(set(actions)) > 1:
                issues.append(f"Action oscillating between: {', '.join(set(actions))}")

        # Check for conflicting extractions
        # (same note_cible with different info)
        all_extractions: dict[str, list[str]] = {}
        for p in pass_history:
            for e in p.extractions:
                if e.note_cible:
                    if e.note_cible not in all_extractions:
                        all_extractions[e.note_cible] = []
                    all_extractions[e.note_cible].append(e.info)

        for note, infos in all_extractions.items():
            if len(set(infos)) > 1:
                issues.append(f"Conflicting info for '{note}'")

        return issues

    async def _call_model(
        self,
        prompt: str,
        model_tier: ModelTier,
        pass_number: int,
        pass_type: PassType,
    ) -> PassResult:
        """
        Call the AI model and parse the response.

        Args:
            prompt: Rendered prompt
            model_tier: Model tier to use
            pass_number: Current pass number
            pass_type: Type of pass

        Returns:
            Parsed PassResult

        Raises:
            APICallError: If API call fails
            ParseError: If response parsing fails
        """
        start_time = time.time()
        model = self.MODEL_MAP[model_tier]

        try:
            # Call Claude via router
            response, usage = self.ai_router._call_claude(
                prompt=prompt,
                model=model,
                max_tokens=2048,
            )

            duration_ms = (time.time() - start_time) * 1000

            if response is None:
                raise APICallError("API returned None response")

            # Parse response
            return self._parse_response(
                response=response,
                model_tier=model_tier,
                model_id=model.value,
                pass_number=pass_number,
                pass_type=pass_type,
                usage=usage,
                duration_ms=duration_ms,
            )

        except ParseError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"API call failed for Pass {pass_number}: {e}", exc_info=True)
            raise APICallError(f"API call failed: {e}") from e

    def _parse_response(
        self,
        response: str,
        model_tier: ModelTier,
        model_id: str,
        pass_number: int,
        pass_type: PassType,
        usage: dict,
        duration_ms: float,
    ) -> PassResult:
        """
        Parse the JSON response into PassResult.

        Args:
            response: Raw response text from Claude
            model_tier: Model tier used
            model_id: Full model ID
            pass_number: Pass number
            pass_type: Pass type
            usage: Token usage dict
            duration_ms: API call duration

        Returns:
            Parsed PassResult

        Raises:
            ParseError: If JSON parsing fails
        """
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)

            # Multi-level JSON repair strategy (same as router.py)
            # Level 1: Direct parse (ideal case)
            # Level 2: json-repair library (robust, handles most issues)
            # Level 3: Regex cleaning + json-repair (last resort)
            data = None
            parse_method = "direct"

            # Level 1: Try direct parse
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Level 2: Try json-repair library first
                repaired, repair_success = _repair_json_with_library(json_str)
                if repair_success:
                    try:
                        data = json.loads(repaired)
                        parse_method = "json-repair"
                        logger.debug("JSON repaired successfully using json-repair library")
                    except json.JSONDecodeError:
                        pass

                # Level 3: If json-repair didn't work, try regex + json-repair
                if data is None:
                    cleaned = clean_json_string(json_str)
                    try:
                        data = json.loads(cleaned)
                        parse_method = "regex-clean"
                        logger.debug("JSON parsed after regex cleaning")
                    except json.JSONDecodeError:
                        # Last resort: json-repair on regex-cleaned string
                        repaired2, _ = _repair_json_with_library(cleaned)
                        try:
                            data = json.loads(repaired2)
                            parse_method = "regex+json-repair"
                            logger.debug("JSON repaired using regex + json-repair")
                        except json.JSONDecodeError as e:
                            # All methods failed, raise with details
                            preview = json_str[:300].replace("\n", "\\n")
                            raise ParseError(
                                f"All JSON repair methods failed. Error: {e}. Preview: {preview}"
                            ) from e

            if parse_method != "direct":
                logger.info(f"Pass {pass_number} JSON parsed using method: {parse_method}")

            # Parse confidence FIRST (so we can use global confidence as default for extractions)
            confidence = self._parse_confidence(data.get("confidence", {}))

            # Parse extractions (passing global confidence as default for per-extraction confidence)
            extractions = self._parse_extractions(
                data.get("extractions", []), default_confidence=confidence.overall
            )

            # Get entities discovered
            entities = set(data.get("entities_discovered", []))

            # Get changes made
            changes = data.get("changes_made", [])

            # Get reasoning
            reasoning = data.get("reasoning", "")

            # Get thinking (for Opus Pass 5)
            thinking = data.get("thinking", "")

            return PassResult(
                pass_number=pass_number,
                pass_type=pass_type,
                model_used=model_tier.value,
                model_id=model_id,
                extractions=extractions,
                action=data.get("action", "rien"),
                confidence=confidence,
                entities_discovered=entities,
                changes_made=changes,
                reasoning=reasoning,
                tokens_used=usage.get("total_tokens", 0),
                duration_ms=duration_ms,
                thinking=thinking,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in Pass {pass_number}: {e}\nResponse: {response[:500]}")
            raise ParseError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            logger.error(f"Parse error in Pass {pass_number}: {e}", exc_info=True)
            raise ParseError(f"Failed to parse response: {e}") from e

    def _extract_json(self, response: str) -> str:
        """
        Extract JSON object from response text.

        Uses multiple strategies to find valid JSON:
        1. Look for ```json code blocks
        2. Look for ``` code blocks
        3. Find first { and last }
        4. Handle edge cases (empty response, text-only response)

        Args:
            response: Raw response text

        Returns:
            Extracted JSON string

        Raises:
            ParseError: If no valid JSON found
        """
        if not response or not response.strip():
            raise ParseError("Empty response from AI")

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                extracted = response[start:end].strip()
                if extracted:
                    return extracted

        if "```" in response:
            start = response.find("```") + 3
            # Skip language identifier if present (e.g., ```javascript)
            newline_pos = response.find("\n", start)
            if newline_pos != -1 and newline_pos < start + 20:
                start = newline_pos + 1
            end = response.find("```", start)
            if end > start:
                extracted = response[start:end].strip()
                if extracted and "{" in extracted:
                    return extracted

        # Find first { and last }
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start == -1 or json_end <= json_start:
            # Last resort: check if the response is just text without JSON
            # Log the actual response for debugging
            preview = response[:200].replace("\n", "\\n")
            logger.warning(f"No JSON braces found in response. Preview: {preview}...")
            raise ParseError(
                f"No JSON object found in response. Response starts with: {response[:100]}"
            )

        return response[json_start:json_end]

    def _parse_extractions(
        self, extractions_data: list, default_confidence: float = 0.8
    ) -> list[Extraction]:
        """
        Parse extractions list from JSON data.

        Args:
            extractions_data: List of extraction dicts from JSON
            default_confidence: Default confidence to use if not specified per-extraction
                               (typically the global analysis confidence)

        Returns:
            List of validated Extraction objects
        """
        extractions = []

        for ext_data in extractions_data:
            try:
                # Validate required fields (handle None values)
                info = (ext_data.get("info") or "").strip()
                if not info:
                    logger.warning("Skipping extraction with empty info")
                    continue

                # CRITICAL: Reject extractions targeting the owner "Johan"
                # Johan Le Bail is the system owner - his name appears everywhere but should never be a target
                note_cible = (ext_data.get("note_cible") or "").strip()
                if note_cible:
                    note_cible_lower = note_cible.lower()
                    if note_cible_lower in ("johan", "johan le bail", "johan l.", "johanlb"):
                        logger.warning(
                            f"Rejecting extraction targeting owner 'Johan': {info} -> {note_cible}"
                        )
                        continue

                # Determine if this extraction should be required based on type/importance
                # if not explicitly set
                ext_type = ext_data.get("type", "fait")
                importance = ext_data.get("importance", "moyenne")
                explicit_required = ext_data.get("required")

                # Auto-determine required if not explicitly set
                if explicit_required is None:
                    required = self._should_be_required(ext_type, importance)
                else:
                    required = bool(explicit_required)

                # Get confidence for this extraction (4 dimensions or single score)
                ext_confidence_data = ext_data.get("confidence")
                if ext_confidence_data is None:
                    # Use global confidence as default
                    ext_confidence = ExtractionConfidence.from_single_score(default_confidence)
                elif isinstance(ext_confidence_data, dict):
                    # New format: 4 dimensions
                    ext_confidence = ExtractionConfidence.from_dict(ext_confidence_data)
                elif isinstance(ext_confidence_data, (int, float)):
                    # Backwards compatibility: single score
                    ext_confidence = ExtractionConfidence.from_single_score(
                        float(ext_confidence_data)
                    )
                else:
                    ext_confidence = ExtractionConfidence.from_single_score(default_confidence)

                # Check for past dates (> 90 days ago)
                ext_date = ext_data.get("date")
                has_obsolete_date = False
                if ext_date:
                    has_obsolete_date = self._is_date_obsolete(ext_date)
                    if has_obsolete_date:
                        # Don't mark as required if date is obsolete
                        required = False
                        # Set very low confidence to signal "not actionable"
                        ext_confidence = ExtractionConfidence(
                            quality=0.0, target_match=0.0, relevance=0.0, completeness=0.0
                        )
                        logger.debug(
                            f"Extraction with obsolete date ({ext_date}): not required, confidence=0"
                        )

                extraction = Extraction(
                    info=info,
                    type=ext_type,
                    importance=importance,
                    note_cible=ext_data.get("note_cible"),
                    note_action=ext_data.get("note_action", "enrichir"),
                    omnifocus=bool(ext_data.get("omnifocus", False)),
                    calendar=bool(ext_data.get("calendar", False)),
                    date=ext_date,
                    time=ext_data.get("time"),
                    timezone=ext_data.get("timezone"),
                    duration=ext_data.get("duration"),
                    required=required,
                    confidence=ext_confidence,
                    generic_title=bool(ext_data.get("generic_title", False)),
                )
                extractions.append(extraction)

            except Exception as e:
                logger.warning(f"Failed to parse extraction: {e}")
                continue

        return extractions

    def _parse_confidence(self, confidence_data: dict) -> DecomposedConfidence:
        """
        Parse confidence data into DecomposedConfidence.

        Args:
            confidence_data: Dict with confidence scores

        Returns:
            DecomposedConfidence object
        """
        # Handle both old (single score) and new (decomposed) formats
        if isinstance(confidence_data, (int, float)):
            return DecomposedConfidence.from_single_score(float(confidence_data))

        return DecomposedConfidence(
            entity_confidence=float(confidence_data.get("entity_confidence", 0.5)),
            action_confidence=float(confidence_data.get("action_confidence", 0.5)),
            extraction_confidence=float(confidence_data.get("extraction_confidence", 0.5)),
            completeness=float(confidence_data.get("completeness", 0.5)),
        )

    def _should_be_required(self, ext_type: str, importance: str) -> bool:
        """
        Determine if an extraction should be marked as required.

        An extraction is required if losing it would mean losing important
        information when archiving/deleting the email.

        Logic based on type and importance:
        - All deadlines are ALWAYS required (any importance)
        - High importance: decision, engagement, demande, montant, fait, evenement
        - Medium importance: engagement, demande (typically have implicit deadlines)

        Args:
            ext_type: Type of extraction (deadline, engagement, decision, etc.)
            importance: Importance level (haute, moyenne, basse)

        Returns:
            True if extraction should be required for safe archiving
        """
        ext_type = ext_type.lower()
        importance = importance.lower()

        # Deadlines are ALWAYS required regardless of importance
        if ext_type == "deadline":
            return True

        # High importance extractions
        if importance == "haute":
            return ext_type in {
                "decision",
                "engagement",
                "demande",
                "montant",
                "fait",
                "evenement",
            }

        # Medium importance - only engagements and demandes
        # (they typically imply follow-up actions)
        if importance == "moyenne":
            return ext_type in {"engagement", "demande"}

        # Low importance extractions are optional
        return False

    def _is_date_obsolete(self, date_str: str, days_threshold: int = 90) -> bool:
        """
        Check if a date is obsolete (more than N days in the past).

        Args:
            date_str: Date string in YYYY-MM-DD format
            days_threshold: Number of days after which a date is considered obsolete

        Returns:
            True if the date is more than days_threshold days in the past
        """
        from datetime import datetime, timedelta

        if not date_str:
            return False

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            threshold_date = datetime.now().date() - timedelta(days=days_threshold)
            return date_obj < threshold_date
        except ValueError:
            # If we can't parse the date, don't mark as obsolete
            logger.warning(f"Could not parse date: {date_str}")
            return False

    def _calculate_event_age_days(self, event: PerceivedEvent) -> int:
        """
        Calculate the age of an event in days.

        Uses occurred_at (original event date) if available,
        otherwise falls back to received_at.

        Args:
            event: The event to check

        Returns:
            Age in days (0 if event is from today)
        """
        now = datetime.now(timezone.utc)
        event_date = getattr(event, "occurred_at", None) or event.received_at
        age = now - event_date
        return max(0, age.days)

    def _is_ephemeral_content(
        self,
        extractions: list[Extraction],
        event: PerceivedEvent,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if email contains ephemeral content with no lasting value.

        Detects:
        1. Event invitations with dates that have passed
        2. Time-limited offers that have expired
        3. Newsletters/digests (periodic content aggregations)

        NEVER marks as ephemeral:
        - Financial documents (bilans, rapports financiers, etc.)
        - Legal documents (contrats, factures, etc.)
        - Corporate documents (statuts, PV, etc.)

        Args:
            extractions: List of extractions from the email
            event: The event being analyzed (for email date context)

        Returns:
            Tuple of (is_ephemeral, reason)
        """
        # Get text for analysis
        # PerceivedEvent uses from_person (string), not sender object
        from_person = (getattr(event, "from_person", "") or "").lower()
        sender_email = (getattr(event.sender, "email", "") or "").lower() if event.sender else ""
        title = (getattr(event, "title", "") or "").lower()
        content = getattr(event, "content", "") or ""
        full_text = f"{title} {content}".lower()

        # FIRST: Check for protected document types (NEVER ephemeral)
        # Financial documents that must ALWAYS be archived
        financial_indicators = [
            "bilan",
            "bilan financier",
            "bilan annuel",
            "annual report",
            "financial statement",
            "financial report",
            "rapport financier",
            "comptes annuels",
            "états financiers",
            "compte de résultat",
            "résumé financier",
            "financial summary",
            "audit",
            "comptes",
            "rapport annuel",
            "yearly report",
            "fiscal year",
            "clôture comptable",
            "exercice comptable",
            "year end",
        ]

        # Legal/corporate documents that must ALWAYS be archived
        # NOTE: Avoid short words that could match common text (e.g., "accord" matches "according")
        legal_indicators = [
            "contrat",
            "contract",
            "facture",
            "invoice",
            "bon de commande",
            "purchase order",
            "devis signé",
            "procès-verbal",
            "pv de réunion",
            "procuration",
            "power of attorney",
            "statuts sociaux",
            "bylaws",
            "certificat",
            "certificate",
            "attestation officielle",
            "déclaration fiscale",
            "companies act",
            "accord commercial",
            "accord signé",
            "legal agreement",
            "avenant au contrat",
            "amendment",
            "résiliation",
            "termination notice",
            "licence commerciale",
            "business license",
            "permis de construire",
        ]

        # Check if this is a protected document type
        is_financial = any(ind in full_text for ind in financial_indicators)
        is_legal = any(ind in full_text for ind in legal_indicators)

        if is_financial or is_legal:
            # Find which indicator matched
            matched_ind = next(
                (ind for ind in financial_indicators + legal_indicators if ind in full_text),
                "unknown",
            )
            logger.info(
                f"Protected document detected (NOT ephemeral): matched='{matched_ind}' "
                f"in from='{from_person}'"
            )
            return False, None

        # Now proceed with ephemeral content detection
        newsletter_indicators = [
            "newsletter",
            "digest",
            "daily",
            "weekly",
            "monthly",
            "highlights",
            "roundup",
            "recap",
            "summary",
            "bulletin",
            "noreply",
            "no-reply",
            "mailer",
            "news@",
            "updates@",
            "medium",
            "substack",
            "mailchimp",
            "sendinblue",
        ]

        is_newsletter = any(ind in from_person or ind in title for ind in newsletter_indicators)

        logger.info(
            f"Ephemeral check: from_person='{from_person}', title='{title[:50]}', "
            f"is_newsletter={is_newsletter}"
        )

        if is_newsletter:
            logger.info(f"Detected newsletter/digest: from_person='{from_person}'")
            return True, "newsletter/digest (periodic content, no lasting value)"

        # Second check: OTP/verification codes (always ephemeral)
        otp_indicators = [
            "otp",
            "one-time password",
            "code de vérification",
            "verification code",
            "code d'authentification",
            "authentication code",
            "code de sécurité",
            "security code",
            "code de confirmation",
            "confirmation code",
            "code à usage unique",
            "single-use code",
            "2fa",
            "two-factor",
            "mot de passe temporaire",
            "temporary password",
            "code pin",
            "entrer le code",
            "enter the code",
            "saisissez le code",
            "pour vous authentifier",
            "to authenticate",
            "pour confirmer",
            "code suivant",
            "following code",
            "voici votre code",
        ]

        is_otp = any(ind in full_text or ind in sender_email for ind in otp_indicators)

        if is_otp:
            return True, "OTP/verification code (expired, no lasting value)"

        # Third check: Does email contain past events/invitations?
        import re

        from dateutil import parser as date_parser

        now = datetime.now(timezone.utc)
        event_date = getattr(event, "occurred_at", None) or getattr(event, "received_at", now)

        # Types that indicate time-bound content
        time_bound_types = {"evenement", "deadline", "fait"}

        # Look for dates in extractions
        dates_found = []
        has_time_bound_content = False

        for ext in extractions:
            # Check if extraction type suggests time-bound content
            if ext.type in time_bound_types:
                has_time_bound_content = True

            # Try to extract dates from the extraction info
            info = ext.info or ""

            # Common date patterns in French/English
            # Examples: "30 septembre", "31 mars 2022", "September 30", "2021-09-30"
            date_patterns = [
                r"\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*\d{0,4}",
                r"\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{0,4}",
                r"\d{1,2}/\d{1,2}/\d{2,4}",
                r"\d{4}-\d{2}-\d{2}",
                r"jusqu'au\s+\d{1,2}\s+\w+\s*\d{0,4}",
                r"until\s+\d{1,2}\s+\w+\s*\d{0,4}",
            ]

            for pattern in date_patterns:
                matches = re.findall(pattern, info.lower())
                for match in matches:
                    try:
                        # Try to parse the date
                        # Add year from email if not present
                        date_str = match
                        if not re.search(r"\d{4}", date_str):
                            # Add year from email date
                            date_str = f"{date_str} {event_date.year}"

                        parsed = date_parser.parse(date_str, fuzzy=True, dayfirst=True)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        dates_found.append(parsed)
                    except (ValueError, TypeError):
                        pass

            # Also check the extraction's explicit date field
            if ext.date:
                try:
                    parsed = date_parser.parse(ext.date, fuzzy=True)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    dates_found.append(parsed)
                except (ValueError, TypeError):
                    pass

        # If we found time-bound content and dates, check if all dates are past
        if has_time_bound_content and dates_found:
            all_past = all(d < now for d in dates_found)
            if all_past:
                oldest = min(dates_found)
                days_ago = (now - oldest).days
                return (
                    True,
                    f"event/offer dated {oldest.strftime('%Y-%m-%d')} ({days_ago} days ago)",
                )

        # Also check the email content directly for event indicators
        # (full_text already set above for OTP check)

        # Event/invitation indicators
        event_indicators = [
            "vous invite",
            "invitation",
            "événement",
            "event",
            "rendez-vous",
            "rencontrer",
            "découvrir",
            "jeudi",
            "vendredi",
            "samedi",
            "dimanche",
            "lundi",
            "mardi",
            "mercredi",
            "à 17h",
            "à 18h",
            "à 19h",
            "à 20h",
            "offre valable",
            "jusqu'au",
            "expire",
            "limited time",
        ]

        has_event_indicator = any(ind in full_text for ind in event_indicators)

        if has_event_indicator and dates_found:
            all_past = all(d < now for d in dates_found)
            if all_past:
                oldest = min(dates_found)
                days_ago = (now - oldest).days
                return (
                    True,
                    f"invitation/offer dated {oldest.strftime('%Y-%m-%d')} ({days_ago} days ago)",
                )

        return False, None

    def _apply_age_adjustments(
        self,
        action: str,
        extractions: list[Extraction],
        age_days: int,
        event: PerceivedEvent,
    ) -> tuple[str, list[Extraction], Optional[str]]:
        """
        Apply age-based adjustments to action and extractions.

        Rules:
        - Emails > 90 days with flag/queue: downgrade to archive/delete
        - Promotional emails > 90 days without extractions: delete
        - Emails > 365 days: Remove OmniFocus tasks (too old for follow-up)
        - Note enrichments are always kept (historical value)

        Args:
            action: Proposed action
            extractions: Proposed extractions
            age_days: Event age in days
            event: The event being analyzed (for sender detection)

        Returns:
            Tuple of (adjusted_action, adjusted_extractions, adjustment_reason)
        """
        adjustment_reason = None
        adjusted_action = action
        adjusted_extractions = extractions

        # Check for valuable extractions (note enrichments, not just OmniFocus tasks)
        has_valuable_extractions = any(ext.note_cible and not ext.omnifocus for ext in extractions)

        # Rule 1: Downgrade "flag" or "queue" for old emails
        # - Both require active follow-up which is inappropriate for old emails
        # - If has valuable extractions → archive (historical value)
        # - If no extractions → delete (truly obsolete, no point keeping)
        if age_days > OLD_EMAIL_THRESHOLD_DAYS and action in ("flag", "queue"):
            if has_valuable_extractions:
                adjusted_action = "archive"
                adjustment_reason = (
                    f"Action downgraded from '{action}' to 'archive' "
                    f"(email is {age_days} days old, but has historical value)"
                )
            else:
                adjusted_action = "delete"
                adjustment_reason = (
                    f"Action downgraded from '{action}' to 'delete' "
                    f"(email is {age_days} days old, no valuable extractions)"
                )
            logger.info(adjustment_reason)

        # Rule 2: Delete emails with ephemeral content (past events, newsletters)
        # - Event invitations with dates in the past
        # - Newsletters/digests (periodic content with no lasting value)
        # - Time-limited offers that have expired
        is_ephemeral, ephemeral_reason = self._is_ephemeral_content(adjusted_extractions, event)
        if age_days > OLD_EMAIL_THRESHOLD_DAYS and adjusted_action == "archive" and is_ephemeral:
            adjusted_action = "delete"
            # Clear extractions since ephemeral content has no lasting value
            adjusted_extractions = []
            adjustment_reason = (
                f"Ephemeral content upgraded to 'delete' "
                f"(email is {age_days} days old, {ephemeral_reason})"
            )
            logger.info(adjustment_reason)

        # Rule 3: Remove OmniFocus tasks for very old emails
        if age_days > VERY_OLD_EMAIL_THRESHOLD_DAYS:
            original_count = len(extractions)
            adjusted_extractions = []
            for ext in extractions:
                if ext.omnifocus:
                    logger.info(
                        f"Removing OmniFocus task for old email ({age_days} days): "
                        f"{ext.info[:50]}..."
                    )
                    # Keep the extraction but remove OmniFocus flag
                    adjusted_extractions.append(
                        Extraction(
                            info=ext.info,
                            type=ext.type,
                            importance=ext.importance,
                            note_cible=ext.note_cible,
                            note_action=ext.note_action,
                            omnifocus=False,  # Remove OmniFocus
                            calendar=ext.calendar,
                            date=ext.date,
                            time=ext.time,
                            timezone=ext.timezone,
                            duration=ext.duration,
                            required=ext.required,
                            confidence=ext.confidence,
                        )
                    )
                else:
                    adjusted_extractions.append(ext)

            if adjustment_reason:
                adjustment_reason += f"; OmniFocus tasks disabled for {original_count - len([e for e in adjusted_extractions if e.omnifocus])} extractions"
            elif original_count != len([e for e in adjusted_extractions if e.omnifocus]):
                adjustment_reason = (
                    f"OmniFocus tasks disabled (email is {age_days} days old, "
                    f"threshold: {VERY_OLD_EMAIL_THRESHOLD_DAYS})"
                )

        return adjusted_action, adjusted_extractions, adjustment_reason

    def _build_result(
        self,
        pass_history: list[PassResult],
        start_time: float,
        total_tokens: int,
        stop_reason: str,
        escalated: bool,
        analysis_context: AnalysisContext,
        event: PerceivedEvent,
    ) -> MultiPassResult:
        """
        Build the final MultiPassResult.

        Args:
            pass_history: All pass results
            start_time: Analysis start time
            total_tokens: Total tokens used
            stop_reason: Reason for stopping
            escalated: Whether model was escalated
            analysis_context: Analysis context
            event: Original event (for age-based adjustments)

        Returns:
            MultiPassResult
        """
        last_pass = pass_history[-1]
        total_duration = (time.time() - start_time) * 1000

        # Check for high-stakes
        high_stakes_detected = is_high_stakes(
            last_pass.extractions,
            analysis_context,
            self.config,
        )

        # Collect all entities
        all_entities: set[str] = set()
        for p in pass_history:
            all_entities.update(p.entities_discovered)

        # Apply age-based adjustments
        age_days = self._calculate_event_age_days(event)
        logger.info(f"Age-based check: age_days={age_days}, action={last_pass.action}")
        adjusted_action, adjusted_extractions, age_adjustment = self._apply_age_adjustments(
            last_pass.action,
            last_pass.extractions,
            age_days,
            event,
        )
        if age_adjustment:
            logger.info(f"Age adjustment applied: {age_adjustment}")

        # Run coherence pass on adjusted extractions
        # This validates note targets, detects duplicates, and suggests sections
        coherence_validated = False
        coherence_corrections = 0
        coherence_duplicates = 0
        coherence_confidence = 1.0
        coherence_warnings: list[dict] = []

        if adjusted_extractions:
            validated_extractions, coherence_result = self._run_coherence_pass(
                adjusted_extractions, event
            )
            if coherence_result is not None:
                adjusted_extractions = validated_extractions
                coherence_validated = True
                coherence_corrections = coherence_result.coherence_summary.corrected
                coherence_duplicates = coherence_result.coherence_summary.duplicates_detected
                coherence_confidence = coherence_result.coherence_confidence
                coherence_warnings = [
                    {"type": w.type, "index": w.extraction_index, "message": w.message}
                    for w in coherence_result.warnings
                ]
                total_tokens += coherence_result.tokens_used

        # Update stop reason if adjustments were made
        final_stop_reason = stop_reason
        if age_adjustment:
            final_stop_reason = f"{stop_reason}; {age_adjustment}"
        if coherence_validated and coherence_corrections > 0:
            final_stop_reason = (
                f"{final_stop_reason}; coherence_pass: {coherence_corrections} corrected"
            )

        return MultiPassResult(
            extractions=adjusted_extractions,
            action=adjusted_action,
            confidence=last_pass.confidence,
            entities_discovered=all_entities,
            passes_count=len(pass_history),
            total_duration_ms=total_duration,
            total_tokens=total_tokens,
            final_model=last_pass.model_used,
            escalated=escalated,
            pass_history=pass_history,
            stop_reason=final_stop_reason,
            high_stakes=high_stakes_detected or analysis_context.high_stakes,
            # Coherence validation metadata
            coherence_validated=coherence_validated,
            coherence_corrections=coherence_corrections,
            coherence_duplicates_detected=coherence_duplicates,
            coherence_confidence=coherence_confidence,
            coherence_warnings=coherence_warnings,
        )


# Factory function for convenience
def create_multi_pass_analyzer(
    ai_router: Optional[AIRouter] = None,
    context_searcher: Optional["ContextSearcher"] = None,
    config: Optional[MultiPassConfig] = None,
    note_manager: Optional["NoteManager"] = None,
    entity_searcher: Optional["EntitySearcher"] = None,
    enable_coherence_pass: bool = True,
) -> MultiPassAnalyzer:
    """
    Create a MultiPassAnalyzer with default or provided dependencies.

    Args:
        ai_router: AIRouter instance (creates default if None)
        context_searcher: ContextSearcher instance (optional)
        config: MultiPassConfig (uses defaults if None)
        note_manager: NoteManager for coherence validation (optional)
        entity_searcher: EntitySearcher for finding similar notes (optional)
        enable_coherence_pass: Whether to run coherence validation (default: True)

    Returns:
        Configured MultiPassAnalyzer instance
    """
    if ai_router is None:
        from src.core.config_manager import get_config

        app_config = get_config()
        ai_router = AIRouter(app_config.ai)

    return MultiPassAnalyzer(
        ai_router=ai_router,
        context_searcher=context_searcher,
        config=config,
        note_manager=note_manager,
        entity_searcher=entity_searcher,
        enable_coherence_pass=enable_coherence_pass,
    )
