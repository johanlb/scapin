"""
iCloud Calendar adapter for CrossSourceEngine.

Provides CalDAV-based search functionality for finding relevant
calendar events in the user's iCloud Calendar.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

if TYPE_CHECKING:
    from src.integrations.apple.calendar_client import ICloudCalendarClient
    from src.passepartout.cross_source.config import ICloudCalendarAdapterConfig

logger = logging.getLogger("scapin.cross_source.icloud_calendar")


class ICloudCalendarAdapter(BaseAdapter):
    """
    iCloud Calendar adapter using CalDAV for cross-source queries.

    Searches calendar events for matching summary, description,
    attendees, and location information.
    """

    _source_name = "icloud_calendar"

    def __init__(
        self,
        icloud_calendar_client: ICloudCalendarClient | None = None,
        adapter_config: ICloudCalendarAdapterConfig | None = None,
    ) -> None:
        """
        Initialize the iCloud Calendar adapter.

        Args:
            icloud_calendar_client: iCloud Calendar client instance
            adapter_config: Adapter-specific configuration
        """
        self._icloud_client = icloud_calendar_client
        self._adapter_config = adapter_config

    @property
    def is_available(self) -> bool:
        """Check if iCloud Calendar is configured and accessible."""
        if self._icloud_client is None:
            return False
        return self._icloud_client.is_available()

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search iCloud Calendar events for relevant meetings.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context with additional filters
                    - date_from: Start date for search range
                    - date_to: End date for search range
                    - include_past: Whether to include past events (default True)
                    - include_future: Whether to include future events (default True)
                    - calendar_names: List of specific calendars to search

        Returns:
            List of SourceItem objects representing matching events
        """
        if not self.is_available or self._icloud_client is None:
            logger.warning("iCloud Calendar adapter not available, skipping search")
            return []

        try:
            # Get options from context
            include_past = True
            include_future = True
            calendar_names = None

            if context:
                include_past = context.get("include_past", True)
                include_future = context.get("include_future", True)
                calendar_names = context.get("calendar_names")

            # Calculate date range
            days_behind = self._get_days_behind(context) if include_past else 0
            days_ahead = self._get_days_ahead(context) if include_future else 0

            # Run sync search in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            events = await loop.run_in_executor(
                None,
                lambda: self._icloud_client.search_events(
                    query=query,
                    days_ahead=days_ahead,
                    days_behind=days_behind,
                    calendar_names=calendar_names,
                    max_results=max(max_results * 2, 50),  # Fetch more to filter
                ),
            )

            # Convert to SourceItems
            results = [
                self._event_to_source_item(event, query)
                for event in events
            ]

            # Sort by relevance (most recent first)
            results.sort(key=lambda x: x.timestamp, reverse=True)

            logger.debug(
                "iCloud Calendar search found %d events matching '%s'",
                len(results),
                query[:50],
            )

            return results[:max_results]

        except Exception as e:
            logger.error("iCloud Calendar search failed: %s", e)
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

    def _event_to_source_item(
        self,
        event: Any,
        query: str,
    ) -> SourceItem:
        """
        Convert an ICloudCalendarEvent to SourceItem.

        Args:
            event: ICloudCalendarEvent object
            query: Original search query

        Returns:
            SourceItem representation
        """
        # Build content preview
        content_parts = []

        # Add time info
        start_str = event.start_date.strftime("%d/%m/%Y %H:%M") if event.start_date else "?"
        end_str = event.end_date.strftime("%H:%M") if event.end_date else "?"

        if event.is_all_day:
            content_parts.append(f"Journée entière - {start_str[:10]}")
        else:
            content_parts.append(f"{start_str} - {end_str}")

        # Add calendar name
        if event.calendar_name:
            content_parts.append(f"Calendrier: {event.calendar_name}")

        # Add location
        if event.location:
            content_parts.append(f"Lieu: {event.location}")

        # Add organizer
        if event.organizer:
            content_parts.append(f"Organisateur: {event.organizer.name}")

        # Add attendees count
        if event.attendees:
            content_parts.append(f"{len(event.attendees)} participants")

        # Add description preview
        if event.description:
            preview = event.description[:200]
            if len(event.description) > 200:
                preview += "..."
            content_parts.append(preview)

        content = "\n".join(content_parts)

        # Calculate relevance
        relevance = self._calculate_relevance(event, query)

        # Build metadata
        attendee_names = [a.name for a in event.attendees] if event.attendees else []
        attendee_emails = [a.email for a in event.attendees] if event.attendees else []

        return SourceItem(
            source="icloud_calendar",
            type="event",
            title=event.summary or "(Sans titre)",
            content=content,
            timestamp=event.start_date if event.start_date else datetime.now(timezone.utc),
            relevance_score=relevance,
            url=event.url if event.url else None,
            metadata={
                "event_uid": event.uid,
                "calendar_name": event.calendar_name,
                "is_all_day": event.is_all_day,
                "is_online": event.is_online_meeting,
                "organizer": event.organizer.email if event.organizer else None,
                "organizer_name": event.organizer.name if event.organizer else None,
                "attendees": attendee_emails,
                "attendee_names": attendee_names,
                "location": event.location,
                "status": event.status.value,
                "is_recurring": bool(event.recurrence_rule),
            },
        )

    def _calculate_relevance(self, event: Any, query: str) -> float:
        """
        Calculate relevance score based on match quality and recency.

        Factors:
        - Match in summary vs description (summary > description)
        - Recency (closer to now = more relevant)
        - Online meeting indicator

        Args:
            event: ICloudCalendarEvent object
            query: Original search query

        Returns:
            Relevance score (0.0 - 1.0)
        """
        base_score = 0.7
        query_lower = query.lower()

        # Summary match bonus
        if query_lower in event.summary.lower():
            base_score += 0.15

        # Organizer/attendee match bonus
        if event.organizer and query_lower in event.organizer.name.lower():
            base_score += 0.10

        for attendee in event.attendees:
            if query_lower in attendee.name.lower():
                base_score += 0.05
                break

        # Location match bonus
        if event.location and query_lower in event.location.lower():
            base_score += 0.05

        # Recency factor
        now = datetime.now(timezone.utc)
        if event.start_date:
            # Ensure we compare timezone-aware datetimes
            start = event.start_date
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)

            days_diff = abs((now - start).days)
            if days_diff <= 7:
                base_score += 0.05
            elif days_diff <= 30:
                base_score += 0.02
            # Older events get slight penalty
            elif days_diff > 90:
                base_score -= 0.05

        # Cap at 0.95
        return min(max(base_score, 0.0), 0.95)
