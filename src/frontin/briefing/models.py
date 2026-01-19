"""
Briefing Models

Data models for morning and pre-meeting briefings.
Provides structured representations of aggregated information from
multiple sources (Email, Calendar, Teams).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from src.core.events import EventSource, PerceivedEvent


@dataclass(frozen=True)
class BriefingItem:
    """
    Item in a briefing with enriched context

    Wraps a PerceivedEvent with additional briefing-specific metadata
    like priority ranking and human-readable time context.

    Attributes:
        event: The underlying PerceivedEvent
        priority_rank: Priority ranking (1 = highest)
        time_context: Human-readable time context (e.g., "In 30 min", "2h ago")
        action_summary: AI-generated summary if action is required
        confidence: Perception confidence score (0.0-1.0)
    """

    event: PerceivedEvent
    priority_rank: int
    time_context: str
    action_summary: Optional[str] = None
    confidence: float = 0.9

    def __post_init__(self) -> None:
        """Validate BriefingItem fields"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        if self.priority_rank < 1:
            raise ValueError(f"priority_rank must be >= 1, got {self.priority_rank}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event.event_id,
            "title": self.event.title,
            "source": self.event.source.value,
            "priority_rank": self.priority_rank,
            "time_context": self.time_context,
            "action_summary": self.action_summary,
            "confidence": self.confidence,
            "urgency": self.event.urgency.value,
            "from_person": self.event.from_person,
        }


@dataclass
class MorningBriefing:
    """
    Morning briefing aggregating all sources

    Provides a structured overview of the day ahead, including:
    - Urgent items requiring immediate attention
    - Today's calendar events
    - Pending emails
    - Unread Teams messages

    Designed for multi-layer display:
    - Layer 1 (5s): Quick stats overview
    - Layer 2 (2min): Detailed item lists
    - Layer 3 (optional): Full details and AI reasoning

    Attributes:
        date: The date this briefing is for
        generated_at: When this briefing was generated
        urgent_items: Items requiring immediate attention
        calendar_today: Today's calendar events
        emails_pending: Pending emails requiring action
        teams_unread: Unread Teams messages
        ai_summary: AI-generated 2-3 sentence summary
        key_decisions: Key decisions to be made today
        total_items: Total count of all items
        urgent_count: Count of urgent items
        meetings_today: Number of meetings today
    """

    date: date
    generated_at: datetime

    # Urgent items (next 3h or HIGH/CRITICAL urgency)
    urgent_items: list[BriefingItem] = field(default_factory=list)

    # Standard items by source
    calendar_today: list[BriefingItem] = field(default_factory=list)
    emails_pending: list[BriefingItem] = field(default_factory=list)
    teams_unread: list[BriefingItem] = field(default_factory=list)

    # AI-generated insights
    ai_summary: Optional[str] = None
    key_decisions: list[str] = field(default_factory=list)

    # Statistics
    total_items: int = 0
    urgent_count: int = 0
    meetings_today: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "date": self.date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "urgent_items": [item.to_dict() for item in self.urgent_items],
            "calendar_today": [item.to_dict() for item in self.calendar_today],
            "emails_pending": [item.to_dict() for item in self.emails_pending],
            "teams_unread": [item.to_dict() for item in self.teams_unread],
            "ai_summary": self.ai_summary,
            "key_decisions": self.key_decisions,
            "total_items": self.total_items,
            "urgent_count": self.urgent_count,
            "meetings_today": self.meetings_today,
        }

    def to_markdown(self) -> str:
        """
        Convert to Markdown format for export

        Returns:
            Markdown-formatted string representation of the briefing
        """
        lines = [
            f"# Morning Briefing - {self.date.strftime('%A, %B %d, %Y')}",
            "",
            f"*Generated at {self.generated_at.strftime('%H:%M')}*",
            "",
            "## Quick Overview",
            "",
            f"- **Urgent items**: {self.urgent_count}",
            f"- **Meetings today**: {self.meetings_today}",
            f"- **Pending emails**: {len(self.emails_pending)}",
            f"- **Unread Teams**: {len(self.teams_unread)}",
            "",
        ]

        # AI Summary
        if self.ai_summary:
            lines.extend([
                "## Summary",
                "",
                self.ai_summary,
                "",
            ])

        # Urgent items
        if self.urgent_items:
            lines.extend([
                "## Urgent Items",
                "",
            ])
            for item in self.urgent_items:
                source_icon = _get_source_icon(item.event.source)
                lines.append(
                    f"- {source_icon} **{item.time_context}**: {item.event.title}"
                )
            lines.append("")

        # Calendar
        if self.calendar_today:
            lines.extend([
                "## Today's Schedule",
                "",
            ])
            for item in self.calendar_today:
                duration = item.event.metadata.get("duration_minutes", 0)
                dur_str = _format_duration(duration)
                lines.append(
                    f"- **{item.time_context}** ({dur_str}): {item.event.title}"
                )
            lines.append("")

        # Emails
        if self.emails_pending:
            lines.extend([
                "## Pending Emails",
                "",
            ])
            for item in self.emails_pending:
                from_name = _extract_display_name(item.event.from_person)
                lines.append(f"- [{item.time_context}] **{from_name}**: {item.event.title}")
            lines.append("")

        # Teams
        if self.teams_unread:
            lines.extend([
                "## Unread Teams",
                "",
            ])
            for item in self.teams_unread:
                from_name = _extract_display_name(item.event.from_person)
                lines.append(f"- [{item.time_context}] **{from_name}**: {item.event.title}")
            lines.append("")

        # Key decisions
        if self.key_decisions:
            lines.extend([
                "## Key Decisions Today",
                "",
            ])
            for decision in self.key_decisions:
                lines.append(f"- {decision}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class AttendeeContext:
    """
    Context about a meeting attendee

    Provides relationship context for pre-meeting preparation,
    including interaction history and relationship indicators.

    Attributes:
        name: Attendee display name
        email: Attendee email address
        is_organizer: Whether this attendee is the meeting organizer
        last_interaction: When we last communicated with this person
        interaction_count: Number of interactions in the last 30 days
        relationship_hint: Human-readable relationship description
    """

    name: str
    email: str
    is_organizer: bool = False
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    relationship_hint: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "email": self.email,
            "is_organizer": self.is_organizer,
            "last_interaction": (
                self.last_interaction.isoformat() if self.last_interaction else None
            ),
            "interaction_count": self.interaction_count,
            "relationship_hint": self.relationship_hint,
        }


@dataclass
class PreMeetingBriefing:
    """
    Pre-meeting briefing with context

    Provides comprehensive context for an upcoming meeting, including:
    - Attendee information and relationship context
    - Recent communications with attendees
    - AI-generated talking points
    - Open action items

    Attributes:
        event: The calendar event for this meeting
        generated_at: When this briefing was generated
        minutes_until_start: Minutes until the meeting starts
        attendees: List of attendees with context
        recent_emails: Recent email communications with attendees
        recent_teams: Recent Teams messages with attendees
        meeting_url: Online meeting URL if available
        location: Physical location if applicable
        talking_points: AI-generated suggested talking points
        open_items: Open action items related to attendees
    """

    event: PerceivedEvent
    generated_at: datetime
    minutes_until_start: int

    # Attendee context
    attendees: list[AttendeeContext] = field(default_factory=list)

    # Related communications
    recent_emails: list[PerceivedEvent] = field(default_factory=list)
    recent_teams: list[PerceivedEvent] = field(default_factory=list)

    # Meeting details
    meeting_url: Optional[str] = None
    location: Optional[str] = None

    # AI-generated insights
    talking_points: list[str] = field(default_factory=list)
    open_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event.event_id,
            "event_title": self.event.title,
            "generated_at": self.generated_at.isoformat(),
            "minutes_until_start": self.minutes_until_start,
            "attendees": [att.to_dict() for att in self.attendees],
            "recent_emails_count": len(self.recent_emails),
            "recent_teams_count": len(self.recent_teams),
            "meeting_url": self.meeting_url,
            "location": self.location,
            "talking_points": self.talking_points,
            "open_items": self.open_items,
        }

    def to_markdown(self) -> str:
        """
        Convert to Markdown format for export

        Returns:
            Markdown-formatted string representation of the briefing
        """
        lines = [
            f"# Pre-Meeting Briefing: {self.event.title}",
            "",
            f"*Generated at {self.generated_at.strftime('%H:%M')}*",
            "",
        ]

        # Time until start
        if self.minutes_until_start > 0:
            lines.append(f"**Starts in {self.minutes_until_start} minutes**")
        else:
            lines.append("**Meeting in progress or starting now**")
        lines.append("")

        # Meeting details
        if self.meeting_url or self.location:
            lines.append("## Meeting Details")
            lines.append("")
            if self.meeting_url:
                lines.append(f"- **Join**: {self.meeting_url}")
            if self.location:
                lines.append(f"- **Location**: {self.location}")
            lines.append("")

        # Attendees
        if self.attendees:
            lines.append("## Attendees")
            lines.append("")
            for att in self.attendees:
                organizer_badge = " (organizer)" if att.is_organizer else ""
                hint = f" - {att.relationship_hint}" if att.relationship_hint else ""
                lines.append(f"- **{att.name}**{organizer_badge}{hint}")
            lines.append("")

        # Recent context
        if self.recent_emails or self.recent_teams:
            lines.append("## Recent Communications")
            lines.append("")
            if self.recent_emails:
                lines.append(f"- {len(self.recent_emails)} recent emails")
            if self.recent_teams:
                lines.append(f"- {len(self.recent_teams)} recent Teams messages")
            lines.append("")

        # Talking points
        if self.talking_points:
            lines.append("## Talking Points")
            lines.append("")
            for point in self.talking_points:
                lines.append(f"- {point}")
            lines.append("")

        # Open items
        if self.open_items:
            lines.append("## Open Items")
            lines.append("")
            for item in self.open_items:
                lines.append(f"- [ ] {item}")
            lines.append("")

        return "\n".join(lines)


def _get_source_icon(source: EventSource) -> str:
    """Get icon for event source (for Markdown export)"""
    icons = {
        EventSource.EMAIL: "[Email]",
        EventSource.CALENDAR: "[Cal]",
        EventSource.TEAMS: "[Teams]",
        EventSource.FILE: "[File]",
        EventSource.TASK: "[Task]",
    }
    return icons.get(source, "[?]")


def _extract_display_name(from_person: str) -> str:
    """Extract display name from a person string, handling empty/None values"""
    if not from_person:
        return "Unknown"
    # Extract name before email (e.g., "John Doe <john@example.com>" -> "John Doe")
    name = from_person.split("<")[0].strip()
    if name:
        return name
    # No name before <, check if it's just an email without brackets
    stripped = from_person.strip()
    if stripped.startswith("<"):
        # Only email in brackets like "<john@example.com>" - no display name
        return "Unknown"
    # Plain email or other format
    return stripped or "Unknown"


def _format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable string"""
    if minutes <= 0:
        return "-"
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining_mins = minutes % 60
    if remaining_mins == 0:
        return f"{hours}h"
    return f"{hours}h{remaining_mins:02d}m"
