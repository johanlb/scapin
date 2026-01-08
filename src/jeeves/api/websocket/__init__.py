"""WebSocket Handlers"""

from src.jeeves.api.websocket.channels import (
    ChannelManager,
    ChannelType,
    ConnectedClient,
    get_channel_manager,
    reset_channel_manager,
)
from src.jeeves.api.websocket.manager import (
    ConnectionManager,
    get_connection_manager,
    reset_connection_manager,
)
from src.jeeves.api.websocket.router_v2 import router as ws_router

__all__ = [
    # Channel management (v2)
    "ChannelManager",
    "ChannelType",
    "ConnectedClient",
    "get_channel_manager",
    "reset_channel_manager",
    # Legacy manager
    "ConnectionManager",
    "get_connection_manager",
    "reset_connection_manager",
    # Router
    "ws_router",
]
