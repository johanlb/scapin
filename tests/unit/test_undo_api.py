"""
Tests for Queue Undo API endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app


@pytest.fixture
def mock_queue_service():
    """Create a mock queue service"""
    service = MagicMock()
    service.undo_item = AsyncMock()
    service.can_undo_item = AsyncMock()
    return service


@pytest.fixture
def test_client(mock_queue_service):
    """Create a test client with mocked dependencies"""
    app = create_app()

    # Override the queue service dependency
    from src.frontin.api.deps import get_queue_service

    app.dependency_overrides[get_queue_service] = lambda: mock_queue_service
    return TestClient(app)


class TestUndoQueueItem:
    """Tests for POST /api/queue/{id}/undo"""

    def test_undo_returns_success(self, test_client, mock_queue_service):
        """Undo returns the updated queue item"""
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
        mock_queue_service.undo_item.return_value = mock_item

        response = test_client.post("/api/queue/item-123/undo")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "item-123"
        assert data["data"]["status"] == "pending"
        mock_queue_service.undo_item.assert_called_once_with("item-123")

    def test_undo_not_found(self, test_client, mock_queue_service):
        """Undo returns 404 if item not found or cannot be undone"""
        mock_queue_service.undo_item.return_value = None

        response = test_client.post("/api/queue/nonexistent/undo")

        assert response.status_code == 404
        data = response.json()
        assert "Cannot undo" in data["detail"]


class TestCanUndoQueueItem:
    """Tests for GET /api/queue/{id}/can-undo"""

    def test_can_undo_returns_true(self, test_client, mock_queue_service):
        """Can undo returns true when undo is available"""
        mock_queue_service.can_undo_item.return_value = True

        response = test_client.get("/api/queue/item-123/can-undo")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["item_id"] == "item-123"
        assert data["data"]["can_undo"] is True

    def test_can_undo_returns_false(self, test_client, mock_queue_service):
        """Can undo returns false when undo is not available"""
        mock_queue_service.can_undo_item.return_value = False

        response = test_client.get("/api/queue/item-456/can-undo")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["item_id"] == "item-456"
        assert data["data"]["can_undo"] is False


class TestQueueServiceUndo:
    """Tests for QueueService undo methods"""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storages"""
        queue_storage = MagicMock()
        snooze_storage = MagicMock()
        action_history = MagicMock()
        return queue_storage, snooze_storage, action_history

    @pytest.mark.asyncio
    async def test_undo_item_success(self, mock_storage):
        """Undo item moves email back and updates status"""
        from src.integrations.storage.action_history import ActionRecord, ActionStatus, ActionType
        from src.frontin.api.services.queue_service import QueueService

        queue_storage, snooze_storage, action_history = mock_storage

        # Setup mock action record
        action_record = ActionRecord(
            action_id="action-123",
            action_type=ActionType.QUEUE_APPROVE,
            item_id="item-123",
            item_type="email",
            executed_at=datetime.now(timezone.utc),
            status=ActionStatus.COMPLETED,
            rollback_data={
                "original_folder": "INBOX",
                "email_id": "456",
                "destination": "Archive",
            },
        )
        action_history.get_last_action_for_item.return_value = action_record
        action_history.can_undo.return_value = True

        # Setup queue item
        queue_storage.get_item.return_value = {"id": "item-123", "status": "pending"}
        queue_storage.update_item.return_value = True

        service = QueueService(
            queue_storage=queue_storage,
            snooze_storage=snooze_storage,
            action_history=action_history,
        )

        # Mock the IMAP undo operation
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(service, "_undo_email_action", AsyncMock(return_value=True))

            result = await service.undo_item("item-123")

        assert result is not None
        action_history.mark_undone.assert_called_once()
        queue_storage.update_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_undo_item_no_action_found(self, mock_storage):
        """Undo returns None when no action found"""
        from src.frontin.api.services.queue_service import QueueService

        queue_storage, snooze_storage, action_history = mock_storage
        action_history.get_last_action_for_item.return_value = None

        service = QueueService(
            queue_storage=queue_storage,
            snooze_storage=snooze_storage,
            action_history=action_history,
        )

        result = await service.undo_item("item-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_can_undo_item_true(self, mock_storage):
        """Can undo returns True for completed action"""
        from src.integrations.storage.action_history import ActionRecord, ActionStatus, ActionType
        from src.frontin.api.services.queue_service import QueueService

        queue_storage, snooze_storage, action_history = mock_storage

        action_record = ActionRecord(
            action_id="action-123",
            action_type=ActionType.QUEUE_APPROVE,
            item_id="item-123",
            item_type="email",
            executed_at=datetime.now(timezone.utc),
            status=ActionStatus.COMPLETED,
        )
        action_history.get_last_action_for_item.return_value = action_record
        action_history.can_undo.return_value = True

        service = QueueService(
            queue_storage=queue_storage,
            snooze_storage=snooze_storage,
            action_history=action_history,
        )

        result = await service.can_undo_item("item-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_can_undo_item_false_no_action(self, mock_storage):
        """Can undo returns False when no action exists"""
        from src.frontin.api.services.queue_service import QueueService

        queue_storage, snooze_storage, action_history = mock_storage
        action_history.get_last_action_for_item.return_value = None

        service = QueueService(
            queue_storage=queue_storage,
            snooze_storage=snooze_storage,
            action_history=action_history,
        )

        result = await service.can_undo_item("item-123")

        assert result is False
