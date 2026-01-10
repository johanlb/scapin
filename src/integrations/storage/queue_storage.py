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
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from src.core.schemas import EmailAnalysis, EmailMetadata
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

        # File to track processed message_ids (Bug #60 fix)
        self._processed_ids_file = self.queue_dir / ".processed_message_ids.json"
        self._processed_message_ids: set[str] = self._load_processed_ids()

        # Thread lock for file operations
        self._lock = threading.Lock()

        logger.info("QueueStorage initialized", extra={"queue_dir": str(self.queue_dir)})

    def _load_processed_ids(self) -> set[str]:
        """Load processed message IDs from persistent storage"""
        if self._processed_ids_file.exists():
            try:
                with open(self._processed_ids_file) as f:
                    data = json.load(f)
                    return set(data.get("message_ids", []))
            except Exception as e:
                logger.warning(f"Failed to load processed IDs: {e}")
        return set()

    def _save_processed_ids(self) -> None:
        """Save processed message IDs to persistent storage"""
        try:
            with open(self._processed_ids_file, "w") as f:
                json.dump({"message_ids": list(self._processed_message_ids)}, f)
        except Exception as e:
            logger.warning(f"Failed to save processed IDs: {e}")

    def mark_message_processed(self, message_id: str) -> None:
        """Mark a message_id as processed (Bug #60 fix)"""
        if message_id:
            with self._lock:
                self._processed_message_ids.add(message_id)
                self._save_processed_ids()
            logger.debug(f"Marked message as processed: {message_id}")

    def is_email_known(self, message_id: str) -> bool:
        """
        Check if email with this message_id is already in queue or was processed.

        Bug #60 fix: Prevents re-adding emails that were already processed.

        Args:
            message_id: Email message ID

        Returns:
            True if email is known (in queue or processed), False otherwise
        """
        if not message_id:
            return False

        # Check if already processed
        if message_id in self._processed_message_ids:
            logger.debug(f"Email already processed: {message_id}")
            return True

        # Check if in current queue (any status)
        with self._lock:
            for file_path in self.queue_dir.glob("*.json"):
                if file_path.name.startswith("."):
                    continue
                try:
                    with open(file_path) as f:
                        item = json.load(f)
                        item_message_id = item.get("metadata", {}).get("message_id")
                        if item_message_id == message_id:
                            logger.debug(f"Email already in queue: {message_id}")
                            return True
                except Exception:
                    continue

        return False

    def save_item(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis,
        content_preview: str,
        account_id: Optional[str] = None,
        html_body: Optional[str] = None,
        full_text: Optional[str] = None,
    ) -> str | None:
        """
        Save email to review queue

        Args:
            metadata: Email metadata (from, subject, date, etc.)
            analysis: AI analysis results (action, confidence, reasoning)
            content_preview: Plain text preview (first 200 chars)
            account_id: Account identifier (for multi-account support)
            html_body: Full HTML body of the email (optional)
            full_text: Full plain text body of the email (optional)

        Returns:
            item_id: Unique identifier for queued item, or None if duplicate

        Example:
            item_id = storage.save_item(metadata, analysis, preview, "personal")
        """
        # Bug #60 fix: Check for duplicates before saving
        if metadata.message_id and self.is_email_known(metadata.message_id):
            logger.info(
                f"Skipping duplicate email: {metadata.subject[:50]}",
                extra={"message_id": metadata.message_id}
            )
            return None

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
                "attachments": [
                    {
                        "filename": att.filename,
                        "size_bytes": att.size_bytes,
                        "content_type": att.content_type,
                    }
                    for att in metadata.attachments
                ] if metadata.attachments else [],
                "folder": metadata.folder,
                "message_id": metadata.message_id,
            },
            "analysis": {
                "action": analysis.action.value,
                "confidence": analysis.confidence,
                "category": analysis.category.value if analysis.category else None,
                "reasoning": analysis.reasoning or "",
                "summary": analysis.summary,
                "options": [
                    {
                        "action": opt.action.value,
                        "destination": opt.destination,
                        "confidence": opt.confidence,
                        "reasoning": opt.reasoning,
                        "is_recommended": opt.is_recommended,
                    }
                    for opt in analysis.options
                ] if analysis.options else [],
            },
            "content": {
                "preview": content_preview[:200],  # Limit to 200 chars
                "html_body": html_body,  # Full HTML body for rendering
                "full_text": full_text,  # Full plain text body
            },
            "status": "pending",  # pending, approved, rejected, skipped
            "reviewed_at": None,
            "review_decision": None,
        }

        # Write to file (thread-safe)
        file_path = self.queue_dir / f"{item_id}.json"

        with self._lock, open(file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)

        logger.info(
            "Email queued for review",
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
    ) -> list[dict[str, Any]]:
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
                    with open(file_path, encoding="utf-8") as f:
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

    def get_item(self, item_id: str) -> Optional[dict[str, Any]]:
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
            with self._lock, open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load queue item {item_id}: {e}")
            return None

    def update_item(self, item_id: str, updates: dict[str, Any]) -> bool:
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
                with open(file_path, encoding="utf-8") as f:
                    item = json.load(f)

                # Apply updates
                item.update(updates)

                # Write back
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)

            logger.info("Queue item updated", extra={"item_id": item_id, "updates": list(updates.keys())})
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

            logger.info("Queue item removed", extra={"item_id": item_id})
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
                    with open(file_path, encoding="utf-8") as f:
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
            "Queue cleared",
            extra={
                "deleted_count": deleted_count,
                "account_id": account_id,
                "status": status,
            },
        )

        return deleted_count

    def get_stats(self) -> dict[str, Any]:
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
                    with open(file_path, encoding="utf-8") as f:
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
