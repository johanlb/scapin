"""
Tests for Calendar Normalizer

Tests the CalendarNormalizer class that converts CalendarEvent to PerceivedEvent.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.core.events.universal_event import EventSource, EventType, UrgencyLevel
from src.integrations.microsoft.calendar_models import (
    CalendarAttendee,
    CalendarEvent,
    CalendarEventImportance,
    CalendarLocation,
    CalendarResponseStatus,
)
from src.integrations.microsoft.calendar_normalizer import CalendarNormalizer


class TestCalendarNormalizer:
    """Tests for CalendarNormalizer"""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance"""
        return CalendarNormalizer()

    @pytest.fixture
    def basic_event(self):
        """Create a basic event for testing"""
        now = datetime.now(timezone.utc)
        return CalendarEvent(
            event_id="event123",
            calendar_id="calendar456",
            subject="Test Event",
            body_preview="Test preview",
            body_content="Test content",
            start=now + timedelta(hours=2),
            end=now + timedelta(hours=3),
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
            subject="Team Meeting",
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
            response_status=CalendarResponseStatus.ACCEPTED,
            is_online_meeting=True,
            online_meeting_url="https://teams.microsoft.com/meeting/123",
        )

    def test_normalize_basic_event(self, normalizer, basic_event):
        """Test normalizing a basic event"""
        perceived = normalizer.normalize(basic_event)

        assert perceived.event_id == "calendar-event123"
        assert perceived.source == EventSource.CALENDAR
        assert perceived.source_id == "event123"
        assert "Test Event" in perceived.title
        assert perceived.from_person == "Organizer <organizer@example.com>"

    def test_normalize_meeting_event(self, normalizer, meeting_event):
        """Test normalizing a meeting with attendees"""
        perceived = normalizer.normalize(meeting_event)

        assert perceived.event_id == "calendar-meeting123"
        assert len(perceived.to_people) == 2
        assert "User 1 <user1@example.com>" in perceived.to_people
        assert "User 2 <user2@example.com>" in perceived.to_people

    def test_normalize_extracts_urls(self, normalizer, meeting_event):
        """Test URL extraction includes online meeting URL"""
        perceived = normalizer.normalize(meeting_event)

        assert len(perceived.urls) > 0
        assert "https://teams.microsoft.com/meeting/123" in perceived.urls

    def test_normalize_metadata(self, normalizer, meeting_event):
        """Test metadata is correctly populated"""
        perceived = normalizer.normalize(meeting_event)
        meta = perceived.metadata

        assert meta["event_id"] == "meeting123"
        assert meta["calendar_id"] == "calendar456"
        assert meta["is_meeting"] is True
        assert meta["is_online"] is True
        assert meta["attendee_count"] == 2

    def test_normalize_title_includes_time(self, normalizer, basic_event):
        """Test that title includes time prefix"""
        perceived = normalizer.normalize(basic_event)

        # Title should be like "[HH:MM] Test Event"
        assert perceived.title.startswith("[")
        assert "]" in perceived.title
        assert "Test Event" in perceived.title

    def test_normalize_timing_uses_current_time(self, normalizer, basic_event):
        """Test that occurred_at uses current time, not event start"""
        perceived = normalizer.normalize(basic_event)

        # occurred_at should be close to now, not event start time
        # Event start is in future, but occurred_at should be <= received_at
        assert perceived.occurred_at <= perceived.received_at
        assert perceived.received_at <= perceived.perceived_at

        # The actual event start time is stored in metadata
        assert "start" in perceived.metadata
        assert perceived.metadata["start"] == basic_event.start.isoformat()

    def test_normalize_all_day_event_title(self, normalizer):
        """Test all-day event has 'All Day' in title"""
        now = datetime.now(timezone.utc)
        all_day_event = CalendarEvent(
            event_id="allday123",
            calendar_id="cal",
            subject="Holiday",
            body_preview="",
            body_content="",
            start=now,
            end=now + timedelta(days=1),
            timezone="UTC",
            is_all_day=True,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
        )
        perceived = normalizer.normalize(all_day_event)

        assert "All Day" in perceived.title


class TestDetermineEventType:
    """Tests for _determine_event_type"""

    @pytest.fixture
    def normalizer(self):
        return CalendarNormalizer()

    def test_cancelled_event_is_information(self, normalizer):
        """Cancelled events should be informational"""
        event = CalendarEvent(
            event_id="cancelled",
            calendar_id="cal",
            subject="Cancelled",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
            is_cancelled=True,
        )
        perceived = normalizer.normalize(event)
        assert perceived.event_type == EventType.INFORMATION

    def test_meeting_not_responded_is_decision_needed(self, normalizer):
        """Meeting invitation not responded should need decision"""
        event = CalendarEvent(
            event_id="pending",
            calendar_id="cal",
            subject="Meeting",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(
                CalendarAttendee(
                    email="att@example.com",
                    display_name="Attendee",
                    response_status=CalendarResponseStatus.ACCEPTED,
                ),
            ),
            response_status=CalendarResponseStatus.NOT_RESPONDED,
        )
        perceived = normalizer.normalize(event)
        assert perceived.event_type == EventType.DECISION_NEEDED

    def test_accepted_meeting_is_reminder(self, normalizer):
        """Accepted meeting should be a reminder"""
        event = CalendarEvent(
            event_id="accepted",
            calendar_id="cal",
            subject="Meeting",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(
                CalendarAttendee(
                    email="att@example.com",
                    display_name="Attendee",
                    response_status=CalendarResponseStatus.ACCEPTED,
                ),
            ),
            response_status=CalendarResponseStatus.ACCEPTED,
        )
        perceived = normalizer.normalize(event)
        assert perceived.event_type == EventType.REMINDER

    def test_personal_event_is_reminder(self, normalizer):
        """Personal event (no attendees) should be reminder"""
        event = CalendarEvent(
            event_id="personal",
            calendar_id="cal",
            subject="Personal Task",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="me@example.com",
                display_name="Me",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
        )
        perceived = normalizer.normalize(event)
        assert perceived.event_type == EventType.REMINDER


class TestDetermineUrgency:
    """Tests for _determine_urgency"""

    @pytest.fixture
    def normalizer(self):
        return CalendarNormalizer()

    def _create_event_at_time(self, start_offset: timedelta) -> CalendarEvent:
        """Helper to create event at a specific time offset"""
        now = datetime.now(timezone.utc)
        return CalendarEvent(
            event_id="test",
            calendar_id="cal",
            subject="Test",
            body_preview="",
            body_content="",
            start=now + start_offset,
            end=now + start_offset + timedelta(hours=1),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
        )

    def test_past_event_no_urgency(self, normalizer):
        """Past events should have no urgency"""
        event = self._create_event_at_time(timedelta(hours=-3))
        perceived = normalizer.normalize(event)
        assert perceived.urgency == UrgencyLevel.NONE

    def test_within_hour_is_critical(self, normalizer):
        """Event within 1 hour is critical"""
        event = self._create_event_at_time(timedelta(minutes=30))
        perceived = normalizer.normalize(event)
        assert perceived.urgency == UrgencyLevel.CRITICAL

    def test_within_4_hours_is_high(self, normalizer):
        """Event within 4 hours is high urgency"""
        event = self._create_event_at_time(timedelta(hours=2))
        perceived = normalizer.normalize(event)
        assert perceived.urgency == UrgencyLevel.HIGH

    def test_within_12_hours_is_medium(self, normalizer):
        """Event within 12 hours is medium urgency"""
        event = self._create_event_at_time(timedelta(hours=8))
        perceived = normalizer.normalize(event)
        assert perceived.urgency == UrgencyLevel.MEDIUM

    def test_more_than_24_hours_is_low(self, normalizer):
        """Event more than 24 hours away is low urgency"""
        event = self._create_event_at_time(timedelta(hours=48))
        perceived = normalizer.normalize(event)
        assert perceived.urgency == UrgencyLevel.LOW


class TestExtractEntities:
    """Tests for _extract_entities"""

    @pytest.fixture
    def normalizer(self):
        return CalendarNormalizer()

    def test_extracts_organizer_as_person(self, normalizer):
        """Organizer should be extracted as person entity"""
        event = CalendarEvent(
            event_id="test",
            calendar_id="cal",
            subject="Meeting",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="organizer@example.com",
                display_name="The Organizer",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
        )
        perceived = normalizer.normalize(event)

        person_entities = [e for e in perceived.entities if e.type == "person"]
        assert len(person_entities) >= 1
        assert any(e.value == "The Organizer" for e in person_entities)

    def test_extracts_attendees_as_persons(self, normalizer):
        """Attendees should be extracted as person entities"""
        event = CalendarEvent(
            event_id="test",
            calendar_id="cal",
            subject="Meeting",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(
                CalendarAttendee(
                    email="att1@example.com",
                    display_name="Attendee One",
                    response_status=CalendarResponseStatus.ACCEPTED,
                ),
                CalendarAttendee(
                    email="att2@example.com",
                    display_name="Attendee Two",
                    response_status=CalendarResponseStatus.DECLINED,
                ),
            ),
        )
        perceived = normalizer.normalize(event)

        person_entities = [e for e in perceived.entities if e.type == "person"]
        assert len(person_entities) >= 3  # Organizer + 2 attendees
        assert any(e.value == "Attendee One" for e in person_entities)
        assert any(e.value == "Attendee Two" for e in person_entities)

    def test_extracts_location(self, normalizer):
        """Location should be extracted as entity"""
        event = CalendarEvent(
            event_id="test",
            calendar_id="cal",
            subject="Meeting",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
            location=CalendarLocation(display_name="Conference Room A"),
        )
        perceived = normalizer.normalize(event)

        location_entities = [e for e in perceived.entities if e.type == "location"]
        assert len(location_entities) == 1
        assert location_entities[0].value == "Conference Room A"

    def test_extracts_datetime(self, normalizer):
        """Event datetime should be extracted as entity"""
        event = CalendarEvent(
            event_id="test",
            calendar_id="cal",
            subject="Meeting",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
        )
        perceived = normalizer.normalize(event)

        datetime_entities = [e for e in perceived.entities if e.type == "datetime"]
        assert len(datetime_entities) == 1


class TestExtractTopicsAndKeywords:
    """Tests for _extract_topics_and_keywords"""

    @pytest.fixture
    def normalizer(self):
        return CalendarNormalizer()

    def test_extracts_categories_as_topics(self, normalizer):
        """Categories should become topics"""
        event = CalendarEvent(
            event_id="test",
            calendar_id="cal",
            subject="Meeting",
            body_preview="",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
            categories=("Project X", "Important"),
        )
        perceived = normalizer.normalize(event)

        assert "Project X" in perceived.topics
        assert "Important" in perceived.topics

    def test_extracts_keywords_from_subject(self, normalizer):
        """Keywords should be extracted from subject"""
        event = CalendarEvent(
            event_id="test",
            calendar_id="cal",
            subject="Urgent Review Meeting",
            body_preview="This is a review",
            body_content="",
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
            is_all_day=False,
            organizer=CalendarAttendee(
                email="org@example.com",
                display_name="Org",
                response_status=CalendarResponseStatus.ORGANIZER,
            ),
            attendees=(),
        )
        perceived = normalizer.normalize(event)

        assert "urgent" in perceived.keywords
        assert "review" in perceived.keywords
