"""
Queue Service

Async service wrapper for QueueStorage operations.
"""

from datetime import datetime
from typing import Any

from src.integrations.storage.queue_storage import QueueStorage, get_queue_storage
from src.utils import now_utc


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
    ) -> dict[str, Any] | None:
        """
        Approve a queue item

        Args:
            item_id: Queue item ID
            modified_action: Override action (optional)
            modified_category: Override category (optional)

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

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

    async def modify_item(
        self,
        item_id: str,
        action: str,
        category: str | None = None,
        reasoning: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Modify a queue item's suggested action

        Args:
            item_id: Queue item ID
            action: New action
            category: New category (optional)
            reasoning: Reason for modification

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        updates: dict[str, Any] = {
            "status": "modified",
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
        Reject a queue item

        Args:
            item_id: Queue item ID
            reason: Reason for rejection

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

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
