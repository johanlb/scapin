"""
WebSocket Router

Provides the /ws/live endpoint for real-time event streaming.
Authentication via JWT token in query parameter.
"""

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
    token: str = Query(None, description="JWT access token"),
):
    """
    WebSocket endpoint for real-time event streaming

    Connect to receive live events from Scapin processing.

    Authentication:
        - If auth is enabled: Requires valid JWT token in query param
        - If auth is disabled: No token required

    Usage:
        ws://localhost:8000/ws/live?token=YOUR_JWT_TOKEN

    Messages received:
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

    # Authenticate if auth is enabled
    if config.auth.enabled:
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            logger.warning("WebSocket connection rejected: No token provided")
            return

        jwt_handler = JWTHandler()
        token_data = jwt_handler.verify_token(token)

        if token_data is None:
            await websocket.close(code=4001, reason="Invalid or expired token")
            logger.warning("WebSocket connection rejected: Invalid token")
            return

        logger.info(f"WebSocket authenticated: {token_data.sub}")

    # Connect and handle messages
    await manager.connect(websocket)

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
