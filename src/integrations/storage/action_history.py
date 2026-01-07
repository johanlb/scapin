"""
Action History Storage

Tracks executed actions for undo capability.

Each action is stored with:
- What was done (action type, parameters)
- When it was done
- What item it affected
- Data needed for rollback

Architecture:
    - Each action is a separate JSON file
    - Filename: {action_id}.json
    - Directory: data/actions/
    - Thread-safe file operations
"""

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("action_history")


class ActionType(str, Enum):
    """Types of actions that can be tracked for undo"""

    # Email actions
    EMAIL_ARCHIVE = "email_archive"
    EMAIL_DELETE = "email_delete"
    EMAIL_MOVE = "email_move"
    EMAIL_FLAG = "email_flag"
    EMAIL_MARK_READ = "email_mark_read"

    # Teams actions
    TEAMS_REPLY = "teams_reply"
    TEAMS_FLAG = "teams_flag"
    TEAMS_MARK_READ = "teams_mark_read"

    # Calendar actions
    CALENDAR_RESPOND = "calendar_respond"
    CALENDAR_CREATE = "calendar_create"
    CALENDAR_UPDATE = "calendar_update"
    CALENDAR_DELETE = "calendar_delete"

    # Queue actions
    QUEUE_APPROVE = "queue_approve"
    QUEUE_REJECT = "queue_reject"
    QUEUE_SNOOZE = "queue_snooze"

    # Note actions
    NOTE_CREATE = "note_create"
    NOTE_UPDATE = "note_update"

    # Task actions
    TASK_CREATE = "task_create"


class ActionStatus(str, Enum):
    """Status of an action"""

    COMPLETED = "completed"
    UNDONE = "undone"
    FAILED = "failed"


@dataclass
class ActionRecord:
    """Record of an executed action"""

    action_id: str
    action_type: ActionType
    item_id: str  # ID of the item the action was performed on
    item_type: str  # email, teams_message, calendar_event, note, task
    executed_at: datetime
    status: ActionStatus = ActionStatus.COMPLETED

    # Data for the action
    action_data: dict[str, Any] = field(default_factory=dict)
    # Example: {"destination": "Archive/Work", "old_folder": "INBOX"}

    # Data needed for rollback
    rollback_data: dict[str, Any] = field(default_factory=dict)
    # Example: {"original_folder": "INBOX", "original_flags": ["\\Seen"]}

    # Result of the action
    result_data: dict[str, Any] = field(default_factory=dict)
    # Example: {"new_uid": 12345, "success": True}

    # Undo information
    undone_at: Optional[datetime] = None
    undo_result: Optional[dict[str, Any]] = None

    # Metadata
    account_id: Optional[str] = None
    user_id: Optional[str] = None


class ActionHistoryStorage:
    """
    JSON-based storage for action history

    Tracks all executed actions for undo capability
    """

    def __init__(self, actions_dir: Optional[Path] = None):
        """
        Initialize action history storage

        Args:
            actions_dir: Directory for action files (default: data/actions)
        """
        self.actions_dir = Path(actions_dir) if actions_dir else Path("data/actions")
        self.actions_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        logger.info("ActionHistoryStorage initialized", extra={"actions_dir": str(self.actions_dir)})

    def save_action(self, record: ActionRecord) -> str:
        """
        Save an action record

        Args:
            record: Action record to save

        Returns:
            action_id: Unique identifier for the action
        """
        file_path = self.actions_dir / f"{record.action_id}.json"

        # Serialize the record
        data = {
            "action_id": record.action_id,
            "action_type": record.action_type.value,
            "item_id": record.item_id,
            "item_type": record.item_type,
            "executed_at": record.executed_at.isoformat(),
            "status": record.status.value,
            "action_data": record.action_data,
            "rollback_data": record.rollback_data,
            "result_data": record.result_data,
            "undone_at": record.undone_at.isoformat() if record.undone_at else None,
            "undo_result": record.undo_result,
            "account_id": record.account_id,
            "user_id": record.user_id,
        }

        with self._lock, open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(
            "Action recorded",
            extra={
                "action_id": record.action_id,
                "action_type": record.action_type.value,
                "item_id": record.item_id,
            },
        )

        return record.action_id

    def create_action(
        self,
        action_type: ActionType,
        item_id: str,
        item_type: str,
        action_data: Optional[dict[str, Any]] = None,
        rollback_data: Optional[dict[str, Any]] = None,
        result_data: Optional[dict[str, Any]] = None,
        account_id: Optional[str] = None,
    ) -> ActionRecord:
        """
        Create and save a new action record

        Args:
            action_type: Type of action
            item_id: ID of the item acted upon
            item_type: Type of item (email, teams_message, etc.)
            action_data: Data about what was done
            rollback_data: Data needed to undo the action
            result_data: Result of the action
            account_id: Account identifier

        Returns:
            ActionRecord: The created record
        """
        record = ActionRecord(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            item_id=item_id,
            item_type=item_type,
            executed_at=now_utc(),
            status=ActionStatus.COMPLETED,
            action_data=action_data or {},
            rollback_data=rollback_data or {},
            result_data=result_data or {},
            account_id=account_id,
        )

        self.save_action(record)
        return record

    def get_action(self, action_id: str) -> Optional[ActionRecord]:
        """
        Get an action record by ID

        Args:
            action_id: Action identifier

        Returns:
            ActionRecord or None if not found
        """
        file_path = self.actions_dir / f"{action_id}.json"

        if not file_path.exists():
            return None

        try:
            with self._lock, open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            return ActionRecord(
                action_id=data["action_id"],
                action_type=ActionType(data["action_type"]),
                item_id=data["item_id"],
                item_type=data["item_type"],
                executed_at=datetime.fromisoformat(data["executed_at"]),
                status=ActionStatus(data["status"]),
                action_data=data.get("action_data", {}),
                rollback_data=data.get("rollback_data", {}),
                result_data=data.get("result_data", {}),
                undone_at=(
                    datetime.fromisoformat(data["undone_at"]) if data.get("undone_at") else None
                ),
                undo_result=data.get("undo_result"),
                account_id=data.get("account_id"),
                user_id=data.get("user_id"),
            )

        except Exception as e:
            logger.error(f"Failed to load action {action_id}: {e}")
            return None

    def get_actions_for_item(
        self,
        item_id: str,
        status: Optional[ActionStatus] = None,
    ) -> list[ActionRecord]:
        """
        Get all actions for an item

        Args:
            item_id: Item identifier
            status: Filter by status (optional)

        Returns:
            List of action records (newest first)
        """
        actions = []

        with self._lock:
            for file_path in self.actions_dir.glob("*.json"):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)

                    if data.get("item_id") != item_id:
                        continue

                    if status and data.get("status") != status.value:
                        continue

                    actions.append(
                        ActionRecord(
                            action_id=data["action_id"],
                            action_type=ActionType(data["action_type"]),
                            item_id=data["item_id"],
                            item_type=data["item_type"],
                            executed_at=datetime.fromisoformat(data["executed_at"]),
                            status=ActionStatus(data["status"]),
                            action_data=data.get("action_data", {}),
                            rollback_data=data.get("rollback_data", {}),
                            result_data=data.get("result_data", {}),
                            undone_at=(
                                datetime.fromisoformat(data["undone_at"])
                                if data.get("undone_at")
                                else None
                            ),
                            undo_result=data.get("undo_result"),
                            account_id=data.get("account_id"),
                            user_id=data.get("user_id"),
                        )
                    )

                except Exception as e:
                    logger.warning(f"Failed to load action {file_path.name}: {e}")

        # Sort by executed_at, newest first
        actions.sort(key=lambda x: x.executed_at, reverse=True)
        return actions

    def get_recent_actions(
        self,
        limit: int = 50,
        item_type: Optional[str] = None,
        action_type: Optional[ActionType] = None,
        status: Optional[ActionStatus] = None,
    ) -> list[ActionRecord]:
        """
        Get recent actions

        Args:
            limit: Maximum number of actions to return
            item_type: Filter by item type
            action_type: Filter by action type
            status: Filter by status

        Returns:
            List of action records (newest first)
        """
        actions = []

        with self._lock:
            for file_path in self.actions_dir.glob("*.json"):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)

                    # Apply filters
                    if item_type and data.get("item_type") != item_type:
                        continue

                    if action_type and data.get("action_type") != action_type.value:
                        continue

                    if status and data.get("status") != status.value:
                        continue

                    actions.append(
                        ActionRecord(
                            action_id=data["action_id"],
                            action_type=ActionType(data["action_type"]),
                            item_id=data["item_id"],
                            item_type=data["item_type"],
                            executed_at=datetime.fromisoformat(data["executed_at"]),
                            status=ActionStatus(data["status"]),
                            action_data=data.get("action_data", {}),
                            rollback_data=data.get("rollback_data", {}),
                            result_data=data.get("result_data", {}),
                            undone_at=(
                                datetime.fromisoformat(data["undone_at"])
                                if data.get("undone_at")
                                else None
                            ),
                            undo_result=data.get("undo_result"),
                            account_id=data.get("account_id"),
                            user_id=data.get("user_id"),
                        )
                    )

                except Exception as e:
                    logger.warning(f"Failed to load action {file_path.name}: {e}")

        # Sort by executed_at, newest first
        actions.sort(key=lambda x: x.executed_at, reverse=True)
        return actions[:limit]

    def get_last_action_for_item(self, item_id: str) -> Optional[ActionRecord]:
        """
        Get the most recent action for an item

        Args:
            item_id: Item identifier

        Returns:
            Most recent ActionRecord or None
        """
        actions = self.get_actions_for_item(item_id, status=ActionStatus.COMPLETED)
        return actions[0] if actions else None

    def mark_undone(
        self,
        action_id: str,
        undo_result: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Mark an action as undone

        Args:
            action_id: Action identifier
            undo_result: Result of the undo operation

        Returns:
            True if successful
        """
        record = self.get_action(action_id)
        if not record:
            return False

        record.status = ActionStatus.UNDONE
        record.undone_at = now_utc()
        record.undo_result = undo_result

        self.save_action(record)
        logger.info("Action marked as undone", extra={"action_id": action_id})
        return True

    def can_undo(self, action_id: str) -> bool:
        """
        Check if an action can be undone

        Args:
            action_id: Action identifier

        Returns:
            True if action exists and is in COMPLETED status
        """
        record = self.get_action(action_id)
        if not record:
            return False

        return record.status == ActionStatus.COMPLETED

    def get_stats(self) -> dict[str, Any]:
        """
        Get action history statistics

        Returns:
            Dictionary with stats
        """
        all_actions = []

        with self._lock:
            for file_path in self.actions_dir.glob("*.json"):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                    all_actions.append(data)
                except Exception:
                    pass

        if not all_actions:
            return {
                "total": 0,
                "by_type": {},
                "by_status": {},
                "by_item_type": {},
            }

        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_item_type: dict[str, int] = {}

        for action in all_actions:
            action_type = action.get("action_type", "unknown")
            status = action.get("status", "unknown")
            item_type = action.get("item_type", "unknown")

            by_type[action_type] = by_type.get(action_type, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
            by_item_type[item_type] = by_item_type.get(item_type, 0) + 1

        return {
            "total": len(all_actions),
            "by_type": by_type,
            "by_status": by_status,
            "by_item_type": by_item_type,
        }


# Singleton instance
_action_history_instance: Optional[ActionHistoryStorage] = None
_action_history_lock = threading.Lock()


def get_action_history(actions_dir: Optional[Path] = None) -> ActionHistoryStorage:
    """
    Get global ActionHistoryStorage instance (thread-safe singleton)

    Args:
        actions_dir: Actions directory (only used on first call)

    Returns:
        ActionHistoryStorage instance
    """
    global _action_history_instance

    if _action_history_instance is None:
        with _action_history_lock:
            # Double-check locking
            if _action_history_instance is None:
                _action_history_instance = ActionHistoryStorage(actions_dir=actions_dir)

    return _action_history_instance
