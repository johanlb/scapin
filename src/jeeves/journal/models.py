"""
Journal Models

Dataclasses for daily journaling and feedback collection.

Summary types (EmailSummary, TaskSummary, etc.) are frozen for immutability.
JournalEntry is mutable to allow updates during interactive session.
"""

import json
import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from src.core.events.universal_event import now_utc


def _escape_markdown_table(text: str) -> str:
    """Escape text for markdown table cells (escape pipes)"""
    return text.replace("|", "\\|")


class JournalStatus(str, Enum):
    """Status of a journal entry"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class QuestionCategory(str, Enum):
    """Category of journal question"""
    # Original categories
    NEW_PERSON = "new_person"          # New person detected
    LOW_CONFIDENCE = "low_confidence"  # Decision with low confidence
    CLARIFICATION = "clarification"    # Need clarification
    ACTION_VERIFY = "action_verify"    # Verify action taken
    # New categories for pattern/preference learning
    PATTERN_CONFIRM = "pattern_confirm"      # Confirm detected pattern
    PREFERENCE_LEARN = "preference_learn"    # Learn user preference
    CALIBRATION_CHECK = "calibration_check"  # Check calibration accuracy
    PRIORITY_REVIEW = "priority_review"      # Review task priorities


# ============================================================================
# SUMMARY MODELS
# ============================================================================


@dataclass(frozen=True)
class EmailSummary:
    """
    Summary of a processed email for journaling

    Contains minimal info needed for journal display and feedback.
    """
    email_id: str
    from_address: str
    subject: str
    action: str
    category: str
    confidence: int  # 0-100
    processed_at: datetime

    # Optional details
    from_name: Optional[str] = None
    reasoning: Optional[str] = None

    def __post_init__(self):
        """Validate email summary"""
        if not (0 <= self.confidence <= 100):
            raise ValueError(f"confidence must be 0-100, got {self.confidence}")
        if not self.email_id:
            raise ValueError("email_id is required")
        if not self.from_address:
            raise ValueError("from_address is required")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "email_id": self.email_id,
            "from_address": self.from_address,
            "from_name": self.from_name,
            "subject": self.subject,
            "action": self.action,
            "category": self.category,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "processed_at": self.processed_at.isoformat(),
        }


@dataclass(frozen=True)
class TaskSummary:
    """Summary of a created task"""
    task_id: str
    title: str
    source_email_id: Optional[str]
    created_at: datetime

    # Optional details
    project: Optional[str] = None
    due_date: Optional[date] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "source_email_id": self.source_email_id,
            "project": self.project,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# MULTI-SOURCE SUMMARY MODELS
# ============================================================================


@dataclass(frozen=True)
class TeamsSummary:
    """
    Summary of a processed Teams message for journaling

    Contains minimal info for journal display and feedback.
    """
    message_id: str
    chat_name: str
    sender: str
    preview: str
    action: str  # e.g., "replied", "flagged", "archived", "task_created"
    confidence: int  # 0-100
    processed_at: datetime

    # Optional details
    chat_type: Optional[str] = None  # "oneOnOne", "group", "meeting"
    importance: Optional[str] = None

    def __post_init__(self):
        """Validate teams summary"""
        if not (0 <= self.confidence <= 100):
            raise ValueError(f"confidence must be 0-100, got {self.confidence}")
        if not self.message_id:
            raise ValueError("message_id is required")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "chat_name": self.chat_name,
            "sender": self.sender,
            "preview": self.preview,
            "action": self.action,
            "confidence": self.confidence,
            "chat_type": self.chat_type,
            "importance": self.importance,
            "processed_at": self.processed_at.isoformat(),
        }


@dataclass(frozen=True)
class CalendarSummary:
    """
    Summary of a calendar event for journaling

    Contains minimal info for journal display and feedback.
    """
    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    action: str  # "attended", "declined", "rescheduled", "cancelled", "pending"
    processed_at: datetime

    # Optional details
    attendees: tuple[str, ...] = field(default_factory=tuple)
    location: Optional[str] = None
    is_online: bool = False
    notes: Optional[str] = None
    response_status: Optional[str] = None  # "accepted", "declined", "tentative"

    def __post_init__(self):
        """Validate calendar summary"""
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.title:
            raise ValueError("title is required")

    @property
    def duration_minutes(self) -> int:
        """Calculate event duration in minutes"""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
            "action": self.action,
            "attendees": list(self.attendees),
            "location": self.location,
            "is_online": self.is_online,
            "notes": self.notes,
            "response_status": self.response_status,
            "processed_at": self.processed_at.isoformat(),
        }


@dataclass(frozen=True)
class OmniFocusSummary:
    """
    Summary of an OmniFocus task for journaling

    Contains minimal info for journal display and feedback.
    """
    task_id: str
    title: str
    status: str  # "completed", "created", "deferred", "due", "overdue"
    processed_at: datetime

    # Optional details
    project: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    flagged: bool = False
    estimated_minutes: Optional[int] = None

    def __post_init__(self):
        """Validate omnifocus summary"""
        if not self.task_id:
            raise ValueError("task_id is required")
        if not self.title:
            raise ValueError("title is required")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "project": self.project,
            "tags": list(self.tags),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "flagged": self.flagged,
            "estimated_minutes": self.estimated_minutes,
            "processed_at": self.processed_at.isoformat(),
        }


@dataclass(frozen=True)
class DecisionSummary:
    """Summary of an automated decision"""
    decision_id: str
    email_id: str
    decision_type: str  # e.g., "archive", "create_task"
    confidence: int
    automated: bool  # True if executed automatically
    timestamp: datetime

    # Result
    success: Optional[bool] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "decision_id": self.decision_id,
            "email_id": self.email_id,
            "decision_type": self.decision_type,
            "confidence": self.confidence,
            "automated": self.automated,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# QUESTION MODEL
# ============================================================================


@dataclass(frozen=True)
class JournalQuestion:
    """
    Targeted question for the user

    Generated based on low-confidence decisions, new entities,
    or other situations requiring user input.
    """
    question_id: str
    category: QuestionCategory
    question_text: str
    context: str  # Why we're asking this question
    options: tuple[str, ...]  # Possible choices (tuple for immutability)

    # Optional link to entity
    related_email_id: Optional[str] = None
    related_entity: Optional[str] = None

    # Priority (1 = high, 5 = low)
    priority: int = 3

    # Answer (None if not yet answered)
    answer: Optional[str] = None

    def __post_init__(self):
        """Validate question"""
        if not (1 <= self.priority <= 5):
            raise ValueError(f"priority must be 1-5, got {self.priority}")
        if not self.question_text:
            raise ValueError("question_text is required")
        if not self.context:
            raise ValueError("context is required")

    def with_answer(self, answer: str) -> "JournalQuestion":
        """Return new question with answer set"""
        return replace(self, answer=answer)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "question_id": self.question_id,
            "category": self.category.value,
            "question_text": self.question_text,
            "context": self.context,
            "options": list(self.options),
            "related_email_id": self.related_email_id,
            "related_entity": self.related_entity,
            "priority": self.priority,
            "answer": self.answer,
        }


# ============================================================================
# CORRECTION MODEL
# ============================================================================


@dataclass(frozen=True)
class Correction:
    """
    User correction on a decision

    Used to train Sganarelle with explicit feedback on
    what the system got wrong.
    """
    correction_id: str
    email_id: str

    # What was predicted
    original_action: str
    original_category: str
    original_confidence: int

    # What should have been
    corrected_action: Optional[str] = None
    corrected_category: Optional[str] = None

    # Context
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=now_utc)

    def __post_init__(self):
        """Validate correction"""
        if not self.email_id:
            raise ValueError("email_id is required")
        if not (0 <= self.original_confidence <= 100):
            raise ValueError(f"original_confidence must be 0-100, got {self.original_confidence}")
        if self.corrected_action is None and self.corrected_category is None:
            raise ValueError("At least one of corrected_action or corrected_category is required")

    @property
    def has_action_correction(self) -> bool:
        """Check if action was corrected"""
        return self.corrected_action is not None

    @property
    def has_category_correction(self) -> bool:
        """Check if category was corrected"""
        return self.corrected_category is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "correction_id": self.correction_id,
            "email_id": self.email_id,
            "original_action": self.original_action,
            "original_category": self.original_category,
            "original_confidence": self.original_confidence,
            "corrected_action": self.corrected_action,
            "corrected_category": self.corrected_category,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# JOURNAL ENTRY
# ============================================================================


@dataclass
class JournalEntry:
    """
    Daily journal entry

    Contains summary of the day's processing, questions for user,
    and collected corrections. Mutable to allow updates during
    interactive session.

    Multi-source support: Email, Teams, Calendar, OmniFocus.
    """
    journal_date: date
    created_at: datetime

    # Summary of the day - Email (required for backwards compatibility)
    emails_processed: list[EmailSummary]
    tasks_created: list[TaskSummary]
    decisions: list[DecisionSummary]

    # Questions for user
    questions: list[JournalQuestion]

    # Multi-source data (optional)
    teams_messages: list[TeamsSummary] = field(default_factory=list)
    calendar_events: list[CalendarSummary] = field(default_factory=list)
    omnifocus_items: list[OmniFocusSummary] = field(default_factory=list)

    # Editable content
    notes: str = ""
    reflections: str = ""

    # User corrections
    corrections: list[Correction] = field(default_factory=list)

    # Metadata
    status: JournalStatus = JournalStatus.DRAFT
    duration_minutes: Optional[int] = None

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ----------------------------------------------------------------
    # COMPUTED PROPERTIES
    # ----------------------------------------------------------------

    @property
    def high_confidence_emails(self) -> list[EmailSummary]:
        """Emails with confidence >= 85%"""
        return [e for e in self.emails_processed if e.confidence >= 85]

    @property
    def low_confidence_emails(self) -> list[EmailSummary]:
        """Emails with confidence < 85%"""
        return [e for e in self.emails_processed if e.confidence < 85]

    @property
    def answered_questions(self) -> list[JournalQuestion]:
        """Questions that have been answered"""
        return [q for q in self.questions if q.answer is not None]

    @property
    def unanswered_questions(self) -> list[JournalQuestion]:
        """Questions not yet answered"""
        return [q for q in self.questions if q.answer is None]

    @property
    def average_confidence(self) -> float:
        """Average confidence across all processed emails"""
        if not self.emails_processed:
            return 0.0
        return sum(e.confidence for e in self.emails_processed) / len(self.emails_processed)

    # ----------------------------------------------------------------
    # MUTATION METHODS
    # ----------------------------------------------------------------

    def answer_question(self, question_id: str, answer: str) -> bool:
        """
        Answer a question by ID

        Returns True if question was found and answered.
        """
        for i, q in enumerate(self.questions):
            if q.question_id == question_id:
                self.questions[i] = q.with_answer(answer)
                return True
        return False

    def add_correction(self, correction: Correction) -> None:
        """Add a correction"""
        self.corrections.append(correction)

    def complete(self, duration_minutes: int) -> None:
        """Mark journal as completed"""
        self.status = JournalStatus.COMPLETED
        self.duration_minutes = duration_minutes

    # ----------------------------------------------------------------
    # SERIALIZATION
    # ----------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "entry_id": self.entry_id,
            "journal_date": self.journal_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "duration_minutes": self.duration_minutes,
            # Email data
            "emails_processed": [e.to_dict() for e in self.emails_processed],
            "tasks_created": [t.to_dict() for t in self.tasks_created],
            "decisions": [d.to_dict() for d in self.decisions],
            # Multi-source data
            "teams_messages": [m.to_dict() for m in self.teams_messages],
            "calendar_events": [e.to_dict() for e in self.calendar_events],
            "omnifocus_items": [i.to_dict() for i in self.omnifocus_items],
            # Questions and corrections
            "questions": [q.to_dict() for q in self.questions],
            "corrections": [c.to_dict() for c in self.corrections],
            "notes": self.notes,
            "reflections": self.reflections,
            "summary": {
                "total_emails": len(self.emails_processed),
                "high_confidence_count": len(self.high_confidence_emails),
                "low_confidence_count": len(self.low_confidence_emails),
                "average_confidence": self.average_confidence,
                "total_teams_messages": len(self.teams_messages),
                "total_calendar_events": len(self.calendar_events),
                "total_omnifocus_items": len(self.omnifocus_items),
                "questions_total": len(self.questions),
                "questions_answered": len(self.answered_questions),
                "corrections_count": len(self.corrections),
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """
        Convert to Markdown format for display/export

        Follows the format specified in the plan.
        Multi-source: Email, Teams, Calendar, OmniFocus.
        """
        lines = [
            "---",
            f"date: {self.journal_date.isoformat()}",
            f"status: {self.status.value}",
            f"emails_processed: {len(self.emails_processed)}",
            f"teams_messages: {len(self.teams_messages)}",
            f"calendar_events: {len(self.calendar_events)}",
            f"omnifocus_items: {len(self.omnifocus_items)}",
            f"questions_answered: {len(self.answered_questions)}",
            f"corrections: {len(self.corrections)}",
        ]
        if self.duration_minutes is not None:
            lines.append(f"duration_minutes: {self.duration_minutes}")
        lines.extend([
            "---",
            "",
            f"# Journal du {self.journal_date.strftime('%d %B %Y')}",
            "",
        ])

        # Emails processed section
        if self.emails_processed:
            lines.append(f"## Emails Traites ({len(self.emails_processed)})")
            lines.append("")

            if self.high_confidence_emails:
                lines.append("### Haute confiance (>=85%)")
                lines.append("| De | Sujet | Action | Confiance |")
                lines.append("|----|-------|--------|-----------|")
                for email in self.high_confidence_emails:
                    from_display = _escape_markdown_table(email.from_name or email.from_address)
                    subject = _escape_markdown_table(email.subject[:40])
                    lines.append(f"| {from_display} | {subject} | {email.action.capitalize()} | {email.confidence}% |")
                lines.append("")

            if self.low_confidence_emails:
                lines.append("### Basse confiance (<85%)")
                lines.append("| De | Sujet | Action | Confiance |")
                lines.append("|----|-------|--------|-----------|")
                for email in self.low_confidence_emails:
                    from_display = _escape_markdown_table(email.from_name or email.from_address)
                    subject = _escape_markdown_table(email.subject[:40])
                    lines.append(f"| {from_display} | {subject} | {email.action.capitalize()} | {email.confidence}% |")
                lines.append("")

        # Teams messages section
        if self.teams_messages:
            lines.append(f"## Messages Teams ({len(self.teams_messages)})")
            lines.append("")
            lines.append("| Chat | Expediteur | Apercu | Action | Confiance |")
            lines.append("|------|------------|--------|--------|-----------|")
            for msg in self.teams_messages:
                chat = _escape_markdown_table(msg.chat_name[:20])
                sender = _escape_markdown_table(msg.sender[:15])
                preview = _escape_markdown_table(msg.preview[:30])
                lines.append(f"| {chat} | {sender} | {preview}... | {msg.action.capitalize()} | {msg.confidence}% |")
            lines.append("")

        # Calendar events section
        if self.calendar_events:
            lines.append(f"## Evenements Calendrier ({len(self.calendar_events)})")
            lines.append("")
            lines.append("| Heure | Titre | Duree | Action |")
            lines.append("|-------|-------|-------|--------|")
            for event in self.calendar_events:
                time_str = event.start_time.strftime("%H:%M")
                title = _escape_markdown_table(event.title[:30])
                duration = f"{event.duration_minutes}min"
                lines.append(f"| {time_str} | {title} | {duration} | {event.action.capitalize()} |")
            lines.append("")

        # OmniFocus section
        if self.omnifocus_items:
            lines.append(f"## Taches OmniFocus ({len(self.omnifocus_items)})")
            lines.append("")

            # Group by status
            completed = [i for i in self.omnifocus_items if i.status == "completed"]
            created = [i for i in self.omnifocus_items if i.status == "created"]
            due = [i for i in self.omnifocus_items if i.status in ("due", "overdue")]

            if completed:
                lines.append("### Completees")
                for item in completed:
                    project = f" [{item.project}]" if item.project else ""
                    lines.append(f"- ✓ {item.title}{project}")
                lines.append("")

            if created:
                lines.append("### Creees")
                for item in created:
                    project = f" [{item.project}]" if item.project else ""
                    lines.append(f"- + {item.title}{project}")
                lines.append("")

            if due:
                lines.append("### Dues/En retard")
                for item in due:
                    project = f" [{item.project}]" if item.project else ""
                    flag = "⚠" if item.status == "overdue" else "📅"
                    lines.append(f"- {flag} {item.title}{project}")
                lines.append("")

        # Tasks created section
        if self.tasks_created:
            lines.append(f"## Taches Creees depuis Email ({len(self.tasks_created)})")
            lines.append("")
            for task in self.tasks_created:
                project_info = f" [{task.project}]" if task.project else ""
                due_info = f" (echeance: {task.due_date})" if task.due_date else ""
                lines.append(f"- {task.title}{project_info}{due_info}")
            lines.append("")

        # Questions answered section
        if self.answered_questions:
            lines.append(f"## Questions Repondues ({len(self.answered_questions)})")
            lines.append("")
            for i, q in enumerate(self.answered_questions, 1):
                category_label = {
                    QuestionCategory.NEW_PERSON: "Nouvelle personne",
                    QuestionCategory.LOW_CONFIDENCE: "Verification",
                    QuestionCategory.CLARIFICATION: "Clarification",
                    QuestionCategory.ACTION_VERIFY: "Verification action",
                    QuestionCategory.PATTERN_CONFIRM: "Pattern detecte",
                    QuestionCategory.PREFERENCE_LEARN: "Preference",
                    QuestionCategory.CALIBRATION_CHECK: "Calibration",
                    QuestionCategory.PRIORITY_REVIEW: "Priorites",
                }.get(q.category, q.category.value)

                lines.append(f"### Q{i} : {category_label}")
                lines.append(f"> {q.question_text}")
                lines.append(f"**Reponse** : {q.answer}")
                lines.append("")

        # Corrections section
        if self.corrections:
            lines.append(f"## Corrections ({len(self.corrections)})")
            lines.append("")
            for i, c in enumerate(self.corrections, 1):
                correction_details = []
                if c.has_action_correction:
                    correction_details.append(f'Action "{c.original_action}" -> "{c.corrected_action}"')
                if c.has_category_correction:
                    correction_details.append(f'Categorie "{c.original_category}" -> "{c.corrected_category}"')

                lines.append(f"{i}. **Email** : {c.email_id[:20]}...")
                for detail in correction_details:
                    lines.append(f"   - {detail}")
                if c.reason:
                    lines.append(f"   - Raison : {c.reason}")
                lines.append("")

        # Notes section
        lines.append("## Notes libres")
        lines.append("")
        if self.notes:
            lines.append(self.notes)
        else:
            lines.append("_Aucune note_")
        lines.append("")

        # Footer
        lines.extend([
            "---",
            "*Journal genere par Scapin*",
        ])
        if self.corrections:
            lines.append("*Feedback envoye a Sganarelle pour amelioration continue*")

        return "\n".join(lines)
