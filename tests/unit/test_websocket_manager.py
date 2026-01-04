"""
Tests for WebSocket Connection Manager

Tests connection tracking, event broadcasting, and EventBus integration.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.processing_events import EventBus, ProcessingEvent, ProcessingEventType
from src.jeeves.api.websocket.manager import (
    ConnectionManager,
    get_connection_manager,
    reset_connection_manager,
)


class TestConnectionManager:
    """Tests for ConnectionManager"""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus for testing"""
        return EventBus()

    @pytest.fixture
    def manager(self, event_bus):
        """Create a ConnectionManager with test EventBus"""
        return ConnectionManager(event_bus=event_bus)

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket"""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager, mock_websocket):
        """Connect should accept the websocket and add to connections"""
        await manager.connect(mock_websocket)

        mock_websocket.accept.assert_called_once()
        assert manager.active_connection_count == 1

    @pytest.mark.asyncio
    async def test_connect_sends_welcome_message(self, manager, mock_websocket):
        """Connect should send a welcome message"""
        await manager.connect(mock_websocket)

        # Check that send_text was called
        assert mock_websocket.send_text.called
        call_args = mock_websocket.send_text.call_args[0][0]
        assert "connected" in call_args

    @pytest.mark.asyncio
    async def test_disconnect_removes_websocket(self, manager, mock_websocket):
        """Disconnect should remove websocket from connections"""
        await manager.connect(mock_websocket)
        await manager.disconnect(mock_websocket)

        assert manager.active_connection_count == 0

    @pytest.mark.asyncio
    async def test_connect_subscribes_to_events(self, manager, mock_websocket, event_bus):
        """First connection should subscribe to EventBus"""
        assert not manager.is_subscribed

        await manager.connect(mock_websocket)

        assert manager.is_subscribed
        # Check subscription count in EventBus
        total_subs = event_bus.get_subscriber_count()
        assert total_subs > 0

    @pytest.mark.asyncio
    async def test_disconnect_last_unsubscribes(self, manager, mock_websocket, event_bus):
        """Disconnecting last client should unsubscribe from EventBus"""
        await manager.connect(mock_websocket)
        assert manager.is_subscribed

        await manager.disconnect(mock_websocket)

        assert not manager.is_subscribed
        assert event_bus.get_subscriber_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_event_sends_to_all(self, manager):
        """Broadcast event should send to all connected clients"""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1)
        await manager.connect(ws2)

        # Reset call counts after connect
        ws1.send_text.reset_mock()
        ws2.send_text.reset_mock()

        event = ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_COMPLETED,
            email_id=123,
            subject="Test Email",
        )

        await manager.broadcast_event(event)

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connections(self, manager, mock_websocket):
        """Broadcast should remove connections that fail to receive"""
        await manager.connect(mock_websocket)

        # Make send_text fail
        mock_websocket.send_text.side_effect = Exception("Connection closed")
        mock_websocket.send_text.reset_mock()

        event = ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_COMPLETED,
        )

        await manager.broadcast_event(event)

        # Connection should be removed
        assert manager.active_connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_message_sends_custom_data(self, manager, mock_websocket):
        """Broadcast message should send custom dict data"""
        await manager.connect(mock_websocket)
        mock_websocket.send_text.reset_mock()

        await manager.broadcast_message({"type": "custom", "data": "test"})

        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        assert "custom" in call_args

    def test_event_to_dict_converts_properly(self, manager):
        """Event to dict should produce JSON-serializable output"""
        event = ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_ANALYZING,
            email_id=42,
            subject="Test Subject",
            timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

        result = manager._event_to_dict(event)

        assert result["type"] == "event"
        assert result["data"]["event_type"] == "email_analyzing"
        assert result["data"]["email_id"] == 42
        assert result["data"]["subject"] == "Test Subject"
        assert "2026-01-01" in result["data"]["timestamp"]


class TestConnectionManagerSingleton:
    """Tests for singleton functions"""

    def test_get_connection_manager_returns_same_instance(self):
        """get_connection_manager should return singleton"""
        reset_connection_manager()

        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2

        reset_connection_manager()

    def test_reset_connection_manager_creates_new(self):
        """reset should allow creating new manager"""
        manager1 = get_connection_manager()
        reset_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is not manager2

        reset_connection_manager()
