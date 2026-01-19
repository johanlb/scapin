"""
Tests for Briefing Generator

Tests the briefing generation system.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.config_manager import BriefingConfig
from src.core.events import EventSource, EventType, PerceivedEvent, UrgencyLevel
from src.frontin.briefing.generator import BriefingGenerator

# Mock Data Provider


@dataclass
class MockBriefingDataProvider:
    """Mock data provider for testing"""

    calendar_events: list[PerceivedEvent] = field(default_factory=list)
    email_events: list[PerceivedEvent] = field(default_factory=list)
    teams_events: list[PerceivedEvent] = field(default_factory=list)
    emails_with_people: list[PerceivedEvent] = field(default_factory=list)
    teams_with_people: list[PerceivedEvent] = field(default_factory=list)

    async def get_emails_since(
        self,
        since: datetime,
        limit: int = 50,
    ) -> list[PerceivedEvent]:
        return self.email_events[:limit]

    async def get_calendar_events(
        self,
        hours_ahead: int,
        include_in_progress: bool = True,
    ) -> list[PerceivedEvent]:
        return self.calendar_events

    async def get_teams_messages(
        self,
        since: datetime,
        limit: int = 50,
    ) -> list[PerceivedEvent]:
        return self.teams_events[:limit]

    async def get_emails_with_people(
        self,
        emails: list[str],
        days: int = 7,
    ) -> list[PerceivedEvent]:
        return self.emails_with_people

    async def get_teams_with_people(
        self,
        emails: list[str],
        days: int = 7,
    ) -> list[PerceivedEvent]:
        return self.teams_with_people


# Fixtures


@pytest.fixture
def briefing_config() -> BriefingConfig:
    """Create a test briefing configuration"""
    return BriefingConfig(
        enabled=True,
        morning_hours_behind=12,
        morning_hours_ahead=24,
        pre_meeting_minutes_before=15,
        pre_meeting_context_days=7,
        max_urgent_items=5,
        max_standard_items=10,
        show_confidence=True,
        include_emails=True,
        include_calendar=True,
        include_teams=True,
    )


@pytest.fixture
def mock_provider() -> MockBriefingDataProvider:
    """Create a mock data provider"""
    return MockBriefingDataProvider()


def create_event(
    event_id: str,
    source: EventSource,
    title: str,
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
    minutes_from_now: int = 0,
    from_person: str = "Test Person <test@example.com>",
    metadata: dict | None = None,
) -> PerceivedEvent:
    """Helper to create test events with all required fields"""
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(minutes=minutes_from_now)

    base_metadata = {
        "start": start_time.isoformat(),
        "end": (start_time + timedelta(hours=1)).isoformat(),
        "duration_minutes": 60,
        "attendee_count": 2,
    }
    if metadata:
        base_metadata.update(metadata)

    return PerceivedEvent(
        event_id=event_id,
        source=source,
        source_id=f"{source.value}-{event_id}",
        occurred_at=now,  # Always use now (occurred_at cannot be after received_at)
        received_at=now,
        title=title,
        content=f"Content for {title}",
        event_type=EventType.INVITATION if source == EventSource.CALENDAR else EventType.INFORMATION,
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
        metadata=base_metadata,
        perception_confidence=0.9,
        needs_clarification=False,
        clarification_questions=[],
    )


# BriefingGenerator Tests


class TestBriefingGeneratorInit:
    """Tests for BriefingGenerator initialization"""

    def test_init_with_config(self, briefing_config: BriefingConfig) -> None:
        """Test generator initialization with config"""
        generator = BriefingGenerator(config=briefing_config)

        assert generator.config == briefing_config
        assert generator.data_provider is not None

    def test_init_with_custom_provider(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test generator initialization with custom data provider"""
        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        assert generator.data_provider == mock_provider


class TestMorningBriefingGeneration:
    """Tests for morning briefing generation"""

    @pytest.mark.asyncio
    async def test_generate_empty_briefing(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test generating briefing with no events"""
        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        assert briefing.date == date.today()
        assert briefing.total_items == 0
        assert briefing.urgent_count == 0
        assert briefing.meetings_today == 0
        assert len(briefing.urgent_items) == 0
        assert len(briefing.calendar_today) == 0
        assert len(briefing.emails_pending) == 0
        assert len(briefing.teams_unread) == 0

    @pytest.mark.asyncio
    async def test_generate_briefing_with_calendar(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test generating briefing with calendar events"""
        mock_provider.calendar_events = [
            create_event("cal-1", EventSource.CALENDAR, "Morning Standup", minutes_from_now=60),
            create_event("cal-2", EventSource.CALENDAR, "Team Meeting", minutes_from_now=180),
        ]

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        assert briefing.total_items == 2
        assert len(briefing.calendar_today) == 2
        assert briefing.meetings_today == 2  # Both have attendee_count > 1

    @pytest.mark.asyncio
    async def test_generate_briefing_with_urgent_items(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that urgent items are extracted correctly"""
        mock_provider.calendar_events = [
            create_event(
                "cal-1",
                EventSource.CALENDAR,
                "Urgent Meeting",
                urgency=UrgencyLevel.HIGH,
                minutes_from_now=30,
            ),
            create_event(
                "cal-2",
                EventSource.CALENDAR,
                "Normal Meeting",
                urgency=UrgencyLevel.MEDIUM,
                minutes_from_now=300,
            ),
        ]

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        # First meeting is urgent (HIGH urgency and within 3 hours)
        assert briefing.urgent_count == 1
        assert len(briefing.urgent_items) == 1
        assert briefing.urgent_items[0].event.title == "Urgent Meeting"

    @pytest.mark.asyncio
    async def test_calendar_within_3_hours_is_urgent(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that calendar events within 3 hours are marked urgent"""
        mock_provider.calendar_events = [
            create_event(
                "cal-1",
                EventSource.CALENDAR,
                "Soon Meeting",
                urgency=UrgencyLevel.LOW,  # Low urgency but still should be urgent
                minutes_from_now=30,  # 30 minutes from now
            ),
        ]

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        # Should be urgent because within 3 hours
        assert briefing.urgent_count == 1
        assert len(briefing.urgent_items) == 1

    @pytest.mark.asyncio
    async def test_max_urgent_items_respected(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that max_urgent_items limit is respected"""
        # Create 10 urgent events
        mock_provider.email_events = [
            create_event(
                f"email-{i}",
                EventSource.EMAIL,
                f"Urgent Email {i}",
                urgency=UrgencyLevel.CRITICAL,
            )
            for i in range(10)
        ]

        # Config limits to 5 urgent items
        generator = BriefingGenerator(
            config=briefing_config,  # max_urgent_items = 5
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        assert briefing.urgent_count == 10  # Total urgent count
        assert len(briefing.urgent_items) == 5  # Limited to 5

    @pytest.mark.asyncio
    async def test_source_filtering(
        self,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that source filtering works"""
        mock_provider.calendar_events = [
            create_event("cal-1", EventSource.CALENDAR, "Meeting"),
        ]
        mock_provider.email_events = [
            create_event("email-1", EventSource.EMAIL, "Email"),
        ]
        mock_provider.teams_events = [
            create_event("teams-1", EventSource.TEAMS, "Teams Message"),
        ]

        # Disable all but calendar
        config = BriefingConfig(
            include_emails=False,
            include_calendar=True,
            include_teams=False,
        )

        generator = BriefingGenerator(
            config=config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        assert briefing.total_items == 1
        assert len(briefing.calendar_today) == 1
        assert len(briefing.emails_pending) == 0
        assert len(briefing.teams_unread) == 0

    @pytest.mark.asyncio
    async def test_ai_summary_generated(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that AI summary is generated when show_confidence is True"""
        mock_provider.calendar_events = [
            create_event("cal-1", EventSource.CALENDAR, "Meeting"),
        ]

        generator = BriefingGenerator(
            config=briefing_config,  # show_confidence = True
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        assert briefing.ai_summary is not None
        assert "1 meetings" in briefing.ai_summary


class TestPreMeetingBriefingGeneration:
    """Tests for pre-meeting briefing generation"""

    @pytest.mark.asyncio
    async def test_generate_pre_meeting_briefing(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test generating a pre-meeting briefing"""
        event = create_event(
            "cal-1",
            EventSource.CALENDAR,
            "Important Meeting",
            minutes_from_now=30,
            metadata={
                "attendees": [
                    {"name": "John Doe", "email": "john@example.com"},
                    {"name": "Jane Smith", "email": "jane@example.com"},
                ],
                "organizer_email": "john@example.com",
                "online_url": "https://teams.microsoft.com/meet/123",
                "location": "Room 101",
            },
        )

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_pre_meeting_briefing(event)

        assert briefing.event == event
        # Allow 1-2 minutes tolerance for test execution time
        assert 28 <= briefing.minutes_until_start <= 30
        assert briefing.meeting_url == "https://teams.microsoft.com/meet/123"
        assert briefing.location == "Room 101"

    @pytest.mark.asyncio
    async def test_attendee_context_built(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that attendee context is built correctly"""
        event = create_event(
            "cal-1",
            EventSource.CALENDAR,
            "Team Meeting",
            minutes_from_now=30,
            metadata={
                "attendees": [
                    {"name": "John Doe", "email": "john@example.com"},
                    {"name": "Jane Smith", "email": "jane@example.com"},
                ],
                "organizer_email": "john@example.com",
            },
        )

        # Add some recent emails from one attendee
        mock_provider.emails_with_people = [
            create_event(
                "email-1",
                EventSource.EMAIL,
                "Previous discussion",
                from_person="John Doe <john@example.com>",
            ),
            create_event(
                "email-2",
                EventSource.EMAIL,
                "Another email",
                from_person="John Doe <john@example.com>",
            ),
        ]

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_pre_meeting_briefing(event)

        assert len(briefing.attendees) == 2

        # John should be first (organizer) and have interaction count
        john = next(a for a in briefing.attendees if a.name == "John Doe")
        assert john.is_organizer is True
        assert john.interaction_count == 2

        # Jane should have no interactions
        jane = next(a for a in briefing.attendees if a.name == "Jane Smith")
        assert jane.is_organizer is False
        assert jane.interaction_count == 0
        assert jane.relationship_hint == "New contact"

    @pytest.mark.asyncio
    async def test_talking_points_generated(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that talking points are generated"""
        event = create_event(
            "cal-1",
            EventSource.CALENDAR,
            "Quick Sync",
            minutes_from_now=5,  # Very soon
            metadata={
                "attendees": [
                    {"name": "New Person", "email": "new@example.com"},
                ],
            },
        )

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_pre_meeting_briefing(event)

        # Should have talking points about meeting starting soon
        assert len(briefing.talking_points) > 0
        assert any("soon" in p.lower() for p in briefing.talking_points)

    @pytest.mark.asyncio
    async def test_attendee_email_matching_is_case_insensitive(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test that attendee email matching works regardless of case"""
        # Attendee email with mixed case
        event = create_event(
            "cal-1",
            EventSource.CALENDAR,
            "Team Meeting",
            minutes_from_now=30,
            metadata={
                "attendees": [
                    {"name": "John Doe", "email": "John.Doe@Example.COM"},
                ],
                "organizer_email": "john.doe@example.com",
            },
        )

        # Related email uses lowercase email
        mock_provider.emails_with_people = [
            create_event(
                "email-1",
                EventSource.EMAIL,
                "Previous discussion",
                from_person="John Doe <john.doe@example.com>",  # lowercase
            ),
        ]

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_pre_meeting_briefing(event)

        # Should match despite case difference
        assert len(briefing.attendees) == 1
        john = briefing.attendees[0]
        assert john.interaction_count == 1  # Should have found the email
        assert john.is_organizer is True


class TestTimeContextFormatting:
    """Tests for time context formatting"""

    @pytest.mark.asyncio
    async def test_calendar_time_context(
        self,
        briefing_config: BriefingConfig,
        mock_provider: MockBriefingDataProvider,
    ) -> None:
        """Test time context for calendar events"""
        mock_provider.calendar_events = [
            create_event("cal-1", EventSource.CALENDAR, "Soon", minutes_from_now=15),
            create_event("cal-2", EventSource.CALENDAR, "Later", minutes_from_now=180),
        ]

        generator = BriefingGenerator(
            config=briefing_config,
            data_provider=mock_provider,
        )

        briefing = await generator.generate_morning_briefing()

        # First event should show "In X min"
        soon_item = next(
            i for i in briefing.calendar_today
            if i.event.title == "Soon"
        )
        assert "min" in soon_item.time_context.lower()

        # Later event should show time
        later_item = next(
            i for i in briefing.calendar_today
            if i.event.title == "Later"
        )
        assert ":" in later_item.time_context  # HH:MM format


class TestExtractAttendeeEmails:
    """Tests for attendee email extraction"""

    def test_extract_from_dict_format(
        self,
        briefing_config: BriefingConfig,
    ) -> None:
        """Test extracting emails from dict format attendees"""
        generator = BriefingGenerator(config=briefing_config)

        event = create_event(
            "cal-1",
            EventSource.CALENDAR,
            "Test",
            metadata={
                "attendees": [
                    {"name": "John", "email": "john@example.com"},
                    {"name": "Jane", "email": "jane@example.com"},
                ],
            },
        )

        emails = generator._extract_attendee_emails(event)

        assert emails == ["john@example.com", "jane@example.com"]

    def test_extract_from_string_format(
        self,
        briefing_config: BriefingConfig,
    ) -> None:
        """Test extracting emails from string format attendees"""
        generator = BriefingGenerator(config=briefing_config)

        event = create_event(
            "cal-1",
            EventSource.CALENDAR,
            "Test",
            metadata={
                "attendees": [
                    "john@example.com",
                    "jane@example.com",
                ],
            },
        )

        emails = generator._extract_attendee_emails(event)

        assert emails == ["john@example.com", "jane@example.com"]


class TestEmailExtraction:
    """Tests for email extraction from person strings"""

    def test_extract_email_with_angle_brackets(
        self,
        briefing_config: BriefingConfig,
    ) -> None:
        """Test extracting email from 'Name <email>' format"""
        generator = BriefingGenerator(config=briefing_config)

        email = generator._extract_email_from_person("John Doe <john@example.com>")

        assert email == "john@example.com"

    def test_extract_email_plain(
        self,
        briefing_config: BriefingConfig,
    ) -> None:
        """Test extracting plain email address"""
        generator = BriefingGenerator(config=briefing_config)

        email = generator._extract_email_from_person("john@example.com")

        assert email == "john@example.com"

    def test_extract_email_no_email(
        self,
        briefing_config: BriefingConfig,
    ) -> None:
        """Test extracting from string without email"""
        generator = BriefingGenerator(config=briefing_config)

        email = generator._extract_email_from_person("John Doe")

        assert email is None
