"""
Error Store - SQLite Persistence for Errors

Stores system errors in SQLite for:
- Long-term tracking
- Pattern analysis
- Error history
- Recovery tracking

Database Schema:
    errors table:
        - id (TEXT PRIMARY KEY)
        - timestamp (TEXT)
        - category (TEXT)
        - severity (TEXT)
        - exception_type (TEXT)
        - exception_message (TEXT)
        - traceback (TEXT)
        - component (TEXT)
        - operation (TEXT)
        - context (TEXT JSON)
        - recovery_strategy (TEXT)
        - recovery_attempted (INTEGER)
        - recovery_successful (INTEGER)
        - recovery_attempts (INTEGER)
        - max_recovery_attempts (INTEGER)
        - resolved (INTEGER)
        - resolved_at (TEXT)
        - notes (TEXT)

Usage:
    from src.core.error_store import get_error_store

    store = get_error_store()
    store.save_error(error)
    recent = store.get_recent_errors(limit=10)
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from threading import Lock

# Import only for type checking to avoid circular import
if TYPE_CHECKING:
    from src.core.error_manager import SystemError, ErrorCategory, ErrorSeverity
else:
    # Runtime: import late when needed
    SystemError = 'SystemError'
    ErrorCategory = 'ErrorCategory'
    ErrorSeverity = 'ErrorSeverity'

from src.monitoring.logger import get_logger
from src.core.config_manager import get_config

logger = get_logger("error_store")


class ErrorStore:
    """
    SQLite-based error persistence

    Thread-safe storage for system errors.
    Uses context managers for robust connection handling.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize error store

        Args:
            db_path: Path to SQLite database (uses config default if None)
        """
        if db_path is None:
            config = get_config()
            # Store errors in same database as main app
            db_path = Path(config.storage.database_path).parent / "errors.db"

        self.db_path = db_path
        self._lock = Lock()

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        logger.info(f"ErrorStore initialized at {self.db_path}")

    def _get_connection(self):
        """
        Get database connection with context manager support

        Returns:
            sqlite3.Connection with context manager

        Example:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
                conn.commit()
            # Connection automatically closed
        """
        return sqlite3.connect(str(self.db_path))

    def _init_database(self) -> None:
        """Initialize database schema"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create errors table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS errors (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        category TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        exception_type TEXT NOT NULL,
                        exception_message TEXT NOT NULL,
                        traceback TEXT NOT NULL,
                        component TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        context TEXT,
                        recovery_strategy TEXT NOT NULL,
                        recovery_attempted INTEGER DEFAULT 0,
                        recovery_successful INTEGER,
                        recovery_attempts INTEGER DEFAULT 0,
                        max_recovery_attempts INTEGER DEFAULT 3,
                        resolved INTEGER DEFAULT 0,
                        resolved_at TEXT,
                        notes TEXT DEFAULT ''
                    )
                """)

                # Create indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp DESC)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_errors_category ON errors(category)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_errors_severity ON errors(severity)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_errors_resolved ON errors(resolved)"
                )

                conn.commit()

                logger.debug("Database schema initialized")

    def save_error(self, error: 'SystemError') -> bool:
        """
        Save error to database

        Uses context manager for robust connection handling.

        Args:
            error: SystemError to save

        Returns:
            True if successful
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO errors (
                            id, timestamp, category, severity,
                            exception_type, exception_message, traceback,
                            component, operation, context,
                            recovery_strategy, recovery_attempted, recovery_successful,
                            recovery_attempts, max_recovery_attempts,
                            resolved, resolved_at, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            error.id,
                            error.timestamp.isoformat(),
                            error.category.value,
                            error.severity.value,
                            error.exception_type,
                            error.exception_message,
                            error.traceback,
                            error.component,
                            error.operation,
                            json.dumps(error.context),
                            error.recovery_strategy.value,
                            1 if error.recovery_attempted else 0,
                            1 if error.recovery_successful else (0 if error.recovery_successful is False else None),
                            error.recovery_attempts,
                            error.max_recovery_attempts,
                            1 if error.resolved else 0,
                            error.resolved_at.isoformat() if error.resolved_at else None,
                            error.notes,
                        ),
                    )

                    conn.commit()
                    # Connection automatically closed by context manager

                logger.debug(f"Saved error {error.id} to database")
                return True

        except Exception as e:
            logger.error(f"Failed to save error to database: {e}", exc_info=True)
            return False

    def update_error(self, error: 'SystemError') -> bool:
        """
        Update existing error in database

        Args:
            error: SystemError with updated fields

        Returns:
            True if successful
        """
        # Same as save (INSERT OR REPLACE)
        return self.save_error(error)

    def get_error(self, error_id: str) -> Optional['SystemError']:
        """
        Get error by ID

        Args:
            error_id: Error ID

        Returns:
            SystemError or None if not found
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute("SELECT * FROM errors WHERE id = ?", (error_id,))
                    row = cursor.fetchone()

                    if row:
                        return self._row_to_error(row)
                    return None

        except Exception as e:
            logger.error(f"Failed to get error {error_id}: {e}", exc_info=True)
            return None

    def get_recent_errors(
        self,
        limit: int = 10,
        category: Optional['ErrorCategory'] = None,
        severity: Optional['ErrorSeverity'] = None,
        resolved: Optional[bool] = None,
    ) -> List['SystemError']:
        """
        Get recent errors with optional filters

        Args:
            limit: Maximum number of errors to return
            category: Filter by category
            severity: Filter by severity
            resolved: Filter by resolved status

        Returns:
            List of SystemError objects (newest first)
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Build query
                    query = "SELECT * FROM errors WHERE 1=1"
                    params = []

                    if category:
                        query += " AND category = ?"
                        params.append(category.value)

                    if severity:
                        query += " AND severity = ?"
                        params.append(severity.value)

                    if resolved is not None:
                        query += " AND resolved = ?"
                        params.append(1 if resolved else 0)

                    query += " ORDER BY timestamp DESC LIMIT ?"
                    params.append(limit)

                    cursor.execute(query, params)
                    rows = cursor.fetchall()

                    return [self._row_to_error(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}", exc_info=True)
            return []

    def get_error_count(
        self,
        category: Optional['ErrorCategory'] = None,
        severity: Optional['ErrorSeverity'] = None,
        resolved: Optional[bool] = None,
    ) -> int:
        """
        Get count of errors with optional filters

        Args:
            category: Filter by category
            severity: Filter by severity
            resolved: Filter by resolved status

        Returns:
            Count of matching errors
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Build query
                    query = "SELECT COUNT(*) FROM errors WHERE 1=1"
                    params = []

                    if category:
                        query += " AND category = ?"
                        params.append(category.value)

                    if severity:
                        query += " AND severity = ?"
                        params.append(severity.value)

                    if resolved is not None:
                        query += " AND resolved = ?"
                        params.append(1 if resolved else 0)

                    cursor.execute(query, params)
                    count = cursor.fetchone()[0]

                    return count

        except Exception as e:
            logger.error(f"Failed to get error count: {e}", exc_info=True)
            return 0

    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics

        Returns:
            Dictionary with error stats
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    stats = {}

                    # Total errors
                    cursor.execute("SELECT COUNT(*) FROM errors")
                    stats["total_errors"] = cursor.fetchone()[0]

                    # Errors by category
                    cursor.execute("""
                        SELECT category, COUNT(*) as count
                        FROM errors
                        GROUP BY category
                        ORDER BY count DESC
                    """)
                    stats["by_category"] = {row[0]: row[1] for row in cursor.fetchall()}

                    # Errors by severity
                    cursor.execute("""
                        SELECT severity, COUNT(*) as count
                        FROM errors
                        GROUP BY severity
                        ORDER BY count DESC
                    """)
                    stats["by_severity"] = {row[0]: row[1] for row in cursor.fetchall()}

                    # Resolved vs unresolved
                    cursor.execute("SELECT COUNT(*) FROM errors WHERE resolved = 1")
                    stats["resolved"] = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM errors WHERE resolved = 0")
                    stats["unresolved"] = cursor.fetchone()[0]

                    # Recovery stats
                    cursor.execute("SELECT COUNT(*) FROM errors WHERE recovery_attempted = 1")
                    stats["recovery_attempted"] = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM errors WHERE recovery_successful = 1")
                    stats["recovery_successful"] = cursor.fetchone()[0]

                    return stats

        except Exception as e:
            logger.error(f"Failed to get error stats: {e}", exc_info=True)
            return {}

    def clear_resolved_errors(self, older_than_days: int = 30) -> int:
        """
        Clear resolved errors older than specified days

        Args:
            older_than_days: Clear errors resolved more than this many days ago

        Returns:
            Number of errors deleted
        """
        try:
            from datetime import datetime, timedelta

            cutoff_date = (
                datetime.now() - timedelta(days=older_than_days)
            ).isoformat()

            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        DELETE FROM errors
                        WHERE resolved = 1 AND resolved_at < ?
                    """,
                        (cutoff_date,),
                    )

                    deleted = cursor.rowcount
                    conn.commit()

                    logger.info(f"Cleared {deleted} resolved errors older than {older_than_days} days")
                    return deleted

        except Exception as e:
            logger.error(f"Failed to clear resolved errors: {e}", exc_info=True)
            return 0

    def _row_to_error(self, row: sqlite3.Row) -> 'SystemError':
        """
        Convert database row to SystemError

        Args:
            row: SQLite row

        Returns:
            SystemError object
        """
        from datetime import datetime
        # Import at runtime to avoid circular dependency
        from src.core.error_manager import (
            SystemError,
            ErrorCategory,
            ErrorSeverity,
            RecoveryStrategy
        )

        return SystemError(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            category=ErrorCategory(row["category"]),
            severity=ErrorSeverity(row["severity"]),
            exception_type=row["exception_type"],
            exception_message=row["exception_message"],
            traceback=row["traceback"],
            component=row["component"],
            operation=row["operation"],
            context=json.loads(row["context"]) if row["context"] else {},
            recovery_strategy=RecoveryStrategy(row["recovery_strategy"]),
            recovery_attempted=bool(row["recovery_attempted"]),
            recovery_successful=bool(row["recovery_successful"]) if row["recovery_successful"] is not None else None,
            recovery_attempts=row["recovery_attempts"],
            max_recovery_attempts=row["max_recovery_attempts"],
            resolved=bool(row["resolved"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            notes=row["notes"] or "",
        )


# Global error store instance (singleton)
_error_store: Optional[ErrorStore] = None
_error_store_lock = Lock()


def get_error_store() -> ErrorStore:
    """
    Get the global error store instance (singleton)

    Returns:
        The global ErrorStore instance
    """
    global _error_store

    if _error_store is None:
        with _error_store_lock:
            if _error_store is None:
                _error_store = ErrorStore()
                logger.info("Created global error store instance")

    return _error_store


def reset_error_store() -> None:
    """Reset the global error store (for tests)"""
    global _error_store
    _error_store = None
