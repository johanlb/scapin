"""
Storage integrations

JSON-based storage systems for various application data.
"""

from src.integrations.storage.action_history import (
    ActionHistoryStorage,
    ActionRecord,
    ActionStatus,
    ActionType,
    get_action_history,
)
from src.integrations.storage.draft_storage import (
    DraftReply,
    DraftStatus,
    DraftStorage,
    ReplyFormat,
    get_draft_storage,
)
from src.integrations.storage.queue_storage import QueueStorage, get_queue_storage
from src.integrations.storage.snooze_storage import (
    SnoozeReason,
    SnoozeRecord,
    SnoozeStorage,
    get_snooze_storage,
    snooze_until_later_today,
    snooze_until_next_week,
    snooze_until_tomorrow,
)

__all__ = [
    # Queue Storage
    "QueueStorage",
    "get_queue_storage",
    # Action History
    "ActionHistoryStorage",
    "ActionRecord",
    "ActionStatus",
    "ActionType",
    "get_action_history",
    # Snooze Storage
    "SnoozeStorage",
    "SnoozeRecord",
    "SnoozeReason",
    "get_snooze_storage",
    "snooze_until_later_today",
    "snooze_until_tomorrow",
    "snooze_until_next_week",
    # Draft Storage
    "DraftStorage",
    "DraftReply",
    "DraftStatus",
    "ReplyFormat",
    "get_draft_storage",
]
