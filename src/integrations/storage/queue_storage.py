"""
Queue Storage System

JSON-based storage for emails queued for manual review.

Low-confidence emails (below threshold) are saved to disk
for later review and approval.

Architecture:
    - Each queued item is a separate JSON file
    - Filename: {item_id}.json
    - Directory: data/queue/
    - Thread-safe file operations

Usage:
    from src.integrations.storage.queue_storage import QueueStorage

    storage = QueueStorage()

    # Queue an email
    item_id = storage.save_item(metadata, analysis, content_preview)

    # Load all queued items
    items = storage.load_queue()

    # Remove from queue after review
    storage.remove_item(item_id)
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading

from src.core.schemas import EmailMetadata, EmailAnalysis
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("queue_storage")


class QueueStorage:
    """
    JSON-based storage for review queue

    Stores emails that need manual review (low-confidence decisions)
    """

    def __init__(self, queue_dir: Optional[Path] = None):
        """
        Initialize queue storage

        Args:
            queue_dir: Directory for queue files (default: data/queue)
        """
        self.queue_dir = Path(queue_dir) if queue_dir else Path("data/queue")
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        logger.info(f"QueueStorage initialized", extra={"queue_dir": str(self.queue_dir)})

    def save_item(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis,
        content_preview: str,
        account_id: Optional[str] = None,
    ) -> str:
        """
        Save email to review queue

        Args:
            metadata: Email metadata (from, subject, date, etc.)
            analysis: AI analysis results (action, confidence, reasoning)
            content_preview: Plain text preview (first 200 chars)
            account_id: Account identifier (for multi-account support)

        Returns:
            item_id: Unique identifier for queued item

        Example:
            item_id = storage.save_item(metadata, analysis, preview, "personal")
        """
        item_id = str(uuid.uuid4())

        # Build queue item
        item = {
            "id": item_id,
            "account_id": account_id,
            "queued_at": now_utc().isoformat(),
            "metadata": {
                "id": metadata.id,
                "subject": metadata.subject,
                "from_address": metadata.from_address,
                "from_name": metadata.from_name or "",
                "date": metadata.date.isoformat() if metadata.date else None,
                "has_attachments": metadata.has_attachments,
                "folder": metadata.folder,
                "message_id": metadata.message_id,
            },
            "analysis": {
                "action": analysis.action.value,
                "confidence": analysis.confidence,
                "category": analysis.category.value if analysis.category else None,
                "reasoning": analysis.reasoning or "",
            },
            "content": {
                "preview": content_preview[:200],  # Limit to 200 chars
            },
            "status": "pending",  # pending, approved, rejected, skipped
            "reviewed_at": None,
            "review_decision": None,
        }

        # Write to file (thread-safe)
        file_path = self.queue_dir / f"{item_id}.json"

        with self._lock:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(item, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Email queued for review",
            extra={
                "item_id": item_id,
                "subject": metadata.subject,
                "confidence": analysis.confidence,
                "account_id": account_id,
            },
        )

        return item_id

    def load_queue(
        self, account_id: Optional[str] = None, status: str = "pending"
    ) -> List[Dict[str, Any]]:
        """
        Load all queued items

        Args:
            account_id: Filter by account (None = all accounts)
            status: Filter by status ('pending', 'approved', 'rejected', etc.)

        Returns:
            List of queue items (sorted by queued_at, oldest first)

        Example:
            # Load all pending items
            items = storage.load_queue()

            # Load pending items for specific account
            items = storage.load_queue(account_id="personal")
        """
        items = []

        with self._lock:
            for file_path in self.queue_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        item = json.load(f)

                    # Apply filters
                    if account_id and item.get("account_id") != account_id:
                        continue

                    if status and item.get("status") != status:
                        continue

                    items.append(item)

                except Exception as e:
                    logger.warning(
                        f"Failed to load queue item {file_path.name}: {e}",
                        extra={"file": str(file_path)},
                    )

        # Sort by queued_at (oldest first)
        items.sort(key=lambda x: x.get("queued_at", ""))

        logger.debug(
            f"Loaded {len(items)} queue items",
            extra={"count": len(items), "account_id": account_id, "status": status},
        )

        return items

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single queue item by ID

        Args:
            item_id: Item identifier

        Returns:
            Queue item or None if not found
        """
        file_path = self.queue_dir / f"{item_id}.json"

        if not file_path.exists():
            return None

        try:
            with self._lock:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load queue item {item_id}: {e}")
            return None

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update queue item

        Args:
            item_id: Item identifier
            updates: Dictionary of fields to update

        Returns:
            True if successful, False if item not found

        Example:
            # Mark as reviewed
            storage.update_item(item_id, {
                "status": "approved",
                "reviewed_at": datetime.now().isoformat(),
                "review_decision": "approve"
            })
        """
        file_path = self.queue_dir / f"{item_id}.json"

        if not file_path.exists():
            logger.warning(f"Queue item not found: {item_id}")
            return False

        try:
            with self._lock:
                # Load existing item
                with open(file_path, "r", encoding="utf-8") as f:
                    item = json.load(f)

                # Apply updates
                item.update(updates)

                # Write back
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)

            logger.info(f"Queue item updated", extra={"item_id": item_id, "updates": list(updates.keys())})
            return True

        except Exception as e:
            logger.error(f"Failed to update queue item {item_id}: {e}", exc_info=True)
            return False

    def remove_item(self, item_id: str) -> bool:
        """
        Remove item from queue

        Args:
            item_id: Item identifier

        Returns:
            True if removed, False if not found

        Example:
            # After approving and executing
            storage.remove_item(item_id)
        """
        file_path = self.queue_dir / f"{item_id}.json"

        if not file_path.exists():
            logger.warning(f"Queue item not found: {item_id}")
            return False

        try:
            with self._lock:
                file_path.unlink()

            logger.info(f"Queue item removed", extra={"item_id": item_id})
            return True

        except Exception as e:
            logger.error(f"Failed to remove queue item {item_id}: {e}", exc_info=True)
            return False

    def get_queue_size(self, account_id: Optional[str] = None, status: str = "pending") -> int:
        """
        Get number of items in queue

        Args:
            account_id: Filter by account (None = all accounts)
            status: Filter by status

        Returns:
            Number of items matching filters
        """
        items = self.load_queue(account_id=account_id, status=status)
        return len(items)

    def clear_queue(self, account_id: Optional[str] = None, status: Optional[str] = None) -> int:
        """
        Clear queue (delete all matching items)

        Args:
            account_id: Filter by account (None = all accounts)
            status: Filter by status (None = all statuses)

        Returns:
            Number of items deleted

        Warning:
            This is a destructive operation. Use with caution.
        """
        deleted_count = 0

        with self._lock:
            for file_path in list(self.queue_dir.glob("*.json")):
                try:
                    # Read item to check filters
                    with open(file_path, "r", encoding="utf-8") as f:
                        item = json.load(f)

                    # Apply filters
                    if account_id and item.get("account_id") != account_id:
                        continue

                    if status is not None and item.get("status") != status:
                        continue

                    # Delete matching item
                    file_path.unlink()
                    deleted_count += 1

                except Exception as e:
                    logger.warning(f"Failed to process {file_path.name}: {e}")
                    continue

        logger.warning(
            f"Queue cleared",
            extra={
                "deleted_count": deleted_count,
                "account_id": account_id,
                "status": status,
            },
        )

        return deleted_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics

        Returns:
            Dictionary with queue stats:
            {
                "total": int,
                "by_status": {"pending": 5, "approved": 2, ...},
                "by_account": {"personal": 3, "work": 2, ...},
                "oldest_item": ISO datetime string,
                "newest_item": ISO datetime string
            }
        """
        all_items = []

        with self._lock:
            for file_path in self.queue_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        item = json.load(f)
                    all_items.append(item)
                except Exception:
                    pass

        if not all_items:
            return {
                "total": 0,
                "by_status": {},
                "by_account": {},
                "oldest_item": None,
                "newest_item": None,
            }

        # Count by status
        by_status = {}
        for item in all_items:
            status = item.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        # Count by account
        by_account = {}
        for item in all_items:
            account = item.get("account_id") or "unknown"
            by_account[account] = by_account.get(account, 0) + 1

        # Find oldest/newest
        sorted_items = sorted(all_items, key=lambda x: x.get("queued_at", ""))
        oldest = sorted_items[0].get("queued_at") if sorted_items else None
        newest = sorted_items[-1].get("queued_at") if sorted_items else None

        return {
            "total": len(all_items),
            "by_status": by_status,
            "by_account": by_account,
            "oldest_item": oldest,
            "newest_item": newest,
        }


# Singleton instance
_queue_storage_instance: Optional[QueueStorage] = None
_queue_storage_lock = threading.Lock()


def get_queue_storage(queue_dir: Optional[Path] = None) -> QueueStorage:
    """
    Get global QueueStorage instance (thread-safe singleton)

    Args:
        queue_dir: Queue directory (only used on first call)

    Returns:
        QueueStorage instance
    """
    global _queue_storage_instance

    if _queue_storage_instance is None:
        with _queue_storage_lock:
            # Double-check locking
            if _queue_storage_instance is None:
                _queue_storage_instance = QueueStorage(queue_dir=queue_dir)

    return _queue_storage_instance
