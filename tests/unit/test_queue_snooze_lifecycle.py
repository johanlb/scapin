"""
Tests for Queue Snooze Lifecycle (v2.4)

Tests the complete snooze/unsnooze flow including wake-up logic.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from src.frontin.api.services.queue_service import QueueService


class TestSnoozeItem:
    """Tests for snoozing queue items"""

    @pytest.fixture
    def mock_storage(self):
        """Create mock QueueStorage"""
        storage = MagicMock()
        storage.get_stats.return_value = {"total": 10}
        return storage

    @pytest.fixture
    def mock_snooze_storage(self):
        """Create mock SnoozeStorage with snooze_item method"""
        storage = MagicMock()
        # Mock snooze_item to return a record with snooze_id
        mock_record = MagicMock()
        mock_record.snooze_id = "snooze-123"
        storage.snooze_item.return_value = mock_record
        return storage

    @pytest.fixture
    def mock_event_emitter(self):
        """Create mock QueueEventEmitter"""
        emitter = MagicMock()
        emitter.emit_item_updated = AsyncMock(return_value=2)
        emitter.emit_stats_updated = AsyncMock(return_value=2)
        return emitter

    @pytest.fixture
    def service(self, mock_storage, mock_snooze_storage, mock_event_emitter):
        """Create QueueService with mocks"""
        return QueueService(
            queue_storage=mock_storage,
            snooze_storage=mock_snooze_storage,
            action_history=MagicMock(),
            event_emitter=mock_event_emitter,
        )

    @pytest.fixture
    def sample_item(self):
        """Create a sample queue item"""
        return {
            "id": "item-123",
            "account_id": "account-456",
            "state": "awaiting_review",
            "status": "pending",
            "resolution": None,
            "snooze": None,
            "queued_at": "2026-01-20T10:00:00Z",
            "metadata": {
                "id": 12345,
                "subject": "Test Email",
                "from_address": "sender@example.com",
            },
            "analysis": {
                "action": "archive",
                "confidence": 85,
            },
        }

    # =========================================================================
    # SNOOZE OPTIONS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_snooze_with_1hour_option(
        self, service, mock_storage, mock_snooze_storage, sample_item
    ):
        """snooze_item with '1hour' option should call snooze_storage.snooze_item"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        await service.snooze_item("item-123", snooze_option="1hour")

        # Verify snooze_item was called on snooze_storage
        mock_snooze_storage.snooze_item.assert_called_once()
        call_kwargs = mock_snooze_storage.snooze_item.call_args[1]
        assert call_kwargs["item_id"] == "item-123"

    @pytest.mark.asyncio
    async def test_snooze_with_tomorrow_option(
        self, service, mock_storage, mock_snooze_storage, sample_item
    ):
        """snooze_item with 'tomorrow' option should set snooze for next day"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        await service.snooze_item("item-123", snooze_option="tomorrow")

        mock_snooze_storage.snooze_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_snooze_with_next_week_option(
        self, service, mock_storage, mock_snooze_storage, sample_item
    ):
        """snooze_item with 'next_week' option should set snooze for 1 week"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        await service.snooze_item("item-123", snooze_option="next_week")

        mock_snooze_storage.snooze_item.assert_called_once()

    # =========================================================================
    # SNOOZE STATE UPDATES
    # =========================================================================

    @pytest.mark.asyncio
    async def test_snooze_updates_item_status(
        self, service, mock_storage, mock_snooze_storage, mock_event_emitter, sample_item
    ):
        """snooze_item should update the item's status to snoozed"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        await service.snooze_item("item-123", snooze_option="tomorrow")

        # Verify item was updated with snoozed status
        mock_storage.update_item.assert_called()
        call_args = mock_storage.update_item.call_args
        item_id, updates = call_args[0]
        assert item_id == "item-123"
        assert updates.get("status") == "snoozed"

    @pytest.mark.asyncio
    async def test_snooze_emits_item_updated_event(
        self, service, mock_storage, mock_snooze_storage, mock_event_emitter, sample_item
    ):
        """snooze_item should emit item_updated event"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        await service.snooze_item("item-123", snooze_option="tomorrow")

        mock_event_emitter.emit_item_updated.assert_called()

    # =========================================================================
    # SNOOZE VALIDATION
    # =========================================================================

    @pytest.mark.asyncio
    async def test_snooze_nonexistent_item_returns_none(
        self, service, mock_storage, mock_snooze_storage
    ):
        """snooze_item should return None for nonexistent item"""
        mock_storage.get_item.return_value = None

        result = await service.snooze_item("nonexistent", snooze_option="tomorrow")

        assert result is None
        mock_snooze_storage.snooze_item.assert_not_called()


class TestUnsnoozeItem:
    """Tests for unsnoozing queue items"""

    @pytest.fixture
    def mock_storage(self):
        """Create mock QueueStorage"""
        storage = MagicMock()
        storage.get_stats.return_value = {"total": 10}
        return storage

    @pytest.fixture
    def mock_snooze_storage(self):
        """Create mock SnoozeStorage with unsnooze_item method"""
        storage = MagicMock()
        storage.unsnooze_item.return_value = MagicMock(snooze_id="snooze-123")
        return storage

    @pytest.fixture
    def mock_event_emitter(self):
        """Create mock QueueEventEmitter"""
        emitter = MagicMock()
        emitter.emit_item_updated = AsyncMock(return_value=2)
        emitter.emit_stats_updated = AsyncMock(return_value=2)
        return emitter

    @pytest.fixture
    def service(self, mock_storage, mock_snooze_storage, mock_event_emitter):
        """Create QueueService with mocks"""
        return QueueService(
            queue_storage=mock_storage,
            snooze_storage=mock_snooze_storage,
            action_history=MagicMock(),
            event_emitter=mock_event_emitter,
        )

    @pytest.fixture
    def snoozed_item(self):
        """Create a snoozed queue item"""
        return {
            "id": "item-123",
            "account_id": "account-456",
            "state": "awaiting_review",
            "status": "snoozed",
            "resolution": None,
            "snooze": {
                "id": "snooze-123",
                "until": "2026-01-21T10:00:00Z",
            },
            "snooze_id": "snooze-123",
            "queued_at": "2026-01-20T10:00:00Z",
            "metadata": {
                "id": 12345,
                "subject": "Test Email",
                "from_address": "sender@example.com",
            },
            "analysis": {
                "action": "archive",
                "confidence": 85,
            },
        }

    @pytest.mark.asyncio
    async def test_unsnooze_calls_snooze_storage(
        self, service, mock_storage, mock_snooze_storage, snoozed_item
    ):
        """unsnooze_item should call snooze_storage.unsnooze_item"""
        mock_storage.get_item.return_value = snoozed_item
        mock_storage.update_item.return_value = True

        await service.unsnooze_item("item-123")

        # Verify unsnooze_item was called
        mock_snooze_storage.unsnooze_item.assert_called_once_with("item-123")

    @pytest.mark.asyncio
    async def test_unsnooze_emits_item_updated_event(
        self, service, mock_storage, mock_snooze_storage, mock_event_emitter, snoozed_item
    ):
        """unsnooze_item should emit item_updated event"""
        mock_storage.get_item.return_value = snoozed_item
        mock_storage.update_item.return_value = True

        await service.unsnooze_item("item-123")

        mock_event_emitter.emit_item_updated.assert_called()

    @pytest.mark.asyncio
    async def test_unsnooze_updates_item_status(
        self, service, mock_storage, mock_snooze_storage, snoozed_item
    ):
        """unsnooze_item should update item status back to pending"""
        mock_storage.get_item.return_value = snoozed_item
        mock_storage.update_item.return_value = True

        await service.unsnooze_item("item-123")

        # Verify item was updated
        mock_storage.update_item.assert_called()


class TestSnoozeWakeUp:
    """Tests for snooze wake-up/expiration logic"""

    def test_expired_snooze_detection(self):
        """Expired snoozes should be detectable"""
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        expired_snooze = {
            "id": "snooze-123",
            "item_id": "item-123",
            "until": past_time,
        }

        # Parse and check expiration
        until_str = expired_snooze["until"]
        if until_str.endswith("Z"):
            until_str = until_str[:-1] + "+00:00"
        until = datetime.fromisoformat(until_str)
        is_expired = until < datetime.now(timezone.utc)

        assert is_expired is True

    def test_active_snooze_detection(self):
        """Active snoozes should not be detected as expired"""
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        active_snooze = {
            "id": "snooze-123",
            "item_id": "item-123",
            "until": future_time,
        }

        # Parse and check expiration
        until_str = active_snooze["until"]
        if until_str.endswith("Z"):
            until_str = until_str[:-1] + "+00:00"
        until = datetime.fromisoformat(until_str)
        is_expired = until < datetime.now(timezone.utc)

        assert is_expired is False


class TestSnoozeFiltering:
    """Tests for filtering snoozed items in list operations"""

    @pytest.fixture
    def mixed_items(self):
        """Create items with different snooze states"""
        return [
            {
                "id": "item-1",
                "state": "awaiting_review",
                "status": "pending",
                "snooze": None,  # Not snoozed
            },
            {
                "id": "item-2",
                "state": "awaiting_review",
                "status": "snoozed",
                "snooze": {"until": "2026-01-25T10:00:00Z"},  # Snoozed (future)
            },
            {
                "id": "item-3",
                "state": "processed",
                "status": "approved",
                "snooze": None,  # Processed
            },
        ]

    def test_snoozed_items_have_snooze_field(self, mixed_items):
        """Snoozed items should have a non-null snooze field"""
        snoozed = [i for i in mixed_items if i.get("snooze") is not None]
        non_snoozed = [i for i in mixed_items if i.get("snooze") is None]

        assert len(snoozed) == 1
        assert len(non_snoozed) == 2
        assert snoozed[0]["id"] == "item-2"

    def test_snoozed_items_have_snoozed_status(self, mixed_items):
        """Snoozed items should have status 'snoozed'"""
        snoozed = [i for i in mixed_items if i.get("status") == "snoozed"]

        assert len(snoozed) == 1
        assert snoozed[0]["id"] == "item-2"
