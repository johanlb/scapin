"""
Unit tests for Figaro Actions (Email, Tasks, Notes)
"""

from unittest.mock import patch

import pytest

from src.core.config_manager import EmailAccountConfig
from src.core.events.universal_event import Entity
from src.figaro.actions.email import ArchiveEmailAction, DeleteEmailAction, MoveEmailAction
from src.figaro.actions.notes import CreateNoteAction, UpdateNoteAction
from src.figaro.actions.tasks import CompleteTaskAction, CreateTaskAction


def _create_test_email_config() -> EmailAccountConfig:
    """Helper to create test email account config"""
    return EmailAccountConfig(
        account_id="test",
        account_name="Test Account",
        email_address="test@example.com",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="test@example.com",
        imap_password="password",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="test@example.com",
        smtp_password="password"
    )


@pytest.mark.skip(reason="Email actions not yet implemented - pending Week 5")
class TestArchiveEmailAction:
    """Test ArchiveEmailAction"""

    def test_init(self):
        """Test action initialization"""
        config = _create_test_email_config()
        action = ArchiveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config
        )

        assert action.email_id == 123
        assert action.account_email == "test@example.com"
        assert action.current_folder == "INBOX"
        assert action.archive_folder == "Archive"

    def test_action_id(self):
        """Test unique action ID generation"""
        config = _create_test_email_config()
        action = ArchiveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config
        )

        assert action.action_id == "archive_email_test@example.com_123"

    def test_action_type(self):
        """Test action type"""
        config = _create_test_email_config()
        action = ArchiveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config
        )

        assert action.action_type == "archive_email"

    def test_validate_invalid_email_id(self):
        """Test validation fails for invalid email ID"""
        config = _create_test_email_config()
        action = ArchiveEmailAction(
            email_id=0,  # Invalid
            account_email="test@example.com",
            imap_config=config
        )

        # Mock IMAP client to avoid actual connection
        with patch('src.figaro.actions.email.IMAPClient'):
            result = action.validate()

            assert result.valid is False
            assert any("Invalid email ID" in error for error in result.errors)

    def test_dependencies(self):
        """Test action has no dependencies"""
        config = _create_test_email_config()
        action = ArchiveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config
        )

        assert action.dependencies() == []

    def test_estimated_duration(self):
        """Test estimated duration"""
        config = _create_test_email_config()
        action = ArchiveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config
        )

        assert action.estimated_duration() == 2.0


@pytest.mark.skip(reason="Email actions not yet implemented - pending Week 5")
class TestDeleteEmailAction:
    """Test DeleteEmailAction"""

    def test_init_default(self):
        """Test default initialization"""
        config = _create_test_email_config()
        action = DeleteEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config
        )

        assert action.permanent is False
        assert action.trash_folder == "Trash"

    def test_init_permanent(self):
        """Test permanent deletion flag"""
        config = _create_test_email_config()
        action = DeleteEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config,
            permanent=True
        )

        assert action.permanent is True

    def test_can_undo_permanent(self):
        """Test permanent deletion cannot be undone"""
        config = _create_test_email_config()
        action = DeleteEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config,
            permanent=True
        )

        # Even after "execution", permanent delete cannot be undone
        action._executed = True
        action._original_folder = "INBOX"

        assert action.can_undo() is False


@pytest.mark.skip(reason="Email actions not yet implemented - pending Week 5")
class TestMoveEmailAction:
    """Test MoveEmailAction"""

    def test_init(self):
        """Test initialization"""
        config = _create_test_email_config()
        action = MoveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config,
            source_folder="INBOX",
            destination_folder="Work"
        )

        assert action.source_folder == "INBOX"
        assert action.destination_folder == "Work"

    def test_action_id_includes_destination(self):
        """Test action ID includes destination folder"""
        config = _create_test_email_config()
        action = MoveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config,
            source_folder="INBOX",
            destination_folder="Work"
        )

        assert "Work" in action.action_id

    def test_validate_same_folders(self):
        """Test validation fails if source == destination"""
        config = _create_test_email_config()
        action = MoveEmailAction(
            email_id=123,
            account_email="test@example.com",
            imap_config=config,
            source_folder="INBOX",
            destination_folder="INBOX"  # Same as source
        )

        with patch('src.figaro.actions.email.IMAPClient'):
            result = action.validate()

            assert result.valid is False
            assert any("same" in error.lower() for error in result.errors)


class TestCreateTaskAction:
    """Test CreateTaskAction"""

    def test_init(self):
        """Test initialization"""
        action = CreateTaskAction(
            name="Test task",
            note="Task notes",
            tags=["work", "urgent"]
        )

        assert action.name == "Test task"
        assert action.note == "Task notes"
        assert action.tags == ["work", "urgent"]

    def test_action_id_uniqueness(self):
        """Test action IDs are unique"""
        action1 = CreateTaskAction(name="Task 1")
        action2 = CreateTaskAction(name="Task 1")

        # Same name but different timestamps
        assert action1.action_id != action2.action_id

    def test_action_type(self):
        """Test action type"""
        action = CreateTaskAction(name="Test task")

        assert action.action_type == "create_task"

    def test_validate_empty_name(self):
        """Test validation fails for empty name"""
        action = CreateTaskAction(name="")

        result = action.validate()

        assert result.valid is False
        assert any("required" in error.lower() for error in result.errors)

    def test_validate_invalid_dates(self):
        """Test validation fails for invalid date formats"""
        action = CreateTaskAction(
            name="Test task",
            due_date="not-a-date"
        )

        result = action.validate()

        assert result.valid is False
        assert any("date" in error.lower() for error in result.errors)

    def test_validate_defer_after_due(self):
        """Test validation warns if defer date is after due date"""
        action = CreateTaskAction(
            name="Test task",
            due_date="2025-01-01",
            defer_date="2025-01-10"  # After due date
        )

        result = action.validate()

        # Should have warning but still be valid
        assert len(result.warnings) > 0
        assert any("after due" in warning.lower() for warning in result.warnings)

    def test_estimated_duration(self):
        """Test estimated duration"""
        action = CreateTaskAction(name="Test task")

        assert action.estimated_duration() == 1.0

    def test_dependencies(self):
        """Test no dependencies"""
        action = CreateTaskAction(name="Test task")

        assert action.dependencies() == []


class TestCompleteTaskAction:
    """Test CompleteTaskAction"""

    def test_init_with_task_id(self):
        """Test initialization with task ID"""
        action = CompleteTaskAction(task_id="task123")

        assert action.task_id == "task123"
        assert action.task_name is None

    def test_init_with_task_name(self):
        """Test initialization with task name"""
        action = CompleteTaskAction(task_name="My Task")

        assert action.task_id is None
        assert action.task_name == "My Task"

    def test_validate_no_identifier(self):
        """Test validation fails if no task ID or name"""
        action = CompleteTaskAction()

        result = action.validate()

        assert result.valid is False
        assert any("required" in error.lower() for error in result.errors)

    def test_validate_task_name_warning(self):
        """Test validation warns about ambiguous task name"""
        action = CompleteTaskAction(task_name="My Task")

        result = action.validate()

        # Valid but with warning
        assert result.valid is True
        assert len(result.warnings) > 0
        assert any("ambiguous" in warning.lower() for warning in result.warnings)


class TestCreateNoteAction:
    """Test CreateNoteAction"""

    def test_init(self):
        """Test initialization"""
        action = CreateNoteAction(
            title="Test Note",
            content="Note content",
            tags=["personal", "idea"]
        )

        assert action.title == "Test Note"
        assert action.content == "Note content"
        assert action.tags == ["personal", "idea"]

    def test_init_with_entities(self):
        """Test initialization with entities"""
        entity = Entity(
            type="person",
            value="John Doe",
            confidence=0.9
        )
        action = CreateNoteAction(
            title="Meeting Notes",
            content="Discussion with John",
            entities=[entity]
        )

        assert len(action.entities) == 1
        assert action.entities[0].value == "John Doe"

    def test_action_type(self):
        """Test action type"""
        action = CreateNoteAction(
            title="Test",
            content="Content"
        )

        assert action.action_type == "create_note"

    def test_validate_empty_title(self):
        """Test validation fails for empty title"""
        action = CreateNoteAction(
            title="",
            content="Content"
        )

        result = action.validate()

        assert result.valid is False
        assert any("title" in error.lower() for error in result.errors)

    def test_validate_empty_content(self):
        """Test validation fails for empty content"""
        action = CreateNoteAction(
            title="Title",
            content=""
        )

        result = action.validate()

        assert result.valid is False
        assert any("content" in error.lower() for error in result.errors)

    def test_estimated_duration(self):
        """Test estimated duration"""
        action = CreateNoteAction(
            title="Title",
            content="Content"
        )

        assert action.estimated_duration() == 1.5



class TestUpdateNoteAction:
    """Test UpdateNoteAction"""

    def test_init(self):
        """Test initialization"""
        action = UpdateNoteAction(
            note_id="note123",
            new_content="Updated content"
        )

        assert action.note_id == "note123"
        assert action.new_content == "Updated content"

    def test_init_with_tags(self):
        """Test initialization with tag updates"""
        action = UpdateNoteAction(
            note_id="note123",
            add_tags=["new-tag"],
            remove_tags=["old-tag"]
        )

        assert action.add_tags == ["new-tag"]
        assert action.remove_tags == ["old-tag"]

    def test_action_type(self):
        """Test action type"""
        action = UpdateNoteAction(
            note_id="note123",
            new_content="Content"
        )

        assert action.action_type == "update_note"

    def test_validate_no_note_id(self):
        """Test validation fails without note ID"""
        action = UpdateNoteAction(
            note_id="",
            new_content="Content"
        )

        result = action.validate()

        assert result.valid is False
        assert any("required" in error.lower() for error in result.errors)

    def test_validate_no_updates(self):
        """Test validation fails if no updates specified"""
        action = UpdateNoteAction(note_id="note123")

        result = action.validate()

        assert result.valid is False
        assert any("at least one update" in error.lower() for error in result.errors)

    def test_validate_conflicting_tag_operations(self):
        """Test validation warns about conflicting tag operations"""
        action = UpdateNoteAction(
            note_id="note123",
            replace_tags=["new"],
            add_tags=["another"]  # Conflicting with replace
        )

        result = action.validate()

        # Valid but with warning
        assert len(result.warnings) > 0
        assert any("override" in warning.lower() for warning in result.warnings)

    def test_estimated_duration(self):
        """Test estimated duration"""
        action = UpdateNoteAction(
            note_id="note123",
            new_content="Content"
        )

        assert action.estimated_duration() == 1.5

    def test_dependencies(self):
        """Test no dependencies"""
        action = UpdateNoteAction(
            note_id="note123",
            new_content="Content"
        )

        assert action.dependencies() == []
