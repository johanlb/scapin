"""
Microsoft Integration Module

Provides integration with Microsoft Graph API for Teams, Calendar, etc.

Modules:
    - auth: MSAL OAuth 2.0 authentication
    - graph_client: Microsoft Graph API client
    - models: Data models for Teams messages, chats, etc.
    - teams_client: Teams-specific operations
    - teams_normalizer: Normalize Teams messages to PerceivedEvent
"""

from src.integrations.microsoft.auth import (
    AuthenticationError,
    MicrosoftAuthenticator,
    TokenCache,
)
from src.integrations.microsoft.graph_client import GraphAPIError, GraphClient
from src.integrations.microsoft.models import (
    TeamsChat,
    TeamsChatType,
    TeamsMessage,
    TeamsSender,
)
from src.integrations.microsoft.teams_client import TeamsClient
from src.integrations.microsoft.teams_normalizer import TeamsNormalizer

__all__ = [
    # Auth
    "MicrosoftAuthenticator",
    "TokenCache",
    "AuthenticationError",
    # Graph
    "GraphClient",
    "GraphAPIError",
    # Models
    "TeamsMessage",
    "TeamsChat",
    "TeamsSender",
    "TeamsChatType",
    # Client
    "TeamsClient",
    # Normalizer
    "TeamsNormalizer",
]
