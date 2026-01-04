"""
Tests for Calendar API Router

Tests calendar event listing, today's events, responding, and polling endpoints.
"""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.jeeves.api.app import create_app
from src.jeeves.api.routers.calendar import _get_calendar_service


@pytest.fixture
def mock_calendar_service() -> MagicMock:
    """Create mock calendar service"""
    service = MagicMock()

    # Sample calendar event
    service.sample_event = {
        "id": "event-123",
        "title": "Team Standup",
        "start": "2026-01-04T09:00:00+00:00",
        "end": "2026-01-04T09:30:00+00:00",
        "location": "Conference Room A",
        "is_online": True,
        "meeting_url": "https://teams.microsoft.com/meet/123",
        "organizer": "boss@example.com",
        "attendees": [
            {
                "email": "user@example.com",
                "name": "Current User",
                "response_status": "accepted",
                "is_organizer": False,
            },
            {
                "email": "boss@example.com",
                "name": "Boss",
                "response_status": "organizer",
                "is_organizer": True,
            },
        ],
        "is_all_day": False,
        "is_recurring": True,
        "description": "Daily standup meeting",
        "status": "confirmed",
    }

    # Mock async methods
    service.get_events = AsyncMock(return_value=[service.sample_event])
    service.get_event = AsyncMock(return_value=service.sample_event)
    service.get_today_events = AsyncMock(return_value={
        "date": "2026-01-04",
        "total_events": 5,
        "meetings": 4,
        "all_day_events": 1,
        "events": [service.sample_event],
    })
    service.respond_to_event = AsyncMock(return_value=True)
    service.poll = AsyncMock(return_value={
        "events_fetched": 15,
        "events_new": 3,
        "events_updated": 2,
        "polled_at": "2026-01-04T10:00:00+00:00",
    })

    return service


@pytest.fixture
def client(mock_calendar_service: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked service"""
    app = create_app()
    app.dependency_overrides[_get_calendar_service] = lambda: mock_calendar_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListCalendarEvents:
    """Tests for GET /api/calendar/events endpoint"""

    def test_list_returns_success(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test listing events returns success"""
        response = client.get("/api/calendar/events")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_list_includes_pagination(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test listing includes pagination info"""
        response = client.get("/api/calendar/events?page=1&page_size=20")

        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "has_more" in data
        assert "total" in data

    def test_list_filters_by_date_range(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test listing can filter by date range"""
        response = client.get(
            "/api/calendar/events?start_date=2026-01-04T00:00:00&end_date=2026-01-05T00:00:00"
        )

        assert response.status_code == 200
        mock_calendar_service.get_events.assert_called_once()

    def test_list_event_includes_attendees(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test events include attendee information"""
        response = client.get("/api/calendar/events")

        data = response.json()["data"][0]
        assert "attendees" in data
        assert len(data["attendees"]) == 2
        assert data["attendees"][0]["email"] == "user@example.com"


class TestGetCalendarEvent:
    """Tests for GET /api/calendar/events/{event_id} endpoint"""

    def test_get_event_returns_success(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test getting single event returns success"""
        response = client.get("/api/calendar/events/event-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "event-123"

    def test_get_event_not_found(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test getting non-existent event returns 404"""
        mock_calendar_service.get_event = AsyncMock(return_value=None)

        response = client.get("/api/calendar/events/non-existent")

        assert response.status_code == 404

    def test_get_event_includes_full_details(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test event includes all details"""
        response = client.get("/api/calendar/events/event-123")

        data = response.json()["data"]
        assert data["title"] == "Team Standup"
        assert data["is_online"] is True
        assert data["meeting_url"] == "https://teams.microsoft.com/meet/123"
        assert data["is_recurring"] is True


class TestGetTodayEvents:
    """Tests for GET /api/calendar/today endpoint"""

    def test_today_returns_success(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test getting today's events returns success"""
        response = client.get("/api/calendar/today")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_today_includes_summary(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test today includes summary counts"""
        response = client.get("/api/calendar/today")

        data = response.json()["data"]
        assert data["date"] == "2026-01-04"
        assert data["total_events"] == 5
        assert data["meetings"] == 4
        assert data["all_day_events"] == 1

    def test_today_includes_events(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test today includes event list"""
        response = client.get("/api/calendar/today")

        data = response.json()["data"]
        assert "events" in data
        assert len(data["events"]) == 1


class TestRespondToEvent:
    """Tests for POST /api/calendar/events/{event_id}/respond endpoint"""

    def test_respond_accept_success(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test accepting invitation returns success"""
        response = client.post(
            "/api/calendar/events/event-123/respond",
            json={"response": "accept"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["sent"] is True

    def test_respond_decline_success(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test declining invitation returns success"""
        response = client.post(
            "/api/calendar/events/event-123/respond",
            json={"response": "decline"},
        )

        assert response.status_code == 200

    def test_respond_tentative_success(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test tentative response returns success"""
        response = client.post(
            "/api/calendar/events/event-123/respond",
            json={"response": "tentative"},
        )

        assert response.status_code == 200

    def test_respond_with_message(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test responding with message"""
        response = client.post(
            "/api/calendar/events/event-123/respond",
            json={"response": "decline", "message": "I have a conflict"},
        )

        assert response.status_code == 200
        call_kwargs = mock_calendar_service.respond_to_event.call_args[1]
        assert call_kwargs["message"] == "I have a conflict"

    def test_respond_invalid_response(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test invalid response type returns 400"""
        response = client.post(
            "/api/calendar/events/event-123/respond",
            json={"response": "maybe"},
        )

        # 400 for invalid response type (validated in endpoint)
        assert response.status_code == 400

    def test_respond_failure(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test respond failure returns 400"""
        mock_calendar_service.respond_to_event = AsyncMock(return_value=False)

        response = client.post(
            "/api/calendar/events/event-123/respond",
            json={"response": "accept"},
        )

        assert response.status_code == 400


class TestPollCalendar:
    """Tests for POST /api/calendar/poll endpoint"""

    def test_poll_returns_success(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test polling returns success"""
        response = client.post("/api/calendar/poll")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_poll_includes_counts(self, client: TestClient, mock_calendar_service: MagicMock) -> None:
        """Test poll includes event counts"""
        response = client.post("/api/calendar/poll")

        data = response.json()["data"]
        assert data["events_fetched"] == 15
        assert data["events_new"] == 3
        assert data["events_updated"] == 2
        assert "polled_at" in data
