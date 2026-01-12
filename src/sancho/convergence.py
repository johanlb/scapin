"""
Convergence Logic for Multi-Pass Analysis

Determines when to stop iterating and when to escalate to a more powerful model.
Part of Sancho's multi-pass extraction system (v2.2).

Key responsibilities:
- should_stop(): Determine if we should stop iterating
- select_model(): Choose the right model for the next pass
- is_high_stakes(): Detect critical decisions requiring extra care
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from src.monitoring.logger import get_logger
from src.sancho.model_selector import ModelTier

logger = get_logger("convergence")


class PassType(Enum):
    """Types of analysis passes"""

    BLIND_EXTRACTION = "blind"  # Pass 1: No context
    CONTEXTUAL_REFINEMENT = "refine"  # Pass 2-3: With context
    DEEP_REASONING = "deep"  # Pass 4: Sonnet
    EXPERT_ANALYSIS = "expert"  # Pass 5: Opus


@dataclass
class DecomposedConfidence:
    """
    Decomposed confidence scores by dimension.

    Instead of a single confidence score, we track confidence
    across multiple dimensions to enable targeted escalation.
    """

    entity_confidence: float  # Are people/projects well identified?
    action_confidence: float  # Is the suggested action correct?
    extraction_confidence: float  # Are all important facts captured?
    completeness: float  # Is nothing forgotten?

    # Optional dimensions (Sprint 8+)
    date_confidence: float | None = None
    amount_confidence: float | None = None

    @property
    def overall(self) -> float:
        """Global score = minimum of dimensions (conservative)"""
        scores = [
            self.entity_confidence,
            self.action_confidence,
            self.extraction_confidence,
            self.completeness,
        ]
        return min(scores)

    @property
    def weakest_dimension(self) -> tuple[str, float]:
        """Identify the weakest dimension"""
        dimensions = {
            "entity": self.entity_confidence,
            "action": self.action_confidence,
            "extraction": self.extraction_confidence,
            "completeness": self.completeness,
        }
        weakest = min(dimensions, key=lambda k: dimensions[k])
        return weakest, dimensions[weakest]

    def needs_improvement(self, threshold: float = 0.85) -> list[str]:
        """List dimensions below threshold"""
        weak = []
        if self.entity_confidence < threshold:
            weak.append("entity")
        if self.action_confidence < threshold:
            weak.append("action")
        if self.extraction_confidence < threshold:
            weak.append("extraction")
        if self.completeness < threshold:
            weak.append("completeness")
        return weak

    @classmethod
    def from_single_score(cls, score: float) -> "DecomposedConfidence":
        """Create from a single confidence score (backward compatibility)"""
        return cls(
            entity_confidence=score,
            action_confidence=score,
            extraction_confidence=score,
            completeness=score,
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "entity_confidence": self.entity_confidence,
            "action_confidence": self.action_confidence,
            "extraction_confidence": self.extraction_confidence,
            "completeness": self.completeness,
            "overall": self.overall,
        }
        if self.date_confidence is not None:
            result["date_confidence"] = self.date_confidence
        if self.amount_confidence is not None:
            result["amount_confidence"] = self.amount_confidence
        return result


@dataclass
class Extraction:
    """A single extracted piece of information"""

    info: str
    type: str  # fait, decision, engagement, deadline, etc.
    importance: str  # haute, moyenne, basse
    note_cible: str | None = None
    note_action: str = "enrichir"  # enrichir, creer
    omnifocus: bool = False
    calendar: bool = False
    date: str | None = None
    time: str | None = None
    timezone: str | None = None
    duration: int | None = None
    # New fields for atomic transaction logic
    required: bool = False  # If True, this extraction MUST be executed for safe archiving
    confidence: float = 0.8  # Confidence in this specific extraction (0.0-1.0)

    def is_actionable(self) -> bool:
        """Check if this extraction leads to an action (note, task, calendar)"""
        return bool(self.note_cible or self.omnifocus or self.calendar)


@dataclass
class PassResult:
    """Result of a single analysis pass"""

    pass_number: int
    pass_type: PassType
    model_used: str  # haiku, sonnet, opus
    model_id: str  # Full model ID
    extractions: list[Extraction]
    action: str  # archive, flag, queue, delete, rien
    confidence: DecomposedConfidence
    entities_discovered: set[str] = field(default_factory=set)
    changes_made: list[str] = field(default_factory=list)
    reasoning: str = ""
    tokens_used: int = 0
    duration_ms: float = 0.0

    # For Chain-of-Thought (Sprint 8)
    thinking: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "pass_number": self.pass_number,
            "pass_type": self.pass_type.value,
            "model_used": self.model_used,
            "model_id": self.model_id,
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
            "changes_made": self.changes_made,
            "reasoning": self.reasoning,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AnalysisContext:
    """Context information for analysis decisions"""

    sender_importance: str = "normal"  # normal, important, vip
    has_conflicting_info: bool = False
    high_stakes: bool = False
    is_thread: bool = False
    has_attachments: bool = False


@dataclass
class MultiPassConfig:
    """Configuration for multi-pass analysis"""

    # Confidence thresholds
    confidence_stop_threshold: float = 0.95  # Stop if reached
    confidence_acceptable: float = 0.90  # Acceptable for application
    confidence_escalate_sonnet: float = 0.80  # Escalate to Sonnet
    confidence_escalate_opus: float = 0.75  # Escalate to Opus
    confidence_minimum: float = 0.85  # Minimum for auto-application

    # Limits
    max_passes: int = 5
    max_context_notes: int = 5
    max_calendar_events: int = 10
    max_email_history: int = 5
    max_content_chars: int = 8000  # Max content chars for template rendering

    # Optimizations
    skip_context_for_simple: bool = True  # Skip if newsletter/spam
    skip_pass2_if_confident: bool = True  # Skip if Pass 1 > 95%

    # High-stakes thresholds
    high_stakes_amount_threshold: float = 10000  # EUR
    high_stakes_deadline_days: int = 2  # days

    # Costs (for monitoring, in USD per 1k tokens)
    cost_haiku_per_1k: float = 0.00025
    cost_sonnet_per_1k: float = 0.003
    cost_opus_per_1k: float = 0.015


# Status messages for UI (see UI_VOCABULARY.md)
PASS_STATUS_MESSAGES = {
    1: "Sancho jette un coup d'œil au contenu...",
    2: "Sancho investigue...",
    3: "Sancho enquête de manière approfondie...",
    4: "Sancho consulte ses sources...",
    5: "Sancho délibère sur cette affaire...",
}

PASS_UI_NAMES = {
    1: "Coup d'œil",
    2: "Investigation",
    3: "Enquête approfondie",
    4: "Consultation",
    5: "Délibération",
}


def should_stop(
    current: PassResult,
    previous: PassResult | None,
    config: MultiPassConfig,
) -> tuple[bool, str]:
    """
    Determine if we should stop iterating.

    Returns:
        Tuple of (should_stop, reason)
    """
    confidence = current.confidence.overall

    # Criterion 1: Sufficient confidence
    if confidence >= config.confidence_stop_threshold:
        logger.debug(f"Pass {current.pass_number}: Stopping - confidence {confidence:.2f} >= {config.confidence_stop_threshold}")
        return True, "confidence_sufficient"

    # Criterion 2: Convergence (no changes)
    if previous and len(current.changes_made) == 0:
        logger.debug(f"Pass {current.pass_number}: Stopping - no changes made")
        return True, "no_changes"

    # Criterion 3: No new entities to explore
    if (
        previous
        and current.entities_discovered == previous.entities_discovered
        and confidence >= config.confidence_acceptable
    ):
        logger.debug(f"Pass {current.pass_number}: Stopping - no new entities, confidence acceptable")
        return True, "no_new_entities"

    # Criterion 4: Max passes reached
    if current.pass_number >= config.max_passes:
        logger.debug(f"Pass {current.pass_number}: Stopping - max passes reached")
        return True, "max_passes"

    # Criterion 5: Simple action and acceptable confidence
    # BUT only if no required extractions have low confidence
    if current.action in ["archive", "rien"] and confidence >= config.confidence_minimum:
        global_conf = calculate_global_confidence(current)
        if global_conf >= config.confidence_minimum:
            logger.debug(f"Pass {current.pass_number}: Stopping - simple action with acceptable global confidence ({global_conf:.2f})")
            return True, "simple_action"
        else:
            logger.debug(f"Pass {current.pass_number}: Continuing - required extractions have low confidence ({global_conf:.2f})")

    return False, ""


def calculate_global_confidence(result: PassResult) -> float:
    """
    Calculate global confidence considering required extractions.

    The global confidence is the MINIMUM of:
    - The action confidence (overall)
    - The confidence of any REQUIRED extractions (that have confidence >= 10%)

    Extractions with confidence < 10% are considered "rejections" by the AI
    (the AI is saying "don't do this") and are excluded from the calculation.
    They should NOT pull down the global confidence or trigger escalation.

    This ensures we don't archive an email if we're not confident
    about capturing the important information it contains.

    Args:
        result: The pass result containing action and extractions

    Returns:
        Global confidence score (0.0-1.0)
    """
    # Threshold below which we consider the AI is saying "no" rather than "unsure"
    REJECTION_THRESHOLD = 0.20

    action_confidence = result.confidence.overall

    # Get required extractions that lead to actions AND have meaningful confidence
    # Extractions with confidence < 10% are "rejections", not "uncertainties"
    required_extractions = [
        e for e in result.extractions
        if e.required and e.is_actionable() and e.confidence >= REJECTION_THRESHOLD
    ]

    if not required_extractions:
        # No required extractions with meaningful confidence, use action confidence
        return action_confidence

    # Global confidence = min(action, all required extractions)
    extraction_confidences = [e.confidence for e in required_extractions]
    min_extraction_conf = min(extraction_confidences)

    global_conf = min(action_confidence, min_extraction_conf)

    # Count rejected extractions for logging
    rejected_count = len([
        e for e in result.extractions
        if e.required and e.is_actionable() and e.confidence < REJECTION_THRESHOLD
    ])

    logger.debug(
        f"Global confidence: {global_conf:.2f} "
        f"(action={action_confidence:.2f}, "
        f"required_extractions={len(required_extractions)}, "
        f"rejected_extractions={rejected_count}, "
        f"min_extraction={min_extraction_conf:.2f})"
    )

    return global_conf


def get_required_extractions(result: PassResult, exclude_rejections: bool = True) -> list[Extraction]:
    """
    Get all required extractions that lead to actions.

    Args:
        result: The pass result containing extractions
        exclude_rejections: If True, exclude extractions with confidence < 10%
                           (these are "rejections" by the AI, not uncertainties)

    Returns:
        List of required, actionable extractions
    """
    REJECTION_THRESHOLD = 0.20

    extractions = [e for e in result.extractions if e.required and e.is_actionable()]

    if exclude_rejections:
        extractions = [e for e in extractions if e.confidence >= REJECTION_THRESHOLD]

    return extractions


def should_downgrade_action(result: PassResult, config: MultiPassConfig) -> tuple[bool, str]:
    """
    Check if action should be downgraded due to low extraction confidence.

    If we want to archive but have required extractions with low confidence,
    we should flag for review instead of archiving.

    Returns:
        Tuple of (should_downgrade, new_action)
    """
    if result.action not in ["archive", "delete", "rien"]:
        return False, result.action

    required = get_required_extractions(result)
    if not required:
        return False, result.action

    min_conf = min(e.confidence for e in required)

    # If any required extraction has low confidence, flag for review
    if min_conf < config.confidence_minimum:
        logger.info(
            f"Downgrading action from '{result.action}' to 'flag' - "
            f"required extraction confidence too low ({min_conf:.2f})"
        )
        return True, "flag"

    return False, result.action


def select_model(
    pass_number: int,
    confidence: float,
    context: AnalysisContext,
    config: MultiPassConfig,
) -> tuple[ModelTier, str]:
    """
    Select the model for the next pass.

    Args:
        pass_number: The pass number (1-5)
        confidence: Current confidence score
        context: Analysis context with metadata
        config: Multi-pass configuration

    Returns:
        Tuple of (ModelTier, reason)
    """
    # Pass 1-3: Always Haiku (economical, sufficient with context)
    if pass_number <= 3:
        return ModelTier.HAIKU, "default"

    # Pass 4: Sonnet if Haiku hasn't converged
    if pass_number == 4:
        if confidence < config.confidence_escalate_sonnet:
            logger.info(f"Pass 4: Escalating to Sonnet (confidence {confidence:.2f} < {config.confidence_escalate_sonnet})")
            return ModelTier.SONNET, "low_confidence"
        # One more chance with Haiku if close
        if confidence < config.confidence_acceptable:
            return ModelTier.HAIKU, "retry"
        return ModelTier.HAIKU, "confident"

    # Pass 5: Opus for difficult cases
    if pass_number == 5:
        # Always Opus if we get here
        if confidence < config.confidence_escalate_opus:
            logger.info(f"Pass 5: Escalating to Opus (confidence {confidence:.2f} < {config.confidence_escalate_opus})")
            return ModelTier.OPUS, "very_low_confidence"
        if context.has_conflicting_info:
            logger.info("Pass 5: Escalating to Opus (conflicting info)")
            return ModelTier.OPUS, "conflict_resolution"
        if context.high_stakes:
            logger.info("Pass 5: Escalating to Opus (high stakes)")
            return ModelTier.OPUS, "high_stakes"
        return ModelTier.SONNET, "fallback"

    # Safety fallback
    return ModelTier.OPUS, "max_passes"


def is_high_stakes(
    extractions: list[Extraction],
    context: AnalysisContext,
    config: MultiPassConfig,
) -> bool:
    """
    Determine if an extraction is high-stakes.

    High-stakes decisions require extra care (cross-verification in Sprint 8).
    """
    for extraction in extractions:
        # Important financial amount
        if extraction.type == "montant":
            amount = _parse_amount(extraction.info)
            if amount and amount > config.high_stakes_amount_threshold:
                logger.debug(f"High-stakes: amount {amount} > {config.high_stakes_amount_threshold}")
                return True

        # Critical deadline (< 48h)
        if extraction.type in ["deadline", "engagement"] and extraction.date:
            days_until = _days_until(extraction.date)
            if days_until is not None and days_until <= config.high_stakes_deadline_days:
                logger.debug(f"High-stakes: deadline in {days_until} days")
                return True

        # Strategic decision
        if extraction.type == "decision" and extraction.importance == "haute":
            logger.debug("High-stakes: high importance decision")
            return True

    # VIP sender
    if context.sender_importance == "vip":
        logger.debug("High-stakes: VIP sender")
        return True

    return False


def get_pass_type(pass_number: int) -> PassType:
    """Get the pass type for a given pass number"""
    if pass_number == 1:
        return PassType.BLIND_EXTRACTION
    elif pass_number <= 3:
        return PassType.CONTEXTUAL_REFINEMENT
    elif pass_number == 4:
        return PassType.DEEP_REASONING
    else:
        return PassType.EXPERT_ANALYSIS


def get_status_message(pass_number: int) -> str:
    """Get the UI status message for a pass"""
    return PASS_STATUS_MESSAGES.get(pass_number, "Sancho analyse...")


def get_pass_ui_name(pass_number: int) -> str:
    """Get the UI name for a pass"""
    return PASS_UI_NAMES.get(pass_number, f"Pass {pass_number}")


def targeted_escalation(confidence: DecomposedConfidence) -> dict[str, dict]:
    """
    Targeted escalation strategy based on weak dimensions.

    Returns a dictionary of strategies for each weak dimension.
    """
    weak_dims = confidence.needs_improvement(threshold=0.85)
    strategies: dict[str, dict] = {}

    if "entity" in weak_dims:
        strategies["entity"] = {
            "action": "search_more_context",
            "sources": ["notes_pkm", "email_history"],
            "prompt_focus": "Clarifier identité des personnes mentionnées",
        }

    if "action" in weak_dims:
        strategies["action"] = {
            "action": "analyze_intent",
            "sources": ["sender_history", "thread_context"],
            "prompt_focus": "Déterminer l'action attendue",
        }

    if "extraction" in weak_dims:
        strategies["extraction"] = {
            "action": "reread_careful",
            "sources": ["full_email"],
            "prompt_focus": "Relire attentivement pour extraire tous les faits",
        }

    if "completeness" in weak_dims:
        strategies["completeness"] = {
            "action": "reread_full",
            "sources": ["attachments", "full_thread"],
            "prompt_focus": "Vérifier rien n'a été oublié",
        }

    return strategies


def _parse_amount(text: str) -> float | None:
    """Parse an amount from text (e.g., '15 000 €' -> 15000.0)"""
    import re

    # Remove currency symbols and spaces
    cleaned = re.sub(r"[€$£\s]", "", text)
    # Handle French decimal separator
    cleaned = cleaned.replace(",", ".")
    # Remove thousand separators
    cleaned = re.sub(r"\.(?=\d{3})", "", cleaned)

    try:
        return float(cleaned)
    except ValueError:
        return None


def _days_until(date_str: str) -> int | None:
    """Calculate days until a date string (YYYY-MM-DD format)"""
    from datetime import datetime

    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (target - date.today()).days
    except ValueError:
        return None
