"""
Tests for Universal Event Model

Tests PerceivedEvent and related types (EventSource, EventType, UrgencyLevel, Entity).
"""

import pytest
from datetime import datetime, timedelta
from src.core.events import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
    Entity,
)
from src.utils import now_utc


class TestEntity:
    """Tests for Entity dataclass"""

    def test_entity_creation(self):
        """Test creating an entity"""
        entity = Entity(
            type="person",
            value="john@example.com",
            confidence=0.95,
            metadata={"name": "John Doe"}
        )

        assert entity.type == "person"
        assert entity.value == "john@example.com"
        assert entity.confidence == 0.95
        assert entity.metadata["name"] == "John Doe"

    def test_entity_default_metadata(self):
        """Test entity with default empty metadata"""
        entity = Entity(
            type="organization",
            value="Acme Corp",
            confidence=1.0
        )

        assert entity.metadata == {}

    def test_entity_various_types(self):
        """Test different entity types"""
        types = ["person", "organization", "location", "date", "topic", "url"]

        for entity_type in types:
            entity = Entity(
                type=entity_type,
                value="test_value",
                confidence=0.8
            )
            assert entity.type == entity_type


class TestEventEnums:
    """Tests for Event-related enums"""

    def test_event_source_values(self):
        """Test EventSource enum values"""
        assert EventSource.EMAIL == "email"
        assert EventSource.FILE == "file"
        assert EventSource.QUESTION == "question"
        assert EventSource.CALENDAR == "calendar"
        assert EventSource.WEB == "web"
        assert EventSource.NOTE == "note"

    def test_event_type_values(self):
        """Test EventType enum values"""
        assert EventType.REQUEST == "request"
        assert EventType.INFORMATION == "information"
        assert EventType.ACTION_REQUIRED == "action_required"
        assert EventType.DECISION_NEEDED == "decision_needed"
        assert EventType.REPLY == "reply"
        assert EventType.INVITATION == "invitation"
        assert EventType.STATUS_UPDATE == "status_update"
        assert EventType.REFERENCE == "reference"

    def test_urgency_level_values(self):
        """Test UrgencyLevel enum values"""
        assert UrgencyLevel.CRITICAL == "critical"
        assert UrgencyLevel.HIGH == "high"
        assert UrgencyLevel.MEDIUM == "medium"
        assert UrgencyLevel.LOW == "low"
        assert UrgencyLevel.NONE == "none"


class TestPerceivedEvent:
    """Tests for PerceivedEvent dataclass"""

    def test_minimal_event_creation(self):
        """Test creating event with minimal required fields"""
        now = now_utc()
        event = PerceivedEvent(
            event_id="test_event_123",
            source=EventSource.EMAIL,
            source_id="email_456",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Test Event",
            content="Test content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="test@example.com",
            to_people=["recipient@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        assert event.event_id == "test_event_123"
        assert event.source == EventSource.EMAIL
        assert event.title == "Test Event"
        assert event.event_type == EventType.INFORMATION
        assert event.urgency == UrgencyLevel.LOW

    def test_event_with_entities(self):
        """Test event with extracted entities"""
        now = now_utc()
        entities = [
            Entity(type="person", value="john@example.com", confidence=0.95),
            Entity(type="organization", value="Acme Corp", confidence=0.9),
        ]

        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Meeting with Acme",
            content="Discussion about project",
            event_type=EventType.INVITATION,
            urgency=UrgencyLevel.MEDIUM,
            entities=entities,
            topics=["meeting", "project"],
            keywords=["discussion", "acme"],
            from_person="john@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id="thread_1",
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.85,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        assert len(event.entities) == 2
        assert event.entities[0].type == "person"
        assert event.entities[1].type == "organization"
        assert "meeting" in event.topics
        assert "discussion" in event.keywords

    def test_event_with_attachments(self):
        """Test event with attachments"""
        now = now_utc()
        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Report with attachments",
            content="Please review attached files",
            event_type=EventType.ACTION_REQUIRED,
            urgency=UrgencyLevel.HIGH,
            entities=[],
            topics=[],
            keywords=[],
            from_person="sender@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=True,
            attachment_count=3,
            attachment_types=["pdf", "xlsx", "docx"],
            urls=["https://example.com/doc"],
            metadata={"email_size_bytes": 5242880},
            perception_confidence=0.9,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        assert event.has_attachments is True
        assert event.attachment_count == 3
        assert "pdf" in event.attachment_types
        assert "xlsx" in event.attachment_types
        assert len(event.urls) == 1

    def test_event_thread_information(self):
        """Test event with thread/conversation context"""
        now = now_utc()
        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_3",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Re: Project Discussion",
            content="Following up on previous email",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="sender@example.com",
            to_people=["me@example.com"],
            cc_people=["other@example.com"],
            thread_id="thread_abc123",
            references=["<msg1@example.com>", "<msg2@example.com>"],
            in_reply_to="<msg2@example.com>",
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.8,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        assert event.thread_id == "thread_abc123"
        assert event.in_reply_to == "<msg2@example.com>"
        assert len(event.references) == 2
        assert event.event_type == EventType.REPLY

    def test_event_needs_clarification(self):
        """Test event that needs clarification"""
        now = now_utc()
        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Ambiguous request",
            content="Can you do that thing?",
            event_type=EventType.REQUEST,
            urgency=UrgencyLevel.MEDIUM,
            entities=[],
            topics=[],
            keywords=[],
            from_person="sender@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.4,
            needs_clarification=True,
            clarification_questions=[
                "What specific thing are you referring to?",
                "When do you need this completed?"
            ],
            summary=None
        )

        assert event.needs_clarification is True
        assert len(event.clarification_questions) == 2
        assert event.perception_confidence == 0.4

    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        now = now_utc()
        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Test",
            content="Content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="test@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={"custom": "value"},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary="Test summary"
        )

        event_dict = event.to_dict()

        assert event_dict["event_id"] == "test_event"
        assert event_dict["source"] == "email"
        assert event_dict["title"] == "Test"
        assert event_dict["summary"] == "Test summary"
        assert event_dict["metadata"]["custom"] == "value"
        assert "occurred_at" in event_dict
        assert "received_at" in event_dict

    def test_event_str_representation(self):
        """Test string representation of event"""
        now = now_utc()
        event = PerceivedEvent(
            event_id="test_event_123456",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Test Event",
            content="Content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.MEDIUM,
            entities=[],
            topics=[],
            keywords=[],
            from_person="test@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.85,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        str_repr = str(event)

        assert "test_eve" in str_repr  # First 8 chars of event_id
        assert "email" in str_repr
        assert "information" in str_repr
        assert "medium" in str_repr

    def test_event_multiple_recipients(self):
        """Test event with multiple to/cc recipients"""
        now = now_utc()
        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now,
            received_at=now,
            title="Team Update",
            content="Update for the team",
            event_type=EventType.STATUS_UPDATE,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="manager@example.com",
            to_people=["alice@example.com", "bob@example.com", "charlie@example.com"],
            cc_people=["hr@example.com", "admin@example.com"],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.9,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        assert len(event.to_people) == 3
        assert len(event.cc_people) == 2
        assert "alice@example.com" in event.to_people
        assert "hr@example.com" in event.cc_people

    def test_event_time_relationships(self):
        """Test event timing relationships"""
        occurred = now_utc() - timedelta(hours=2)
        received = now_utc() - timedelta(hours=1)
        perceived = now_utc()

        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=occurred,
            received_at=received,
            perceived_at=perceived,
            title="Test",
            content="Content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="test@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        # Verify time progression: occurred <= received <= perceived
        assert event.occurred_at <= event.received_at
        assert event.received_at <= event.perceived_at

    def test_event_custom_metadata(self):
        """Test event with custom metadata"""
        now = now_utc()
        custom_metadata = {
            "email_flags": ["\\Seen", "\\Flagged"],
            "email_folder": "INBOX",
            "email_size_bytes": 12345,
            "custom_field": "custom_value"
        }

        event = PerceivedEvent(
            event_id="test_event",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Test",
            content="Content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="test@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata=custom_metadata,
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        assert event.metadata["email_flags"] == ["\\Seen", "\\Flagged"]
        assert event.metadata["email_folder"] == "INBOX"
        assert event.metadata["email_size_bytes"] == 12345
        assert event.metadata["custom_field"] == "custom_value"
