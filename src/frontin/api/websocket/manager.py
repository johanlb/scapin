"""
WebSocket Connection Manager

Manages WebSocket connections and broadcasts events from EventBus to clients.
"""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket

from src.core.processing_events import (
    EventBus,
    ProcessingEvent,
    ProcessingEventType,
    get_event_bus,
)
from src.monitoring.logger import ScapinLogger

logger = ScapinLogger.get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts events

    Thread-safe for concurrent connections/disconnections.
    Subscribes to EventBus to automatically broadcast processing events.

    Usage:
        manager = ConnectionManager()
        await manager.connect(websocket)
        # Events are automatically broadcast from EventBus
        await manager.disconnect(websocket)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize connection manager

        Args:
            event_bus: Optional EventBus instance. Uses global singleton if not provided.
        """
        self._active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()
        self._event_bus = event_bus or get_event_bus()
        self._subscribed = False

        logger.info("WebSocket ConnectionManager initialized")

    def _subscribe_to_events(self) -> None:
        """Subscribe to all EventBus events for broadcasting"""
        if self._subscribed:
            return

        for event_type in ProcessingEventType:
            self._event_bus.subscribe(event_type, self._on_event)

        self._subscribed = True
        logger.debug("Subscribed to all ProcessingEventType events")

    def _unsubscribe_from_events(self) -> None:
        """Unsubscribe from all EventBus events"""
        if not self._subscribed:
            return

        for event_type in ProcessingEventType:
            self._event_bus.unsubscribe(event_type, self._on_event)

        self._subscribed = False
        logger.debug("Unsubscribed from all ProcessingEventType events")

    def _on_event(self, event: ProcessingEvent) -> None:
        """
        Callback for EventBus events

        Schedules async broadcast in the event loop.
        """
        # Schedule async broadcast - we're called from a sync context
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_event(event))
        except RuntimeError:
            # No running event loop - log and skip
            logger.debug(f"No event loop for broadcast: {event.event_type.value}")

    async def connect(self, websocket: WebSocket, already_accepted: bool = False) -> None:
        """
        Register a WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
            already_accepted: If True, skip accept() call (already done by router)
        """
        if not already_accepted:
            await websocket.accept()

        async with self._lock:
            self._active_connections.append(websocket)
            connection_count = len(self._active_connections)

            # Subscribe to events when first client connects
            if connection_count == 1:
                self._subscribe_to_events()

        logger.info(f"WebSocket connected. Active connections: {connection_count}")

        # Send welcome message
        await self._send_json(websocket, {
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Connected to Scapin live events",
        })

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance to remove
        """
        async with self._lock:
            if websocket in self._active_connections:
                self._active_connections.remove(websocket)

            connection_count = len(self._active_connections)

            # Unsubscribe from events when last client disconnects
            if connection_count == 0:
                self._unsubscribe_from_events()

        logger.info(f"WebSocket disconnected. Active connections: {connection_count}")

    async def broadcast_event(self, event: ProcessingEvent) -> None:
        """
        Broadcast a ProcessingEvent to all connected clients

        Args:
            event: ProcessingEvent to broadcast
        """
        if not self._active_connections:
            return

        # Convert event to JSON-serializable dict
        message = self._event_to_dict(event)

        async with self._lock:
            connections = self._active_connections.copy()

        # Broadcast to all clients
        disconnected = []
        for connection in connections:
            try:
                await self._send_json(connection, message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_message(self, message: dict) -> None:
        """
        Broadcast a custom message to all connected clients

        Args:
            message: Dict message to broadcast (will be JSON encoded)
        """
        async with self._lock:
            connections = self._active_connections.copy()

        disconnected = []
        for connection in connections:
            try:
                await self._send_json(connection, message)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            await self.disconnect(connection)

    async def _send_json(self, websocket: WebSocket, data: dict) -> None:
        """Send JSON data to a WebSocket"""
        await websocket.send_text(json.dumps(data, default=str))

    def _event_to_dict(self, event: ProcessingEvent) -> dict:
        """
        Convert ProcessingEvent to JSON-serializable dict

        Args:
            event: ProcessingEvent to convert

        Returns:
            Dict suitable for JSON serialization
        """
        # Use dataclass asdict for conversion
        data = asdict(event)

        # Convert enum to string
        data["event_type"] = event.event_type.value

        # Convert datetime to ISO format
        if event.timestamp:
            data["timestamp"] = event.timestamp.isoformat()
        if event.email_date:
            data["email_date"] = event.email_date.isoformat()

        # Add wrapper type field
        return {
            "type": "event",
            "data": data,
        }

    @property
    def active_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self._active_connections)

    @property
    def is_subscribed(self) -> bool:
        """Check if manager is subscribed to EventBus"""
        return self._subscribed


# Global manager singleton
_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get global ConnectionManager singleton

    Returns:
        Global ConnectionManager instance
    """
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


def reset_connection_manager() -> None:
    """Reset global ConnectionManager (for testing)"""
    global _manager
    if _manager is not None:
        _manager._unsubscribe_from_events()
    _manager = None
