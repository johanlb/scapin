"""
Tests for Briefing Display

Tests the Rich-based briefing display system.
"""

from datetime import date, datetime, timezone
from io import StringIO

import pytest
from rich.console import Console

from src.core.events import EventSource, EventType, PerceivedEvent, UrgencyLevel
from src.frontin.briefing.display import BriefingDisplay, _format_duration, _truncate
from src.frontin.briefing.models import (
    AttendeeContext,
    BriefingItem,
    MorningBriefing,
    PreMeetingBriefing,
)

# Fixtures


@pytest.fixture
def console() -> Console:
    """Create a console that captures output"""
    return Console(file=StringIO(), force_terminal=True)


@pytest.fixture
def display(console: Console) -> BriefingDisplay:
    """Create a display instance"""
    return BriefingDisplay(console)


def create_test_event(
    event_id: str = "test-1",
    source: EventSource = EventSource.EMAIL,
    title: str = "Test Event",
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
    from_person: str = "Test Person <test@example.com>",
) -> PerceivedEvent:
    """Create a test event with all required fields"""
    now = datetime.now(timezone.utc)
    return PerceivedEvent(
        event_id=event_id,
        source=source,
        source_id=f"{source.value}-{event_id}",
        occurred_at=now,
        received_at=now,
        title=title,
        content="Test content",
        event_type=EventType.INFORMATION if source != EventSource.CALENDAR else EventType.INVITATION,
        urgency=urgency,
        entities=[],
        topics=[],
        keywords=[],
        from_person=from_person,
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
            "duration_minutes": 60,
            "attendee_count": 3,
        },
        perception_confidence=0.9,
        needs_clarification=False,
        clarification_questions=[],
    )


def create_test_briefing_item(
    event: PerceivedEvent | None = None,
    priority_rank: int = 1,
    time_context: str = "2h ago",
) -> BriefingItem:
    """Create a test briefing item"""
    if event is None:
        event = create_test_event()
    return BriefingItem(
        event=event,
        priority_rank=priority_rank,
        time_context=time_context,
    )


# BriefingDisplay Tests


class TestBriefingDisplayInit:
    """Tests for BriefingDisplay initialization"""

    def test_init_with_console(self, console: Console) -> None:
        """Test initialization with provided console"""
        display = BriefingDisplay(console)
        assert display.console == console

    def test_init_without_console(self) -> None:
        """Test initialization without console creates default"""
        display = BriefingDisplay()
        assert display.console is not None


class TestMorningBriefingRendering:
    """Tests for morning briefing rendering"""

    def test_render_empty_briefing(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering an empty briefing"""
        briefing = MorningBriefing(
            date=date.today(),
            generated_at=datetime.now(timezone.utc),
            total_items=0,
            urgent_count=0,
            meetings_today=0,
        )

        display.render_morning_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Morning Briefing" in output
        assert "0" in output  # meetings count

    def test_render_briefing_with_urgent_items(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering briefing with urgent items"""
        event = create_test_event(urgency=UrgencyLevel.HIGH)
        item = create_test_briefing_item(event=event)

        briefing = MorningBriefing(
            date=date.today(),
            generated_at=datetime.now(timezone.utc),
            urgent_items=[item],
            total_items=1,
            urgent_count=1,
            meetings_today=0,
        )

        display.render_morning_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Urgent" in output
        assert "Test Event" in output

    def test_render_briefing_with_calendar(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering briefing with calendar events"""
        event = create_test_event(source=EventSource.CALENDAR, title="Team Standup")
        item = create_test_briefing_item(event=event, time_context="09:00")

        briefing = MorningBriefing(
            date=date.today(),
            generated_at=datetime.now(timezone.utc),
            calendar_today=[item],
            total_items=1,
            urgent_count=0,
            meetings_today=1,
        )

        display.render_morning_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Schedule" in output
        assert "Team Standup" in output

    def test_render_briefing_with_pending_emails(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering briefing with pending emails"""
        event = create_test_event(source=EventSource.EMAIL, title="Important Email")
        item = create_test_briefing_item(event=event)

        briefing = MorningBriefing(
            date=date.today(),
            generated_at=datetime.now(timezone.utc),
            emails_pending=[item],
            total_items=1,
            urgent_count=0,
            meetings_today=0,
        )

        display.render_morning_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Communications" in output or "Pending" in output

    def test_render_briefing_with_ai_summary(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering briefing with AI summary"""
        briefing = MorningBriefing(
            date=date.today(),
            generated_at=datetime.now(timezone.utc),
            total_items=5,
            urgent_count=1,
            meetings_today=2,
            ai_summary="Busy day ahead with 2 meetings and 1 urgent item.",
        )

        display.render_morning_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Summary" in output
        assert "Busy day ahead" in output

    def test_render_briefing_quiet_mode(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering briefing in quiet mode (overview only)"""
        event = create_test_event()
        item = create_test_briefing_item(event=event)

        briefing = MorningBriefing(
            date=date.today(),
            generated_at=datetime.now(timezone.utc),
            urgent_items=[item],
            calendar_today=[item],
            emails_pending=[item],
            total_items=3,
            urgent_count=1,
            meetings_today=1,
            ai_summary="Test summary",
        )

        display.render_morning_briefing(briefing, show_details=False)

        output = console.file.getvalue()  # type: ignore
        # Overview should be shown
        assert "Morning Briefing" in output
        # Details should not be shown (no tables)
        assert "Urgent Items" not in output
        assert "Today's Schedule" not in output


class TestPreMeetingBriefingRendering:
    """Tests for pre-meeting briefing rendering"""

    def test_render_pre_meeting_briefing(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering a pre-meeting briefing"""
        event = create_test_event(
            source=EventSource.CALENDAR,
            title="Important Meeting",
        )

        briefing = PreMeetingBriefing(
            event=event,
            generated_at=datetime.now(timezone.utc),
            minutes_until_start=15,
            meeting_url="https://teams.microsoft.com/meet/123",
            location="Room 101",
        )

        display.render_pre_meeting_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Pre-Meeting" in output
        assert "Important Meeting" in output
        assert "15 min" in output

    def test_render_meeting_in_progress(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering when meeting is in progress"""
        event = create_test_event(source=EventSource.CALENDAR)

        briefing = PreMeetingBriefing(
            event=event,
            generated_at=datetime.now(timezone.utc),
            minutes_until_start=-5,  # Started 5 minutes ago
        )

        display.render_pre_meeting_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "progress" in output.lower()

    def test_render_with_attendees(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering with attendee list"""
        event = create_test_event(source=EventSource.CALENDAR)
        attendees = [
            AttendeeContext(
                name="John Doe",
                email="john@example.com",
                is_organizer=True,
                interaction_count=10,
            ),
            AttendeeContext(
                name="Jane Smith",
                email="jane@example.com",
                is_organizer=False,
                relationship_hint="New contact",
            ),
        ]

        briefing = PreMeetingBriefing(
            event=event,
            generated_at=datetime.now(timezone.utc),
            minutes_until_start=15,
            attendees=attendees,
        )

        display.render_pre_meeting_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Attendees" in output
        assert "John Doe" in output
        assert "Organizer" in output

    def test_render_with_talking_points(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering with talking points"""
        event = create_test_event(source=EventSource.CALENDAR)

        briefing = PreMeetingBriefing(
            event=event,
            generated_at=datetime.now(timezone.utc),
            minutes_until_start=15,
            talking_points=[
                "Discuss Q1 goals",
                "Review budget allocation",
            ],
        )

        display.render_pre_meeting_briefing(briefing)

        output = console.file.getvalue()  # type: ignore
        assert "Talking Points" in output
        assert "Q1 goals" in output

    def test_render_quiet_mode(
        self,
        display: BriefingDisplay,
        console: Console,
    ) -> None:
        """Test rendering in quiet mode"""
        event = create_test_event(source=EventSource.CALENDAR)
        attendees = [
            AttendeeContext(name="John", email="john@example.com"),
        ]

        briefing = PreMeetingBriefing(
            event=event,
            generated_at=datetime.now(timezone.utc),
            minutes_until_start=15,
            attendees=attendees,
            talking_points=["Point 1"],
        )

        display.render_pre_meeting_briefing(briefing, show_details=False)

        output = console.file.getvalue()  # type: ignore
        # Header should be shown
        assert "Pre-Meeting" in output
        # Details should not be shown
        assert "Attendees" not in output
        assert "Talking Points" not in output


class TestSourceBadge:
    """Tests for source badge formatting"""

    def test_email_badge(self) -> None:
        """Test email source badge"""
        display = BriefingDisplay()
        badge = display._source_badge(EventSource.EMAIL)
        assert "Email" in badge

    def test_calendar_badge(self) -> None:
        """Test calendar source badge"""
        display = BriefingDisplay()
        badge = display._source_badge(EventSource.CALENDAR)
        assert "Cal" in badge

    def test_teams_badge(self) -> None:
        """Test Teams source badge"""
        display = BriefingDisplay()
        badge = display._source_badge(EventSource.TEAMS)
        assert "Teams" in badge


class TestHelperFunctions:
    """Tests for helper functions"""

    def test_truncate_short_text(self) -> None:
        """Test truncate with short text"""
        result = _truncate("Hello", 10)
        assert result == "Hello"

    def test_truncate_long_text(self) -> None:
        """Test truncate with long text"""
        result = _truncate("Hello World", 10)
        # Function takes max_length-3 chars and adds "..." to get exactly max_length
        assert result == "Hello W..."
        assert len(result) == 10

    def test_truncate_exact_length(self) -> None:
        """Test truncate with exact length"""
        result = _truncate("Hello", 5)
        assert result == "Hello"

    def test_format_duration_zero(self) -> None:
        """Test format duration with zero"""
        assert _format_duration(0) == "-"

    def test_format_duration_minutes(self) -> None:
        """Test format duration with minutes only"""
        assert _format_duration(30) == "30m"
        assert _format_duration(45) == "45m"

    def test_format_duration_hours(self) -> None:
        """Test format duration with full hours"""
        assert _format_duration(60) == "1h"
        assert _format_duration(120) == "2h"

    def test_format_duration_mixed(self) -> None:
        """Test format duration with hours and minutes"""
        # display.py uses "1h30m" format (with 'm' suffix and zero-padding)
        assert _format_duration(90) == "1h30m"
        assert _format_duration(150) == "2h30m"
        assert _format_duration(75) == "1h15m"

    def test_truncate_very_short_max_length(self) -> None:
        """Test truncate with max_length <= 3"""
        assert _truncate("Hello", 3) == "..."
        assert _truncate("Hello", 2) == ".."
        assert _truncate("Hello", 1) == "."


class TestExtractDisplayName:
    """Tests for _extract_display_name helper function"""

    def test_extract_from_name_email_format(self) -> None:
        """Test extracting name from 'Name <email>' format"""
        from src.frontin.briefing.display import _extract_display_name
        assert _extract_display_name("John Doe <john@example.com>") == "John Doe"

    def test_extract_from_plain_email(self) -> None:
        """Test extracting from plain email"""
        from src.frontin.briefing.display import _extract_display_name
        assert _extract_display_name("john@example.com") == "john@example.com"

    def test_extract_from_empty_string(self) -> None:
        """Test extracting from empty string"""
        from src.frontin.briefing.display import _extract_display_name
        assert _extract_display_name("") == "Unknown"

    def test_extract_from_none_string(self) -> None:
        """Test extracting from None-like input"""
        from src.frontin.briefing.display import _extract_display_name
        # Empty string case
        assert _extract_display_name("") == "Unknown"

    def test_extract_from_email_only_in_brackets(self) -> None:
        """Test extracting when only email in brackets"""
        from src.frontin.briefing.display import _extract_display_name
        assert _extract_display_name("<john@example.com>") == "Unknown"
