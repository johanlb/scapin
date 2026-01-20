"""
Tests for Queue Service Event Emission (v2.4)

Tests that WebSocket events are properly emitted when queue items are modified.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.frontin.api.services.queue_service import QueueService


class TestQueueServiceEventEmission:
    """Tests for event emission in QueueService operations"""

    @pytest.fixture
    def mock_storage(self):
        """Create mock QueueStorage"""
        storage = MagicMock()
        storage.get_stats.return_value = {
            "total": 10,
            "by_status": {"pending": 5, "approved": 5},
            "by_tab": {"to_process": 5, "history": 5},
        }
        return storage

    @pytest.fixture
    def mock_snooze_storage(self):
        """Create mock SnoozeStorage"""
        return MagicMock()

    @pytest.fixture
    def mock_action_history(self):
        """Create mock ActionHistoryStorage"""
        return MagicMock()

    @pytest.fixture
    def mock_event_emitter(self):
        """Create mock QueueEventEmitter"""
        emitter = MagicMock()
        emitter.emit_item_added = AsyncMock(return_value=2)
        emitter.emit_item_updated = AsyncMock(return_value=2)
        emitter.emit_item_removed = AsyncMock(return_value=2)
        emitter.emit_stats_updated = AsyncMock(return_value=2)
        return emitter

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
            "reviewed_at": None,
            "metadata": {
                "id": 12345,  # Must be numeric for IMAP
                "subject": "Test Email",
                "from_address": "sender@example.com",
                "from_name": "Test Sender",
                "date": "2026-01-20T09:00:00Z",
                "has_attachments": False,
                "folder": "INBOX",
                "message_id": "<test@example.com>",
            },
            "analysis": {
                "action": "archive",
                "confidence": 85,
                "category": "newsletter",
                "reasoning": "Newsletter detected",
                "options": [{"action": "archive", "confidence": 85, "is_recommended": True}],
            },
            "content": {"preview": "Test preview..."},
        }

    @pytest.fixture
    def service(self, mock_storage, mock_snooze_storage, mock_action_history, mock_event_emitter):
        """Create QueueService with mocks"""
        return QueueService(
            queue_storage=mock_storage,
            snooze_storage=mock_snooze_storage,
            action_history=mock_action_history,
            event_emitter=mock_event_emitter,
        )

    # =========================================================================
    # APPROVE ITEM EVENTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_approve_item_emits_item_updated(
        self, service, mock_storage, mock_event_emitter, sample_item
    ):
        """approve_item should emit item_updated event with status and resolution changes"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        # Mock IMAP client and config for the sync method that runs in thread
        with (
            patch("src.integrations.email.imap_client.IMAPClient") as mock_imap_class,
            patch("src.core.config_manager.get_config") as mock_get_config,
        ):
            # Setup config mock
            mock_config = MagicMock()
            mock_config.email = MagicMock()
            mock_get_config.return_value = mock_config

            # Setup IMAP mock with context manager support
            mock_imap = MagicMock()
            mock_imap.connect.return_value.__enter__ = MagicMock(return_value=mock_imap)
            mock_imap.connect.return_value.__exit__ = MagicMock(return_value=None)
            mock_imap.add_flag = MagicMock(return_value=True)
            mock_imap.archive_email = MagicMock(return_value=True)
            mock_imap_class.return_value = mock_imap

            await service.approve_item("item-123")

        # Verify item_updated was called
        mock_event_emitter.emit_item_updated.assert_called()

    @pytest.mark.asyncio
    async def test_approve_item_emits_stats_updated(
        self, service, mock_storage, mock_event_emitter, sample_item
    ):
        """approve_item should emit stats_updated event after approval"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        # Mock IMAP client and config for the sync method that runs in thread
        with (
            patch("src.integrations.email.imap_client.IMAPClient") as mock_imap_class,
            patch("src.core.config_manager.get_config") as mock_get_config,
        ):
            # Setup config mock
            mock_config = MagicMock()
            mock_config.email = MagicMock()
            mock_get_config.return_value = mock_config

            # Setup IMAP mock with context manager support
            mock_imap = MagicMock()
            mock_imap.connect.return_value.__enter__ = MagicMock(return_value=mock_imap)
            mock_imap.connect.return_value.__exit__ = MagicMock(return_value=None)
            mock_imap.add_flag = MagicMock(return_value=True)
            mock_imap.archive_email = MagicMock(return_value=True)
            mock_imap_class.return_value = mock_imap

            await service.approve_item("item-123")

        # Verify stats_updated was called
        mock_event_emitter.emit_stats_updated.assert_called()

    # =========================================================================
    # REJECT ITEM EVENTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_reject_item_emits_item_updated(
        self, service, mock_storage, mock_event_emitter, sample_item
    ):
        """reject_item should emit item_updated event"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        await service.reject_item("item-123")

        mock_event_emitter.emit_item_updated.assert_called()

    @pytest.mark.asyncio
    async def test_reject_item_emits_stats_updated(
        self, service, mock_storage, mock_event_emitter, sample_item
    ):
        """reject_item should emit stats_updated event"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        await service.reject_item("item-123")

        mock_event_emitter.emit_stats_updated.assert_called()

    # =========================================================================
    # MODIFY ITEM EVENTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_modify_item_emits_item_updated(
        self, service, mock_storage, mock_event_emitter, sample_item
    ):
        """modify_item should emit item_updated event with modified_action in changes"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True

        # Mock IMAP client and config for the sync method that runs in thread
        with (
            patch("src.integrations.email.imap_client.IMAPClient") as mock_imap_class,
            patch("src.core.config_manager.get_config") as mock_get_config,
        ):
            # Setup config mock
            mock_config = MagicMock()
            mock_config.email = MagicMock()
            mock_get_config.return_value = mock_config

            # Setup IMAP mock with context manager support
            mock_imap = MagicMock()
            mock_imap.connect.return_value.__enter__ = MagicMock(return_value=mock_imap)
            mock_imap.connect.return_value.__exit__ = MagicMock(return_value=None)
            mock_imap.add_flag = MagicMock(return_value=True)
            mock_imap.delete_email = MagicMock(return_value=True)
            mock_imap_class.return_value = mock_imap

            await service.modify_item("item-123", action="delete")

        mock_event_emitter.emit_item_updated.assert_called()

    # =========================================================================
    # DELETE ITEM EVENTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_item_emits_item_removed(
        self, service, mock_storage, mock_event_emitter, sample_item
    ):
        """delete_item should emit item_removed event"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.remove_item.return_value = True

        await service.delete_item("item-123")

        mock_event_emitter.emit_item_removed.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_item_emits_stats_updated(
        self, service, mock_storage, mock_event_emitter, sample_item
    ):
        """delete_item should emit stats_updated event"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.remove_item.return_value = True

        await service.delete_item("item-123")

        mock_event_emitter.emit_stats_updated.assert_called()

    # =========================================================================
    # SNOOZE ITEM EVENTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_snooze_item_emits_item_updated(
        self, service, mock_storage, mock_snooze_storage, mock_event_emitter, sample_item
    ):
        """snooze_item should emit item_updated event with snooze in changes"""
        mock_storage.get_item.return_value = sample_item
        mock_storage.update_item.return_value = True
        mock_snooze_storage.create_snooze.return_value = {
            "id": "snooze-123",
            "item_id": "item-123",
            "until": "2026-01-21T10:00:00Z",
        }

        # Use correct parameter name: snooze_option
        await service.snooze_item("item-123", snooze_option="tomorrow")

        mock_event_emitter.emit_item_updated.assert_called()

    # =========================================================================
    # UNSNOOZE ITEM EVENTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_unsnooze_item_emits_item_updated(
        self, service, mock_storage, mock_snooze_storage, mock_event_emitter, sample_item
    ):
        """unsnooze_item should emit item_updated event"""
        snoozed_item = {**sample_item, "snooze": {"until": "2026-01-21T10:00:00Z"}}
        mock_storage.get_item.return_value = snoozed_item
        mock_storage.update_item.return_value = True
        mock_snooze_storage.delete_snooze.return_value = True

        await service.unsnooze_item("item-123")

        mock_event_emitter.emit_item_updated.assert_called()

    # =========================================================================
    # UNDO ITEM EVENTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_undo_item_emits_item_updated(
        self, service, mock_storage, mock_action_history, mock_event_emitter, sample_item
    ):
        """undo_item should emit item_updated event with undone in changes"""
        approved_item = {**sample_item, "status": "approved", "reviewed_at": "2026-01-20T11:00:00Z"}
        mock_storage.get_item.return_value = approved_item
        mock_storage.update_item.return_value = True
        mock_action_history.can_undo.return_value = True
        mock_action_history.get_last_action.return_value = {
            "action_type": "archive",
            "executed_at": "2026-01-20T11:00:00Z",
            "can_undo": True,
            "original_folder": "INBOX",
        }
        mock_action_history.mark_undone.return_value = True

        # Mock IMAP client and config for the sync method that runs in thread
        with (
            patch("src.integrations.email.imap_client.IMAPClient") as mock_imap_class,
            patch("src.core.config_manager.get_config") as mock_get_config,
        ):
            # Setup config mock
            mock_config = MagicMock()
            mock_config.email = MagicMock()
            mock_get_config.return_value = mock_config

            # Setup IMAP mock with context manager support
            mock_imap = MagicMock()
            mock_imap.connect.return_value.__enter__ = MagicMock(return_value=mock_imap)
            mock_imap.connect.return_value.__exit__ = MagicMock(return_value=None)
            mock_imap.move_email = MagicMock(return_value=True)
            mock_imap_class.return_value = mock_imap

            await service.undo_item("item-123")

        mock_event_emitter.emit_item_updated.assert_called()


class TestQueueServiceEnqueueEvents:
    """Tests for event emission when enqueueing items"""

    @pytest.fixture
    def mock_storage(self):
        """Create mock QueueStorage"""
        storage = MagicMock()
        storage.save_item.return_value = "new-item-123"
        storage.get_stats.return_value = {"total": 11}
        return storage

    @pytest.fixture
    def mock_event_emitter(self):
        """Create mock QueueEventEmitter"""
        emitter = MagicMock()
        emitter.emit_item_added = AsyncMock(return_value=2)
        emitter.emit_stats_updated = AsyncMock(return_value=2)
        return emitter

    @pytest.fixture
    def service(self, mock_storage, mock_event_emitter):
        """Create QueueService with mocks"""
        return QueueService(
            queue_storage=mock_storage,
            snooze_storage=MagicMock(),
            action_history=MagicMock(),
            event_emitter=mock_event_emitter,
        )

    @pytest.mark.asyncio
    async def test_enqueue_email_emits_item_added(
        self, service, mock_storage, mock_event_emitter
    ):
        """enqueue_email should emit item_added event"""
        # Mock the processed tracker
        with patch("src.frontin.api.services.queue_service.get_processed_tracker") as mock_tracker:
            mock_tracker.return_value.is_processed.return_value = False
            mock_tracker.return_value.mark_processed.return_value = None

            # Create mock metadata and analysis objects
            metadata = MagicMock()
            metadata.id = 12345
            metadata.subject = "Test Email"
            metadata.from_address = "sender@example.com"
            metadata.from_name = "Sender"
            metadata.to_addresses = ["recipient@example.com"]
            metadata.date = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
            metadata.has_attachments = False
            metadata.folder = "INBOX"
            metadata.message_id = "<unique@example.com>"
            metadata.in_reply_to = None
            metadata.references = []
            metadata.attachments = []
            metadata.model_dump.return_value = {
                "id": 12345,
                "subject": "Test Email",
                "from_address": "sender@example.com",
                "from_name": "Sender",
            }

            analysis = MagicMock()
            analysis.action = MagicMock(value="archive")
            analysis.confidence = 85
            analysis.category = MagicMock(value="newsletter")
            analysis.reasoning = "Newsletter detected"
            analysis.destination = None
            analysis.model_dump.return_value = {
                "action": "archive",
                "confidence": 85,
            }

            # Use correct parameter name: content_preview
            await service.enqueue_email(
                metadata=metadata,
                analysis=analysis,
                content_preview="Email content preview...",
                account_id="personal",
            )

        # Verify item_added was called
        mock_event_emitter.emit_item_added.assert_called_once()
