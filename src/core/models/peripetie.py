"""
Peripetie Data Models (v2.4)

This module defines the new data model for Péripéties with clear separation between:
- State: Where the item is in the processing pipeline
- Resolution: How the item was resolved (if at all)
- Snooze: Temporary postponement (orthogonal to state)
- Error: Error details (if state = 'error')

The key insight is that 'pending', 'approved', 'rejected' confuse state with resolution.
An item can be:
- In 'awaiting_review' state and later get 'manual_approved' resolution
- In 'processed' state with 'auto_applied' resolution

See: docs/specs/PERIPETIES_REFONTE_SPEC.md for full specification.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# ============================================================================
# ENUMS
# ============================================================================


class PeripetieState(str, Enum):
    """
    State of a péripétie in the processing pipeline.

    This represents WHERE the item is, not HOW it was resolved.
    """

    QUEUED = "queued"
    """Received, waiting for analysis to start."""

    ANALYZING = "analyzing"
    """Sancho is currently analyzing this item."""

    AWAITING_REVIEW = "awaiting_review"
    """Analysis complete, waiting for human decision."""

    PROCESSED = "processed"
    """Processing complete (either auto or manual)."""

    ERROR = "error"
    """Failed somewhere in the pipeline."""


class ResolutionType(str, Enum):
    """
    How a péripétie was resolved.

    Only set when state reaches 'processed'.
    """

    AUTO_APPLIED = "auto_applied"
    """Confidence was sufficient, action was applied automatically."""

    MANUAL_APPROVED = "manual_approved"
    """Human approved the recommended action."""

    MANUAL_MODIFIED = "manual_modified"
    """Human modified the action before approving."""

    MANUAL_REJECTED = "manual_rejected"
    """Human rejected (no action taken)."""

    MANUAL_SKIPPED = "manual_skipped"
    """Human skipped without deciding."""


class ErrorType(str, Enum):
    """
    Type of error that occurred during processing.
    """

    ANALYSIS_FAILED = "analysis_failed"
    """Sancho could not analyze the item."""

    ACTION_FAILED = "action_failed"
    """Analysis OK but action failed (IMAP down, etc.)."""

    ENRICHMENT_FAILED = "enrichment_failed"
    """Notes/tasks could not be created."""

    TIMEOUT = "timeout"
    """Timeout during processing."""


class ResolvedBy(str, Enum):
    """Who resolved the péripétie."""

    SYSTEM = "system"
    """Resolved automatically by the system."""

    USER = "user"
    """Resolved by user action."""


# ============================================================================
# MODELS
# ============================================================================


class PeripetieResolution(BaseModel):
    """
    Resolution details for a processed péripétie.

    Captures HOW the item was resolved, by whom, and any modifications made.
    """

    type: ResolutionType = Field(
        ...,
        description="Type of resolution (auto_applied, manual_approved, etc.)"
    )

    action_taken: str = Field(
        ...,
        description="Action that was taken: 'archive', 'delete', 'task', 'keep', etc."
    )

    resolved_at: datetime = Field(
        ...,
        description="When the resolution occurred"
    )

    resolved_by: ResolvedBy = Field(
        ...,
        description="Who resolved: 'system' or 'user'"
    )

    # Optional details
    confidence_at_resolution: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score at time of resolution (0-1)"
    )

    user_modified_action: bool = Field(
        False,
        description="Whether user modified the recommended action"
    )

    original_action: Optional[str] = Field(
        None,
        description="Original recommended action if user modified it"
    )

    destination: Optional[str] = Field(
        None,
        description="Destination folder for archive action"
    )

    rejection_reason: Optional[str] = Field(
        None,
        description="Reason for rejection (if manual_rejected)"
    )

    feedback_tags: list[str] = Field(
        default_factory=list,
        description="Feedback tags from user (for Sganarelle learning)"
    )


class PeripetieSnooze(BaseModel):
    """
    Snooze information for a péripétie.

    Snooze is orthogonal to state - an item can be snoozed while in 'awaiting_review'.
    When snooze expires, item returns to normal visibility.
    """

    until: datetime = Field(
        ...,
        description="When the snooze expires (UTC)"
    )

    created_at: datetime = Field(
        ...,
        description="When the item was snoozed (UTC)"
    )

    reason: Optional[str] = Field(
        None,
        description="Optional reason for snoozing"
    )

    snooze_count: int = Field(
        1,
        ge=1,
        description="Number of times this item has been snoozed"
    )

    snooze_option: str = Field(
        "custom",
        description="Snooze option used: later_today, tomorrow, this_weekend, next_week, custom"
    )


class PeripetieError(BaseModel):
    """
    Error details when state = 'error'.

    Captures what went wrong, when, and whether it can be retried.
    """

    type: ErrorType = Field(
        ...,
        description="Type of error"
    )

    message: str = Field(
        ...,
        description="Human-readable error message"
    )

    occurred_at: datetime = Field(
        ...,
        description="When the error occurred (UTC)"
    )

    retryable: bool = Field(
        True,
        description="Whether this error can be retried"
    )

    retry_count: int = Field(
        0,
        ge=0,
        description="Number of retry attempts"
    )

    last_retry_at: Optional[datetime] = Field(
        None,
        description="When the last retry was attempted"
    )

    details: Optional[dict] = Field(
        None,
        description="Additional error details (stack trace, etc.)"
    )


class PeripetieTimestamps(BaseModel):
    """
    Timestamps tracking the péripétie lifecycle.
    """

    queued_at: datetime = Field(
        ...,
        description="When the item entered the queue (UTC)"
    )

    analysis_started_at: Optional[datetime] = Field(
        None,
        description="When analysis started (UTC)"
    )

    analysis_completed_at: Optional[datetime] = Field(
        None,
        description="When analysis completed (UTC)"
    )

    reviewed_at: Optional[datetime] = Field(
        None,
        description="When user reviewed the item (if applicable)"
    )


# ============================================================================
# MIGRATION HELPERS
# ============================================================================


def migrate_legacy_status(legacy_status: str) -> tuple[PeripetieState, Optional[ResolutionType]]:
    """
    Migrate legacy status to new state/resolution model.

    Legacy statuses were:
    - 'pending' -> awaiting_review, no resolution
    - 'approved' -> processed, manual_approved
    - 'rejected' -> processed, manual_rejected
    - 'skipped' -> processed, manual_skipped

    Args:
        legacy_status: Old status value

    Returns:
        Tuple of (new_state, resolution_type or None)
    """
    mapping = {
        "pending": (PeripetieState.AWAITING_REVIEW, None),
        "approved": (PeripetieState.PROCESSED, ResolutionType.MANUAL_APPROVED),
        "rejected": (PeripetieState.PROCESSED, ResolutionType.MANUAL_REJECTED),
        "skipped": (PeripetieState.PROCESSED, ResolutionType.MANUAL_SKIPPED),
    }

    return mapping.get(
        legacy_status,
        (PeripetieState.AWAITING_REVIEW, None)  # Default for unknown
    )


def state_to_tab(state: PeripetieState, has_snooze: bool = False) -> str:
    """
    Map state to UI tab name.

    Args:
        state: Péripétie state
        has_snooze: Whether item has active snooze

    Returns:
        Tab name: 'to_process', 'in_progress', 'snoozed', 'history', 'errors'
    """
    if has_snooze and state == PeripetieState.AWAITING_REVIEW:
        return "snoozed"

    mapping = {
        PeripetieState.QUEUED: "in_progress",
        PeripetieState.ANALYZING: "in_progress",
        PeripetieState.AWAITING_REVIEW: "to_process",
        PeripetieState.PROCESSED: "history",
        PeripetieState.ERROR: "errors",
    }

    return mapping.get(state, "to_process")
