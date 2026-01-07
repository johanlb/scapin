"""
Apple Integrations

Integration modules for Apple ecosystem services.
"""

from src.integrations.apple.notes_client import AppleNotesClient, get_apple_notes_client
from src.integrations.apple.notes_models import (
    AppleFolder,
    AppleNote,
    ConflictResolution,
    SyncAction,
    SyncConflict,
    SyncDirection,
    SyncMapping,
    SyncResult,
)
from src.integrations.apple.notes_sync import AppleNotesSync, get_apple_notes_sync

__all__ = [
    # Client
    "AppleNotesClient",
    "get_apple_notes_client",
    # Models
    "AppleNote",
    "AppleFolder",
    "SyncDirection",
    "SyncAction",
    "ConflictResolution",
    "SyncConflict",
    "SyncResult",
    "SyncMapping",
    # Sync
    "AppleNotesSync",
    "get_apple_notes_sync",
]
