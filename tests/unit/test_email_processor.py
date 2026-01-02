"""
Unit Tests for Email Processor

Tests for email processing orchestration.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.schemas import (
    EmailAction,
    EmailAnalysis,
    EmailCategory,
    EmailContent,
    EmailMetadata,
    ProcessedEmail,
)
from src.trivelin.processor import EmailProcessor
from src.utils import now_utc


@pytest.fixture
def sample_metadata():
    """Create sample email metadata"""
    return EmailMetadata(
        id=123,
        folder="INBOX",
        message_id="<test@example.com>",
        from_address="sender@example.com",
        from_name="Sender Name",
        to_addresses=["recipient@example.com"],
        subject="Test Email Subject",
        date=now_utc(),
        has_attachments=False,
        size_bytes=1024,
        flags=[]
    )


@pytest.fixture
def sample_content():
    """Create sample email content"""
    return EmailContent(
        plain_text="This is the email content.",
        html="<p>This is the email content.</p>"
    )


@pytest.fixture
def sample_analysis():
    """Create sample email analysis"""
    return EmailAnalysis(
        action=EmailAction.ARCHIVE,
        category=EmailCategory.WORK,
        destination="Archive/2025/Work",
        confidence=95,
        reasoning="Work-related project update",
        tags=["work", "project"],
        entities={"people": [], "projects": [], "dates": []},
        needs_full_content=False
    )


class TestEmailProcessorInit:
    """Test email processor initialization"""

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_init(self, mock_get_router, mock_imap, mock_get_state, mock_get_config, mock_config):
        """Test processor initialization"""
        local_mock_config = MagicMock()
        local_mock_config.email = MagicMock()
        local_mock_config.ai = MagicMock()
        mock_get_config.return_value = local_mock_config

        processor = EmailProcessor()

        assert processor.config == local_mock_config
        mock_get_state.assert_called_once()
        mock_imap.assert_called_once_with(local_mock_config.email)
        mock_get_router.assert_called_once_with(local_mock_config.ai)


class TestProcessInbox:
    """Test inbox processing"""

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_process_inbox_success(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        sample_content,
        sample_analysis,
        mock_config  # Fixture for global config mock
    ):
        """Test successful inbox processing"""
        # Setup mocks - use the mock_config fixture directly
        mock_config.email.inbox_folder = "INBOX"
        mock_config.ai.confidence_threshold = 90
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_state.is_processed.return_value = False
        mock_state.get.return_value = 0
        mock_state.get_average_confidence.return_value = 95.0
        mock_get_state.return_value = mock_state

        mock_imap = MagicMock()
        mock_imap.fetch_emails.return_value = [(sample_metadata, sample_content)]
        mock_imap_class.return_value = mock_imap

        mock_router = MagicMock()
        mock_router.analyze_email.return_value = sample_analysis
        mock_router.get_rate_limit_status.return_value = {"current_requests": 1}
        mock_get_router.return_value = mock_router

        # Process inbox
        processor = EmailProcessor()
        results = processor.process_inbox(limit=10, auto_execute=False)

        assert len(results) == 1
        assert isinstance(results[0], ProcessedEmail)
        assert results[0].metadata.id == 123

        # Verify state updates
        mock_state.increment.assert_called()
        mock_state.mark_processed.assert_called_with('123')

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_process_inbox_empty(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        mock_config
    ):
        """Test processing empty inbox"""
        mock_config.email.inbox_folder = "INBOX"
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_get_state.return_value = mock_state

        mock_imap = MagicMock()
        mock_imap.fetch_emails.return_value = []
        mock_imap_class.return_value = mock_imap

        processor = EmailProcessor()
        results = processor.process_inbox()

        assert len(results) == 0

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_process_inbox_with_limit(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        sample_content,
        mock_config
    ):
        """Test inbox processing with limit"""
        mock_config.email.inbox_folder = "INBOX"
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_get_state.return_value = mock_state

        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap

        processor = EmailProcessor()
        processor.process_inbox(limit=5)

        # Verify limit was passed to fetch_emails
        mock_imap.fetch_emails.assert_called_once()
        call_kwargs = mock_imap.fetch_emails.call_args[1]
        assert call_kwargs['limit'] == 5


class TestProcessSingleEmail:
    """Test single email processing"""

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_process_single_email_success(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        sample_content,
        sample_analysis,
        mock_config
    ):
        """Test successful single email processing"""
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_state.is_processed.return_value = False
        mock_get_state.return_value = mock_state

        mock_router = MagicMock()
        mock_router.analyze_email.return_value = sample_analysis
        mock_get_router.return_value = mock_router

        processor = EmailProcessor()
        result = processor._process_single_email(
            sample_metadata,
            sample_content,
            auto_execute=False
        )

        assert result is not None
        assert result.metadata.id == 123
        assert result.analysis.action == EmailAction.ARCHIVE

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_process_single_email_already_processed(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        sample_content,
        mock_config
    ):
        """Test processing already processed email"""
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_state.is_processed.return_value = True  # Already processed
        mock_get_state.return_value = mock_state

        processor = EmailProcessor()
        result = processor._process_single_email(sample_metadata, sample_content)

        assert result is None

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_process_single_email_analysis_failure(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        sample_content,
        mock_config
    ):
        """Test processing when analysis fails"""
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_state.is_processed.return_value = False
        mock_get_state.return_value = mock_state

        mock_router = MagicMock()
        mock_router.analyze_email.return_value = None  # Analysis failed
        mock_get_router.return_value = mock_router

        processor = EmailProcessor()
        result = processor._process_single_email(sample_metadata, sample_content)

        assert result is None


class TestExecuteAction:
    """Test action execution"""

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_execute_archive_action(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        mock_config
    ):
        """Test executing archive action"""
        mock_config.email.archive_folder = "Archive"
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_get_state.return_value = mock_state

        mock_imap = MagicMock()
        mock_imap.move_email.return_value = True
        mock_imap_class.return_value = mock_imap

        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.WORK,
            destination="Archive/2025",
            confidence=95,
            reasoning="Archive email",
            tags=[],
            entities={},
            needs_full_content=False
        )

        processor = EmailProcessor()
        result = processor._execute_action(sample_metadata, analysis)

        assert result is True
        mock_state.increment.assert_called_with("emails_archived")

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_execute_delete_action(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        mock_config
    ):
        """Test executing delete action"""
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_get_state.return_value = mock_state

        mock_imap = MagicMock()
        mock_imap.move_email.return_value = True
        mock_imap_class.return_value = mock_imap

        analysis = EmailAnalysis(
            action=EmailAction.DELETE,
            category=EmailCategory.SPAM,
            destination="Trash",
            confidence=99,
            reasoning="Spam email",
            tags=[],
            entities={},
            needs_full_content=False
        )

        processor = EmailProcessor()
        result = processor._execute_action(sample_metadata, analysis)

        assert result is True
        mock_state.increment.assert_called_with("emails_deleted")

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_execute_task_action(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        sample_metadata,
        mock_config
    ):
        """Test executing task creation action"""
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_get_state.return_value = mock_state

        analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            destination="Tasks",
            confidence=90,
            reasoning="Actionable email",
            tags=["work"],
            entities={},
            omnifocus_task={
                "title": "Review document",
                "note": "Document needs review",
                "tags": ["work"]
            },
            needs_full_content=False
        )

        processor = EmailProcessor()
        result = processor._execute_action(sample_metadata, analysis)

        # Task creation not fully implemented yet, but should not fail
        assert result is True
        mock_state.increment.assert_called_with("tasks_created")


class TestGetProcessingStats:
    """Test getting processing statistics"""

    @patch('src.trivelin.processor.get_config')
    @patch('src.trivelin.processor.get_state_manager')
    @patch('src.trivelin.processor.IMAPClient')
    @patch('src.trivelin.processor.get_ai_router')
    def test_get_processing_stats(
        self,
        mock_get_router,
        mock_imap_class,
        mock_get_state,
        mock_get_config,
        mock_config
    ):
        """Test getting processing statistics"""
        mock_get_config.return_value = mock_config

        mock_state = MagicMock()
        mock_state.get.side_effect = lambda key, default=None: {
            "emails_processed": 10,
            "emails_archived": 5,
            "emails_deleted": 2,
            "emails_queued": 3,
            "tasks_created": 1,
            "processing_mode": "auto"
        }.get(key, default)
        mock_state.get_average_confidence.return_value = 92.5
        mock_get_state.return_value = mock_state

        mock_router = MagicMock()
        mock_router.get_rate_limit_status.return_value = {"usage_percent": 25.0}
        mock_get_router.return_value = mock_router

        processor = EmailProcessor()
        stats = processor.get_processing_stats()

        assert stats["emails_processed"] == 10
        assert stats["emails_archived"] == 5
        assert stats["emails_deleted"] == 2
        assert stats["tasks_created"] == 1
        assert stats["average_confidence"] == 92.5
        assert stats["processing_mode"] == "auto"
        assert "rate_limit_status" in stats
