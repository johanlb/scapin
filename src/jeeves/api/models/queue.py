"""
Queue API Models

Pydantic models for queue API requests and responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EntityResponse(BaseModel):
    """Extracted entity in response"""

    type: str = Field(..., description="Entity type (person, date, project, etc.)")
    value: str = Field(..., description="Entity value")
    confidence: float = Field(..., description="Extraction confidence 0-1")
    source: str = Field("extraction", description="Source: extraction, ai_validation, user")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProposedNoteResponse(BaseModel):
    """Proposed note creation or enrichment"""

    action: str = Field(..., description="create or enrich")
    note_type: str = Field(..., description="Type of note (personne, projet, etc.)")
    title: str = Field(..., description="Note title")
    content_summary: str = Field(..., description="Content summary")
    confidence: float = Field(..., description="Proposal confidence 0-1")
    reasoning: str = Field("", description="Why this note should be created/enriched")
    target_note_id: str | None = Field(None, description="Target note ID for enrichment")
    auto_applied: bool = Field(False, description="Whether this was auto-applied (conf >= 0.90)")


class ProposedTaskResponse(BaseModel):
    """Proposed OmniFocus task"""

    title: str = Field(..., description="Task title")
    note: str = Field("", description="Task note")
    project: str | None = Field(None, description="Target project")
    due_date: str | None = Field(None, description="Due date (ISO format)")
    confidence: float = Field(..., description="Proposal confidence 0-1")
    reasoning: str = Field("", description="Why this task should be created")
    auto_applied: bool = Field(False, description="Whether this was auto-applied (conf >= 0.90)")


class QueueItemMetadata(BaseModel):
    """Email metadata in queue item"""

    id: str = Field(..., description="Email ID")
    subject: str = Field(..., description="Email subject")
    from_address: str = Field(..., description="Sender email")
    from_name: str = Field("", description="Sender name")
    date: datetime | None = Field(None, description="Email date")
    has_attachments: bool = Field(False, description="Has attachments")
    folder: str | None = Field(None, description="Source folder")


class ActionOptionResponse(BaseModel):
    """Option d'action proposée par l'IA"""

    action: str = Field(..., description="Type d'action (archive, delete, task, etc.)")
    destination: str | None = Field(None, description="Dossier de destination")
    confidence: int = Field(..., description="Score de confiance 0-100")
    reasoning: str = Field(..., description="Explication courte de l'action")
    reasoning_detailed: str | None = Field(None, description="Explication détaillée de l'action")
    is_recommended: bool = Field(False, description="Option recommandée")


class QueueItemAnalysis(BaseModel):
    """AI analysis in queue item"""

    action: str = Field(..., description="Suggested action (from recommended option)")
    confidence: float = Field(..., description="Confidence score 0-100")
    category: str | None = Field(None, description="Email category")
    reasoning: str = Field("", description="AI reasoning")
    summary: str | None = Field(None, description="Résumé de l'email en français")
    options: list[ActionOptionResponse] = Field(
        default_factory=list,
        description="Options d'action proposées par l'IA"
    )
    # Sprint 2: Entity extraction & bidirectional loop
    entities: dict[str, list[EntityResponse]] = Field(
        default_factory=dict,
        description="Extracted entities grouped by type (person, date, project, etc.)"
    )
    proposed_notes: list[ProposedNoteResponse] = Field(
        default_factory=list,
        description="Proposed notes to create or enrich"
    )
    proposed_tasks: list[ProposedTaskResponse] = Field(
        default_factory=list,
        description="Proposed OmniFocus tasks"
    )
    context_used: list[str] = Field(
        default_factory=list,
        description="IDs of notes used as context for this analysis"
    )


class QueueItemContent(BaseModel):
    """Content preview in queue item"""

    preview: str = Field(..., description="Text preview (max 200 chars)")
    html_body: str | None = Field(None, description="Full HTML body if available")
    full_text: str | None = Field(None, description="Full plain text body if available")


class QueueItemResponse(BaseModel):
    """Queue item in API response"""

    id: str = Field(..., description="Queue item ID")
    account_id: str | None = Field(None, description="Email account")
    queued_at: datetime = Field(..., description="Time queued")
    metadata: QueueItemMetadata = Field(..., description="Email metadata")
    analysis: QueueItemAnalysis = Field(..., description="AI analysis")
    content: QueueItemContent = Field(..., description="Content preview")
    status: str = Field(..., description="Status: pending, approved, rejected, skipped")
    reviewed_at: datetime | None = Field(None, description="Time reviewed")
    review_decision: str | None = Field(None, description="Review decision")


class QueueStatsResponse(BaseModel):
    """Queue statistics response"""

    total: int = Field(..., description="Total items in queue")
    by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Count by status",
    )
    by_account: dict[str, int] = Field(
        default_factory=dict,
        description="Count by account",
    )
    oldest_item: datetime | None = Field(None, description="Oldest item timestamp")
    newest_item: datetime | None = Field(None, description="Newest item timestamp")


class ApproveRequest(BaseModel):
    """Request to approve a queue item"""

    modified_action: str | None = Field(
        None,
        description="Override suggested action (optional)",
    )
    modified_category: str | None = Field(
        None,
        description="Override category (optional)",
    )
    destination: str | None = Field(
        None,
        description="Destination folder for archive action (optional)",
    )


class ModifyRequest(BaseModel):
    """Request to modify a queue item - select an option or provide custom instruction"""

    action: str = Field(..., description="New action to take")
    destination: str | None = Field(None, description="Dossier de destination")
    category: str | None = Field(None, description="New category (optional)")
    reasoning: str | None = Field(None, description="Reason for modification")
    selected_option_index: int | None = Field(
        None,
        description="Index de l'option sélectionnée (0-based)"
    )
    custom_instruction: str | None = Field(
        None,
        description="Instruction personnalisée (si aucune option ne convient)"
    )


class RejectRequest(BaseModel):
    """Request to reject a queue item"""

    reason: str | None = Field(None, description="Reason for rejection")
