"""
Queue API Models

Pydantic models for queue API requests and responses.

## Version History

- v2.3 (Jan 2026): Added MultiPassMetadataResponse and PassHistoryEntryResponse
  for analysis transparency. These expose the multi-pass analysis metadata
  (passes count, models used, timing, escalation) to the frontend.

- v2.2.2 (Jan 2026): Added RetrievedContextResponse and ContextInfluenceResponse
  for context transparency.

## Multi-Pass Analysis Models (v2.3)

The multi-pass analysis system uses up to 5 passes with escalating models:
- Pass 1: Haiku (blind extraction, no context)
- Pass 2-3: Sonnet (contextual refinement with PKM/calendar context)
- Pass 4: Sonnet (deep reasoning for complex cases)
- Pass 5: Opus (expert analysis for high-stakes emails)

The `MultiPassMetadataResponse` captures:
- `passes_count`: Number of passes executed (1-5)
- `final_model`: Model used in the final pass
- `models_used`: Sequence of models used (e.g., ['haiku', 'sonnet', 'sonnet'])
- `escalated`: Whether escalation occurred (moved to a more powerful model)
- `stop_reason`: Why analysis stopped (confidence_sufficient, max_passes, no_changes)
- `total_tokens`, `total_duration_ms`: Resource consumption
- `pass_history`: Detailed history of each pass

The `PassHistoryEntryResponse` captures per-pass details:
- `pass_type`: blind, refine, deep, expert
- `model`: haiku, sonnet, opus
- `confidence_before/after`: Confidence evolution
- `context_searched`, `notes_found`: Context usage
- `escalation_triggered`: Whether this pass triggered escalation
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AttachmentResponse(BaseModel):
    """Email attachment information"""

    filename: str = Field(..., description="Attachment filename")
    size_bytes: int = Field(0, description="Attachment size in bytes")
    content_type: str = Field("application/octet-stream", description="MIME content type")


class EntityResponse(BaseModel):
    """Extracted entity in response"""

    type: str = Field(..., description="Entity type (person, date, project, etc.)")
    value: str = Field(..., description="Entity value")
    confidence: float = Field(..., description="Extraction confidence 0-1")
    source: str = Field("extraction", description="Source: extraction, ai_validation, user")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ExtractionConfidenceResponse(BaseModel):
    """4-dimension confidence for an extraction"""

    quality: float = Field(0.8, description="Info accuracy (0-1)")
    target_match: float = Field(0.8, description="Correct target note (0-1)")
    relevance: float = Field(0.8, description="Worth saving (0-1)")
    completeness: float = Field(0.8, description="No missing details (0-1)")
    overall: float = Field(0.8, description="Geometric mean of 4 dimensions")


class ProposedNoteResponse(BaseModel):
    """Proposed note creation or enrichment"""

    action: str = Field(..., description="create or enrich")
    note_type: str = Field(..., description="Type of note (personne, projet, etc.)")
    title: str = Field(..., description="Note title")
    content_summary: str = Field(..., description="Content summary")
    confidence: float = Field(..., description="Overall confidence (geometric mean) 0-1")
    confidence_details: ExtractionConfidenceResponse | None = Field(
        None, description="4-dimension confidence breakdown"
    )
    weakness_label: str | None = Field(
        None, description="Label for weakest dimension if significantly lower"
    )
    reasoning: str = Field("", description="Why this note should be created/enriched")
    target_note_id: str | None = Field(None, description="Target note ID for enrichment")
    auto_applied: bool = Field(False, description="Whether this was auto-applied (conf >= threshold)")
    required: bool = Field(False, description="Whether this enrichment is required for safe archiving")
    importance: str = Field("moyenne", description="Importance level: haute, moyenne, basse")
    manually_approved: bool | None = Field(
        None, description="User override: True=force save, False=reject, None=auto"
    )


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
    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="List of attachments with filename, size, and type"
    )
    folder: str | None = Field(None, description="Source folder")


class ActionOptionResponse(BaseModel):
    """Option d'action proposée par l'IA"""

    action: str = Field(..., description="Type d'action (archive, delete, task, etc.)")
    destination: str | None = Field(None, description="Dossier de destination")
    confidence: int = Field(..., description="Score de confiance 0-100")
    reasoning: str = Field(..., description="Explication courte de l'action")
    reasoning_detailed: str | None = Field(None, description="Explication détaillée de l'action")
    is_recommended: bool = Field(False, description="Option recommandée")
    # v2.3.1: "Why not X?" - Reason this option was rejected (if not recommended)
    rejection_reason: str | None = Field(
        None,
        description="Why this option was NOT chosen (for non-recommended options)"
    )


class ContextNoteResponse(BaseModel):
    """Note found during context search"""

    note_id: str = Field(..., description="Note identifier")
    title: str = Field(..., description="Note title")
    note_type: str = Field(..., description="Note type (personne, projet, etc.)")
    summary: str = Field("", description="Brief excerpt from the note")
    relevance: float = Field(..., description="Relevance score 0-1")
    tags: list[str] = Field(default_factory=list, description="Note tags")
    path: str = Field("", description="Folder path for navigation")


class ContextCalendarResponse(BaseModel):
    """Calendar event found during context search"""

    event_id: str = Field(..., description="Event identifier")
    title: str = Field(..., description="Event title")
    date: str = Field(..., description="Event date (YYYY-MM-DD)")
    time: str | None = Field(None, description="Event time (HH:MM)")
    relevance: float = Field(..., description="Relevance score 0-1")


class ContextTaskResponse(BaseModel):
    """Task found during context search"""

    task_id: str = Field(..., description="Task identifier")
    title: str = Field(..., description="Task title")
    project: str | None = Field(None, description="Project name")
    due_date: str | None = Field(None, description="Due date")
    relevance: float = Field(..., description="Relevance score 0-1")


class EntityProfileResponse(BaseModel):
    """Entity profile built from context"""

    canonical_name: str = Field(..., description="Canonical name in PKM")
    entity_type: str = Field(..., description="Entity type (personne, projet, etc.)")
    role: str | None = Field(None, description="Role or position")
    relationship: str | None = Field(None, description="Relationship to user")
    key_facts: list[str] = Field(default_factory=list, description="Key facts about entity")


class RetrievedContextResponse(BaseModel):
    """Full context retrieved during analysis"""

    entities_searched: list[str] = Field(default_factory=list, description="Entities searched for")
    sources_searched: list[str] = Field(default_factory=list, description="Sources searched")
    total_results: int = Field(0, description="Total results found")
    notes: list[ContextNoteResponse] = Field(default_factory=list, description="Notes found")
    calendar: list[ContextCalendarResponse] = Field(
        default_factory=list, description="Calendar events found"
    )
    tasks: list[ContextTaskResponse] = Field(default_factory=list, description="Tasks found")
    entity_profiles: dict[str, EntityProfileResponse] = Field(
        default_factory=dict, description="Entity profiles built"
    )
    conflicts: list[dict[str, Any]] = Field(
        default_factory=list, description="Conflicts detected"
    )


class ContextInfluenceResponse(BaseModel):
    """AI explanation of how context influenced the analysis"""

    notes_used: list[str] = Field(default_factory=list, description="Notes that were useful")
    explanation: str = Field("", description="Summary of how context influenced analysis")
    confirmations: list[str] = Field(
        default_factory=list, description="What was confirmed by context"
    )
    contradictions: list[str] = Field(
        default_factory=list, description="What was contradicted by context"
    )
    missing_info: list[str] = Field(
        default_factory=list, description="Information missing from context"
    )


class PassHistoryEntryResponse(BaseModel):
    """Single pass in multi-pass analysis history (v2.3)"""

    pass_number: int = Field(..., description="Pass number (1-5)")
    pass_type: str = Field(..., description="Pass type: blind, refine, deep, expert")
    model: str = Field(..., description="Model used: haiku, sonnet, opus")
    duration_ms: float = Field(0.0, description="Pass duration in milliseconds")
    tokens: int = Field(0, description="Tokens used in this pass")
    confidence_before: float = Field(0.0, description="Confidence before this pass (0-1)")
    confidence_after: float = Field(0.0, description="Confidence after this pass (0-1)")
    context_searched: bool = Field(False, description="Whether context was searched in this pass")
    notes_found: int = Field(0, description="Number of notes found (if context searched)")
    escalation_triggered: bool = Field(False, description="Whether this pass triggered escalation")
    # v2.3.1: Thinking Bubbles - Questions/doubts for next pass
    questions: list[str] = Field(
        default_factory=list,
        description="Questions/doubts the AI had for the next pass (Thinking Bubbles)"
    )


class CanevasFileStatusResponse(BaseModel):
    """Status of a single canevas file (v3.2)"""

    name: str = Field(..., description="File name without extension (e.g., 'Profile')")
    status: str = Field(..., description="File status: present, partial, missing, empty")
    char_count: int = Field(0, description="Character count of file content")
    line_count: int = Field(0, description="Line count of file content")
    required: bool = Field(True, description="Whether this file is required for complete canevas")
    loaded_from: str | None = Field(None, description="Actual filename loaded (primary or alternative)")


class CanevasStatusResponse(BaseModel):
    """Canevas completeness status (v3.2)

    Shows the status of canevas files used to personalize AI analysis.
    The Canevas is Johan's permanent context - Profile, Projects, Goals (required), Preferences (optional).
    """

    completeness: str = Field(
        ..., description="Overall completeness: complete, partial, incomplete"
    )
    files: list[CanevasFileStatusResponse] = Field(
        default_factory=list, description="Status of each canevas file"
    )
    total_chars: int = Field(0, description="Total characters across all present files")
    files_present: int = Field(0, description="Count of files with substantial content")
    files_missing: int = Field(0, description="Count of missing required files")
    files_partial: int = Field(0, description="Count of files with insufficient content")
    loaded_at: str | None = Field(None, description="Timestamp when canevas was loaded (ISO format)")


class MultiPassMetadataResponse(BaseModel):
    """Metadata from multi-pass analysis (v2.3)"""

    passes_count: int = Field(..., description="Total number of passes executed (1-5)")
    final_model: str = Field(..., description="Model used in final pass: haiku, sonnet, opus")
    models_used: list[str] = Field(
        default_factory=list, description="All models used in order (e.g., ['haiku', 'sonnet', 'sonnet'])"
    )
    escalated: bool = Field(False, description="Whether escalation occurred during analysis")
    stop_reason: str = Field("", description="Why analysis stopped: confidence_sufficient, max_passes, no_changes")
    high_stakes: bool = Field(False, description="Whether email was flagged as high-stakes")
    total_tokens: int = Field(0, description="Total tokens consumed across all passes")
    total_duration_ms: float = Field(0.0, description="Total analysis duration in milliseconds")
    pass_history: list[PassHistoryEntryResponse] = Field(
        default_factory=list, description="Detailed history of each pass"
    )
    # v3.2: Canevas status visibility
    canevas_status: CanevasStatusResponse | None = Field(
        None, description="Status of canevas context used for personalization"
    )


class StrategicQuestionResponse(BaseModel):
    """Strategic question requiring human decision (v3.1)

    Strategic questions are identified by the Four Valets pipeline and represent
    decisions that require human reflection, not just factual lookups.
    """

    question: str = Field(..., description="The strategic question for the user")
    target_note: str | None = Field(
        None, description="Note where this question should be stored (thematic note)"
    )
    category: str = Field(
        "decision",
        description="Question category: organisation, processus, structure_pkm, decision"
    )
    context: str = Field("", description="Why this question is being asked")
    source: str = Field(
        "mousqueton",
        description="Valet who identified this question: grimaud, bazin, planchet, mousqueton"
    )


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
    # Sprint 3: Draft replies
    draft_reply: str | None = Field(
        None,
        description="AI-generated draft reply when action is REPLY"
    )
    # v2.2.2: Context transparency
    retrieved_context: RetrievedContextResponse | None = Field(
        None,
        description="Full context retrieved during analysis (notes, calendar, tasks)"
    )
    context_influence: ContextInfluenceResponse | None = Field(
        None,
        description="AI explanation of how context influenced the analysis"
    )
    # v2.3: Analysis transparency
    multi_pass: MultiPassMetadataResponse | None = Field(
        None,
        description="Multi-pass analysis metadata (passes count, models, timing)"
    )
    # v3.1: Strategic questions for human decision
    strategic_questions: list[StrategicQuestionResponse] = Field(
        default_factory=list,
        description="Questions requiring human decision, accumulated from all valets"
    )


class QueueItemContent(BaseModel):
    """Content preview in queue item"""

    preview: str = Field(..., description="Text preview (max 200 chars)")
    html_body: str | None = Field(None, description="Full HTML body if available")
    full_text: str | None = Field(None, description="Full plain text body if available")


class PeripetieResolutionResponse(BaseModel):
    """Resolution details for a processed péripétie (v2.4)"""

    type: str = Field(..., description="Resolution type: auto_applied, manual_approved, manual_modified, manual_rejected, manual_skipped")
    action_taken: str = Field(..., description="Action that was taken")
    resolved_at: datetime = Field(..., description="When resolved")
    resolved_by: str = Field(..., description="Who resolved: system or user")
    confidence_at_resolution: float | None = Field(None, description="Confidence at resolution")
    user_modified_action: bool = Field(False, description="Whether user modified the action")
    original_action: str | None = Field(None, description="Original action if modified")


class PeripetieSnoozeResponse(BaseModel):
    """Snooze info for a péripétie (v2.4)"""

    until: datetime = Field(..., description="When snooze expires")
    created_at: datetime = Field(..., description="When snoozed")
    reason: str | None = Field(None, description="Reason for snooze")
    snooze_count: int = Field(1, description="Times snoozed")


class PeripetieErrorResponse(BaseModel):
    """Error details for a péripétie (v2.4)"""

    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    occurred_at: datetime = Field(..., description="When error occurred")
    retryable: bool = Field(True, description="Can be retried")
    retry_count: int = Field(0, description="Retry attempts")


class PeripetieTimestampsResponse(BaseModel):
    """Timestamps for péripétie lifecycle (v2.4)"""

    queued_at: datetime = Field(..., description="When queued")
    analysis_started_at: datetime | None = Field(None, description="When analysis started")
    analysis_completed_at: datetime | None = Field(None, description="When analysis completed")
    reviewed_at: datetime | None = Field(None, description="When reviewed")


class QueueItemResponse(BaseModel):
    """Queue item in API response"""

    id: str = Field(..., description="Queue item ID")
    account_id: str | None = Field(None, description="Email account")
    queued_at: datetime = Field(..., description="Time queued")
    metadata: QueueItemMetadata = Field(..., description="Email metadata")
    analysis: QueueItemAnalysis = Field(..., description="AI analysis")
    content: QueueItemContent = Field(..., description="Content preview")
    # Legacy fields (for backwards compatibility)
    status: str = Field(..., description="Status: pending, approved, rejected, skipped")
    reviewed_at: datetime | None = Field(None, description="Time reviewed")
    review_decision: str | None = Field(None, description="Review decision")
    # v2.4 fields
    state: str | None = Field(None, description="v2.4 state: queued, analyzing, awaiting_review, processed, error")
    resolution: PeripetieResolutionResponse | None = Field(None, description="v2.4 resolution details")
    snooze: PeripetieSnoozeResponse | None = Field(None, description="v2.4 snooze info")
    error: PeripetieErrorResponse | None = Field(None, description="v2.4 error details")
    timestamps: PeripetieTimestampsResponse | None = Field(None, description="v2.4 timestamps")
    tab: str | None = Field(None, description="v2.4 UI tab: to_process, in_progress, snoozed, history, errors")


class QueueStatsResponse(BaseModel):
    """Queue statistics response (v2.4 enhanced)"""

    total: int = Field(..., description="Total items in queue")
    by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Count by legacy status",
    )
    by_account: dict[str, int] = Field(
        default_factory=dict,
        description="Count by account",
    )
    oldest_item: datetime | None = Field(None, description="Oldest item timestamp")
    newest_item: datetime | None = Field(None, description="Newest item timestamp")
    # v2.4 fields
    by_state: dict[str, int] = Field(
        default_factory=dict,
        description="v2.4: Count by state (queued, analyzing, awaiting_review, processed, error)",
    )
    by_resolution: dict[str, int] = Field(
        default_factory=dict,
        description="v2.4: Count by resolution type",
    )
    by_tab: dict[str, int] = Field(
        default_factory=dict,
        description="v2.4: Count by UI tab (to_process, in_progress, snoozed, history, errors)",
    )
    snoozed_count: int = Field(0, description="v2.4: Number of snoozed items")
    error_count: int = Field(0, description="v2.4: Number of error items")


class EnrichmentApprovalUpdate(BaseModel):
    """Manual approval update for a single enrichment"""

    index: int = Field(..., description="Index of the enrichment in proposed_notes list")
    approved: bool | None = Field(
        ..., description="True=force save, False=reject, None=reset to auto"
    )


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
    enrichment_approvals: list[EnrichmentApprovalUpdate] | None = Field(
        None,
        description="Manual approval overrides for enrichments (optional)",
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


class SnoozeRequest(BaseModel):
    """Request to snooze a queue item"""

    snooze_option: str = Field(
        ...,
        description="Snooze option: later_today, tomorrow, this_weekend, next_week, custom"
    )
    custom_hours: int | None = Field(
        None,
        ge=1,
        le=168,
        description="Custom snooze hours (only for custom option, max 168h = 7 days)"
    )
    reason: str | None = Field(None, description="Optional reason for snoozing")


class SnoozeResponse(BaseModel):
    """Response for snooze operation"""

    snooze_id: str = Field(..., description="Unique snooze identifier")
    item_id: str = Field(..., description="Snoozed queue item ID")
    snoozed_at: str = Field(..., description="When the item was snoozed (ISO format)")
    snooze_until: str = Field(..., description="When the snooze expires (ISO format)")
    snooze_option: str = Field(..., description="Snooze option used")


class ReanalyzeRequest(BaseModel):
    """Request to reanalyze a queue item with user instruction"""

    user_instruction: str = Field(
        default="",
        max_length=500,
        description="User instruction for reanalysis (e.g., 'Classer dans Archive/2025/Relevés')",
    )
    mode: str = Field(
        "immediate",
        description="Reanalysis mode: 'immediate' (wait for result) or 'background' (queue for later)",
    )
    force_model: str | None = Field(
        None,
        description="Force a specific model: 'opus', 'sonnet', or 'haiku'. If None, uses automatic escalation.",
    )


class ReanalyzeResponse(BaseModel):
    """Response for reanalysis operation"""

    item_id: str = Field(..., description="Queue item ID")
    status: str = Field(..., description="Status: 'analyzing', 'complete', 'queued'")
    analysis_id: str | None = Field(None, description="Analysis tracking ID (for background mode)")
    new_analysis: "QueueItemAnalysis | None" = Field(
        None, description="New analysis result (for immediate mode)"
    )


class BulkReanalyzeResponse(BaseModel):
    """Response for bulk reanalysis operation"""

    total_items: int = Field(..., description="Total items to reanalyze")
    started: int = Field(..., description="Items started for reanalysis")
    failed: int = Field(0, description="Items that failed to start")
    status: str = Field("processing", description="Overall status")
