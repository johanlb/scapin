"""
Discussion Models

Models for conversation threads with Scapin.
Discussions can be free-form or attached to objects (notes, emails, tasks).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DiscussionType(str, Enum):
    """Type of discussion"""

    FREE = "free"  # Free-form discussion
    NOTE = "note"  # Attached to a note
    EMAIL = "email"  # Attached to an email
    TASK = "task"  # Attached to a task
    EVENT = "event"  # Attached to a calendar event


class MessageRole(str, Enum):
    """Role of message sender"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SuggestionType(str, Enum):
    """Type of contextual suggestion"""

    ACTION = "action"  # Suggested action to take
    QUESTION = "question"  # Follow-up question
    INSIGHT = "insight"  # Related insight
    REMINDER = "reminder"  # Reminder about related item


# =============================================================================
# Request Models
# =============================================================================


class DiscussionCreateRequest(BaseModel):
    """Request to create a new discussion"""

    title: Optional[str] = Field(None, max_length=200, description="Discussion title")
    discussion_type: DiscussionType = Field(
        default=DiscussionType.FREE, description="Type of discussion"
    )
    attached_to_id: Optional[str] = Field(
        None, description="ID of attached object (note_id, email_id, etc.)"
    )
    attached_to_type: Optional[str] = Field(
        None, description="Type of attached object for context"
    )
    initial_message: Optional[str] = Field(
        None, min_length=1, max_length=10000, description="Initial user message"
    )
    context: Optional[dict[str, Any]] = Field(
        None, description="Additional context for the discussion"
    )


class MessageCreateRequest(BaseModel):
    """Request to add a message to a discussion"""

    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    role: MessageRole = Field(default=MessageRole.USER, description="Message sender role")


class QuickChatRequest(BaseModel):
    """Request for quick one-off chat (no persistent discussion)"""

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    context_type: Optional[str] = Field(None, description="Type of context (note, email, etc.)")
    context_id: Optional[str] = Field(None, description="ID of context object")
    include_suggestions: bool = Field(
        default=True, description="Include contextual suggestions in response"
    )


# =============================================================================
# Response Models
# =============================================================================


class MessageResponse(BaseModel):
    """A message in a discussion"""

    id: str = Field(..., description="Message ID")
    discussion_id: str = Field(..., description="Parent discussion ID")
    role: MessageRole = Field(..., description="Message sender role")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Message timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SuggestionResponse(BaseModel):
    """A contextual suggestion"""

    type: SuggestionType = Field(..., description="Type of suggestion")
    content: str = Field(..., description="Suggestion content")
    action_id: Optional[str] = Field(None, description="ID if actionable")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score")


class DiscussionResponse(BaseModel):
    """A discussion thread"""

    id: str = Field(..., description="Discussion ID")
    title: Optional[str] = Field(None, description="Discussion title")
    discussion_type: DiscussionType = Field(..., description="Type of discussion")
    attached_to_id: Optional[str] = Field(None, description="Attached object ID")
    attached_to_type: Optional[str] = Field(None, description="Attached object type")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages")
    last_message_preview: Optional[str] = Field(None, description="Preview of last message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DiscussionDetailResponse(DiscussionResponse):
    """Full discussion with messages"""

    messages: list[MessageResponse] = Field(default_factory=list, description="All messages")
    suggestions: list[SuggestionResponse] = Field(
        default_factory=list, description="Contextual suggestions"
    )


class DiscussionListResponse(BaseModel):
    """List of discussions"""

    discussions: list[DiscussionResponse] = Field(..., description="Discussion list")
    total: int = Field(..., description="Total count")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Items per page")


class QuickChatResponse(BaseModel):
    """Response for quick one-off chat"""

    response: str = Field(..., description="Assistant response")
    suggestions: list[SuggestionResponse] = Field(
        default_factory=list, description="Contextual suggestions"
    )
    context_used: list[str] = Field(
        default_factory=list, description="IDs of context items used"
    )
