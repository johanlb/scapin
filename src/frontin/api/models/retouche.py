"""
Retouche API Models

Pydantic models for retouche lifecycle actions API.
Handles pending actions approval/rejection and lifecycle operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RetoucheActionType(str, Enum):
    """Types of retouche lifecycle actions"""

    FLAG_OBSOLETE = "flag_obsolete"
    MERGE_INTO = "merge_into"
    MOVE_TO_FOLDER = "move_to_folder"


class PendingRetoucheActionResponse(BaseModel):
    """Pending retouche action awaiting human approval"""

    action_id: str = Field(..., description="Unique action identifier")
    note_id: str = Field(..., description="ID of the note this action applies to")
    note_title: str = Field(..., description="Title of the note")
    note_path: str = Field(..., description="Path to the note")
    action_type: RetoucheActionType = Field(..., description="Type of lifecycle action")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="AI confidence score (0-1)"
    )
    reasoning: str = Field(..., description="AI explanation for suggesting this action")
    target_note_id: str | None = Field(
        None, description="For merge_into: ID of the target note"
    )
    target_note_title: str | None = Field(
        None, description="For merge_into: title of the target note"
    )
    target_folder: str | None = Field(
        None, description="For move_to_folder: target folder path"
    )
    created_at: datetime | None = Field(None, description="When this action was proposed")


class RetoucheQueueResponse(BaseModel):
    """Queue of pending retouche actions"""

    pending_actions: list[PendingRetoucheActionResponse] = Field(
        default_factory=list, description="Actions awaiting approval"
    )
    total_count: int = Field(0, description="Total number of pending actions")
    by_type: dict[str, int] = Field(
        default_factory=dict, description="Count by action type"
    )


class ApproveActionRequest(BaseModel):
    """Request to approve a pending retouche action"""

    action_id: str = Field(..., description="ID of the action to approve")
    note_id: str = Field(..., description="ID of the note")
    apply_immediately: bool = Field(
        True, description="Whether to apply the action immediately"
    )
    custom_params: dict[str, Any] | None = Field(
        None,
        description="Optional custom parameters (e.g., different target folder)",
    )


class RejectActionRequest(BaseModel):
    """Request to reject a pending retouche action"""

    action_id: str = Field(..., description="ID of the action to reject")
    note_id: str = Field(..., description="ID of the note")
    reason: str | None = Field(
        None, description="Optional reason for rejection (for learning)"
    )
    suppress_future: bool = Field(
        False,
        description="Whether to suppress similar suggestions in the future",
    )


class ActionResultResponse(BaseModel):
    """Result of approving/rejecting a retouche action"""

    success: bool = Field(..., description="Whether the operation succeeded")
    action_id: str = Field(..., description="ID of the action")
    note_id: str = Field(..., description="ID of the note")
    action_type: str = Field(..., description="Type of action that was processed")
    message: str = Field(..., description="Human-readable result message")
    applied: bool = Field(False, description="Whether the action was applied")
    rollback_available: bool = Field(
        False, description="Whether the action can be rolled back"
    )
    rollback_token: str | None = Field(
        None, description="Token to use for rollback, if available"
    )


class RollbackActionRequest(BaseModel):
    """Request to rollback an applied retouche action"""

    rollback_token: str = Field(..., description="Rollback token from apply response")
    note_id: str = Field(..., description="ID of the note")


class RollbackResultResponse(BaseModel):
    """Result of rolling back a retouche action"""

    success: bool = Field(..., description="Whether the rollback succeeded")
    note_id: str = Field(..., description="ID of the note")
    action_type: str = Field(..., description="Type of action that was rolled back")
    message: str = Field(..., description="Human-readable result message")


class BatchApproveRequest(BaseModel):
    """Request to approve multiple pending actions at once"""

    action_ids: list[str] = Field(
        ..., min_length=1, description="List of action IDs to approve"
    )
    note_ids: list[str] = Field(
        ..., min_length=1, description="Corresponding note IDs"
    )


class BatchApproveResponse(BaseModel):
    """Result of batch approval"""

    success: bool = Field(..., description="Whether all operations succeeded")
    approved_count: int = Field(0, description="Number of actions approved")
    failed_count: int = Field(0, description="Number of actions that failed")
    results: list[ActionResultResponse] = Field(
        default_factory=list, description="Individual results"
    )


class NoteLifecycleStatusResponse(BaseModel):
    """Current lifecycle status of a note"""

    note_id: str = Field(..., description="Note identifier")
    obsolete_flag: bool = Field(False, description="Whether note is marked obsolete")
    obsolete_reason: str = Field("", description="Reason for obsolescence")
    merge_target_id: str | None = Field(
        None, description="ID of note this will be merged into"
    )
    merge_target_title: str | None = Field(
        None, description="Title of merge target note"
    )
    pending_actions_count: int = Field(
        0, description="Number of pending actions for this note"
    )
    quality_score: int | None = Field(
        None, ge=0, le=100, description="Quality score (0-100)"
    )
