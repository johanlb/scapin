"""
Apple Integrations

Integration modules for Apple ecosystem services.
"""

from src.integrations.apple.calendar_client import (
    ICloudCalendarClient,
    ICloudCalendarConfig,
)
from src.integrations.apple.calendar_models import (
    ICloudAttendee,
    ICloudAttendeeStatus,
    ICloudCalendar,
    ICloudCalendarEvent,
    ICloudCalendarSearchResult,
    ICloudEventStatus,
)
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
    # iCloud Calendar Client
    "ICloudCalendarClient",
    "ICloudCalendarConfig",
    # iCloud Calendar Models
    "ICloudCalendarEvent",
    "ICloudCalendar",
    "ICloudAttendee",
    "ICloudAttendeeStatus",
    "ICloudEventStatus",
    "ICloudCalendarSearchResult",
    # Apple Notes Client
    "AppleNotesClient",
    "get_apple_notes_client",
    # Apple Notes Models
    "AppleNote",
    "AppleFolder",
    "SyncDirection",
    "SyncAction",
    "ConflictResolution",
    "SyncConflict",
    "SyncResult",
    "SyncMapping",
    # Apple Notes Sync
    "AppleNotesSync",
    "get_apple_notes_sync",
]
