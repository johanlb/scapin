"""
Local SQLite tracker for processed emails

iCloud Mail (and some other IMAP servers) don't support KEYWORD/UNKEYWORD
searches for custom keywords. This module provides a local SQLite-based
tracking system to record which emails have been processed.

The IMAP flags are still added for visual feedback in email clients,
but the actual filtering is done locally.
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional

from src.monitoring.logger import get_logger
from src.utils import get_data_dir

logger = get_logger("processed_tracker")


class ProcessedEmailTracker:
    """
    Track processed emails using local SQLite database.

    This is necessary because iCloud IMAP doesn't support KEYWORD search
    even though it accepts and stores custom flags.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the tracker.

        Args:
            db_path: Path to SQLite database. Defaults to data/processed_emails.db
        """
        if db_path is None:
            # Use absolute path to ensure correct location regardless of working directory
            data_dir = get_data_dir()
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "processed_emails.db")

        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

        logger.info(
            "ProcessedEmailTracker initialized",
            extra={"db_path": db_path}
        )

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor with auto-commit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE NOT NULL,
                    account_id TEXT NOT NULL DEFAULT 'default',
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subject TEXT,
                    from_address TEXT
                )
            """)

            # Create index for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_id
                ON processed_emails(message_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_account_processed
                ON processed_emails(account_id, processed_at)
            """)

            logger.debug("Database schema initialized")

    def _normalize_message_id(self, message_id: str) -> str:
        """
        Normalize message_id for consistent deduplication.

        Removes angle brackets and converts to lowercase to handle
        variations like '<id@domain>' vs 'id@domain' or different casing.
        """
        if not message_id:
            return ""
        # Remove leading/trailing whitespace and angle brackets, lowercase
        return message_id.strip().strip("<>").lower()

    def is_processed(self, message_id: str) -> bool:
        """
        Check if an email has been processed.

        Args:
            message_id: RFC 822 Message-ID header value

        Returns:
            True if email was already processed
        """
        if not message_id:
            return False

        normalized = self._normalize_message_id(message_id)

        with self._get_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM processed_emails WHERE message_id = ?",
                (normalized,)
            )
            result = cursor.fetchone()
            return result is not None

    def mark_processed(
        self,
        message_id: str,
        account_id: str = "default",
        subject: Optional[str] = None,
        from_address: Optional[str] = None
    ) -> bool:
        """
        Mark an email as processed.

        Args:
            message_id: RFC 822 Message-ID header value
            account_id: Account identifier for multi-account support
            subject: Email subject (for debugging/logging)
            from_address: Sender address (for debugging/logging)

        Returns:
            True if marked successfully, False if already existed
        """
        if not message_id:
            logger.warning("Cannot mark email without message_id")
            return False

        normalized = self._normalize_message_id(message_id)

        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO processed_emails
                    (message_id, account_id, subject, from_address)
                    VALUES (?, ?, ?, ?)
                    """,
                    (normalized, account_id, subject, from_address)
                )

                if cursor.rowcount > 0:
                    logger.debug(
                        "Marked email as processed",
                        extra={
                            "message_id": message_id[:50],
                            "account_id": account_id
                        }
                    )
                    return True
                else:
                    # Already existed (INSERT OR IGNORE)
                    return False

        except Exception as e:
            logger.error(f"Failed to mark email as processed: {e}")
            return False

    def get_processed_count(self, account_id: Optional[str] = None) -> int:
        """
        Get count of processed emails.

        Args:
            account_id: Filter by account (None for all accounts)

        Returns:
            Number of processed emails
        """
        with self._get_cursor() as cursor:
            if account_id:
                cursor.execute(
                    "SELECT COUNT(*) FROM processed_emails WHERE account_id = ?",
                    (account_id,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM processed_emails")

            result = cursor.fetchone()
            return result[0] if result else 0

    def get_unprocessed_message_ids(
        self,
        all_message_ids: list[str],
        _account_id: str = "default"
    ) -> list[str]:
        """
        Filter a list of message IDs to return only unprocessed ones.

        Args:
            all_message_ids: List of message IDs to check
            account_id: Account identifier

        Returns:
            List of message IDs that haven't been processed
        """
        if not all_message_ids:
            return []

        # Normalize all message IDs for consistent comparison
        normalized_map = {self._normalize_message_id(mid): mid for mid in all_message_ids}
        normalized_ids = list(normalized_map.keys())

        with self._get_cursor() as cursor:
            # Use parameterized query with placeholders
            placeholders = ','.join('?' * len(normalized_ids))
            cursor.execute(
                f"SELECT message_id FROM processed_emails WHERE message_id IN ({placeholders})",
                normalized_ids
            )

            processed_set = {row[0] for row in cursor.fetchall()}

        # Return original message IDs for those not in processed set
        return [
            normalized_map[norm_id]
            for norm_id in normalized_ids
            if norm_id not in processed_set
        ]

    def clear_old_entries(self, days: int = 365) -> int:
        """
        Remove old entries to keep database size manageable.

        Args:
            days: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM processed_emails
                WHERE processed_at < datetime('now', ?)
                """,
                (f'-{days} days',)
            )
            count = cursor.rowcount

            if count > 0:
                logger.info(
                    f"Cleared {count} old processed email entries",
                    extra={"days": days}
                )

            return count


# Module-level singleton
_tracker: Optional[ProcessedEmailTracker] = None
_lock = threading.Lock()


def get_processed_tracker() -> ProcessedEmailTracker:
    """Get the singleton ProcessedEmailTracker instance."""
    global _tracker

    if _tracker is None:
        with _lock:
            if _tracker is None:
                _tracker = ProcessedEmailTracker()

    return _tracker
