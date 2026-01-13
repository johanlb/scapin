"""
Snooze Storage System

Tracks snoozed items with reminder times.

A snoozed item is temporarily hidden from the queue and
will reappear when the snooze period expires.

Architecture:
    - Each snooze is a separate JSON file
    - Filename: {snooze_id}.json
    - Directory: data/snoozes/
    - Thread-safe file operations
"""

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.utils import get_data_dir, now_utc

logger = get_logger("snooze_storage")


class SnoozeReason(str, Enum):
    """Predefined snooze reasons"""

    LATER_TODAY = "later_today"
    TOMORROW = "tomorrow"
    THIS_WEEKEND = "this_weekend"
    NEXT_WEEK = "next_week"
    CUSTOM = "custom"


@dataclass
class SnoozeRecord:
    """Record of a snoozed item"""

    snooze_id: str
    item_id: str  # ID of the snoozed item (queue item, email, etc.)
    item_type: str  # queue_item, email, teams_message, etc.

    snoozed_at: datetime
    snooze_until: datetime

    reason: SnoozeReason = SnoozeReason.CUSTOM
    reason_text: Optional[str] = None

    # Original item data (for restoration)
    original_data: dict[str, Any] = field(default_factory=dict)

    # Status
    is_active: bool = True
    woken_at: Optional[datetime] = None

    # Metadata
    account_id: Optional[str] = None


class SnoozeStorage:
    """
    JSON-based storage for snoozed items

    Tracks items that are temporarily hidden
    """

    def __init__(self, snoozes_dir: Optional[Path] = None):
        """
        Initialize snooze storage

        Args:
            snoozes_dir: Directory for snooze files (default: data/snoozes)
        """
        # Use absolute path to ensure correct location regardless of working directory
        self.snoozes_dir = Path(snoozes_dir) if snoozes_dir else get_data_dir() / "snoozes"
        self.snoozes_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        logger.info("SnoozeStorage initialized", extra={"snoozes_dir": str(self.snoozes_dir)})

    def snooze_item(
        self,
        item_id: str,
        item_type: str,
        snooze_until: datetime,
        reason: SnoozeReason = SnoozeReason.CUSTOM,
        reason_text: Optional[str] = None,
        original_data: Optional[dict[str, Any]] = None,
        account_id: Optional[str] = None,
    ) -> SnoozeRecord:
        """
        Snooze an item

        Args:
            item_id: ID of the item to snooze
            item_type: Type of item
            snooze_until: When the snooze expires
            reason: Why the item was snoozed
            reason_text: Custom reason text
            original_data: Original item data for restoration
            account_id: Account identifier

        Returns:
            SnoozeRecord: The created record
        """
        record = SnoozeRecord(
            snooze_id=str(uuid.uuid4()),
            item_id=item_id,
            item_type=item_type,
            snoozed_at=now_utc(),
            snooze_until=snooze_until,
            reason=reason,
            reason_text=reason_text,
            original_data=original_data or {},
            is_active=True,
            account_id=account_id,
        )

        self._save_record(record)

        logger.info(
            "Item snoozed",
            extra={
                "snooze_id": record.snooze_id,
                "item_id": item_id,
                "snooze_until": snooze_until.isoformat(),
                "reason": reason.value,
            },
        )

        return record

    def snooze_for_duration(
        self,
        item_id: str,
        item_type: str,
        hours: Optional[int] = None,
        days: Optional[int] = None,
        reason: SnoozeReason = SnoozeReason.CUSTOM,
        reason_text: Optional[str] = None,
        original_data: Optional[dict[str, Any]] = None,
        account_id: Optional[str] = None,
    ) -> SnoozeRecord:
        """
        Snooze an item for a duration

        Args:
            item_id: ID of the item to snooze
            item_type: Type of item
            hours: Hours to snooze (optional)
            days: Days to snooze (optional)
            reason: Why the item was snoozed
            reason_text: Custom reason text
            original_data: Original item data for restoration
            account_id: Account identifier

        Returns:
            SnoozeRecord: The created record
        """
        delta = timedelta(hours=hours or 0, days=days or 0)
        snooze_until = now_utc() + delta

        return self.snooze_item(
            item_id=item_id,
            item_type=item_type,
            snooze_until=snooze_until,
            reason=reason,
            reason_text=reason_text,
            original_data=original_data,
            account_id=account_id,
        )

    def _save_record(self, record: SnoozeRecord) -> None:
        """Save a snooze record to disk"""
        file_path = self.snoozes_dir / f"{record.snooze_id}.json"

        data = {
            "snooze_id": record.snooze_id,
            "item_id": record.item_id,
            "item_type": record.item_type,
            "snoozed_at": record.snoozed_at.isoformat(),
            "snooze_until": record.snooze_until.isoformat(),
            "reason": record.reason.value,
            "reason_text": record.reason_text,
            "original_data": record.original_data,
            "is_active": record.is_active,
            "woken_at": record.woken_at.isoformat() if record.woken_at else None,
            "account_id": record.account_id,
        }

        with self._lock, open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_record(self, file_path: Path) -> Optional[SnoozeRecord]:
        """Load a snooze record from disk"""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            return SnoozeRecord(
                snooze_id=data["snooze_id"],
                item_id=data["item_id"],
                item_type=data["item_type"],
                snoozed_at=datetime.fromisoformat(data["snoozed_at"]),
                snooze_until=datetime.fromisoformat(data["snooze_until"]),
                reason=SnoozeReason(data.get("reason", "custom")),
                reason_text=data.get("reason_text"),
                original_data=data.get("original_data", {}),
                is_active=data.get("is_active", True),
                woken_at=(
                    datetime.fromisoformat(data["woken_at"]) if data.get("woken_at") else None
                ),
                account_id=data.get("account_id"),
            )

        except Exception as e:
            logger.warning(f"Failed to load snooze {file_path.name}: {e}")
            return None

    def get_snooze(self, snooze_id: str) -> Optional[SnoozeRecord]:
        """
        Get a snooze record by ID

        Args:
            snooze_id: Snooze identifier

        Returns:
            SnoozeRecord or None if not found
        """
        file_path = self.snoozes_dir / f"{snooze_id}.json"

        if not file_path.exists():
            return None

        with self._lock:
            return self._load_record(file_path)

    def get_snooze_for_item(self, item_id: str) -> Optional[SnoozeRecord]:
        """
        Get active snooze for an item

        Args:
            item_id: Item identifier

        Returns:
            Active SnoozeRecord or None
        """
        with self._lock:
            for file_path in self.snoozes_dir.glob("*.json"):
                record = self._load_record(file_path)
                if record and record.item_id == item_id and record.is_active:
                    return record

        return None

    def get_snoozed_items(
        self,
        item_type: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> list[SnoozeRecord]:
        """
        Get all currently snoozed (active) items

        Args:
            item_type: Filter by item type
            account_id: Filter by account

        Returns:
            List of active snooze records
        """
        records = []

        with self._lock:
            for file_path in self.snoozes_dir.glob("*.json"):
                record = self._load_record(file_path)

                if not record or not record.is_active:
                    continue

                if item_type and record.item_type != item_type:
                    continue

                if account_id and record.account_id != account_id:
                    continue

                records.append(record)

        # Sort by snooze_until (soonest first)
        records.sort(key=lambda x: x.snooze_until)
        return records

    def get_expired_snoozes(self) -> list[SnoozeRecord]:
        """
        Get snoozes that have expired but are still active

        These items should be "woken up" and returned to their original state.

        Returns:
            List of expired snooze records
        """
        now = now_utc()
        expired = []

        with self._lock:
            for file_path in self.snoozes_dir.glob("*.json"):
                record = self._load_record(file_path)

                if not record or not record.is_active:
                    continue

                if record.snooze_until <= now:
                    expired.append(record)

        # Sort by snooze_until (oldest first)
        expired.sort(key=lambda x: x.snooze_until)
        return expired

    def unsnooze_item(self, item_id: str) -> Optional[SnoozeRecord]:
        """
        Manually unsnooze an item

        Args:
            item_id: Item identifier

        Returns:
            The unsnooze record or None if not found
        """
        record = self.get_snooze_for_item(item_id)

        if not record:
            logger.warning(f"No active snooze found for item {item_id}")
            return None

        record.is_active = False
        record.woken_at = now_utc()
        self._save_record(record)

        logger.info(
            "Item unsnoozed",
            extra={
                "snooze_id": record.snooze_id,
                "item_id": item_id,
            },
        )

        return record

    def wake_expired_snoozes(self) -> list[SnoozeRecord]:
        """
        Wake up all expired snoozes

        This should be called periodically to process expired snoozes.

        Returns:
            List of woken snooze records
        """
        expired = self.get_expired_snoozes()
        woken = []

        for record in expired:
            record.is_active = False
            record.woken_at = now_utc()
            self._save_record(record)
            woken.append(record)

            logger.info(
                "Snooze expired and woken",
                extra={
                    "snooze_id": record.snooze_id,
                    "item_id": record.item_id,
                },
            )

        return woken

    def delete_snooze(self, snooze_id: str) -> bool:
        """
        Delete a snooze record

        Args:
            snooze_id: Snooze identifier

        Returns:
            True if deleted, False if not found
        """
        file_path = self.snoozes_dir / f"{snooze_id}.json"

        if not file_path.exists():
            return False

        try:
            with self._lock:
                file_path.unlink()

            logger.info("Snooze deleted", extra={"snooze_id": snooze_id})
            return True

        except Exception as e:
            logger.error(f"Failed to delete snooze {snooze_id}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get snooze statistics

        Returns:
            Dictionary with stats
        """
        all_records = []

        with self._lock:
            for file_path in self.snoozes_dir.glob("*.json"):
                record = self._load_record(file_path)
                if record:
                    all_records.append(record)

        if not all_records:
            return {
                "total": 0,
                "active": 0,
                "expired_pending": 0,
                "by_reason": {},
                "by_item_type": {},
            }

        now = now_utc()
        active = [r for r in all_records if r.is_active]
        expired_pending = [r for r in active if r.snooze_until <= now]

        by_reason: dict[str, int] = {}
        by_item_type: dict[str, int] = {}

        for record in active:
            reason = record.reason.value
            item_type = record.item_type

            by_reason[reason] = by_reason.get(reason, 0) + 1
            by_item_type[item_type] = by_item_type.get(item_type, 0) + 1

        return {
            "total": len(all_records),
            "active": len(active),
            "expired_pending": len(expired_pending),
            "by_reason": by_reason,
            "by_item_type": by_item_type,
        }


# Singleton instance
_snooze_storage_instance: Optional[SnoozeStorage] = None
_snooze_storage_lock = threading.Lock()


def get_snooze_storage(snoozes_dir: Optional[Path] = None) -> SnoozeStorage:
    """
    Get global SnoozeStorage instance (thread-safe singleton)

    Args:
        snoozes_dir: Snoozes directory (only used on first call)

    Returns:
        SnoozeStorage instance
    """
    global _snooze_storage_instance

    if _snooze_storage_instance is None:
        with _snooze_storage_lock:
            # Double-check locking
            if _snooze_storage_instance is None:
                _snooze_storage_instance = SnoozeStorage(snoozes_dir=snoozes_dir)

    return _snooze_storage_instance


# Convenience functions for common snooze durations
def snooze_until_later_today(
    item_id: str,
    item_type: str,
    original_data: Optional[dict[str, Any]] = None,
    account_id: Optional[str] = None,
) -> SnoozeRecord:
    """Snooze until later today (3 hours)"""
    storage = get_snooze_storage()
    return storage.snooze_for_duration(
        item_id=item_id,
        item_type=item_type,
        hours=3,
        reason=SnoozeReason.LATER_TODAY,
        original_data=original_data,
        account_id=account_id,
    )


def snooze_until_tomorrow(
    item_id: str,
    item_type: str,
    original_data: Optional[dict[str, Any]] = None,
    account_id: Optional[str] = None,
) -> SnoozeRecord:
    """Snooze until tomorrow morning (next day at 9 AM)"""
    storage = get_snooze_storage()
    now = now_utc()
    tomorrow_9am = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)

    return storage.snooze_item(
        item_id=item_id,
        item_type=item_type,
        snooze_until=tomorrow_9am,
        reason=SnoozeReason.TOMORROW,
        original_data=original_data,
        account_id=account_id,
    )


def snooze_until_next_week(
    item_id: str,
    item_type: str,
    original_data: Optional[dict[str, Any]] = None,
    account_id: Optional[str] = None,
) -> SnoozeRecord:
    """Snooze until next Monday at 9 AM"""
    storage = get_snooze_storage()
    now = now_utc()

    # Find next Monday
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # If today is Monday, go to next Monday

    next_monday = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
        days=days_until_monday
    )

    return storage.snooze_item(
        item_id=item_id,
        item_type=item_type,
        snooze_until=next_monday,
        reason=SnoozeReason.NEXT_WEEK,
        original_data=original_data,
        account_id=account_id,
    )
