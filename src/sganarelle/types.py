"""
Sganarelle Types

Dataclasses pour learning engine et composants associés.
Tous les types sont immutables (frozen=True) pour thread-safety.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Import circular dependencies with TYPE_CHECKING
from typing import TYPE_CHECKING, Any, Optional

from src.core.events.universal_event import PerceivedEvent, now_utc

if TYPE_CHECKING:
    from src.figaro.actions.base import Action


class UpdateType(str, Enum):
    """Type de mise à jour de connaissances"""
    NOTE_CREATED = "note_created"
    NOTE_UPDATED = "note_updated"
    ENTITY_ADDED = "entity_added"
    TAG_ADDED = "tag_added"
    RELATIONSHIP_CREATED = "relationship_created"


class PatternType(str, Enum):
    """Type de pattern appris"""
    ACTION_SEQUENCE = "action_sequence"
    ENTITY_RELATIONSHIP = "entity_relationship"
    TIME_BASED = "time_based"
    CONTEXT_TRIGGER = "context_trigger"


@dataclass(frozen=True)
class UserFeedback:
    """
    Feedback utilisateur sur une décision

    Combine feedback explicite (approval, rating, comment) et
    implicite (action_executed, time_to_action) pour évaluer
    la qualité de la décision.

    Immutable pour thread-safety.
    """
    # Explicit feedback
    approval: bool
    rating: Optional[int] = None  # 1-5 scale
    comment: Optional[str] = None
    correction: Optional[str] = None

    # Implicit signals
    action_executed: bool = False
    time_to_action: float = 0.0  # Seconds
    modification: Optional["Action"] = None

    # Metadata
    timestamp: datetime = field(default_factory=now_utc)
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate feedback"""
        if self.rating is not None and not (1 <= self.rating <= 5):
            raise ValueError(f"Rating must be 1-5, got {self.rating}")

        if self.time_to_action < 0:
            raise ValueError(f"time_to_action must be >= 0, got {self.time_to_action}")

    @property
    def is_positive(self) -> bool:
        """Check if feedback is generally positive"""
        if not self.approval:
            return False
        return not (self.rating is not None and self.rating < 3)

    @property
    def implicit_quality_score(self) -> float:
        """
        Calculate quality score from implicit signals

        Fast action execution + no modification = high quality
        Returns score 0-1
        """
        score = 1.0

        # Penalize slow action (> 60s)
        if self.time_to_action > 60:
            score *= 0.7
        elif self.time_to_action > 30:
            score *= 0.85

        # Penalize if action was modified
        if self.modification is not None:
            score *= 0.5

        # Penalize if action was not executed
        if not self.action_executed:
            score *= 0.3

        return score


@dataclass(frozen=True)
class FeedbackAnalysis:
    """
    Résultat de l'analyse de feedback

    Extrait des insights depuis UserFeedback pour learning.
    Immutable.
    """
    feedback: UserFeedback
    correctness_score: float  # 0-1, 1 = décision parfaite
    suggested_improvements: list[str]
    confidence_error: float  # Différence entre confiance prédite et réalité
    action_quality_score: float  # 0-1
    reasoning_quality_score: float  # 0-1

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate analysis"""
        if not (0 <= self.correctness_score <= 1):
            raise ValueError(f"correctness_score must be 0-1, got {self.correctness_score}")
        if not (0 <= self.action_quality_score <= 1):
            raise ValueError(f"action_quality_score must be 0-1, got {self.action_quality_score}")
        if not (0 <= self.reasoning_quality_score <= 1):
            raise ValueError(f"reasoning_quality_score must be 0-1, got {self.reasoning_quality_score}")


@dataclass(frozen=True)
class KnowledgeUpdate:
    """
    Une mise à jour de la base de connaissances

    Représente un changement à appliquer au PKM.
    Immutable.
    """
    update_type: UpdateType
    target_id: str
    changes: dict[str, Any]
    confidence: float  # 0-1
    source: str  # e.g., "learning_from_execution"
    timestamp: datetime = field(default_factory=now_utc)
    update_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate update"""
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")
        if not self.target_id:
            raise ValueError("target_id is required")
        if not self.changes:
            raise ValueError("changes dict cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "update_id": self.update_id,
            "update_type": self.update_type.value,
            "target_id": self.target_id,
            "changes": self.changes,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass(frozen=True)
class Pattern:
    """
    Un pattern identifié dans les décisions

    Représente un pattern récurrent qui peut être utilisé
    pour suggérer des actions futures.
    Immutable.
    """
    pattern_id: str
    pattern_type: PatternType
    conditions: dict[str, Any]  # Quand s'applique ce pattern
    suggested_actions: list[str]  # Action types à suggérer
    confidence: float  # 0-1
    success_rate: float  # 0-1
    occurrences: int
    last_seen: datetime
    created_at: datetime

    def __post_init__(self):
        """Validate pattern"""
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")
        if not (0 <= self.success_rate <= 1):
            raise ValueError(f"success_rate must be 0-1, got {self.success_rate}")
        if self.occurrences < 0:
            raise ValueError(f"occurrences must be >= 0, got {self.occurrences}")
        if not self.suggested_actions:
            raise ValueError("suggested_actions cannot be empty")

    def matches(self, event: PerceivedEvent, context: dict[str, Any]) -> bool:
        """
        Check if pattern matches current situation

        Args:
            event: Current event
            context: Additional context (e.g., time of day, thread length)

        Returns:
            True if pattern conditions match
        """
        # Check event type
        if "event_type" in self.conditions and event.event_type.value != self.conditions["event_type"]:
            return False

        # Check urgency
        if "min_urgency" in self.conditions and event.urgency.value < self.conditions["min_urgency"]:
            return False

        # Check entity presence
        if "required_entities" in self.conditions:
            event_entity_types = {e.type for e in event.entities}
            required = set(self.conditions["required_entities"])
            if not required.issubset(event_entity_types):
                return False

        # Check context conditions
        if "context" in self.conditions:
            for key, value in self.conditions["context"].items():
                if context.get(key) != value:
                    return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "conditions": self.conditions,
            "suggested_actions": self.suggested_actions,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            "occurrences": self.occurrences,
            "last_seen": self.last_seen.isoformat(),
            "created_at": self.created_at.isoformat()
        }


@dataclass(frozen=True)
class ProviderScore:
    """
    Score de performance d'un AI provider

    Track performance, quality, latency, et cost metrics.
    Immutable.
    """
    provider_name: str
    model_tier: str  # "haiku", "sonnet", "opus"

    # Performance metrics
    total_calls: int
    successful_calls: int
    failed_calls: int

    # Quality metrics
    avg_confidence: float
    calibration_error: float  # Abs difference between predicted and actual

    # Latency metrics
    avg_latency_ms: float
    p95_latency_ms: float

    # Cost metrics
    total_cost_usd: float

    # Timestamp
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self):
        """Validate score"""
        if self.total_calls < 0:
            raise ValueError(f"total_calls must be >= 0, got {self.total_calls}")
        if self.total_calls != self.successful_calls + self.failed_calls:
            raise ValueError("total_calls must equal successful_calls + failed_calls")
        if not (0 <= self.avg_confidence <= 1):
            raise ValueError(f"avg_confidence must be 0-1, got {self.avg_confidence}")
        if self.calibration_error < 0:
            raise ValueError(f"calibration_error must be >= 0, got {self.calibration_error}")

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-1)"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def cost_per_success_usd(self) -> float:
        """Calculate cost per successful call"""
        if self.successful_calls == 0:
            return 0.0
        return self.total_cost_usd / self.successful_calls

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "provider_name": self.provider_name,
            "model_tier": self.model_tier,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": self.success_rate,
            "avg_confidence": self.avg_confidence,
            "calibration_error": self.calibration_error,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "total_cost_usd": self.total_cost_usd,
            "cost_per_success_usd": self.cost_per_success_usd,
            "updated_at": self.updated_at.isoformat()
        }


@dataclass(frozen=True)
class LearningResult:
    """
    Résultat d'un cycle d'apprentissage

    Contient toutes les mises à jour et metrics d'un learning cycle.
    Immutable.
    """
    knowledge_updates: list[KnowledgeUpdate]
    pattern_updates: list[Pattern]
    provider_scores: dict[str, ProviderScore]
    confidence_adjustments: dict[str, float]

    # Metadata
    duration: float
    updates_applied: int
    updates_failed: int

    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=now_utc)
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate result"""
        if self.duration < 0:
            raise ValueError(f"duration must be >= 0, got {self.duration}")
        if self.updates_applied < 0:
            raise ValueError(f"updates_applied must be >= 0, got {self.updates_applied}")
        if self.updates_failed < 0:
            raise ValueError(f"updates_failed must be >= 0, got {self.updates_failed}")

    @property
    def success(self) -> bool:
        """Check if learning succeeded"""
        return self.updates_failed == 0

    @property
    def total_updates(self) -> int:
        """Total number of updates attempted"""
        return self.updates_applied + self.updates_failed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "result_id": self.result_id,
            "success": self.success,
            "duration": self.duration,
            "knowledge_updates": [u.to_dict() for u in self.knowledge_updates],
            "pattern_updates": [p.to_dict() for p in self.pattern_updates],
            "provider_scores": {k: v.to_dict() for k, v in self.provider_scores.items()},
            "confidence_adjustments": self.confidence_adjustments,
            "updates_applied": self.updates_applied,
            "updates_failed": self.updates_failed,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
