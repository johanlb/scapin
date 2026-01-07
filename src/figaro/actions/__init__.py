"""
Figaro Actions - Concrete Action Implementations

Provides executable actions for email, tasks, notes, Teams, and Calendar.
"""

from src.figaro.actions.base import Action, ActionResult, ExecutionMode, ValidationResult
from src.figaro.actions.calendar import (
    CalendarBlockTimeAction,
    CalendarCreateEventAction,
    CalendarCreateTaskFromEventAction,
    CalendarRespondAction,
)
from src.figaro.actions.email import (
    ArchiveEmailAction,
    DeleteEmailAction,
    MoveEmailAction,
    PrepareEmailReplyAction,
    create_email_reply_draft,
)
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
    "PrepareEmailReplyAction",
    "create_email_reply_draft",

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
    # Calendar actions
    "CalendarCreateEventAction",
    "CalendarRespondAction",
    "CalendarCreateTaskFromEventAction",
    "CalendarBlockTimeAction",
]
