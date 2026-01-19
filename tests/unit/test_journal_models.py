"""
Tests for Journal Models

Tests the dataclasses and enums for daily journaling.
"""

import json
from datetime import date, datetime, timezone

import pytest

from src.frontin.journal.models import (
    CalendarSummary,
    Correction,
    DecisionSummary,
    EmailSummary,
    JournalEntry,
    JournalQuestion,
    JournalStatus,
    OmniFocusSummary,
    QuestionCategory,
    TaskSummary,
    TeamsSummary,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_datetime():
    """Sample datetime for tests"""
    return datetime(2026, 1, 2, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_email_summary(sample_datetime):
    """Sample email summary"""
    return EmailSummary(
        email_id="email-123",
        from_address="sender@example.com",
        from_name="John Sender",
        subject="Test Subject",
        action="archive",
        category="work",
        confidence=85,
        reasoning="High-priority work email",
        processed_at=sample_datetime,
    )


@pytest.fixture
def sample_task_summary(sample_datetime):
    """Sample task summary"""
    return TaskSummary(
        task_id="task-456",
        title="Follow up on email",
        source_email_id="email-123",
        project="Work",
        due_date=date(2026, 1, 5),
        created_at=sample_datetime,
    )


@pytest.fixture
def sample_decision_summary(sample_datetime):
    """Sample decision summary"""
    return DecisionSummary(
        decision_id="decision-789",
        email_id="email-123",
        decision_type="archive",
        confidence=85,
        automated=True,
        success=True,
        timestamp=sample_datetime,
    )


@pytest.fixture
def sample_question():
    """Sample journal question"""
    return JournalQuestion(
        question_id="q-001",
        category=QuestionCategory.LOW_CONFIDENCE,
        question_text="Was this decision correct?",
        context="Low confidence detection",
        options=("Yes", "No", "Not sure"),
        related_email_id="email-123",
        priority=1,
    )


@pytest.fixture
def sample_correction(sample_datetime):
    """Sample correction"""
    return Correction(
        correction_id="corr-001",
        email_id="email-123",
        original_action="archive",
        original_category="work",
        original_confidence=85,
        corrected_action="delete",
        reason="Should be deleted",
        timestamp=sample_datetime,
    )


@pytest.fixture
def sample_journal_entry(
    sample_email_summary,
    sample_task_summary,
    sample_decision_summary,
    sample_question,
    sample_datetime,
):
    """Sample journal entry"""
    return JournalEntry(
        journal_date=date(2026, 1, 2),
        created_at=sample_datetime,
        emails_processed=[sample_email_summary],
        tasks_created=[sample_task_summary],
        decisions=[sample_decision_summary],
        questions=[sample_question],
    )


# ============================================================================
# EMAIL SUMMARY TESTS
# ============================================================================


class TestEmailSummary:
    """Tests for EmailSummary"""

    def test_create_email_summary(self, sample_email_summary):
        """Test creating email summary"""
        assert sample_email_summary.email_id == "email-123"
        assert sample_email_summary.from_address == "sender@example.com"
        assert sample_email_summary.subject == "Test Subject"
        assert sample_email_summary.confidence == 85

    def test_email_summary_to_dict(self, sample_email_summary):
        """Test email summary serialization"""
        d = sample_email_summary.to_dict()
        assert d["email_id"] == "email-123"
        assert d["from_address"] == "sender@example.com"
        assert d["from_name"] == "John Sender"
        assert "processed_at" in d

    def test_email_summary_without_optional_fields(self, sample_datetime):
        """Test email summary without optional fields"""
        summary = EmailSummary(
            email_id="email-456",
            from_address="sender@example.com",
            subject="Test",
            action="archive",
            category="work",
            confidence=90,
            processed_at=sample_datetime,
        )
        assert summary.from_name is None
        assert summary.reasoning is None

    def test_email_summary_validation_confidence(self, sample_datetime):
        """Test email summary validates confidence range"""
        with pytest.raises(ValueError, match="confidence must be 0-100"):
            EmailSummary(
                email_id="email-456",
                from_address="sender@example.com",
                subject="Test",
                action="archive",
                category="work",
                confidence=150,  # Invalid: > 100
                processed_at=sample_datetime,
            )

    def test_email_summary_validation_negative_confidence(self, sample_datetime):
        """Test email summary validates confidence not negative"""
        with pytest.raises(ValueError, match="confidence must be 0-100"):
            EmailSummary(
                email_id="email-456",
                from_address="sender@example.com",
                subject="Test",
                action="archive",
                category="work",
                confidence=-10,  # Invalid: negative
                processed_at=sample_datetime,
            )

    def test_email_summary_validation_email_id(self, sample_datetime):
        """Test email summary requires email_id"""
        with pytest.raises(ValueError, match="email_id is required"):
            EmailSummary(
                email_id="",  # Invalid: empty
                from_address="sender@example.com",
                subject="Test",
                action="archive",
                category="work",
                confidence=85,
                processed_at=sample_datetime,
            )

    def test_email_summary_validation_from_address(self, sample_datetime):
        """Test email summary requires from_address"""
        with pytest.raises(ValueError, match="from_address is required"):
            EmailSummary(
                email_id="email-456",
                from_address="",  # Invalid: empty
                subject="Test",
                action="archive",
                category="work",
                confidence=85,
                processed_at=sample_datetime,
            )


# ============================================================================
# TASK SUMMARY TESTS
# ============================================================================


class TestTaskSummary:
    """Tests for TaskSummary"""

    def test_create_task_summary(self, sample_task_summary):
        """Test creating task summary"""
        assert sample_task_summary.task_id == "task-456"
        assert sample_task_summary.title == "Follow up on email"
        assert sample_task_summary.project == "Work"

    def test_task_summary_to_dict(self, sample_task_summary):
        """Test task summary serialization"""
        d = sample_task_summary.to_dict()
        assert d["task_id"] == "task-456"
        assert d["due_date"] == "2026-01-05"


# ============================================================================
# QUESTION TESTS
# ============================================================================


class TestJournalQuestion:
    """Tests for JournalQuestion"""

    def test_create_question(self, sample_question):
        """Test creating question"""
        assert sample_question.question_id == "q-001"
        assert sample_question.category == QuestionCategory.LOW_CONFIDENCE
        assert sample_question.priority == 1

    def test_question_validation_priority(self):
        """Test priority validation"""
        with pytest.raises(ValueError, match="priority must be 1-5"):
            JournalQuestion(
                question_id="q-bad",
                category=QuestionCategory.LOW_CONFIDENCE,
                question_text="Test?",
                context="Test context",
                options=("Yes", "No"),
                priority=0,  # Invalid
            )

        with pytest.raises(ValueError, match="priority must be 1-5"):
            JournalQuestion(
                question_id="q-bad",
                category=QuestionCategory.LOW_CONFIDENCE,
                question_text="Test?",
                context="Test context",
                options=("Yes", "No"),
                priority=6,  # Invalid
            )

    def test_question_validation_empty_text(self):
        """Test empty question text validation"""
        with pytest.raises(ValueError, match="question_text is required"):
            JournalQuestion(
                question_id="q-bad",
                category=QuestionCategory.LOW_CONFIDENCE,
                question_text="",  # Empty
                context="Test context",
                options=("Yes", "No"),
            )

    def test_question_with_answer(self, sample_question):
        """Test answering a question"""
        answered = sample_question.with_answer("Yes")
        assert answered.answer == "Yes"
        # Original should be unchanged (immutable)
        assert sample_question.answer is None

    def test_question_to_dict(self, sample_question):
        """Test question serialization"""
        d = sample_question.to_dict()
        assert d["question_id"] == "q-001"
        assert d["category"] == "low_confidence"
        assert d["options"] == ["Yes", "No", "Not sure"]


# ============================================================================
# CORRECTION TESTS
# ============================================================================


class TestCorrection:
    """Tests for Correction"""

    def test_create_correction(self, sample_correction):
        """Test creating correction"""
        assert sample_correction.email_id == "email-123"
        assert sample_correction.original_action == "archive"
        assert sample_correction.corrected_action == "delete"

    def test_correction_validation_confidence(self):
        """Test confidence validation"""
        with pytest.raises(ValueError, match="original_confidence must be 0-100"):
            Correction(
                correction_id="corr-bad",
                email_id="email-123",
                original_action="archive",
                original_category="work",
                original_confidence=150,  # Invalid
                corrected_action="delete",
            )

    def test_correction_validation_no_correction(self):
        """Test that at least one correction is required"""
        with pytest.raises(ValueError, match="At least one of corrected_action or corrected_category"):
            Correction(
                correction_id="corr-bad",
                email_id="email-123",
                original_action="archive",
                original_category="work",
                original_confidence=85,
                # No corrected_action or corrected_category
            )

    def test_correction_properties(self, sample_correction):
        """Test correction properties"""
        assert sample_correction.has_action_correction is True
        assert sample_correction.has_category_correction is False

    def test_correction_category_only(self, sample_datetime):
        """Test correction with category only"""
        correction = Correction(
            correction_id="corr-cat",
            email_id="email-123",
            original_action="archive",
            original_category="work",
            original_confidence=85,
            corrected_category="personal",  # Only category
            timestamp=sample_datetime,
        )
        assert correction.has_action_correction is False
        assert correction.has_category_correction is True


# ============================================================================
# JOURNAL ENTRY TESTS
# ============================================================================


class TestJournalEntry:
    """Tests for JournalEntry"""

    def test_create_journal_entry(self, sample_journal_entry):
        """Test creating journal entry"""
        assert sample_journal_entry.journal_date == date(2026, 1, 2)
        assert len(sample_journal_entry.emails_processed) == 1
        assert len(sample_journal_entry.questions) == 1
        assert sample_journal_entry.status == JournalStatus.DRAFT

    def test_high_confidence_emails(self, sample_journal_entry):
        """Test high confidence emails filter"""
        high = sample_journal_entry.high_confidence_emails
        assert len(high) == 1  # 85% is >= 85%

    def test_low_confidence_emails(self, sample_datetime):
        """Test low confidence emails filter"""
        low_conf_email = EmailSummary(
            email_id="low-123",
            from_address="sender@example.com",
            subject="Low confidence",
            action="archive",
            category="work",
            confidence=70,
            processed_at=sample_datetime,
        )
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[low_conf_email],
            tasks_created=[],
            decisions=[],
            questions=[],
        )
        assert len(entry.low_confidence_emails) == 1

    def test_answer_question(self, sample_journal_entry):
        """Test answering a question"""
        question_id = sample_journal_entry.questions[0].question_id
        result = sample_journal_entry.answer_question(question_id, "Yes")
        assert result is True
        assert sample_journal_entry.answered_questions[0].answer == "Yes"

    def test_answer_question_not_found(self, sample_journal_entry):
        """Test answering non-existent question"""
        result = sample_journal_entry.answer_question("non-existent", "Yes")
        assert result is False

    def test_add_correction(self, sample_journal_entry, sample_correction):
        """Test adding a correction"""
        initial_count = len(sample_journal_entry.corrections)
        sample_journal_entry.add_correction(sample_correction)
        assert len(sample_journal_entry.corrections) == initial_count + 1

    def test_complete_journal(self, sample_journal_entry):
        """Test completing journal"""
        sample_journal_entry.complete(duration_minutes=15)
        assert sample_journal_entry.status == JournalStatus.COMPLETED
        assert sample_journal_entry.duration_minutes == 15

    def test_to_dict(self, sample_journal_entry):
        """Test journal entry serialization"""
        d = sample_journal_entry.to_dict()
        assert d["journal_date"] == "2026-01-02"
        assert d["status"] == "draft"
        assert "summary" in d
        assert d["summary"]["total_emails"] == 1

    def test_to_json(self, sample_journal_entry):
        """Test JSON serialization"""
        json_str = sample_journal_entry.to_json()
        parsed = json.loads(json_str)
        assert parsed["journal_date"] == "2026-01-02"

    def test_to_markdown(self, sample_journal_entry):
        """Test markdown generation"""
        md = sample_journal_entry.to_markdown()
        assert "# Journal du" in md
        assert "Emails Traites" in md
        assert "Test Subject" in md

    def test_to_markdown_escapes_pipes(self, sample_datetime):
        """Test markdown generation escapes pipe characters in tables"""
        email_with_pipe = EmailSummary(
            email_id="email-pipe",
            from_address="test|pipe@example.com",
            from_name="Test | Pipe",
            subject="Subject | with | pipes",
            action="archive",
            category="work",
            confidence=90,
            processed_at=sample_datetime,
        )
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[email_with_pipe],
            tasks_created=[],
            decisions=[],
            questions=[],
        )
        md = entry.to_markdown()
        # Pipes should be escaped in the table
        assert "\\|" in md
        # The table should still be valid (4 pipes per row + escaped ones)
        assert "Test \\| Pipe" in md or "Subject \\| with \\| pipes" in md

    def test_average_confidence(self, sample_journal_entry):
        """Test average confidence calculation"""
        assert sample_journal_entry.average_confidence == 85.0

    def test_average_confidence_empty(self, sample_datetime):
        """Test average confidence with no emails"""
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[],
            tasks_created=[],
            decisions=[],
            questions=[],
        )
        assert entry.average_confidence == 0.0


# ============================================================================
# ENUM TESTS
# ============================================================================


class TestEnums:
    """Tests for enums"""

    def test_journal_status_values(self):
        """Test journal status values"""
        assert JournalStatus.DRAFT.value == "draft"
        assert JournalStatus.IN_PROGRESS.value == "in_progress"
        assert JournalStatus.COMPLETED.value == "completed"

    def test_question_category_values(self):
        """Test question category values"""
        assert QuestionCategory.NEW_PERSON.value == "new_person"
        assert QuestionCategory.LOW_CONFIDENCE.value == "low_confidence"
        assert QuestionCategory.CLARIFICATION.value == "clarification"
        assert QuestionCategory.ACTION_VERIFY.value == "action_verify"

    def test_question_category_new_values(self):
        """Test new question category values for pattern learning"""
        assert QuestionCategory.PATTERN_CONFIRM.value == "pattern_confirm"
        assert QuestionCategory.PREFERENCE_LEARN.value == "preference_learn"
        assert QuestionCategory.CALIBRATION_CHECK.value == "calibration_check"
        assert QuestionCategory.PRIORITY_REVIEW.value == "priority_review"


# ============================================================================
# TEAMS SUMMARY TESTS
# ============================================================================


@pytest.fixture
def sample_teams_summary(sample_datetime):
    """Sample Teams message summary"""
    return TeamsSummary(
        message_id="teams-001",
        chat_name="Project Alpha",
        sender="Alice Smith",
        preview="Can you review the latest changes?",
        action="flagged",
        confidence=78,
        processed_at=sample_datetime,
        chat_type="group",
        importance="high",
    )


class TestTeamsSummary:
    """Tests for TeamsSummary"""

    def test_create_teams_summary(self, sample_teams_summary):
        """Test creating teams summary"""
        assert sample_teams_summary.message_id == "teams-001"
        assert sample_teams_summary.chat_name == "Project Alpha"
        assert sample_teams_summary.sender == "Alice Smith"
        assert sample_teams_summary.confidence == 78

    def test_teams_summary_to_dict(self, sample_teams_summary):
        """Test teams summary serialization"""
        d = sample_teams_summary.to_dict()
        assert d["message_id"] == "teams-001"
        assert d["chat_name"] == "Project Alpha"
        assert d["chat_type"] == "group"
        assert d["importance"] == "high"

    def test_teams_summary_validation_confidence(self, sample_datetime):
        """Test teams summary validates confidence range"""
        with pytest.raises(ValueError, match="confidence must be 0-100"):
            TeamsSummary(
                message_id="teams-002",
                chat_name="Test Chat",
                sender="Test User",
                preview="Test message",
                action="read",
                confidence=200,
                processed_at=sample_datetime,
            )

    def test_teams_summary_validation_message_id(self, sample_datetime):
        """Test teams summary requires message_id"""
        with pytest.raises(ValueError, match="message_id is required"):
            TeamsSummary(
                message_id="",
                chat_name="Test Chat",
                sender="Test User",
                preview="Test message",
                action="read",
                confidence=50,
                processed_at=sample_datetime,
            )

    def test_teams_summary_optional_fields(self, sample_datetime):
        """Test teams summary without optional fields"""
        summary = TeamsSummary(
            message_id="teams-003",
            chat_name="Test",
            sender="User",
            preview="Message",
            action="read",
            confidence=90,
            processed_at=sample_datetime,
        )
        assert summary.chat_type is None
        assert summary.importance is None


# ============================================================================
# CALENDAR SUMMARY TESTS
# ============================================================================


@pytest.fixture
def sample_calendar_summary(sample_datetime):
    """Sample calendar event summary"""
    return CalendarSummary(
        event_id="cal-001",
        title="Team Standup",
        start_time=sample_datetime,
        end_time=sample_datetime.replace(hour=11, minute=0),
        action="attended",
        processed_at=sample_datetime,
        attendees=("Alice", "Bob", "Charlie"),
        location="Room 101",
        is_online=False,
        notes="Discussed sprint progress",
        response_status="accepted",
    )


class TestCalendarSummary:
    """Tests for CalendarSummary"""

    def test_create_calendar_summary(self, sample_calendar_summary):
        """Test creating calendar summary"""
        assert sample_calendar_summary.event_id == "cal-001"
        assert sample_calendar_summary.title == "Team Standup"
        assert len(sample_calendar_summary.attendees) == 3

    def test_calendar_summary_duration_minutes(self, sample_calendar_summary):
        """Test duration calculation"""
        assert sample_calendar_summary.duration_minutes == 30

    def test_calendar_summary_to_dict(self, sample_calendar_summary):
        """Test calendar summary serialization"""
        d = sample_calendar_summary.to_dict()
        assert d["event_id"] == "cal-001"
        assert d["title"] == "Team Standup"
        assert d["duration_minutes"] == 30
        assert d["attendees"] == ["Alice", "Bob", "Charlie"]

    def test_calendar_summary_validation_event_id(self, sample_datetime):
        """Test calendar summary requires event_id"""
        with pytest.raises(ValueError, match="event_id is required"):
            CalendarSummary(
                event_id="",
                title="Test Event",
                start_time=sample_datetime,
                end_time=sample_datetime,
                action="pending",
                processed_at=sample_datetime,
            )

    def test_calendar_summary_validation_title(self, sample_datetime):
        """Test calendar summary requires title"""
        with pytest.raises(ValueError, match="title is required"):
            CalendarSummary(
                event_id="cal-003",
                title="",
                start_time=sample_datetime,
                end_time=sample_datetime,
                action="pending",
                processed_at=sample_datetime,
            )

    def test_calendar_summary_default_attendees(self, sample_datetime):
        """Test default attendees tuple"""
        summary = CalendarSummary(
            event_id="cal-004",
            title="Solo Event",
            start_time=sample_datetime,
            end_time=sample_datetime.replace(hour=12),
            action="attended",
            processed_at=sample_datetime,
        )
        assert summary.attendees == ()
        assert len(summary.attendees) == 0


# ============================================================================
# OMNIFOCUS SUMMARY TESTS
# ============================================================================


@pytest.fixture
def sample_omnifocus_summary(sample_datetime):
    """Sample OmniFocus task summary"""
    return OmniFocusSummary(
        task_id="of-001",
        title="Review PR #123",
        status="completed",
        processed_at=sample_datetime,
        project="Code Reviews",
        tags=("urgent", "dev"),
        completed_at=sample_datetime,
        due_date=sample_datetime.replace(hour=17),
        flagged=True,
        estimated_minutes=30,
    )


class TestOmniFocusSummary:
    """Tests for OmniFocusSummary"""

    def test_create_omnifocus_summary(self, sample_omnifocus_summary):
        """Test creating omnifocus summary"""
        assert sample_omnifocus_summary.task_id == "of-001"
        assert sample_omnifocus_summary.title == "Review PR #123"
        assert sample_omnifocus_summary.status == "completed"
        assert sample_omnifocus_summary.flagged is True

    def test_omnifocus_summary_to_dict(self, sample_omnifocus_summary):
        """Test omnifocus summary serialization"""
        d = sample_omnifocus_summary.to_dict()
        assert d["task_id"] == "of-001"
        assert d["project"] == "Code Reviews"
        assert d["tags"] == ["urgent", "dev"]
        assert d["flagged"] is True
        assert d["estimated_minutes"] == 30

    def test_omnifocus_summary_validation_task_id(self, sample_datetime):
        """Test omnifocus summary requires task_id"""
        with pytest.raises(ValueError, match="task_id is required"):
            OmniFocusSummary(
                task_id="",
                title="Test Task",
                status="created",
                processed_at=sample_datetime,
            )

    def test_omnifocus_summary_validation_title(self, sample_datetime):
        """Test omnifocus summary requires title"""
        with pytest.raises(ValueError, match="title is required"):
            OmniFocusSummary(
                task_id="of-002",
                title="",
                status="created",
                processed_at=sample_datetime,
            )

    def test_omnifocus_summary_minimal(self, sample_datetime):
        """Test omnifocus summary with minimal fields"""
        summary = OmniFocusSummary(
            task_id="of-003",
            title="Simple Task",
            status="created",
            processed_at=sample_datetime,
        )
        assert summary.project is None
        assert summary.tags == ()
        assert summary.completed_at is None
        assert summary.flagged is False


# ============================================================================
# MULTI-SOURCE JOURNAL ENTRY TESTS
# ============================================================================


class TestJournalEntryMultiSource:
    """Tests for JournalEntry with multi-source data"""

    def test_journal_entry_with_teams(
        self,
        sample_email_summary,
        sample_task_summary,
        sample_decision_summary,
        sample_question,
        sample_teams_summary,
        sample_datetime,
    ):
        """Test journal entry with Teams messages"""
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[sample_email_summary],
            tasks_created=[sample_task_summary],
            decisions=[sample_decision_summary],
            questions=[sample_question],
            teams_messages=[sample_teams_summary],
        )
        assert len(entry.teams_messages) == 1
        assert entry.teams_messages[0].chat_name == "Project Alpha"

    def test_journal_entry_with_calendar(
        self,
        sample_email_summary,
        sample_task_summary,
        sample_decision_summary,
        sample_question,
        sample_calendar_summary,
        sample_datetime,
    ):
        """Test journal entry with calendar events"""
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[sample_email_summary],
            tasks_created=[sample_task_summary],
            decisions=[sample_decision_summary],
            questions=[sample_question],
            calendar_events=[sample_calendar_summary],
        )
        assert len(entry.calendar_events) == 1
        assert entry.calendar_events[0].title == "Team Standup"

    def test_journal_entry_with_omnifocus(
        self,
        sample_email_summary,
        sample_task_summary,
        sample_decision_summary,
        sample_question,
        sample_omnifocus_summary,
        sample_datetime,
    ):
        """Test journal entry with OmniFocus items"""
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[sample_email_summary],
            tasks_created=[sample_task_summary],
            decisions=[sample_decision_summary],
            questions=[sample_question],
            omnifocus_items=[sample_omnifocus_summary],
        )
        assert len(entry.omnifocus_items) == 1
        assert entry.omnifocus_items[0].title == "Review PR #123"

    def test_journal_entry_to_dict_with_multi_source(
        self,
        sample_email_summary,
        sample_teams_summary,
        sample_calendar_summary,
        sample_omnifocus_summary,
        sample_datetime,
    ):
        """Test journal entry serialization with multi-source data"""
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[sample_email_summary],
            tasks_created=[],
            decisions=[],
            questions=[],
            teams_messages=[sample_teams_summary],
            calendar_events=[sample_calendar_summary],
            omnifocus_items=[sample_omnifocus_summary],
        )
        d = entry.to_dict()
        assert len(d["teams_messages"]) == 1
        assert len(d["calendar_events"]) == 1
        assert len(d["omnifocus_items"]) == 1
        assert d["summary"]["total_teams_messages"] == 1
        assert d["summary"]["total_calendar_events"] == 1
        assert d["summary"]["total_omnifocus_items"] == 1

    def test_journal_entry_to_markdown_with_multi_source(
        self,
        sample_email_summary,
        sample_teams_summary,
        sample_calendar_summary,
        sample_omnifocus_summary,
        sample_datetime,
    ):
        """Test journal entry markdown with multi-source data"""
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[sample_email_summary],
            tasks_created=[],
            decisions=[],
            questions=[],
            teams_messages=[sample_teams_summary],
            calendar_events=[sample_calendar_summary],
            omnifocus_items=[sample_omnifocus_summary],
        )
        md = entry.to_markdown()
        assert "## Messages Teams" in md
        assert "Project Alpha" in md
        assert "## Evenements Calendrier" in md
        assert "Team Standup" in md
        assert "## Taches OmniFocus" in md
        assert "Review PR #123" in md
