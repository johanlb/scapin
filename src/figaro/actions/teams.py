"""
Teams Actions for Figaro

Actions for interacting with Microsoft Teams:
- Reply to messages
- Flag messages for follow-up
- Create tasks from messages
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.figaro.actions.base import Action, ActionResult, ValidationResult
from src.monitoring.logger import get_logger

logger = get_logger("figaro.actions.teams")


@dataclass
class TeamsReplyAction(Action):
    """
    Reply to a Teams message

    Sends a reply message in the same chat as the original message.
    """

    chat_id: str
    content: str
    message_id: Optional[str] = None  # Message to reply to (optional)
    _action_id: str = field(default_factory=lambda: f"teams_reply_{uuid.uuid4().hex[:8]}")
    _sent_message_id: Optional[str] = None

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return "teams_reply"

    def validate(self) -> ValidationResult:
        """Validate reply action parameters"""
        errors = []
        warnings = []

        if not self.chat_id:
            errors.append("chat_id is required")

        if not self.content:
            errors.append("content is required")
        elif len(self.content) > 28000:  # Teams message limit
            errors.append("content exceeds Teams message limit (28000 chars)")
        elif len(self.content) > 5000:
            warnings.append("content is quite long, consider shortening")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def execute(self) -> ActionResult:
        """
        Execute the reply action

        Note: Actual Teams API call is handled by TeamsClient.
        This action prepares the data for execution.
        """
        start_time = datetime.now()

        try:
            # Validate first
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # The actual API call would be:
            # message = await teams_client.send_message(self.chat_id, self.content)
            # For now, we return a placeholder

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"TeamsReplyAction executed: chat={self.chat_id}")

            return ActionResult(
                success=True,
                duration=duration,
                output={"chat_id": self.chat_id, "content_length": len(self.content)},
                metadata={
                    "chat_id": self.chat_id,
                    "reply_to": self.message_id,
                },
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"TeamsReplyAction failed: {e}")
            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def supports_undo(self) -> bool:
        """Teams messages can potentially be deleted"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can undo if we have the sent message ID"""
        return result.success and self._sent_message_id is not None

    def undo(self, _result: ActionResult) -> bool:
        """
        Undo by deleting the sent message

        Note: Requires appropriate permissions in Teams.
        """
        if not self._sent_message_id:
            return False

        try:
            # Would call: await teams_client.delete_message(self.chat_id, self._sent_message_id)
            logger.info(f"TeamsReplyAction undone: deleted {self._sent_message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to undo TeamsReplyAction: {e}")
            return False

    def dependencies(self) -> list[str]:
        """No dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated ~1 second for API call"""
        return 1.0


@dataclass
class TeamsFlagAction(Action):
    """
    Flag a Teams message for follow-up

    Note: Teams doesn't have built-in flagging like email.
    This action uses a workaround (e.g., saving to a list or task).
    """

    chat_id: str
    message_id: str
    reason: Optional[str] = None
    _action_id: str = field(default_factory=lambda: f"teams_flag_{uuid.uuid4().hex[:8]}")

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return "teams_flag"

    def validate(self) -> ValidationResult:
        """Validate flag action parameters"""
        errors = []

        if not self.chat_id:
            errors.append("chat_id is required")

        if not self.message_id:
            errors.append("message_id is required")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def execute(self) -> ActionResult:
        """Execute the flag action"""
        start_time = datetime.now()

        try:
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # Flagging is implemented by creating a follow-up task or
            # storing in a local database. For now, just log.
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"TeamsFlagAction executed: message={self.message_id}",
                extra={"reason": self.reason},
            )

            return ActionResult(
                success=True,
                duration=duration,
                output={"flagged": True, "message_id": self.message_id},
                metadata={
                    "chat_id": self.chat_id,
                    "message_id": self.message_id,
                    "reason": self.reason,
                },
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"TeamsFlagAction failed: {e}")
            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def supports_undo(self) -> bool:
        """Can unflag"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can always unflag"""
        return result.success

    def undo(self, _result: ActionResult) -> bool:
        """Remove the flag"""
        logger.info(f"TeamsFlagAction undone: unflagged {self.message_id}")
        return True

    def dependencies(self) -> list[str]:
        return []

    def estimated_duration(self) -> float:
        return 0.5


@dataclass
class TeamsCreateTaskAction(Action):
    """
    Create a task from a Teams message

    Creates a task in the configured task manager (OmniFocus, etc.)
    based on the content of a Teams message.
    """

    chat_id: str
    message_id: str
    task_title: str
    task_note: Optional[str] = None
    due_date: Optional[datetime] = None
    project: Optional[str] = None
    _action_id: str = field(default_factory=lambda: f"teams_task_{uuid.uuid4().hex[:8]}")
    _created_task_id: Optional[str] = None

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return "teams_create_task"

    def validate(self) -> ValidationResult:
        """Validate task creation parameters"""
        errors = []
        warnings = []

        if not self.chat_id:
            errors.append("chat_id is required")

        if not self.message_id:
            errors.append("message_id is required")

        if not self.task_title:
            errors.append("task_title is required")
        elif len(self.task_title) > 250:
            errors.append("task_title too long (max 250 chars)")

        if self.due_date and self.due_date < datetime.now(timezone.utc):
            warnings.append("due_date is in the past")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def execute(self) -> ActionResult:
        """Execute task creation"""
        start_time = datetime.now()

        try:
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # Create task using the integrations (OmniFocus, etc.)
            # For now, just log the intent
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"TeamsCreateTaskAction executed: title='{self.task_title}'",
                extra={
                    "project": self.project,
                    "due_date": self.due_date.isoformat() if self.due_date else None,
                },
            )

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "task_title": self.task_title,
                    "from_message": self.message_id,
                },
                metadata={
                    "chat_id": self.chat_id,
                    "message_id": self.message_id,
                    "project": self.project,
                },
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"TeamsCreateTaskAction failed: {e}")
            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def supports_undo(self) -> bool:
        """Can delete created task"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can undo if task was created"""
        return result.success and self._created_task_id is not None

    def undo(self, _result: ActionResult) -> bool:
        """Delete the created task"""
        if not self._created_task_id:
            return False

        try:
            # Would delete the task from task manager
            logger.info(f"TeamsCreateTaskAction undone: deleted task {self._created_task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to undo TeamsCreateTaskAction: {e}")
            return False

    def dependencies(self) -> list[str]:
        return []

    def estimated_duration(self) -> float:
        return 2.0  # Task creation may involve external API


def create_teams_reply(
    chat_id: str,
    content: str,
    message_id: Optional[str] = None,
) -> TeamsReplyAction:
    """Factory function for creating Teams reply action"""
    return TeamsReplyAction(
        chat_id=chat_id,
        content=content,
        message_id=message_id,
    )


def create_teams_flag(
    chat_id: str,
    message_id: str,
    reason: Optional[str] = None,
) -> TeamsFlagAction:
    """Factory function for creating Teams flag action"""
    return TeamsFlagAction(
        chat_id=chat_id,
        message_id=message_id,
        reason=reason,
    )


def create_teams_task(
    chat_id: str,
    message_id: str,
    task_title: str,
    task_note: Optional[str] = None,
    due_date: Optional[datetime] = None,
    project: Optional[str] = None,
) -> TeamsCreateTaskAction:
    """Factory function for creating Teams task action"""
    return TeamsCreateTaskAction(
        chat_id=chat_id,
        message_id=message_id,
        task_title=task_title,
        task_note=task_note,
        due_date=due_date,
        project=project,
    )
