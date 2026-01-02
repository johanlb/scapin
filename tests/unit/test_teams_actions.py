"""
Unit Tests for Teams Actions

Tests TeamsReplyAction, TeamsFlagAction, TeamsCreateTaskAction.
"""

from datetime import datetime, timezone

from src.figaro.actions.teams import (
    TeamsCreateTaskAction,
    TeamsFlagAction,
    TeamsReplyAction,
    create_teams_flag,
    create_teams_reply,
    create_teams_task,
)


class TestTeamsReplyAction:
    """Tests for TeamsReplyAction"""

    def test_create_reply_action(self):
        """Test creating a reply action"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Thank you for the update!",
        )

        assert action.chat_id == "chat-123"
        assert action.content == "Thank you for the update!"
        assert action.message_id is None
        assert action.action_type == "teams_reply"

    def test_create_reply_action_with_message_id(self):
        """Test creating reply action targeting specific message"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Reply to specific message",
            message_id="msg-456",
        )

        assert action.message_id == "msg-456"

    def test_action_id_is_unique(self):
        """Test that action IDs are unique"""
        action1 = TeamsReplyAction(chat_id="chat-1", content="Content 1")
        action2 = TeamsReplyAction(chat_id="chat-1", content="Content 1")

        assert action1.action_id != action2.action_id
        assert action1.action_id.startswith("teams_reply_")

    def test_validate_success(self):
        """Test validation passes with valid data"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Valid content",
        )

        result = action.validate()

        assert result.valid is True
        assert result.errors == []

    def test_validate_missing_chat_id(self):
        """Test validation fails without chat_id"""
        action = TeamsReplyAction(
            chat_id="",
            content="Some content",
        )

        result = action.validate()

        assert result.valid is False
        assert any("chat_id" in err for err in result.errors)

    def test_validate_missing_content(self):
        """Test validation fails without content"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="",
        )

        result = action.validate()

        assert result.valid is False
        assert any("content" in err for err in result.errors)

    def test_validate_content_too_long(self):
        """Test validation fails with content exceeding limit"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="A" * 30000,  # Exceeds 28000 char limit
        )

        result = action.validate()

        assert result.valid is False
        assert any("28000" in err for err in result.errors)

    def test_validate_warns_long_content(self):
        """Test validation warns for long but valid content"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="A" * 6000,  # Long but under limit
        )

        result = action.validate()

        assert result.valid is True
        assert len(result.warnings) > 0

    def test_execute_success(self):
        """Test successful execution"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Test reply",
        )

        result = action.execute()

        assert result.success is True
        assert result.error is None
        assert result.output["chat_id"] == "chat-123"
        assert result.output["content_length"] == len("Test reply")

    def test_execute_validation_failure(self):
        """Test execution fails on validation error"""
        action = TeamsReplyAction(
            chat_id="",  # Invalid
            content="Test",
        )

        result = action.execute()

        assert result.success is False
        assert result.error is not None

    def test_supports_undo(self):
        """Test undo is supported"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Test",
        )

        assert action.supports_undo() is True

    def test_can_undo_requires_sent_message_id(self):
        """Test can_undo requires sent message ID"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Test",
        )

        result = action.execute()
        assert action.can_undo(result) is False  # No sent_message_id set

    def test_dependencies_empty(self):
        """Test no dependencies"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Test",
        )

        assert action.dependencies() == []

    def test_estimated_duration(self):
        """Test estimated duration is reasonable"""
        action = TeamsReplyAction(
            chat_id="chat-123",
            content="Test",
        )

        assert action.estimated_duration() > 0
        assert action.estimated_duration() < 10  # Should be seconds


class TestTeamsFlagAction:
    """Tests for TeamsFlagAction"""

    def test_create_flag_action(self):
        """Test creating a flag action"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="msg-456",
        )

        assert action.chat_id == "chat-123"
        assert action.message_id == "msg-456"
        assert action.reason is None
        assert action.action_type == "teams_flag"

    def test_create_flag_action_with_reason(self):
        """Test creating flag action with reason"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="msg-456",
            reason="Follow up required",
        )

        assert action.reason == "Follow up required"

    def test_action_id_is_unique(self):
        """Test that action IDs are unique"""
        action1 = TeamsFlagAction(chat_id="chat-1", message_id="msg-1")
        action2 = TeamsFlagAction(chat_id="chat-1", message_id="msg-1")

        assert action1.action_id != action2.action_id
        assert action1.action_id.startswith("teams_flag_")

    def test_validate_success(self):
        """Test validation passes with valid data"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="msg-456",
        )

        result = action.validate()

        assert result.valid is True
        assert result.errors == []

    def test_validate_missing_chat_id(self):
        """Test validation fails without chat_id"""
        action = TeamsFlagAction(
            chat_id="",
            message_id="msg-456",
        )

        result = action.validate()

        assert result.valid is False
        assert any("chat_id" in err for err in result.errors)

    def test_validate_missing_message_id(self):
        """Test validation fails without message_id"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="",
        )

        result = action.validate()

        assert result.valid is False
        assert any("message_id" in err for err in result.errors)

    def test_execute_success(self):
        """Test successful execution"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="msg-456",
            reason="Important",
        )

        result = action.execute()

        assert result.success is True
        assert result.output["flagged"] is True
        assert result.metadata["reason"] == "Important"

    def test_supports_undo(self):
        """Test undo is supported"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="msg-456",
        )

        assert action.supports_undo() is True

    def test_can_undo_after_execution(self):
        """Test can undo after successful execution"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="msg-456",
        )

        result = action.execute()
        assert action.can_undo(result) is True

    def test_undo_success(self):
        """Test undo succeeds"""
        action = TeamsFlagAction(
            chat_id="chat-123",
            message_id="msg-456",
        )

        result = action.execute()
        undo_result = action.undo(result)

        assert undo_result is True


class TestTeamsCreateTaskAction:
    """Tests for TeamsCreateTaskAction"""

    def test_create_task_action(self):
        """Test creating a task action"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Review document",
        )

        assert action.chat_id == "chat-123"
        assert action.message_id == "msg-456"
        assert action.task_title == "Review document"
        assert action.action_type == "teams_create_task"

    def test_create_task_action_with_all_fields(self):
        """Test creating task action with all optional fields"""
        due_date = datetime(2025, 1, 20, 17, 0, tzinfo=timezone.utc)

        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Review document",
            task_note="Important review needed",
            due_date=due_date,
            project="Work",
        )

        assert action.task_note == "Important review needed"
        assert action.due_date == due_date
        assert action.project == "Work"

    def test_action_id_is_unique(self):
        """Test that action IDs are unique"""
        action1 = TeamsCreateTaskAction(
            chat_id="chat-1", message_id="msg-1", task_title="Task"
        )
        action2 = TeamsCreateTaskAction(
            chat_id="chat-1", message_id="msg-1", task_title="Task"
        )

        assert action1.action_id != action2.action_id
        assert action1.action_id.startswith("teams_task_")

    def test_validate_success(self):
        """Test validation passes with valid data"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Valid task title",
        )

        result = action.validate()

        assert result.valid is True
        assert result.errors == []

    def test_validate_missing_chat_id(self):
        """Test validation fails without chat_id"""
        action = TeamsCreateTaskAction(
            chat_id="",
            message_id="msg-456",
            task_title="Task",
        )

        result = action.validate()

        assert result.valid is False
        assert any("chat_id" in err for err in result.errors)

    def test_validate_missing_message_id(self):
        """Test validation fails without message_id"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="",
            task_title="Task",
        )

        result = action.validate()

        assert result.valid is False
        assert any("message_id" in err for err in result.errors)

    def test_validate_missing_task_title(self):
        """Test validation fails without task_title"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="",
        )

        result = action.validate()

        assert result.valid is False
        assert any("task_title" in err for err in result.errors)

    def test_validate_task_title_too_long(self):
        """Test validation fails with task_title exceeding limit"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="A" * 260,  # Exceeds 250 char limit
        )

        result = action.validate()

        assert result.valid is False
        assert any("250" in err for err in result.errors)

    def test_validate_warns_past_due_date(self):
        """Test validation warns for past due date"""
        past_date = datetime(2020, 1, 1, tzinfo=timezone.utc)

        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Task",
            due_date=past_date,
        )

        result = action.validate()

        assert result.valid is True  # Still valid
        assert len(result.warnings) > 0
        assert any("past" in warn for warn in result.warnings)

    def test_execute_success(self):
        """Test successful execution"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Test task",
            project="Inbox",
        )

        result = action.execute()

        assert result.success is True
        assert result.output["task_title"] == "Test task"
        assert result.metadata["project"] == "Inbox"

    def test_supports_undo(self):
        """Test undo is supported"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Task",
        )

        assert action.supports_undo() is True

    def test_can_undo_requires_created_task_id(self):
        """Test can_undo requires created task ID"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Task",
        )

        result = action.execute()
        assert action.can_undo(result) is False  # No _created_task_id set

    def test_estimated_duration(self):
        """Test estimated duration is reasonable"""
        action = TeamsCreateTaskAction(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Task",
        )

        # Task creation should take longer than simple actions
        assert action.estimated_duration() >= 1.0


class TestFactoryFunctions:
    """Tests for factory functions"""

    def test_create_teams_reply(self):
        """Test create_teams_reply factory"""
        action = create_teams_reply(
            chat_id="chat-123",
            content="Hello!",
            message_id="msg-456",
        )

        assert isinstance(action, TeamsReplyAction)
        assert action.chat_id == "chat-123"
        assert action.content == "Hello!"
        assert action.message_id == "msg-456"

    def test_create_teams_reply_minimal(self):
        """Test create_teams_reply with minimal args"""
        action = create_teams_reply(
            chat_id="chat-123",
            content="Hello!",
        )

        assert isinstance(action, TeamsReplyAction)
        assert action.message_id is None

    def test_create_teams_flag(self):
        """Test create_teams_flag factory"""
        action = create_teams_flag(
            chat_id="chat-123",
            message_id="msg-456",
            reason="Important",
        )

        assert isinstance(action, TeamsFlagAction)
        assert action.chat_id == "chat-123"
        assert action.message_id == "msg-456"
        assert action.reason == "Important"

    def test_create_teams_flag_minimal(self):
        """Test create_teams_flag with minimal args"""
        action = create_teams_flag(
            chat_id="chat-123",
            message_id="msg-456",
        )

        assert isinstance(action, TeamsFlagAction)
        assert action.reason is None

    def test_create_teams_task(self):
        """Test create_teams_task factory"""
        due_date = datetime(2025, 1, 20, tzinfo=timezone.utc)

        action = create_teams_task(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Review",
            task_note="Note",
            due_date=due_date,
            project="Work",
        )

        assert isinstance(action, TeamsCreateTaskAction)
        assert action.chat_id == "chat-123"
        assert action.message_id == "msg-456"
        assert action.task_title == "Review"
        assert action.task_note == "Note"
        assert action.due_date == due_date
        assert action.project == "Work"

    def test_create_teams_task_minimal(self):
        """Test create_teams_task with minimal args"""
        action = create_teams_task(
            chat_id="chat-123",
            message_id="msg-456",
            task_title="Task",
        )

        assert isinstance(action, TeamsCreateTaskAction)
        assert action.task_note is None
        assert action.due_date is None
        assert action.project is None
