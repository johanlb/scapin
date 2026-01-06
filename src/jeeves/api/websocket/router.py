"""
WebSocket Router

Provides the /ws/live endpoint for real-time event streaming.
Authentication via first message (more secure than query parameter).
"""

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.core.config_manager import get_config
from src.jeeves.api.auth import JWTHandler
from src.jeeves.api.websocket.manager import get_connection_manager
from src.monitoring.logger import ScapinLogger

logger = ScapinLogger.get_logger(__name__)

router = APIRouter()


@router.websocket("/live")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None, description="JWT access token (deprecated, use first message auth)"),
):
    """
    WebSocket endpoint for real-time event streaming

    Connect to receive live events from Scapin processing.

    Authentication (two methods supported):
        1. First message auth (preferred): Send {"type": "auth", "token": "YOUR_JWT"}
        2. Query param (deprecated): ws://localhost:8000/ws/live?token=YOUR_JWT

    Usage:
        const ws = new WebSocket('ws://localhost:8000/ws/live');
        ws.onopen = () => ws.send(JSON.stringify({type: 'auth', token: 'YOUR_JWT'}));

    Messages received:
        - {"type": "authenticated"} - Auth successful
        - {"type": "connected", ...} - Initial connection confirmation
        - {"type": "event", "data": {...}} - Processing events

    Events include:
        - processing_started/completed
        - account_started/completed/error
        - email_started/analyzing/completed/queued/executed/error
        - batch_started/completed/progress
        - system_ready/error
    """
    config = get_config()
    manager = get_connection_manager()
    jwt_handler = JWTHandler()

    # Accept the WebSocket connection first
    await websocket.accept()

    # Authenticate if auth is enabled
    if config.auth.enabled:
        authenticated = False

        # Try query param first (deprecated but still supported for backwards compat)
        if token:
            token_data = jwt_handler.verify_token(token)
            if token_data:
                authenticated = True
                logger.info(f"WebSocket authenticated via query param: {token_data.sub}")
                # Note: Query param auth works but is deprecated
                logger.warning(
                    "WebSocket auth via query param is deprecated. "
                    "Use first message auth: {\"type\": \"auth\", \"token\": \"...\"}"
                )

        # If not authenticated via query, wait for first message auth
        if not authenticated:
            try:
                # Wait for auth message (with timeout handled by client)
                auth_message = await websocket.receive_text()
                auth_data = json.loads(auth_message)

                if auth_data.get("type") == "auth" and auth_data.get("token"):
                    token_data = jwt_handler.verify_token(auth_data["token"])
                    if token_data:
                        authenticated = True
                        logger.info(f"WebSocket authenticated via first message: {token_data.sub}")
                        await websocket.send_json({"type": "authenticated", "user": token_data.sub})
                    else:
                        await websocket.close(code=4001, reason="Invalid or expired token")
                        logger.warning("WebSocket connection rejected: Invalid token")
                        return
                else:
                    await websocket.close(code=4001, reason="Expected auth message")
                    logger.warning("WebSocket connection rejected: No auth message")
                    return
            except json.JSONDecodeError:
                await websocket.close(code=4001, reason="Invalid auth message format")
                logger.warning("WebSocket connection rejected: Invalid JSON")
                return
            except Exception as e:
                await websocket.close(code=4001, reason="Authentication failed")
                logger.warning(f"WebSocket auth error: {e}")
                return

        if not authenticated:
            await websocket.close(code=4001, reason="Authentication required")
            logger.warning("WebSocket connection rejected: Not authenticated")
            return

    # Connect and handle messages (WebSocket already accepted for auth)
    await manager.connect(websocket, already_accepted=True)

    try:
        while True:
            # Wait for messages from client (keepalive, etc.)
            data = await websocket.receive_text()

            # Handle client messages
            if data == "ping":
                await websocket.send_text("pong")
            else:
                logger.debug(f"Received from client: {data}")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)
