"""
Task Actions for Figaro

Concrete implementations of task-related actions using OmniFocus.
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.figaro.actions.base import Action, ActionResult, ValidationResult
from src.monitoring.logger import get_logger

logger = get_logger("figaro.actions.tasks")


def _sanitize_id_component(text: str, max_length: int = 30) -> str:
    """
    Sanitize text for use in action IDs

    Removes special characters and limits length to prevent
    injection attacks or malformed IDs.

    Args:
        text: Text to sanitize
        max_length: Maximum length of sanitized text

    Returns:
        Sanitized text safe for use in action IDs
    """
    if not text:
        return "unknown"

    # Remove all characters except alphanumeric, spaces, underscores, and hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9_ -]', '', text)

    # Collapse multiple spaces/underscores
    sanitized = re.sub(r'[\s_-]+', '_', sanitized)

    # Strip leading/trailing underscores and whitespace
    sanitized = sanitized.strip('_ ')

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Ensure non-empty
    return sanitized if sanitized else "unknown"


@dataclass
class CreateTaskAction(Action):
    """
    Create a new task in OmniFocus

    This action can create tasks with:
    - Title and notes
    - Due date and defer date
    - Tags
    - Project assignment
    - Estimated duration
    """

    name: str
    note: Optional[str] = None
    project_name: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    due_date: Optional[str] = None  # ISO format
    defer_date: Optional[str] = None  # ISO format
    estimated_minutes: Optional[int] = None
    flagged: bool = False

    # Stable unique ID (generated once on creation)
    _action_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False, repr=False)

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        safe_name = _sanitize_id_component(self.name, max_length=30)
        return f"create_task_{safe_name}_{self._action_id[:8]}"

    @property
    def action_type(self) -> str:
        """Action type"""
        return "create_task"

    def supports_undo(self) -> bool:
        """Task creation supports undo"""
        return True

    def validate(self) -> ValidationResult:
        """
        Validate task creation

        Checks:
        1. Name is not empty
        2. Date formats are valid (if provided)
        3. Estimated minutes is positive (if provided)
        """
        errors = []
        warnings = []

        if not self.name or not self.name.strip():
            errors.append("Task name is required")

        if self.estimated_minutes is not None and self.estimated_minutes <= 0:
            errors.append(f"Estimated minutes must be positive: {self.estimated_minutes}")

        # Validate date formats
        if self.due_date:
            try:
                datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"Invalid due date format: {self.due_date} (use ISO format)")

        if self.defer_date:
            try:
                datetime.fromisoformat(self.defer_date.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"Invalid defer date format: {self.defer_date} (use ISO format)")

        # Warn if defer date is after due date
        if self.due_date and self.defer_date:
            try:
                due = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
                defer = datetime.fromisoformat(self.defer_date.replace('Z', '+00:00'))
                if defer > due:
                    warnings.append("Defer date is after due date")
            except ValueError:
                pass  # Already caught above

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def execute(self) -> ActionResult:
        """
        Execute task creation

        Creates task in OmniFocus using MCP tools.
        """
        start_time = time.time()

        try:
            # Import here to avoid circular dependencies
            from src.integrations.apple.omnifocus_client import OmniFocusClient

            client = OmniFocusClient()

            # Create task
            result = client.add_task(
                name=self.name,
                note=self.note,
                project_name=self.project_name,
                tags=self.tags if self.tags else [],
                due_date=self.due_date,
                defer_date=self.defer_date,
                estimated_minutes=self.estimated_minutes,
                flagged=self.flagged
            )

            # Extract task ID
            created_task_id = result.get("id")

            duration = time.time() - start_time

            logger.info(
                f"Created task: {self.name}",
                extra={
                    "task_name": self.name,
                    "task_id": created_task_id,
                    "project": self.project_name,
                    "tags": self.tags,
                    "duration": duration
                }
            )

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "task_id": created_task_id,
                    "task_name": self.name,
                    "project": self.project_name
                },
                metadata={
                    "action": self,
                    "created_task_id": created_task_id  # Store for undo
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to create task '{self.name}': {e}", exc_info=True)

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
                metadata={"action": self}
            )

    def can_undo(self, result: ActionResult) -> bool:
        """Task creation is reversible if we have the task ID"""
        return result.success and "created_task_id" in result.metadata

    def undo(self, result: ActionResult) -> bool:
        """
        Undo task creation by deleting the task

        Note: This permanently deletes the task from OmniFocus.

        Args:
            result: The ActionResult from execute() containing created_task_id
        """
        if not self.can_undo(result):
            logger.warning("Cannot undo task creation: not executed or task ID unknown")
            return False

        try:
            from src.integrations.apple.omnifocus_client import OmniFocusClient

            client = OmniFocusClient()

            # Extract task ID from result
            created_task_id = result.metadata["created_task_id"]

            # Delete the created task
            client.remove_task(task_id=created_task_id)

            logger.info(
                f"Undid task creation: {self.name}",
                extra={
                    "task_name": self.name,
                    "task_id": created_task_id
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to undo task creation for '{self.name}': {e}", exc_info=True)
            return False

    def dependencies(self) -> list[str]:
        """Task creation has no dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated duration in seconds"""
        return 1.0  # OmniFocus operations are typically very fast


@dataclass
class CompleteTaskAction(Action):
    """
    Mark a task as completed in OmniFocus

    This action is reversible - tasks can be marked incomplete.
    """

    task_id: Optional[str] = None
    task_name: Optional[str] = None  # Alternative to task_id

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        identifier = self.task_id or self.task_name or "unknown"
        safe_identifier = _sanitize_id_component(identifier, max_length=40)
        return f"complete_task_{safe_identifier}"

    @property
    def action_type(self) -> str:
        """Action type"""
        return "complete_task"

    def supports_undo(self) -> bool:
        """Task completion supports undo"""
        return True

    def validate(self) -> ValidationResult:
        """
        Validate task completion

        Requires either task_id or task_name.
        """
        errors = []
        warnings = []

        if not self.task_id and not self.task_name:
            errors.append("Either task_id or task_name is required")

        if self.task_name:
            warnings.append("Using task_name may be ambiguous if multiple tasks have the same name")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def execute(self) -> ActionResult:
        """
        Execute task completion

        Marks task as completed in OmniFocus.
        """
        start_time = time.time()

        try:
            from src.integrations.apple.omnifocus_client import OmniFocusClient

            client = OmniFocusClient()

            # Resolve task ID if needed
            resolved_task_id: str
            if self.task_id:
                resolved_task_id = self.task_id
            elif self.task_name:
                # Find task by name
                task = client.get_task_by_name(self.task_name)
                if not task:
                    raise ValueError(f"Task not found: {self.task_name}")
                resolved_task_id = task.get("id")
            else:
                raise ValueError("Either task_id or task_name is required")

            # Mark as completed
            client.edit_task(
                task_id=resolved_task_id,
                new_status="completed"
            )

            duration = time.time() - start_time

            logger.info(
                f"Completed task: {self.task_name or self.task_id}",
                extra={
                    "task_id": resolved_task_id,
                    "task_name": self.task_name,
                    "duration": duration
                }
            )

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "task_id": resolved_task_id,
                    "status": "completed"
                },
                metadata={
                    "action": self,
                    "resolved_task_id": resolved_task_id  # Store for undo
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Failed to complete task '{self.task_name or self.task_id}': {e}",
                exc_info=True
            )

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
                metadata={"action": self}
            )

    def can_undo(self, result: ActionResult) -> bool:
        """Task completion is reversible"""
        return result.success and "resolved_task_id" in result.metadata

    def undo(self, result: ActionResult) -> bool:
        """
        Undo task completion by marking as incomplete

        Args:
            result: The ActionResult from execute() containing resolved_task_id
        """
        if not self.can_undo(result):
            logger.warning("Cannot undo task completion: not executed or task ID unknown")
            return False

        try:
            from src.integrations.apple.omnifocus_client import OmniFocusClient

            client = OmniFocusClient()

            # Extract task ID from result
            resolved_task_id = result.metadata["resolved_task_id"]

            # Mark as incomplete
            client.edit_task(
                task_id=resolved_task_id,
                new_status="incomplete"
            )

            logger.info(
                f"Undid task completion: {self.task_name or self.task_id}",
                extra={
                    "task_id": resolved_task_id,
                    "task_name": self.task_name
                }
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to undo task completion for '{self.task_name or self.task_id}': {e}",
                exc_info=True
            )
            return False

    def dependencies(self) -> list[str]:
        """Task completion has no dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated duration in seconds"""
        return 1.0
