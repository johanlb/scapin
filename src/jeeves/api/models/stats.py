"""
Stats API Models

Pydantic models for aggregated statistics endpoints.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.jeeves.api.models.calendar import CalendarStatsResponse
from src.jeeves.api.models.email import EmailStatsResponse
from src.jeeves.api.models.notes import ReviewStatsResponse
from src.jeeves.api.models.queue import QueueStatsResponse
from src.jeeves.api.models.teams import TeamsStatsResponse


class TrendDataPoint(BaseModel):
    """A single data point in a trend"""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: int = Field(0, description="Value for this date")


class SourceTrend(BaseModel):
    """Trend data for a single source"""

    source: str = Field(..., description="Source identifier")
    label: str = Field(..., description="Display label")
    color: str = Field(..., description="Color for chart")
    data: list[TrendDataPoint] = Field(default_factory=list, description="Data points")
    total: int = Field(0, description="Total over the period")


class StatsTrendsResponse(BaseModel):
    """Historical trends data for charts"""

    period: Literal["7d", "30d"] = Field(..., description="Time period")
    start_date: str = Field(..., description="Start date of period")
    end_date: str = Field(..., description="End date of period")
    trends: list[SourceTrend] = Field(default_factory=list, description="Trends by source")
    total_processed: int = Field(0, description="Total items processed in period")


class StatsOverviewResponse(BaseModel):
    """Aggregated overview statistics"""

    # Totals across all sources
    total_processed: int = Field(0, description="Total items processed across all sources")
    total_pending: int = Field(0, description="Total items pending across all sources")
    sources_active: int = Field(0, description="Number of active/enabled sources")

    # System info
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    last_activity: datetime | None = Field(None, description="Most recent activity timestamp")

    # Quick summary per source
    email_processed: int = Field(0, description="Emails processed")
    email_queued: int = Field(0, description="Emails in queue")
    teams_messages: int = Field(0, description="Teams messages processed")
    teams_unread: int = Field(0, description="Teams chats with unread messages")
    calendar_events_today: int = Field(0, description="Calendar events today")
    calendar_events_week: int = Field(0, description="Calendar events this week")
    notes_due: int = Field(0, description="Notes due for review")
    notes_reviewed_today: int = Field(0, description="Notes reviewed today")


class StatsBySourceResponse(BaseModel):
    """Detailed statistics per source"""

    email: EmailStatsResponse | None = Field(None, description="Email statistics")
    teams: TeamsStatsResponse | None = Field(None, description="Teams statistics")
    calendar: CalendarStatsResponse | None = Field(None, description="Calendar statistics")
    queue: QueueStatsResponse | None = Field(None, description="Queue statistics")
    notes: ReviewStatsResponse | None = Field(None, description="Notes review statistics")
