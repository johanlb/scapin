"""
Microsoft Calendar Models

Dataclasses for Calendar events, attendees, and related entities.
All models are frozen (immutable) for thread safety.
"""

import html
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional


class CalendarResponseStatus(str, Enum):
    """Response status for a calendar event"""

    NONE = "none"
    ORGANIZER = "organizer"
    TENTATIVELY_ACCEPTED = "tentativelyAccepted"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    NOT_RESPONDED = "notResponded"


class CalendarEventImportance(str, Enum):
    """Importance level of a calendar event"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class CalendarEventSensitivity(str, Enum):
    """Sensitivity/privacy level of a calendar event"""

    NORMAL = "normal"
    PERSONAL = "personal"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class CalendarEventShowAs(str, Enum):
    """Show-as status for a calendar event"""

    FREE = "free"
    TENTATIVE = "tentative"
    BUSY = "busy"
    OOF = "oof"  # Out of office
    WORKING_ELSEWHERE = "workingElsewhere"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CalendarAttendee:
    """
    Attendee of a calendar event

    Represents a participant in a meeting or event.
    """

    email: str
    display_name: str
    response_status: CalendarResponseStatus
    attendee_type: str = "required"  # required, optional, resource
    is_organizer: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "email": self.email,
            "display_name": self.display_name,
            "response_status": self.response_status.value,
            "attendee_type": self.attendee_type,
            "is_organizer": self.is_organizer,
        }

    @classmethod
    def from_api(cls, data: dict[str, Any], is_organizer: bool = False) -> "CalendarAttendee":
        """Create from Graph API response"""
        email_address = data.get("emailAddress", {})
        status_data = data.get("status", {})

        response_str = status_data.get("response", "none")
        try:
            response_status = CalendarResponseStatus(response_str)
        except ValueError:
            response_status = CalendarResponseStatus.NONE

        return cls(
            email=email_address.get("address", ""),
            display_name=email_address.get("name", "Unknown"),
            response_status=response_status,
            attendee_type=data.get("type", "required"),
            is_organizer=is_organizer,
        )


@dataclass(frozen=True)
class CalendarLocation:
    """
    Location of a calendar event

    Can be physical address or online meeting info.
    """

    display_name: str
    location_type: str = "default"  # default, conferenceRoom, homeAddress, etc.
    address: Optional[str] = None
    coordinates: Optional[tuple[float, float]] = None  # (latitude, longitude)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        result: dict[str, Any] = {
            "display_name": self.display_name,
            "location_type": self.location_type,
        }
        if self.address:
            result["address"] = self.address
        if self.coordinates:
            result["coordinates"] = {"latitude": self.coordinates[0], "longitude": self.coordinates[1]}
        return result

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Optional["CalendarLocation"]:
        """Create from Graph API response"""
        if not data:
            return None

        display_name = data.get("displayName", "")
        if not display_name:
            return None

        # Parse address if available
        address_data = data.get("address", {})
        address = None
        if address_data:
            parts = [
                address_data.get("street", ""),
                address_data.get("city", ""),
                address_data.get("state", ""),
                address_data.get("countryOrRegion", ""),
            ]
            address = ", ".join(p for p in parts if p)

        # Parse coordinates if available
        coords_data = data.get("coordinates", {})
        coordinates = None
        if coords_data and "latitude" in coords_data and "longitude" in coords_data:
            coordinates = (coords_data["latitude"], coords_data["longitude"])

        return cls(
            display_name=display_name,
            location_type=data.get("locationType", "default"),
            address=address if address else None,
            coordinates=coordinates,
        )


@dataclass(frozen=True)
class CalendarEvent:
    """
    Calendar event

    Represents a meeting, appointment, or all-day event.
    """

    event_id: str
    calendar_id: str
    subject: str
    body_preview: str
    body_content: str

    # Timing
    start: datetime
    end: datetime
    timezone: str
    is_all_day: bool

    # Participants
    organizer: CalendarAttendee
    attendees: tuple[CalendarAttendee, ...]

    # Metadata
    location: Optional[CalendarLocation] = None
    categories: tuple[str, ...] = ()
    importance: CalendarEventImportance = CalendarEventImportance.NORMAL
    sensitivity: CalendarEventSensitivity = CalendarEventSensitivity.NORMAL
    show_as: CalendarEventShowAs = CalendarEventShowAs.BUSY

    # Online meeting
    is_online_meeting: bool = False
    online_meeting_url: Optional[str] = None
    online_meeting_provider: Optional[str] = None  # teamsForBusiness, skypeForBusiness, etc.

    # Reminders
    is_reminder_on: bool = True
    reminder_minutes: int = 15

    # Response and status
    response_status: CalendarResponseStatus = CalendarResponseStatus.NONE
    is_cancelled: bool = False

    # Recurrence
    is_recurring: bool = False
    series_master_id: Optional[str] = None

    # Web link
    web_link: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate event"""
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.calendar_id:
            raise ValueError("calendar_id is required")

    @property
    def duration_minutes(self) -> int:
        """Duration in minutes"""
        return int((self.end - self.start).total_seconds() / 60)

    @property
    def duration(self) -> timedelta:
        """Duration as timedelta"""
        return self.end - self.start

    @property
    def is_meeting(self) -> bool:
        """True if this is a meeting (has attendees besides organizer)"""
        return len(self.attendees) > 0

    @property
    def is_past(self) -> bool:
        """True if event has ended"""
        return self.end < datetime.now(timezone.utc)

    @property
    def is_in_progress(self) -> bool:
        """True if event is currently happening"""
        now = datetime.now(timezone.utc)
        return self.start <= now <= self.end

    @property
    def is_upcoming(self) -> bool:
        """True if event hasn't started yet"""
        return self.start > datetime.now(timezone.utc)

    @property
    def minutes_until_start(self) -> int:
        """Minutes until event starts (negative if already started)"""
        delta = self.start - datetime.now(timezone.utc)
        return int(delta.total_seconds() / 60)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "calendar_id": self.calendar_id,
            "subject": self.subject,
            "body_preview": self.body_preview,
            "body_content": self.body_content,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "timezone": self.timezone,
            "is_all_day": self.is_all_day,
            "organizer": self.organizer.to_dict(),
            "attendees": [a.to_dict() for a in self.attendees],
            "location": self.location.to_dict() if self.location else None,
            "categories": list(self.categories),
            "importance": self.importance.value,
            "sensitivity": self.sensitivity.value,
            "show_as": self.show_as.value,
            "is_online_meeting": self.is_online_meeting,
            "online_meeting_url": self.online_meeting_url,
            "online_meeting_provider": self.online_meeting_provider,
            "is_reminder_on": self.is_reminder_on,
            "reminder_minutes": self.reminder_minutes,
            "response_status": self.response_status.value,
            "is_cancelled": self.is_cancelled,
            "is_recurring": self.is_recurring,
            "series_master_id": self.series_master_id,
            "web_link": self.web_link,
            "duration_minutes": self.duration_minutes,
            "is_meeting": self.is_meeting,
        }

    @classmethod
    def from_api(cls, data: dict[str, Any], calendar_id: str) -> "CalendarEvent":
        """
        Create from Graph API response

        Args:
            data: Graph API event response
            calendar_id: ID of the calendar this event belongs to

        Returns:
            CalendarEvent instance
        """
        # Parse subject
        subject = data.get("subject", "(No subject)")

        # Parse body
        body_data = data.get("body") or {}
        body_content_html = body_data.get("content", "")
        body_preview = data.get("bodyPreview", "")

        # Extract plain text from HTML
        body_content_plain = _extract_plain_text(body_content_html)

        # Parse start/end datetime
        start_data = data.get("start", {})
        end_data = data.get("end", {})

        start_str = start_data.get("dateTime", "")
        end_str = end_data.get("dateTime", "")
        tz = start_data.get("timeZone", "UTC")

        # Parse datetime (Graph API returns ISO format without Z)
        if start_str:
            # Handle both with and without timezone info
            if "Z" in start_str or "+" in start_str:
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            else:
                start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        else:
            start = datetime.now(timezone.utc)

        if end_str:
            if "Z" in end_str or "+" in end_str:
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            else:
                end = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        else:
            end = start + timedelta(hours=1)

        # Parse is_all_day
        is_all_day = data.get("isAllDay", False)

        # Parse organizer
        organizer_data = data.get("organizer", {})
        organizer_email = organizer_data.get("emailAddress", {})
        organizer = CalendarAttendee(
            email=organizer_email.get("address", ""),
            display_name=organizer_email.get("name", "Unknown"),
            response_status=CalendarResponseStatus.ORGANIZER,
            attendee_type="required",
            is_organizer=True,
        )

        # Parse attendees
        attendees_data = data.get("attendees", [])
        attendees = tuple(
            CalendarAttendee.from_api(a)
            for a in attendees_data
            # Exclude organizer from attendees list
            if a.get("emailAddress", {}).get("address") != organizer.email
        )

        # Parse location
        location_data = data.get("location")
        location = CalendarLocation.from_api(location_data) if location_data else None

        # Parse categories
        categories = tuple(data.get("categories", []))

        # Parse importance
        importance_str = data.get("importance", "normal")
        try:
            importance = CalendarEventImportance(importance_str)
        except ValueError:
            importance = CalendarEventImportance.NORMAL

        # Parse sensitivity
        sensitivity_str = data.get("sensitivity", "normal")
        try:
            sensitivity = CalendarEventSensitivity(sensitivity_str)
        except ValueError:
            sensitivity = CalendarEventSensitivity.NORMAL

        # Parse showAs
        show_as_str = data.get("showAs", "busy")
        try:
            show_as = CalendarEventShowAs(show_as_str)
        except ValueError:
            show_as = CalendarEventShowAs.BUSY

        # Parse online meeting
        is_online = data.get("isOnlineMeeting", False)
        online_url = None
        online_provider = None
        if is_online:
            online_meeting = data.get("onlineMeeting", {})
            online_url = online_meeting.get("joinUrl")
            online_provider = data.get("onlineMeetingProvider")

        # Parse reminders
        is_reminder_on = data.get("isReminderOn", True)
        reminder_minutes = data.get("reminderMinutesBeforeStart", 15)

        # Parse response status
        response_status_data = data.get("responseStatus", {})
        response_str = response_status_data.get("response", "none")
        try:
            response_status = CalendarResponseStatus(response_str)
        except ValueError:
            response_status = CalendarResponseStatus.NONE

        # Parse cancelled status
        is_cancelled = data.get("isCancelled", False)

        # Parse recurrence
        is_recurring = data.get("recurrence") is not None
        series_master_id = data.get("seriesMasterId")

        # Parse web link
        web_link = data.get("webLink")

        return cls(
            event_id=data.get("id", "unknown"),
            calendar_id=calendar_id,
            subject=subject,
            body_preview=body_preview,
            body_content=body_content_plain,
            start=start,
            end=end,
            timezone=tz,
            is_all_day=is_all_day,
            organizer=organizer,
            attendees=attendees,
            location=location,
            categories=categories,
            importance=importance,
            sensitivity=sensitivity,
            show_as=show_as,
            is_online_meeting=is_online,
            online_meeting_url=online_url,
            online_meeting_provider=online_provider,
            is_reminder_on=is_reminder_on,
            reminder_minutes=reminder_minutes,
            response_status=response_status,
            is_cancelled=is_cancelled,
            is_recurring=is_recurring,
            series_master_id=series_master_id,
            web_link=web_link,
        )


def _extract_plain_text(html_content: str) -> str:
    """
    Extract plain text from HTML content

    Calendar event bodies are in HTML format. This extracts readable text.

    Args:
        html_content: HTML string from Graph API

    Returns:
        Plain text content
    """
    if not html_content:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html_content)

    # Decode HTML entities using standard library
    text = html.unescape(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text
