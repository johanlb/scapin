"""
Tests for Briefing API Router

Tests morning and pre-meeting briefing endpoints.
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.events import EventSource, EventType, PerceivedEvent, UrgencyLevel
from src.jeeves.api.app import create_app
from src.jeeves.api.deps import get_briefing_service
from src.jeeves.briefing.models import (
    AttendeeContext,
    BriefingItem,
    MorningBriefing,
    PreMeetingBriefing,
)


@pytest.fixture
def sample_event() -> PerceivedEvent:
    """Create a sample PerceivedEvent"""
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
        metadata={},
        perception_confidence=0.85,
        needs_clarification=False,
        clarification_questions=[],
    )


@pytest.fixture
def sample_morning_briefing(sample_event: PerceivedEvent) -> MorningBriefing:
    """Create a sample MorningBriefing"""
    now = datetime.now(timezone.utc)
    item = BriefingItem(
        event=sample_event,
        priority_rank=1,
        time_context="2h ago",
        confidence=0.85,
    )
    return MorningBriefing(
        date=date.today(),
        generated_at=now,
        urgent_items=[item],
        calendar_today=[],
        emails_pending=[item],
        teams_unread=[],
        total_items=2,
        urgent_count=1,
        meetings_today=0,
        ai_summary="One urgent email to review.",
    )


@pytest.fixture
def sample_pre_meeting_briefing(sample_event: PerceivedEvent) -> PreMeetingBriefing:
    """Create a sample PreMeetingBriefing"""
    now = datetime.now(timezone.utc)
    attendee = AttendeeContext(
        name="John Doe",
        email="john@example.com",
        is_organizer=True,
        interaction_count=5,
        relationship_hint="Frequent contact",
    )
    return PreMeetingBriefing(
        event=sample_event,
        generated_at=now,
        minutes_until_start=15,
        attendees=[attendee],
        recent_emails=[],
        recent_teams=[],
        meeting_url="https://teams.microsoft.com/meet/123",
        location="Room 101",
        talking_points=["Discuss Q1 goals"],
        open_items=["Follow up on budget"],
    )


@pytest.fixture
def mock_service() -> MagicMock:
    """Create a mock BriefingService"""
    return MagicMock()


@pytest.fixture
def client(mock_service: MagicMock) -> TestClient:
    """Create test client with mocked briefing service"""
    app = create_app()
    # Override dependency
    app.dependency_overrides[get_briefing_service] = lambda: mock_service
    yield TestClient(app)
    # Clear overrides after test
    app.dependency_overrides.clear()


class TestMorningBriefingEndpoint:
    """Tests for GET /api/briefing/morning endpoint"""

    def test_morning_briefing_returns_success(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_morning_briefing: MorningBriefing,
    ) -> None:
        """Test morning briefing endpoint returns success"""
        mock_service.generate_morning_briefing = AsyncMock(
            return_value=sample_morning_briefing
        )

        response = client.get("/api/briefing/morning")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_morning_briefing_includes_counts(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_morning_briefing: MorningBriefing,
    ) -> None:
        """Test morning briefing includes item counts"""
        mock_service.generate_morning_briefing = AsyncMock(
            return_value=sample_morning_briefing
        )

        response = client.get("/api/briefing/morning")

        data = response.json()["data"]
        assert data["urgent_count"] == 1
        assert data["meetings_today"] == 0
        assert data["total_items"] == 2

    def test_morning_briefing_includes_items(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_morning_briefing: MorningBriefing,
    ) -> None:
        """Test morning briefing includes item lists"""
        mock_service.generate_morning_briefing = AsyncMock(
            return_value=sample_morning_briefing
        )

        response = client.get("/api/briefing/morning")

        data = response.json()["data"]
        assert len(data["urgent_items"]) == 1
        assert len(data["emails_pending"]) == 1
        assert data["urgent_items"][0]["title"] == "Test Email Subject"

    def test_morning_briefing_with_hours_param(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_morning_briefing: MorningBriefing,
    ) -> None:
        """Test morning briefing accepts hours_ahead parameter"""
        mock_service.generate_morning_briefing = AsyncMock(
            return_value=sample_morning_briefing
        )

        response = client.get("/api/briefing/morning?hours_ahead=12")

        assert response.status_code == 200
        mock_service.generate_morning_briefing.assert_called_once_with(hours_ahead=12)

    def test_morning_briefing_includes_ai_summary(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_morning_briefing: MorningBriefing,
    ) -> None:
        """Test morning briefing includes AI summary"""
        mock_service.generate_morning_briefing = AsyncMock(
            return_value=sample_morning_briefing
        )

        response = client.get("/api/briefing/morning")

        data = response.json()["data"]
        assert data["ai_summary"] == "One urgent email to review."


class TestPreMeetingBriefingEndpoint:
    """Tests for GET /api/briefing/meeting/{event_id} endpoint"""

    def test_pre_meeting_briefing_returns_success(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_pre_meeting_briefing: PreMeetingBriefing,
    ) -> None:
        """Test pre-meeting briefing endpoint returns success"""
        mock_service.generate_pre_meeting_briefing = AsyncMock(
            return_value=sample_pre_meeting_briefing
        )

        response = client.get("/api/briefing/meeting/event-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_pre_meeting_briefing_includes_attendees(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_pre_meeting_briefing: PreMeetingBriefing,
    ) -> None:
        """Test pre-meeting briefing includes attendees"""
        mock_service.generate_pre_meeting_briefing = AsyncMock(
            return_value=sample_pre_meeting_briefing
        )

        response = client.get("/api/briefing/meeting/event-123")

        data = response.json()["data"]
        assert len(data["attendees"]) == 1
        assert data["attendees"][0]["name"] == "John Doe"
        assert data["attendees"][0]["is_organizer"] is True

    def test_pre_meeting_briefing_includes_meeting_details(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_pre_meeting_briefing: PreMeetingBriefing,
    ) -> None:
        """Test pre-meeting briefing includes meeting URL and location"""
        mock_service.generate_pre_meeting_briefing = AsyncMock(
            return_value=sample_pre_meeting_briefing
        )

        response = client.get("/api/briefing/meeting/event-123")

        data = response.json()["data"]
        assert data["meeting_url"] == "https://teams.microsoft.com/meet/123"
        assert data["location"] == "Room 101"
        assert data["minutes_until_start"] == 15

    def test_pre_meeting_briefing_includes_talking_points(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_pre_meeting_briefing: PreMeetingBriefing,
    ) -> None:
        """Test pre-meeting briefing includes talking points"""
        mock_service.generate_pre_meeting_briefing = AsyncMock(
            return_value=sample_pre_meeting_briefing
        )

        response = client.get("/api/briefing/meeting/event-123")

        data = response.json()["data"]
        assert data["talking_points"] == ["Discuss Q1 goals"]
        assert data["open_items"] == ["Follow up on budget"]

    def test_pre_meeting_briefing_not_found(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        """Test pre-meeting briefing returns 404 for unknown event"""
        mock_service.generate_pre_meeting_briefing = AsyncMock(
            side_effect=ValueError("Calendar event not found: unknown-event")
        )

        response = client.get("/api/briefing/meeting/unknown-event")

        assert response.status_code == 404
