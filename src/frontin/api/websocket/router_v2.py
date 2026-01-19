"""
WebSocket Router v2

Enhanced WebSocket endpoints with channel subscriptions.
Supports: /ws/events, /ws/status, /ws/notifications, /ws/discussions/{id}

Authentication via first message: {"type": "auth", "token": "JWT"}
"""

import json
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.config_manager import get_config
from src.frontin.api.auth import JWTHandler
from src.frontin.api.websocket.channels import (
    ChannelManager,
    ChannelType,
    get_channel_manager,
)
from src.monitoring.logger import ScapinLogger

logger = ScapinLogger.get_logger(__name__)

# Rate limiting configuration
RATE_LIMIT_MESSAGES = 30  # Max messages
RATE_LIMIT_WINDOW = 60  # Per 60 seconds

router = APIRouter()


async def authenticate_websocket(
    websocket: WebSocket,
    jwt_handler: JWTHandler,
    config_auth_enabled: bool,
) -> Optional[str]:
    """
    Authenticate WebSocket connection via first message

    Args:
        websocket: WebSocket to authenticate
        jwt_handler: JWT handler for token verification
        config_auth_enabled: Whether auth is enabled

    Returns:
        User ID if authenticated, None if failed (connection already closed)
    """
    if not config_auth_enabled:
        return "anonymous"

    try:
        # Wait for auth message
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)

        if auth_data.get("type") == "auth" and auth_data.get("token"):
            token_data = jwt_handler.verify_token(auth_data["token"])
            if token_data:
                await websocket.send_json({"type": "authenticated", "user": token_data.sub})
                logger.info(f"WebSocket authenticated: {token_data.sub}")
                return token_data.sub
            else:
                await websocket.close(code=4001, reason="Invalid or expired token")
                return None
        else:
            await websocket.close(code=4001, reason="Expected auth message")
            return None

    except json.JSONDecodeError:
        await websocket.close(code=4001, reason="Invalid JSON")
        return None
    except WebSocketDisconnect:
        return None
    except Exception as e:
        logger.warning(f"WebSocket auth error: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return None


async def handle_client_messages(
    websocket: WebSocket,
    manager: ChannelManager,
    user_id: str,
) -> None:
    """
    Handle messages from connected client

    Supports:
        - {"type": "ping"} → {"type": "pong"}
        - {"type": "subscribe", "channel": "...", "room_id": "..."} → Subscribe to channel
        - {"type": "unsubscribe", "channel": "...", "room_id": "..."} → Unsubscribe

    Includes rate limiting to prevent abuse.
    """
    # Rate limiting state
    message_times: list[float] = []

    while True:
        try:
            data = await websocket.receive_text()

            # Rate limiting check
            now = time.time()
            # Remove old timestamps outside the window
            message_times = [t for t in message_times if now - t < RATE_LIMIT_WINDOW]
            message_times.append(now)

            if len(message_times) > RATE_LIMIT_MESSAGES:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Rate limit exceeded. Please slow down.",
                })
                continue

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
                continue

            # Parse JSON messages
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "subscribe":
                channel_str = message.get("channel")
                room_id = message.get("room_id")
                try:
                    channel = ChannelType(channel_str)
                    success = await manager.subscribe(websocket, channel, room_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel_str,
                        "room_id": room_id,
                        "success": success,
                    })
                except ValueError:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown channel: {channel_str}",
                    })

            elif msg_type == "unsubscribe":
                channel_str = message.get("channel")
                room_id = message.get("room_id")
                try:
                    channel = ChannelType(channel_str)
                    success = await manager.unsubscribe(websocket, channel, room_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channel": channel_str,
                        "room_id": room_id,
                        "success": success,
                    })
                except ValueError:
                    logger.warning(f"Invalid channel for unsubscribe: {channel_str}")

            else:
                logger.debug(f"Unknown message type from {user_id}: {msg_type}")

        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.error(f"Error handling client message: {e}")


@router.websocket("/events")
async def websocket_events(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time processing events

    Events include:
        - Email processing (started, analyzing, completed, queued, executed)
        - Teams messages (new, reply, flag)
        - Calendar events (new, updated, conflict)
        - Queue updates (item added, approved, rejected)
        - Notes (review due, enriched)

    Authentication:
        Send first message: {"type": "auth", "token": "YOUR_JWT"}

    Subscribe to additional channels:
        {"type": "subscribe", "channel": "status"}
        {"type": "subscribe", "channel": "notifications"}
    """
    await websocket.accept()

    config = get_config()
    jwt_handler = JWTHandler()
    manager = get_channel_manager()

    # Authenticate
    user_id = await authenticate_websocket(websocket, jwt_handler, config.auth.enabled)
    if not user_id:
        return

    # Connect and auto-subscribe to events channel
    client = await manager.connect(websocket, user_id, auto_subscribe=[ChannelType.EVENTS])

    await websocket.send_json({
        "type": "connected",
        "channel": "events",
        "message": "Connected to Scapin events stream",
        "subscriptions": [s.channel.value for s in client.subscriptions],
    })

    try:
        await handle_client_messages(websocket, manager, user_id)
    except WebSocketDisconnect:
        logger.info(f"Events client disconnected: {user_id}")
    finally:
        await manager.disconnect(websocket)


@router.websocket("/status")
async def websocket_status(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for system status updates

    Status updates include:
        - Worker status (running, idle, paused)
        - Processing progress
        - System health changes
        - Integration connection status

    Authentication:
        Send first message: {"type": "auth", "token": "YOUR_JWT"}
    """
    await websocket.accept()

    config = get_config()
    jwt_handler = JWTHandler()
    manager = get_channel_manager()

    user_id = await authenticate_websocket(websocket, jwt_handler, config.auth.enabled)
    if not user_id:
        return

    client = await manager.connect(websocket, user_id, auto_subscribe=[ChannelType.STATUS])

    await websocket.send_json({
        "type": "connected",
        "channel": "status",
        "message": "Connected to Scapin status stream",
        "subscriptions": [s.channel.value for s in client.subscriptions],
    })

    try:
        await handle_client_messages(websocket, manager, user_id)
    except WebSocketDisconnect:
        logger.info(f"Status client disconnected: {user_id}")
    finally:
        await manager.disconnect(websocket)


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for user notifications

    Notifications include:
        - New items requiring attention
        - Action confirmations (approved, rejected)
        - Reminders (snoozed items due)
        - System alerts

    Authentication:
        Send first message: {"type": "auth", "token": "YOUR_JWT"}
    """
    await websocket.accept()

    config = get_config()
    jwt_handler = JWTHandler()
    manager = get_channel_manager()

    user_id = await authenticate_websocket(websocket, jwt_handler, config.auth.enabled)
    if not user_id:
        return

    client = await manager.connect(
        websocket,
        user_id,
        auto_subscribe=[ChannelType.NOTIFICATIONS],
    )

    await websocket.send_json({
        "type": "connected",
        "channel": "notifications",
        "message": "Connected to Scapin notifications stream",
        "subscriptions": [s.channel.value for s in client.subscriptions],
    })

    try:
        await handle_client_messages(websocket, manager, user_id)
    except WebSocketDisconnect:
        logger.info(f"Notifications client disconnected: {user_id}")
    finally:
        await manager.disconnect(websocket)


@router.websocket("/discussions/{discussion_id}")
async def websocket_discussion(websocket: WebSocket, discussion_id: str) -> None:
    """
    WebSocket endpoint for real-time discussion chat

    Join a specific discussion room for live updates.

    Messages include:
        - New messages in the discussion
        - AI suggestions
        - Typing indicators
        - Read receipts

    Authentication:
        Send first message: {"type": "auth", "token": "YOUR_JWT"}

    Args:
        discussion_id: ID of the discussion to join
    """
    await websocket.accept()

    config = get_config()
    jwt_handler = JWTHandler()
    manager = get_channel_manager()

    user_id = await authenticate_websocket(websocket, jwt_handler, config.auth.enabled)
    if not user_id:
        return

    # Connect and subscribe to the specific discussion room
    client = await manager.connect(websocket, user_id)
    await manager.subscribe(websocket, ChannelType.DISCUSSION, room_id=discussion_id)

    await websocket.send_json({
        "type": "connected",
        "channel": "discussion",
        "room_id": discussion_id,
        "message": f"Joined discussion room: {discussion_id}",
        "subscriptions": [
            {"channel": s.channel.value, "room_id": s.room_id}
            for s in client.subscriptions
        ],
    })

    try:
        await handle_client_messages(websocket, manager, user_id)
    except WebSocketDisconnect:
        logger.info(f"Discussion client disconnected: {user_id} from {discussion_id}")
    finally:
        await manager.disconnect(websocket)


# Legacy endpoint (kept for backwards compatibility)
@router.websocket("/live")
async def websocket_live(websocket: WebSocket) -> None:
    """
    Legacy WebSocket endpoint (deprecated)

    Use /ws/events instead for better channel control.

    This endpoint auto-subscribes to all channels for backwards compatibility.
    """
    await websocket.accept()

    config = get_config()
    jwt_handler = JWTHandler()
    manager = get_channel_manager()

    user_id = await authenticate_websocket(websocket, jwt_handler, config.auth.enabled)
    if not user_id:
        return

    # Auto-subscribe to all channels for backwards compat
    client = await manager.connect(
        websocket,
        user_id,
        auto_subscribe=[ChannelType.EVENTS, ChannelType.STATUS, ChannelType.NOTIFICATIONS],
    )

    await websocket.send_json({
        "type": "connected",
        "message": "Connected to Scapin live events (deprecated, use /ws/events)",
        "subscriptions": [s.channel.value for s in client.subscriptions],
    })

    try:
        await handle_client_messages(websocket, manager, user_id)
    except WebSocketDisconnect:
        logger.info(f"Live client disconnected: {user_id}")
    finally:
        await manager.disconnect(websocket)
