"""
Tests for Queue WebSocket Events (v2.4)

Tests the QueueEventEmitter class for broadcasting queue events.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.frontin.api.websocket.queue_events import (
    QueueEventEmitter,
    _sanitize_item,
    get_queue_event_emitter,
    reset_queue_event_emitter,
)


class TestQueueEventEmitter:
    """Tests for QueueEventEmitter"""

    @pytest.fixture
    def mock_channel_manager(self):
        """Create a mock ChannelManager"""
        manager = MagicMock()
        manager.broadcast_to_channel = AsyncMock(return_value=2)
        return manager

    @pytest.fixture
    def emitter(self, mock_channel_manager):
        """Create a QueueEventEmitter with mock manager"""
        return QueueEventEmitter(channel_manager=mock_channel_manager)

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
            "error": None,
            "timestamps": {"queued_at": "2026-01-20T10:00:00Z"},
            "queued_at": "2026-01-20T10:00:00Z",
            "reviewed_at": None,
            "metadata": {
                "subject": "Test Email",
                "from_address": "sender@example.com",
                "from_name": "Test Sender",
                "date": "2026-01-20T09:00:00Z",
                "has_attachments": False,
                "full_text": "This is a long email body that should be stripped...",
            },
            "analysis": {
                "action": "archive",
                "confidence": 85,
                "summary": "Newsletter about tech news",
                "reasoning": "Long reasoning text that should be stripped...",
                "options": [{"action": "archive", "confidence": 85}],
            },
            "content": {
                "preview": "This is a preview...",
                "full_text": "Very long content...",
            },
        }

    @pytest.mark.asyncio
    async def test_emit_item_added(self, emitter, mock_channel_manager, sample_item):
        """emit_item_added should broadcast to QUEUE channel"""
        count = await emitter.emit_item_added(sample_item)

        assert count == 2
        mock_channel_manager.broadcast_to_channel.assert_called_once()

        call_args = mock_channel_manager.broadcast_to_channel.call_args
        assert call_args[0][0].value == "queue"  # ChannelType.QUEUE

        message = call_args[0][1]
        assert message["type"] == "item_added"
        assert message["item"]["id"] == "item-123"
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_emit_item_updated(self, emitter, mock_channel_manager, sample_item):
        """emit_item_updated should include changes and previous_state"""
        count = await emitter.emit_item_updated(
            sample_item,
            changes=["status", "resolution"],
            previous_state="pending",
        )

        assert count == 2
        mock_channel_manager.broadcast_to_channel.assert_called_once()

        message = mock_channel_manager.broadcast_to_channel.call_args[0][1]
        assert message["type"] == "item_updated"
        assert message["changes"] == ["status", "resolution"]
        assert message["previous_state"] == "pending"
        assert message["item"]["id"] == "item-123"

    @pytest.mark.asyncio
    async def test_emit_item_updated_defaults(self, emitter, mock_channel_manager, sample_item):
        """emit_item_updated should have sensible defaults"""
        await emitter.emit_item_updated(sample_item)

        message = mock_channel_manager.broadcast_to_channel.call_args[0][1]
        assert message["changes"] == []
        assert message["previous_state"] is None

    @pytest.mark.asyncio
    async def test_emit_item_removed(self, emitter, mock_channel_manager):
        """emit_item_removed should broadcast item_id and reason"""
        count = await emitter.emit_item_removed("item-123", reason="deleted")

        assert count == 2
        mock_channel_manager.broadcast_to_channel.assert_called_once()

        message = mock_channel_manager.broadcast_to_channel.call_args[0][1]
        assert message["type"] == "item_removed"
        assert message["item_id"] == "item-123"
        assert message["reason"] == "deleted"
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_emit_item_removed_no_reason(self, emitter, mock_channel_manager):
        """emit_item_removed should work without reason"""
        await emitter.emit_item_removed("item-123")

        message = mock_channel_manager.broadcast_to_channel.call_args[0][1]
        assert message["reason"] is None

    @pytest.mark.asyncio
    async def test_emit_stats_updated(self, emitter, mock_channel_manager):
        """emit_stats_updated should broadcast stats"""
        stats = {
            "total": 42,
            "by_status": {"pending": 10, "approved": 30, "rejected": 2},
            "by_tab": {"to_process": 10, "history": 32},
        }

        count = await emitter.emit_stats_updated(stats)

        assert count == 2
        mock_channel_manager.broadcast_to_channel.assert_called_once()

        message = mock_channel_manager.broadcast_to_channel.call_args[0][1]
        assert message["type"] == "stats_updated"
        assert message["stats"]["total"] == 42
        assert message["stats"]["by_tab"]["to_process"] == 10


class TestSanitizeItem:
    """Tests for _sanitize_item helper"""

    def test_sanitize_removes_large_fields(self):
        """Sanitize should remove content and full analysis"""
        item = {
            "id": "item-123",
            "account_id": "account-456",
            "state": "awaiting_review",
            "status": "pending",
            "metadata": {
                "subject": "Test",
                "from_address": "test@example.com",
                "from_name": "Test",
                "date": "2026-01-20",
                "has_attachments": False,
                "full_text": "Large body text...",
            },
            "analysis": {
                "action": "archive",
                "confidence": 85,
                "summary": "Short summary",
                "reasoning": "Long reasoning...",
                "options": [{"action": "archive"}],
            },
            "content": {
                "full_text": "Very long email content...",
                "html_body": "<html>...</html>",
            },
        }

        sanitized = _sanitize_item(item)

        # Should include essential fields
        assert sanitized["id"] == "item-123"
        assert sanitized["state"] == "awaiting_review"
        assert sanitized["metadata"]["subject"] == "Test"
        assert sanitized["analysis"]["action"] == "archive"
        assert sanitized["analysis"]["confidence"] == 85

        # Should NOT include large fields
        assert "full_text" not in sanitized.get("metadata", {})
        assert "reasoning" not in sanitized.get("analysis", {})
        assert "options" not in sanitized.get("analysis", {})
        assert "content" not in sanitized

    def test_sanitize_handles_missing_fields(self):
        """Sanitize should handle items with missing fields"""
        item = {"id": "item-123"}

        sanitized = _sanitize_item(item)

        assert sanitized["id"] == "item-123"
        assert sanitized["metadata"]["subject"] is None
        assert sanitized["analysis"]["action"] is None


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_queue_event_emitter_singleton(self):
        """get_queue_event_emitter should return same instance"""
        reset_queue_event_emitter()

        emitter1 = get_queue_event_emitter()
        emitter2 = get_queue_event_emitter()

        assert emitter1 is emitter2

    def test_reset_creates_new_instance(self):
        """reset should create a new instance on next get"""
        emitter1 = get_queue_event_emitter()
        reset_queue_event_emitter()
        emitter2 = get_queue_event_emitter()

        assert emitter1 is not emitter2

    def teardown_method(self):
        """Reset singleton after each test"""
        reset_queue_event_emitter()


class TestLazyManagerInit:
    """Tests for lazy manager initialization"""

    def test_manager_property_uses_singleton_if_none(self):
        """Manager should use get_channel_manager if none provided"""
        emitter = QueueEventEmitter(channel_manager=None)

        with patch("src.frontin.api.websocket.queue_events.get_channel_manager") as mock_get:
            mock_manager = MagicMock()
            mock_get.return_value = mock_manager

            result = emitter.manager

            mock_get.assert_called_once()
            assert result is mock_manager

    def test_manager_property_uses_provided_manager(self):
        """Manager should use provided manager if given"""
        mock_manager = MagicMock()
        emitter = QueueEventEmitter(channel_manager=mock_manager)

        with patch("src.frontin.api.websocket.queue_events.get_channel_manager") as mock_get:
            result = emitter.manager

            mock_get.assert_not_called()
            assert result is mock_manager
