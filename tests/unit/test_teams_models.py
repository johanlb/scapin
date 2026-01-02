"""
Unit Tests for Teams Models

Tests TeamsMessage, TeamsChat, TeamsSender dataclasses.
"""

from datetime import datetime, timezone

import pytest

from src.integrations.microsoft.models import (
    TeamsChat,
    TeamsChatType,
    TeamsMessage,
    TeamsMessageImportance,
    TeamsSender,
    _extract_plain_text,
)


class TestTeamsSender:
    """Tests for TeamsSender dataclass"""

    def test_create_sender_with_required_fields(self):
        """Test creating sender with minimum required fields"""
        sender = TeamsSender(
            user_id="user-123",
            display_name="John Doe",
        )

        assert sender.user_id == "user-123"
        assert sender.display_name == "John Doe"
        assert sender.email is None

    def test_create_sender_with_all_fields(self):
        """Test creating sender with all fields"""
        sender = TeamsSender(
            user_id="user-456",
            display_name="Jane Doe",
            email="jane.doe@example.com",
        )

        assert sender.user_id == "user-456"
        assert sender.display_name == "Jane Doe"
        assert sender.email == "jane.doe@example.com"

    def test_sender_is_frozen(self):
        """Test that TeamsSender is immutable"""
        sender = TeamsSender(
            user_id="user-123",
            display_name="John Doe",
        )

        with pytest.raises(AttributeError):
            sender.display_name = "New Name"

    def test_sender_equality(self):
        """Test TeamsSender equality comparison"""
        sender1 = TeamsSender(user_id="user-123", display_name="John Doe")
        sender2 = TeamsSender(user_id="user-123", display_name="John Doe")
        sender3 = TeamsSender(user_id="user-456", display_name="Jane Doe")

        assert sender1 == sender2
        assert sender1 != sender3


class TestTeamsChat:
    """Tests for TeamsChat dataclass"""

    def test_create_one_on_one_chat(self):
        """Test creating a 1:1 chat"""
        created_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        chat = TeamsChat(
            chat_id="chat-abc",
            chat_type=TeamsChatType.ONE_ON_ONE,
            created_at=created_at,
        )

        assert chat.chat_id == "chat-abc"
        assert chat.chat_type == TeamsChatType.ONE_ON_ONE
        assert chat.topic is None
        assert chat.members == ()
        assert chat.created_at == created_at

    def test_create_group_chat_with_topic(self):
        """Test creating a group chat with topic"""
        created_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        members = (
            TeamsSender(user_id="user-1", display_name="User 1"),
            TeamsSender(user_id="user-2", display_name="User 2"),
        )

        chat = TeamsChat(
            chat_id="chat-xyz",
            chat_type=TeamsChatType.GROUP,
            topic="Project Discussion",
            members=members,
            created_at=created_at,
        )

        assert chat.chat_id == "chat-xyz"
        assert chat.chat_type == TeamsChatType.GROUP
        assert chat.topic == "Project Discussion"
        assert len(chat.members) == 2
        assert chat.members[0].display_name == "User 1"

    def test_create_meeting_chat(self):
        """Test creating a meeting chat"""
        created_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        chat = TeamsChat(
            chat_id="meeting-123",
            chat_type=TeamsChatType.MEETING,
            topic="Weekly Standup",
            created_at=created_at,
        )

        assert chat.chat_type == TeamsChatType.MEETING
        assert chat.topic == "Weekly Standup"

    def test_chat_is_frozen(self):
        """Test that TeamsChat is immutable"""
        chat = TeamsChat(
            chat_id="chat-123",
            chat_type=TeamsChatType.GROUP,
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(AttributeError):
            chat.topic = "New Topic"


class TestTeamsChatType:
    """Tests for TeamsChatType enum"""

    def test_chat_type_values(self):
        """Test enum values"""
        assert TeamsChatType.ONE_ON_ONE.value == "oneOnOne"
        assert TeamsChatType.GROUP.value == "group"
        assert TeamsChatType.MEETING.value == "meeting"

    def test_chat_type_from_string(self):
        """Test creating enum from string value"""
        assert TeamsChatType("oneOnOne") == TeamsChatType.ONE_ON_ONE
        assert TeamsChatType("group") == TeamsChatType.GROUP
        assert TeamsChatType("meeting") == TeamsChatType.MEETING


class TestTeamsMessageImportance:
    """Tests for TeamsMessageImportance enum"""

    def test_importance_values(self):
        """Test enum values"""
        assert TeamsMessageImportance.NORMAL.value == "normal"
        assert TeamsMessageImportance.HIGH.value == "high"
        assert TeamsMessageImportance.URGENT.value == "urgent"


class TestTeamsMessage:
    """Tests for TeamsMessage dataclass"""

    @pytest.fixture
    def sample_sender(self):
        """Create sample sender"""
        return TeamsSender(
            user_id="sender-123",
            display_name="Test User",
            email="test@example.com",
        )

    @pytest.fixture
    def sample_chat(self):
        """Create sample chat"""
        return TeamsChat(
            chat_id="chat-456",
            chat_type=TeamsChatType.GROUP,
            topic="Test Chat",
            created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )

    def test_create_message_minimal(self, sample_sender):
        """Test creating message with minimum required fields"""
        created_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)

        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="<p>Hello World</p>",
            content_plain="Hello World",
            created_at=created_at,
        )

        assert message.message_id == "msg-001"
        assert message.chat_id == "chat-123"
        assert message.sender == sample_sender
        assert message.content == "<p>Hello World</p>"
        assert message.content_plain == "Hello World"
        assert message.created_at == created_at
        assert message.importance == TeamsMessageImportance.NORMAL
        assert message.mentions == ()
        assert message.attachments == ()
        assert message.is_reply is False
        assert message.reply_to_id is None
        assert message.chat is None

    def test_create_message_with_all_fields(self, sample_sender, sample_chat):
        """Test creating message with all fields"""
        created_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)

        message = TeamsMessage(
            message_id="msg-002",
            chat_id="chat-456",
            sender=sample_sender,
            content="<p>@user1 Check this <a href='https://example.com'>link</a></p>",
            content_plain="@user1 Check this link",
            created_at=created_at,
            importance=TeamsMessageImportance.HIGH,
            mentions=("user-1", "user-2"),
            attachments=("report.pdf", "data.xlsx"),
            is_reply=True,
            reply_to_id="msg-001",
            chat=sample_chat,
        )

        assert message.importance == TeamsMessageImportance.HIGH
        assert len(message.mentions) == 2
        assert "user-1" in message.mentions
        assert len(message.attachments) == 2
        assert "report.pdf" in message.attachments
        assert message.is_reply is True
        assert message.reply_to_id == "msg-001"
        assert message.chat == sample_chat

    def test_message_is_frozen(self, sample_sender):
        """Test that TeamsMessage is immutable"""
        message = TeamsMessage(
            message_id="msg-001",
            chat_id="chat-123",
            sender=sample_sender,
            content="Hello",
            content_plain="Hello",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(AttributeError):
            message.content = "New content"

    def test_urgent_message(self, sample_sender):
        """Test creating urgent message"""
        message = TeamsMessage(
            message_id="msg-urgent",
            chat_id="chat-123",
            sender=sample_sender,
            content="URGENT: Please respond ASAP",
            content_plain="URGENT: Please respond ASAP",
            created_at=datetime.now(timezone.utc),
            importance=TeamsMessageImportance.URGENT,
        )

        assert message.importance == TeamsMessageImportance.URGENT

    def test_message_with_mentions(self, sample_sender):
        """Test message with @mentions"""
        message = TeamsMessage(
            message_id="msg-mention",
            chat_id="chat-123",
            sender=sample_sender,
            content="@alice @bob Please review",
            content_plain="@alice @bob Please review",
            created_at=datetime.now(timezone.utc),
            mentions=("alice-id", "bob-id"),
        )

        assert len(message.mentions) == 2
        assert "alice-id" in message.mentions
        assert "bob-id" in message.mentions


class TestExtractPlainText:
    """Tests for _extract_plain_text helper function"""

    def test_extract_simple_html(self):
        """Test extracting text from simple HTML"""
        html = "<p>Hello World</p>"
        result = _extract_plain_text(html)
        assert result == "Hello World"

    def test_extract_nested_html(self):
        """Test extracting text from nested HTML"""
        html = "<div><p>Line 1</p><p>Line 2</p></div>"
        result = _extract_plain_text(html)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_extract_with_links(self):
        """Test extracting text with links"""
        html = '<p>Check <a href="https://example.com">this link</a></p>'
        result = _extract_plain_text(html)
        assert "Check" in result
        assert "this link" in result
        assert "https://example.com" not in result

    def test_extract_empty_string(self):
        """Test extracting text from empty string"""
        result = _extract_plain_text("")
        assert result == ""

    def test_extract_plain_text_passthrough(self):
        """Test that plain text passes through unchanged"""
        text = "Plain text without HTML"
        result = _extract_plain_text(text)
        assert result == text

    def test_extract_handles_br_tags(self):
        """Test handling of br tags"""
        html = "Line 1<br/>Line 2<br>Line 3"
        result = _extract_plain_text(html)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_extract_special_characters(self):
        """Test handling of HTML entities"""
        html = "<p>A &amp; B &lt; C &gt; D</p>"
        result = _extract_plain_text(html)
        # Should decode HTML entities
        assert "A" in result
        assert "B" in result
