"""
Events API Models

Pydantic models for events API requests and responses.
Handles snooze/undo operations for queue items.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SnoozeRequest(BaseModel):
    """Request to snooze an item"""

    hours: int | None = Field(None, ge=1, le=168, description="Hours to snooze (max 7 days)")
    days: int | None = Field(None, ge=1, le=30, description="Days to snooze (max 30)")
    until: datetime | None = Field(None, description="Specific datetime to snooze until")
    reason: str | None = Field(None, description="Reason for snoozing")


class SnoozeResponse(BaseModel):
    """Response for snooze operation"""

    snooze_id: str = Field(..., description="Unique snooze identifier")
    item_id: str = Field(..., description="ID of the snoozed item")
    item_type: str = Field(..., description="Type of item (queue_item, email, etc.)")
    snoozed_at: datetime = Field(..., description="When the item was snoozed")
    snooze_until: datetime = Field(..., description="When the snooze expires")
    reason: str | None = Field(None, description="Reason for snoozing")


class SnoozedItemResponse(BaseModel):
    """A snoozed item in the list"""

    snooze_id: str = Field(..., description="Snooze identifier")
    item_id: str = Field(..., description="ID of the snoozed item")
    item_type: str = Field(..., description="Type of item")
    snoozed_at: datetime = Field(..., description="When snoozed")
    snooze_until: datetime = Field(..., description="When it expires")
    reason: str | None = Field(None, description="Snooze reason")
    time_remaining_minutes: int = Field(..., description="Minutes until expiration")
    is_expired: bool = Field(False, description="Whether snooze has expired")

    # Item preview data
    item_preview: dict[str, Any] = Field(
        default_factory=dict,
        description="Preview of the snoozed item (subject, sender, etc.)"
    )


class ActionHistoryResponse(BaseModel):
    """An action in the history"""

    action_id: str = Field(..., description="Action identifier")
    action_type: str = Field(..., description="Type of action")
    item_id: str = Field(..., description="ID of the item")
    item_type: str = Field(..., description="Type of item")
    executed_at: datetime = Field(..., description="When the action was executed")
    status: str = Field(..., description="Status: completed, undone, failed")
    can_undo: bool = Field(False, description="Whether this action can be undone")

    # Action details
    action_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Action parameters"
    )


class UndoRequest(BaseModel):
    """Request to undo an action"""

    reason: str | None = Field(None, description="Reason for undoing")


class UndoResponse(BaseModel):
    """Response for undo operation"""

    action_id: str = Field(..., description="ID of the undone action")
    item_id: str = Field(..., description="ID of the item")
    success: bool = Field(..., description="Whether undo succeeded")
    message: str = Field("", description="Result message")
    undo_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Details of the undo operation"
    )


class EventsStatsResponse(BaseModel):
    """Statistics for events (snoozes and actions)"""

    # Snooze stats
    snoozed_count: int = Field(0, description="Currently snoozed items")
    expired_pending: int = Field(0, description="Expired snoozes pending wake-up")

    # Action stats
    total_actions: int = Field(0, description="Total recorded actions")
    undoable_actions: int = Field(0, description="Actions that can be undone")
    actions_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Actions count by type"
    )
