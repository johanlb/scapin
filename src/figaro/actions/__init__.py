"""
Figaro Actions - Concrete Action Implementations

Provides executable actions for email, tasks, and notes.
"""

from src.figaro.actions.base import Action, ActionResult, ExecutionMode, ValidationResult
from src.figaro.actions.email import ArchiveEmailAction, DeleteEmailAction, MoveEmailAction
from src.figaro.actions.notes import CreateNoteAction, UpdateNoteAction
from src.figaro.actions.tasks import CompleteTaskAction, CreateTaskAction

__all__ = [
    # Base classes
    "Action",
    "ActionResult",
    "ExecutionMode",
    "ValidationResult",

    # Email actions
    "ArchiveEmailAction",
    "DeleteEmailAction",
    "MoveEmailAction",

    # Task actions
    "CreateTaskAction",
    "CompleteTaskAction",

    # Note actions
    "CreateNoteAction",
    "UpdateNoteAction"
]
