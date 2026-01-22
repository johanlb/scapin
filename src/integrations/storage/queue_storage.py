"""
Queue Storage System (v2.4)

JSON-based storage for péripéties (emails queued for review/processing).

Architecture:
    - Each queued item is a separate JSON file
    - Filename: {item_id}.json
    - Directory: data/queue/
    - Thread-safe file operations

v2.4 Changes:
    - New data model separating state/resolution/snooze/error
    - state: queued, analyzing, awaiting_review, processed, error
    - resolution: auto_applied, manual_approved, manual_modified, manual_rejected, manual_skipped
    - snooze: orthogonal to state, tracks postponed items
    - timestamps: queued_at, analysis_started_at, analysis_completed_at, reviewed_at
    - Backwards compatible with legacy 'status' field

Usage:
    from src.integrations.storage.queue_storage import QueueStorage

    storage = QueueStorage()

    # Queue an email
    item_id = storage.save_item(metadata, analysis, content_preview)

    # Load items by state
    items = storage.load_queue_by_state(state="awaiting_review")

    # Load items (legacy API, still works)
    items = storage.load_queue(status="pending")

    # Remove from queue after processing
    storage.remove_item(item_id)
"""

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.core.models.peripetie import (
    PeripetieState,
    ResolutionType,
    ResolvedBy,
    migrate_legacy_status,
    state_to_tab,
)
from src.core.schemas import EmailAnalysis, EmailMetadata
from src.monitoring.logger import get_logger
from src.utils import get_data_dir, now_utc

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
        # Use absolute path to ensure correct location regardless of working directory
        self.queue_dir = Path(queue_dir) if queue_dir else get_data_dir() / "queue"
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
        multi_pass_data: Optional[dict[str, Any]] = None,
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
            multi_pass_data: Multi-pass analysis transparency data (v2.3)

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
        now = now_utc()

        # Build queue item with v2.4 structure
        item = {
            "id": item_id,
            "account_id": account_id,
            # v2.4: New state/resolution model
            "state": PeripetieState.AWAITING_REVIEW.value,  # Items go directly to review
            "resolution": None,  # Set when processed
            "snooze": None,  # Set when snoozed
            "error": None,  # Set on error
            # v2.4: Explicit timestamps
            "timestamps": {
                "queued_at": now.isoformat(),
                "analysis_started_at": now.isoformat(),  # Analysis already done
                "analysis_completed_at": now.isoformat(),
                "reviewed_at": None,
            },
            # Legacy field for backwards compatibility
            "queued_at": now.isoformat(),
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
                # v2.3: Multi-pass analysis transparency
                "multi_pass": multi_pass_data,
            },
            "content": {
                "preview": content_preview[:200],  # Limit to 200 chars
                "html_body": html_body,  # Full HTML body for rendering
                "full_text": full_text,  # Full plain text body
            },
            # Legacy fields for backwards compatibility
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

    def create_analyzing_item(
        self,
        metadata: EmailMetadata,
        content_preview: str,
        account_id: Optional[str] = None,
        html_body: Optional[str] = None,
        full_text: Optional[str] = None,
    ) -> str | None:
        """
        Create a queue item in ANALYZING state (before analysis is complete).

        This is used when fetching emails to show them in the "En cours" tab
        immediately, before the AI analysis completes.

        Args:
            metadata: Email metadata (from, subject, date, etc.)
            content_preview: Plain text preview (first 200 chars)
            account_id: Account identifier (for multi-account support)
            html_body: Full HTML body of the email (optional)
            full_text: Full plain text body of the email (optional)

        Returns:
            item_id: Unique identifier for queued item, or None if duplicate
        """
        # Bug #60 fix: Check for duplicates before saving
        if metadata.message_id and self.is_email_known(metadata.message_id):
            logger.info(
                f"Skipping duplicate email: {metadata.subject[:50]}",
                extra={"message_id": metadata.message_id}
            )
            return None

        item_id = str(uuid.uuid4())
        now = now_utc()

        # Build queue item with ANALYZING state
        item = {
            "id": item_id,
            "account_id": account_id,
            # v2.4: State is ANALYZING (not yet analyzed)
            "state": PeripetieState.ANALYZING.value,
            "resolution": None,
            "snooze": None,
            "error": None,
            # v2.4: Explicit timestamps
            "timestamps": {
                "queued_at": now.isoformat(),
                "analysis_started_at": now.isoformat(),
                "analysis_completed_at": None,  # Not yet complete
                "reviewed_at": None,
            },
            # Legacy field for backwards compatibility
            "queued_at": now.isoformat(),
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
            "analysis": None,  # Will be filled after analysis
            "content": {
                "preview": content_preview[:200],
                "html_body": html_body,
                "full_text": full_text,
            },
            # Legacy fields for backwards compatibility
            "status": "in_progress",  # Maps to ANALYZING in v2.4
            "reviewed_at": None,
            "review_decision": None,
        }

        # Write to file (thread-safe)
        file_path = self.queue_dir / f"{item_id}.json"

        with self._lock, open(file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)

        logger.info(
            "Email queued for analysis",
            extra={
                "item_id": item_id,
                "subject": metadata.subject,
                "state": "analyzing",
                "account_id": account_id,
            },
        )

        return item_id

    def complete_analysis(
        self,
        item_id: str,
        analysis: EmailAnalysis,
        multi_pass_data: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Update item with analysis results and transition to AWAITING_REVIEW.

        Called after AI analysis completes for an item created with create_analyzing_item().

        Args:
            item_id: Queue item ID
            analysis: AI analysis results
            multi_pass_data: Multi-pass analysis transparency data (v2.3)

        Returns:
            True if successful, False if item not found
        """
        file_path = self.queue_dir / f"{item_id}.json"

        with self._lock:
            if not file_path.exists():
                logger.warning(f"Item not found for analysis completion: {item_id}")
                return False

            try:
                with open(file_path, encoding="utf-8") as f:
                    item = json.load(f)

                now = now_utc()

                # Update analysis data
                item["analysis"] = {
                    "action": analysis.action.value,
                    "confidence": analysis.confidence,
                    "category": analysis.category.value if analysis.category else None,
                    "reasoning": analysis.reasoning or "",
                    "summary": analysis.summary,
                    "proposed_notes": [
                        {
                            "note_type": note.note_type.value if hasattr(note.note_type, 'value') else note.note_type,
                            "title": note.title,
                            "content_to_add": note.content_to_add,
                            "action": note.action.value if hasattr(note.action, 'value') else note.action,
                            "confidence": note.confidence,
                            "reasoning": note.reasoning,
                            "content_summary": getattr(note, 'content_summary', None),
                            "required": getattr(note, 'required', False),
                            "manually_approved": None,
                        }
                        for note in (analysis.proposed_notes or [])
                    ],
                    "proposed_tasks": [
                        {
                            "title": task.title,
                            "project": task.project,
                            "due_date": task.due_date.isoformat() if task.due_date else None,
                            "note": task.note,
                            "confidence": task.confidence,
                            "manually_approved": None,
                        }
                        for task in (analysis.proposed_tasks or [])
                    ],
                    "options": [
                        {"label": opt.label, "action": opt.action.value}
                        for opt in analysis.options
                    ] if analysis.options else [],
                    "multi_pass": multi_pass_data,
                }

                # Update state to AWAITING_REVIEW
                item["state"] = PeripetieState.AWAITING_REVIEW.value
                item["status"] = "pending"  # Legacy compatibility

                # Update timestamps
                if "timestamps" not in item:
                    item["timestamps"] = {}
                item["timestamps"]["analysis_completed_at"] = now.isoformat()

                # Write back
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)

                logger.info(
                    "Analysis completed for item",
                    extra={
                        "item_id": item_id,
                        "confidence": analysis.confidence,
                        "action": analysis.action.value,
                    },
                )

                return True

            except Exception as e:
                logger.error(f"Failed to complete analysis for {item_id}: {e}")
                return False

    def mark_analysis_error(
        self,
        item_id: str,
        error_message: str,
    ) -> bool:
        """
        Mark an item as failed during analysis.

        Args:
            item_id: Queue item ID
            error_message: Error description

        Returns:
            True if successful, False if item not found
        """
        file_path = self.queue_dir / f"{item_id}.json"

        with self._lock:
            if not file_path.exists():
                return False

            try:
                with open(file_path, encoding="utf-8") as f:
                    item = json.load(f)

                now = now_utc()

                # Update state to ERROR
                item["state"] = PeripetieState.ERROR.value
                item["error"] = {
                    "message": error_message,
                    "occurred_at": now.isoformat(),
                }

                # Write back
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)

                logger.warning(
                    "Analysis failed for item",
                    extra={"item_id": item_id, "error": error_message},
                )

                return True

            except Exception as e:
                logger.error(f"Failed to mark error for {item_id}: {e}")
                return False

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
        Get queue statistics (v2.4 enhanced)

        Returns:
            Dictionary with queue stats:
            {
                "total": int,
                "by_status": {"pending": 5, "approved": 2, ...},  # Legacy
                "by_state": {"awaiting_review": 18, "processed": 21, ...},  # v2.4
                "by_resolution": {"manual_approved": 10, "auto_applied": 5, ...},  # v2.4
                "by_tab": {"to_process": 18, "history": 21, "snoozed": 3, ...},  # v2.4
                "by_account": {"personal": 3, "work": 2, ...},
                "oldest_item": ISO datetime string,
                "newest_item": ISO datetime string,
                "snoozed_count": int,  # v2.4
                "error_count": int,  # v2.4
            }
        """
        all_items = []

        with self._lock:
            for file_path in self.queue_dir.glob("*.json"):
                if file_path.name.startswith("."):
                    continue
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
                "by_state": {},
                "by_resolution": {},
                "by_tab": {},
                "by_account": {},
                "oldest_item": None,
                "newest_item": None,
                "snoozed_count": 0,
                "error_count": 0,
            }

        # Count by legacy status
        by_status: dict[str, int] = {}
        for item in all_items:
            status = item.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        # v2.4: Count by state
        by_state: dict[str, int] = {}
        for item in all_items:
            state = self._get_item_state(item)
            by_state[state] = by_state.get(state, 0) + 1

        # v2.4: Count by resolution type
        by_resolution: dict[str, int] = {}
        for item in all_items:
            resolution = item.get("resolution")
            if resolution:
                res_type = resolution.get("type", "unknown")
                by_resolution[res_type] = by_resolution.get(res_type, 0) + 1

        # v2.4: Count by UI tab
        by_tab: dict[str, int] = {}
        snoozed_count = 0
        error_count = 0
        for item in all_items:
            state = self._get_item_state(item)
            has_snooze = item.get("snooze") is not None
            tab = state_to_tab(PeripetieState(state), has_snooze)
            by_tab[tab] = by_tab.get(tab, 0) + 1
            if has_snooze:
                snoozed_count += 1
            if state == PeripetieState.ERROR.value:
                error_count += 1

        # Count by account
        by_account: dict[str, int] = {}
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
            "by_state": by_state,
            "by_resolution": by_resolution,
            "by_tab": by_tab,
            "by_account": by_account,
            "oldest_item": oldest,
            "newest_item": newest,
            "snoozed_count": snoozed_count,
            "error_count": error_count,
        }

    # =========================================================================
    # v2.4 NEW METHODS
    # =========================================================================

    def _get_item_state(self, item: dict[str, Any]) -> str:
        """
        Get the state of an item, handling legacy format.

        Args:
            item: Queue item dictionary

        Returns:
            State value (from PeripetieState enum)
        """
        # Check for v2.4 state field first
        if "state" in item:
            return item["state"]

        # Fall back to legacy status mapping
        legacy_status = item.get("status", "pending")
        state, _ = migrate_legacy_status(legacy_status)
        return state.value

    def load_queue_by_state(
        self,
        state: Optional[str] = None,
        tab: Optional[str] = None,
        account_id: Optional[str] = None,
        include_snoozed: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Load queue items by state (v2.4 API).

        Args:
            state: Filter by state ('queued', 'analyzing', 'awaiting_review', 'processed', 'error')
            tab: Filter by UI tab ('to_process', 'in_progress', 'snoozed', 'history', 'errors')
            account_id: Filter by account (None = all accounts)
            include_snoozed: Whether to include snoozed items (default True)

        Returns:
            List of queue items (sorted by queued_at, oldest first)

        Example:
            # Load items awaiting review
            items = storage.load_queue_by_state(state="awaiting_review")

            # Load items for "À traiter" tab (excludes snoozed)
            items = storage.load_queue_by_state(tab="to_process", include_snoozed=False)
        """
        items = []

        with self._lock:
            for file_path in self.queue_dir.glob("*.json"):
                if file_path.name.startswith("."):
                    continue
                try:
                    with open(file_path, encoding="utf-8") as f:
                        item = json.load(f)

                    # Apply account filter
                    if account_id and item.get("account_id") != account_id:
                        continue

                    # Get item state
                    item_state = self._get_item_state(item)
                    has_snooze = item.get("snooze") is not None

                    # Filter out snoozed if requested
                    if not include_snoozed and has_snooze:
                        continue

                    # Apply state filter
                    if state and item_state != state:
                        continue

                    # Apply tab filter
                    if tab:
                        item_tab = state_to_tab(PeripetieState(item_state), has_snooze)
                        if item_tab != tab:
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
            extra={
                "count": len(items),
                "state": state,
                "tab": tab,
                "account_id": account_id,
            },
        )

        return items

    def set_state(
        self,
        item_id: str,
        new_state: PeripetieState,
        resolution: Optional[dict[str, Any]] = None,
        error: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Update item state (v2.4 API).

        Args:
            item_id: Item identifier
            new_state: New state to set
            resolution: Resolution details (required if state is PROCESSED)
            error: Error details (required if state is ERROR)

        Returns:
            True if successful, False if item not found

        Example:
            # Mark as processed with manual approval
            storage.set_state(item_id, PeripetieState.PROCESSED, resolution={
                "type": "manual_approved",
                "action_taken": "archive",
                "resolved_at": now_utc().isoformat(),
                "resolved_by": "user",
            })
        """
        updates: dict[str, Any] = {
            "state": new_state.value,
        }

        # Map to legacy status for backwards compatibility
        legacy_status_map = {
            PeripetieState.QUEUED: "pending",
            PeripetieState.ANALYZING: "pending",
            PeripetieState.AWAITING_REVIEW: "pending",
            PeripetieState.PROCESSED: "approved",  # Default, overridden below
            PeripetieState.ERROR: "pending",
        }
        updates["status"] = legacy_status_map.get(new_state, "pending")

        if resolution:
            updates["resolution"] = resolution
            # Set legacy status based on resolution type
            res_type = resolution.get("type", "")
            if res_type == ResolutionType.MANUAL_REJECTED.value:
                updates["status"] = "rejected"
            elif res_type == ResolutionType.MANUAL_SKIPPED.value:
                updates["status"] = "skipped"
            else:
                updates["status"] = "approved"

            # Update timestamps
            updates["reviewed_at"] = resolution.get("resolved_at")
            updates["review_decision"] = resolution.get("type")

        if error:
            updates["error"] = error

        return self.update_item(item_id, updates)

    def set_snooze(
        self,
        item_id: str,
        until: datetime,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Snooze an item (v2.4 API).

        Args:
            item_id: Item identifier
            until: When the snooze expires
            reason: Optional reason for snoozing

        Returns:
            True if successful, False if item not found
        """
        item = self.get_item(item_id)
        if not item:
            return False

        # Get existing snooze count
        existing_snooze = item.get("snooze")
        snooze_count = (existing_snooze.get("snooze_count", 0) if existing_snooze else 0) + 1

        updates = {
            "snooze": {
                "until": until.isoformat(),
                "created_at": now_utc().isoformat(),
                "reason": reason,
                "snooze_count": snooze_count,
            }
        }

        return self.update_item(item_id, updates)

    def clear_snooze(self, item_id: str) -> bool:
        """
        Clear snooze from an item (v2.4 API).

        Args:
            item_id: Item identifier

        Returns:
            True if successful, False if item not found
        """
        return self.update_item(item_id, {"snooze": None})

    def get_snoozed_items(self, account_id: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Get all snoozed items.

        Args:
            account_id: Filter by account (None = all accounts)

        Returns:
            List of snoozed items sorted by snooze expiry (soonest first)
        """
        items = []

        with self._lock:
            for file_path in self.queue_dir.glob("*.json"):
                if file_path.name.startswith("."):
                    continue
                try:
                    with open(file_path, encoding="utf-8") as f:
                        item = json.load(f)

                    # Filter: must have snooze
                    if not item.get("snooze"):
                        continue

                    # Apply account filter
                    if account_id and item.get("account_id") != account_id:
                        continue

                    items.append(item)

                except Exception:
                    continue

        # Sort by snooze expiry (soonest first)
        items.sort(key=lambda x: x.get("snooze", {}).get("until", ""))

        return items

    def get_expired_snoozes(self) -> list[dict[str, Any]]:
        """
        Get items with expired snoozes that should be "woken up".

        Returns:
            List of items with expired snoozes
        """
        now = now_utc().isoformat()
        items = []

        with self._lock:
            for file_path in self.queue_dir.glob("*.json"):
                if file_path.name.startswith("."):
                    continue
                try:
                    with open(file_path, encoding="utf-8") as f:
                        item = json.load(f)

                    snooze = item.get("snooze")
                    if snooze and snooze.get("until", "") <= now:
                        items.append(item)

                except Exception:
                    continue

        return items

    def wake_expired_snoozes(self) -> int:
        """
        Clear snoozes that have expired.

        Returns:
            Number of items woken up
        """
        expired = self.get_expired_snoozes()
        count = 0

        for item in expired:
            if self.clear_snooze(item["id"]):
                count += 1
                logger.info(
                    "Snooze expired and cleared",
                    extra={"item_id": item["id"]},
                )

        return count

    def migrate_item_to_v24(self, item_id: str) -> bool:
        """
        Migrate a single item to v2.4 format.

        Args:
            item_id: Item identifier

        Returns:
            True if migrated, False if not found or already migrated
        """
        item = self.get_item(item_id)
        if not item:
            return False

        # Already migrated if has 'state' field
        if "state" in item:
            return False

        # Migrate legacy status to state/resolution
        legacy_status = item.get("status", "pending")
        state, resolution_type = migrate_legacy_status(legacy_status)

        updates: dict[str, Any] = {
            "state": state.value,
            "snooze": None,
            "error": None,
            "timestamps": {
                "queued_at": item.get("queued_at"),
                "analysis_started_at": item.get("queued_at"),
                "analysis_completed_at": item.get("queued_at"),
                "reviewed_at": item.get("reviewed_at"),
            },
        }

        # Create resolution if item was processed
        if resolution_type:
            updates["resolution"] = {
                "type": resolution_type.value,
                "action_taken": item.get("analysis", {}).get("action", "unknown"),
                "resolved_at": item.get("reviewed_at") or item.get("queued_at"),
                "resolved_by": ResolvedBy.USER.value,
            }
        else:
            updates["resolution"] = None

        return self.update_item(item_id, updates)


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
