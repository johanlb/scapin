"""
Teams adapter for CrossSourceEngine.

Provides Microsoft Graph API search functionality for finding relevant
Teams messages across all chats.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

if TYPE_CHECKING:
    from src.integrations.microsoft.teams_client import TeamsClient
    from src.passepartout.cross_source.config import TeamsAdapterConfig

logger = logging.getLogger("scapin.cross_source.teams")


class TeamsAdapter(BaseAdapter):
    """
    Teams adapter using Microsoft Graph API for cross-source queries.

    Searches Teams messages for matching content, sender information,
    and chat context.
    """

    _source_name = "teams"

    def __init__(
        self,
        teams_client: TeamsClient | None = None,
        adapter_config: TeamsAdapterConfig | None = None,
    ) -> None:
        """
        Initialize the Teams adapter.

        Args:
            teams_client: Microsoft Teams client instance
            adapter_config: Adapter-specific configuration
        """
        self._teams_client = teams_client
        self._adapter_config = adapter_config

    @property
    def is_available(self) -> bool:
        """Check if Teams is configured and accessible."""
        return self._teams_client is not None

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search Teams messages for relevant content.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context with additional filters
                    - since: datetime to filter messages from
                    - chat_filter: str to filter by chat name/topic
                    - mentions_only: bool to only include messages with mentions

        Returns:
            List of SourceItem objects representing matching messages
        """
        if not self.is_available or self._teams_client is None:
            logger.warning("Teams adapter not available, skipping search")
            return []

        try:
            # Get filter options from context
            since = None
            mentions_only = False
            chat_filter = None

            if context:
                since = context.get("since")
                mentions_only = context.get("mentions_only", False)
                chat_filter = context.get("chat_filter")

            # Calculate since date if not provided
            if since is None:
                # Default: look back 30 days
                days_back = 30
                if self._adapter_config:
                    days_back = getattr(self._adapter_config, "days_back", 30)
                since = datetime.now(timezone.utc) - timedelta(days=days_back)

            # Fetch recent messages
            messages = await self._teams_client.get_recent_messages(
                limit_per_chat=max(max_results, 50),  # Fetch more to filter
                since=since,
                include_chat_context=True,
                mentions_only=mentions_only,
            )

            # Filter messages by query
            query_lower = query.lower()
            matching_messages = []

            for message in messages:
                # Apply chat filter if specified
                if chat_filter and message.chat:
                    chat_name = message.chat.topic or ""
                    if chat_filter.lower() not in chat_name.lower():
                        continue

                if self._matches_query(message, query_lower):
                    matching_messages.append(message)
                    if len(matching_messages) >= max_results:
                        break

            # Convert to SourceItems
            results = [
                self._message_to_source_item(message, query)
                for message in matching_messages
            ]

            # Sort by relevance (most recent first)
            results.sort(key=lambda x: x.timestamp, reverse=True)

            logger.debug(
                "Teams search found %d messages matching '%s'",
                len(results),
                query[:50],
            )

            return results[:max_results]

        except Exception as e:
            logger.error("Teams search failed: %s", e)
            return []

    def _matches_query(self, message: Any, query_lower: str) -> bool:
        """
        Check if a message matches the search query.

        Searches in:
        - Message content (plain text)
        - Sender display name and email
        - Chat topic
        - Attachments

        Args:
            message: TeamsMessage object
            query_lower: Lowercase search query

        Returns:
            True if message matches
        """
        # Search in message content
        if query_lower in message.content_plain.lower():
            return True

        # Search in sender info
        if message.sender:
            if query_lower in message.sender.display_name.lower():
                return True
            if message.sender.email and query_lower in message.sender.email.lower():
                return True

        # Search in chat topic
        if message.chat and message.chat.topic and query_lower in message.chat.topic.lower():
            return True

        # Search in attachments
        return any(query_lower in attachment.lower() for attachment in message.attachments)

    def _message_to_source_item(
        self,
        message: Any,
        query: str,
    ) -> SourceItem:
        """
        Convert a TeamsMessage to SourceItem.

        Args:
            message: TeamsMessage object
            query: Original search query

        Returns:
            SourceItem representation
        """
        # Build title from chat context
        if message.chat and message.chat.topic:
            title = f"[{message.chat.topic}] {message.sender.display_name}"
        else:
            title = f"Message de {message.sender.display_name}"

        # Build content preview
        content_parts = []

        # Add timestamp
        time_str = message.created_at.strftime("%d/%m/%Y %H:%M")
        content_parts.append(f"Date: {time_str}")

        # Add sender
        sender_info = message.sender.display_name
        if message.sender.email:
            sender_info += f" ({message.sender.email})"
        content_parts.append(f"De: {sender_info}")

        # Add chat context
        if message.chat:
            chat_type_names = {
                "oneOnOne": "Conversation privée",
                "group": "Groupe",
                "meeting": "Réunion",
            }
            chat_type = chat_type_names.get(
                message.chat.chat_type.value, message.chat.chat_type.value
            )
            content_parts.append(f"Type: {chat_type}")

        # Add message content preview
        content_preview = message.content_plain[:300]
        if len(message.content_plain) > 300:
            content_preview += "..."
        content_parts.append(content_preview)

        # Add attachments if any
        if message.attachments:
            content_parts.append(f"Pièces jointes: {', '.join(message.attachments)}")

        content = "\n".join(content_parts)

        # Calculate relevance
        relevance = self._calculate_relevance(message, query)

        # Build metadata
        chat_members = []
        if message.chat and message.chat.members:
            chat_members = [m.display_name for m in message.chat.members]

        return SourceItem(
            source="teams",
            type="message",
            title=title,
            content=content,
            timestamp=message.created_at,
            relevance_score=relevance,
            url=None,  # Teams doesn't provide direct message URLs easily
            metadata={
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "sender_id": message.sender.user_id,
                "sender_name": message.sender.display_name,
                "sender_email": message.sender.email,
                "chat_type": message.chat.chat_type.value if message.chat else None,
                "chat_topic": message.chat.topic if message.chat else None,
                "chat_members": chat_members,
                "importance": message.importance.value,
                "is_reply": message.is_reply,
                "has_mentions": len(message.mentions) > 0,
                "mentions_count": len(message.mentions),
                "attachments": list(message.attachments),
            },
        )

    def _calculate_relevance(self, message: Any, query: str) -> float:
        """
        Calculate relevance score based on match quality and recency.

        Factors:
        - Match in content vs sender/topic (content > sender)
        - Recency (closer to now = more relevant)
        - Importance level (high/urgent messages get bonus)
        - Mentions (messages with mentions slightly higher)

        Args:
            message: TeamsMessage object
            query: Original search query

        Returns:
            Relevance score (0.0 - 1.0)
        """
        base_score = 0.6
        query_lower = query.lower()

        # Content match bonus
        if query_lower in message.content_plain.lower():
            base_score += 0.15

        # Sender match bonus
        if message.sender:
            if query_lower in message.sender.display_name.lower():
                base_score += 0.10
            if message.sender.email and query_lower in message.sender.email.lower():
                base_score += 0.05

        # Chat topic match bonus
        if message.chat and message.chat.topic and query_lower in message.chat.topic.lower():
            base_score += 0.08

        # Importance bonus
        if message.importance.value == "high":
            base_score += 0.05
        elif message.importance.value == "urgent":
            base_score += 0.10

        # Mentions bonus
        if message.mentions:
            base_score += 0.05

        # Recency factor
        now = datetime.now(timezone.utc)
        days_diff = abs((now - message.created_at).days)
        if days_diff <= 1:
            base_score += 0.10
        elif days_diff <= 7:
            base_score += 0.05
        elif days_diff <= 30:
            base_score += 0.02
        # Older messages get slight penalty
        elif days_diff > 90:
            base_score -= 0.05

        # Cap at 0.95
        return min(max(base_score, 0.0), 0.95)
