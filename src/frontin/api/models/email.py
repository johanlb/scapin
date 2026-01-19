"""
Email API Models

Pydantic models for email API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class EmailAccountResponse(BaseModel):
    """Email account information"""

    name: str = Field(..., description="Account name")
    email: str = Field(..., description="Email address")
    enabled: bool = Field(..., description="Whether account is enabled")
    inbox_folder: str = Field("INBOX", description="Inbox folder name")


class EmailMetadataResponse(BaseModel):
    """Email metadata in response"""

    id: str = Field(..., description="Email ID")
    subject: str = Field(..., description="Email subject")
    from_address: str = Field(..., description="Sender email")
    from_name: str | None = Field(None, description="Sender name")
    date: datetime | None = Field(None, description="Email date")
    has_attachments: bool = Field(False, description="Has attachments")
    folder: str | None = Field(None, description="Source folder")


class EmailAnalysisResponse(BaseModel):
    """AI analysis result"""

    action: str = Field(..., description="Suggested action")
    confidence: float = Field(..., description="Confidence score 0-100")
    category: str | None = Field(None, description="Email category")
    reasoning: str | None = Field(None, description="AI reasoning")
    destination: str | None = Field(None, description="Destination folder")


class ProcessedEmailResponse(BaseModel):
    """Processed email in response"""

    metadata: EmailMetadataResponse = Field(..., description="Email metadata")
    analysis: EmailAnalysisResponse = Field(..., description="AI analysis")
    processed_at: datetime = Field(..., description="Processing timestamp")
    executed: bool = Field(False, description="Whether action was executed")


class EmailStatsResponse(BaseModel):
    """Email processing statistics"""

    emails_processed: int = Field(0, description="Total processed")
    emails_auto_executed: int = Field(0, description="Auto-executed actions")
    emails_archived: int = Field(0, description="Archived count")
    emails_deleted: int = Field(0, description="Deleted count")
    emails_queued: int = Field(0, description="Queued for review")
    emails_skipped: int = Field(0, description="Skipped count")
    tasks_created: int = Field(0, description="Tasks created")
    average_confidence: float = Field(0.0, description="Average confidence")
    processing_mode: str = Field("unknown", description="Processing mode")


class ProcessInboxRequest(BaseModel):
    """Request to process inbox"""

    limit: int | None = Field(None, ge=1, le=100, description="Max emails to process")
    auto_execute: bool = Field(False, description="Auto-execute high confidence actions")
    confidence_threshold: int | None = Field(
        None,
        ge=0,
        le=100,
        description="Minimum confidence for auto-execution",
    )
    unread_only: bool = Field(False, description="Only process unread emails")
    unprocessed_only: bool = Field(True, description="Only fetch emails not yet processed by Scapin")


class ProcessInboxResponse(BaseModel):
    """Response from inbox processing"""

    total_processed: int = Field(..., description="Total emails processed")
    auto_executed: int = Field(0, description="Actions auto-executed")
    queued: int = Field(0, description="Emails queued for review")
    skipped: int = Field(0, description="Emails skipped")
    emails: list[ProcessedEmailResponse] = Field(
        default_factory=list,
        description="Processed emails",
    )


class AnalyzeEmailRequest(BaseModel):
    """Request to analyze a single email"""

    email_id: str = Field(..., description="Email ID to analyze")
    folder: str = Field("INBOX", description="Folder containing the email")


class ExecuteActionRequest(BaseModel):
    """Request to execute an action on an email"""

    email_id: str = Field(..., description="Email ID")
    action: str = Field(..., description="Action to execute: archive, delete, task")
    destination: str | None = Field(None, description="Destination folder for archive")
    task_title: str | None = Field(None, description="Task title if action is 'task'")


# ============================================================================
# Folder Models
# ============================================================================


class FolderResponse(BaseModel):
    """Single folder information"""

    path: str = Field(..., description="Full folder path (e.g., 'Archive/2024')")
    name: str = Field(..., description="Display name (last component)")
    delimiter: str = Field("/", description="Hierarchy delimiter")
    has_children: bool = Field(False, description="Whether folder has subfolders")
    selectable: bool = Field(True, description="Whether folder can be selected")


class FolderTreeNode(BaseModel):
    """Folder in hierarchical tree structure"""

    name: str = Field(..., description="Folder display name")
    path: str = Field(..., description="Full folder path")
    children: list["FolderTreeNode"] = Field(
        default_factory=list,
        description="Child folders",
    )


class FolderSuggestionResponse(BaseModel):
    """AI-powered folder suggestion"""

    folder: str = Field(..., description="Suggested folder path")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    reason: str = Field(..., description="Reason for suggestion")


class FolderSuggestionsResponse(BaseModel):
    """Response with folder suggestions"""

    suggestions: list[FolderSuggestionResponse] = Field(
        default_factory=list,
        description="Suggested folders ordered by confidence",
    )
    recent_folders: list[str] = Field(
        default_factory=list,
        description="Recently used folders",
    )
    popular_folders: list[str] = Field(
        default_factory=list,
        description="Most frequently used folders",
    )


class CreateFolderRequest(BaseModel):
    """Request to create a new folder"""

    path: str = Field(
        ...,
        min_length=1,
        description="Folder path to create (e.g., 'Archive/Projects/2024')",
    )


class CreateFolderResponse(BaseModel):
    """Response from folder creation"""

    path: str = Field(..., description="Created folder path")
    created: bool = Field(..., description="Whether folder was newly created")


class RecordArchiveRequest(BaseModel):
    """Request to record an archive action for learning"""

    folder: str = Field(..., description="Destination folder used")
    sender_email: str | None = Field(None, description="Sender email address")
    subject: str | None = Field(None, description="Email subject")
