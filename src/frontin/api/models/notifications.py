"""
Notification Models

Pydantic models for the notifications system.
Supports: creation, updates, filtering, and persistence.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications"""

    # Processing notifications
    EMAIL_RECEIVED = "email_received"
    EMAIL_PROCESSED = "email_processed"
    TEAMS_MESSAGE = "teams_message"
    CALENDAR_EVENT = "calendar_event"
    CALENDAR_CONFLICT = "calendar_conflict"

    # Action notifications
    ITEM_APPROVED = "item_approved"
    ITEM_REJECTED = "item_rejected"
    ITEM_SNOOZED = "item_snoozed"
    SNOOZE_EXPIRED = "snooze_expired"

    # Review notifications
    NOTES_DUE = "notes_due"
    NOTE_ENRICHED = "note_enriched"

    # Retouche notifications (Phase 6)
    RETOUCHE_IMPORTANT = "retouche_important"  # Action proactive (HIGH priority)
    RETOUCHE_PENDING = "retouche_pending"  # Actions en attente validation (NORMAL)
    RETOUCHE_AUTO = "retouche_auto"  # Retouches auto-appliquées (LOW)
    RETOUCHE_ERROR = "retouche_error"  # Échec répété (HIGH priority)

    # System notifications
    SYSTEM_INFO = "system_info"
    SYSTEM_WARNING = "system_warning"
    SYSTEM_ERROR = "system_error"


class NotificationPriority(str, Enum):
    """Priority levels for notifications"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationBase(BaseModel):
    """Base notification fields"""

    type: NotificationType
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    priority: NotificationPriority = NotificationPriority.NORMAL
    link: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = None


class NotificationCreate(NotificationBase):
    """Request to create a notification"""

    pass


class NotificationResponse(NotificationBase):
    """Notification response with all fields"""

    id: str
    user_id: str
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    expires_at: datetime

    class Config:
        """Pydantic config"""

        from_attributes = True


class NotificationUpdate(BaseModel):
    """Request to update a notification"""

    is_read: Optional[bool] = None


class NotificationListResponse(BaseModel):
    """Response for listing notifications"""

    notifications: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    has_more: bool


class NotificationStats(BaseModel):
    """Statistics about notifications"""

    total: int
    unread: int
    by_type: dict[str, int]
    by_priority: dict[str, int]


class NotificationFilter(BaseModel):
    """Filters for listing notifications"""

    types: Optional[list[NotificationType]] = None
    priorities: Optional[list[NotificationPriority]] = None
    is_read: Optional[bool] = None
    since: Optional[datetime] = None


class MarkReadRequest(BaseModel):
    """Request to mark notifications as read"""

    notification_ids: Optional[list[str]] = None
    mark_all: bool = False


class MarkReadResponse(BaseModel):
    """Response after marking notifications as read"""

    marked_count: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
