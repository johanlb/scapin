"""
OmniFocus History Provider

Provides OmniFocus task history for journal generation.
Uses the OmniFocusProcessor to retrieve real-time data from OmniFocus.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("frontin.journal.providers.omnifocus")


@dataclass
class OmniFocusHistoryProvider:
    """
    Provides OmniFocus task history via AppleScript

    Unlike other providers, this fetches real-time data from
    OmniFocus rather than reading from log files.
    """
    _processor: Optional[Any] = field(default=None, repr=False)

    def _get_processor(self) -> Any:
        """Lazy-load the OmniFocus processor"""
        if self._processor is None:
            from src.trivelin.omnifocus_processor import OmniFocusProcessor
            self._processor = OmniFocusProcessor()
        return self._processor

    def get_omnifocus_items(self, target_date: date) -> list[dict[str, Any]]:
        """
        Get OmniFocus task activity on the target date

        Returns list of dicts with:
        - task_id
        - title
        - status (completed, created, deferred, due, overdue)
        - project
        - tags
        - completed_at
        - due_date
        - flagged
        - estimated_minutes
        - processed_at
        """
        processor = self._get_processor()

        if not processor.is_available():
            logger.debug("OmniFocus not available")
            return []

        try:
            # Get daily stats from OmniFocus
            stats = processor.get_daily_stats()

            result = []
            now_iso = now_utc().isoformat()

            # Completed tasks
            for task in stats.completed_tasks:
                result.append({
                    "task_id": task.task_id,
                    "title": task.name,
                    "status": "completed",
                    "project": task.project_name,
                    "tags": list(task.tags),
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "flagged": task.flagged,
                    "estimated_minutes": task.estimated_minutes,
                    "processed_at": now_iso,
                })

            # Created tasks
            for task in stats.created_tasks:
                # Skip if already in completed (avoid duplicates)
                if any(r["task_id"] == task.task_id for r in result):
                    continue

                result.append({
                    "task_id": task.task_id,
                    "title": task.name,
                    "status": "created",
                    "project": task.project_name,
                    "tags": list(task.tags),
                    "completed_at": None,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "flagged": task.flagged,
                    "estimated_minutes": task.estimated_minutes,
                    "processed_at": now_iso,
                })

            # Due tasks
            for task in stats.due_tasks:
                # Skip if already in result
                if any(r["task_id"] == task.task_id for r in result):
                    continue

                result.append({
                    "task_id": task.task_id,
                    "title": task.name,
                    "status": "due",
                    "project": task.project_name,
                    "tags": list(task.tags),
                    "completed_at": None,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "flagged": task.flagged,
                    "estimated_minutes": task.estimated_minutes,
                    "processed_at": now_iso,
                })

            # Overdue tasks (fetch separately)
            overdue_tasks = processor.get_overdue()
            for task in overdue_tasks:
                # Skip if already in result
                if any(r["task_id"] == task.task_id for r in result):
                    continue

                result.append({
                    "task_id": task.task_id,
                    "title": task.name,
                    "status": "overdue",
                    "project": task.project_name,
                    "tags": list(task.tags),
                    "completed_at": None,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "flagged": task.flagged,
                    "estimated_minutes": task.estimated_minutes,
                    "processed_at": now_iso,
                })

            logger.debug(f"Found {len(result)} OmniFocus items for {target_date}")
            return result

        except Exception as e:
            logger.warning(f"Failed to get OmniFocus items: {e}")
            return []

    # Stub methods to satisfy protocol
    def get_processed_emails(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use email provider"""
        return []

    def get_created_tasks(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use email provider"""
        return []

    def get_decisions(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use email provider"""
        return []

    def get_known_entities(self) -> set[str]:
        """Not implemented - use email provider"""
        return set()

    def get_teams_messages(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use teams provider"""
        return []

    def get_calendar_events(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use calendar provider"""
        return []
