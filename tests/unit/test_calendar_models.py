"""
Tests for Calendar Models

Tests the CalendarEvent, CalendarAttendee, and related dataclasses.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.integrations.microsoft.calendar_models import (
    CalendarAttendee,
    CalendarEvent,
    CalendarEventImportance,
    CalendarEventSensitivity,
    CalendarEventShowAs,
    CalendarLocation,
    CalendarResponseStatus,
    _extract_plain_text,
)


class TestCalendarResponseStatus:
    """Tests for CalendarResponseStatus enum"""

    def test_all_values(self):
        """Test all response status values"""
        assert CalendarResponseStatus.NONE.value == "none"
        assert CalendarResponseStatus.ORGANIZER.value == "organizer"
        assert CalendarResponseStatus.TENTATIVELY_ACCEPTED.value == "tentativelyAccepted"
        assert CalendarResponseStatus.ACCEPTED.value == "accepted"
        assert CalendarResponseStatus.DECLINED.value == "declined"
        assert CalendarResponseStatus.NOT_RESPONDED.value == "notResponded"


class TestCalendarEventImportance:
    """Tests for CalendarEventImportance enum"""

    def test_all_values(self):
        """Test all importance values"""
        assert CalendarEventImportance.LOW.value == "low"
        assert CalendarEventImportance.NORMAL.value == "normal"
        assert CalendarEventImportance.HIGH.value == "high"


class TestCalendarAttendee:
    """Tests for CalendarAttendee dataclass"""

    def test_basic_creation(self):
        """Test creating a basic attendee"""
        attendee = CalendarAttendee(
            email="test@example.com",
            display_name="Test User",
            response_status=CalendarResponseStatus.ACCEPTED,
        )
        assert attendee.email == "test@example.com"
        assert attendee.display_name == "Test User"
        assert attendee.response_status == CalendarResponseStatus.ACCEPTED
        assert attendee.attendee_type == "required"
        assert attendee.is_organizer is False

    def test_attendee_with_all_fields(self):
        """Test attendee with all fields"""
        attendee = CalendarAttendee(
            email="organizer@example.com",
            display_name="Organizer",
            response_status=CalendarResponseStatus.ORGANIZER,
            attendee_type="optional",
            is_organizer=True,
        )
        assert attendee.attendee_type == "optional"
        assert attendee.is_organizer is True

    def test_to_dict(self):
        """Test conversion to dictionary"""
        attendee = CalendarAttendee(
            email="test@example.com",
            display_name="Test User",
            response_status=CalendarResponseStatus.TENTATIVELY_ACCEPTED,
        )
        d = attendee.to_dict()
        assert d["email"] == "test@example.com"
        assert d["display_name"] == "Test User"
        assert d["response_status"] == "tentativelyAccepted"
        assert d["attendee_type"] == "required"
        assert d["is_organizer"] is False

    def test_from_api(self):
        """Test creating attendee from Graph API response"""
        api_data = {
            "emailAddress": {
                "address": "user@example.com",
                "name": "User Name",
            },
            "status": {
                "response": "accepted",
            },
            "type": "optional",
        }
        attendee = CalendarAttendee.from_api(api_data)
        assert attendee.email == "user@example.com"
        assert attendee.display_name == "User Name"
        assert attendee.response_status == CalendarResponseStatus.ACCEPTED
        assert attendee.attendee_type == "optional"

    def test_from_api_with_unknown_response(self):
        """Test handling unknown response status"""
        api_data = {
            "emailAddress": {
                "address": "user@example.com",
                "name": "User Name",
            },
            "status": {
                "response": "unknown_status",
            },
        }
        attendee = CalendarAttendee.from_api(api_data)
        assert attendee.response_status == CalendarResponseStatus.NONE


class TestCalendarLocation:
    """Tests for CalendarLocation dataclass"""

    def test_basic_creation(self):
        """Test creating a basic location"""
        location = CalendarLocation(display_name="Conference Room A")
        assert location.display_name == "Conference Room A"
        assert location.location_type == "default"
        assert location.address is None
        assert location.coordinates is None

    def test_location_with_all_fields(self):
        """Test location with all fields"""
        location = CalendarLocation(
            display_name="Office",
            location_type="businessAddress",
            address="123 Main St, City, State",
            coordinates=(40.7128, -74.0060),
        )
        assert location.address == "123 Main St, City, State"
        assert location.coordinates == (40.7128, -74.0060)

    def test_to_dict(self):
        """Test conversion to dictionary"""
        location = CalendarLocation(
            display_name="Meeting Room",
            address="Floor 2",
        )
        d = location.to_dict()
        assert d["display_name"] == "Meeting Room"
        assert d["address"] == "Floor 2"
        assert "coordinates" not in d

    def test_to_dict_with_coordinates(self):
        """Test to_dict includes coordinates when present"""
        location = CalendarLocation(
            display_name="Office",
            coordinates=(51.5074, -0.1278),
        )
        d = location.to_dict()
        assert d["coordinates"] == {"latitude": 51.5074, "longitude": -0.1278}

    def test_from_api_basic(self):
        """Test creating from API response"""
        api_data = {
            "displayName": "Room 101",
            "locationType": "conferenceRoom",
        }
        location = CalendarLocation.from_api(api_data)
        assert location is not None
        assert location.display_name == "Room 101"
        assert location.location_type == "conferenceRoom"

    def test_from_api_empty(self):
        """Test handling empty/missing location"""
        assert CalendarLocation.from_api({}) is None
        assert CalendarLocation.from_api({"displayName": ""}) is None

    def test_from_api_with_address(self):
        """Test parsing address from API"""
        api_data = {
            "displayName": "Office",
            "address": {
                "street": "123 Main St",
                "city": "New York",
                "state": "NY",
                "countryOrRegion": "USA",
            },
        }
        location = CalendarLocation.from_api(api_data)
        assert location is not None
        assert "123 Main St" in location.address
        assert "New York" in location.address


class TestCalendarEvent:
    """Tests for CalendarEvent dataclass"""

    @pytest.fixture
    def basic_event(self):
        """Create a basic event for testing"""
        now = datetime.now(timezone.utc)
        return CalendarEvent(
            event_id="event123",
            calendar_id="calendar456",
            subject="Test Meeting",
            body_preview="Meeting about testing",
            body_content="Full body content",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="organizer@example.com",
                display_name="Organizer",
                response_status=CalendarResponseStatus.ORGANIZER,
                is_organizer=True,
            ),
            attendees=(),
        )

    @pytest.fixture
    def meeting_event(self):
        """Create a meeting with attendees"""
        now = datetime.now(timezone.utc)
        return CalendarEvent(
            event_id="meeting123",
            calendar_id="calendar456",
            subject="Team Sync",
            body_preview="Weekly sync",
            body_content="<p>Weekly sync meeting</p>",
            start=now + timedelta(hours=2),
            end=now + timedelta(hours=3),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="manager@example.com",
                display_name="Manager",
                response_status=CalendarResponseStatus.ORGANIZER,
                is_organizer=True,
            ),
            attendees=(
                CalendarAttendee(
                    email="user1@example.com",
                    display_name="User 1",
                    response_status=CalendarResponseStatus.ACCEPTED,
                ),
                CalendarAttendee(
                    email="user2@example.com",
                    display_name="User 2",
                    response_status=CalendarResponseStatus.TENTATIVELY_ACCEPTED,
                ),
            ),
            is_online_meeting=True,
            online_meeting_url="https://teams.microsoft.com/meeting/123",
        )

    def test_basic_event_creation(self, basic_event):
        """Test creating a basic event"""
        assert basic_event.event_id == "event123"
        assert basic_event.subject == "Test Meeting"
        assert basic_event.is_meeting is False  # No attendees

    def test_meeting_event_creation(self, meeting_event):
        """Test creating a meeting with attendees"""
        assert meeting_event.is_meeting is True
        assert len(meeting_event.attendees) == 2
        assert meeting_event.is_online_meeting is True

    def test_event_validation_no_event_id(self):
        """Test validation fails without event_id"""
        with pytest.raises(ValueError, match="event_id is required"):
            CalendarEvent(
                event_id="",
                calendar_id="cal",
                subject="Test",
                body_preview="",
                body_content="",
                start=datetime.now(timezone.utc),
                end=datetime.now(timezone.utc) + timedelta(hours=1),
                timezone="UTC",
                is_all_day=False,
                organizer=CalendarAttendee(
                    email="test@example.com",
                    display_name="Test",
                    response_status=CalendarResponseStatus.ORGANIZER,
                ),
                attendees=(),
            )

    def test_event_validation_no_calendar_id(self):
        """Test validation fails without calendar_id"""
        with pytest.raises(ValueError, match="calendar_id is required"):
            CalendarEvent(
                event_id="event123",
                calendar_id="",
                subject="Test",
                body_preview="",
                body_content="",
                start=datetime.now(timezone.utc),
                end=datetime.now(timezone.utc) + timedelta(hours=1),
                timezone="UTC",
                is_all_day=False,
                organizer=CalendarAttendee(
                    email="test@example.com",
                    display_name="Test",
                    response_status=CalendarResponseStatus.ORGANIZER,
                ),
                attendees=(),
            )

    def test_duration_minutes(self, basic_event):
        """Test duration calculation"""
        assert basic_event.duration_minutes == 60

    def test_duration_property(self, basic_event):
        """Test duration timedelta property"""
        assert basic_event.duration == timedelta(hours=1)

    def test_is_past(self):
        """Test is_past property"""
        past_event = CalendarEvent(
            event_id="past",
            calendar_id="cal",
            subject="Past Event",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) - timedelta(hours=2),
            end=datetime.now(timezone.utc) - timedelta(hours=1),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="test@example.com",
                display_name="Test",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
        )
        assert past_event.is_past is True

    def test_is_upcoming(self, basic_event):
        """Test is_upcoming property"""
        assert basic_event.is_upcoming is True

    def test_minutes_until_start(self, basic_event):
        """Test minutes until start calculation"""
        # Event is 1 hour in the future
        assert 55 <= basic_event.minutes_until_start <= 65

    def test_to_dict(self, meeting_event):
        """Test conversion to dictionary"""
        d = meeting_event.to_dict()
        assert d["event_id"] == "meeting123"
        assert d["subject"] == "Team Sync"
        assert d["is_meeting"] is True
        assert d["is_online_meeting"] is True
        assert len(d["attendees"]) == 2
        assert d["duration_minutes"] == 60

    def test_from_api_basic(self):
        """Test creating event from Graph API response"""
        api_data = {
            "id": "api_event_123",
            "subject": "API Meeting",
            "bodyPreview": "Preview text",
            "body": {
                "contentType": "html",
                "content": "<p>Body content</p>",
            },
            "start": {
                "dateTime": "2026-01-03T10:00:00",
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": "2026-01-03T11:00:00",
                "timeZone": "UTC",
            },
            "organizer": {
                "emailAddress": {
                    "address": "org@example.com",
                    "name": "Organizer",
                },
            },
            "attendees": [],
        }
        event = CalendarEvent.from_api(api_data, "cal_123")
        assert event.event_id == "api_event_123"
        assert event.subject == "API Meeting"
        assert event.calendar_id == "cal_123"
        assert event.organizer.email == "org@example.com"

    def test_from_api_with_online_meeting(self):
        """Test parsing online meeting info"""
        api_data = {
            "id": "online_event",
            "subject": "Online Meeting",
            "start": {"dateTime": "2026-01-03T10:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-03T11:00:00", "timeZone": "UTC"},
            "organizer": {
                "emailAddress": {"address": "org@example.com", "name": "Org"},
            },
            "isOnlineMeeting": True,
            "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/join"},
            "onlineMeetingProvider": "teamsForBusiness",
        }
        event = CalendarEvent.from_api(api_data, "cal")
        assert event.is_online_meeting is True
        assert event.online_meeting_url == "https://teams.microsoft.com/join"
        assert event.online_meeting_provider == "teamsForBusiness"

    def test_from_api_with_attendees(self):
        """Test parsing attendees from API"""
        api_data = {
            "id": "meeting",
            "subject": "Meeting",
            "start": {"dateTime": "2026-01-03T10:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-03T11:00:00", "timeZone": "UTC"},
            "organizer": {
                "emailAddress": {"address": "org@example.com", "name": "Org"},
            },
            "attendees": [
                {
                    "emailAddress": {"address": "att1@example.com", "name": "Attendee 1"},
                    "status": {"response": "accepted"},
                    "type": "required",
                },
                {
                    "emailAddress": {"address": "att2@example.com", "name": "Attendee 2"},
                    "status": {"response": "declined"},
                    "type": "optional",
                },
            ],
        }
        event = CalendarEvent.from_api(api_data, "cal")
        assert len(event.attendees) == 2
        assert event.attendees[0].response_status == CalendarResponseStatus.ACCEPTED
        assert event.attendees[1].response_status == CalendarResponseStatus.DECLINED

    def test_from_api_all_day_event(self):
        """Test parsing all-day event"""
        api_data = {
            "id": "allday",
            "subject": "Holiday",
            "isAllDay": True,
            "start": {"dateTime": "2026-01-03T00:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-04T00:00:00", "timeZone": "UTC"},
            "organizer": {
                "emailAddress": {"address": "org@example.com", "name": "Org"},
            },
        }
        event = CalendarEvent.from_api(api_data, "cal")
        assert event.is_all_day is True


class TestExtractPlainText:
    """Tests for _extract_plain_text helper function"""

    def test_extract_from_html(self):
        """Test extracting text from HTML"""
        html = "<p>Hello <b>World</b></p>"
        assert _extract_plain_text(html) == "Hello World"

    def test_handle_empty_string(self):
        """Test handling empty string"""
        assert _extract_plain_text("") == ""

    def test_decode_html_entities(self):
        """Test decoding HTML entities"""
        html = "Hello &amp; World &lt;test&gt;"
        result = _extract_plain_text(html)
        assert "&amp;" not in result
        assert "&" in result
        assert "<test>" in result

    def test_normalize_whitespace(self):
        """Test whitespace normalization"""
        html = "<p>Hello</p>   <p>World</p>"
        result = _extract_plain_text(html)
        assert "  " not in result

    def test_preserve_content(self):
        """Test that content is preserved"""
        html = "<div><p>Line 1</p><p>Line 2</p></div>"
        result = _extract_plain_text(html)
        assert "Line 1" in result
        assert "Line 2" in result
