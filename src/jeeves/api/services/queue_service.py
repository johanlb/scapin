"""
Queue Service

Async service wrapper for QueueStorage operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from src.integrations.storage.action_history import (
    ActionHistoryStorage,
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

logger = get_logger("api.queue_service")


class QueueService:
    """Async service for queue operations"""

    def __init__(
        self,
        queue_storage: QueueStorage | None = None,
        snooze_storage: SnoozeStorage | None = None,
        action_history: ActionHistoryStorage | None = None,
    ):
        """
        Initialize queue service

        Args:
            queue_storage: Optional QueueStorage instance (uses singleton if None)
            snooze_storage: Optional SnoozeStorage instance (uses singleton if None)
            action_history: Optional ActionHistoryStorage instance (uses singleton if None)
        """
        self._storage = queue_storage or get_queue_storage()
        self._snooze_storage = snooze_storage or get_snooze_storage()
        self._action_history = action_history or get_action_history()

    async def list_items(
        self,
        account_id: str | None = None,
        status: str = "pending",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List queue items with pagination

        Args:
            account_id: Filter by account
            status: Filter by status
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (items, total_count)
        """
        all_items = self._storage.load_queue(account_id=account_id, status=status)
        total = len(all_items)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        items = all_items[start:end]

        return items, total

    async def get_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Get single queue item

        Args:
            item_id: Queue item ID

        Returns:
            Queue item or None if not found
        """
        return self._storage.get_item(item_id)

    async def get_stats(self) -> dict[str, Any]:
        """
        Get queue statistics

        Returns:
            Dictionary with queue stats
        """
        return self._storage.get_stats()

    async def approve_item(
        self,
        item_id: str,
        modified_action: str | None = None,
        modified_category: str | None = None,
        destination: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Approve a queue item and execute the IMAP action

        Args:
            item_id: Queue item ID
            modified_action: Override action (optional)
            modified_category: Override category (optional)
            destination: Destination folder (optional, uses option's destination if not provided)

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Determine the action to execute
        action = modified_action or item.get("analysis", {}).get("action", "archive")

        # Use provided destination, or fall back to analysis destination
        dest = destination or item.get("analysis", {}).get("destination")

        # Get metadata for rollback
        metadata = item.get("metadata", {})
        original_folder = metadata.get("folder", "INBOX")
        email_id = metadata.get("id")

        # Execute the IMAP action
        imap_success = await self._execute_email_action(item, action, dest)

        # Bug #52 fix: Only mark as approved if IMAP action succeeded
        # If IMAP fails, keep item in pending so user can retry
        if not imap_success:
            logger.error(
                f"IMAP action failed for item {item_id}, keeping in pending",
                extra={"item_id": item_id, "action": action, "email_id": email_id},
            )
            # Return None to signal failure - frontend will show error
            return None

        if email_id:
            # Record action in history for undo capability
            self._action_history.create_action(
                action_type=ActionType.QUEUE_APPROVE,
                item_id=item_id,
                item_type="email",
                action_data={
                    "action": action,
                    "destination": dest,
                    "subject": metadata.get("subject"),
                },
                rollback_data={
                    "original_folder": original_folder,
                    "email_id": email_id,
                    "destination": dest,
                    "action": action,
                },
                account_id=item.get("account_id"),
            )

        updates: dict[str, Any] = {
            "status": "approved",
            "reviewed_at": now_utc().isoformat(),
            "review_decision": "approve",
        }

        if modified_action:
            updates["modified_action"] = modified_action
        if modified_category:
            updates["modified_category"] = modified_category

        success = self._storage.update_item(item_id, updates)
        if not success:
            return None

        # Bug #51: Log feedback for debugging and learning
        original_action = item.get("analysis", {}).get("action")
        original_confidence = item.get("analysis", {}).get("confidence")
        logger.info(
            "Feedback received: APPROVE",
            extra={
                "item_id": item_id,
                "feedback_type": "approve",
                "original_action": original_action,
                "executed_action": action,
                "action_modified": modified_action is not None,
                "original_confidence": original_confidence,
                "destination": dest,
                "subject": metadata.get("subject", "")[:50],
            }
        )

        # Bug #60 fix: Mark message_id as processed to prevent re-queueing
        message_id = metadata.get("message_id")
        if message_id:
            self._storage.mark_message_processed(message_id)

        return self._storage.get_item(item_id)

    async def _execute_email_action(
        self,
        item: dict[str, Any],
        action: str,
        destination: str | None = None,
    ) -> bool:
        """
        Execute IMAP action for a queue item

        Args:
            item: Queue item data
            action: Action to execute (archive, delete, task, etc.)
            destination: Destination folder (optional)

        Returns:
            True if action executed successfully
        """
        # Run blocking IMAP operations in a thread to not block event loop
        return await asyncio.to_thread(
            self._execute_email_action_sync, item, action, destination
        )

    def _execute_email_action_sync(
        self,
        item: dict[str, Any],
        action: str,
        destination: str | None,
    ) -> bool:
        """Synchronous IMAP action execution (runs in thread pool)"""
        from src.core.config_manager import get_config
        from src.integrations.email.imap_client import IMAPClient

        metadata = item.get("metadata", {})
        email_id = metadata.get("id")
        folder = metadata.get("folder", "INBOX")

        if not email_id:
            logger.warning(f"No email ID in queue item {item.get('id')}")
            return False

        config = get_config()
        imap_client = IMAPClient(config.email)

        try:
            with imap_client.connect():
                # Bug #60 fix: Add gray flag FIRST to mark as processed
                # This prevents re-fetching even if the subsequent action fails
                imap_client.add_flag(int(email_id), folder)

                if action in ("archive", "ARCHIVE"):
                    dest = destination or config.email.archive_folder or "Archive"
                    success = imap_client.move_email(
                        msg_id=int(email_id),
                        from_folder=folder,
                        to_folder=dest,
                    )
                    if success:
                        logger.info(f"Archived email {email_id} to {dest}")
                    return success

                elif action in ("delete", "DELETE"):
                    dest = destination or config.email.delete_folder or "Trash"
                    success = imap_client.move_email(
                        msg_id=int(email_id),
                        from_folder=folder,
                        to_folder=dest,
                    )
                    if success:
                        logger.info(f"Deleted email {email_id} to {dest}")
                    return success

                elif action in ("task", "TASK"):
                    # Task creation - move to archive after creating task
                    # TODO: Integrate with OmniFocus
                    dest = destination or config.email.archive_folder or "Archive"
                    success = imap_client.move_email(
                        msg_id=int(email_id),
                        from_folder=folder,
                        to_folder=dest,
                    )
                    if success:
                        logger.info(f"Archived email {email_id} after task action")
                    return success

                elif action in ("keep", "KEEP", "defer", "DEFER"):
                    # Bug #60 fix: Keep in inbox with gray flag so it won't be re-fetched
                    logger.info(f"Keep/defer action for email {email_id} - marked as processed")
                    return True

                else:
                    logger.warning(f"Unknown action: {action} for email {email_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to execute action {action} on email {email_id}: {e}")
            return False

    async def modify_item(
        self,
        item_id: str,
        action: str,
        category: str | None = None,
        reasoning: str | None = None,
        destination: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Modify a queue item's action and execute it

        Args:
            item_id: Queue item ID
            action: New action to execute
            category: New category (optional)
            reasoning: Reason for modification
            destination: Destination folder (optional)

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Execute the modified action
        await self._execute_email_action(item, action, destination)

        updates: dict[str, Any] = {
            "status": "approved",  # Modified items are approved with new action
            "reviewed_at": now_utc().isoformat(),
            "review_decision": "modify",
            "modified_action": action,
        }

        if category:
            updates["modified_category"] = category
        if reasoning:
            updates["modification_reason"] = reasoning

        success = self._storage.update_item(item_id, updates)
        if not success:
            return None

        # Bug #51: Log feedback for debugging and learning
        original_action = item.get("analysis", {}).get("action")
        original_confidence = item.get("analysis", {}).get("confidence")
        metadata = item.get("metadata", {})
        logger.info(
            "Feedback received: MODIFY",
            extra={
                "item_id": item_id,
                "feedback_type": "modify",
                "original_action": original_action,
                "modified_action": action,
                "original_confidence": original_confidence,
                "modification_reason": reasoning,
                "destination": destination,
                "subject": metadata.get("subject", "")[:50],
            }
        )

        # Bug #60 fix: Mark message_id as processed to prevent re-queueing
        message_id = metadata.get("message_id")
        if message_id:
            self._storage.mark_message_processed(message_id)

        return self._storage.get_item(item_id)

    async def reject_item(
        self,
        item_id: str,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Reject a queue item (no action on email, unflag for potential reprocessing)

        Args:
            item_id: Queue item ID
            reason: Reason for rejection

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Optionally unflag the email so it can be reprocessed later
        # This is useful if the user wants to reconsider the email
        await self._unflag_email(item)

        updates: dict[str, Any] = {
            "status": "rejected",
            "reviewed_at": now_utc().isoformat(),
            "review_decision": "reject",
        }

        if reason:
            updates["rejection_reason"] = reason

        success = self._storage.update_item(item_id, updates)
        if not success:
            return None

        # Bug #51: Log feedback for debugging and learning
        original_action = item.get("analysis", {}).get("action")
        original_confidence = item.get("analysis", {}).get("confidence")
        metadata = item.get("metadata", {})
        logger.info(
            "Feedback received: REJECT",
            extra={
                "item_id": item_id,
                "feedback_type": "reject",
                "original_action": original_action,
                "original_confidence": original_confidence,
                "rejection_reason": reason,
                "subject": metadata.get("subject", "")[:50],
            }
        )

        return self._storage.get_item(item_id)

    async def _unflag_email(self, item: dict[str, Any]) -> bool:
        """
        Remove the flag from an email to allow reprocessing

        Args:
            item: Queue item data

        Returns:
            True if successful
        """
        # Run blocking IMAP operations in a thread to not block event loop
        return await asyncio.to_thread(self._unflag_email_sync, item)

    def _unflag_email_sync(self, item: dict[str, Any]) -> bool:
        """Synchronous unflag operation (runs in thread pool)"""
        from src.core.config_manager import get_config
        from src.integrations.email.imap_client import IMAPClient

        metadata = item.get("metadata", {})
        email_id = metadata.get("id")
        folder = metadata.get("folder", "INBOX")

        if not email_id:
            return False

        config = get_config()
        imap_client = IMAPClient(config.email)

        try:
            with imap_client.connect():
                return imap_client.remove_flag(
                    msg_id=int(email_id),
                    folder=folder,
                )
        except Exception as e:
            logger.warning(f"Failed to unflag email {email_id}: {e}")
            return False

    async def delete_item(self, item_id: str) -> bool:
        """
        Delete a queue item

        Args:
            item_id: Queue item ID

        Returns:
            True if deleted, False if not found
        """
        return self._storage.remove_item(item_id)

    async def snooze_item(
        self,
        item_id: str,
        snooze_option: str,
        custom_hours: int | None = None,
        reason: str | None = None,
    ) -> SnoozeRecord | None:
        """
        Snooze a queue item

        Args:
            item_id: Queue item ID
            snooze_option: One of later_today, tomorrow, this_weekend, next_week, custom
            custom_hours: Hours to snooze (only for custom option)
            reason: Optional reason for snoozing

        Returns:
            SnoozeRecord or None if item not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Calculate snooze_until based on option
        now = now_utc()

        if snooze_option == "in_30_min":
            snooze_until = now + timedelta(minutes=30)
            snooze_reason = SnoozeReason.CUSTOM
        elif snooze_option == "in_2_hours" or snooze_option == "later_today":
            # 2 hours from now (Sprint 3 decision)
            snooze_until = now + timedelta(hours=2)
            snooze_reason = SnoozeReason.LATER_TODAY
        elif snooze_option == "tomorrow":
            # Tomorrow at 9 AM
            tomorrow = now + timedelta(days=1)
            snooze_until = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            snooze_reason = SnoozeReason.TOMORROW
        elif snooze_option == "this_weekend":
            # Saturday at 10 AM
            days_until_saturday = (5 - now.weekday()) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7  # If today is Saturday, go to next Saturday
            weekend = now + timedelta(days=days_until_saturday)
            snooze_until = weekend.replace(hour=10, minute=0, second=0, microsecond=0)
            snooze_reason = SnoozeReason.THIS_WEEKEND
        elif snooze_option == "next_week":
            # Next Monday at 9 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # If today is Monday, go to next Monday
            next_monday = now + timedelta(days=days_until_monday)
            snooze_until = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
            snooze_reason = SnoozeReason.NEXT_WEEK
        elif snooze_option == "custom" and custom_hours:
            snooze_until = now + timedelta(hours=custom_hours)
            snooze_reason = SnoozeReason.CUSTOM
        else:
            # Default to 3 hours
            snooze_until = now + timedelta(hours=3)
            snooze_reason = SnoozeReason.CUSTOM

        # Create snooze record
        record = self._snooze_storage.snooze_item(
            item_id=item_id,
            item_type="queue_item",
            snooze_until=snooze_until,
            reason=snooze_reason,
            reason_text=reason,
            original_data=item,
            account_id=item.get("account_id"),
        )

        # Update queue item status to snoozed
        self._storage.update_item(
            item_id,
            {
                "status": "snoozed",
                "snoozed_at": now.isoformat(),
                "snooze_until": snooze_until.isoformat(),
                "snooze_id": record.snooze_id,
            },
        )

        logger.info(
            f"Queue item snoozed: {item_id} until {snooze_until.isoformat()}",
            extra={"snooze_id": record.snooze_id, "snooze_option": snooze_option},
        )

        return record

    async def unsnooze_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Manually unsnooze a queue item

        Args:
            item_id: Queue item ID

        Returns:
            Updated queue item or None if not found
        """
        record = self._snooze_storage.unsnooze_item(item_id)
        if not record:
            return None

        # Update queue item status back to pending
        self._storage.update_item(
            item_id,
            {
                "status": "pending",
                "snoozed_at": None,
                "snooze_until": None,
                "snooze_id": None,
            },
        )

        return self._storage.get_item(item_id)

    async def undo_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Undo an approved queue item action

        Moves the email back to its original folder and marks the queue item as pending.

        Args:
            item_id: Queue item ID

        Returns:
            Updated queue item or None if not found or cannot undo
        """
        # Find the last action for this item
        action_record = self._action_history.get_last_action_for_item(item_id)
        if not action_record:
            logger.warning(f"No action found to undo for item {item_id}")
            return None

        if not self._action_history.can_undo(action_record.action_id):
            logger.warning(f"Action {action_record.action_id} cannot be undone")
            return None

        rollback_data = action_record.rollback_data
        original_folder = rollback_data.get("original_folder", "INBOX")
        email_id = rollback_data.get("email_id")
        destination = rollback_data.get("destination")

        if not email_id or not destination:
            logger.warning(f"Missing rollback data for action {action_record.action_id}")
            return None

        # Execute the undo IMAP action (move back to original folder)
        success = await self._undo_email_action(email_id, destination, original_folder)

        if success:
            # Mark the action as undone
            self._action_history.mark_undone(
                action_record.action_id,
                undo_result={"moved_to": original_folder},
            )

            # Update queue item status back to pending
            self._storage.update_item(
                item_id,
                {
                    "status": "pending",
                    "reviewed_at": None,
                    "review_decision": None,
                    "undone_at": now_utc().isoformat(),
                },
            )

            logger.info(
                f"Undid action for queue item {item_id}",
                extra={"action_id": action_record.action_id, "moved_to": original_folder},
            )

            return self._storage.get_item(item_id)

        return None

    async def _undo_email_action(
        self,
        email_id: str,
        from_folder: str,
        to_folder: str,
    ) -> bool:
        """
        Move an email back to its original folder

        Args:
            email_id: Email UID
            from_folder: Current folder where email is
            to_folder: Target folder to move email back to

        Returns:
            True if successful
        """
        return await asyncio.to_thread(
            self._undo_email_action_sync, email_id, from_folder, to_folder
        )

    def _undo_email_action_sync(
        self,
        email_id: str,
        from_folder: str,
        to_folder: str,
    ) -> bool:
        """Synchronous undo IMAP operation (runs in thread pool)"""
        from src.core.config_manager import get_config
        from src.integrations.email.imap_client import IMAPClient

        config = get_config()
        imap_client = IMAPClient(config.email)

        try:
            with imap_client.connect():
                success = imap_client.move_email(
                    msg_id=int(email_id),
                    from_folder=from_folder,
                    to_folder=to_folder,
                )
                if success:
                    logger.info(f"Undid email {email_id}: moved from {from_folder} to {to_folder}")
                return success

        except Exception as e:
            logger.error(f"Failed to undo email action for {email_id}: {e}")
            return False

    async def can_undo_item(self, item_id: str) -> bool:
        """
        Check if a queue item's action can be undone

        Args:
            item_id: Queue item ID

        Returns:
            True if the item has a completed action that can be undone
        """
        action_record = self._action_history.get_last_action_for_item(item_id)
        if not action_record:
            return False
        return self._action_history.can_undo(action_record.action_id)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
