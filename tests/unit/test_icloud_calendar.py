"""
Unit tests for iCloud Calendar integration.

Tests the models, client, and cross-source adapter.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.apple.calendar_client import (
    ICloudCalendarClient,
    ICloudCalendarConfig,
)
from src.integrations.apple.calendar_models import (
    ICloudAttendee,
    ICloudAttendeeStatus,
    ICloudCalendar,
    ICloudCalendarEvent,
    ICloudCalendarSearchResult,
)
from src.passepartout.cross_source.adapters.icloud_calendar_adapter import (
    ICloudCalendarAdapter,
)
from src.passepartout.cross_source.config import ICloudCalendarAdapterConfig

# ============================================================================
# Model Tests
# ============================================================================


class TestICloudAttendee:
    """Tests for ICloudAttendee model"""

    def test_create_attendee(self):
        """Test creating an attendee"""
        attendee = ICloudAttendee(
            name="John Doe",
            email="john@example.com",
            status=ICloudAttendeeStatus.ACCEPTED,
            is_organizer=True,
        )
        assert attendee.name == "John Doe"
        assert attendee.email == "john@example.com"
        assert attendee.status == ICloudAttendeeStatus.ACCEPTED
        assert attendee.is_organizer is True

    def test_attendee_to_dict(self):
        """Test attendee serialization"""
        attendee = ICloudAttendee(
            name="Jane Doe",
            email="jane@example.com",
            status=ICloudAttendeeStatus.TENTATIVE,
        )
        data = attendee.to_dict()
        assert data["name"] == "Jane Doe"
        assert data["email"] == "jane@example.com"
        assert data["status"] == "tentative"
        assert data["is_organizer"] is False


class TestICloudCalendar:
    """Tests for ICloudCalendar model"""

    def test_create_calendar(self):
        """Test creating a calendar"""
        calendar = ICloudCalendar(
            name="Work",
            uid="calendar-123",
            color="#FF0000",
            is_writable=True,
        )
        assert calendar.name == "Work"
        assert calendar.uid == "calendar-123"
        assert calendar.color == "#FF0000"
        assert calendar.is_writable is True

    def test_calendar_to_dict(self):
        """Test calendar serialization"""
        calendar = ICloudCalendar(name="Personal")
        data = calendar.to_dict()
        assert data["name"] == "Personal"
        assert data["is_writable"] is True


class TestICloudCalendarEvent:
    """Tests for ICloudCalendarEvent model"""

    @pytest.fixture
    def sample_event(self):
        """Create a sample event for testing"""
        # Use a future date (7 days from now) to ensure is_past is False
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        return ICloudCalendarEvent(
            uid="event-123",
            summary="Team Meeting",
            start_date=future_date.replace(hour=10, minute=0, second=0, microsecond=0),
            end_date=future_date.replace(hour=11, minute=0, second=0, microsecond=0),
            calendar_name="Work",
            description="Weekly sync",
            location="Zoom",
            attendees=[
                ICloudAttendee(name="Alice", email="alice@example.com"),
                ICloudAttendee(name="Bob", email="bob@example.com"),
            ],
            organizer=ICloudAttendee(
                name="Alice",
                email="alice@example.com",
                is_organizer=True,
            ),
        )

    def test_duration_minutes(self, sample_event):
        """Test duration calculation"""
        assert sample_event.duration_minutes == 60

    def test_all_day_duration(self):
        """Test all-day event duration"""
        event = ICloudCalendarEvent(
            uid="all-day-123",
            summary="Holiday",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 2, tzinfo=timezone.utc),
            is_all_day=True,
        )
        assert event.duration_minutes == 24 * 60

    def test_is_past(self, sample_event):
        """Test is_past property"""
        # Event in the past
        past_event = ICloudCalendarEvent(
            uid="past-123",
            summary="Old Meeting",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        )
        assert past_event.is_past is True

        # Future event (2026)
        assert sample_event.is_past is False

    def test_is_online_meeting(self):
        """Test online meeting detection"""
        # Zoom meeting
        event1 = ICloudCalendarEvent(
            uid="zoom-123",
            summary="Zoom Call",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            location="https://zoom.us/j/123456",
        )
        assert event1.is_online_meeting is True

        # Teams meeting
        event2 = ICloudCalendarEvent(
            uid="teams-123",
            summary="Teams Meeting",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            url="https://teams.microsoft.com/l/meetup-join/...",
        )
        assert event2.is_online_meeting is True

        # In-person meeting
        event3 = ICloudCalendarEvent(
            uid="inperson-123",
            summary="Coffee Chat",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            location="Starbucks",
        )
        assert event3.is_online_meeting is False

    def test_to_dict(self, sample_event):
        """Test event serialization"""
        data = sample_event.to_dict()
        assert data["uid"] == "event-123"
        assert data["summary"] == "Team Meeting"
        assert data["calendar_name"] == "Work"
        assert data["duration_minutes"] == 60
        assert len(data["attendees"]) == 2
        assert data["organizer"]["name"] == "Alice"


class TestICloudCalendarSearchResult:
    """Tests for ICloudCalendarSearchResult model"""

    def test_empty_result(self):
        """Test empty search result"""
        result = ICloudCalendarSearchResult()
        assert len(result.events) == 0
        assert result.total_found == 0

    def test_result_with_events(self):
        """Test search result with events"""
        events = [
            ICloudCalendarEvent(
                uid=f"event-{i}",
                summary=f"Event {i}",
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            for i in range(3)
        ]
        result = ICloudCalendarSearchResult(
            events=events,
            calendars_searched=["Work", "Personal"],
            total_found=3,
            query="meeting",
        )
        assert len(result.events) == 3
        assert result.total_found == 3
        assert "Work" in result.calendars_searched


# ============================================================================
# Client Tests
# ============================================================================


class TestICloudCalendarClient:
    """Tests for ICloudCalendarClient"""

    @pytest.fixture
    def client_config(self):
        """Create test config"""
        return ICloudCalendarConfig(
            username="test@icloud.com",
            app_specific_password="xxxx-xxxx-xxxx-xxxx",
        )

    def test_client_not_configured(self):
        """Test client behavior when not configured"""
        client = ICloudCalendarClient()
        assert client.is_configured is False
        assert client.is_available() is False

    def test_client_configured(self, client_config):
        """Test client with configuration"""
        client = ICloudCalendarClient(client_config)
        assert client.is_configured is True

    def test_configure_after_init(self, client_config):
        """Test configuring client after initialization"""
        client = ICloudCalendarClient()
        assert client.is_configured is False

        client.configure(client_config)
        assert client.is_configured is True

    @patch("caldav.DAVClient")
    def test_connect_success(self, mock_dav_client, client_config):
        """Test successful connection"""
        mock_client = MagicMock()
        mock_principal = MagicMock()
        mock_dav_client.return_value = mock_client
        mock_client.principal.return_value = mock_principal

        client = ICloudCalendarClient(client_config)
        assert client.is_available() is True

    @patch("caldav.DAVClient")
    def test_connect_failure(self, mock_dav_client, client_config):
        """Test connection failure"""
        mock_dav_client.side_effect = Exception("Connection failed")

        client = ICloudCalendarClient(client_config)
        assert client.is_available() is False

    @patch("caldav.DAVClient")
    def test_get_calendars(self, mock_dav_client, client_config):
        """Test getting calendars"""
        mock_cal1 = MagicMock()
        mock_cal1.name = "Work"
        mock_cal1.url = "https://caldav.icloud.com/123/work"

        mock_cal2 = MagicMock()
        mock_cal2.name = "Personal"
        mock_cal2.url = "https://caldav.icloud.com/123/personal"

        mock_principal = MagicMock()
        mock_principal.calendars.return_value = [mock_cal1, mock_cal2]

        mock_client = MagicMock()
        mock_client.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client

        client = ICloudCalendarClient(client_config)
        calendars = client.get_calendars()

        assert len(calendars) == 2
        assert calendars[0].name == "Work"
        assert calendars[1].name == "Personal"

    @patch("caldav.DAVClient")
    def test_search_events(self, mock_dav_client, client_config):
        """Test searching events"""
        # Create mock iCalendar component
        mock_ical = MagicMock()
        mock_ical.get.side_effect = lambda key, default=None: {
            "uid": "event-123",
            "summary": "Team Meeting",
            "description": "Weekly sync meeting",
            "location": "Office",
            "status": "CONFIRMED",
        }.get(key, default)

        mock_dtstart = MagicMock()
        mock_dtstart.dt = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        mock_ical.get.side_effect = lambda key, default=None: {
            "uid": "event-123",
            "summary": "Team Meeting",
            "description": "Weekly sync meeting",
            "location": "Office",
            "status": "CONFIRMED",
            "dtstart": mock_dtstart,
            "dtend": MagicMock(dt=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc)),
        }.get(key, default)

        mock_event = MagicMock()
        mock_event.icalendar_component = mock_ical

        mock_cal = MagicMock()
        mock_cal.name = "Work"
        mock_cal.search.return_value = [mock_event]

        mock_principal = MagicMock()
        mock_principal.calendars.return_value = [mock_cal]

        mock_client_instance = MagicMock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = ICloudCalendarClient(client_config)
        _events = client.search_events("Meeting", days_ahead=30, days_behind=7)

        # The search will call the calendar's search method
        mock_cal.search.assert_called_once()
        assert _events is not None  # Use the variable to validate call succeeded


# ============================================================================
# Adapter Tests
# ============================================================================


class TestICloudCalendarAdapter:
    """Tests for ICloudCalendarAdapter"""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client"""
        client = MagicMock()
        client.is_available.return_value = True
        return client

    @pytest.fixture
    def adapter_config(self):
        """Create test adapter config"""
        return ICloudCalendarAdapterConfig(
            enabled=True,
            past_days=90,
            future_days=30,
        )

    def test_adapter_not_available(self):
        """Test adapter when client is not available"""
        adapter = ICloudCalendarAdapter(None)
        assert adapter.is_available is False

    def test_adapter_available(self, mock_client):
        """Test adapter when client is available"""
        adapter = ICloudCalendarAdapter(mock_client)
        assert adapter.is_available is True

    def test_source_name(self, mock_client):
        """Test adapter source name"""
        adapter = ICloudCalendarAdapter(mock_client)
        assert adapter.source_name == "icloud_calendar"

    @pytest.mark.asyncio
    async def test_search_not_available(self):
        """Test search when adapter not available"""
        adapter = ICloudCalendarAdapter(None)
        results = await adapter.search("meeting")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self, mock_client, adapter_config):
        """Test successful search"""
        # Create sample events
        sample_events = [
            ICloudCalendarEvent(
                uid="event-1",
                summary="Team Meeting",
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=1),
                calendar_name="Work",
                description="Weekly sync",
            ),
            ICloudCalendarEvent(
                uid="event-2",
                summary="Project Meeting",
                start_date=datetime.now(timezone.utc) + timedelta(days=1),
                end_date=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
                calendar_name="Work",
            ),
        ]

        mock_client.search_events.return_value = sample_events

        adapter = ICloudCalendarAdapter(mock_client, adapter_config)
        results = await adapter.search("meeting", max_results=10)

        assert len(results) == 2
        assert results[0].source == "icloud_calendar"
        assert results[0].type == "event"
        assert "Meeting" in results[0].title

    @pytest.mark.asyncio
    async def test_search_with_context(self, mock_client, adapter_config):
        """Test search with context filters"""
        mock_client.search_events.return_value = []

        adapter = ICloudCalendarAdapter(mock_client, adapter_config)
        context = {
            "include_past": False,
            "include_future": True,
            "calendar_names": ["Work"],
        }

        await adapter.search("meeting", context=context)

        # Verify search was called with correct parameters
        mock_client.search_events.assert_called_once()
        call_kwargs = mock_client.search_events.call_args[1]
        assert call_kwargs["days_behind"] == 0  # include_past=False
        assert call_kwargs["calendar_names"] == ["Work"]

    @pytest.mark.asyncio
    async def test_search_error_handling(self, mock_client, adapter_config):
        """Test search error handling"""
        mock_client.search_events.side_effect = Exception("Search failed")

        adapter = ICloudCalendarAdapter(mock_client, adapter_config)
        results = await adapter.search("meeting")

        # Should return empty list on error, not raise
        assert results == []

    def test_calculate_relevance_summary_match(self, mock_client):
        """Test relevance calculation with summary match"""
        adapter = ICloudCalendarAdapter(mock_client)

        event = ICloudCalendarEvent(
            uid="event-1",
            summary="Team Meeting",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            attendees=[],
        )

        relevance = adapter._calculate_relevance(event, "meeting")
        # Base (0.7) + summary match (0.15) + recency (0.05) = 0.9
        assert relevance >= 0.85

    def test_calculate_relevance_no_match(self, mock_client):
        """Test relevance calculation without match"""
        adapter = ICloudCalendarAdapter(mock_client)

        event = ICloudCalendarEvent(
            uid="event-1",
            summary="Lunch Break",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            attendees=[],
        )

        relevance = adapter._calculate_relevance(event, "meeting")
        # Base (0.7) + recency (0.05) = 0.75
        assert relevance < 0.85


class TestICloudCalendarAdapterConfig:
    """Tests for ICloudCalendarAdapterConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ICloudCalendarAdapterConfig()
        assert config.enabled is True
        assert config.past_days == 365
        assert config.future_days == 90
        assert config.max_results == 20
        assert config.server_url == "https://caldav.icloud.com"

    def test_custom_config(self):
        """Test custom configuration"""
        config = ICloudCalendarAdapterConfig(
            enabled=False,
            past_days=30,
            future_days=14,
            username="user@icloud.com",
            app_specific_password="secret",
        )
        assert config.enabled is False
        assert config.past_days == 30
        assert config.future_days == 14
        assert config.username == "user@icloud.com"
