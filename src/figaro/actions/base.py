"""
Base Action Classes for Figaro

Defines abstract base class and common types for all actions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ExecutionMode(str, Enum):
    """Execution mode for actions"""
    AUTO = "auto"        # Execute automatically without user approval
    REVIEW = "review"    # Queue for user review before execution
    MANUAL = "manual"    # Requires manual execution by user


@dataclass
class ValidationResult:
    """Result of action validation"""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean context"""
        return self.valid


class ValidationBuilder:
    """
    Fluent builder for ValidationResult.

    Allows chaining validation checks for cleaner validation code.

    Example:
        return (ValidationBuilder()
            .error_if(not self.name, "Name is required")
            .error_if(self.amount < 0, "Amount must be positive")
            .warning_if(self.amount > 1000, "Large amount detected")
            .build())
    """

    def __init__(self) -> None:
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def error(self, message: str) -> "ValidationBuilder":
        """Add an error message."""
        self._errors.append(message)
        return self

    def error_if(self, condition: bool, message: str) -> "ValidationBuilder":
        """Add an error message if condition is True."""
        if condition:
            self._errors.append(message)
        return self

    def error_unless(self, condition: bool, message: str) -> "ValidationBuilder":
        """Add an error message if condition is False."""
        if not condition:
            self._errors.append(message)
        return self

    def warning(self, message: str) -> "ValidationBuilder":
        """Add a warning message."""
        self._warnings.append(message)
        return self

    def warning_if(self, condition: bool, message: str) -> "ValidationBuilder":
        """Add a warning message if condition is True."""
        if condition:
            self._warnings.append(message)
        return self

    def validate_date(self, value: str | None, field_name: str) -> "ValidationBuilder":
        """Validate ISO date format if value is provided."""
        if value:
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                self._errors.append(f"Invalid {field_name} format: {value} (use ISO format)")
        return self

    def build(self) -> ValidationResult:
        """Build the ValidationResult."""
        return ValidationResult(
            valid=len(self._errors) == 0,
            errors=self._errors,
            warnings=self._warnings,
        )

    @property
    def is_valid(self) -> bool:
        """Check if validation passes so far (no errors)."""
        return len(self._errors) == 0


@dataclass
class ActionResult:
    """Result of action execution"""
    success: bool
    duration: float  # Execution time in seconds
    output: Any = None
    error: Optional[Exception] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    executed_at: Optional[datetime] = None

    def __post_init__(self):
        """Set executed_at to current time if not provided"""
        if self.executed_at is None:
            self.executed_at = datetime.now()

    def __bool__(self) -> bool:
        """Allow using ActionResult in boolean context"""
        return self.success


class Action(ABC):
    """
    Abstract base class for all actions

    All actions must implement:
    - validation (pre-execution checks)
    - execution (the actual work)
    - undo support (for rollback)
    - dependency declaration

    Actions are immutable once created and should be lightweight data holders.
    Heavy operations should happen in execute(), not __init__().
    """

    @property
    @abstractmethod
    def action_id(self) -> str:
        """
        Unique identifier for this action

        Used for:
        - Dependency resolution
        - Logging and debugging
        - Deduplication

        Returns:
            Unique string identifier
        """
        pass

    @property
    @abstractmethod
    def action_type(self) -> str:
        """
        Type of action (e.g., 'archive_email', 'create_task')

        Returns:
            Action type string
        """
        pass

    @abstractmethod
    def validate(self) -> ValidationResult:
        """
        Validate action before execution

        Checks:
        - Required resources exist
        - Permissions are valid
        - Parameters are correct

        Returns:
            ValidationResult with status and any errors/warnings
        """
        pass

    @abstractmethod
    def execute(self) -> ActionResult:
        """
        Execute the action

        This is where the actual work happens. Should be:
        - Idempotent (safe to run multiple times)
        - Atomic (succeeds or fails completely)
        - Fast (offload long operations to background if needed)

        Returns:
            ActionResult with execution status and output
        """
        pass

    def supports_undo(self) -> bool:
        """
        Check if this action type supports undo in general

        This is a static check that doesn't require an ActionResult.
        Used for planning and risk assessment.

        Returns:
            True if this action type can be undone (default: False)
        """
        return False

    @abstractmethod
    def can_undo(self, result: ActionResult) -> bool:
        """
        Check if this action supports rollback

        Args:
            result: The ActionResult from execute() containing state needed for undo

        Returns:
            True if undo() can reverse this action
        """
        pass

    @abstractmethod
    def undo(self, result: ActionResult) -> bool:
        """
        Rollback/reverse this action

        Only called if can_undo() returns True.
        Should restore state to before execute() was called.

        Args:
            result: The ActionResult from execute() containing state needed for undo

        Returns:
            True if undo succeeded, False otherwise
        """
        pass

    @abstractmethod
    def dependencies(self) -> list[str]:
        """
        List of action IDs that must execute before this one

        Used by orchestrator to build execution DAG.

        Returns:
            List of action_id strings (empty if no dependencies)
        """
        pass

    @abstractmethod
    def estimated_duration(self) -> float:
        """
        Estimated execution time in seconds

        Used for:
        - Progress estimation
        - Timeout configuration
        - Resource planning

        Returns:
            Estimated duration in seconds
        """
        pass

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"{self.__class__.__name__}(id={self.action_id}, type={self.action_type})"

    def __hash__(self) -> int:
        """Make actions hashable for use in sets/dicts"""
        return hash(self.action_id)

    def __eq__(self, other: object) -> bool:
        """Actions are equal if they have the same ID"""
        if not isinstance(other, Action):
            return NotImplemented
        return self.action_id == other.action_id
