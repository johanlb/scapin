"""
Calendar adapter for CrossSourceEngine.

Provides Microsoft Graph API search functionality for finding relevant
calendar events in the user's past and upcoming schedule.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

if TYPE_CHECKING:
    from src.integrations.microsoft.calendar_client import CalendarClient
    from src.passepartout.cross_source.config import CalendarAdapterConfig

logger = logging.getLogger("scapin.cross_source.calendar")


class CalendarAdapter(BaseAdapter):
    """
    Calendar adapter using Microsoft Graph API for cross-source queries.

    Searches calendar events for matching subject, body, attendees,
    and location information.
    """

    _source_name = "calendar"

    def __init__(
        self,
        calendar_client: CalendarClient | None = None,
        adapter_config: CalendarAdapterConfig | None = None,
    ) -> None:
        """
        Initialize the calendar adapter.

        Args:
            calendar_client: Microsoft Calendar client instance
            adapter_config: Adapter-specific configuration
        """
        self._calendar_client = calendar_client
        self._adapter_config = adapter_config

    @property
    def is_available(self) -> bool:
        """Check if calendar is configured and accessible."""
        return self._calendar_client is not None

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search calendar events for relevant meetings.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context with additional filters
                    - date_from: Start date for search range
                    - date_to: End date for search range
                    - include_past: Whether to include past events (default True)
                    - include_future: Whether to include future events (default True)

        Returns:
            List of SourceItem objects representing matching events
        """
        if not self.is_available or self._calendar_client is None:
            logger.warning("Calendar adapter not available, skipping search")
            return []

        try:
            # Get date range from context or use defaults
            include_past = True
            include_future = True
            if context:
                include_past = context.get("include_past", True)
                include_future = context.get("include_future", True)

            # Calculate date range
            days_behind = self._get_days_behind(context) if include_past else 0
            days_ahead = self._get_days_ahead(context) if include_future else 0

            # Fetch events
            events = await self._calendar_client.get_events(
                days_ahead=days_ahead,
                days_behind=days_behind,
                limit=max(max_results * 3, 100),  # Fetch more to filter
                include_cancelled=False,
            )

            # Filter events by query
            query_lower = query.lower()
            matching_events = []

            for event in events:
                if self._matches_query(event, query_lower):
                    matching_events.append(event)
                    if len(matching_events) >= max_results:
                        break

            # Convert to SourceItems
            results = [
                self._event_to_source_item(event, query)
                for event in matching_events
            ]

            # Sort by relevance (most recent first for past, soonest first for future)
            results.sort(key=lambda x: x.timestamp, reverse=True)

            logger.debug(
                "Calendar search found %d events matching '%s'",
                len(results),
                query[:50],
            )

            return results[:max_results]

        except Exception as e:
            logger.error("Calendar search failed: %s", e)
            return []

    def _get_days_behind(self, context: dict[str, Any] | None) -> int:
        """Get number of days to look behind from context or config."""
        if context and "date_from" in context:
            date_from = context["date_from"]
            if isinstance(date_from, datetime):
                delta = datetime.now(timezone.utc) - date_from
                return max(int(delta.days), 0)

        # Use config or default
        if self._adapter_config:
            return self._adapter_config.past_days
        return 90  # Default: 90 days back

    def _get_days_ahead(self, context: dict[str, Any] | None) -> int:
        """Get number of days to look ahead from context or config."""
        if context and "date_to" in context:
            date_to = context["date_to"]
            if isinstance(date_to, datetime):
                delta = date_to - datetime.now(timezone.utc)
                return max(int(delta.days), 0)

        # Use config or default
        if self._adapter_config:
            return self._adapter_config.future_days
        return 30  # Default: 30 days ahead

    def _matches_query(self, event: Any, query_lower: str) -> bool:
        """
        Check if an event matches the search query.

        Searches in:
        - Subject
        - Body preview/content
        - Attendee names and emails
        - Organizer name and email
        - Location

        Args:
            event: CalendarEvent object
            query_lower: Lowercase search query

        Returns:
            True if event matches
        """
        # Search in subject
        if query_lower in event.subject.lower():
            return True

        # Search in body
        if event.body_preview and query_lower in event.body_preview.lower():
            return True
        if event.body_content and query_lower in event.body_content.lower():
            return True

        # Search in organizer
        if event.organizer:
            if query_lower in event.organizer.display_name.lower():
                return True
            if query_lower in event.organizer.email.lower():
                return True

        # Search in attendees
        for attendee in event.attendees:
            if query_lower in attendee.display_name.lower():
                return True
            if query_lower in attendee.email.lower():
                return True

        # Search in location
        if event.location and query_lower in event.location.display_name.lower():
            return True

        # Search in categories
        return any(query_lower in category.lower() for category in event.categories)

    def _event_to_source_item(
        self,
        event: Any,
        query: str,
    ) -> SourceItem:
        """
        Convert a CalendarEvent to SourceItem.

        Args:
            event: CalendarEvent object
            query: Original search query

        Returns:
            SourceItem representation
        """
        # Build content preview
        content_parts = []

        # Add time info
        start_str = event.start.strftime("%d/%m/%Y %H:%M") if event.start else "?"
        end_str = event.end.strftime("%H:%M") if event.end else "?"

        if event.is_all_day:
            content_parts.append(f"Journée entière - {start_str[:10]}")
        else:
            content_parts.append(f"{start_str} - {end_str}")

        # Add location
        if event.location:
            content_parts.append(f"Lieu: {event.location.display_name}")

        # Add organizer
        if event.organizer:
            content_parts.append(f"Organisateur: {event.organizer.display_name}")

        # Add attendees count
        if event.attendees:
            content_parts.append(f"{len(event.attendees)} participants")

        # Add body preview
        if event.body_preview:
            preview = event.body_preview[:200]
            if len(event.body_preview) > 200:
                preview += "..."
            content_parts.append(preview)

        content = "\n".join(content_parts)

        # Calculate relevance
        relevance = self._calculate_relevance(event, query)

        # Build metadata
        attendee_names = [a.display_name for a in event.attendees] if event.attendees else []
        attendee_emails = [a.email for a in event.attendees] if event.attendees else []

        return SourceItem(
            source="calendar",
            type="event",
            title=event.subject or "(Sans titre)",
            content=content,
            timestamp=event.start if event.start else datetime.now(timezone.utc),
            relevance_score=relevance,
            url=getattr(event, "web_link", None),
            metadata={
                "event_id": event.event_id,
                "calendar_id": event.calendar_id,
                "is_all_day": event.is_all_day,
                "is_online": event.is_online_meeting,
                "online_url": event.online_meeting_url,
                "organizer": event.organizer.email if event.organizer else None,
                "organizer_name": event.organizer.display_name if event.organizer else None,
                "attendees": attendee_emails,
                "attendee_names": attendee_names,
                "location": event.location.display_name if event.location else None,
                "importance": event.importance.value if event.importance else "normal",
                "categories": list(event.categories) if event.categories else [],
            },
        )

    def _calculate_relevance(self, event: Any, query: str) -> float:
        """
        Calculate relevance score based on match quality and recency.

        Factors:
        - Match in subject vs body (subject > body)
        - Recency (closer to now = more relevant)
        - Online meeting (slightly higher for Teams meetings)

        Args:
            event: CalendarEvent object
            query: Original search query

        Returns:
            Relevance score (0.0 - 1.0)
        """
        base_score = 0.7
        query_lower = query.lower()

        # Subject match bonus
        if query_lower in event.subject.lower():
            base_score += 0.15

        # Organizer/attendee match bonus
        if event.organizer and query_lower in event.organizer.display_name.lower():
            base_score += 0.10
        for attendee in event.attendees:
            if query_lower in attendee.display_name.lower():
                base_score += 0.05
                break

        # Recency factor
        now = datetime.now(timezone.utc)
        if event.start:
            days_diff = abs((now - event.start).days)
            if days_diff <= 7:
                base_score += 0.05
            elif days_diff <= 30:
                base_score += 0.02
            # Older events get slight penalty
            elif days_diff > 90:
                base_score -= 0.05

        # Cap at 0.95
        return min(max(base_score, 0.0), 0.95)
