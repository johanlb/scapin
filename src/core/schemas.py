"""
PKM Pydantic Schemas

Data validation schemas for all PKM entities:
- Email processing
- Decision tracking
- Knowledge management
- Review/FSRS
- Conversations
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict


# ============================================================================
# ENUMS
# ============================================================================


class EmailAction(str, Enum):
    """Email processing actions"""

    DELETE = "delete"
    ARCHIVE = "archive"
    REFERENCE = "reference"
    KEEP = "keep"
    TASK = "task"
    REPLY = "reply"
    DEFER = "defer"
    QUEUE = "queue"


class EmailCategory(str, Enum):
    """Email categories"""

    PERSONAL = "personal"
    WORK = "work"
    FINANCE = "finance"
    TRAVEL = "travel"
    SHOPPING = "shopping"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    NOTIFICATION = "notification"
    SPAM = "spam"
    OTHER = "other"


class ReviewGrade(str, Enum):
    """FSRS review grades"""

    AGAIN = "again"  # Complete blackout, forgot completely
    HARD = "hard"  # Incorrect response, but upon review, remembered
    GOOD = "good"  # Correct response, with some hesitation
    EASY = "easy"  # Perfect response, immediate recall


class ProcessingMode(str, Enum):
    """Email processor modes"""

    AUTO = "auto"  # High confidence auto-processing
    LEARNING = "learning"  # User validation for learning
    REVIEW = "review"  # Review past decisions


# ============================================================================
# EMAIL SCHEMAS
# ============================================================================


class EmailAttachment(BaseModel):
    """Email attachment information"""
    model_config = ConfigDict(str_strip_whitespace=True)

    filename: str = Field(..., min_length=1, description="Attachment filename")
    size_bytes: int = Field(default=0, ge=0, description="Attachment size in bytes")
    content_type: str = Field(
        default="application/octet-stream",
        description="MIME content type"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename is not empty and has no path separators"""
        if not v.strip():
            raise ValueError("Filename cannot be empty")
        if "/" in v or "\\" in v:
            raise ValueError("Filename cannot contain path separators")
        return v.strip()


class EmailMetadata(BaseModel):
    """Email metadata from IMAP"""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = Field(..., description="IMAP message UID")
    folder: str = Field(default="INBOX", description="IMAP folder path")
    message_id: Optional[str] = Field(None, description="Email Message-ID header")
    from_address: EmailStr = Field(..., description="Sender email address")
    from_name: Optional[str] = Field(None, description="Sender display name")
    to_addresses: List[EmailStr] = Field(default_factory=list, description="Recipients")
    cc_addresses: List[EmailStr] = Field(default_factory=list, description="CC recipients")
    bcc_addresses: List[EmailStr] = Field(default_factory=list, description="BCC recipients")
    subject: str = Field(..., min_length=1, description="Email subject")
    date: datetime = Field(..., description="Email date")
    has_attachments: bool = Field(default=False, description="Has attachments")
    attachments: List[EmailAttachment] = Field(default_factory=list, description="Attachment information")
    size_bytes: Optional[int] = Field(None, description="Email size in bytes")
    flags: List[str] = Field(default_factory=list, description="IMAP flags")
    references: List[str] = Field(default_factory=list, description="Message references for threading")
    in_reply_to: Optional[str] = Field(None, description="In-Reply-To header for threading")

    @field_validator("subject")
    @classmethod
    def subject_not_empty(cls, v: str) -> str:
        """Validate subject is not empty after stripping"""
        if not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()


class EmailContent(BaseModel):
    """Email body content"""

    model_config = ConfigDict(str_strip_whitespace=True)

    plain_text: Optional[str] = Field(None, description="Plain text body")
    html: Optional[str] = Field(None, description="HTML body")
    preview: Optional[str] = Field(None, max_length=500, description="Email preview (first 500 chars)")
    attachments: List[str] = Field(default_factory=list, description="Attachment filenames")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Content metadata (encoding issues, truncation, etc.)"
    )

    @model_validator(mode='after')
    def generate_preview(self) -> 'EmailContent':
        """Generate preview from plain text if not provided"""
        if not self.preview and self.plain_text:
            self.preview = self.plain_text[:500]
        elif not self.preview:
            self.preview = ""  # Ensure preview is never None
        return self


class EmailAnalysis(BaseModel):
    """AI analysis result for an email"""

    model_config = ConfigDict(str_strip_whitespace=True)

    action: EmailAction = Field(..., description="Recommended action")
    category: EmailCategory = Field(..., description="Email category")
    destination: Optional[str] = Field(None, description="Destination folder (archive/reference)")
    confidence: int = Field(..., description="Confidence score 0-100")
    reasoning: str = Field(..., min_length=10, description="Explanation for decision")
    omnifocus_task: Optional[Dict[str, Any]] = Field(None, description="OmniFocus task data (title, note, tags, dates)")
    tags: List[str] = Field(default_factory=list, description="Suggested tags")
    related_emails: List[str] = Field(
        default_factory=list, description="Related email Message-IDs"
    )
    entities: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities (people, dates, amounts)"
    )
    needs_full_content: bool = Field(
        default=False, description="Needs full email content (preview mode)"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: int) -> int:
        """
        Ensure confidence is within valid range [0, 100]

        Raises ValueError instead of silently clamping to catch bugs in
        confidence calculation logic.
        """
        if not (0 <= v <= 100):
            raise ValueError(
                f"Confidence must be 0-100, got {v}. "
                f"This indicates a bug in confidence calculation."
            )
        return v


class EmailValidationResult(BaseModel):
    """Result of email validation check"""

    model_config = ConfigDict(str_strip_whitespace=True)

    is_valid: bool = Field(..., description="Email is valid for processing")
    should_truncate: bool = Field(default=False, description="Content should be truncated")
    reason: Optional[str] = Field(None, description="Reason for validation result")
    details: Optional[str] = Field(None, description="Additional validation details")


class ProcessedEmail(BaseModel):
    """Complete email with metadata, content, and analysis"""

    model_config = ConfigDict(str_strip_whitespace=True)

    metadata: EmailMetadata
    content: EmailContent
    analysis: Optional[EmailAnalysis] = None
    processed_at: Optional[datetime] = None
    user_action: Optional[EmailAction] = None
    user_destination: Optional[str] = None
    is_correction: bool = Field(default=False, description="User corrected AI decision")


# ============================================================================
# DECISION TRACKING SCHEMAS
# ============================================================================


class DecisionRecord(BaseModel):
    """Record of a processing decision"""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., description="Unique decision ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    email_metadata: EmailMetadata
    ai_analysis: Optional[EmailAnalysis] = None
    user_action: EmailAction
    user_destination: Optional[str] = None
    is_correction: bool = Field(default=False, description="User corrected AI")
    processing_mode: ProcessingMode
    reviewed: bool = Field(default=False, description="Decision has been reviewed")
    review_status: Optional[str] = Field(
        None, description="Review result: confirmed, corrected"
    )
    review_date: Optional[datetime] = None
    correct_action: Optional[EmailAction] = Field(
        None, description="Correct action if reviewed and corrected"
    )
    correct_destination: Optional[str] = None

    @model_validator(mode='after')
    def validate_correction_consistency(self) -> 'DecisionRecord':
        """
        Validate consistency between is_correction and correct_action

        Rules:
        - If is_correction=True, correct_action must be set
        - If is_correction=False, correct_action should be None
        """
        if self.is_correction and not self.correct_action:
            raise ValueError(
                "correct_action is required when is_correction=True"
            )
        if not self.is_correction and self.correct_action:
            raise ValueError(
                "correct_action should be None when is_correction=False"
            )
        return self


# ============================================================================
# KNOWLEDGE SCHEMAS
# ============================================================================


class KnowledgeEntry(BaseModel):
    """Knowledge base entry (markdown file)"""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., description="Unique entry ID (filename)")
    title: str = Field(..., min_length=1, description="Entry title")
    content: str = Field(..., description="Markdown content")
    category: str = Field(..., description="Knowledge category")
    tags: List[str] = Field(default_factory=list, description="Tags")
    source_email_id: Optional[str] = Field(
        None, description="Source email Message-ID if from email"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[str] = Field(None, description="Git file path")
    git_tracked: bool = Field(default=False, description="Tracked in Git")


class KnowledgeQuery(BaseModel):
    """Query for knowledge base search"""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(..., min_length=1, description="Search query")
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)
    include_content: bool = Field(default=True, description="Include full content in results")


# ============================================================================
# REVIEW/FSRS SCHEMAS
# ============================================================================


class FSRSCard(BaseModel):
    """FSRS flashcard for spaced repetition"""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., description="Card ID")
    knowledge_entry_id: str = Field(..., description="Linked knowledge entry")
    question: str = Field(..., min_length=1, description="Review question")
    answer: str = Field(..., min_length=1, description="Expected answer")
    stability: float = Field(default=1.0, description="Memory stability")
    difficulty: float = Field(default=5.0, description="Card difficulty")
    elapsed_days: int = Field(default=0, description="Days since last review")
    scheduled_days: int = Field(default=0, description="Days until next review")
    reps: int = Field(default=0, description="Number of reviews")
    lapses: int = Field(default=0, description="Number of lapses")
    state: str = Field(default="new", description="Card state: new, learning, review, relearning")
    last_review: Optional[datetime] = None
    next_review: datetime = Field(default_factory=datetime.now)


class FSRSReview(BaseModel):
    """FSRS review session result"""

    model_config = ConfigDict(str_strip_whitespace=True)

    card_id: str
    grade: ReviewGrade
    review_date: datetime = Field(default_factory=datetime.now)
    elapsed_days: int = Field(..., ge=0)
    scheduled_days: int = Field(..., ge=0)
    new_stability: float
    new_difficulty: float


# ============================================================================
# CONVERSATION SCHEMAS
# ============================================================================


class ConversationMessage(BaseModel):
    """Message in a conversation context"""

    model_config = ConfigDict(str_strip_whitespace=True)

    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationContext(BaseModel):
    """Conversation context for email threads"""

    model_config = ConfigDict(str_strip_whitespace=True)

    thread_id: str = Field(..., description="Email thread identifier")
    email_ids: List[str] = Field(default_factory=list, description="Email Message-IDs in thread")
    messages: List[ConversationMessage] = Field(default_factory=list)
    summary: Optional[str] = Field(None, description="Conversation summary")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Tracked entities")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# HEALTH CHECK SCHEMAS
# ============================================================================


class ServiceStatus(str, Enum):
    """Service health status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck(BaseModel):
    """Health check result for a service"""

    model_config = ConfigDict(str_strip_whitespace=True)

    service: str = Field(..., description="Service name")
    status: ServiceStatus
    message: str = Field(..., description="Status message")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    checked_at: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class SystemHealth(BaseModel):
    """Overall system health status"""

    model_config = ConfigDict(str_strip_whitespace=True)

    overall_status: ServiceStatus
    checks: List[HealthCheck] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_healthy(self) -> bool:
        """Check if all services are healthy"""
        return self.overall_status == ServiceStatus.HEALTHY

    @property
    def unhealthy_services(self) -> List[str]:
        """Get list of unhealthy services"""
        return [
            check.service
            for check in self.checks
            if check.status == ServiceStatus.UNHEALTHY
        ]
