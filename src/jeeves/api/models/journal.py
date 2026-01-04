"""
Journal API Models

Pydantic models for journal API endpoints.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

# ============================================================================
# REQUEST MODELS
# ============================================================================


class AnswerRequest(BaseModel):
    """Request to answer a journal question"""

    question_id: str = Field(..., description="Question ID to answer")
    answer: str = Field(..., description="User's answer")


class CorrectionRequest(BaseModel):
    """Request to submit a correction"""

    email_id: str = Field(..., description="Email ID being corrected")
    corrected_action: Optional[str] = Field(None, description="Corrected action")
    corrected_category: Optional[str] = Field(None, description="Corrected category")
    reason: Optional[str] = Field(None, description="Reason for correction")
    confidence_override: Optional[int] = Field(
        None, ge=0, le=100, description="Override confidence (0-100)"
    )


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class EmailSummaryResponse(BaseModel):
    """Email summary in journal response"""

    email_id: str
    from_address: str
    from_name: Optional[str] = None
    subject: str
    action: str
    category: str
    confidence: int
    reasoning: Optional[str] = None
    processed_at: datetime


class TaskSummaryResponse(BaseModel):
    """Task summary in journal response"""

    task_id: str
    title: str
    source_email_id: Optional[str] = None
    project: Optional[str] = None
    due_date: Optional[date] = None
    created_at: datetime


class QuestionResponse(BaseModel):
    """Journal question in response"""

    question_id: str
    category: str
    question_text: str
    context: Optional[str] = None
    options: list[str]
    priority: int
    related_email_id: Optional[str] = None
    related_entity: Optional[str] = None
    answer: Optional[str] = None


class CorrectionResponse(BaseModel):
    """Correction in journal response"""

    email_id: str
    original_action: str
    corrected_action: Optional[str] = None
    original_category: Optional[str] = None
    corrected_category: Optional[str] = None
    reason: Optional[str] = None


class TeamsSummaryResponse(BaseModel):
    """Teams message summary in journal response"""

    message_id: str
    chat_name: str
    sender: str
    preview: str
    action: str
    confidence: int
    processed_at: datetime


class CalendarSummaryResponse(BaseModel):
    """Calendar event summary in journal response"""

    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    action: str
    attendees: list[str]
    location: Optional[str] = None
    is_online: bool = False
    notes: Optional[str] = None


class OmniFocusSummaryResponse(BaseModel):
    """OmniFocus item summary in journal response"""

    task_id: str
    title: str
    project: Optional[str] = None
    status: str
    tags: list[str]
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    flagged: bool = False
    estimated_minutes: Optional[int] = None


class JournalEntryResponse(BaseModel):
    """Complete journal entry response"""

    entry_id: str
    journal_date: date
    created_at: datetime
    status: str
    # Metrics
    emails_count: int
    tasks_count: int
    teams_count: int
    calendar_count: int
    omnifocus_count: int
    questions_count: int
    corrections_count: int
    # Lists
    emails_processed: list[EmailSummaryResponse]
    tasks_created: list[TaskSummaryResponse]
    teams_messages: list[TeamsSummaryResponse]
    calendar_events: list[CalendarSummaryResponse]
    omnifocus_items: list[OmniFocusSummaryResponse]
    questions: list[QuestionResponse]
    corrections: list[CorrectionResponse]
    # Computed
    average_confidence: float
    unanswered_questions: int


class JournalListItemResponse(BaseModel):
    """Journal entry in list response"""

    entry_id: str
    journal_date: date
    status: str
    emails_count: int
    questions_count: int
    corrections_count: int
    average_confidence: float
    completed_at: Optional[datetime] = None


# ============================================================================
# REVIEW RESPONSE MODELS
# ============================================================================


class PatternResponse(BaseModel):
    """Detected pattern in review response"""

    pattern_type: str
    description: str
    frequency: int
    confidence: float
    examples: list[str]


class WeeklyReviewResponse(BaseModel):
    """Weekly review response"""

    week_start: date
    week_end: date
    daily_entry_count: int
    patterns_detected: list[PatternResponse]
    productivity_score: float
    top_categories: list[tuple[str, int]]
    suggestions: list[str]
    emails_total: int
    tasks_total: int
    corrections_total: int
    accuracy_rate: float


class MonthlyReviewResponse(BaseModel):
    """Monthly review response"""

    month: date
    weekly_review_count: int
    trends: list[str]
    goals_progress: dict[str, float]
    calibration_summary: dict[str, float]
    productivity_average: float


# ============================================================================
# CALIBRATION RESPONSE MODELS
# ============================================================================


class SourceCalibrationResponse(BaseModel):
    """Calibration data for a source"""

    source: str
    total_items: int
    correct_decisions: int
    incorrect_decisions: int
    accuracy: float
    correction_rate: float
    average_confidence: float
    last_updated: datetime


class CalibrationResponse(BaseModel):
    """Overall calibration response"""

    sources: dict[str, SourceCalibrationResponse]
    overall_accuracy: float
    recommended_threshold_adjustment: int
    patterns_learned: int


# ============================================================================
# EXPORT MODELS
# ============================================================================


class ExportRequest(BaseModel):
    """Request to export journal"""

    format: str = Field(
        default="markdown",
        description="Export format: markdown, json, html"
    )
    include_questions: bool = Field(
        default=True,
        description="Include questions in export"
    )
    include_corrections: bool = Field(
        default=True,
        description="Include corrections in export"
    )
