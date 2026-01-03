"""
API Response Models

Pydantic models for all API responses.
Provides type safety and automatic OpenAPI documentation.
"""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper

    All API endpoints return this structure for consistency.
    """

    success: bool = Field(..., description="Whether the request succeeded")
    data: T | None = Field(None, description="Response data")
    error: str | None = Field(None, description="Error message if failed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp (UTC)",
    )


class PaginatedResponse(APIResponse[T], Generic[T]):
    """Paginated response with metadata"""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")


class HealthCheckResult(BaseModel):
    """Individual health check result"""

    name: str = Field(..., description="Check name")
    status: str = Field(..., description="Check status: ok, warning, error")
    message: str | None = Field(None, description="Status message")
    latency_ms: float | None = Field(None, description="Check latency in ms")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Overall status: healthy, degraded, unhealthy")
    checks: list[HealthCheckResult] = Field(
        default_factory=list,
        description="Individual check results",
    )
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    version: str = Field(..., description="API version")


class StatsResponse(BaseModel):
    """System statistics response"""

    emails_processed: int = Field(0, description="Total emails processed")
    teams_messages: int = Field(0, description="Total Teams messages processed")
    calendar_events: int = Field(0, description="Total calendar events processed")
    queue_size: int = Field(0, description="Current queue size")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    last_activity: datetime | None = Field(None, description="Last processing activity")


class BriefingItemResponse(BaseModel):
    """Briefing item in response"""

    event_id: str
    title: str
    source: str
    priority_rank: int
    time_context: str
    action_summary: str | None = None
    confidence: float
    urgency: str
    from_person: str | None = None


class BriefingResponse(BaseModel):
    """Morning briefing response"""

    date: str = Field(..., description="Briefing date (ISO format)")
    generated_at: str = Field(..., description="Generation timestamp")
    urgent_count: int = Field(..., description="Number of urgent items")
    meetings_today: int = Field(..., description="Number of meetings today")
    total_items: int = Field(..., description="Total number of items")
    urgent_items: list[BriefingItemResponse] = Field(
        default_factory=list,
        description="Urgent items requiring attention",
    )
    calendar_today: list[BriefingItemResponse] = Field(
        default_factory=list,
        description="Today's calendar events",
    )
    emails_pending: list[BriefingItemResponse] = Field(
        default_factory=list,
        description="Pending emails",
    )
    teams_unread: list[BriefingItemResponse] = Field(
        default_factory=list,
        description="Unread Teams messages",
    )
    ai_summary: str | None = Field(None, description="AI-generated summary")
    key_decisions: list[str] = Field(
        default_factory=list,
        description="Key decisions for today",
    )


class AttendeeResponse(BaseModel):
    """Meeting attendee in response"""

    name: str
    email: str
    is_organizer: bool = False
    interaction_count: int = 0
    relationship_hint: str | None = None


class PreMeetingBriefingResponse(BaseModel):
    """Pre-meeting briefing response"""

    event_id: str = Field(..., description="Calendar event ID")
    event_title: str = Field(..., description="Meeting title")
    generated_at: str = Field(..., description="Generation timestamp")
    minutes_until_start: int = Field(..., description="Minutes until meeting starts")
    attendees: list[AttendeeResponse] = Field(
        default_factory=list,
        description="Meeting attendees with context",
    )
    recent_emails_count: int = Field(0, description="Recent emails with attendees")
    recent_teams_count: int = Field(0, description="Recent Teams messages with attendees")
    meeting_url: str | None = Field(None, description="Online meeting URL")
    location: str | None = Field(None, description="Physical location")
    talking_points: list[str] = Field(
        default_factory=list,
        description="Suggested talking points",
    )
    open_items: list[str] = Field(
        default_factory=list,
        description="Open action items",
    )


class ConfigResponse(BaseModel):
    """Configuration response (with masked secrets)"""

    email_accounts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Configured email accounts",
    )
    ai_model: str = Field(..., description="AI model in use")
    teams_enabled: bool = Field(False, description="Teams integration enabled")
    calendar_enabled: bool = Field(False, description="Calendar integration enabled")
    briefing_enabled: bool = Field(False, description="Briefing system enabled")
