"""
Tests for ActionExecutor

Covers action execution, dry-run mode, IMAP operations, and OmniFocus integration.
"""

from unittest.mock import Mock

import pytest

from src.core.processors.action_executor import ActionExecutor
from src.core.schemas import EmailAction, EmailAnalysis, EmailCategory, EmailMetadata
from src.utils import now_utc


@pytest.fixture
def mock_imap_client():
    """Create mock IMAP client"""
    client = Mock()
    client.move_email = Mock()
    client.delete_email = Mock()
    return client


@pytest.fixture
def mock_omnifocus():
    """Create mock OmniFocus integration"""
    omnifocus = Mock()
    omnifocus.create_task = Mock(return_value="task-123")
    return omnifocus


@pytest.fixture
def executor(mock_imap_client, mock_omnifocus):
    """Create ActionExecutor with mocks"""
    return ActionExecutor(
        imap_client=mock_imap_client,
        omnifocus=mock_omnifocus
    )


@pytest.fixture
def sample_metadata():
    """Create sample email metadata"""
    return EmailMetadata(
        id=1,
        message_id="test@example.com",
        subject="Test Email",
        from_address="sender@example.com",
        from_name="Test Sender",
        to_addresses=["recipient@example.com"],
        date=now_utc(),
        has_attachments=False,
        flags=[]
    )


class TestEmailActions:
    """Test email action execution"""

    def test_archive_action(self, executor, mock_imap_client, sample_metadata):
        """Test archiving an email"""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=95,
            reasoning="Newsletter",
            destination="Archive"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Verify IMAP action
        mock_imap_client.move_email.assert_called_once_with(
            message_id="test@example.com",
            destination_folder="Archive"
        )

        # Verify result
        assert result.success is True
        assert len(result.actions_taken) == 1
        assert "archived to Archive" in result.actions_taken[0]
        assert len(result.errors) == 0

    def test_archive_default_folder(self, executor, mock_imap_client, sample_metadata):
        """Test archive uses default folder when destination not specified"""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.OTHER,
            confidence=95,
            reasoning="Archive it",
            destination=None  # No destination specified
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Should use "Archive" as default
        mock_imap_client.move_email.assert_called_once_with(
            message_id="test@example.com",
            destination_folder="Archive"
        )

        assert "archived to Archive" in result.actions_taken[0]

    def test_delete_action(self, executor, mock_imap_client, sample_metadata):
        """Test deleting an email"""
        analysis = EmailAnalysis(
            action=EmailAction.DELETE,
            category=EmailCategory.SPAM,
            confidence=98,
            reasoning="Spam email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        mock_imap_client.delete_email.assert_called_once_with(
            message_id="test@example.com"
        )

        assert result.success is True
        assert "deleted" in result.actions_taken[0]

    def test_defer_action(self, executor, sample_metadata):
        """Test defer action (no IMAP operation)"""
        analysis = EmailAnalysis(
            action=EmailAction.DEFER,
            category=EmailCategory.OTHER,
            confidence=80,
            reasoning="Review later"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        assert result.success is True
        assert "deferred for later review" in result.actions_taken[0]

    def test_queue_action(self, executor, sample_metadata):
        """Test queue action (no IMAP operation)"""
        analysis = EmailAnalysis(
            action=EmailAction.QUEUE,
            category=EmailCategory.OTHER,
            confidence=70,
            reasoning="Needs review"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        assert result.success is True
        assert "queued for review" in result.actions_taken[0]


@pytest.mark.skip(reason="EmailAction.TASK not yet implemented - OmniFocus integration planned for Phase 5")
class TestTaskCreation:
    """Test OmniFocus task creation"""

    def test_task_action_creates_task(self, executor, mock_omnifocus, sample_metadata):
        """Test TASK action creates OmniFocus task"""
        analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=92,
            reasoning="Action required"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Should create task
        assert mock_omnifocus.create_task.called
        assert result.success is True
        assert any("task created" in action for action in result.actions_taken)

    def test_task_with_omnifocus_data(self, executor, mock_omnifocus, sample_metadata):
        """Test task creation with detailed OmniFocus data"""
        analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=92,
            reasoning="Action required",
            omnifocus_task={
                "title": "Custom Task Title",
                "note": "Task notes here",
                "defer_date": "2024-01-15",
                "due_date": "2024-01-20",
                "tags": ["email", "urgent"]
            }
        )

        _result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Verify task was created with correct parameters
        mock_omnifocus.create_task.assert_called_once()
        call_kwargs = mock_omnifocus.create_task.call_args.kwargs

        assert call_kwargs["title"] == "Custom Task Title"
        assert call_kwargs["note"] == "Task notes here"
        assert call_kwargs["defer_date"] == "2024-01-15"
        assert call_kwargs["due_date"] == "2024-01-20"
        assert call_kwargs["tags"] == ["email", "urgent"]

    def test_task_fallback_to_subject(self, executor, mock_omnifocus, sample_metadata):
        """Test task creation falls back to subject when no omnifocus_task"""
        analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=90,
            reasoning="Simple task"
        )

        _result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Should use email subject as title
        call_kwargs = mock_omnifocus.create_task.call_args.kwargs
        assert call_kwargs["title"] == "Test Email"
        assert "sender@example.com" in call_kwargs["note"]

    def test_archive_with_task(self, executor, mock_imap_client, mock_omnifocus, sample_metadata):
        """Test archive action can also create task if omnifocus_task specified"""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.OTHER,
            confidence=95,
            reasoning="Archive but track",
            destination="Archive",
            omnifocus_task={
                "title": "Follow up on archived email",
                "note": "Check later"
            }
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Both actions should be executed
        mock_imap_client.move_email.assert_called_once()
        mock_omnifocus.create_task.assert_called_once()

        assert len(result.actions_taken) == 2
        assert any("archived" in action for action in result.actions_taken)
        assert any("task created" in action for action in result.actions_taken)


class TestDryRun:
    """Test dry-run mode"""

    def test_dry_run_archive(self, executor, mock_imap_client, sample_metadata):
        """Test dry-run mode doesn't execute IMAP actions"""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.OTHER,
            confidence=95,
            reasoning="Test email analysis",
            destination="Archive"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=True)

        # Should NOT call IMAP
        mock_imap_client.move_email.assert_not_called()

        # But should report what would be done
        assert result.success is True
        assert "archived to Archive" in result.actions_taken[0]

    def test_dry_run_delete(self, executor, mock_imap_client, sample_metadata):
        """Test dry-run mode doesn't delete emails"""
        analysis = EmailAnalysis(
            action=EmailAction.DELETE,
            category=EmailCategory.SPAM,
            confidence=98,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=True)

        mock_imap_client.delete_email.assert_not_called()
        assert "deleted" in result.actions_taken[0]

    @pytest.mark.skip(reason="EmailAction.TASK not yet implemented - OmniFocus integration planned for Phase 5")
    def test_dry_run_task(self, executor, mock_omnifocus, sample_metadata):
        """Test dry-run mode doesn't create tasks"""
        analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=90,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=True)

        mock_omnifocus.create_task.assert_not_called()
        assert any("task created" in action for action in result.actions_taken)


class TestNoClients:
    """Test behavior when clients are not configured"""

    def test_no_imap_client(self, mock_omnifocus, sample_metadata):
        """Test executor without IMAP client"""
        executor = ActionExecutor(imap_client=None, omnifocus=mock_omnifocus)

        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.OTHER,
            confidence=95,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Should complete successfully but no actions taken
        assert result.success is True
        assert len(result.actions_taken) == 0

    @pytest.mark.skip(reason="EmailAction.TASK not yet implemented - OmniFocus integration planned for Phase 5")
    def test_no_omnifocus_client(self, mock_imap_client, sample_metadata):
        """Test executor without OmniFocus client"""
        executor = ActionExecutor(imap_client=mock_imap_client, omnifocus=None)

        analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=90,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Should complete successfully but no task created
        assert result.success is True
        assert len(result.actions_taken) == 0

    def test_no_clients_at_all(self, sample_metadata):
        """Test executor with no clients configured"""
        executor = ActionExecutor(imap_client=None, omnifocus=None)

        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.OTHER,
            confidence=95,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        assert result.success is True
        assert len(result.actions_taken) == 0


class TestErrorHandling:
    """Test error handling during execution"""

    def test_imap_error_logged(self, executor, mock_imap_client, sample_metadata):
        """Test IMAP errors are caught and logged"""
        mock_imap_client.move_email.side_effect = Exception("IMAP connection failed")

        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.OTHER,
            confidence=95,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Should succeed (error caught) but no actions taken
        assert result.success is True
        assert len(result.actions_taken) == 0

    @pytest.mark.skip(reason="EmailAction.TASK not yet implemented - OmniFocus integration planned for Phase 5")
    def test_omnifocus_error_logged(self, executor, mock_omnifocus, sample_metadata):
        """Test OmniFocus errors are caught and logged"""
        mock_omnifocus.create_task.side_effect = Exception("OmniFocus API error")

        analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=90,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        # Should succeed (error caught) but no task created
        assert result.success is True
        assert len(result.actions_taken) == 0


class TestExecutionResult:
    """Test ExecutionResult metadata"""

    def test_result_includes_metadata(self, executor, sample_metadata):
        """Test execution result includes email metadata"""
        analysis = EmailAnalysis(
            action=EmailAction.DEFER,
            category=EmailCategory.OTHER,
            confidence=80,
            reasoning="Test email analysis"
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        assert result.metadata == "test@example.com"

    def test_multiple_actions(self, executor, mock_imap_client, mock_omnifocus, sample_metadata):
        """Test result tracks multiple actions"""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.OTHER,
            confidence=95,
            reasoning="Archive and track",
            destination="Done",
            omnifocus_task={"title": "Follow up"}
        )

        result = executor.execute(sample_metadata, analysis, dry_run=False)

        assert len(result.actions_taken) == 2
        assert result.success is True
        assert result.metadata == "test@example.com"
