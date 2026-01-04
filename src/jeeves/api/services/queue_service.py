"""
Queue Service

Async service wrapper for QueueStorage operations.
"""

from datetime import datetime
from typing import Any

from src.integrations.storage.queue_storage import QueueStorage, get_queue_storage
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("api.queue_service")


class QueueService:
    """Async service for queue operations"""

    def __init__(self, queue_storage: QueueStorage | None = None):
        """
        Initialize queue service

        Args:
            queue_storage: Optional QueueStorage instance (uses singleton if None)
        """
        self._storage = queue_storage or get_queue_storage()

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

        # Execute the IMAP action
        await self._execute_email_action(item, action, dest)

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
        # Lazy import to avoid circular imports
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
                    # Keep in inbox but unflag so it won't be reprocessed
                    # Actually for keep/defer, we should leave it flagged
                    logger.info(f"Keep/defer action for email {email_id} - no IMAP change")
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

        return self._storage.get_item(item_id)

    async def _unflag_email(self, item: dict[str, Any]) -> bool:
        """
        Remove the flag from an email to allow reprocessing

        Args:
            item: Queue item data

        Returns:
            True if successful
        """
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


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
