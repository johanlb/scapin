"""
WhatsApp adapter for CrossSourceEngine.

Provides search functionality for WhatsApp message history via SQLite database.
WhatsApp stores messages in ~/Library/Messages/ChatStorage.sqlite on macOS
when using WhatsApp Desktop with local backup.

Note: This adapter requires WhatsApp Desktop to be installed and configured
with local message storage enabled, or access to a WhatsApp backup database.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

logger = logging.getLogger("scapin.cross_source.whatsapp")

# Security constants
MAX_QUERY_LENGTH = 500
MAX_CONTACT_LENGTH = 100

# Default WhatsApp database paths
WHATSAPP_DB_PATHS = [
    # WhatsApp Desktop on macOS
    Path.home() / "Library" / "Application Support" / "WhatsApp" / "IndexedDB",
    # Alternative path for some versions
    Path.home() / "Library" / "Group Containers" / "group.net.whatsapp.WhatsApp.shared" / "Message" / "Message" / "Media",
    # Custom path can be set via config
]


class WhatsAppAdapter(BaseAdapter):
    """
    WhatsApp adapter for cross-source queries.

    Searches WhatsApp message history stored in local SQLite database.
    This adapter uses a read-only connection to ensure message safety.

    Note: WhatsApp uses a complex database schema. This adapter supports
    common database formats but may need adjustment for different versions.
    """

    _source_name = "whatsapp"

    @staticmethod
    def _escape_like_pattern(value: str) -> str:
        """
        Escape special characters for SQL LIKE patterns.

        Prevents SQL injection by escaping %, _, and backslash characters.

        Args:
            value: Raw search value

        Returns:
            Escaped value safe for LIKE clause
        """
        # Escape backslash first, then other special chars
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _validate_query(self, query: str) -> str:
        """Validate and sanitize search query."""
        if not query or not isinstance(query, str):
            return ""
        # Truncate to max length
        return query[:MAX_QUERY_LENGTH].strip()

    def _validate_contact(self, contact: str | None) -> str | None:
        """Validate and sanitize contact filter."""
        if not contact or not isinstance(contact, str):
            return None
        return contact[:MAX_CONTACT_LENGTH].strip()

    def __init__(
        self,
        db_path: Path | str | None = None,
        days_back: int = 90,
    ) -> None:
        """
        Initialize the WhatsApp adapter.

        Args:
            db_path: Path to WhatsApp SQLite database (auto-detected if None)
            days_back: How many days back to search (default: 90)
        """
        self._db_path = Path(db_path) if db_path else None
        self._days_back = days_back
        self._connection: sqlite3.Connection | None = None
        self._available: bool | None = None
        self._cached_schema: str | None = None  # Cache detected schema type
        self._lock = threading.RLock()  # Thread-safety for connection management

    @property
    def is_available(self) -> bool:
        """Check if WhatsApp database is accessible."""
        with self._lock:
            if self._available is not None:
                return self._available

            # Try to find and connect to database
            db_path = self._find_database()
            if db_path is None:
                self._available = False
                return False

            try:
                # Test connection with read-only mode
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                conn.execute("SELECT 1")
                conn.close()
                self._db_path = db_path
                self._available = True
                logger.info("WhatsApp database found at %s", db_path)
                return True
            except (sqlite3.Error, OSError) as e:
                logger.debug("WhatsApp database not accessible: %s", e)
                self._available = False
                return False

    def _find_database(self) -> Path | None:
        """
        Find WhatsApp database file.

        Returns:
            Path to database file or None if not found
        """
        if self._db_path and self._db_path.exists():
            return self._db_path

        # Check common paths
        for base_path in WHATSAPP_DB_PATHS:
            if not base_path.exists():
                continue

            # Look for SQLite files
            for db_file in base_path.rglob("*.sqlite"):
                if self._is_whatsapp_db(db_file):
                    return db_file

            for db_file in base_path.rglob("*.db"):
                if self._is_whatsapp_db(db_file):
                    return db_file

        return None

    def _is_whatsapp_db(self, path: Path) -> bool:
        """
        Check if a file is a valid WhatsApp database.

        Args:
            path: Path to check

        Returns:
            True if valid WhatsApp database
        """
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            cursor = conn.cursor()
            # Check for WhatsApp-specific tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            # Check for known WhatsApp table names
            whatsapp_tables = {"ZWAMESSAGE", "ZWACHATSESSION", "messages", "chat"}
            return bool(tables & whatsapp_tables)
        except sqlite3.Error:
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection (thread-safe)."""
        with self._lock:
            if self._connection is None:
                if self._db_path is None:
                    raise RuntimeError("WhatsApp database not found")
                self._connection = sqlite3.connect(
                    f"file:{self._db_path}?mode=ro",
                    uri=True,
                    timeout=5.0,
                )
                self._connection.row_factory = sqlite3.Row
            return self._connection

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search WhatsApp messages for relevant content.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context with additional filters
                    - since: datetime to filter messages from
                    - contact: str to filter by contact name

        Returns:
            List of SourceItem objects representing matching messages
        """
        if not self.is_available:
            logger.warning("WhatsApp adapter not available, skipping search")
            return []

        try:
            # Get filter options from context
            since = None
            contact_filter = None

            if context:
                since = context.get("since")
                contact_filter = context.get("contact")

            # Calculate since date if not provided
            if since is None:
                since = datetime.now(timezone.utc) - timedelta(days=self._days_back)

            # Search messages
            messages = self._search_messages(
                query=query,
                since=since,
                contact=contact_filter,
                limit=max_results,
            )

            # Convert to SourceItems
            results = [
                self._message_to_source_item(msg, query)
                for msg in messages
            ]

            logger.debug(
                "WhatsApp search found %d messages matching '%s'",
                len(results),
                query[:50],
            )

            return results

        except Exception as e:
            logger.error("WhatsApp search failed: %s", e)
            return []

    def _search_messages(
        self,
        query: str,
        since: datetime,
        contact: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Search messages in the database.

        Args:
            query: Search query
            since: Filter messages after this date
            contact: Optional contact name filter
            limit: Maximum results

        Returns:
            List of message dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Use cached schema or detect (avoid repeated detection)
        if self._cached_schema is None:
            self._cached_schema = self._detect_schema(cursor)
        schema = self._cached_schema

        if schema == "ios_backup":
            return self._search_ios_backup(cursor, query, since, contact, limit)
        elif schema == "android":
            return self._search_android(cursor, query, since, contact, limit)
        else:
            logger.warning("Unknown WhatsApp database schema")
            return []

    def _detect_schema(self, cursor: sqlite3.Cursor) -> str:
        """
        Detect the database schema type.

        Returns:
            Schema type: 'ios_backup', 'android', or 'unknown'
        """
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        if "ZWAMESSAGE" in tables:
            return "ios_backup"
        elif "messages" in tables and "jid" in tables:
            return "android"
        else:
            return "unknown"

    def _search_ios_backup(
        self,
        cursor: sqlite3.Cursor,
        query: str,
        since: datetime,
        contact: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search iOS backup database schema."""
        # iOS WhatsApp uses Core Data with Z prefix
        # ZWAMESSAGE table contains messages
        # ZWACHATSESSION contains chat info

        # Convert datetime to Core Data timestamp (seconds since 2001-01-01)
        cd_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        since_ts = (since - cd_epoch).total_seconds()

        # Validate and escape inputs to prevent SQL injection
        safe_query = self._validate_query(query)
        if not safe_query:
            return []
        escaped_query = self._escape_like_pattern(safe_query)

        sql = """
            SELECT
                m.ZTEXT as text,
                m.ZMESSAGEDATE as timestamp,
                m.ZISFROMME as is_from_me,
                c.ZCONTACTJID as contact_jid,
                c.ZPARTNERNAME as contact_name
            FROM ZWAMESSAGE m
            LEFT JOIN ZWACHATSESSION c ON m.ZCHATSESSION = c.Z_PK
            WHERE m.ZTEXT LIKE ? ESCAPE '\\'
            AND m.ZMESSAGEDATE > ?
        """
        params: list[Any] = [f"%{escaped_query}%", since_ts]

        if contact:
            safe_contact = self._validate_contact(contact)
            if safe_contact:
                escaped_contact = self._escape_like_pattern(safe_contact)
                sql += " AND (c.ZPARTNERNAME LIKE ? ESCAPE '\\' OR c.ZCONTACTJID LIKE ? ESCAPE '\\')"
                params.extend([f"%{escaped_contact}%", f"%{escaped_contact}%"])

        sql += " ORDER BY m.ZMESSAGEDATE DESC LIMIT ?"
        params.append(limit)

        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                # Convert Core Data timestamp back to datetime
                ts = row["timestamp"]
                msg_time = cd_epoch + timedelta(seconds=ts) if ts else datetime.now(timezone.utc)

                messages.append({
                    "text": row["text"] or "",
                    "timestamp": msg_time,
                    "is_from_me": bool(row["is_from_me"]),
                    "contact_jid": row["contact_jid"] or "",
                    "contact_name": row["contact_name"] or "Unknown",
                })

            return messages
        except sqlite3.Error as e:
            logger.error("iOS backup search failed: %s", e)
            return []

    def _search_android(
        self,
        cursor: sqlite3.Cursor,
        query: str,
        since: datetime,
        contact: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search Android database schema."""
        # Android WhatsApp uses different table structure
        since_ts = int(since.timestamp() * 1000)  # Android uses milliseconds

        # Validate and escape inputs to prevent SQL injection
        safe_query = self._validate_query(query)
        if not safe_query:
            return []
        escaped_query = self._escape_like_pattern(safe_query)

        sql = """
            SELECT
                m.data as text,
                m.timestamp as timestamp,
                m.key_from_me as is_from_me,
                m.key_remote_jid as contact_jid,
                j.display_name as contact_name
            FROM messages m
            LEFT JOIN jid j ON m.key_remote_jid = j.raw_string
            WHERE m.data LIKE ? ESCAPE '\\'
            AND m.timestamp > ?
        """
        params: list[Any] = [f"%{escaped_query}%", since_ts]

        if contact:
            safe_contact = self._validate_contact(contact)
            if safe_contact:
                escaped_contact = self._escape_like_pattern(safe_contact)
                sql += " AND (j.display_name LIKE ? ESCAPE '\\' OR m.key_remote_jid LIKE ? ESCAPE '\\')"
                params.extend([f"%{escaped_contact}%", f"%{escaped_contact}%"])

        sql += " ORDER BY m.timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                ts = row["timestamp"]
                msg_time = datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else datetime.now(timezone.utc)

                messages.append({
                    "text": row["text"] or "",
                    "timestamp": msg_time,
                    "is_from_me": bool(row["is_from_me"]),
                    "contact_jid": row["contact_jid"] or "",
                    "contact_name": row["contact_name"] or "Unknown",
                })

            return messages
        except sqlite3.Error as e:
            logger.error("Android search failed: %s", e)
            return []

    def _message_to_source_item(
        self,
        message: dict[str, Any],
        query: str,
    ) -> SourceItem:
        """
        Convert a message dict to SourceItem.

        Args:
            message: Message dictionary
            query: Original search query

        Returns:
            SourceItem representation
        """
        contact_name = message.get("contact_name", "Unknown")
        is_from_me = message.get("is_from_me", False)

        # Build title
        title = f"Message to {contact_name}" if is_from_me else f"Message from {contact_name}"

        # Build content
        content_parts = []
        time_str = message["timestamp"].strftime("%d/%m/%Y %H:%M")
        content_parts.append(f"Date: {time_str}")
        content_parts.append(f"Contact: {contact_name}")
        content_parts.append(f"Direction: {'Sent' if is_from_me else 'Received'}")
        content_parts.append("")
        content_parts.append(message.get("text", "")[:400])

        content = "\n".join(content_parts)

        # Calculate relevance
        relevance = self._calculate_relevance(message, query)

        return SourceItem(
            source="whatsapp",
            type="message",
            title=title,
            content=content,
            timestamp=message["timestamp"],
            relevance_score=relevance,
            url=None,
            metadata={
                "contact_jid": message.get("contact_jid"),
                "contact_name": contact_name,
                "is_from_me": is_from_me,
            },
        )

    def _calculate_relevance(
        self,
        message: dict[str, Any],
        query: str,
    ) -> float:
        """
        Calculate relevance score.

        Args:
            message: Message dictionary
            query: Original search query

        Returns:
            Relevance score (0.0 - 1.0)
        """
        base_score = 0.6
        query_lower = query.lower()
        text = message.get("text", "").lower()

        # Exact phrase match bonus
        if query_lower in text:
            base_score += 0.15

        # Contact name match
        contact_name = message.get("contact_name", "").lower()
        if query_lower in contact_name:
            base_score += 0.10

        # Recency factor
        now = datetime.now(timezone.utc)
        days_diff = abs((now - message["timestamp"]).days)
        if days_diff <= 1:
            base_score += 0.10
        elif days_diff <= 7:
            base_score += 0.05
        elif days_diff <= 30:
            base_score += 0.02
        elif days_diff > 90:
            base_score -= 0.05

        return min(max(base_score, 0.0), 0.95)

    def close(self) -> None:
        """Close database connection (thread-safe)."""
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
