"""
Email adapter for CrossSourceEngine.

Provides IMAP search functionality for finding relevant emails
in the user's archived mail.

Uses connection pooling for improved performance across multiple searches.
"""

from __future__ import annotations

import asyncio
import contextlib
import email
import imaplib
import logging
import threading
import time
from datetime import datetime, timezone
from email.header import decode_header
from typing import TYPE_CHECKING, Any

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

if TYPE_CHECKING:
    from src.core.config_manager import EmailAccountConfig
    from src.passepartout.cross_source.config import EmailAdapterConfig

logger = logging.getLogger("scapin.cross_source.email")

# Security constants
MAX_QUERY_LENGTH = 500
# Characters that need escaping in IMAP SEARCH strings
IMAP_SPECIAL_CHARS = frozenset('"\\()*')

# Connection pool constants
POOL_MAX_SIZE = 3  # Maximum connections per account
POOL_CONNECTION_TTL = 300  # 5 minutes
POOL_ACQUIRE_TIMEOUT = 10  # Seconds to wait for connection


class IMAPConnectionPool:
    """
    Connection pool for IMAP connections.

    Provides connection reuse and lifecycle management:
    - Creates connections on demand up to max_size
    - Recycles connections after TTL expires
    - Thread-safe for concurrent access

    Example:
        pool = IMAPConnectionPool(account_config, max_size=3)
        async with pool.acquire() as conn:
            conn.select("INBOX")
            # ... use connection
        pool.close_all()
    """

    def __init__(
        self,
        account_config: EmailAccountConfig,
        max_size: int = POOL_MAX_SIZE,
        ttl_seconds: int = POOL_CONNECTION_TTL,
    ) -> None:
        """
        Initialize the connection pool.

        Args:
            account_config: IMAP account configuration
            max_size: Maximum number of connections
            ttl_seconds: Connection time-to-live in seconds
        """
        self._account_config = account_config
        self._max_size = max_size
        self._ttl = ttl_seconds

        # Pool storage: (connection, created_at, in_use)
        self._pool: list[tuple[imaplib.IMAP4_SSL, float, bool]] = []
        self._lock = threading.Lock()

        # Stats
        self._connections_created = 0
        self._connections_reused = 0

    def _create_connection(self) -> imaplib.IMAP4_SSL | None:
        """Create a new IMAP connection."""
        try:
            conn = imaplib.IMAP4_SSL(
                self._account_config.imap_host,
                self._account_config.imap_port,
            )
            conn.login(
                self._account_config.imap_username,
                self._account_config.imap_password,
            )
            self._connections_created += 1
            logger.debug(
                "IMAP connection created (total_created=%d)",
                self._connections_created,
            )
            return conn
        except Exception as e:
            logger.error("Failed to create IMAP connection: %s", type(e).__name__)
            return None

    def _is_connection_valid(
        self,
        conn: imaplib.IMAP4_SSL,
        created_at: float,
    ) -> bool:
        """Check if a connection is still valid."""
        # Check TTL
        if time.time() - created_at > self._ttl:
            return False

        # Check IMAP state
        try:
            conn.noop()
            return True
        except Exception:
            return False

    def _close_connection(self, conn: imaplib.IMAP4_SSL) -> None:
        """Close a connection gracefully."""
        with contextlib.suppress(Exception):
            conn.logout()

    def acquire(self) -> IMAPConnectionContext:
        """
        Acquire a connection from the pool.

        Returns:
            Context manager that yields the connection

        Example:
            async with pool.acquire() as conn:
                conn.select("INBOX")
        """
        return IMAPConnectionContext(self)

    def _acquire_sync(self, timeout: float = POOL_ACQUIRE_TIMEOUT) -> imaplib.IMAP4_SSL | None:
        """
        Synchronously acquire a connection from the pool with timeout.

        Args:
            timeout: Maximum seconds to wait for connection (default: 10)

        Returns:
            IMAP connection or None if unavailable/timeout
        """
        start_time = time.time()
        retry_interval = 0.1  # 100ms between retries

        while time.time() - start_time < timeout:
            conn = self._try_acquire()
            if conn is not None:
                return conn

            # Wait briefly before retry
            time.sleep(retry_interval)
            retry_interval = min(retry_interval * 1.5, 1.0)  # Exponential backoff, max 1s

        logger.warning("IMAP pool acquire timeout after %.1fs", timeout)
        return None

    def _try_acquire(self) -> imaplib.IMAP4_SSL | None:
        """
        Single attempt to acquire a connection (internal).

        Returns:
            IMAP connection or None if none available
        """
        with self._lock:
            now = time.time()

            # First pass: find available, valid connections
            # Use index-based loop to safely handle removal
            to_remove: list[int] = []
            acquired_conn: imaplib.IMAP4_SSL | None = None
            acquired_idx: int | None = None

            for i, (conn, created_at, in_use) in enumerate(self._pool):
                if in_use:
                    continue

                if self._is_connection_valid(conn, created_at):
                    # Found valid connection - mark for acquisition
                    acquired_conn = conn
                    acquired_idx = i
                    break
                else:
                    # Mark invalid connection for removal
                    to_remove.append(i)
                    self._close_connection(conn)

            # Remove invalid connections (reverse order to preserve indices)
            for idx in reversed(to_remove):
                del self._pool[idx]

            # If we found a valid connection, mark it as in_use
            if acquired_conn is not None and acquired_idx is not None:
                # Adjust index if we removed items before it
                adjusted_idx = acquired_idx - sum(1 for r in to_remove if r < acquired_idx)
                if 0 <= adjusted_idx < len(self._pool):
                    conn, created_at, _ = self._pool[adjusted_idx]
                    self._pool[adjusted_idx] = (conn, created_at, True)
                    self._connections_reused += 1
                    logger.debug(
                        "IMAP connection reused (total_reused=%d)",
                        self._connections_reused,
                    )
                    return conn

            # Create new connection if pool not full
            if len(self._pool) < self._max_size:
                conn = self._create_connection()
                if conn is not None:
                    self._pool.append((conn, now, True))
                    return conn

            # Pool full, caller should retry
            return None

    def _release(self, conn: imaplib.IMAP4_SSL) -> bool:
        """
        Release a connection back to the pool.

        Args:
            conn: Connection to release

        Returns:
            True if released successfully, False if connection not found in pool
        """
        with self._lock:
            for i, (pool_conn, created_at, _in_use) in enumerate(self._pool):
                if pool_conn is conn:
                    self._pool[i] = (conn, created_at, False)
                    logger.debug("IMAP connection released to pool")
                    return True

            # Connection not found - might have been removed due to error
            logger.debug("IMAP connection not found in pool during release")
            return False

    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            for conn, _, _ in self._pool:
                self._close_connection(conn)
            self._pool.clear()
            logger.debug("IMAP connection pool closed")

    @property
    def stats(self) -> dict[str, int]:
        """Get pool statistics."""
        with self._lock:
            return {
                "pool_size": len(self._pool),
                "max_size": self._max_size,
                "in_use": sum(1 for _, _, in_use in self._pool if in_use),
                "connections_created": self._connections_created,
                "connections_reused": self._connections_reused,
            }


class IMAPConnectionContext:
    """
    Context manager for IMAP pool connections.

    Ensures proper acquire/release semantics and prevents use-after-release.
    """

    def __init__(self, pool: IMAPConnectionPool) -> None:
        self._pool = pool
        self._conn: imaplib.IMAP4_SSL | None = None
        self._released: bool = False

    async def __aenter__(self) -> imaplib.IMAP4_SSL | None:
        """Acquire connection."""
        # Run sync acquire in thread to not block event loop
        loop = asyncio.get_event_loop()
        self._conn = await loop.run_in_executor(None, self._pool._acquire_sync)
        self._released = False
        return self._conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Release connection and clear reference to prevent use-after-release."""
        if self._conn is not None and not self._released:
            self._pool._release(self._conn)
            self._released = True
        # Clear reference to prevent accidental use
        self._conn = None


class EmailAdapter(BaseAdapter):
    """
    Email adapter using IMAP SEARCH for cross-source queries.

    Searches across all email folders for messages matching
    the query in subject, body, or sender fields.

    Uses connection pooling for improved performance across
    multiple searches - connections are reused with TTL-based
    recycling.
    """

    _source_name = "email"

    def __init__(
        self,
        account_config: EmailAccountConfig | None = None,
        adapter_config: EmailAdapterConfig | None = None,
    ) -> None:
        """
        Initialize the email adapter.

        Args:
            account_config: Email account configuration (IMAP credentials)
            adapter_config: Adapter-specific configuration
        """
        self._account_config = account_config
        self._adapter_config = adapter_config
        # Legacy connection field (deprecated, use pool instead)
        self._connection: imaplib.IMAP4_SSL | None = None
        # Connection pool for improved performance
        self._pool: IMAPConnectionPool | None = None
        if account_config is not None:
            self._pool = IMAPConnectionPool(account_config)

    @property
    def is_available(self) -> bool:
        """Check if email is configured and accessible."""
        if self._account_config is None:
            return False
        return bool(
            self._account_config.imap_host
            and self._account_config.imap_username
            and self._account_config.imap_password
        )

    @property
    def pool_stats(self) -> dict[str, int]:
        """
        Get connection pool statistics.

        Returns:
            Dict with pool_size, in_use, connections_created, connections_reused
        """
        if self._pool is None:
            return {
                "pool_size": 0,
                "max_size": 0,
                "in_use": 0,
                "connections_created": 0,
                "connections_reused": 0,
            }
        return self._pool.stats

    def close(self) -> None:
        """
        Close the adapter and clean up resources.

        Closes all connections in the pool.
        """
        if self._pool is not None:
            self._pool.close_all()
            logger.debug("Email adapter connection pool closed")

    @staticmethod
    def _escape_imap_string(value: str) -> str:
        """
        Escape special characters for IMAP SEARCH strings.

        IMAP SEARCH has specific quoting requirements:
        - Strings containing spaces or special chars must be quoted
        - Backslashes and quotes inside strings must be escaped

        Args:
            value: Raw search string

        Returns:
            Escaped string safe for IMAP SEARCH
        """
        if not value:
            return ""

        # Escape backslash first (order matters)
        result = value.replace("\\", "\\\\")
        # Escape double quotes
        result = result.replace('"', '\\"')

        return result

    def _validate_query(self, query: str) -> str:
        """
        Validate and sanitize search query.

        Args:
            query: Raw search query

        Returns:
            Sanitized query or empty string if invalid
        """
        if not query or not isinstance(query, str):
            return ""

        # Truncate to max length
        safe_query = query[:MAX_QUERY_LENGTH].strip()

        # Remove control characters that could break IMAP protocol
        safe_query = "".join(c for c in safe_query if c.isprintable() or c == " ")

        return safe_query

    def _sanitize_email_filter(self, email_filter: str | None) -> str | None:
        """
        Sanitize email_filter from context to prevent injection.

        Only allows safe IMAP SEARCH keywords.

        Args:
            email_filter: Raw email filter from context

        Returns:
            Sanitized filter or None if invalid
        """
        if not email_filter or not isinstance(email_filter, str):
            return None

        # Whitelist of safe IMAP SEARCH keywords
        safe_keywords = {
            "ALL", "ANSWERED", "BCC", "BEFORE", "CC", "DELETED", "DRAFT",
            "FLAGGED", "FROM", "HEADER", "KEYWORD", "LARGER", "NEW", "NOT",
            "OLD", "ON", "OR", "RECENT", "SEEN", "SENTBEFORE", "SENTON",
            "SENTSINCE", "SINCE", "SMALLER", "SUBJECT", "TEXT", "TO",
            "UID", "UNANSWERED", "UNDELETED", "UNDRAFT", "UNFLAGGED",
            "UNKEYWORD", "UNSEEN",
        }

        # Parse and validate filter tokens
        safe_parts = []
        tokens = email_filter.upper().split()

        for token in tokens:
            # Check if it's a known keyword
            if token in safe_keywords:
                safe_parts.append(token)
            # Allow date-like values (YYYY-MM-DD format)
            elif len(token) == 10 and token.count("-") == 2:
                try:
                    # Validate it looks like a date
                    parts = token.split("-")
                    if all(p.isdigit() for p in parts):
                        safe_parts.append(token)
                except ValueError:
                    pass
            # Allow numeric values (for LARGER, SMALLER, etc.)
            elif token.isdigit():
                safe_parts.append(token)

        if not safe_parts:
            logger.warning("Invalid email_filter rejected: %s", email_filter[:50])
            return None

        return " ".join(safe_parts)

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search emails for relevant messages.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context with additional filters
                    - email_filter: IMAP search filter string
                    - folders: List of folders to search

        Returns:
            List of SourceItem objects representing matching emails
        """
        if not self.is_available or self._account_config is None:
            logger.warning("Email adapter not available, skipping search")
            return []

        # Validate and sanitize query
        safe_query = self._validate_query(query)
        if not safe_query:
            logger.warning("Invalid or empty email search query")
            return []

        # Run IMAP search in thread pool (blocking I/O)
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None,
                self._search_sync,
                safe_query,
                max_results,
                context,
            )
            return results
        except Exception as e:
            logger.error("Email search failed: %s", e)
            return []

    def _search_sync(
        self,
        query: str,
        max_results: int,
        context: dict[str, Any] | None,
    ) -> list[SourceItem]:
        """
        Synchronous IMAP search implementation.

        Uses connection pooling for improved performance.

        Args:
            query: The search query
            max_results: Maximum results
            context: Optional context

        Returns:
            List of SourceItem objects
        """
        results: list[SourceItem] = []

        # Acquire connection from pool (or create new if pool unavailable)
        conn = self._acquire_connection()
        if conn is None:
            return []

        try:
            # Get folders to search
            folders = self._get_search_folders(context)

            # Build IMAP search criteria
            search_criteria = self._build_search_criteria(query, context)

            # Search each folder
            for folder in folders:
                if len(results) >= max_results:
                    break

                folder_results = self._search_folder(
                    conn,
                    folder,
                    search_criteria,
                    max_results - len(results),
                )
                results.extend(folder_results)

            # Sort by timestamp (newest first for relevance)
            results.sort(key=lambda x: x.timestamp, reverse=True)

            return results[:max_results]

        except Exception as e:
            logger.error("IMAP search error: %s", e)
            return []

        finally:
            self._release_connection(conn)

    def _acquire_connection(self) -> imaplib.IMAP4_SSL | None:
        """
        Acquire an IMAP connection from the pool.

        Falls back to creating a direct connection if pool unavailable.

        Returns:
            IMAP connection or None if unavailable
        """
        # Try pool first
        if self._pool is not None:
            conn = self._pool._acquire_sync()
            if conn is not None:
                return conn

        # Fallback to direct connection (legacy mode)
        self._connect()
        return self._connection

    def _release_connection(self, conn: imaplib.IMAP4_SSL | None) -> None:
        """
        Release an IMAP connection back to the pool.

        Args:
            conn: Connection to release
        """
        if conn is None:
            return

        # If using pool, release to pool
        if self._pool is not None:
            self._pool._release(conn)
        else:
            # Legacy mode: disconnect
            self._disconnect()

    def _connect(self) -> None:
        """Establish IMAP connection."""
        if self._account_config is None:
            return

        try:
            self._connection = imaplib.IMAP4_SSL(
                self._account_config.imap_host,
                self._account_config.imap_port,
            )
            self._connection.login(
                self._account_config.imap_username,
                self._account_config.imap_password,
            )
            logger.debug("IMAP connection established for search")
        except Exception as e:
            logger.error("Failed to connect to IMAP: %s", e)
            self._connection = None

    def _disconnect(self) -> None:
        """Close IMAP connection."""
        if self._connection is not None:
            with contextlib.suppress(Exception):
                self._connection.logout()
            self._connection = None

    def _get_search_folders(self, context: dict[str, Any] | None) -> list[str]:
        """
        Get list of folders to search.

        Args:
            context: Optional context with folders list

        Returns:
            List of folder names
        """
        # Check if specific folders specified in context
        if context and "folders" in context:
            return context["folders"]

        # Default: search INBOX and Archive
        return ["INBOX", "Archive", "[Gmail]/All Mail", "Sent"]

    def _build_search_criteria(
        self,
        query: str,
        context: dict[str, Any] | None,
    ) -> str:
        """
        Build IMAP SEARCH criteria from query.

        IMAP SEARCH syntax:
        - OR criterion1 criterion2
        - SUBJECT "text"
        - BODY "text"
        - FROM "text"
        - TEXT "text" (searches everywhere)

        Args:
            query: The search query (already validated)
            context: Optional context with additional filters

        Returns:
            IMAP SEARCH criteria string
        """
        # Properly escape query for IMAP SEARCH
        escaped_query = self._escape_imap_string(query)

        # Check if we should search body (can be slow)
        search_body = True
        if self._adapter_config:
            search_body = self._adapter_config.search_body

        # Build OR criteria for subject, from, and optionally body
        if search_body:
            # Search in subject, from, and body
            criteria = (
                f'OR OR SUBJECT "{escaped_query}" '
                f'FROM "{escaped_query}" '
                f'BODY "{escaped_query}"'
            )
        else:
            # Search only in subject and from
            criteria = f'OR SUBJECT "{escaped_query}" FROM "{escaped_query}"'

        # Add custom filter from context (sanitized)
        if context and "email_filter" in context:
            safe_filter = self._sanitize_email_filter(context["email_filter"])
            if safe_filter:
                criteria = f"{criteria} {safe_filter}"

        return criteria

    def _search_folder(
        self,
        conn: imaplib.IMAP4_SSL,
        folder: str,
        search_criteria: str,
        max_results: int,
    ) -> list[SourceItem]:
        """
        Search a single folder for matching emails.

        Args:
            conn: IMAP connection to use
            folder: Folder name
            search_criteria: IMAP SEARCH criteria
            max_results: Maximum results from this folder

        Returns:
            List of SourceItem objects
        """
        results: list[SourceItem] = []

        try:
            # Select folder (readonly)
            status, _ = conn.select(folder, readonly=True)
            if status != "OK":
                logger.debug("Could not select folder: %s", folder)
                return []

            # Execute search
            status, message_ids = conn.search(None, search_criteria)
            if status != "OK":
                logger.debug("Search failed in folder: %s", folder)
                return []

            # Get message IDs (newest first for better relevance)
            id_list = message_ids[0].split()
            id_list = list(reversed(id_list))  # Newest first
            id_list = id_list[:max_results]

            # Batch fetch emails (more efficient than individual fetches)
            if id_list:
                results.extend(self._batch_fetch_emails(conn, id_list, folder))

            logger.debug(
                "Found %d emails in %s matching search",
                len(results),
                folder,
            )

        except Exception as e:
            logger.debug("Error searching folder %s: %s", folder, e)

        return results

    def _batch_fetch_emails(
        self,
        conn: imaplib.IMAP4_SSL,
        id_list: list[bytes],
        folder: str,
    ) -> list[SourceItem]:
        """
        Batch fetch multiple emails in a single IMAP command.

        More efficient than individual fetches - reduces network roundtrips.

        Args:
            conn: IMAP connection to use
            id_list: List of IMAP message IDs
            folder: Folder name for metadata

        Returns:
            List of SourceItem objects
        """
        if not id_list:
            return []

        results: list[SourceItem] = []

        try:
            # Build comma-separated ID list for batch fetch
            id_set = b",".join(id_list)

            # Batch fetch headers and partial body for all emails
            status, response = conn.fetch(
                id_set,
                "(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.500>)",
            )
            if status != "OK" or not response:
                logger.debug("Batch fetch failed for folder: %s", folder)
                return []

            # Process response - each email comes in pairs (header info, data)
            current_msg_id = None
            header_data = b""
            body_preview = b""

            for item in response:
                if item is None:
                    continue

                if isinstance(item, tuple) and len(item) >= 2:
                    header = item[0]
                    data = item[1]

                    if isinstance(header, bytes):
                        # Extract message ID from header
                        if b"HEADER" in header:
                            header_data = data
                            # Try to extract msg ID from the header line
                            header_str = header.decode("ascii", errors="ignore")
                            # Format: "1 (BODY[HEADER] ..."
                            parts = header_str.split()
                            if parts:
                                current_msg_id = parts[0].encode()
                        elif b"TEXT" in header:
                            body_preview = data

                            # We have both header and body - create SourceItem
                            if header_data:
                                source_item = self._parse_email_parts(
                                    current_msg_id or b"",
                                    header_data,
                                    body_preview,
                                    folder,
                                )
                                if source_item:
                                    results.append(source_item)

                            # Reset for next email
                            header_data = b""
                            body_preview = b""

            logger.debug(
                "Batch fetched %d emails from %s",
                len(results),
                folder,
            )

        except Exception as e:
            logger.debug("Batch fetch error: %s", e)

        return results

    def _parse_email_parts(
        self,
        msg_id: bytes,
        header_data: bytes,
        body_preview: bytes,
        folder: str,
    ) -> SourceItem | None:
        """
        Parse email header and body into a SourceItem.

        Args:
            msg_id: IMAP message ID
            header_data: Raw email headers
            body_preview: Partial body text
            folder: Folder name

        Returns:
            SourceItem or None if parsing failed
        """
        try:
            # Parse headers
            msg = email.message_from_bytes(header_data)

            # Extract fields
            subject = self._decode_header(msg.get("Subject", ""))
            from_header = self._decode_header(msg.get("From", ""))
            date_str = msg.get("Date", "")
            message_id_header = msg.get("Message-ID", "")

            # Parse date
            timestamp = self._parse_date(date_str)

            # Build content preview
            content = self._build_content_preview(body_preview, from_header)

            # Calculate relevance (higher for more recent emails)
            relevance = self._calculate_relevance(timestamp)

            return SourceItem(
                source="email",
                type="message",
                title=subject or "(No Subject)",
                content=content,
                timestamp=timestamp,
                relevance_score=relevance,
                url=None,
                metadata={
                    "message_id": message_id_header,
                    "from": from_header,
                    "folder": folder,
                    "imap_id": msg_id.decode() if isinstance(msg_id, bytes) else msg_id,
                },
            )
        except Exception as e:
            logger.debug("Error parsing email: %s", e)
            return None

    def _fetch_email_item(
        self,
        msg_id: bytes,
        folder: str,
    ) -> SourceItem | None:
        """
        Fetch an email and convert to SourceItem.

        Args:
            msg_id: IMAP message ID
            folder: Folder name

        Returns:
            SourceItem or None if fetch failed
        """
        if self._connection is None:
            return None

        try:
            # Fetch email headers and partial body
            status, response = self._connection.fetch(
                msg_id,
                "(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.500>)",
            )
            if status != "OK" or not response:
                return None

            # Parse email parts
            header_data = b""
            body_preview = b""

            for item in response:
                if isinstance(item, tuple) and len(item) >= 2:
                    header = item[0]
                    data = item[1]
                    if isinstance(header, bytes):
                        if b"HEADER" in header:
                            header_data = data
                        elif b"TEXT" in header:
                            body_preview = data

            if not header_data:
                return None

            # Parse headers
            msg = email.message_from_bytes(header_data)

            # Extract fields
            subject = self._decode_header(msg.get("Subject", ""))
            from_header = self._decode_header(msg.get("From", ""))
            date_str = msg.get("Date", "")
            message_id_header = msg.get("Message-ID", "")

            # Parse date
            timestamp = self._parse_date(date_str)

            # Build content preview
            content = self._build_content_preview(body_preview, from_header)

            # Calculate relevance (higher for more recent emails)
            relevance = self._calculate_relevance(timestamp)

            return SourceItem(
                source="email",
                type="message",
                title=subject or "(No Subject)",
                content=content,
                timestamp=timestamp,
                relevance_score=relevance,
                url=None,  # No direct URL for IMAP emails
                metadata={
                    "message_id": message_id_header,
                    "from": from_header,
                    "folder": folder,
                    "imap_id": msg_id.decode() if isinstance(msg_id, bytes) else msg_id,
                },
            )

        except Exception as e:
            logger.debug("Error fetching email: %s", e)
            return None

    def _decode_header(self, header_value: str) -> str:
        """
        Decode MIME-encoded header value.

        Args:
            header_value: Raw header value

        Returns:
            Decoded string
        """
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)
            result = []
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    charset = charset or "utf-8"
                    try:
                        result.append(part.decode(charset))
                    except (UnicodeDecodeError, LookupError):
                        result.append(part.decode("utf-8", errors="replace"))
                else:
                    result.append(part)
            return "".join(result)
        except Exception:
            return header_value

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse email date string.

        Args:
            date_str: Date header value

        Returns:
            datetime object (UTC)
        """
        from email.utils import parsedate_to_datetime

        try:
            dt = parsedate_to_datetime(date_str)
            # Convert to UTC if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc)

    def _build_content_preview(
        self,
        body_preview: bytes,
        from_header: str,
    ) -> str:
        """
        Build content preview string.

        Args:
            body_preview: Raw body preview bytes
            from_header: From header for context

        Returns:
            Content preview string (max 500 chars)
        """
        # Try to decode body preview
        preview = ""
        if body_preview:
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    preview = body_preview.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

        # Clean up preview
        preview = preview.replace("\r\n", " ").replace("\n", " ")
        preview = " ".join(preview.split())  # Normalize whitespace

        # Build final content with from info
        content = f"From: {from_header}\n{preview}" if from_header else preview

        # Truncate to 500 chars
        if len(content) > 500:
            content = content[:497] + "..."

        return content

    def _calculate_relevance(self, timestamp: datetime) -> float:
        """
        Calculate relevance score based on recency.

        More recent emails are more relevant.

        Args:
            timestamp: Email timestamp

        Returns:
            Relevance score (0.0 - 1.0)
        """
        now = datetime.now(timezone.utc)
        age_days = (now - timestamp).days

        # Base relevance of 0.7, decays over 30 days
        if age_days <= 0:
            return 0.95
        elif age_days <= 7:
            return 0.9
        elif age_days <= 30:
            return 0.8
        elif age_days <= 90:
            return 0.7
        elif age_days <= 365:
            return 0.6
        else:
            return 0.5
