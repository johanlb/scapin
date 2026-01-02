"""
Figaro Actions - Concrete Action Implementations

Provides executable actions for email, tasks, notes, and Teams.
"""

from src.figaro.actions.base import Action, ActionResult, ExecutionMode, ValidationResult
from src.figaro.actions.email import ArchiveEmailAction, DeleteEmailAction, MoveEmailAction
from src.figaro.actions.notes import CreateNoteAction, UpdateNoteAction
from src.figaro.actions.tasks import CompleteTaskAction, CreateTaskAction
from src.figaro.actions.teams import (
    TeamsCreateTaskAction,
    TeamsFlagAction,
    TeamsReplyAction,
    create_teams_flag,
    create_teams_reply,
    create_teams_task,
)

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
    "UpdateNoteAction",

    # Teams actions
    "TeamsReplyAction",
    "TeamsFlagAction",
    "TeamsCreateTaskAction",
    "create_teams_reply",
    "create_teams_flag",
    "create_teams_task",
]
