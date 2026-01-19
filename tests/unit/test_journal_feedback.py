"""
Tests for Journal Feedback Processor

Tests the conversion of journal corrections to Sganarelle feedback.
"""

import json
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.frontin.journal.feedback import (
    CalibrationAnalysis,
    FeedbackProcessingResult,
    JournalFeedbackProcessor,
    SourceCalibration,
    StoredFeedback,
    WeeklyReviewResult,
    process_corrections,
)
from src.frontin.journal.models import (
    Correction,
    EmailSummary,
    JournalEntry,
    JournalQuestion,
    QuestionCategory,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_datetime():
    """Sample datetime"""
    return datetime(2026, 1, 2, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_email(sample_datetime):
    """Sample email summary"""
    return EmailSummary(
        email_id="email-123",
        from_address="sender@example.com",
        subject="Test Subject",
        action="archive",
        category="work",
        confidence=85,
        processed_at=sample_datetime,
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
def sample_question():
    """Sample answered question"""
    return JournalQuestion(
        question_id="q-001",
        category=QuestionCategory.NEW_PERSON,
        question_text="Who is this person?",
        context="New sender detected",
        options=("Colleague", "Client", "Personal"),
        related_email_id="email-123",
        related_entity="new@example.com",
        answer="Colleague",
    )


@pytest.fixture
def sample_journal_entry(sample_email, sample_correction, sample_question, sample_datetime):
    """Sample journal entry with corrections and answers"""
    return JournalEntry(
        journal_date=date(2026, 1, 2),
        created_at=sample_datetime,
        emails_processed=[sample_email],
        tasks_created=[],
        decisions=[],
        questions=[sample_question],
        corrections=[sample_correction],
    )


# ============================================================================
# FEEDBACK PROCESSOR TESTS
# ============================================================================


class TestJournalFeedbackProcessor:
    """Tests for JournalFeedbackProcessor"""

    def test_process_empty_entry(self, tmp_path, sample_datetime):
        """Test processing entry with no corrections or answers"""
        entry = JournalEntry(
            journal_date=date(2026, 1, 2),
            created_at=sample_datetime,
            emails_processed=[],
            tasks_created=[],
            decisions=[],
            questions=[],
        )

        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        result = processor.process(entry)

        assert result.success is True
        assert result.corrections_processed == 0
        assert result.answers_processed == 0

    def test_process_with_corrections(self, tmp_path, sample_journal_entry):
        """Test processing entry with corrections"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        result = processor.process(sample_journal_entry)

        assert result.success is True
        assert result.corrections_processed == 1
        # Should be stored for later (no learning engine)
        assert result.stored_for_later == 1

    def test_process_with_answered_questions(self, tmp_path, sample_journal_entry):
        """Test processing entry with answered questions"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        result = processor.process(sample_journal_entry)

        assert result.answers_processed == 1

    def test_correction_to_feedback(self, tmp_path, sample_correction):
        """Test converting correction to UserFeedback"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        feedback = processor._correction_to_feedback(sample_correction)

        assert feedback.approval is False  # Correction = wrong decision
        assert feedback.rating == 2  # Low rating
        assert "archive -> delete" in feedback.correction
        assert feedback.comment == "Should be deleted"

    def test_store_entry_feedback(self, tmp_path, sample_journal_entry):
        """Test that feedback is stored to file"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        processor.process(sample_journal_entry)

        # Check file was created
        feedback_file = tmp_path / "feedback" / "journal_2026-01-02.json"
        assert feedback_file.exists()

        # Check content
        data = json.loads(feedback_file.read_text())
        assert data["journal_date"] == "2026-01-02"
        assert len(data["corrections"]) == 1
        assert len(data["answers"]) == 1

    def test_store_entity_classification(self, tmp_path, sample_journal_entry):
        """Test that entity classifications are stored"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        processor.process(sample_journal_entry)

        # Check entity file was created
        entity_file = tmp_path / "entities.json"
        assert entity_file.exists()

        data = json.loads(entity_file.read_text())
        assert "new@example.com" in data.get("known_emails", [])
        assert data.get("classifications", {}).get("new@example.com") == "Colleague"

    def test_process_with_learning_engine(self, tmp_path, sample_journal_entry):
        """Test processing with learning engine (mocked)"""
        mock_learning = MagicMock()
        mock_result = MagicMock()
        mock_learning.learn.return_value = mock_result

        processor = JournalFeedbackProcessor(
            storage_dir=tmp_path / "feedback",
            learning_engine=mock_learning,
        )

        # Mock the event/memory retrieval to return None
        # (so it falls back to storage)
        result = processor.process(sample_journal_entry)

        assert result.success is True
        assert result.corrections_processed == 1


# ============================================================================
# RESULT DATACLASS TESTS
# ============================================================================


class TestFeedbackProcessingResult:
    """Tests for FeedbackProcessingResult"""

    def test_create_result(self):
        """Test creating result"""
        result = FeedbackProcessingResult(
            success=True,
            corrections_processed=5,
            answers_processed=3,
            stored_for_later=2,
        )
        assert result.success is True
        assert result.corrections_processed == 5
        assert len(result.learning_results) == 0
        assert len(result.errors) == 0

    def test_result_with_errors(self):
        """Test result with errors"""
        result = FeedbackProcessingResult(
            success=False,
            corrections_processed=3,
            answers_processed=2,
            stored_for_later=0,
            errors=["Error 1", "Error 2"],
        )
        assert result.success is False
        assert len(result.errors) == 2


# ============================================================================
# STORED FEEDBACK TESTS
# ============================================================================


class TestStoredFeedback:
    """Tests for StoredFeedback"""

    def test_to_dict(self, sample_correction, sample_datetime):
        """Test serialization"""
        feedback = StoredFeedback(
            feedback_id="fb-001",
            email_id="email-123",
            correction=sample_correction,
            question_answers={"q-001": "Yes"},
            created_at=sample_datetime,
        )

        d = feedback.to_dict()
        assert d["feedback_id"] == "fb-001"
        assert d["email_id"] == "email-123"
        assert "correction" in d
        assert d["processed"] is False


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================


class TestProcessCorrections:
    """Tests for process_corrections convenience function"""

    def test_process_corrections_function(self, sample_journal_entry, tmp_path, monkeypatch):
        """Test the convenience function"""
        # Patch the default storage dir
        monkeypatch.chdir(tmp_path)

        result = process_corrections(sample_journal_entry)
        assert result.success is True
        assert result.corrections_processed == 1


# ============================================================================
# SOURCE CALIBRATION TESTS
# ============================================================================


class TestSourceCalibration:
    """Tests for SourceCalibration dataclass"""

    def test_create_source_calibration(self):
        """Test creating source calibration"""
        calibration = SourceCalibration(
            source="email",
            total_items=100,
            correct_decisions=85,
            incorrect_decisions=15,
            average_confidence=82.5,
        )
        assert calibration.source == "email"
        assert calibration.total_items == 100

    def test_accuracy_property(self):
        """Test accuracy calculation"""
        calibration = SourceCalibration(
            source="email",
            correct_decisions=80,
            incorrect_decisions=20,
        )
        assert calibration.accuracy == 0.8

    def test_accuracy_with_no_decisions(self):
        """Test accuracy with zero decisions"""
        calibration = SourceCalibration(source="email")
        assert calibration.accuracy == 0.0

    def test_correction_rate_property(self):
        """Test correction rate calculation"""
        calibration = SourceCalibration(
            source="email",
            correct_decisions=90,
            incorrect_decisions=10,
        )
        assert calibration.correction_rate == pytest.approx(0.1)

    def test_to_dict(self):
        """Test serialization"""
        calibration = SourceCalibration(
            source="teams",
            total_items=50,
            correct_decisions=45,
            incorrect_decisions=5,
            average_confidence=88.0,
        )
        d = calibration.to_dict()
        assert d["source"] == "teams"
        assert d["accuracy"] == 0.9
        assert d["correction_rate"] == pytest.approx(0.1)
        assert "last_updated" in d


# ============================================================================
# CALIBRATION ANALYSIS TESTS
# ============================================================================


class TestCalibrationAnalysis:
    """Tests for CalibrationAnalysis dataclass"""

    def test_create_calibration_analysis(self):
        """Test creating calibration analysis"""
        analysis = CalibrationAnalysis(
            source_calibrations={
                "email": SourceCalibration(source="email", correct_decisions=80, incorrect_decisions=20),
                "teams": SourceCalibration(source="teams", correct_decisions=90, incorrect_decisions=10),
            },
            overall_accuracy=0.85,
            recommended_threshold_adjustment=5,
            patterns_learned=12,
        )
        assert analysis.overall_accuracy == 0.85
        assert len(analysis.source_calibrations) == 2

    def test_to_dict(self):
        """Test serialization"""
        analysis = CalibrationAnalysis(
            source_calibrations={
                "email": SourceCalibration(source="email", correct_decisions=80, incorrect_decisions=20),
            },
            overall_accuracy=0.8,
            recommended_threshold_adjustment=-3,
        )
        d = analysis.to_dict()
        assert d["overall_accuracy"] == 0.8
        assert d["recommended_threshold_adjustment"] == -3
        assert "email" in d["source_calibrations"]


# ============================================================================
# WEEKLY REVIEW RESULT TESTS
# ============================================================================


class TestWeeklyReviewResult:
    """Tests for WeeklyReviewResult dataclass"""

    def test_create_weekly_review_result(self):
        """Test creating weekly review result"""
        result = WeeklyReviewResult(
            success=True,
            patterns_processed=5,
            calibrations_updated=3,
            threshold_adjustments={"email": 2, "teams": -1},
        )
        assert result.success is True
        assert result.patterns_processed == 5
        assert result.calibrations_updated == 3
        assert result.threshold_adjustments["email"] == 2


# ============================================================================
# CALIBRATION PROCESSOR TESTS
# ============================================================================


class TestJournalFeedbackProcessorCalibration:
    """Tests for calibration methods in JournalFeedbackProcessor"""

    def test_record_correct_decision(self, tmp_path):
        """Test recording a correct decision"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")

        processor.record_correct_decision("email")
        processor.record_correct_decision("email")
        processor.record_correct_decision("teams")

        analysis = processor.analyze_calibration()
        assert analysis.source_calibrations["email"].correct_decisions == 2
        assert analysis.source_calibrations["teams"].correct_decisions == 1

    def test_record_incorrect_decision(self, tmp_path):
        """Test recording an incorrect decision"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")

        processor.record_incorrect_decision("email")
        processor.record_incorrect_decision("email")
        processor.record_correct_decision("email")

        analysis = processor.analyze_calibration()
        assert analysis.source_calibrations["email"].incorrect_decisions == 2
        assert analysis.source_calibrations["email"].correct_decisions == 1
        assert analysis.source_calibrations["email"].accuracy == pytest.approx(1 / 3)

    def test_analyze_calibration_empty(self, tmp_path):
        """Test calibration analysis with no data"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")

        analysis = processor.analyze_calibration()
        assert analysis.overall_accuracy == 0.0
        assert len(analysis.source_calibrations) == 0

    def test_analyze_calibration_with_data(self, tmp_path):
        """Test calibration analysis with data"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")

        # Record some decisions
        for _ in range(8):
            processor.record_correct_decision("email")
        for _ in range(2):
            processor.record_incorrect_decision("email")

        for _ in range(9):
            processor.record_correct_decision("teams")
        processor.record_incorrect_decision("teams")

        analysis = processor.analyze_calibration()
        assert analysis.source_calibrations["email"].accuracy == 0.8
        assert analysis.source_calibrations["teams"].accuracy == 0.9
        # Overall accuracy should be weighted average
        assert analysis.overall_accuracy > 0

    def test_calibrate_by_source(self, tmp_path, sample_correction):
        """Test calibration by source"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")

        # Record some baseline
        for _ in range(5):
            processor.record_correct_decision("email")
        processor.record_incorrect_decision("email")

        # Calibrate with corrections - returns SourceCalibration
        calibration = processor.calibrate_by_source("email", [sample_correction])
        assert isinstance(calibration, SourceCalibration)
        assert calibration.accuracy < 1.0  # Should be less than perfect after correction
        assert calibration.incorrect_decisions >= 1  # At least one correction was added

    def test_calibration_persistence(self, tmp_path):
        """Test that calibration data persists"""
        # First processor
        processor1 = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        processor1.record_correct_decision("email")
        processor1.record_incorrect_decision("email")

        # Second processor loads same data
        processor2 = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")
        analysis = processor2.analyze_calibration()

        assert analysis.source_calibrations["email"].correct_decisions == 1
        assert analysis.source_calibrations["email"].incorrect_decisions == 1

    def test_update_confidence_thresholds(self, tmp_path):
        """Test updating confidence thresholds based on calibration"""
        processor = JournalFeedbackProcessor(storage_dir=tmp_path / "feedback")

        # High accuracy - may increase threshold
        for _ in range(95):
            processor.record_correct_decision("email")
        for _ in range(5):
            processor.record_incorrect_decision("email")

        analysis = processor.analyze_calibration()
        # With 95% accuracy, system might recommend threshold adjustment
        # (depends on implementation)
        assert analysis.overall_accuracy >= 0.9
