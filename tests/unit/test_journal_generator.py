"""
Tests for JournalGenerator

Tests the journal draft generation from processing history.
"""

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.frontin.journal.generator import (
    JournalGenerator,
    JournalGeneratorConfig,
    JsonFileHistoryProvider,
)
from src.frontin.journal.models import QuestionCategory

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_emails_data():
    """Sample processed emails data"""
    return [
        {
            "email_id": "email-001",
            "from_address": "alice@example.com",
            "from_name": "Alice",
            "subject": "High confidence email",
            "action": "archive",
            "category": "work",
            "confidence": 92,
            "processed_at": "2026-01-02T10:00:00+00:00",
        },
        {
            "email_id": "email-002",
            "from_address": "bob@example.com",
            "subject": "Low confidence email",
            "action": "archive",
            "category": "other",
            "confidence": 65,
            "processed_at": "2026-01-02T11:00:00+00:00",
        },
        {
            "email_id": "email-003",
            "from_address": "new-sender@example.com",
            "subject": "From new sender",
            "action": "queue",
            "category": "other",
            "confidence": 75,
            "processed_at": "2026-01-02T12:00:00+00:00",
        },
    ]


@pytest.fixture
def sample_tasks_data():
    """Sample tasks data"""
    return [
        {
            "task_id": "task-001",
            "title": "Follow up on email",
            "source_email_id": "email-001",
            "project": "Work",
            "created_at": "2026-01-02T10:30:00+00:00",
        }
    ]


@pytest.fixture
def mock_history_provider(sample_emails_data, sample_tasks_data):
    """Create mock history provider"""
    provider = MagicMock()
    provider.get_processed_emails.return_value = sample_emails_data
    provider.get_created_tasks.return_value = sample_tasks_data
    provider.get_decisions.return_value = []
    provider.get_known_entities.return_value = {"alice@example.com", "bob@example.com"}
    return provider


# ============================================================================
# GENERATOR CONFIG TESTS
# ============================================================================


class TestJournalGeneratorConfig:
    """Tests for generator configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = JournalGeneratorConfig()
        assert config.low_confidence_threshold == 80
        assert config.max_questions == 10
        assert config.ask_about_new_senders is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = JournalGeneratorConfig(
            low_confidence_threshold=70,
            max_questions=5,
            ask_about_new_senders=False,
        )
        assert config.low_confidence_threshold == 70
        assert config.max_questions == 5
        assert config.ask_about_new_senders is False


# ============================================================================
# GENERATOR TESTS
# ============================================================================


class TestJournalGenerator:
    """Tests for JournalGenerator"""

    def test_generate_empty_day(self):
        """Test generating journal for day with no activity"""
        provider = MagicMock()
        provider.get_processed_emails.return_value = []
        provider.get_created_tasks.return_value = []
        provider.get_decisions.return_value = []
        provider.get_known_entities.return_value = set()

        generator = JournalGenerator(history_provider=provider)
        entry = generator.generate(date(2026, 1, 2))

        assert entry.journal_date == date(2026, 1, 2)
        assert len(entry.emails_processed) == 0
        assert len(entry.questions) == 0

    def test_generate_with_emails(self, mock_history_provider):
        """Test generating journal with processed emails"""
        generator = JournalGenerator(history_provider=mock_history_provider)
        entry = generator.generate(date(2026, 1, 2))

        assert entry.journal_date == date(2026, 1, 2)
        assert len(entry.emails_processed) == 3
        assert len(entry.tasks_created) == 1

    def test_generate_low_confidence_questions(self, mock_history_provider):
        """Test that low confidence emails generate questions"""
        generator = JournalGenerator(history_provider=mock_history_provider)
        entry = generator.generate(date(2026, 1, 2))

        # Should have questions for low confidence emails (< 80%)
        low_conf_questions = [
            q for q in entry.questions
            if q.category == QuestionCategory.LOW_CONFIDENCE
        ]
        assert len(low_conf_questions) >= 1

    def test_generate_new_sender_questions(self, mock_history_provider):
        """Test that new senders generate questions"""
        generator = JournalGenerator(history_provider=mock_history_provider)
        entry = generator.generate(date(2026, 1, 2))

        # Should have question for new-sender@example.com
        new_sender_questions = [
            q for q in entry.questions
            if q.category == QuestionCategory.NEW_PERSON
        ]
        assert len(new_sender_questions) == 1
        assert "new-sender@example.com" in str(new_sender_questions[0].related_entity)

    def test_generate_respects_max_questions(self, mock_history_provider):
        """Test that max questions config is respected"""
        config = JournalGeneratorConfig(max_questions=2)
        generator = JournalGenerator(
            history_provider=mock_history_provider,
            config=config,
        )
        entry = generator.generate(date(2026, 1, 2))

        assert len(entry.questions) <= 2

    def test_generate_disable_new_sender_questions(self, mock_history_provider):
        """Test disabling new sender questions"""
        config = JournalGeneratorConfig(ask_about_new_senders=False)
        generator = JournalGenerator(
            history_provider=mock_history_provider,
            config=config,
        )
        entry = generator.generate(date(2026, 1, 2))

        new_sender_questions = [
            q for q in entry.questions
            if q.category == QuestionCategory.NEW_PERSON
        ]
        assert len(new_sender_questions) == 0

    def test_generate_questions_sorted_by_priority(self, mock_history_provider):
        """Test that questions are sorted by priority"""
        generator = JournalGenerator(history_provider=mock_history_provider)
        entry = generator.generate(date(2026, 1, 2))

        if len(entry.questions) > 1:
            priorities = [q.priority for q in entry.questions]
            assert priorities == sorted(priorities)


# ============================================================================
# JSON FILE PROVIDER TESTS
# ============================================================================


class TestJsonFileHistoryProvider:
    """Tests for JsonFileHistoryProvider"""

    def test_get_processed_emails_no_file(self, tmp_path):
        """Test getting emails when no log file exists"""
        provider = JsonFileHistoryProvider(data_dir=tmp_path)
        emails = provider.get_processed_emails(date(2026, 1, 2))
        assert emails == []

    def test_get_processed_emails_with_file(self, tmp_path):
        """Test getting emails from log file"""
        # Create log directory and file
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_file = log_dir / "processing_2026-01-02.json"
        log_file.write_text(json.dumps({
            "emails": [
                {"email_id": "test-001", "subject": "Test"}
            ]
        }))

        provider = JsonFileHistoryProvider(data_dir=tmp_path)
        emails = provider.get_processed_emails(date(2026, 1, 2))

        assert len(emails) == 1
        assert emails[0]["email_id"] == "test-001"

    def test_get_known_entities_no_file(self, tmp_path):
        """Test getting entities when no file exists"""
        provider = JsonFileHistoryProvider(data_dir=tmp_path)
        entities = provider.get_known_entities()
        assert entities == set()

    def test_get_known_entities_with_file(self, tmp_path):
        """Test getting entities from file"""
        entity_file = tmp_path / "entities.json"
        entity_file.write_text(json.dumps({
            "known_emails": ["alice@example.com", "bob@example.com"]
        }))

        provider = JsonFileHistoryProvider(data_dir=tmp_path)
        entities = provider.get_known_entities()

        assert "alice@example.com" in entities
        assert "bob@example.com" in entities


# ============================================================================
# CONVERSION TESTS
# ============================================================================


class TestEmailConversion:
    """Tests for email data conversion"""

    def test_convert_email_with_all_fields(self, mock_history_provider):
        """Test converting email with all fields"""
        generator = JournalGenerator(history_provider=mock_history_provider)
        entry = generator.generate(date(2026, 1, 2))

        email = entry.emails_processed[0]
        assert email.email_id == "email-001"
        assert email.from_address == "alice@example.com"
        assert email.from_name == "Alice"
        assert email.confidence == 92

    def test_convert_email_with_missing_fields(self):
        """Test converting email with missing optional fields"""
        provider = MagicMock()
        provider.get_processed_emails.return_value = [
            {
                "id": "minimal-001",  # Using 'id' instead of 'email_id'
                "from": "test@example.com",  # Using 'from' instead of 'from_address'
            }
        ]
        provider.get_created_tasks.return_value = []
        provider.get_decisions.return_value = []
        provider.get_known_entities.return_value = set()

        generator = JournalGenerator(history_provider=provider)
        entry = generator.generate(date(2026, 1, 2))

        assert len(entry.emails_processed) == 1
        email = entry.emails_processed[0]
        assert email.email_id == "minimal-001"
        assert email.from_address == "test@example.com"
        assert email.subject == "(no subject)"

    def test_convert_task_with_dates(self, mock_history_provider):
        """Test converting task with date fields"""
        generator = JournalGenerator(history_provider=mock_history_provider)
        entry = generator.generate(date(2026, 1, 2))

        assert len(entry.tasks_created) == 1
        task = entry.tasks_created[0]
        assert task.task_id == "task-001"
        assert task.project == "Work"
