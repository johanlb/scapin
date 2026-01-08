"""
iCloud Calendar Data Models

Models for representing Apple Calendar/iCloud Calendar data in Scapin.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ICloudEventStatus(str, Enum):
    """Status of a calendar event"""

    NONE = "none"
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class ICloudAttendeeStatus(str, Enum):
    """Participation status of an attendee"""

    UNKNOWN = "unknown"
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"


@dataclass
class ICloudAttendee:
    """Represents an attendee of a calendar event"""

    name: str
    email: str = ""
    status: ICloudAttendeeStatus = ICloudAttendeeStatus.UNKNOWN
    is_organizer: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "email": self.email,
            "status": self.status.value,
            "is_organizer": self.is_organizer,
        }


@dataclass
class ICloudCalendar:
    """Represents an iCloud Calendar"""

    name: str
    uid: str = ""
    color: str = ""
    is_writable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "uid": self.uid,
            "color": self.color,
            "is_writable": self.is_writable,
        }


@dataclass
class ICloudCalendarEvent:
    """
    Represents a calendar event from Apple Calendar/iCloud.

    Attributes:
        uid: Unique identifier for the event
        summary: Title/subject of the event
        description: Description or notes
        location: Location string
        start_date: Start date and time
        end_date: End date and time
        is_all_day: Whether this is an all-day event
        calendar_name: Name of the calendar containing this event
        status: Event status (confirmed, tentative, cancelled)
        url: URL associated with the event
        attendees: List of attendees
        organizer: Organizer of the event
        recurrence_rule: Recurrence rule if recurring
        created_at: When the event was created
        modified_at: When the event was last modified
    """

    uid: str
    summary: str
    start_date: datetime
    end_date: datetime
    calendar_name: str = ""
    description: str = ""
    location: str = ""
    is_all_day: bool = False
    status: ICloudEventStatus = ICloudEventStatus.CONFIRMED
    url: str = ""
    attendees: list[ICloudAttendee] = field(default_factory=list)
    organizer: ICloudAttendee | None = None
    recurrence_rule: str = ""
    created_at: datetime | None = None
    modified_at: datetime | None = None

    @property
    def duration_minutes(self) -> int:
        """Get event duration in minutes"""
        if self.is_all_day:
            return 24 * 60
        delta = self.end_date - self.start_date
        return int(delta.total_seconds() / 60)

    @property
    def is_past(self) -> bool:
        """Check if event has ended"""
        now = datetime.now(timezone.utc)
        end = self.end_date
        if end.tzinfo is None:
            # Assume local time, compare naively
            now = datetime.now()
        return end < now

    @property
    def is_online_meeting(self) -> bool:
        """Check if this appears to be an online meeting"""
        online_keywords = ["zoom", "teams", "meet", "webex", "skype", "facetime"]
        searchable = f"{self.location} {self.description} {self.url}".lower()
        return any(kw in searchable for kw in online_keywords)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "uid": self.uid,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_all_day": self.is_all_day,
            "calendar_name": self.calendar_name,
            "status": self.status.value,
            "url": self.url,
            "attendees": [a.to_dict() for a in self.attendees],
            "organizer": self.organizer.to_dict() if self.organizer else None,
            "recurrence_rule": self.recurrence_rule,
            "duration_minutes": self.duration_minutes,
            "is_past": self.is_past,
            "is_online_meeting": self.is_online_meeting,
        }


@dataclass
class ICloudCalendarSearchResult:
    """Result from searching iCloud Calendar"""

    events: list[ICloudCalendarEvent] = field(default_factory=list)
    calendars_searched: list[str] = field(default_factory=list)
    total_found: int = 0
    query: str = ""
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
