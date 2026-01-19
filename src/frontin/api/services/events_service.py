"""
Events Service

Async service for snooze and undo operations.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from src.integrations.storage.action_history import (
    ActionHistoryStorage,
    ActionRecord,
    ActionStatus,
    ActionType,
    get_action_history,
)
from src.integrations.storage.queue_storage import QueueStorage, get_queue_storage
from src.integrations.storage.snooze_storage import (
    SnoozeReason,
    SnoozeRecord,
    SnoozeStorage,
    get_snooze_storage,
)
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("api.events_service")


class EventsService:
    """Async service for snooze and undo operations"""

    def __init__(self) -> None:
        """Initialize events service"""
        self._snooze_storage: Optional[SnoozeStorage] = None
        self._action_history: Optional[ActionHistoryStorage] = None
        self._queue_storage: Optional[QueueStorage] = None

    @property
    def snooze_storage(self) -> SnoozeStorage:
        """Lazy load snooze storage"""
        if self._snooze_storage is None:
            self._snooze_storage = get_snooze_storage()
        return self._snooze_storage

    @property
    def action_history(self) -> ActionHistoryStorage:
        """Lazy load action history"""
        if self._action_history is None:
            self._action_history = get_action_history()
        return self._action_history

    @property
    def queue_storage(self) -> QueueStorage:
        """Lazy load queue storage"""
        if self._queue_storage is None:
            self._queue_storage = get_queue_storage()
        return self._queue_storage

    async def snooze_item(
        self,
        item_id: str,
        hours: Optional[int] = None,
        days: Optional[int] = None,
        until: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> SnoozeRecord:
        """
        Snooze a queue item

        Args:
            item_id: Queue item ID
            hours: Hours to snooze
            days: Days to snooze
            until: Specific datetime to snooze until
            reason: Reason for snoozing

        Returns:
            SnoozeRecord
        """
        # Get the queue item to verify it exists and get original data
        queue_item = self.queue_storage.get_item(item_id)
        if not queue_item:
            raise ValueError(f"Queue item not found: {item_id}")

        # Calculate snooze_until
        if until:
            snooze_until = until
        elif hours or days:
            delta = timedelta(hours=hours or 0, days=days or 0)
            snooze_until = now_utc() + delta
        else:
            # Default: 3 hours
            snooze_until = now_utc() + timedelta(hours=3)

        # Determine reason enum
        snooze_reason = SnoozeReason.CUSTOM
        if hours and hours <= 4:
            snooze_reason = SnoozeReason.LATER_TODAY
        elif days == 1:
            snooze_reason = SnoozeReason.TOMORROW
        elif days and days >= 7:
            snooze_reason = SnoozeReason.NEXT_WEEK

        # Create snooze record
        record = self.snooze_storage.snooze_item(
            item_id=item_id,
            item_type="queue_item",
            snooze_until=snooze_until,
            reason=snooze_reason,
            reason_text=reason,
            original_data=queue_item,
            account_id=queue_item.get("account_id"),
        )

        # Update queue item status
        self.queue_storage.update_item(item_id, {"status": "snoozed"})

        # Record the action
        self.action_history.create_action(
            action_type=ActionType.QUEUE_SNOOZE,
            item_id=item_id,
            item_type="queue_item",
            action_data={
                "snooze_until": snooze_until.isoformat(),
                "reason": reason,
            },
            rollback_data={
                "original_status": queue_item.get("status", "pending"),
            },
            result_data={
                "snooze_id": record.snooze_id,
            },
            account_id=queue_item.get("account_id"),
        )

        logger.info(
            "Item snoozed via API",
            extra={
                "item_id": item_id,
                "snooze_id": record.snooze_id,
                "snooze_until": snooze_until.isoformat(),
            },
        )

        return record

    async def unsnooze_item(self, item_id: str) -> Optional[SnoozeRecord]:
        """
        Unsnooze an item (cancel snooze)

        Args:
            item_id: Item ID

        Returns:
            The snooze record or None if not found
        """
        record = self.snooze_storage.unsnooze_item(item_id)

        if record:
            # Restore queue item status
            self.queue_storage.update_item(item_id, {"status": "pending"})

            logger.info("Item unsnoozed via API", extra={"item_id": item_id})

        return record

    async def get_snoozed_items(
        self,
        item_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get all snoozed items with preview data

        Args:
            item_type: Filter by item type

        Returns:
            List of snoozed items with preview data
        """
        records = self.snooze_storage.get_snoozed_items(item_type=item_type)
        now = now_utc()

        result = []
        for record in records:
            # Calculate time remaining
            time_remaining = record.snooze_until - now
            time_remaining_minutes = max(0, int(time_remaining.total_seconds() / 60))

            # Get item preview from original data
            item_preview = {}
            if record.original_data:
                metadata = record.original_data.get("metadata", {})
                item_preview = {
                    "subject": metadata.get("subject", ""),
                    "from_name": metadata.get("from_name", ""),
                    "from_address": metadata.get("from_address", ""),
                }

            result.append({
                "snooze_id": record.snooze_id,
                "item_id": record.item_id,
                "item_type": record.item_type,
                "snoozed_at": record.snoozed_at,
                "snooze_until": record.snooze_until,
                "reason": record.reason_text or record.reason.value,
                "time_remaining_minutes": time_remaining_minutes,
                "is_expired": time_remaining_minutes == 0,
                "item_preview": item_preview,
            })

        return result

    async def wake_expired_snoozes(self) -> list[SnoozeRecord]:
        """
        Wake up all expired snoozes and restore items

        Returns:
            List of woken snooze records
        """
        woken = self.snooze_storage.wake_expired_snoozes()

        for record in woken:
            # Restore queue item status
            self.queue_storage.update_item(record.item_id, {"status": "pending"})

            logger.info(
                "Expired snooze woken",
                extra={
                    "item_id": record.item_id,
                    "snooze_id": record.snooze_id,
                },
            )

        return woken

    async def get_action_history(
        self,
        item_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[ActionRecord]:
        """
        Get action history

        Args:
            item_id: Filter by item ID
            limit: Maximum number of actions

        Returns:
            List of action records
        """
        if item_id:
            return self.action_history.get_actions_for_item(item_id)
        return self.action_history.get_recent_actions(limit=limit)

    async def undo_action(
        self,
        action_id: str,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Undo an action

        Args:
            action_id: Action ID to undo
            reason: Reason for undoing

        Returns:
            Undo result
        """
        record = self.action_history.get_action(action_id)

        if not record:
            raise ValueError(f"Action not found: {action_id}")

        if not self.action_history.can_undo(action_id):
            raise ValueError(f"Action cannot be undone (status: {record.status.value})")

        # Perform undo based on action type
        undo_result = await self._perform_undo(record)

        # Mark action as undone
        self.action_history.mark_undone(
            action_id,
            undo_result={
                "reason": reason,
                "result": undo_result,
            },
        )

        logger.info(
            "Action undone",
            extra={
                "action_id": action_id,
                "action_type": record.action_type.value,
                "item_id": record.item_id,
            },
        )

        return undo_result

    async def _perform_undo(self, record: ActionRecord) -> dict[str, Any]:
        """
        Perform the actual undo operation

        Args:
            record: Action record to undo

        Returns:
            Undo result
        """
        action_type = record.action_type

        if action_type == ActionType.QUEUE_APPROVE:
            return await self._undo_queue_approve(record)
        elif action_type == ActionType.QUEUE_REJECT:
            return await self._undo_queue_reject(record)
        elif action_type == ActionType.QUEUE_SNOOZE:
            return await self._undo_queue_snooze(record)
        elif action_type in (ActionType.EMAIL_ARCHIVE, ActionType.EMAIL_MOVE):
            return await self._undo_email_move(record)
        elif action_type == ActionType.EMAIL_DELETE:
            return await self._undo_email_delete(record)
        else:
            return {
                "success": False,
                "message": f"Undo not implemented for {action_type.value}",
            }

    async def _undo_queue_approve(self, record: ActionRecord) -> dict[str, Any]:
        """Undo a queue approve action"""
        # Restore queue item to pending status
        original_status = record.rollback_data.get("original_status", "pending")
        success = self.queue_storage.update_item(
            record.item_id,
            {"status": original_status, "reviewed_at": None, "review_decision": None},
        )

        return {
            "success": success,
            "message": "Item restored to queue" if success else "Failed to restore item",
            "restored_status": original_status,
        }

    async def _undo_queue_reject(self, record: ActionRecord) -> dict[str, Any]:
        """Undo a queue reject action"""
        # Restore queue item to pending status
        original_status = record.rollback_data.get("original_status", "pending")
        success = self.queue_storage.update_item(
            record.item_id,
            {"status": original_status, "reviewed_at": None, "review_decision": None},
        )

        return {
            "success": success,
            "message": "Item restored to queue" if success else "Failed to restore item",
            "restored_status": original_status,
        }

    async def _undo_queue_snooze(self, record: ActionRecord) -> dict[str, Any]:
        """Undo a queue snooze action"""
        # Unsnooze the item
        snooze_record = self.snooze_storage.unsnooze_item(record.item_id)

        if snooze_record:
            # Restore original status
            original_status = record.rollback_data.get("original_status", "pending")
            self.queue_storage.update_item(record.item_id, {"status": original_status})

            return {
                "success": True,
                "message": "Item unsnoozed",
                "restored_status": original_status,
            }

        return {
            "success": False,
            "message": "No active snooze found",
        }

    async def _undo_email_move(self, record: ActionRecord) -> dict[str, Any]:
        """Undo an email move/archive action"""
        # Would need IMAP client to move email back
        # For now, return a message
        original_folder = record.rollback_data.get("original_folder", "INBOX")

        return {
            "success": False,
            "message": f"Email should be moved back to {original_folder}",
            "requires_imap": True,
            "original_folder": original_folder,
        }

    async def _undo_email_delete(self, _record: ActionRecord) -> dict[str, Any]:
        """Undo an email delete action"""
        # Would need to restore from Trash
        return {
            "success": False,
            "message": "Email should be restored from Trash",
            "requires_imap": True,
        }

    async def get_stats(self) -> dict[str, Any]:
        """
        Get events statistics

        Returns:
            Statistics dict
        """
        snooze_stats = self.snooze_storage.get_stats()
        action_stats = self.action_history.get_stats()

        # Count undoable actions
        recent_actions = self.action_history.get_recent_actions(limit=100)
        undoable_count = sum(
            1 for a in recent_actions if a.status == ActionStatus.COMPLETED
        )

        return {
            "snoozed_count": snooze_stats.get("active", 0),
            "expired_pending": snooze_stats.get("expired_pending", 0),
            "total_actions": action_stats.get("total", 0),
            "undoable_actions": undoable_count,
            "actions_by_type": action_stats.get("by_type", {}),
        }
