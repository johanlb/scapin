"""
Email adapter for CrossSourceEngine.

Provides IMAP search functionality for finding relevant emails
in the user's archived mail.
"""

from __future__ import annotations

import asyncio
import contextlib
import email
import imaplib
import logging
from datetime import datetime, timezone
from email.header import decode_header
from typing import TYPE_CHECKING, Any

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

if TYPE_CHECKING:
    from src.core.config_manager import EmailAccountConfig
    from src.passepartout.cross_source.config import EmailAdapterConfig

logger = logging.getLogger("scapin.cross_source.email")


class EmailAdapter(BaseAdapter):
    """
    Email adapter using IMAP SEARCH for cross-source queries.

    Searches across all email folders for messages matching
    the query in subject, body, or sender fields.
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
        self._connection: imaplib.IMAP4_SSL | None = None

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

        # Run IMAP search in thread pool (blocking I/O)
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None,
                self._search_sync,
                query,
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

        Args:
            query: The search query
            max_results: Maximum results
            context: Optional context

        Returns:
            List of SourceItem objects
        """
        results: list[SourceItem] = []

        try:
            # Connect to IMAP server
            self._connect()
            if self._connection is None:
                return []

            # Get folders to search
            folders = self._get_search_folders(context)

            # Build IMAP search criteria
            search_criteria = self._build_search_criteria(query, context)

            # Search each folder
            for folder in folders:
                if len(results) >= max_results:
                    break

                folder_results = self._search_folder(
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
            query: The search query
            context: Optional context with additional filters

        Returns:
            IMAP SEARCH criteria string
        """
        # Escape query for IMAP
        escaped_query = query.replace('"', '\\"')

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

        # Add custom filter from context
        if context and "email_filter" in context:
            criteria = f'{criteria} {context["email_filter"]}'

        return criteria

    def _search_folder(
        self,
        folder: str,
        search_criteria: str,
        max_results: int,
    ) -> list[SourceItem]:
        """
        Search a single folder for matching emails.

        Args:
            folder: Folder name
            search_criteria: IMAP SEARCH criteria
            max_results: Maximum results from this folder

        Returns:
            List of SourceItem objects
        """
        if self._connection is None:
            return []

        results: list[SourceItem] = []

        try:
            # Select folder (readonly)
            status, _ = self._connection.select(folder, readonly=True)
            if status != "OK":
                logger.debug("Could not select folder: %s", folder)
                return []

            # Execute search
            status, message_ids = self._connection.search(None, search_criteria)
            if status != "OK":
                logger.debug("Search failed in folder: %s", folder)
                return []

            # Get message IDs (newest first for better relevance)
            id_list = message_ids[0].split()
            id_list = list(reversed(id_list))  # Newest first
            id_list = id_list[:max_results]

            # Fetch each email
            for msg_id in id_list:
                try:
                    item = self._fetch_email_item(msg_id, folder)
                    if item:
                        results.append(item)
                except Exception as e:
                    logger.debug("Failed to fetch email %s: %s", msg_id, e)

            logger.debug(
                "Found %d emails in %s matching search",
                len(results),
                folder,
            )

        except Exception as e:
            logger.debug("Error searching folder %s: %s", folder, e)

        return results

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
