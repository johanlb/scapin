"""
Tests for Events API (Snooze/Undo)
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.integrations.storage.action_history import (
    ActionHistoryStorage,
    ActionRecord,
    ActionStatus,
    ActionType,
)
from src.integrations.storage.snooze_storage import (
    SnoozeReason,
    SnoozeRecord,
    SnoozeStorage,
)
from src.jeeves.api.services.events_service import EventsService


class TestActionHistoryStorage:
    """Tests for ActionHistoryStorage"""

    def test_create_action(self, tmp_path: Path) -> None:
        """Test creating an action record"""
        storage = ActionHistoryStorage(actions_dir=tmp_path)

        record = storage.create_action(
            action_type=ActionType.EMAIL_ARCHIVE,
            item_id="email-123",
            item_type="email",
            action_data={"destination": "Archive/Work"},
            rollback_data={"original_folder": "INBOX"},
            account_id="personal",
        )

        assert record.action_id is not None
        assert record.action_type == ActionType.EMAIL_ARCHIVE
        assert record.item_id == "email-123"
        assert record.item_type == "email"
        assert record.status == ActionStatus.COMPLETED
        assert record.action_data["destination"] == "Archive/Work"

        # Verify file was created
        file_path = tmp_path / f"{record.action_id}.json"
        assert file_path.exists()

    def test_get_action(self, tmp_path: Path) -> None:
        """Test retrieving an action record"""
        storage = ActionHistoryStorage(actions_dir=tmp_path)

        # Create action
        record = storage.create_action(
            action_type=ActionType.QUEUE_APPROVE,
            item_id="queue-456",
            item_type="queue_item",
        )

        # Retrieve it
        retrieved = storage.get_action(record.action_id)
        assert retrieved is not None
        assert retrieved.action_id == record.action_id
        assert retrieved.action_type == ActionType.QUEUE_APPROVE

    def test_get_action_not_found(self, tmp_path: Path) -> None:
        """Test retrieving non-existent action"""
        storage = ActionHistoryStorage(actions_dir=tmp_path)
        result = storage.get_action("non-existent")
        assert result is None

    def test_get_actions_for_item(self, tmp_path: Path) -> None:
        """Test getting all actions for an item"""
        storage = ActionHistoryStorage(actions_dir=tmp_path)

        # Create multiple actions for same item
        storage.create_action(
            action_type=ActionType.EMAIL_ARCHIVE,
            item_id="email-789",
            item_type="email",
        )
        storage.create_action(
            action_type=ActionType.EMAIL_FLAG,
            item_id="email-789",
            item_type="email",
        )
        storage.create_action(
            action_type=ActionType.EMAIL_ARCHIVE,
            item_id="email-other",
            item_type="email",
        )

        # Get actions for specific item
        actions = storage.get_actions_for_item("email-789")
        assert len(actions) == 2

    def test_get_recent_actions(self, tmp_path: Path) -> None:
        """Test getting recent actions"""
        storage = ActionHistoryStorage(actions_dir=tmp_path)

        # Create actions
        for i in range(5):
            storage.create_action(
                action_type=ActionType.QUEUE_APPROVE,
                item_id=f"item-{i}",
                item_type="queue_item",
            )

        actions = storage.get_recent_actions(limit=3)
        assert len(actions) == 3

    def test_mark_undone(self, tmp_path: Path) -> None:
        """Test marking an action as undone"""
        storage = ActionHistoryStorage(actions_dir=tmp_path)

        record = storage.create_action(
            action_type=ActionType.EMAIL_DELETE,
            item_id="email-delete",
            item_type="email",
        )

        assert storage.can_undo(record.action_id)

        # Mark as undone
        success = storage.mark_undone(record.action_id, undo_result={"restored": True})
        assert success

        # Verify status changed
        updated = storage.get_action(record.action_id)
        assert updated is not None
        assert updated.status == ActionStatus.UNDONE
        assert updated.undone_at is not None

        # Can no longer undo
        assert not storage.can_undo(record.action_id)

    def test_get_stats(self, tmp_path: Path) -> None:
        """Test getting action statistics"""
        storage = ActionHistoryStorage(actions_dir=tmp_path)

        # Create mixed actions
        storage.create_action(
            action_type=ActionType.EMAIL_ARCHIVE,
            item_id="e1",
            item_type="email",
        )
        storage.create_action(
            action_type=ActionType.TEAMS_REPLY,
            item_id="t1",
            item_type="teams_message",
        )

        stats = storage.get_stats()
        assert stats["total"] == 2
        assert "email_archive" in stats["by_type"]
        assert "teams_reply" in stats["by_type"]


class TestSnoozeStorage:
    """Tests for SnoozeStorage"""

    def test_snooze_item(self, tmp_path: Path) -> None:
        """Test snoozing an item"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        snooze_until = datetime.now(timezone.utc) + timedelta(hours=3)
        record = storage.snooze_item(
            item_id="queue-123",
            item_type="queue_item",
            snooze_until=snooze_until,
            reason=SnoozeReason.LATER_TODAY,
            reason_text="Handle after lunch",
        )

        assert record.snooze_id is not None
        assert record.item_id == "queue-123"
        assert record.is_active
        assert record.reason == SnoozeReason.LATER_TODAY

    def test_snooze_for_duration(self, tmp_path: Path) -> None:
        """Test snoozing for a duration"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        record = storage.snooze_for_duration(
            item_id="queue-456",
            item_type="queue_item",
            hours=6,
        )

        assert record.is_active
        # Should be approximately 6 hours from now
        expected = datetime.now(timezone.utc) + timedelta(hours=6)
        delta = abs((record.snooze_until - expected).total_seconds())
        assert delta < 5  # Within 5 seconds

    def test_get_snooze_for_item(self, tmp_path: Path) -> None:
        """Test getting active snooze for an item"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        # Snooze an item
        storage.snooze_for_duration(
            item_id="item-123",
            item_type="queue_item",
            hours=1,
        )

        # Find it
        record = storage.get_snooze_for_item("item-123")
        assert record is not None
        assert record.item_id == "item-123"

    def test_get_snoozed_items(self, tmp_path: Path) -> None:
        """Test getting all snoozed items"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        # Snooze multiple items
        storage.snooze_for_duration("item-1", "queue_item", hours=1)
        storage.snooze_for_duration("item-2", "queue_item", hours=2)
        storage.snooze_for_duration("item-3", "email", hours=3)

        # Get all
        items = storage.get_snoozed_items()
        assert len(items) == 3

        # Filter by type
        queue_items = storage.get_snoozed_items(item_type="queue_item")
        assert len(queue_items) == 2

    def test_get_expired_snoozes(self, tmp_path: Path) -> None:
        """Test getting expired snoozes"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        # Create expired snooze (in the past)
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        storage.snooze_item("item-expired", "queue_item", snooze_until=past_time)

        # Create active snooze (in the future)
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        storage.snooze_item("item-active", "queue_item", snooze_until=future_time)

        expired = storage.get_expired_snoozes()
        assert len(expired) == 1
        assert expired[0].item_id == "item-expired"

    def test_unsnooze_item(self, tmp_path: Path) -> None:
        """Test unsnoozing an item"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        # Snooze
        storage.snooze_for_duration("item-unsnooze", "queue_item", hours=2)

        # Verify active
        assert storage.get_snooze_for_item("item-unsnooze") is not None

        # Unsnooze
        record = storage.unsnooze_item("item-unsnooze")
        assert record is not None
        assert not record.is_active
        assert record.woken_at is not None

        # No longer found as active
        assert storage.get_snooze_for_item("item-unsnooze") is None

    def test_wake_expired_snoozes(self, tmp_path: Path) -> None:
        """Test waking up expired snoozes"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        # Create expired snoozes
        past = datetime.now(timezone.utc) - timedelta(minutes=30)
        storage.snooze_item("exp-1", "queue_item", snooze_until=past)
        storage.snooze_item("exp-2", "queue_item", snooze_until=past)

        # Wake them
        woken = storage.wake_expired_snoozes()
        assert len(woken) == 2

        # No more expired
        assert len(storage.get_expired_snoozes()) == 0

    def test_get_stats(self, tmp_path: Path) -> None:
        """Test getting snooze statistics"""
        storage = SnoozeStorage(snoozes_dir=tmp_path)

        # Create snoozes
        storage.snooze_for_duration(
            "s1", "queue_item", hours=1, reason=SnoozeReason.LATER_TODAY
        )
        storage.snooze_for_duration(
            "s2", "email", hours=24, reason=SnoozeReason.TOMORROW
        )

        stats = storage.get_stats()
        assert stats["total"] == 2
        assert stats["active"] == 2
        assert "later_today" in stats["by_reason"]


class TestEventsService:
    """Tests for EventsService"""

    @pytest.fixture
    def mock_queue_storage(self) -> MagicMock:
        """Create mock queue storage"""
        mock = MagicMock()
        mock.get_item.return_value = {
            "id": "queue-123",
            "status": "pending",
            "account_id": "personal",
            "metadata": {
                "subject": "Test Email",
                "from_name": "Sender",
                "from_address": "sender@test.com",
            },
        }
        mock.update_item.return_value = True
        return mock

    @pytest.fixture
    def mock_snooze_storage(self, tmp_path: Path) -> SnoozeStorage:
        """Create real snooze storage with temp dir"""
        return SnoozeStorage(snoozes_dir=tmp_path / "snoozes")

    @pytest.fixture
    def mock_action_history(self, tmp_path: Path) -> ActionHistoryStorage:
        """Create real action history with temp dir"""
        return ActionHistoryStorage(actions_dir=tmp_path / "actions")

    @pytest.mark.asyncio
    async def test_snooze_item(
        self,
        mock_queue_storage: MagicMock,
        mock_snooze_storage: SnoozeStorage,
        mock_action_history: ActionHistoryStorage,
    ) -> None:
        """Test snoozing a queue item"""
        service = EventsService()
        service._queue_storage = mock_queue_storage
        service._snooze_storage = mock_snooze_storage
        service._action_history = mock_action_history

        record = await service.snooze_item(
            item_id="queue-123",
            hours=3,
            reason="Deal with later",
        )

        assert record.item_id == "queue-123"
        assert record.is_active
        mock_queue_storage.update_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_snooze_item_not_found(
        self,
        mock_snooze_storage: SnoozeStorage,
        mock_action_history: ActionHistoryStorage,
    ) -> None:
        """Test snoozing non-existent item"""
        mock_queue = MagicMock()
        mock_queue.get_item.return_value = None

        service = EventsService()
        service._queue_storage = mock_queue
        service._snooze_storage = mock_snooze_storage
        service._action_history = mock_action_history

        with pytest.raises(ValueError, match="Queue item not found"):
            await service.snooze_item(item_id="non-existent", hours=1)

    @pytest.mark.asyncio
    async def test_get_snoozed_items(
        self,
        mock_queue_storage: MagicMock,
        mock_snooze_storage: SnoozeStorage,
        mock_action_history: ActionHistoryStorage,
    ) -> None:
        """Test getting snoozed items with preview"""
        # Create some snoozes
        mock_snooze_storage.snooze_item(
            item_id="item-1",
            item_type="queue_item",
            snooze_until=datetime.now(timezone.utc) + timedelta(hours=1),
            original_data={
                "metadata": {
                    "subject": "Test Subject",
                    "from_name": "Test Sender",
                }
            },
        )

        service = EventsService()
        service._snooze_storage = mock_snooze_storage

        items = await service.get_snoozed_items()
        assert len(items) == 1
        assert items[0]["item_id"] == "item-1"
        assert "item_preview" in items[0]
        assert items[0]["item_preview"]["subject"] == "Test Subject"

    @pytest.mark.asyncio
    async def test_undo_queue_approve(
        self,
        mock_queue_storage: MagicMock,
        mock_snooze_storage: SnoozeStorage,
        mock_action_history: ActionHistoryStorage,
    ) -> None:
        """Test undoing a queue approve action"""
        # Create an action to undo
        record = mock_action_history.create_action(
            action_type=ActionType.QUEUE_APPROVE,
            item_id="queue-123",
            item_type="queue_item",
            rollback_data={"original_status": "pending"},
        )

        service = EventsService()
        service._queue_storage = mock_queue_storage
        service._action_history = mock_action_history

        result = await service.undo_action(record.action_id, reason="Changed my mind")

        assert result["success"]
        mock_queue_storage.update_item.assert_called()

    @pytest.mark.asyncio
    async def test_get_stats(
        self,
        mock_snooze_storage: SnoozeStorage,
        mock_action_history: ActionHistoryStorage,
    ) -> None:
        """Test getting events stats"""
        # Create some data
        mock_snooze_storage.snooze_for_duration("s1", "queue_item", hours=1)
        mock_action_history.create_action(
            ActionType.EMAIL_ARCHIVE, "e1", "email"
        )

        service = EventsService()
        service._snooze_storage = mock_snooze_storage
        service._action_history = mock_action_history

        stats = await service.get_stats()
        assert stats["snoozed_count"] == 1
        assert stats["total_actions"] == 1


class TestEventsRouter:
    """Tests for Events API router"""

    @pytest.fixture
    def app_with_mock_service(self) -> tuple:
        """Create app with mock service dependency override"""
        from src.jeeves.api.app import create_app
        from src.jeeves.api.routers.events import _get_events_service

        mock_service = AsyncMock(spec=EventsService)
        app = create_app()
        app.dependency_overrides[_get_events_service] = lambda: mock_service
        return app, mock_service

    def test_list_snoozed_items(self, app_with_mock_service: tuple) -> None:
        """Test GET /api/events/snoozed"""
        app, mock_service = app_with_mock_service
        mock_service.get_snoozed_items.return_value = [
            {
                "snooze_id": "snooze-1",
                "item_id": "queue-1",
                "item_type": "queue_item",
                "snoozed_at": datetime.now(timezone.utc),
                "snooze_until": datetime.now(timezone.utc) + timedelta(hours=1),
                "reason": "later",
                "time_remaining_minutes": 60,
                "is_expired": False,
                "item_preview": {"subject": "Test"},
            }
        ]

        client = TestClient(app)
        response = client.get("/api/events/snoozed")

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert len(data["data"]) == 1

    def test_snooze_item(self, app_with_mock_service: tuple) -> None:
        """Test POST /api/events/{item_id}/snooze"""
        app, mock_service = app_with_mock_service
        mock_record = MagicMock()
        mock_record.snooze_id = "snooze-new"
        mock_record.item_id = "queue-123"
        mock_record.item_type = "queue_item"
        mock_record.snoozed_at = datetime.now(timezone.utc)
        mock_record.snooze_until = datetime.now(timezone.utc) + timedelta(hours=3)
        mock_record.reason_text = "Later"

        mock_service.snooze_item.return_value = mock_record

        client = TestClient(app)
        response = client.post(
            "/api/events/queue-123/snooze",
            json={"hours": 3, "reason": "Later"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["data"]["snooze_id"] == "snooze-new"

    def test_unsnooze_item(self, app_with_mock_service: tuple) -> None:
        """Test DELETE /api/events/{item_id}/snooze"""
        app, mock_service = app_with_mock_service
        mock_record = MagicMock()
        mock_record.snooze_id = "snooze-123"
        mock_record.item_id = "queue-123"
        mock_record.item_type = "queue_item"
        mock_record.snoozed_at = datetime.now(timezone.utc)
        mock_record.snooze_until = datetime.now(timezone.utc)
        mock_record.reason_text = None

        mock_service.unsnooze_item.return_value = mock_record

        client = TestClient(app)
        response = client.delete("/api/events/queue-123/snooze")

        assert response.status_code == 200
        data = response.json()
        assert data["success"]

    def test_get_action_history(self, app_with_mock_service: tuple) -> None:
        """Test GET /api/events/history"""
        app, mock_service = app_with_mock_service
        mock_record = MagicMock()
        mock_record.action_id = "action-1"
        mock_record.action_type = ActionType.EMAIL_ARCHIVE
        mock_record.item_id = "email-1"
        mock_record.item_type = "email"
        mock_record.executed_at = datetime.now(timezone.utc)
        mock_record.status = ActionStatus.COMPLETED
        mock_record.action_data = {}

        mock_service.get_action_history.return_value = [mock_record]

        client = TestClient(app)
        response = client.get("/api/events/history")

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert len(data["data"]) == 1
        assert data["data"][0]["action_id"] == "action-1"

    def test_undo_action(self, app_with_mock_service: tuple) -> None:
        """Test POST /api/events/{item_id}/undo"""
        app, mock_service = app_with_mock_service
        mock_action = MagicMock()
        mock_action.action_id = "action-1"
        mock_action.status = ActionStatus.COMPLETED

        mock_service.get_action_history.return_value = [mock_action]
        mock_service.undo_action.return_value = {
            "success": True,
            "message": "Restored",
        }

        client = TestClient(app)
        response = client.post(
            "/api/events/item-1/undo",
            json={"reason": "Changed mind"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["data"]["success"]

    def test_get_events_stats(self, app_with_mock_service: tuple) -> None:
        """Test GET /api/events/stats"""
        app, mock_service = app_with_mock_service
        mock_service.get_stats.return_value = {
            "snoozed_count": 5,
            "expired_pending": 1,
            "total_actions": 100,
            "undoable_actions": 10,
            "actions_by_type": {"email_archive": 50},
        }

        client = TestClient(app)
        response = client.get("/api/events/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["data"]["snoozed_count"] == 5
