"""
Universal Event Model

This module defines the universal event representation that all inputs
(emails, files, questions, etc.) are normalized into.

Architecture: Perception Layer
Design: Event-Driven, Source-Agnostic
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from src.utils import now_utc


class EventSource(str, Enum):
    """
    Source types for events

    All inputs to the cognitive system are categorized by source.
    """
    EMAIL = "email"
    FILE = "file"
    QUESTION = "question"
    DOCUMENT = "document"
    CALENDAR = "calendar"
    WEB = "web"
    TASK = "task"
    NOTE = "note"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    """
    High-level event categories

    Determined during perception/initial classification.
    """
    # Communication events
    REQUEST = "request"              # Someone asks for something
    INFORMATION = "information"      # FYI, news, updates
    DECISION_NEEDED = "decision_needed"  # Requires user decision

    # Task events
    ACTION_REQUIRED = "action_required"  # User must do something
    REMINDER = "reminder"            # Time-based reminder
    DEADLINE = "deadline"            # Time constraint

    # Knowledge events
    REFERENCE = "reference"          # Save for later
    LEARNING = "learning"            # Educational content
    INSIGHT = "insight"              # New understanding/connection

    # System events
    STATUS_UPDATE = "status_update"  # Progress report
    ERROR = "error"                  # Something wrong
    CONFIRMATION = "confirmation"    # Acknowledgment needed

    # Social events
    INVITATION = "invitation"        # Meeting, event invite
    REPLY = "reply"                  # Response to previous event

    UNKNOWN = "unknown"


class UrgencyLevel(str, Enum):
    """Event urgency classification"""
    CRITICAL = "critical"    # Immediate action required
    HIGH = "high"           # Action needed today
    MEDIUM = "medium"       # Action needed this week
    LOW = "low"            # No time pressure
    NONE = "none"          # Informational only


@dataclass
class Entity:
    """
    Extracted entity from event content

    Entities are key pieces of information that help with context retrieval
    and relationship mapping in the PKM.
    """
    type: str  # person, organization, date, location, topic, project, etc.
    value: str  # The actual entity value
    confidence: float  # 0.0-1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate entity"""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        if not self.type or not self.type.strip():
            raise ValueError("type cannot be empty")
        if not self.value or not self.value.strip():
            raise ValueError("value cannot be empty")

    def __str__(self) -> str:
        return f"{self.type}:{self.value} ({self.confidence:.0%})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on type and value (ignore confidence/metadata)"""
        if not isinstance(other, Entity):
            return NotImplemented
        return self.type == other.type and self.value.lower() == other.value.lower()

    def __hash__(self) -> int:
        """Hash based on type and value for use in sets/dicts"""
        return hash((self.type, self.value.lower()))


@dataclass(frozen=True)
class PerceivedEvent:
    """
    Universal event representation (Immutable)

    All inputs (emails, files, questions, etc.) are normalized into this
    unified format. This allows the cognitive system to reason about any
    type of input using the same architecture.

    Design Philosophy:
    - Source-agnostic: Same structure regardless of origin
    - Rich context: Captures all relevant information
    - Extensible: metadata dict for source-specific data
    - Traceable: Full provenance from raw input to perception
    - **Immutable**: Once created, events cannot be modified (frozen=True)
      This ensures data integrity and prevents accidental modification
      during processing. If modifications are needed, create a new event.
    """

    # === REQUIRED FIELDS (no defaults) ===
    # Identity
    event_id: str  # Unique identifier
    source: EventSource  # Where this came from
    source_id: str  # Original ID in source system (e.g., email UID)

    # Timing
    occurred_at: datetime  # When the event happened
    received_at: datetime  # When we received it

    # Core Content
    title: str  # Short summary (subject, filename, question, etc.)
    content: str  # Full content/body

    # Classification (from Perception layer)
    event_type: EventType
    urgency: UrgencyLevel

    # Extracted Information
    entities: List[Entity]
    topics: List[str]  # Main subjects/themes
    keywords: List[str]  # Important terms

    # Participants (for communication events)
    from_person: str
    to_people: List[str]  # Recipients
    cc_people: List[str]  # CC'd people

    # Context Links
    thread_id: Optional[str]  # Conversation/thread identifier
    references: List[str]  # Related event IDs
    in_reply_to: Optional[str]  # If this is a reply

    # Attachments & Resources
    has_attachments: bool
    attachment_count: int
    attachment_types: List[str]
    urls: List[str]

    # Source-Specific Data
    metadata: Dict[str, Any]

    # Quality Metrics
    perception_confidence: float  # How confident is the perception
    needs_clarification: bool  # If true, should ask user
    clarification_questions: List[str]

    # === OPTIONAL FIELDS (with defaults) ===
    perceived_at: datetime = field(default_factory=now_utc)  # When we processed it
    summary: Optional[str] = None  # AI-generated summary (if long)

    def __post_init__(self):
        """Validate event after initialization"""
        # Ensure all datetimes are timezone-aware
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        if self.perceived_at.tzinfo is None:
            raise ValueError("perceived_at must be timezone-aware")

        # Validate string fields are not empty
        if not self.event_id or not self.event_id.strip():
            raise ValueError("event_id cannot be empty")
        if not self.source_id or not self.source_id.strip():
            raise ValueError("source_id cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")
        # Note: content CAN be empty for some event types (calendar invites)
        if not self.from_person or not self.from_person.strip():
            raise ValueError("from_person cannot be empty")

        # Validate lists are not None
        if self.entities is None:
            raise ValueError("entities cannot be None (use empty list)")
        if self.topics is None:
            raise ValueError("topics cannot be None (use empty list)")
        if self.keywords is None:
            raise ValueError("keywords cannot be None (use empty list)")
        if self.to_people is None:
            raise ValueError("to_people cannot be None (use empty list)")
        if self.cc_people is None:
            raise ValueError("cc_people cannot be None (use empty list)")
        if self.references is None:
            raise ValueError("references cannot be None (use empty list)")
        if self.attachment_types is None:
            raise ValueError("attachment_types cannot be None (use empty list)")
        if self.urls is None:
            raise ValueError("urls cannot be None (use empty list)")
        if self.clarification_questions is None:
            raise ValueError("clarification_questions cannot be None (use empty list)")
        if self.metadata is None:
            raise ValueError("metadata cannot be None (use empty dict)")

        # Ensure confidence is in valid range
        if not (0.0 <= self.perception_confidence <= 1.0):
            raise ValueError(f"perception_confidence must be 0.0-1.0, got {self.perception_confidence}")

        # Validate temporal ordering: occurred <= received <= perceived
        if self.occurred_at > self.received_at:
            raise ValueError(
                f"occurred_at ({self.occurred_at}) cannot be after "
                f"received_at ({self.received_at})"
            )
        if self.received_at > self.perceived_at:
            raise ValueError(
                f"received_at ({self.received_at}) cannot be after "
                f"perceived_at ({self.perceived_at})"
            )

        # Ensure occurred_at is not in the future (with 1s tolerance for clock skew)
        # Tolerance prevents spurious failures for events occurring "right now"
        from datetime import timedelta
        current_time = now_utc()
        tolerance = timedelta(seconds=1)
        if self.occurred_at > current_time + tolerance:
            raise ValueError(
                f"occurred_at cannot be in the future: {self.occurred_at} "
                f"(current time: {current_time}, tolerance: 1s)"
            )

        # Validate attachment consistency
        if self.has_attachments and self.attachment_count == 0:
            raise ValueError("has_attachments is True but attachment_count is 0")
        if not self.has_attachments and self.attachment_count > 0:
            raise ValueError("has_attachments is False but attachment_count > 0")
        if self.attachment_count < 0:
            raise ValueError("attachment_count cannot be negative")

        # Validate attachment_count matches attachment_types length exactly
        # This prevents inconsistencies where count doesn't match actual type data
        if self.has_attachments and len(self.attachment_types) != self.attachment_count:
            raise ValueError(
                f"attachment_count ({self.attachment_count}) must exactly match "
                f"attachment_types length ({len(self.attachment_types)}). "
                f"Each attachment must have a corresponding type."
            )

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a specific type"""
        return [e for e in self.entities if e.type == entity_type]

    def has_entity(self, entity_type: str, value: str) -> bool:
        """Check if event contains a specific entity"""
        return any(
            e.type == entity_type and e.value.lower() == value.lower()
            for e in self.entities
        )

    def is_part_of_thread(self) -> bool:
        """Check if this event is part of a conversation thread"""
        return self.thread_id is not None or self.in_reply_to is not None

    def is_urgent(self) -> bool:
        """Check if this event requires urgent attention"""
        return self.urgency in (UrgencyLevel.CRITICAL, UrgencyLevel.HIGH)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "source": self.source.value,
            "source_id": self.source_id,
            "occurred_at": self.occurred_at.isoformat(),
            "received_at": self.received_at.isoformat(),
            "perceived_at": self.perceived_at.isoformat(),
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "event_type": self.event_type.value,
            "urgency": self.urgency.value,
            "entities": [
                {
                    "type": e.type,
                    "value": e.value,
                    "confidence": e.confidence,
                    "metadata": e.metadata
                }
                for e in self.entities
            ],
            "topics": self.topics,
            "keywords": self.keywords,
            "from_person": self.from_person,
            "to_people": self.to_people,
            "cc_people": self.cc_people,
            "thread_id": self.thread_id,
            "references": self.references,
            "in_reply_to": self.in_reply_to,
            "has_attachments": self.has_attachments,
            "attachment_count": self.attachment_count,
            "attachment_types": self.attachment_types,
            "urls": self.urls,
            "metadata": self.metadata,
            "perception_confidence": self.perception_confidence,
            "needs_clarification": self.needs_clarification,
            "clarification_questions": self.clarification_questions
        }

    def __str__(self) -> str:
        """Human-readable representation"""
        return (
            f"PerceivedEvent({self.event_id[:8]}... "
            f"source={self.source.value}, "
            f"type={self.event_type.value}, "
            f"urgency={self.urgency.value}, "
            f"title='{self.title[:50]}{'...' if len(self.title) > 50 else ''}')"
        )

    def __repr__(self) -> str:
        """Developer representation"""
        return self.__str__()
