"""
Tests for Queue Snooze API endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.jeeves.api.app import create_app


@pytest.fixture
def mock_queue_service():
    """Create a mock queue service"""
    service = MagicMock()
    service.snooze_item = AsyncMock()
    service.unsnooze_item = AsyncMock()
    return service


@pytest.fixture
def test_client(mock_queue_service):
    """Create a test client with mocked dependencies"""
    app = create_app()

    # Override the queue service dependency
    from src.jeeves.api.deps import get_queue_service

    app.dependency_overrides[get_queue_service] = lambda: mock_queue_service
    return TestClient(app)


class TestSnoozeQueueItem:
    """Tests for POST /api/queue/{id}/snooze"""

    def test_snooze_later_today_returns_success(self, test_client, mock_queue_service):
        """Snooze with later_today option returns success"""
        from src.integrations.storage.snooze_storage import SnoozeReason, SnoozeRecord

        now = datetime.now(timezone.utc)
        mock_record = SnoozeRecord(
            snooze_id="snz-123",
            item_id="item-456",
            item_type="queue_item",
            snoozed_at=now,
            snooze_until=now + timedelta(hours=3),
            reason=SnoozeReason.LATER_TODAY,
        )
        mock_queue_service.snooze_item.return_value = mock_record

        response = test_client.post(
            "/api/queue/item-456/snooze",
            json={"snooze_option": "later_today"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["snooze_id"] == "snz-123"
        assert data["data"]["item_id"] == "item-456"
        assert data["data"]["snooze_option"] == "later_today"

    def test_snooze_tomorrow_returns_success(self, test_client, mock_queue_service):
        """Snooze with tomorrow option returns success"""
        from src.integrations.storage.snooze_storage import SnoozeReason, SnoozeRecord

        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)
        mock_record = SnoozeRecord(
            snooze_id="snz-456",
            item_id="item-789",
            item_type="queue_item",
            snoozed_at=now,
            snooze_until=tomorrow.replace(hour=9, minute=0, second=0),
            reason=SnoozeReason.TOMORROW,
        )
        mock_queue_service.snooze_item.return_value = mock_record

        response = test_client.post(
            "/api/queue/item-789/snooze",
            json={"snooze_option": "tomorrow"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["snooze_option"] == "tomorrow"

    def test_snooze_custom_hours_returns_success(self, test_client, mock_queue_service):
        """Snooze with custom hours returns success"""
        from src.integrations.storage.snooze_storage import SnoozeReason, SnoozeRecord

        now = datetime.now(timezone.utc)
        mock_record = SnoozeRecord(
            snooze_id="snz-789",
            item_id="item-abc",
            item_type="queue_item",
            snoozed_at=now,
            snooze_until=now + timedelta(hours=24),
            reason=SnoozeReason.CUSTOM,
        )
        mock_queue_service.snooze_item.return_value = mock_record

        response = test_client.post(
            "/api/queue/item-abc/snooze",
            json={"snooze_option": "custom", "custom_hours": 24},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["snooze_option"] == "custom"

    def test_snooze_not_found(self, test_client, mock_queue_service):
        """Snooze returns 404 if item not found"""
        mock_queue_service.snooze_item.return_value = None

        response = test_client.post(
            "/api/queue/nonexistent/snooze",
            json={"snooze_option": "tomorrow"},
        )

        assert response.status_code == 404

    def test_snooze_with_reason(self, test_client, mock_queue_service):
        """Snooze with optional reason"""
        from src.integrations.storage.snooze_storage import SnoozeReason, SnoozeRecord

        now = datetime.now(timezone.utc)
        mock_record = SnoozeRecord(
            snooze_id="snz-100",
            item_id="item-200",
            item_type="queue_item",
            snoozed_at=now,
            snooze_until=now + timedelta(days=7),
            reason=SnoozeReason.NEXT_WEEK,
            reason_text="Waiting for response",
        )
        mock_queue_service.snooze_item.return_value = mock_record

        response = test_client.post(
            "/api/queue/item-200/snooze",
            json={
                "snooze_option": "next_week",
                "reason": "Waiting for response",
            },
        )

        assert response.status_code == 200
        mock_queue_service.snooze_item.assert_called_once_with(
            item_id="item-200",
            snooze_option="next_week",
            custom_hours=None,
            reason="Waiting for response",
        )


class TestUnsnoozeQueueItem:
    """Tests for POST /api/queue/{id}/unsnooze"""

    def test_unsnooze_returns_success(self, test_client, mock_queue_service):
        """Unsnooze returns the updated queue item"""
        mock_item = {
            "id": "item-123",
            "status": "pending",
            "queued_at": "2026-01-07T10:00:00Z",
            "metadata": {
                "id": "123",
                "subject": "Test Email",
                "from_address": "test@example.com",
                "from_name": "Test",
            },
            "analysis": {
                "action": "archive",
                "confidence": 85,
                "reasoning": "Test",
            },
            "content": {"preview": "Test content"},
        }
        mock_queue_service.unsnooze_item.return_value = mock_item

        response = test_client.post("/api/queue/item-123/unsnooze")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "item-123"
        assert data["data"]["status"] == "pending"

    def test_unsnooze_not_found(self, test_client, mock_queue_service):
        """Unsnooze returns 404 if item not found or not snoozed"""
        mock_queue_service.unsnooze_item.return_value = None

        response = test_client.post("/api/queue/nonexistent/unsnooze")

        assert response.status_code == 404


class TestSnoozeRequestValidation:
    """Tests for SnoozeRequest validation"""

    def test_snooze_requires_option(self, test_client, mock_queue_service):
        """Snooze request requires snooze_option"""
        response = test_client.post(
            "/api/queue/item-123/snooze",
            json={},
        )

        assert response.status_code == 422  # Validation error

    def test_snooze_custom_hours_max_limit(self, test_client, mock_queue_service):
        """Custom hours cannot exceed 168 (7 days)"""
        response = test_client.post(
            "/api/queue/item-123/snooze",
            json={"snooze_option": "custom", "custom_hours": 200},
        )

        assert response.status_code == 422  # Validation error

    def test_snooze_custom_hours_min_limit(self, test_client, mock_queue_service):
        """Custom hours must be at least 1"""
        response = test_client.post(
            "/api/queue/item-123/snooze",
            json={"snooze_option": "custom", "custom_hours": 0},
        )

        assert response.status_code == 422  # Validation error
