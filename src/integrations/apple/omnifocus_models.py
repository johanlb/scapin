"""
OmniFocus Models

Dataclasses for OmniFocus data used in journaling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    """OmniFocus task status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    ON_HOLD = "on_hold"


class ProjectStatus(str, Enum):
    """OmniFocus project status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    ON_HOLD = "on_hold"


@dataclass(frozen=True)
class OmniFocusTask:
    """
    Represents an OmniFocus task

    Frozen for immutability in journaling context.
    """
    task_id: str
    name: str
    status: TaskStatus

    # Dates
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    defer_date: Optional[datetime] = None

    # Organization
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    # Details
    note: Optional[str] = None
    flagged: bool = False
    estimated_minutes: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "defer_date": self.defer_date.isoformat() if self.defer_date else None,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "tags": list(self.tags),
            "note": self.note,
            "flagged": self.flagged,
            "estimated_minutes": self.estimated_minutes,
        }


@dataclass(frozen=True)
class OmniFocusProject:
    """
    Represents an OmniFocus project
    """
    project_id: str
    name: str
    status: ProjectStatus

    # Dates
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None

    # Organization
    folder_name: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    # Stats
    task_count: int = 0
    remaining_tasks: int = 0
    completed_tasks: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "folder_name": self.folder_name,
            "tags": list(self.tags),
            "task_count": self.task_count,
            "remaining_tasks": self.remaining_tasks,
            "completed_tasks": self.completed_tasks,
        }


@dataclass(frozen=True)
class OmniFocusDailyStats:
    """
    Daily statistics from OmniFocus for journaling
    """
    date: datetime

    # Task counts
    tasks_completed: int = 0
    tasks_created: int = 0
    tasks_due: int = 0
    tasks_overdue: int = 0

    # Lists
    completed_tasks: tuple[OmniFocusTask, ...] = field(default_factory=tuple)
    created_tasks: tuple[OmniFocusTask, ...] = field(default_factory=tuple)
    due_tasks: tuple[OmniFocusTask, ...] = field(default_factory=tuple)

    # Project activity
    projects_modified: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "date": self.date.isoformat(),
            "tasks_completed": self.tasks_completed,
            "tasks_created": self.tasks_created,
            "tasks_due": self.tasks_due,
            "tasks_overdue": self.tasks_overdue,
            "completed_tasks": [t.to_dict() for t in self.completed_tasks],
            "created_tasks": [t.to_dict() for t in self.created_tasks],
            "due_tasks": [t.to_dict() for t in self.due_tasks],
            "projects_modified": list(self.projects_modified),
        }
