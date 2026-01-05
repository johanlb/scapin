"""
Search API Models

Pydantic models for global search across all content types.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SearchResultType(str, Enum):
    """Types of searchable content"""

    NOTE = "note"
    EMAIL = "email"
    CALENDAR = "calendar"
    TEAMS = "teams"


class SearchResultBase(BaseModel):
    """Base class for search results"""

    id: str = Field(..., description="Item identifier")
    type: SearchResultType = Field(..., description="Result type")
    title: str = Field(..., description="Title or subject")
    excerpt: str = Field(..., description="Content excerpt with highlights")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    timestamp: datetime = Field(..., description="Item timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Type-specific metadata")


class NoteSearchResultItem(SearchResultBase):
    """Search result for a note"""

    type: SearchResultType = Field(default=SearchResultType.NOTE)
    path: str = Field("", description="Folder path")
    tags: list[str] = Field(default_factory=list, description="Tags")


class EmailSearchResultItem(SearchResultBase):
    """Search result for an email"""

    type: SearchResultType = Field(default=SearchResultType.EMAIL)
    from_address: str = Field(..., description="Sender email")
    from_name: str = Field("", description="Sender name")
    status: str = Field("pending", description="Queue status")


class CalendarSearchResultItem(SearchResultBase):
    """Search result for a calendar event"""

    type: SearchResultType = Field(default=SearchResultType.CALENDAR)
    start: datetime = Field(..., description="Event start time")
    end: datetime = Field(..., description="Event end time")
    location: str = Field("", description="Event location")
    organizer: str = Field("", description="Event organizer")


class TeamsSearchResultItem(SearchResultBase):
    """Search result for a Teams message"""

    type: SearchResultType = Field(default=SearchResultType.TEAMS)
    chat_id: str = Field(..., description="Chat ID")
    sender: str = Field(..., description="Message sender")


class SearchResultsByType(BaseModel):
    """Search results grouped by type"""

    notes: list[NoteSearchResultItem] = Field(
        default_factory=list, description="Matching notes"
    )
    emails: list[EmailSearchResultItem] = Field(
        default_factory=list, description="Matching emails"
    )
    calendar: list[CalendarSearchResultItem] = Field(
        default_factory=list, description="Matching calendar events"
    )
    teams: list[TeamsSearchResultItem] = Field(
        default_factory=list, description="Matching Teams messages"
    )


class SearchResultCounts(BaseModel):
    """Count of results by type"""

    notes: int = Field(0, description="Number of matching notes")
    emails: int = Field(0, description="Number of matching emails")
    calendar: int = Field(0, description="Number of matching calendar events")
    teams: int = Field(0, description="Number of matching Teams messages")


class GlobalSearchResponse(BaseModel):
    """Global search response with results from all types"""

    query: str = Field(..., description="Original search query")
    results: SearchResultsByType = Field(
        default_factory=SearchResultsByType, description="Results grouped by type"
    )
    total: int = Field(0, description="Total number of results")
    counts: SearchResultCounts = Field(
        default_factory=SearchResultCounts, description="Result counts by type"
    )
    search_time_ms: float = Field(0, description="Search execution time in milliseconds")


class RecentSearchItem(BaseModel):
    """A recent search query"""

    query: str = Field(..., description="Search query")
    timestamp: datetime = Field(..., description="When search was performed")
    result_count: int = Field(0, description="Number of results returned")


class RecentSearchesResponse(BaseModel):
    """Response containing recent searches"""

    searches: list[RecentSearchItem] = Field(
        default_factory=list, description="Recent search queries"
    )
    total: int = Field(0, description="Total number of recent searches")
