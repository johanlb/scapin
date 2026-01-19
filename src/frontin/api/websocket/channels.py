"""
WebSocket Channel Manager

Manages WebSocket channels for topic-based subscriptions.
Supports: events, status, notifications, discussions/{id}

Bridges EventBus events to EVENTS channel subscribers.
"""

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import WebSocket

from src.core.processing_events import (
    ProcessingEvent,
    ProcessingEventType,
    get_event_bus,
)
from src.monitoring.logger import ScapinLogger

logger = ScapinLogger.get_logger(__name__)


class ChannelType(str, Enum):
    """Available WebSocket channels"""

    EVENTS = "events"  # Processing events (emails, teams, calendar)
    STATUS = "status"  # System status updates
    NOTIFICATIONS = "notifications"  # User notifications
    DISCUSSION = "discussion"  # Discussion-specific (with room_id)
    QUEUE = "queue"  # v2.4: Queue item events (added, updated, removed)


@dataclass
class ChannelSubscription:
    """Represents a client's subscription to a channel"""

    channel: ChannelType
    room_id: Optional[str] = None  # For discussion channels
    subscribed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConnectedClient:
    """Represents a connected WebSocket client"""

    websocket: WebSocket
    user_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    subscriptions: list[ChannelSubscription] = field(default_factory=list)

    def is_subscribed(self, channel: ChannelType, room_id: Optional[str] = None) -> bool:
        """Check if client is subscribed to a channel"""
        for sub in self.subscriptions:
            if sub.channel == channel:
                if channel == ChannelType.DISCUSSION:
                    return sub.room_id == room_id
                return True
        return False

    def subscribe(self, channel: ChannelType, room_id: Optional[str] = None) -> bool:
        """Subscribe to a channel. Returns True if newly subscribed."""
        if self.is_subscribed(channel, room_id):
            return False
        self.subscriptions.append(ChannelSubscription(channel=channel, room_id=room_id))
        return True

    def unsubscribe(self, channel: ChannelType, room_id: Optional[str] = None) -> bool:
        """Unsubscribe from a channel. Returns True if was subscribed."""
        for i, sub in enumerate(self.subscriptions):
            if sub.channel == channel:
                if channel == ChannelType.DISCUSSION and sub.room_id != room_id:
                    continue
                self.subscriptions.pop(i)
                return True
        return False


class ChannelManager:
    """
    Manages WebSocket channels and client subscriptions

    Thread-safe for concurrent connections and broadcasts.
    Bridges EventBus events to EVENTS channel subscribers.

    Usage:
        manager = ChannelManager()
        await manager.connect(websocket, user_id)
        await manager.subscribe(websocket, ChannelType.EVENTS)
        await manager.broadcast_to_channel(ChannelType.EVENTS, message)
        await manager.disconnect(websocket)
    """

    def __init__(self) -> None:
        """Initialize channel manager"""
        self._clients: dict[WebSocket, ConnectedClient] = {}
        self._lock = asyncio.Lock()
        self._event_bus = get_event_bus()
        self._eventbus_subscribed = False
        logger.info("WebSocket ChannelManager initialized")

    def _subscribe_to_eventbus(self) -> None:
        """Subscribe to EventBus for bridging events to WebSocket"""
        if self._eventbus_subscribed:
            return

        for event_type in ProcessingEventType:
            self._event_bus.subscribe(event_type, self._on_processing_event)

        self._eventbus_subscribed = True
        logger.debug("ChannelManager subscribed to EventBus")

    def _unsubscribe_from_eventbus(self) -> None:
        """Unsubscribe from EventBus"""
        if not self._eventbus_subscribed:
            return

        for event_type in ProcessingEventType:
            self._event_bus.unsubscribe(event_type, self._on_processing_event)

        self._eventbus_subscribed = False
        logger.debug("ChannelManager unsubscribed from EventBus")

    def _on_processing_event(self, event: ProcessingEvent) -> None:
        """
        Callback for EventBus events - bridges to EVENTS channel

        Schedules async broadcast in the event loop.
        """
        try:
            loop = asyncio.get_running_loop()
            # Convert ProcessingEvent to message dict
            message = self._event_to_dict(event)
            loop.create_task(self.broadcast_to_channel(ChannelType.EVENTS, message))
        except RuntimeError:
            # No running event loop - log and skip
            logger.debug(f"No event loop for EventBus bridge: {event.event_type.value}")

    def _event_to_dict(self, event: ProcessingEvent) -> dict:
        """Convert ProcessingEvent to JSON-serializable dict"""
        data = asdict(event)

        # Convert enum to string
        data["event_type"] = event.event_type.value

        # Convert datetime to ISO format
        if event.timestamp:
            data["timestamp"] = event.timestamp.isoformat()
        if event.email_date:
            data["email_date"] = event.email_date.isoformat()

        return {
            "type": "processing_event",
            "data": data,
        }

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        auto_subscribe: Optional[list[ChannelType]] = None,
    ) -> ConnectedClient:
        """
        Register a WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Authenticated user identifier
            auto_subscribe: Channels to auto-subscribe on connect

        Returns:
            ConnectedClient instance
        """
        async with self._lock:
            client = ConnectedClient(websocket=websocket, user_id=user_id)

            # Auto-subscribe to specified channels
            if auto_subscribe:
                for channel in auto_subscribe:
                    client.subscribe(channel)

            self._clients[websocket] = client
            client_count = len(self._clients)

            # Subscribe to EventBus when first client connects
            if client_count == 1:
                self._subscribe_to_eventbus()

        logger.info(
            f"Client connected: {user_id}, "
            f"subscriptions: {[s.channel.value for s in client.subscriptions]}, "
            f"total clients: {client_count}"
        )

        return client

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection"""
        async with self._lock:
            if websocket in self._clients:
                client = self._clients.pop(websocket)
                client_count = len(self._clients)

                # Unsubscribe from EventBus when last client disconnects
                if client_count == 0:
                    self._unsubscribe_from_eventbus()

                logger.info(f"Client disconnected: {client.user_id}, total: {client_count}")

    async def subscribe(
        self,
        websocket: WebSocket,
        channel: ChannelType,
        room_id: Optional[str] = None,
    ) -> bool:
        """
        Subscribe a client to a channel

        Args:
            websocket: Client WebSocket
            channel: Channel to subscribe to
            room_id: Room ID for discussion channels

        Returns:
            True if newly subscribed, False if already subscribed
        """
        async with self._lock:
            client = self._clients.get(websocket)
            if not client:
                return False

            success = client.subscribe(channel, room_id)

        if success:
            logger.debug(f"Client {client.user_id} subscribed to {channel.value}")

        return success

    async def unsubscribe(
        self,
        websocket: WebSocket,
        channel: ChannelType,
        room_id: Optional[str] = None,
    ) -> bool:
        """Unsubscribe a client from a channel"""
        async with self._lock:
            client = self._clients.get(websocket)
            if not client:
                return False

            success = client.unsubscribe(channel, room_id)

        if success:
            logger.debug(f"Client {client.user_id} unsubscribed from {channel.value}")

        return success

    async def broadcast_to_channel(
        self,
        channel: ChannelType,
        message: dict,
        room_id: Optional[str] = None,
        exclude_websocket: Optional[WebSocket] = None,
    ) -> int:
        """
        Broadcast a message to all subscribers of a channel

        Args:
            channel: Target channel
            message: Message dict to send
            room_id: Room ID for discussion channels
            exclude_websocket: Optional WebSocket to exclude from broadcast

        Returns:
            Number of clients that received the message
        """
        # Quick snapshot of clients under lock
        async with self._lock:
            clients_snapshot = list(self._clients.values())

        # Filter subscribers outside the lock
        subscribers = [
            client
            for client in clients_snapshot
            if client.is_subscribed(channel, room_id)
            and client.websocket != exclude_websocket
        ]

        if not subscribers:
            return 0

        # Add channel metadata to message
        enriched_message = {
            "channel": channel.value,
            "room_id": room_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **message,
        }

        # Serialize once for all clients
        message_text = json.dumps(enriched_message, default=str)

        # Send in parallel using asyncio.gather
        async def send_to_client(client: ConnectedClient) -> tuple[ConnectedClient, bool]:
            try:
                await client.websocket.send_text(message_text)
                return (client, True)
            except Exception as e:
                logger.warning(f"Failed to send to {client.user_id}: {e}")
                return (client, False)

        results = await asyncio.gather(*[send_to_client(c) for c in subscribers])

        # Process results
        disconnected: list[WebSocket] = []
        sent_count = 0
        for client, success in results:
            if success:
                sent_count += 1
            else:
                disconnected.append(client.websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

        return sent_count

    async def broadcast_to_user(
        self,
        user_id: str,
        message: dict,
        channel: Optional[ChannelType] = None,
    ) -> int:
        """
        Send a message to a specific user (all their connections)

        Args:
            user_id: Target user ID
            message: Message dict to send
            channel: Optional channel context for the message

        Returns:
            Number of connections that received the message
        """
        # Quick snapshot of clients under lock
        async with self._lock:
            clients_snapshot = list(self._clients.values())

        # Filter user clients outside the lock
        user_clients = [c for c in clients_snapshot if c.user_id == user_id]

        if not user_clients:
            return 0

        enriched_message = {
            "channel": channel.value if channel else "direct",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **message,
        }

        # Serialize once for all clients
        message_text = json.dumps(enriched_message, default=str)

        # Send in parallel
        async def send_to_client(client: ConnectedClient) -> tuple[ConnectedClient, bool]:
            try:
                await client.websocket.send_text(message_text)
                return (client, True)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                return (client, False)

        results = await asyncio.gather(*[send_to_client(c) for c in user_clients])

        # Process results
        disconnected: list[WebSocket] = []
        sent_count = 0
        for client, success in results:
            if success:
                sent_count += 1
            else:
                disconnected.append(client.websocket)

        for ws in disconnected:
            await self.disconnect(ws)

        return sent_count

    async def send_to_client(self, websocket: WebSocket, message: dict) -> bool:
        """
        Send a message to a specific client

        Args:
            websocket: Target WebSocket
            message: Message dict to send

        Returns:
            True if sent successfully
        """
        try:
            await websocket.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")
            await self.disconnect(websocket)
            return False

    def get_client(self, websocket: WebSocket) -> Optional[ConnectedClient]:
        """Get client info for a WebSocket"""
        return self._clients.get(websocket)

    def get_channel_subscribers(
        self,
        channel: ChannelType,
        room_id: Optional[str] = None,
    ) -> list[ConnectedClient]:
        """Get all clients subscribed to a channel"""
        return [
            client
            for client in self._clients.values()
            if client.is_subscribed(channel, room_id)
        ]

    @property
    def client_count(self) -> int:
        """Get total number of connected clients"""
        return len(self._clients)

    def get_stats(self) -> dict:
        """Get channel manager statistics"""
        channel_counts: dict[str, int] = {}
        for channel in ChannelType:
            channel_counts[channel.value] = len(self.get_channel_subscribers(channel))

        return {
            "total_clients": self.client_count,
            "channels": channel_counts,
        }


# Global singleton
_channel_manager: Optional[ChannelManager] = None


def get_channel_manager() -> ChannelManager:
    """Get global ChannelManager singleton"""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChannelManager()
    return _channel_manager


def reset_channel_manager() -> None:
    """Reset global ChannelManager (for testing)"""
    global _channel_manager
    _channel_manager = None
