"""
Tests for Calendar API endpoints

Tests for POST, PUT, DELETE /api/calendar/events endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch  # noqa: F401 - patch used in service tests

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app
from src.frontin.api.models.calendar import (
    CreateEventRequest,
    EventCreatedResponse,
    EventDeletedResponse,
    UpdateEventRequest,
)
from src.frontin.api.routers.calendar import _get_calendar_service


@pytest.fixture
def mock_calendar_service():
    """Create mock calendar service"""
    return AsyncMock()


@pytest.fixture
def app(mock_calendar_service):
    """Create test app with mocked service"""
    app = create_app()
    app.dependency_overrides[_get_calendar_service] = lambda: mock_calendar_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestCalendarModels:
    """Tests for calendar API models"""

    def test_create_event_request_valid(self):
        """CreateEventRequest validates correctly"""
        now = datetime.now(timezone.utc)
        request = CreateEventRequest(
            title="Test Meeting",
            start=now,
            end=now + timedelta(hours=1),
            location="Conference Room A",
            description="Test description",
            attendees=["user@example.com"],
            is_online=False,
            reminder_minutes=15,
        )
        assert request.title == "Test Meeting"
        assert request.attendees == ["user@example.com"]

    def test_create_event_request_minimal(self):
        """CreateEventRequest with minimal fields"""
        now = datetime.now(timezone.utc)
        request = CreateEventRequest(
            title="Quick Meeting",
            start=now,
            end=now + timedelta(hours=1),
        )
        assert request.title == "Quick Meeting"
        assert request.location is None
        assert request.is_online is False

    def test_update_event_request_partial(self):
        """UpdateEventRequest allows partial updates"""
        request = UpdateEventRequest(
            title="Updated Title",
        )
        assert request.title == "Updated Title"
        assert request.start is None
        assert request.end is None

    def test_event_created_response(self):
        """EventCreatedResponse structure"""
        now = datetime.now(timezone.utc)
        response = EventCreatedResponse(
            id="event123",
            title="New Meeting",
            start=now,
            end=now + timedelta(hours=1),
            web_link="https://outlook.com/event/123",
            meeting_url="https://teams.microsoft.com/meeting/123",
        )
        assert response.id == "event123"
        assert response.meeting_url is not None

    def test_event_deleted_response(self):
        """EventDeletedResponse structure"""
        response = EventDeletedResponse(
            event_id="event123",
            deleted=True,
        )
        assert response.event_id == "event123"
        assert response.deleted is True


class TestCalendarServiceMethods:
    """Tests for CalendarService methods"""

    @pytest.mark.asyncio
    async def test_create_event_disabled(self):
        """create_event returns None when calendar disabled"""
        from src.frontin.api.services.calendar_service import CalendarService

        with patch("src.frontin.api.services.calendar_service.get_config") as mock_config:
            mock_config.return_value.calendar.enabled = False
            service = CalendarService()

            now = datetime.now(timezone.utc)
            result = await service.create_event(
                title="Test",
                start=now,
                end=now + timedelta(hours=1),
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_update_event_disabled(self):
        """update_event returns None when calendar disabled"""
        from src.frontin.api.services.calendar_service import CalendarService

        with patch("src.frontin.api.services.calendar_service.get_config") as mock_config:
            mock_config.return_value.calendar.enabled = False
            service = CalendarService()

            result = await service.update_event(
                event_id="event123",
                title="Updated",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_event_disabled(self):
        """delete_event returns False when calendar disabled"""
        from src.frontin.api.services.calendar_service import CalendarService

        with patch("src.frontin.api.services.calendar_service.get_config") as mock_config:
            mock_config.return_value.calendar.enabled = False
            service = CalendarService()

            result = await service.delete_event("event123")

            assert result is False


class TestCreateEventEndpoint:
    """Tests for POST /api/calendar/events"""

    def test_create_event_success(self, client, mock_calendar_service):
        """Create event returns success"""
        mock_calendar_service.create_event.return_value = {
            "id": "event123",
            "title": "Test Meeting",
            "start": "2026-01-07T10:00:00+00:00",
            "end": "2026-01-07T11:00:00+00:00",
            "web_link": "https://outlook.com/event/123",
            "meeting_url": None,
        }

        response = client.post(
            "/api/calendar/events",
            json={
                "title": "Test Meeting",
                "start": "2026-01-07T10:00:00+00:00",
                "end": "2026-01-07T11:00:00+00:00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "event123"
        assert data["data"]["title"] == "Test Meeting"

    def test_create_event_with_teams_meeting(self, client, mock_calendar_service):
        """Create event as Teams meeting"""
        mock_calendar_service.create_event.return_value = {
            "id": "event456",
            "title": "Teams Call",
            "start": "2026-01-07T14:00:00+00:00",
            "end": "2026-01-07T15:00:00+00:00",
            "web_link": "https://outlook.com/event/456",
            "meeting_url": "https://teams.microsoft.com/meet/456",
        }

        response = client.post(
            "/api/calendar/events",
            json={
                "title": "Teams Call",
                "start": "2026-01-07T14:00:00+00:00",
                "end": "2026-01-07T15:00:00+00:00",
                "is_online": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["meeting_url"] == "https://teams.microsoft.com/meet/456"

    def test_create_event_invalid_times(self, client, mock_calendar_service):
        """Create event fails when start >= end"""
        response = client.post(
            "/api/calendar/events",
            json={
                "title": "Invalid Meeting",
                "start": "2026-01-07T11:00:00+00:00",
                "end": "2026-01-07T10:00:00+00:00",  # Before start
            },
        )

        assert response.status_code == 400
        assert "Start time must be before end time" in response.json()["detail"]

    def test_create_event_service_failure(self, client, mock_calendar_service):
        """Create event returns 500 when service fails"""
        mock_calendar_service.create_event.return_value = None  # Service failed

        response = client.post(
            "/api/calendar/events",
            json={
                "title": "Test Meeting",
                "start": "2026-01-07T10:00:00+00:00",
                "end": "2026-01-07T11:00:00+00:00",
            },
        )

        assert response.status_code == 500


class TestUpdateEventEndpoint:
    """Tests for PUT /api/calendar/events/{event_id}"""

    def test_update_event_success(self, client, mock_calendar_service):
        """Update event returns success"""
        mock_calendar_service.update_event.return_value = {
            "id": "event123",
            "title": "Updated Meeting",
            "start": "2026-01-07T10:00:00",
            "end": "2026-01-07T11:00:00",
            "location": "New Room",
            "is_online": False,
            "meeting_url": None,
            "organizer": "user@example.com",
            "attendees": [],
            "is_all_day": False,
            "is_recurring": False,
            "description": None,
            "status": "confirmed",
        }

        response = client.put(
            "/api/calendar/events/event123",
            json={
                "title": "Updated Meeting",
                "location": "New Room",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Updated Meeting"

    def test_update_event_not_found(self, client, mock_calendar_service):
        """Update non-existent event returns 404"""
        mock_calendar_service.update_event.return_value = None

        response = client.put(
            "/api/calendar/events/nonexistent",
            json={"title": "Updated"},
        )

        assert response.status_code == 404

    def test_update_event_invalid_times(self, client, mock_calendar_service):
        """Update event fails when start >= end"""
        response = client.put(
            "/api/calendar/events/event123",
            json={
                "start": "2026-01-07T11:00:00+00:00",
                "end": "2026-01-07T10:00:00+00:00",  # Before start
            },
        )

        assert response.status_code == 400


class TestDeleteEventEndpoint:
    """Tests for DELETE /api/calendar/events/{event_id}"""

    def test_delete_event_success(self, client, mock_calendar_service):
        """Delete event returns success"""
        mock_calendar_service.delete_event.return_value = True

        response = client.delete("/api/calendar/events/event123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["event_id"] == "event123"
        assert data["data"]["deleted"] is True

    def test_delete_event_not_found(self, client, mock_calendar_service):
        """Delete non-existent event returns 404"""
        mock_calendar_service.delete_event.return_value = False

        response = client.delete("/api/calendar/events/nonexistent")

        assert response.status_code == 404
