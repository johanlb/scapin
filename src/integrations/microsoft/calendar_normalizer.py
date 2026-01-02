"""
Calendar Event Normalizer

Converts Calendar events to the universal PerceivedEvent format
for processing by the cognitive pipeline.

Follows the same pattern as TeamsNormalizer.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.events.universal_event import (
    Entity,
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
)
from src.integrations.microsoft.calendar_models import (
    CalendarEvent,
    CalendarEventImportance,
    CalendarResponseStatus,
)
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("integrations.microsoft.calendar_normalizer")


@dataclass
class CalendarNormalizer:
    """
    Normalizes Calendar events to PerceivedEvent

    Converts CalendarEvent dataclass to the universal event format
    used by the cognitive pipeline. Follows the same pattern as
    TeamsNormalizer for consistency.

    Key differences from other normalizers:
    - Urgency is based on temporal proximity (not importance flag)
    - Event type focuses on meeting vs reminder distinction
    - Extracts online meeting URLs and locations

    Usage:
        normalizer = CalendarNormalizer()
        event = normalizer.normalize(calendar_event)
    """

    def normalize(self, event: CalendarEvent) -> PerceivedEvent:
        """
        Convert a Calendar event to a PerceivedEvent

        Args:
            event: CalendarEvent to normalize

        Returns:
            PerceivedEvent ready for cognitive processing
        """
        logger.debug(f"Normalizing Calendar event {event.event_id}")

        # Determine event type based on characteristics
        event_type = self._determine_event_type(event)

        # Determine urgency based on temporal proximity
        urgency = self._determine_urgency(event)

        # Extract entities from event
        entities = self._extract_entities(event)

        # Extract topics and keywords
        topics, keywords = self._extract_topics_and_keywords(event)

        # Build title with time prefix
        title = self._build_title(event)

        # Build content summary
        content = self._build_content(event)

        # Get organizer as from_person
        from_person = f"{event.organizer.display_name} <{event.organizer.email}>"

        # Get attendees as to_people
        to_people = [
            f"{a.display_name} <{a.email}>"
            for a in event.attendees
        ]

        # Extract URLs from event
        urls = self._extract_urls(event)

        # For timing, use now() for occurred_at since the event notification
        # was just received. The actual event start time is stored in metadata.
        # This respects the constraint: occurred_at <= received_at <= perceived_at
        current_time = now_utc()

        # Build the PerceivedEvent
        perceived_event = PerceivedEvent(
            # Identity
            event_id=f"calendar-{event.event_id}",
            source=EventSource.CALENDAR,
            source_id=event.event_id,
            # Timing - occurred_at is when we received the event, not when it starts
            occurred_at=current_time,
            received_at=current_time,
            perceived_at=current_time,
            # Content
            title=title,
            content=content,
            # Classification
            event_type=event_type,
            urgency=urgency,
            # Extracted info
            entities=entities,
            topics=topics,
            keywords=keywords,
            # Participants
            from_person=from_person,
            to_people=to_people,
            cc_people=[],
            # Context
            thread_id=event.event_id,
            references=[],
            in_reply_to=event.series_master_id,  # Link to recurring series
            # Attachments (calendar events don't have attachments in this model)
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=urls,
            # Metadata
            metadata={
                "event_id": event.event_id,
                "calendar_id": event.calendar_id,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "duration_minutes": event.duration_minutes,
                "timezone": event.timezone,
                "is_all_day": event.is_all_day,
                "is_meeting": event.is_meeting,
                "is_online": event.is_online_meeting,
                "online_url": event.online_meeting_url,
                "online_provider": event.online_meeting_provider,
                "location": event.location.display_name if event.location else None,
                "importance": event.importance.value,
                "sensitivity": event.sensitivity.value,
                "show_as": event.show_as.value,
                "response_status": event.response_status.value,
                "attendee_count": len(event.attendees),
                "categories": list(event.categories),
                "is_recurring": event.is_recurring,
                "is_cancelled": event.is_cancelled,
                "web_link": event.web_link,
            },
            # Quality
            perception_confidence=0.9,  # High confidence for structured calendar data
            needs_clarification=False,
            clarification_questions=[],
        )

        logger.debug(f"Normalized event to {perceived_event.event_id} (type={event_type.value})")
        return perceived_event

    def _determine_event_type(self, event: CalendarEvent) -> EventType:
        """
        Determine the event type based on event characteristics

        Uses heuristics based on:
        - Whether it's a meeting with attendees
        - Response status (needs response?)
        - Event importance
        - Time proximity
        """
        # Cancelled events are informational
        if event.is_cancelled:
            return EventType.INFORMATION

        # Meeting invitation that needs response
        if event.is_meeting and event.response_status == CalendarResponseStatus.NOT_RESPONDED:
            return EventType.DECISION_NEEDED

        # Meeting that was tentatively accepted may need action
        if event.is_meeting and event.response_status == CalendarResponseStatus.TENTATIVELY_ACCEPTED:
            return EventType.INVITATION

        # Accepted meeting is a reminder
        if event.is_meeting and event.response_status == CalendarResponseStatus.ACCEPTED:
            return EventType.REMINDER

        # High importance events may need action
        if event.importance == CalendarEventImportance.HIGH:
            return EventType.ACTION_REQUIRED

        # Personal events (no attendees) are reminders
        if not event.is_meeting:
            return EventType.REMINDER

        # Default: invitation for meetings, reminder for others
        return EventType.INVITATION if event.is_meeting else EventType.REMINDER

    def _determine_urgency(self, event: CalendarEvent) -> UrgencyLevel:
        """
        Determine urgency based on temporal proximity

        Unlike email/Teams where importance is explicit,
        calendar urgency is primarily time-based.
        """
        now = datetime.now(timezone.utc)

        # Past events have no urgency
        if event.is_past:
            return UrgencyLevel.NONE

        # Calculate time until event starts
        time_until = (event.start - now).total_seconds() / 3600  # in hours

        # Event in progress - depends on if needs response
        if event.is_in_progress:
            if event.response_status == CalendarResponseStatus.NOT_RESPONDED:
                return UrgencyLevel.HIGH
            return UrgencyLevel.MEDIUM

        # Within 1 hour - critical
        if time_until < 1:
            return UrgencyLevel.CRITICAL

        # Within 4 hours - high
        if time_until < 4:
            return UrgencyLevel.HIGH

        # Today (within 12 hours) - medium
        if time_until < 12:
            return UrgencyLevel.MEDIUM

        # Tomorrow (within 24 hours) - low-medium
        if time_until < 24:
            # Needs response = medium, otherwise low
            if event.response_status == CalendarResponseStatus.NOT_RESPONDED:
                return UrgencyLevel.MEDIUM
            return UrgencyLevel.LOW

        # More than 24 hours away - low
        return UrgencyLevel.LOW

    def _extract_entities(self, event: CalendarEvent) -> list[Entity]:
        """
        Extract entities from the event

        Extracts:
        - Organizer as person entity
        - Attendees as person entities
        - Location as location entity
        - Categories as topic entities
        """
        entities: list[Entity] = []

        # Organizer
        entities.append(Entity(
            type="person",
            value=event.organizer.display_name,
            confidence=0.95,
            metadata={
                "email": event.organizer.email,
                "role": "organizer",
            },
        ))

        # Attendees
        for attendee in event.attendees:
            entities.append(Entity(
                type="person",
                value=attendee.display_name,
                confidence=0.90,
                metadata={
                    "email": attendee.email,
                    "role": "attendee",
                    "type": attendee.attendee_type,
                    "response": attendee.response_status.value,
                },
            ))

        # Location
        if event.location:
            entities.append(Entity(
                type="location",
                value=event.location.display_name,
                confidence=0.85,
                metadata={
                    "type": event.location.location_type,
                    "address": event.location.address,
                },
            ))

        # Categories as topics
        for category in event.categories:
            entities.append(Entity(
                type="topic",
                value=category,
                confidence=0.80,
                metadata={"source": "calendar_category"},
            ))

        # Time-related entity
        entities.append(Entity(
            type="datetime",
            value=event.start.isoformat(),
            confidence=0.99,
            metadata={
                "end": event.end.isoformat(),
                "duration_minutes": event.duration_minutes,
                "is_all_day": event.is_all_day,
            },
        ))

        return entities

    def _extract_topics_and_keywords(
        self,
        event: CalendarEvent,
    ) -> tuple[list[str], list[str]]:
        """
        Extract topics and keywords from event content

        Uses categories as topics and extracts keywords from subject/body.
        """
        topics = list(event.categories) if event.categories else []

        # Simple keyword extraction from subject and body
        keywords: list[str] = []
        content = f"{event.subject} {event.body_preview}".lower()

        important_words = [
            "urgent", "important", "deadline", "review", "decision",
            "1:1", "one-on-one", "standup", "sync", "planning",
            "retrospective", "demo", "presentation", "interview",
            "kickoff", "wrap-up", "final", "quarterly", "monthly",
            "weekly", "daily", "status", "update", "discuss",
        ]

        for word in important_words:
            if word in content:
                keywords.append(word)

        return topics, keywords

    def _build_title(self, event: CalendarEvent) -> str:
        """
        Build a title from the event

        Includes time prefix for easy scanning.
        """
        # Format: [HH:MM] Subject or [All Day] Subject
        time_str = "All Day" if event.is_all_day else event.start.strftime("%H:%M")
        return f"[{time_str}] {event.subject}"

    def _build_content(self, event: CalendarEvent) -> str:
        """
        Build content summary for the event

        Combines key information into readable text.
        """
        parts: list[str] = []

        # Subject (in case body is empty)
        parts.append(event.subject)

        # Time info
        if event.is_all_day:
            parts.append(f"All day event on {event.start.strftime('%Y-%m-%d')}")
        else:
            parts.append(
                f"{event.start.strftime('%Y-%m-%d %H:%M')} - "
                f"{event.end.strftime('%H:%M')} ({event.duration_minutes} min)"
            )

        # Location
        if event.location:
            parts.append(f"Location: {event.location.display_name}")

        # Online meeting
        if event.is_online_meeting and event.online_meeting_url:
            parts.append(f"Online: {event.online_meeting_provider or 'Teams'}")

        # Attendees summary
        if event.attendees:
            attendee_names = [a.display_name for a in event.attendees[:5]]
            if len(event.attendees) > 5:
                attendee_names.append(f"and {len(event.attendees) - 5} others")
            parts.append(f"With: {', '.join(attendee_names)}")

        # Body preview
        if event.body_preview:
            parts.append("")
            parts.append(event.body_preview)

        return "\n".join(parts)

    def _extract_urls(self, event: CalendarEvent) -> list[str]:
        """
        Extract URLs from the event

        Includes online meeting URL and any URLs in body.
        """
        urls: list[str] = []

        # Online meeting URL
        if event.online_meeting_url:
            urls.append(event.online_meeting_url)

        # Web link to event
        if event.web_link:
            urls.append(event.web_link)

        # Extract URLs from body content
        if event.body_content:
            # Simple URL extraction
            url_pattern = r'https?://[^\s<>"\']+(?=[<"\'\s]|$)'
            found_urls = re.findall(url_pattern, event.body_content)
            urls.extend(found_urls)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls
