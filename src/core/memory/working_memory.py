"""
Working Memory

Central hub for short-term understanding and reasoning state.

Working Memory holds:
- Current event being processed
- Retrieved context from PKM
- Reasoning trace (all passes)
- Hypotheses and inferences
- Confidence scores
- Open questions/uncertainties
- Conversation history (if continuous)

Architecture: Central component that all other systems read/write to
Design Philosophy: Single source of truth for current cognitive state
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from src.core.events import PerceivedEvent
from src.utils import now_utc


class MemoryState(str, Enum):
    """Working memory lifecycle states"""
    INITIALIZED = "initialized"      # Just created
    PERCEIVING = "perceiving"        # Processing perception
    REASONING = "reasoning"          # In reasoning loop
    PLANNING = "planning"            # Generating action plan
    EXECUTING = "executing"          # Executing actions
    COMPLETE = "complete"            # Processing finished
    ARCHIVED = "archived"            # Moved to long-term memory


@dataclass
class Hypothesis:
    """
    A hypothesis about the event and appropriate response

    The reasoning engine generates and refines hypotheses through
    multiple passes until confidence threshold is met.
    """
    id: str  # Unique hypothesis ID
    description: str  # What we think is true/should happen
    confidence: float  # 0.0-1.0
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate hypothesis"""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    def add_evidence(self, evidence: str, supporting: bool = True) -> None:
        """Add evidence for or against this hypothesis"""
        if supporting:
            self.supporting_evidence.append(evidence)
        else:
            self.contradicting_evidence.append(evidence)
        self.updated_at = now_utc()

    def update_confidence(self, new_confidence: float) -> None:
        """Update confidence score"""
        if not (0.0 <= new_confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {new_confidence}")
        self.confidence = new_confidence
        self.updated_at = now_utc()


@dataclass
class ReasoningPass:
    """
    Record of a single reasoning pass

    Each pass through the reasoning loop is recorded for explainability
    and debugging.
    """
    pass_number: int  # 1, 2, 3, 4, 5
    pass_type: str  # initial_analysis, context_enrichment, deep_reasoning, etc.
    started_at: datetime = field(default_factory=now_utc)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Input state
    input_confidence: float = 0.0
    input_hypotheses_count: int = 0

    # Actions taken
    context_queries: List[str] = field(default_factory=list)
    context_retrieved: List[str] = field(default_factory=list)
    ai_prompts: List[str] = field(default_factory=list)
    ai_responses: List[str] = field(default_factory=list)

    # Output state
    output_confidence: float = 0.0
    output_hypotheses_count: int = 0
    confidence_delta: float = 0.0

    # Insights gained
    insights: List[str] = field(default_factory=list)
    questions_raised: List[str] = field(default_factory=list)
    entities_extracted: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self) -> None:
        """Mark pass as complete and calculate duration"""
        self.completed_at = now_utc()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()
        self.confidence_delta = self.output_confidence - self.input_confidence


@dataclass
class ContextItem:
    """
    A piece of context retrieved from PKM or elsewhere

    Context informs reasoning by providing relevant background information.
    """
    source: str  # Where this came from (pkm, memory, web, etc.)
    type: str  # note, entity, relationship, conversation, etc.
    content: str  # The actual context
    relevance_score: float  # 0.0-1.0
    retrieved_at: datetime = field(default_factory=now_utc)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """
    Working Memory - Central hub for cognitive processing

    This is the "blackboard" where all cognitive components read and write.
    Maintains current understanding, reasoning state, and decision context.

    Thread-Safety: NOT thread-safe by design (single event at a time)
    Persistence: Transient (cleared after event processing)
    """

    def __init__(self, event: PerceivedEvent):
        """
        Initialize working memory for an event

        Args:
            event: The perceived event to process
        """
        # Core State
        self.event = event
        self.state = MemoryState.INITIALIZED
        self.created_at = now_utc()
        self.updated_at = now_utc()

        # Reasoning State
        self.hypotheses: Dict[str, Hypothesis] = {}  # hypothesis_id -> Hypothesis
        self.current_best_hypothesis: Optional[Hypothesis] = None
        self.overall_confidence: float = event.perception_confidence

        # Reasoning History
        self.reasoning_passes: List[ReasoningPass] = []
        self.current_pass: Optional[ReasoningPass] = None

        # Retrieved Context
        self.context_items: List[ContextItem] = []
        self.related_events: List[str] = []  # Event IDs

        # Open Questions
        self.open_questions: List[str] = []
        self.uncertainties: List[str] = []

        # Continuity (if part of conversation/thread)
        self.is_continuous: bool = False
        self.conversation_id: Optional[str] = None
        self.previous_events: List[PerceivedEvent] = []

        # Metadata
        self.metadata: Dict[str, Any] = {}

    def add_hypothesis(self, hypothesis: Hypothesis, replace: bool = False) -> None:
        """
        Add or update a hypothesis

        Args:
            hypothesis: Hypothesis to add
            replace: If True, replace existing hypothesis with same ID.
                     If False, raise error on duplicate ID.

        Raises:
            TypeError: If hypothesis is not a Hypothesis instance
            ValueError: If hypothesis with same ID already exists and replace=False
        """
        if not isinstance(hypothesis, Hypothesis):
            raise TypeError(f"Expected Hypothesis, got {type(hypothesis)}")

        if not replace and hypothesis.id in self.hypotheses:
            raise ValueError(
                f"Hypothesis with ID '{hypothesis.id}' already exists. "
                f"Use replace=True to overwrite."
            )

        self.hypotheses[hypothesis.id] = hypothesis
        self.updated_at = now_utc()

        # Update current best - recalculate from all hypotheses to be safe
        if self.hypotheses:
            self.current_best_hypothesis = max(
                self.hypotheses.values(),
                key=lambda h: h.confidence
            )

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get hypothesis by ID"""
        return self.hypotheses.get(hypothesis_id)

    def get_top_hypotheses(self, n: int = 3) -> List[Hypothesis]:
        """Get top N hypotheses by confidence"""
        sorted_hyps = sorted(
            self.hypotheses.values(),
            key=lambda h: h.confidence,
            reverse=True
        )
        return sorted_hyps[:n]

    def start_reasoning_pass(self, pass_number: int, pass_type: str) -> ReasoningPass:
        """
        Start a new reasoning pass

        Args:
            pass_number: Sequential pass number (1, 2, 3, ...)
            pass_type: Type of pass (initial_analysis, context_enrichment, etc.)

        Returns:
            ReasoningPass object for this pass

        Raises:
            ValueError: If state doesn't allow starting a new pass
        """
        # Validate state transition
        if self.state == MemoryState.COMPLETE:
            raise ValueError("Cannot start reasoning pass on completed memory")
        if self.state == MemoryState.ARCHIVED:
            raise ValueError("Cannot start reasoning pass on archived memory")
        if self.current_pass is not None:
            raise ValueError(
                f"Cannot start new pass while pass {self.current_pass.pass_number} is in progress"
            )

        pass_obj = ReasoningPass(
            pass_number=pass_number,
            pass_type=pass_type,
            input_confidence=self.overall_confidence,
            input_hypotheses_count=len(self.hypotheses)
        )
        self.current_pass = pass_obj
        self.state = MemoryState.REASONING
        self.updated_at = now_utc()
        return pass_obj

    def complete_reasoning_pass(self) -> None:
        """
        Complete current reasoning pass

        Raises:
            ValueError: If no pass is in progress or state is invalid
        """
        if self.current_pass is None:
            raise ValueError("No reasoning pass in progress")
        if self.state != MemoryState.REASONING:
            raise ValueError(f"Cannot complete pass in state {self.state}")

        self.current_pass.output_confidence = self.overall_confidence
        self.current_pass.output_hypotheses_count = len(self.hypotheses)
        self.current_pass.complete()
        self.reasoning_passes.append(self.current_pass)
        self.current_pass = None
        self.updated_at = now_utc()
        # State remains REASONING (could transition to planning, executing, etc.)

    def add_context(self, context: ContextItem) -> None:
        """Add retrieved context"""
        self.context_items.append(context)
        self.updated_at = now_utc()

    def add_context_simple(
        self,
        source: str,
        type: str,
        content: str,
        relevance: float = 1.0
    ) -> None:
        """
        Add context (simplified interface)

        Args:
            source: Where this context came from (pkm, web, memory, etc.)
            type: Type of context (note, entity, relationship, etc.)
            content: The actual context content
            relevance: Relevance score from 0.0 (not relevant) to 1.0 (highly relevant)

        Raises:
            ValueError: If relevance is not in range [0.0, 1.0]
        """
        if not (0.0 <= relevance <= 1.0):
            raise ValueError(f"relevance must be 0.0-1.0, got {relevance}")

        self.add_context(ContextItem(
            source=source,
            type=type,
            content=content,
            relevance_score=relevance
        ))

    def get_context_by_source(self, source: str) -> List[ContextItem]:
        """Get all context from a specific source"""
        return [c for c in self.context_items if c.source == source]

    def get_top_context(self, n: int = 5) -> List[ContextItem]:
        """Get top N most relevant context items"""
        sorted_context = sorted(
            self.context_items,
            key=lambda c: c.relevance_score,
            reverse=True
        )
        return sorted_context[:n]

    def add_question(self, question: str) -> None:
        """Add an open question that needs answering"""
        if question not in self.open_questions:
            self.open_questions.append(question)
            self.updated_at = now_utc()

    def add_uncertainty(self, uncertainty: str) -> None:
        """Add an uncertainty/ambiguity"""
        if uncertainty not in self.uncertainties:
            self.uncertainties.append(uncertainty)
            self.updated_at = now_utc()

    def update_confidence(self, new_confidence: float) -> None:
        """Update overall confidence"""
        if not (0.0 <= new_confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {new_confidence}")
        self.overall_confidence = new_confidence
        self.updated_at = now_utc()

    def is_confident(self, threshold: float = 0.95) -> bool:
        """Check if confidence meets threshold"""
        return self.overall_confidence >= threshold

    def needs_more_reasoning(self, threshold: float = 0.95, max_passes: int = 5) -> bool:
        """
        Check if more reasoning passes are needed

        Considers:
        - Overall confidence vs threshold
        - Number of passes vs max
        - Presence of open questions or uncertainties

        Returns False if:
        - Confidence >= threshold AND no open questions/uncertainties
        - Max passes reached

        Returns True if:
        - Confidence < threshold
        - OR open questions/uncertainties exist
        """
        # Stop if max passes reached (safety limit)
        if len(self.reasoning_passes) >= max_passes:
            return False

        # Continue if confidence is low
        if self.overall_confidence < threshold:
            return True

        # Continue if there are unresolved questions or uncertainties
        # Even with high confidence, open questions indicate incomplete reasoning
        if len(self.open_questions) > 0 or len(self.uncertainties) > 0:
            return True

        # High confidence and no open questions → reasoning complete
        return False

    def set_continuous(self, conversation_id: str, previous_events: List[PerceivedEvent]) -> None:
        """
        Mark this memory as part of a continuous conversation

        Args:
            conversation_id: Unique identifier for the conversation thread
            previous_events: List of previous events in the conversation

        Note: Creates a copy of previous_events list to prevent external modification.
        Since PerceivedEvent is immutable (frozen), the events themselves don't
        need deep copying.
        """
        if not conversation_id or not conversation_id.strip():
            raise ValueError("conversation_id cannot be empty")

        self.is_continuous = True
        self.conversation_id = conversation_id
        # Copy list to prevent external modification
        # Events themselves are immutable so shallow copy is sufficient
        self.previous_events = list(previous_events)
        self.updated_at = now_utc()

    def get_reasoning_summary(self) -> Dict[str, Any]:
        """Get summary of reasoning process"""
        return {
            "total_passes": len(self.reasoning_passes),
            "initial_confidence": self.event.perception_confidence,
            "final_confidence": self.overall_confidence,
            "confidence_gain": self.overall_confidence - self.event.perception_confidence,
            "total_duration_seconds": sum(
                p.duration_seconds for p in self.reasoning_passes if p.duration_seconds
            ),
            "hypotheses_considered": len(self.hypotheses),
            "context_items_retrieved": len(self.context_items),
            "open_questions": len(self.open_questions),
            "uncertainties": len(self.uncertainties),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event": self.event.to_dict(),
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "overall_confidence": self.overall_confidence,
            "hypotheses": [
                {
                    "id": h.id,
                    "description": h.description,
                    "confidence": h.confidence,
                    "supporting_evidence": h.supporting_evidence,
                    "contradicting_evidence": h.contradicting_evidence,
                }
                for h in self.hypotheses.values()
            ],
            "reasoning_passes": [
                {
                    "pass_number": p.pass_number,
                    "pass_type": p.pass_type,
                    "duration_seconds": p.duration_seconds,
                    "confidence_delta": p.confidence_delta,
                    "insights": p.insights,
                }
                for p in self.reasoning_passes
            ],
            "context_count": len(self.context_items),
            "open_questions": self.open_questions,
            "uncertainties": self.uncertainties,
            "is_continuous": self.is_continuous,
            "conversation_id": self.conversation_id,
            "reasoning_summary": self.get_reasoning_summary(),
        }

    def __str__(self) -> str:
        """Human-readable representation"""
        return (
            f"WorkingMemory(event={self.event.event_id[:8]}..., "
            f"state={self.state.value}, "
            f"confidence={self.overall_confidence:.0%}, "
            f"passes={len(self.reasoning_passes)}, "
            f"hypotheses={len(self.hypotheses)})"
        )
