"""
Tests for Briefing Models

Tests the data models used in the briefing system.
"""

from datetime import date, datetime, timezone

import pytest

from src.core.events import EventSource, EventType, PerceivedEvent, UrgencyLevel
from src.jeeves.briefing.models import (
    AttendeeContext,
    BriefingItem,
    MorningBriefing,
    PreMeetingBriefing,
    _extract_display_name,
    _format_duration,
    _get_source_icon,
)

# Fixtures


@pytest.fixture
def sample_event() -> PerceivedEvent:
    """Create a sample PerceivedEvent for testing"""
    now = datetime.now(timezone.utc)
    return PerceivedEvent(
        event_id="test-event-1",
        source=EventSource.EMAIL,
        source_id="email-test-event-1",
        occurred_at=now,
        received_at=now,
        title="Test Email Subject",
        content="This is the email content",
        event_type=EventType.INFORMATION,
        urgency=UrgencyLevel.MEDIUM,
        entities=[],
        topics=[],
        keywords=[],
        from_person="John Doe <john@example.com>",
        to_people=[],
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={"has_attachments": False},
        perception_confidence=0.85,
        needs_clarification=False,
        clarification_questions=[],
    )


@pytest.fixture
def sample_calendar_event() -> PerceivedEvent:
    """Create a sample calendar PerceivedEvent"""
    now = datetime.now(timezone.utc)
    return PerceivedEvent(
        event_id="cal-event-1",
        source=EventSource.CALENDAR,
        source_id="calendar-cal-event-1",
        occurred_at=now,
        received_at=now,
        title="Team Standup",
        content="Daily standup meeting",
        event_type=EventType.INVITATION,
        urgency=UrgencyLevel.MEDIUM,
        entities=[],
        topics=[],
        keywords=[],
        from_person="Alice Smith <alice@example.com>",
        to_people=[],
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={
            "start": now.isoformat(),
            "end": (now.replace(hour=now.hour + 1)).isoformat(),
            "duration_minutes": 60,
            "attendee_count": 5,
            "is_online": True,
            "location": "",
        },
        perception_confidence=0.9,
        needs_clarification=False,
        clarification_questions=[],
    )


# BriefingItem Tests


class TestBriefingItem:
    """Tests for BriefingItem dataclass"""

    def test_create_briefing_item(self, sample_event: PerceivedEvent) -> None:
        """Test creating a BriefingItem"""
        item = BriefingItem(
            event=sample_event,
            priority_rank=1,
            time_context="2h ago",
            action_summary="Review and respond",
            confidence=0.85,
        )

        assert item.event == sample_event
        assert item.priority_rank == 1
        assert item.time_context == "2h ago"
        assert item.action_summary == "Review and respond"
        assert item.confidence == 0.85

    def test_briefing_item_defaults(self, sample_event: PerceivedEvent) -> None:
        """Test BriefingItem default values"""
        item = BriefingItem(
            event=sample_event,
            priority_rank=5,
            time_context="Just now",
        )

        assert item.action_summary is None
        assert item.confidence == 0.9

    def test_briefing_item_to_dict(self, sample_event: PerceivedEvent) -> None:
        """Test BriefingItem serialization"""
        item = BriefingItem(
            event=sample_event,
            priority_rank=1,
            time_context="2h ago",
            action_summary="Review",
            confidence=0.85,
        )

        data = item.to_dict()

        assert data["event_id"] == "test-event-1"
        assert data["title"] == "Test Email Subject"
        assert data["source"] == "email"  # EventSource enum uses lowercase values
        assert data["priority_rank"] == 1
        assert data["time_context"] == "2h ago"
        assert data["action_summary"] == "Review"
        assert data["confidence"] == 0.85
        assert data["urgency"] == "medium"  # UrgencyLevel enum uses lowercase values

    def test_briefing_item_is_frozen(self, sample_event: PerceivedEvent) -> None:
        """Test that BriefingItem is immutable (frozen=True)"""
        item = BriefingItem(
            event=sample_event,
            priority_rank=1,
            time_context="2h ago",
        )

        with pytest.raises(AttributeError):
            item.priority_rank = 2  # type: ignore

    def test_briefing_item_invalid_confidence(self, sample_event: PerceivedEvent) -> None:
        """Test that BriefingItem rejects invalid confidence values"""
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            BriefingItem(
                event=sample_event,
                priority_rank=1,
                time_context="2h ago",
                confidence=1.5,  # Invalid: > 1.0
            )

        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            BriefingItem(
                event=sample_event,
                priority_rank=1,
                time_context="2h ago",
                confidence=-0.1,  # Invalid: < 0.0
            )

    def test_briefing_item_invalid_priority_rank(self, sample_event: PerceivedEvent) -> None:
        """Test that BriefingItem rejects invalid priority_rank values"""
        with pytest.raises(ValueError, match="priority_rank must be >= 1"):
            BriefingItem(
                event=sample_event,
                priority_rank=0,  # Invalid: < 1
                time_context="2h ago",
            )


# MorningBriefing Tests


class TestMorningBriefing:
    """Tests for MorningBriefing dataclass"""

    def test_create_morning_briefing(self) -> None:
        """Test creating a MorningBriefing"""
        now = datetime.now(timezone.utc)
        briefing = MorningBriefing(
            date=date.today(),
            generated_at=now,
            total_items=10,
            urgent_count=2,
            meetings_today=3,
        )

        assert briefing.date == date.today()
        assert briefing.generated_at == now
        assert briefing.total_items == 10
        assert briefing.urgent_count == 2
        assert briefing.meetings_today == 3
        assert briefing.urgent_items == []
        assert briefing.calendar_today == []
        assert briefing.emails_pending == []
        assert briefing.teams_unread == []
        assert briefing.ai_summary is None
        assert briefing.key_decisions == []

    def test_morning_briefing_to_dict(self, sample_event: PerceivedEvent) -> None:
        """Test MorningBriefing serialization"""
        now = datetime.now(timezone.utc)
        item = BriefingItem(
            event=sample_event,
            priority_rank=1,
            time_context="2h ago",
        )

        briefing = MorningBriefing(
            date=date.today(),
            generated_at=now,
            urgent_items=[item],
            total_items=1,
            urgent_count=1,
            meetings_today=0,
            ai_summary="One urgent email to review.",
        )

        data = briefing.to_dict()

        assert data["date"] == date.today().isoformat()
        assert "generated_at" in data
        assert len(data["urgent_items"]) == 1
        assert data["total_items"] == 1
        assert data["urgent_count"] == 1
        assert data["meetings_today"] == 0
        assert data["ai_summary"] == "One urgent email to review."

    def test_morning_briefing_to_markdown(self, sample_event: PerceivedEvent) -> None:
        """Test MorningBriefing Markdown export"""
        now = datetime.now(timezone.utc)
        item = BriefingItem(
            event=sample_event,
            priority_rank=1,
            time_context="2h ago",
        )

        briefing = MorningBriefing(
            date=date.today(),
            generated_at=now,
            urgent_items=[item],
            total_items=1,
            urgent_count=1,
            meetings_today=0,
            ai_summary="One urgent email to review.",
        )

        markdown = briefing.to_markdown()

        assert "# Morning Briefing" in markdown
        assert "Quick Overview" in markdown
        assert "**Urgent items**: 1" in markdown
        assert "**Meetings today**: 0" in markdown
        assert "Summary" in markdown
        assert "One urgent email to review." in markdown
        assert "Urgent Items" in markdown
        assert "Test Email Subject" in markdown


# AttendeeContext Tests


class TestAttendeeContext:
    """Tests for AttendeeContext dataclass"""

    def test_create_attendee_context(self) -> None:
        """Test creating an AttendeeContext"""
        now = datetime.now(timezone.utc)
        attendee = AttendeeContext(
            name="John Doe",
            email="john@example.com",
            is_organizer=True,
            last_interaction=now,
            interaction_count=15,
            relationship_hint="Frequent contact",
        )

        assert attendee.name == "John Doe"
        assert attendee.email == "john@example.com"
        assert attendee.is_organizer is True
        assert attendee.last_interaction == now
        assert attendee.interaction_count == 15
        assert attendee.relationship_hint == "Frequent contact"

    def test_attendee_context_defaults(self) -> None:
        """Test AttendeeContext default values"""
        attendee = AttendeeContext(
            name="Jane Doe",
            email="jane@example.com",
        )

        assert attendee.is_organizer is False
        assert attendee.last_interaction is None
        assert attendee.interaction_count == 0
        assert attendee.relationship_hint is None

    def test_attendee_context_to_dict(self) -> None:
        """Test AttendeeContext serialization"""
        now = datetime.now(timezone.utc)
        attendee = AttendeeContext(
            name="John Doe",
            email="john@example.com",
            is_organizer=True,
            last_interaction=now,
            interaction_count=15,
            relationship_hint="Frequent contact",
        )

        data = attendee.to_dict()

        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["is_organizer"] is True
        assert data["last_interaction"] == now.isoformat()
        assert data["interaction_count"] == 15
        assert data["relationship_hint"] == "Frequent contact"


# PreMeetingBriefing Tests


class TestPreMeetingBriefing:
    """Tests for PreMeetingBriefing dataclass"""

    def test_create_pre_meeting_briefing(
        self, sample_calendar_event: PerceivedEvent
    ) -> None:
        """Test creating a PreMeetingBriefing"""
        now = datetime.now(timezone.utc)

        briefing = PreMeetingBriefing(
            event=sample_calendar_event,
            generated_at=now,
            minutes_until_start=15,
            meeting_url="https://teams.microsoft.com/meet/123",
            location="Conference Room A",
        )

        assert briefing.event == sample_calendar_event
        assert briefing.minutes_until_start == 15
        assert briefing.meeting_url == "https://teams.microsoft.com/meet/123"
        assert briefing.location == "Conference Room A"
        assert briefing.attendees == []
        assert briefing.recent_emails == []
        assert briefing.recent_teams == []
        assert briefing.talking_points == []
        assert briefing.open_items == []

    def test_pre_meeting_briefing_to_dict(
        self, sample_calendar_event: PerceivedEvent
    ) -> None:
        """Test PreMeetingBriefing serialization"""
        now = datetime.now(timezone.utc)
        attendee = AttendeeContext(
            name="John Doe",
            email="john@example.com",
            is_organizer=True,
        )

        briefing = PreMeetingBriefing(
            event=sample_calendar_event,
            generated_at=now,
            minutes_until_start=15,
            attendees=[attendee],
            talking_points=["Discuss Q1 goals", "Review action items"],
        )

        data = briefing.to_dict()

        assert data["event_id"] == "cal-event-1"
        assert data["event_title"] == "Team Standup"
        assert data["minutes_until_start"] == 15
        assert len(data["attendees"]) == 1
        assert data["talking_points"] == ["Discuss Q1 goals", "Review action items"]

    def test_pre_meeting_briefing_to_markdown(
        self, sample_calendar_event: PerceivedEvent
    ) -> None:
        """Test PreMeetingBriefing Markdown export"""
        now = datetime.now(timezone.utc)
        attendee = AttendeeContext(
            name="John Doe",
            email="john@example.com",
            is_organizer=True,
        )

        briefing = PreMeetingBriefing(
            event=sample_calendar_event,
            generated_at=now,
            minutes_until_start=15,
            attendees=[attendee],
            meeting_url="https://teams.microsoft.com/meet/123",
            talking_points=["Discuss Q1 goals"],
            open_items=["Follow up on budget"],
        )

        markdown = briefing.to_markdown()

        assert "# Pre-Meeting Briefing" in markdown
        assert "Team Standup" in markdown
        assert "**Starts in 15 minutes**" in markdown
        assert "Meeting Details" in markdown
        assert "https://teams.microsoft.com/meet/123" in markdown
        assert "Attendees" in markdown
        assert "John Doe" in markdown
        assert "(organizer)" in markdown
        assert "Talking Points" in markdown
        assert "Discuss Q1 goals" in markdown
        assert "Open Items" in markdown
        assert "Follow up on budget" in markdown


# Helper Function Tests


class TestHelperFunctions:
    """Tests for module helper functions"""

    def test_get_source_icon(self) -> None:
        """Test source icon mapping"""
        assert _get_source_icon(EventSource.EMAIL) == "[Email]"
        assert _get_source_icon(EventSource.CALENDAR) == "[Cal]"
        assert _get_source_icon(EventSource.TEAMS) == "[Teams]"
        assert _get_source_icon(EventSource.FILE) == "[File]"
        assert _get_source_icon(EventSource.TASK) == "[Task]"

    def test_format_duration_minutes(self) -> None:
        """Test duration formatting for minutes"""
        assert _format_duration(30) == "30m"
        assert _format_duration(45) == "45m"
        assert _format_duration(59) == "59m"

    def test_format_duration_hours(self) -> None:
        """Test duration formatting for hours"""
        assert _format_duration(60) == "1h"
        assert _format_duration(120) == "2h"

    def test_format_duration_hours_and_minutes(self) -> None:
        """Test duration formatting for mixed hours and minutes"""
        assert _format_duration(90) == "1h30m"
        assert _format_duration(150) == "2h30m"
        assert _format_duration(75) == "1h15m"

    def test_format_duration_zero_and_negative(self) -> None:
        """Test duration formatting for zero and negative values"""
        assert _format_duration(0) == "-"
        assert _format_duration(-30) == "-"
        assert _format_duration(-1) == "-"


class TestExtractDisplayName:
    """Tests for _extract_display_name helper function"""

    def test_extract_from_name_email_format(self) -> None:
        """Test extracting name from 'Name <email>' format"""
        assert _extract_display_name("John Doe <john@example.com>") == "John Doe"
        assert _extract_display_name("Jane Smith <jane@example.com>") == "Jane Smith"

    def test_extract_from_plain_email(self) -> None:
        """Test extracting from plain email"""
        assert _extract_display_name("john@example.com") == "john@example.com"

    def test_extract_from_empty_string(self) -> None:
        """Test extracting from empty string"""
        assert _extract_display_name("") == "Unknown"

    def test_extract_from_email_only_in_brackets(self) -> None:
        """Test extracting when only email in brackets"""
        assert _extract_display_name("<john@example.com>") == "Unknown"

    def test_extract_with_whitespace(self) -> None:
        """Test extracting with extra whitespace"""
        assert _extract_display_name("  John Doe  <john@example.com>") == "John Doe"
        assert _extract_display_name("John Doe  ") == "John Doe"
