"""
Notification Service

Manages notification CRUD operations with SQLite persistence.
Integrates with WebSocket for real-time delivery.

Features:
    - SQLite storage with 7-day retention
    - Automatic cleanup of expired notifications
    - Real-time push via WebSocket
    - User-specific notification streams
"""

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from src.core.config_manager import get_config
from src.jeeves.api.models.notifications import (
    MarkReadResponse,
    NotificationCreate,
    NotificationFilter,
    NotificationListResponse,
    NotificationPriority,
    NotificationResponse,
    NotificationStats,
    NotificationType,
)
from src.jeeves.api.websocket import ChannelType, get_channel_manager
from src.monitoring.logger import ScapinLogger

logger = ScapinLogger.get_logger(__name__)

# Default retention period
DEFAULT_RETENTION_DAYS = 7


class NotificationService:
    """
    Service for managing notifications

    Thread-safe SQLite operations with automatic cleanup.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        """
        Initialize notification service

        Args:
            db_path: Path to SQLite database. Uses config if not provided.
            retention_days: Days to keep notifications before cleanup.
        """
        if db_path is None:
            config = get_config()
            db_path = Path(config.storage.base_dir) / "notifications.db"

        self._db_path = db_path
        self._retention_days = retention_days
        self._lock = asyncio.Lock()

        # Ensure directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        logger.info(f"NotificationService initialized: {self._db_path}")

    def _init_db(self) -> None:
        """Initialize SQLite database schema"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'normal',
                    link TEXT,
                    metadata TEXT,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    read_at TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            # Indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_user_id
                ON notifications(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_created_at
                ON notifications(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_is_read
                ON notifications(user_id, is_read)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_expires_at
                ON notifications(expires_at)
            """)

            conn.commit()

    def _row_to_notification(self, row: sqlite3.Row) -> NotificationResponse:
        """Convert database row to NotificationResponse"""
        metadata = json.loads(row["metadata"]) if row["metadata"] else None
        read_at = datetime.fromisoformat(row["read_at"]) if row["read_at"] else None

        return NotificationResponse(
            id=row["id"],
            user_id=row["user_id"],
            type=NotificationType(row["type"]),
            title=row["title"],
            message=row["message"],
            priority=NotificationPriority(row["priority"]),
            link=row["link"],
            metadata=metadata,
            is_read=bool(row["is_read"]),
            read_at=read_at,
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
        )

    async def create(
        self,
        user_id: str,
        notification: NotificationCreate,
        push_realtime: bool = True,
    ) -> NotificationResponse:
        """
        Create a new notification

        Args:
            user_id: User to notify
            notification: Notification data
            push_realtime: Whether to push via WebSocket

        Returns:
            Created notification
        """
        now = datetime.now(timezone.utc)
        notification_id = str(uuid.uuid4())
        expires_at = now + timedelta(days=self._retention_days)

        metadata_json = json.dumps(notification.metadata) if notification.metadata else None

        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO notifications
                    (id, user_id, type, title, message, priority, link, metadata, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        notification_id,
                        user_id,
                        notification.type.value,
                        notification.title,
                        notification.message,
                        notification.priority.value,
                        notification.link,
                        metadata_json,
                        now.isoformat(),
                        expires_at.isoformat(),
                    ),
                )
                conn.commit()

        result = NotificationResponse(
            id=notification_id,
            user_id=user_id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            priority=notification.priority,
            link=notification.link,
            metadata=notification.metadata,
            is_read=False,
            created_at=now,
            expires_at=expires_at,
        )

        # Push via WebSocket
        if push_realtime:
            await self._push_notification(result)

        logger.debug(f"Created notification {notification_id} for {user_id}")
        return result

    async def _push_notification(self, notification: NotificationResponse) -> None:
        """Push notification via WebSocket"""
        try:
            manager = get_channel_manager()
            await manager.broadcast_to_user(
                notification.user_id,
                {
                    "type": "notification",
                    "data": notification.model_dump(mode="json"),
                },
                channel=ChannelType.NOTIFICATIONS,
            )
        except Exception as e:
            logger.warning(f"Failed to push notification: {e}")

    async def get(self, notification_id: str, user_id: str) -> Optional[NotificationResponse]:
        """
        Get a single notification

        Args:
            notification_id: Notification ID
            user_id: User ID (for access control)

        Returns:
            Notification if found and owned by user, None otherwise
        """
        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM notifications WHERE id = ? AND user_id = ?",
                    (notification_id, user_id),
                )
                row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_notification(row)

    async def list(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        filters: Optional[NotificationFilter] = None,
    ) -> NotificationListResponse:
        """
        List notifications for a user

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            filters: Optional filters

        Returns:
            Paginated notification list
        """
        offset = (page - 1) * page_size

        # Build query conditions
        conditions = ["user_id = ?", "expires_at > ?"]
        params: list = [user_id, datetime.now(timezone.utc).isoformat()]

        if filters:
            if filters.types:
                placeholders = ",".join("?" * len(filters.types))
                conditions.append(f"type IN ({placeholders})")
                params.extend(t.value for t in filters.types)

            if filters.priorities:
                placeholders = ",".join("?" * len(filters.priorities))
                conditions.append(f"priority IN ({placeholders})")
                params.extend(p.value for p in filters.priorities)

            if filters.is_read is not None:
                conditions.append("is_read = ?")
                params.append(1 if filters.is_read else 0)

            if filters.since:
                conditions.append("created_at >= ?")
                params.append(filters.since.isoformat())

        where_clause = " AND ".join(conditions)

        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get total count
                cursor = conn.execute(
                    f"SELECT COUNT(*) as count FROM notifications WHERE {where_clause}",
                    params,
                )
                total = cursor.fetchone()["count"]

                # Get unread count
                cursor = conn.execute(
                    f"SELECT COUNT(*) as count FROM notifications WHERE {where_clause} AND is_read = 0",
                    params,
                )
                unread_count = cursor.fetchone()["count"]

                # Get paginated results
                cursor = conn.execute(
                    f"""
                    SELECT * FROM notifications
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    params + [page_size, offset],
                )
                rows = cursor.fetchall()

        notifications = [self._row_to_notification(row) for row in rows]

        return NotificationListResponse(
            notifications=notifications,
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
            has_more=(offset + len(notifications)) < total,
        )

    async def mark_read(
        self,
        user_id: str,
        notification_ids: Optional[List[str]] = None,
        mark_all: bool = False,
    ) -> MarkReadResponse:
        """
        Mark notifications as read

        Args:
            user_id: User ID
            notification_ids: Specific IDs to mark, or None for mark_all
            mark_all: Mark all notifications as read

        Returns:
            Number of notifications marked
        """
        now = datetime.now(timezone.utc)

        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                if mark_all:
                    cursor = conn.execute(
                        """
                        UPDATE notifications
                        SET is_read = 1, read_at = ?
                        WHERE user_id = ? AND is_read = 0
                        """,
                        (now.isoformat(), user_id),
                    )
                elif notification_ids:
                    placeholders = ",".join("?" * len(notification_ids))
                    cursor = conn.execute(
                        f"""
                        UPDATE notifications
                        SET is_read = 1, read_at = ?
                        WHERE user_id = ? AND id IN ({placeholders}) AND is_read = 0
                        """,
                        [now.isoformat(), user_id] + notification_ids,
                    )
                else:
                    return MarkReadResponse(marked_count=0, timestamp=now)

                marked_count = cursor.rowcount
                conn.commit()

        logger.debug(f"Marked {marked_count} notifications as read for {user_id}")
        return MarkReadResponse(marked_count=marked_count, timestamp=now)

    async def delete(self, notification_id: str, user_id: str) -> bool:
        """
        Delete a notification

        Args:
            notification_id: Notification ID
            user_id: User ID (for access control)

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM notifications WHERE id = ? AND user_id = ?",
                    (notification_id, user_id),
                )
                conn.commit()
                deleted = cursor.rowcount > 0

        if deleted:
            logger.debug(f"Deleted notification {notification_id}")

        return deleted

    async def get_stats(self, user_id: str) -> NotificationStats:
        """
        Get notification statistics for a user

        Args:
            user_id: User ID

        Returns:
            Notification statistics
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Total and unread counts
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread
                    FROM notifications
                    WHERE user_id = ? AND expires_at > ?
                    """,
                    (user_id, now_iso),
                )
                row = cursor.fetchone()
                total = row["total"] or 0
                unread = row["unread"] or 0

                # By type
                cursor = conn.execute(
                    """
                    SELECT type, COUNT(*) as count
                    FROM notifications
                    WHERE user_id = ? AND expires_at > ?
                    GROUP BY type
                    """,
                    (user_id, now_iso),
                )
                by_type = {row["type"]: row["count"] for row in cursor.fetchall()}

                # By priority
                cursor = conn.execute(
                    """
                    SELECT priority, COUNT(*) as count
                    FROM notifications
                    WHERE user_id = ? AND expires_at > ?
                    GROUP BY priority
                    """,
                    (user_id, now_iso),
                )
                by_priority = {row["priority"]: row["count"] for row in cursor.fetchall()}

        return NotificationStats(
            total=total,
            unread=unread,
            by_type=by_type,
            by_priority=by_priority,
        )

    async def cleanup_expired(self) -> int:
        """
        Remove expired notifications

        Returns:
            Number of notifications removed
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM notifications WHERE expires_at <= ?",
                    (now_iso,),
                )
                conn.commit()
                deleted = cursor.rowcount

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired notifications")

        return deleted


# Global singleton
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get global NotificationService singleton"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def reset_notification_service() -> None:
    """Reset global NotificationService (for testing)"""
    global _notification_service
    _notification_service = None
