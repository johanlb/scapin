"""
Teams API Models

Pydantic models for Teams API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TeamsChatResponse(BaseModel):
    """Teams chat in response"""

    id: str = Field(..., description="Chat ID")
    topic: str | None = Field(None, description="Chat topic/name")
    chat_type: str = Field("oneOnOne", description="Chat type: oneOnOne, group, meeting")
    created_at: datetime | None = Field(None, description="Chat creation time")
    last_message_at: datetime | None = Field(None, description="Last message time")
    member_count: int = Field(0, description="Number of members")
    unread_count: int = Field(0, description="Unread message count")


class TeamsSenderResponse(BaseModel):
    """Teams message sender"""

    id: str = Field(..., description="User ID")
    display_name: str = Field(..., description="Display name")
    email: str | None = Field(None, description="Email address")


class TeamsMessageResponse(BaseModel):
    """Teams message in response"""

    id: str = Field(..., description="Message ID")
    chat_id: str = Field(..., description="Chat ID")
    sender: TeamsSenderResponse = Field(..., description="Message sender")
    content: str = Field(..., description="Message content (HTML)")
    content_preview: str = Field("", description="Plain text preview")
    created_at: datetime = Field(..., description="Message timestamp")
    is_read: bool = Field(True, description="Whether message is read")
    importance: str = Field("normal", description="Importance: normal, high, urgent")
    has_mentions: bool = Field(False, description="Whether message mentions user")
    attachments_count: int = Field(0, description="Number of attachments")


class TeamsStatsResponse(BaseModel):
    """Teams statistics"""

    total_chats: int = Field(0, description="Total chats")
    unread_chats: int = Field(0, description="Chats with unread messages")
    messages_processed: int = Field(0, description="Messages processed")
    messages_flagged: int = Field(0, description="Messages flagged")
    last_poll: datetime | None = Field(None, description="Last poll timestamp")


class TeamsPollResponse(BaseModel):
    """Teams poll result"""

    messages_fetched: int = Field(..., description="Messages fetched")
    messages_new: int = Field(0, description="New messages since last poll")
    chats_checked: int = Field(0, description="Chats checked")
    polled_at: datetime = Field(..., description="Poll timestamp")


class SendReplyRequest(BaseModel):
    """Request to reply to a message"""

    content: str = Field(..., min_length=1, description="Reply content")


class FlagMessageRequest(BaseModel):
    """Request to flag a message"""

    flag: bool = Field(True, description="Flag state (True = flagged)")
    reason: str | None = Field(None, description="Optional reason for flagging")
