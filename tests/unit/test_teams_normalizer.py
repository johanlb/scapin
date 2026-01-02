"""
Unit Tests for Teams Normalizer

Tests TeamsNormalizer converting TeamsMessage to PerceivedEvent.
"""

from datetime import datetime, timezone

import pytest

from src.core.events.universal_event import EventSource, EventType, UrgencyLevel
from src.integrations.microsoft.models import (
    TeamsChat,
    TeamsChatType,
    TeamsMessage,
    TeamsMessageImportance,
    TeamsSender,
)
from src.integrations.microsoft.teams_normalizer import TeamsNormalizer


class TestTeamsNormalizer:
    """Tests for TeamsNormalizer"""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance"""
        return TeamsNormalizer()

    @pytest.fixture
    def sample_sender(self):
        """Create sample sender"""
        return TeamsSender(
            user_id="sender-123",
            display_name="John Doe",
            email="john.doe@example.com",
        )

    @pytest.fixture
    def sample_chat(self):
        """Create sample chat"""
        return TeamsChat(
            chat_id="chat-456",
            chat_type=TeamsChatType.GROUP,
            topic="Project Alpha",
            created_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
        )

    @pytest.fixture
    def sample_message(self, sample_sender, sample_chat):
        """Create sample message"""
        return TeamsMessage(
            message_id="msg-001",
            chat_id="chat-456",
            sender=sample_sender,
            content="<p>Hello team, please review the document.</p>",
            content_plain="Hello team, please review the document.",
            created_at=datetime(2025, 1, 15, 14, 30, tzinfo=timezone.utc),
            chat=sample_chat,
        )


class TestNormalizeBasic(TestTeamsNormalizer):
    """Tests for basic normalization"""

    def test_normalize_creates_perceived_event(self, normalizer, sample_message):
        """Test that normalize creates a PerceivedEvent"""
        event = normalizer.normalize(sample_message)

        assert event is not None
        assert event.event_id == "teams-msg-001"
        assert event.source == EventSource.TEAMS
        assert event.source_id == "msg-001"

    def test_normalize_preserves_content(self, normalizer, sample_message):
        """Test that content is preserved"""
        event = normalizer.normalize(sample_message)

        assert event.content == "Hello team, please review the document."
        assert "Hello team" in event.title

    def test_normalize_preserves_timing(self, normalizer, sample_message):
        """Test that timing information is preserved"""
        event = normalizer.normalize(sample_message)

        assert event.occurred_at == sample_message.created_at
        assert event.received_at == sample_message.created_at
        assert event.perceived_at is not None

    def test_normalize_sets_thread_id(self, normalizer, sample_message):
        """Test that thread_id is set to chat_id"""
        event = normalizer.normalize(sample_message)

        assert event.thread_id == "chat-456"

    def test_normalize_sets_from_person(self, normalizer, sample_message):
        """Test that from_person is set correctly"""
        event = normalizer.normalize(sample_message)

        assert "John Doe" in event.from_person
        assert "john.doe@example.com" in event.from_person


class TestNormalizeEventType(TestTeamsNormalizer):
    """Tests for event type determination"""

    def test_urgent_message_becomes_action_required(self, normalizer, sample_sender):
        """Test that urgent messages become ACTION_REQUIRED"""
        message = TeamsMessage(
            message_id="msg-urgent",
            chat_id="chat-123",
            sender=sample_sender,
            content="URGENT: Need response now!",
            content_plain="URGENT: Need response now!",
            created_at=datetime.now(timezone.utc),
            importance=TeamsMessageImportance.URGENT,
        )

        event = normalizer.normalize(message)
        assert event.event_type == EventType.ACTION_REQUIRED

    def test_high_importance_becomes_action_required(self, normalizer, sample_sender):
        """Test that high importance messages become ACTION_REQUIRED"""
        message = TeamsMessage(
            message_id="msg-high",
            chat_id="chat-123",
            sender=sample_sender,
            content="Important: Please review",
            content_plain="Important: Please review",
            created_at=datetime.now(timezone.utc),
            importance=TeamsMessageImportance.HIGH,
        )

        event = normalizer.normalize(message)
        assert event.event_type == EventType.ACTION_REQUIRED

    def test_mention_becomes_request(self, normalizer, sample_sender):
        """Test that messages with mentions become REQUEST"""
        message = TeamsMessage(
            message_id="msg-mention",
            chat_id="chat-123",
            sender=sample_sender,
            content="@user can you help?",
            content_plain="@user can you help?",
            created_at=datetime.now(timezone.utc),
            mentions=("user-456",),
        )

        event = normalizer.normalize(message)
        assert event.event_type == EventType.REQUEST

    def test_reply_becomes_reply(self, normalizer, sample_sender):
        """Test that reply messages get REPLY type"""
        message = TeamsMessage(
            message_id="msg-reply",
            chat_id="chat-123",
            sender=sample_sender,
            content="Thanks for the info",
            content_plain="Thanks for the info",
            created_at=datetime.now(timezone.utc),
            is_reply=True,
            reply_to_id="msg-original",
        )

        event = normalizer.normalize(message)
        assert event.event_type == EventType.REPLY

    def test_meeting_chat_becomes_information(self, normalizer, sample_sender):
        """Test that meeting chat messages become INFORMATION"""
        meeting_chat = TeamsChat(
            chat_id="meeting-123",
            chat_type=TeamsChatType.MEETING,
            topic="Weekly Sync",
            created_at=datetime.now(timezone.utc),
        )
        message = TeamsMessage(
            message_id="msg-meeting",
            chat_id="meeting-123",
            sender=sample_sender,
            content="Meeting notes attached",
            content_plain="Meeting notes attached",
            created_at=datetime.now(timezone.utc),
            chat=meeting_chat,
        )

        event = normalizer.normalize(message)
        assert event.event_type == EventType.INFORMATION

    def test_normal_message_becomes_information(self, normalizer, sample_sender):
        """Test that normal messages become INFORMATION"""
        message = TeamsMessage(
            message_id="msg-normal",
            chat_id="chat-123",
            sender=sample_sender,
            content="FYI: The server is back up",
            content_plain="FYI: The server is back up",
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)
        assert event.event_type == EventType.INFORMATION


class TestNormalizeUrgency(TestTeamsNormalizer):
    """Tests for urgency level determination"""

    def test_urgent_importance_becomes_critical(self, normalizer, sample_sender):
        """Test URGENT importance maps to CRITICAL urgency"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="Emergency!",
            content_plain="Emergency!",
            created_at=datetime.now(timezone.utc),
            importance=TeamsMessageImportance.URGENT,
        )

        event = normalizer.normalize(message)
        assert event.urgency == UrgencyLevel.CRITICAL

    def test_high_importance_becomes_high(self, normalizer, sample_sender):
        """Test HIGH importance maps to HIGH urgency"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="Priority task",
            content_plain="Priority task",
            created_at=datetime.now(timezone.utc),
            importance=TeamsMessageImportance.HIGH,
        )

        event = normalizer.normalize(message)
        assert event.urgency == UrgencyLevel.HIGH

    def test_mention_becomes_medium(self, normalizer, sample_sender):
        """Test mentions increase urgency to MEDIUM"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="@user check this",
            content_plain="@user check this",
            created_at=datetime.now(timezone.utc),
            mentions=("user-456",),
        )

        event = normalizer.normalize(message)
        assert event.urgency == UrgencyLevel.MEDIUM

    def test_normal_message_becomes_low(self, normalizer, sample_sender):
        """Test normal messages have LOW urgency"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="Just an FYI",
            content_plain="Just an FYI",
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)
        assert event.urgency == UrgencyLevel.LOW


class TestNormalizeEntities(TestTeamsNormalizer):
    """Tests for entity extraction"""

    def test_extracts_sender_as_entity(self, normalizer, sample_message):
        """Test that sender is extracted as an entity"""
        event = normalizer.normalize(sample_message)

        sender_entities = [e for e in event.entities if e.metadata.get("role") == "sender"]
        assert len(sender_entities) == 1
        assert sender_entities[0].type == "person"
        assert sender_entities[0].value == "John Doe"

    def test_extracts_mentions_as_entities(self, normalizer, sample_sender):
        """Test that mentioned users are extracted as entities"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="@alice @bob please review",
            content_plain="@alice @bob please review",
            created_at=datetime.now(timezone.utc),
            mentions=("alice-id", "bob-id"),
        )

        event = normalizer.normalize(message)

        mention_entities = [e for e in event.entities if e.metadata.get("role") == "mentioned"]
        assert len(mention_entities) == 2

    def test_extracts_chat_topic_as_entity(self, normalizer, sample_message):
        """Test that chat topic is extracted as an entity"""
        event = normalizer.normalize(sample_message)

        topic_entities = [e for e in event.entities if e.type == "topic"]
        assert len(topic_entities) == 1
        assert topic_entities[0].value == "Project Alpha"


class TestNormalizeMetadata(TestTeamsNormalizer):
    """Tests for metadata extraction"""

    def test_metadata_contains_message_id(self, normalizer, sample_message):
        """Test metadata includes message_id"""
        event = normalizer.normalize(sample_message)

        assert event.metadata["message_id"] == "msg-001"

    def test_metadata_contains_chat_id(self, normalizer, sample_message):
        """Test metadata includes chat_id"""
        event = normalizer.normalize(sample_message)

        assert event.metadata["chat_id"] == "chat-456"

    def test_metadata_contains_sender_info(self, normalizer, sample_message):
        """Test metadata includes sender information"""
        event = normalizer.normalize(sample_message)

        assert event.metadata["sender_id"] == "sender-123"
        assert event.metadata["sender_name"] == "John Doe"
        assert event.metadata["sender_email"] == "john.doe@example.com"

    def test_metadata_contains_importance(self, normalizer, sample_sender):
        """Test metadata includes importance level"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="Test",
            content_plain="Test",
            created_at=datetime.now(timezone.utc),
            importance=TeamsMessageImportance.HIGH,
        )

        event = normalizer.normalize(message)
        assert event.metadata["importance"] == "high"

    def test_metadata_contains_chat_type(self, normalizer, sample_message):
        """Test metadata includes chat type"""
        event = normalizer.normalize(sample_message)

        assert event.metadata["chat_type"] == "group"

    def test_metadata_contains_mentions_list(self, normalizer, sample_sender):
        """Test metadata includes mentions list"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="@user1 @user2",
            content_plain="@user1 @user2",
            created_at=datetime.now(timezone.utc),
            mentions=("user-1", "user-2"),
        )

        event = normalizer.normalize(message)
        assert event.metadata["mentions"] == ["user-1", "user-2"]


class TestNormalizeAttachments(TestTeamsNormalizer):
    """Tests for attachment handling"""

    def test_detects_attachments(self, normalizer, sample_sender):
        """Test that attachments are detected"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="See attached",
            content_plain="See attached",
            created_at=datetime.now(timezone.utc),
            attachments=("report.pdf", "data.xlsx"),
        )

        event = normalizer.normalize(message)

        assert event.has_attachments is True
        assert event.attachment_count == 2
        assert "report.pdf" in event.attachment_types
        assert "data.xlsx" in event.attachment_types

    def test_no_attachments(self, normalizer, sample_message):
        """Test message without attachments"""
        event = normalizer.normalize(sample_message)

        assert event.has_attachments is False
        assert event.attachment_count == 0


class TestNormalizeUrls(TestTeamsNormalizer):
    """Tests for URL extraction"""

    def test_extracts_urls_from_content(self, normalizer, sample_sender):
        """Test URL extraction from HTML content"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content='<p>Check <a href="https://example.com/page">this</a></p>',
            content_plain="Check this",
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)

        assert len(event.urls) > 0
        assert "https://example.com/page" in event.urls

    def test_extracts_multiple_urls(self, normalizer, sample_sender):
        """Test extracting multiple URLs"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content='<a href="https://a.com">A</a> and <a href="https://b.com">B</a>',
            content_plain="A and B",
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)

        assert "https://a.com" in event.urls
        assert "https://b.com" in event.urls


class TestNormalizeBuildTitle(TestTeamsNormalizer):
    """Tests for title building"""

    def test_uses_first_line_as_title(self, normalizer, sample_sender):
        """Test that first line is used as title"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="First line\nSecond line\nThird line",
            content_plain="First line\nSecond line\nThird line",
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)
        assert event.title == "First line"

    def test_truncates_long_title(self, normalizer, sample_sender):
        """Test that long titles are truncated"""
        long_content = "A" * 150  # Longer than 100 chars
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content=long_content,
            content_plain=long_content,
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)
        assert len(event.title) <= 100
        assert event.title.endswith("...")

    def test_handles_empty_content(self, normalizer, sample_sender):
        """Test handling of empty content"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="",
            content_plain="",
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)
        assert event.title == "(empty message)"


class TestNormalizeTopicsKeywords(TestTeamsNormalizer):
    """Tests for topic and keyword extraction"""

    def test_extracts_chat_topic(self, normalizer, sample_message):
        """Test that chat topic is extracted"""
        event = normalizer.normalize(sample_message)

        assert "Project Alpha" in event.topics

    def test_extracts_important_keywords(self, normalizer, sample_sender):
        """Test extraction of important keywords"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="URGENT: Meeting deadline review needed",
            content_plain="URGENT: Meeting deadline review needed",
            created_at=datetime.now(timezone.utc),
        )

        event = normalizer.normalize(message)

        # Should extract keywords like urgent, meeting, deadline, review
        assert any(kw in event.keywords for kw in ["urgent", "meeting", "deadline", "review"])
