"""
Calendar API Models

Pydantic models for calendar API requests and responses.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConflictType(str, Enum):
    """Type of calendar conflict"""

    OVERLAP_FULL = "overlap_full"  # One event fully contains another
    OVERLAP_PARTIAL = "overlap_partial"  # Events partially overlap
    TRAVEL_TIME = "travel_time"  # Insufficient time between different locations


class ConflictSeverity(str, Enum):
    """Severity level of a conflict"""

    HIGH = "high"  # Full overlap - can't attend both
    MEDIUM = "medium"  # Partial overlap - may miss part
    LOW = "low"  # Travel time warning


class CalendarConflict(BaseModel):
    """Represents a conflict between two calendar events"""

    conflict_type: ConflictType = Field(..., description="Type of conflict")
    severity: ConflictSeverity = Field(..., description="Conflict severity")
    conflicting_event_id: str = Field(..., description="ID of the conflicting event")
    conflicting_title: str = Field(..., description="Title of the conflicting event")
    conflicting_start: datetime = Field(..., description="Start time of conflicting event")
    conflicting_end: datetime = Field(..., description="End time of conflicting event")
    overlap_minutes: int = Field(0, description="Minutes of overlap (for overlap conflicts)")
    gap_minutes: int = Field(0, description="Gap in minutes (for travel time conflicts)")
    message: str = Field(..., description="Human-readable conflict description")


class CalendarAttendeeResponse(BaseModel):
    """Meeting attendee"""

    email: str = Field(..., description="Attendee email")
    name: str | None = Field(None, description="Attendee name")
    response_status: str = Field("none", description="Response: accepted, declined, tentative, none")
    is_organizer: bool = Field(False, description="Whether attendee is organizer")


class CalendarEventResponse(BaseModel):
    """Calendar event in response"""

    id: str = Field(..., description="Event ID")
    title: str = Field(..., description="Event title")
    start: datetime = Field(..., description="Start time")
    end: datetime = Field(..., description="End time")
    location: str | None = Field(None, description="Event location")
    is_online: bool = Field(False, description="Whether event is online meeting")
    meeting_url: str | None = Field(None, description="Online meeting URL")
    organizer: str | None = Field(None, description="Organizer email")
    attendees: list[CalendarAttendeeResponse] = Field(
        default_factory=list,
        description="Event attendees",
    )
    is_all_day: bool = Field(False, description="Whether event is all-day")
    is_recurring: bool = Field(False, description="Whether event is recurring")
    description: str | None = Field(None, description="Event description/notes")
    status: str = Field("confirmed", description="Event status")


class CalendarStatsResponse(BaseModel):
    """Calendar statistics"""

    events_today: int = Field(0, description="Events today")
    events_week: int = Field(0, description="Events this week")
    meetings_online: int = Field(0, description="Online meetings")
    meetings_in_person: int = Field(0, description="In-person meetings")
    last_poll: datetime | None = Field(None, description="Last poll timestamp")


class CalendarPollResponse(BaseModel):
    """Calendar poll result"""

    events_fetched: int = Field(..., description="Events fetched")
    events_new: int = Field(0, description="New events since last poll")
    events_updated: int = Field(0, description="Updated events")
    polled_at: datetime = Field(..., description="Poll timestamp")


class RespondToEventRequest(BaseModel):
    """Request to respond to an event invitation"""

    response: str = Field(
        ...,
        description="Response: accept, decline, tentative",
    )
    message: str | None = Field(None, description="Optional message to organizer")


class TodayEventsResponse(BaseModel):
    """Today's calendar events"""

    date: str = Field(..., description="Date (ISO format)")
    total_events: int = Field(..., description="Total events today")
    meetings: int = Field(0, description="Meeting count")
    all_day_events: int = Field(0, description="All-day event count")
    events: list[CalendarEventResponse] = Field(
        default_factory=list,
        description="Today's events",
    )
