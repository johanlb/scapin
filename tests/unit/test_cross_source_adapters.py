"""
Unit tests for CrossSource adapters (Calendar and Teams).

Tests the adapter implementations for calendar and teams data sources.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.passepartout.cross_source.adapters.calendar_adapter import CalendarAdapter
from src.passepartout.cross_source.adapters.teams_adapter import TeamsAdapter
from src.passepartout.cross_source.config import (
    CalendarAdapterConfig,
    TeamsAdapterConfig,
)


# =============================================================================
# Calendar Adapter Tests
# =============================================================================


class TestCalendarAdapter:
    """Tests for CalendarAdapter."""

    def test_init_without_client(self):
        """Test adapter initialization without client."""
        adapter = CalendarAdapter()
        assert adapter.source_name == "calendar"
        assert adapter.is_available is False

    def test_init_with_client(self):
        """Test adapter initialization with client."""
        mock_client = MagicMock()
        adapter = CalendarAdapter(calendar_client=mock_client)
        assert adapter.is_available is True

    def test_source_name(self):
        """Test source name property."""
        adapter = CalendarAdapter()
        assert adapter.source_name == "calendar"

    @pytest.mark.asyncio
    async def test_search_not_available(self):
        """Test search when adapter not available."""
        adapter = CalendarAdapter()
        result = await adapter.search("test query")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Test successful search returning results."""
        # Create mock calendar client
        mock_client = AsyncMock()

        # Create mock event
        mock_event = MagicMock()
        mock_event.event_id = "event-123"
        mock_event.calendar_id = "cal-123"
        mock_event.subject = "Budget Meeting"
        mock_event.body_preview = "Discuss Q1 budget allocations"
        mock_event.body_content = "Full discussion content"
        mock_event.start = datetime.now(timezone.utc)
        mock_event.end = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_event.is_all_day = False
        mock_event.is_online_meeting = True
        mock_event.online_meeting_url = "https://teams.microsoft.com/meet/123"
        mock_event.web_link = "https://outlook.office.com/calendar/item/123"
        mock_event.categories = []

        mock_organizer = MagicMock()
        mock_organizer.display_name = "John Doe"
        mock_organizer.email = "john@example.com"
        mock_event.organizer = mock_organizer

        mock_attendee = MagicMock()
        mock_attendee.display_name = "Jane Smith"
        mock_attendee.email = "jane@example.com"
        mock_event.attendees = [mock_attendee]

        mock_location = MagicMock()
        mock_location.display_name = "Conference Room A"
        mock_event.location = mock_location

        mock_importance = MagicMock()
        mock_importance.value = "normal"
        mock_event.importance = mock_importance

        mock_client.get_events.return_value = [mock_event]

        adapter = CalendarAdapter(calendar_client=mock_client)
        result = await adapter.search("budget")

        assert len(result) == 1
        assert result[0].source == "calendar"
        assert result[0].type == "event"
        assert "Budget Meeting" in result[0].title
        assert result[0].metadata["event_id"] == "event-123"
        assert result[0].metadata["is_online"] is True

    @pytest.mark.asyncio
    async def test_search_filters_by_query(self):
        """Test that search filters events by query."""
        mock_client = AsyncMock()

        # Create events - one matching, one not
        def create_event(subject: str, body: str) -> MagicMock:
            event = MagicMock()
            event.event_id = f"event-{subject}"
            event.calendar_id = "cal-123"
            event.subject = subject
            event.body_preview = body
            event.body_content = body
            event.start = datetime.now(timezone.utc)
            event.end = datetime.now(timezone.utc) + timedelta(hours=1)
            event.is_all_day = False
            event.is_online_meeting = False
            event.online_meeting_url = None
            event.categories = []
            event.organizer = None
            event.attendees = []
            event.location = None
            event.importance = MagicMock(value="normal")
            return event

        matching_event = create_event("Budget Review", "Q1 finances")
        non_matching_event = create_event("Team Lunch", "Food planning")

        mock_client.get_events.return_value = [matching_event, non_matching_event]

        adapter = CalendarAdapter(calendar_client=mock_client)
        result = await adapter.search("budget")

        assert len(result) == 1
        assert "Budget" in result[0].title

    @pytest.mark.asyncio
    async def test_search_matches_organizer(self):
        """Test that search matches organizer name."""
        mock_client = AsyncMock()

        event = MagicMock()
        event.event_id = "event-123"
        event.calendar_id = "cal-123"
        event.subject = "Regular Meeting"
        event.body_preview = ""
        event.body_content = ""
        event.start = datetime.now(timezone.utc)
        event.end = datetime.now(timezone.utc) + timedelta(hours=1)
        event.is_all_day = False
        event.is_online_meeting = False
        event.online_meeting_url = None
        event.categories = []
        event.attendees = []
        event.location = None
        event.importance = MagicMock(value="normal")

        organizer = MagicMock()
        organizer.display_name = "Alice Johnson"
        organizer.email = "alice@example.com"
        event.organizer = organizer

        mock_client.get_events.return_value = [event]

        adapter = CalendarAdapter(calendar_client=mock_client)
        result = await adapter.search("alice")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_matches_attendee(self):
        """Test that search matches attendee name."""
        mock_client = AsyncMock()

        event = MagicMock()
        event.event_id = "event-123"
        event.calendar_id = "cal-123"
        event.subject = "Regular Meeting"
        event.body_preview = ""
        event.body_content = ""
        event.start = datetime.now(timezone.utc)
        event.end = datetime.now(timezone.utc) + timedelta(hours=1)
        event.is_all_day = False
        event.is_online_meeting = False
        event.online_meeting_url = None
        event.categories = []
        event.organizer = None
        event.location = None
        event.importance = MagicMock(value="normal")

        attendee = MagicMock()
        attendee.display_name = "Bob Wilson"
        attendee.email = "bob@example.com"
        event.attendees = [attendee]

        mock_client.get_events.return_value = [event]

        adapter = CalendarAdapter(calendar_client=mock_client)
        result = await adapter.search("bob")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_with_config(self):
        """Test search with adapter configuration."""
        mock_client = AsyncMock()
        mock_client.get_events.return_value = []

        config = CalendarAdapterConfig(
            past_days=90,
            future_days=30,
        )

        adapter = CalendarAdapter(
            calendar_client=mock_client,
            adapter_config=config,
        )

        await adapter.search("test")

        # With parallel fetch, get_events is called twice (past + future)
        assert mock_client.get_events.call_count == 2

        # Verify past_days and future_days were used in separate calls
        all_calls = mock_client.get_events.call_args_list
        past_call = [c for c in all_calls if c.kwargs.get("days_behind", 0) > 0]
        future_call = [c for c in all_calls if c.kwargs.get("days_ahead", 0) > 0]

        assert len(past_call) == 1
        assert past_call[0].kwargs["days_behind"] == 90
        assert past_call[0].kwargs["days_ahead"] == 0

        assert len(future_call) == 1
        assert future_call[0].kwargs["days_ahead"] == 30
        assert future_call[0].kwargs["days_behind"] == 0

    @pytest.mark.asyncio
    async def test_search_handles_exception(self):
        """Test that search handles exceptions gracefully."""
        mock_client = AsyncMock()
        mock_client.get_events.side_effect = Exception("API Error")

        adapter = CalendarAdapter(calendar_client=mock_client)
        result = await adapter.search("test")

        assert result == []

    def test_relevance_calculation_subject_match(self):
        """Test relevance calculation for subject match."""
        adapter = CalendarAdapter()

        event = MagicMock()
        event.subject = "Budget Meeting"
        event.body_preview = ""
        event.organizer = None
        event.attendees = []
        event.start = datetime.now(timezone.utc)

        score = adapter._calculate_relevance(event, "budget")

        # Subject match should boost score
        assert score > 0.7

    def test_relevance_calculation_recency(self):
        """Test relevance calculation for recent events."""
        adapter = CalendarAdapter()

        recent_event = MagicMock()
        recent_event.subject = "Meeting"
        recent_event.body_preview = ""
        recent_event.organizer = None
        recent_event.attendees = []
        recent_event.start = datetime.now(timezone.utc)

        old_event = MagicMock()
        old_event.subject = "Meeting"
        old_event.body_preview = ""
        old_event.organizer = None
        old_event.attendees = []
        old_event.start = datetime.now(timezone.utc) - timedelta(days=120)

        recent_score = adapter._calculate_relevance(recent_event, "meeting")
        old_score = adapter._calculate_relevance(old_event, "meeting")

        assert recent_score > old_score


# =============================================================================
# Teams Adapter Tests
# =============================================================================


class TestTeamsAdapter:
    """Tests for TeamsAdapter."""

    def test_init_without_client(self):
        """Test adapter initialization without client."""
        adapter = TeamsAdapter()
        assert adapter.source_name == "teams"
        assert adapter.is_available is False

    def test_init_with_client(self):
        """Test adapter initialization with client."""
        mock_client = MagicMock()
        adapter = TeamsAdapter(teams_client=mock_client)
        assert adapter.is_available is True

    def test_source_name(self):
        """Test source name property."""
        adapter = TeamsAdapter()
        assert adapter.source_name == "teams"

    @pytest.mark.asyncio
    async def test_search_not_available(self):
        """Test search when adapter not available."""
        adapter = TeamsAdapter()
        result = await adapter.search("test query")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Test successful search returning results."""
        mock_client = AsyncMock()

        # Create mock message
        mock_sender = MagicMock()
        mock_sender.user_id = "user-123"
        mock_sender.display_name = "John Doe"
        mock_sender.email = "john@example.com"

        mock_chat = MagicMock()
        mock_chat.chat_id = "chat-123"
        mock_chat.topic = "Project Discussion"
        mock_chat.chat_type = MagicMock(value="group")
        mock_chat.members = []

        mock_message = MagicMock()
        mock_message.message_id = "msg-123"
        mock_message.chat_id = "chat-123"
        mock_message.sender = mock_sender
        mock_message.content_plain = "Here's the project update for Q1"
        mock_message.created_at = datetime.now(timezone.utc)
        mock_message.importance = MagicMock(value="normal")
        mock_message.mentions = []
        mock_message.attachments = ()
        mock_message.is_reply = False
        mock_message.chat = mock_chat

        mock_client.get_recent_messages.return_value = [mock_message]

        adapter = TeamsAdapter(teams_client=mock_client)
        result = await adapter.search("project")

        assert len(result) == 1
        assert result[0].source == "teams"
        assert result[0].type == "message"
        assert result[0].metadata["message_id"] == "msg-123"
        assert result[0].metadata["sender_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_search_filters_by_content(self):
        """Test that search filters messages by content."""
        mock_client = AsyncMock()

        def create_message(content: str) -> MagicMock:
            sender = MagicMock()
            sender.user_id = "user-123"
            sender.display_name = "User"
            sender.email = "user@example.com"

            msg = MagicMock()
            msg.message_id = f"msg-{hash(content)}"
            msg.chat_id = "chat-123"
            msg.sender = sender
            msg.content_plain = content
            msg.created_at = datetime.now(timezone.utc)
            msg.importance = MagicMock(value="normal")
            msg.mentions = []
            msg.attachments = ()
            msg.is_reply = False
            msg.chat = None
            return msg

        matching = create_message("The budget report is ready")
        non_matching = create_message("Let's have lunch")

        mock_client.get_recent_messages.return_value = [matching, non_matching]

        adapter = TeamsAdapter(teams_client=mock_client)
        result = await adapter.search("budget")

        assert len(result) == 1
        assert "budget" in result[0].content.lower()

    @pytest.mark.asyncio
    async def test_search_matches_sender(self):
        """Test that search matches sender name."""
        mock_client = AsyncMock()

        sender = MagicMock()
        sender.user_id = "user-123"
        sender.display_name = "Alice Smith"
        sender.email = "alice@example.com"

        message = MagicMock()
        message.message_id = "msg-123"
        message.chat_id = "chat-123"
        message.sender = sender
        message.content_plain = "Hello everyone"
        message.created_at = datetime.now(timezone.utc)
        message.importance = MagicMock(value="normal")
        message.mentions = []
        message.attachments = ()
        message.is_reply = False
        message.chat = None

        mock_client.get_recent_messages.return_value = [message]

        adapter = TeamsAdapter(teams_client=mock_client)
        result = await adapter.search("alice")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_matches_chat_topic(self):
        """Test that search matches chat topic."""
        mock_client = AsyncMock()

        sender = MagicMock()
        sender.user_id = "user-123"
        sender.display_name = "User"
        sender.email = "user@example.com"

        chat = MagicMock()
        chat.chat_id = "chat-123"
        chat.topic = "Marketing Campaign"
        chat.chat_type = MagicMock(value="group")
        chat.members = []

        message = MagicMock()
        message.message_id = "msg-123"
        message.chat_id = "chat-123"
        message.sender = sender
        message.content_plain = "Hello"
        message.created_at = datetime.now(timezone.utc)
        message.importance = MagicMock(value="normal")
        message.mentions = []
        message.attachments = ()
        message.is_reply = False
        message.chat = chat

        mock_client.get_recent_messages.return_value = [message]

        adapter = TeamsAdapter(teams_client=mock_client)
        result = await adapter.search("marketing")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_with_chat_filter(self):
        """Test search with chat filter context."""
        mock_client = AsyncMock()

        def create_message_with_chat(chat_topic: str) -> MagicMock:
            sender = MagicMock()
            sender.user_id = "user-123"
            sender.display_name = "User"
            sender.email = "user@example.com"

            chat = MagicMock()
            chat.chat_id = f"chat-{chat_topic}"
            chat.topic = chat_topic
            chat.chat_type = MagicMock(value="group")
            chat.members = []

            msg = MagicMock()
            msg.message_id = f"msg-{chat_topic}"
            msg.chat_id = chat.chat_id
            msg.sender = sender
            msg.content_plain = "Important update"
            msg.created_at = datetime.now(timezone.utc)
            msg.importance = MagicMock(value="normal")
            msg.mentions = []
            msg.attachments = ()
            msg.is_reply = False
            msg.chat = chat
            return msg

        msg1 = create_message_with_chat("Sales Team")
        msg2 = create_message_with_chat("Engineering")

        mock_client.get_recent_messages.return_value = [msg1, msg2]

        adapter = TeamsAdapter(teams_client=mock_client)
        result = await adapter.search("update", context={"chat_filter": "Sales"})

        assert len(result) == 1
        assert result[0].metadata["chat_topic"] == "Sales Team"

    @pytest.mark.asyncio
    async def test_search_handles_exception(self):
        """Test that search handles exceptions gracefully."""
        mock_client = AsyncMock()
        mock_client.get_recent_messages.side_effect = Exception("API Error")

        adapter = TeamsAdapter(teams_client=mock_client)
        result = await adapter.search("test")

        assert result == []

    def test_relevance_calculation_content_match(self):
        """Test relevance calculation for content match."""
        adapter = TeamsAdapter()

        sender = MagicMock()
        sender.display_name = "User"
        sender.email = None

        message = MagicMock()
        message.content_plain = "The budget report is complete"
        message.sender = sender
        message.chat = None
        message.importance = MagicMock(value="normal")
        message.mentions = []
        message.created_at = datetime.now(timezone.utc)

        score = adapter._calculate_relevance(message, "budget")

        # Content match should boost score
        assert score > 0.6

    def test_relevance_calculation_importance(self):
        """Test relevance calculation for high importance messages."""
        adapter = TeamsAdapter()

        sender = MagicMock()
        sender.display_name = "User"
        sender.email = None

        normal_msg = MagicMock()
        normal_msg.content_plain = "Update"
        normal_msg.sender = sender
        normal_msg.chat = None
        normal_msg.importance = MagicMock(value="normal")
        normal_msg.mentions = []
        normal_msg.created_at = datetime.now(timezone.utc)

        urgent_msg = MagicMock()
        urgent_msg.content_plain = "Update"
        urgent_msg.sender = sender
        urgent_msg.chat = None
        urgent_msg.importance = MagicMock(value="urgent")
        urgent_msg.mentions = []
        urgent_msg.created_at = datetime.now(timezone.utc)

        normal_score = adapter._calculate_relevance(normal_msg, "update")
        urgent_score = adapter._calculate_relevance(urgent_msg, "update")

        assert urgent_score > normal_score

    def test_relevance_calculation_recency(self):
        """Test relevance calculation for recent messages."""
        adapter = TeamsAdapter()

        sender = MagicMock()
        sender.display_name = "User"
        sender.email = None

        recent_msg = MagicMock()
        recent_msg.content_plain = "Update"
        recent_msg.sender = sender
        recent_msg.chat = None
        recent_msg.importance = MagicMock(value="normal")
        recent_msg.mentions = []
        recent_msg.created_at = datetime.now(timezone.utc)

        old_msg = MagicMock()
        old_msg.content_plain = "Update"
        old_msg.sender = sender
        old_msg.chat = None
        old_msg.importance = MagicMock(value="normal")
        old_msg.mentions = []
        old_msg.created_at = datetime.now(timezone.utc) - timedelta(days=120)

        recent_score = adapter._calculate_relevance(recent_msg, "update")
        old_score = adapter._calculate_relevance(old_msg, "update")

        assert recent_score > old_score

    def test_relevance_calculation_with_mentions(self):
        """Test relevance calculation for messages with mentions."""
        adapter = TeamsAdapter()

        sender = MagicMock()
        sender.display_name = "User"
        sender.email = None

        no_mentions_msg = MagicMock()
        no_mentions_msg.content_plain = "Update"
        no_mentions_msg.sender = sender
        no_mentions_msg.chat = None
        no_mentions_msg.importance = MagicMock(value="normal")
        no_mentions_msg.mentions = []
        no_mentions_msg.created_at = datetime.now(timezone.utc)

        with_mentions_msg = MagicMock()
        with_mentions_msg.content_plain = "Update"
        with_mentions_msg.sender = sender
        with_mentions_msg.chat = None
        with_mentions_msg.importance = MagicMock(value="normal")
        with_mentions_msg.mentions = ["user-123"]
        with_mentions_msg.created_at = datetime.now(timezone.utc)

        no_mentions_score = adapter._calculate_relevance(no_mentions_msg, "update")
        with_mentions_score = adapter._calculate_relevance(with_mentions_msg, "update")

        assert with_mentions_score > no_mentions_score


# =============================================================================
# Adapter Integration Tests
# =============================================================================


class TestAdapterIntegration:
    """Integration tests for adapters."""

    @pytest.mark.asyncio
    async def test_calendar_adapter_with_config(self):
        """Test calendar adapter respects configuration."""
        mock_client = AsyncMock()
        mock_client.get_events.return_value = []

        config = CalendarAdapterConfig(
            enabled=True,
            past_days=180,
            future_days=60,
        )

        adapter = CalendarAdapter(
            calendar_client=mock_client,
            adapter_config=config,
        )

        # Use custom context
        await adapter.search(
            "test",
            context={
                "include_past": True,
                "include_future": True,
            },
        )

        # With parallel fetch, get_events is called twice
        assert mock_client.get_events.call_count == 2

        # Verify config values were used in separate calls
        all_calls = mock_client.get_events.call_args_list
        past_call = [c for c in all_calls if c.kwargs.get("days_behind", 0) > 0]
        future_call = [c for c in all_calls if c.kwargs.get("days_ahead", 0) > 0]

        assert len(past_call) == 1
        assert past_call[0].kwargs["days_behind"] == 180

        assert len(future_call) == 1
        assert future_call[0].kwargs["days_ahead"] == 60

    @pytest.mark.asyncio
    async def test_teams_adapter_with_config(self):
        """Test teams adapter respects configuration."""
        mock_client = AsyncMock()
        mock_client.get_recent_messages.return_value = []

        config = TeamsAdapterConfig(
            enabled=True,
            include_all_chats=True,
        )

        adapter = TeamsAdapter(
            teams_client=mock_client,
            adapter_config=config,
        )

        await adapter.search("test")

        assert mock_client.get_recent_messages.called

    @pytest.mark.asyncio
    async def test_adapters_return_source_items(self):
        """Test that all adapters return valid SourceItem objects."""
        # Calendar adapter
        cal_client = AsyncMock()
        cal_event = MagicMock()
        cal_event.event_id = "event-1"
        cal_event.calendar_id = "cal-1"
        cal_event.subject = "Test Event"
        cal_event.body_preview = ""
        cal_event.body_content = ""
        cal_event.start = datetime.now(timezone.utc)
        cal_event.end = datetime.now(timezone.utc) + timedelta(hours=1)
        cal_event.is_all_day = False
        cal_event.is_online_meeting = False
        cal_event.online_meeting_url = None
        cal_event.categories = []
        cal_event.organizer = None
        cal_event.attendees = []
        cal_event.location = None
        cal_event.importance = MagicMock(value="normal")

        cal_client.get_events.return_value = [cal_event]

        cal_adapter = CalendarAdapter(calendar_client=cal_client)
        cal_results = await cal_adapter.search("test")

        assert len(cal_results) == 1
        assert cal_results[0].source == "calendar"
        assert cal_results[0].type == "event"
        assert 0.0 <= cal_results[0].relevance_score <= 1.0

        # Teams adapter
        teams_client = AsyncMock()
        teams_sender = MagicMock()
        teams_sender.user_id = "user-1"
        teams_sender.display_name = "Test User"
        teams_sender.email = "test@example.com"

        teams_msg = MagicMock()
        teams_msg.message_id = "msg-1"
        teams_msg.chat_id = "chat-1"
        teams_msg.sender = teams_sender
        teams_msg.content_plain = "Test message"
        teams_msg.created_at = datetime.now(timezone.utc)
        teams_msg.importance = MagicMock(value="normal")
        teams_msg.mentions = []
        teams_msg.attachments = ()
        teams_msg.is_reply = False
        teams_msg.chat = None

        teams_client.get_recent_messages.return_value = [teams_msg]

        teams_adapter = TeamsAdapter(teams_client=teams_client)
        teams_results = await teams_adapter.search("test")

        assert len(teams_results) == 1
        assert teams_results[0].source == "teams"
        assert teams_results[0].type == "message"
        assert 0.0 <= teams_results[0].relevance_score <= 1.0
