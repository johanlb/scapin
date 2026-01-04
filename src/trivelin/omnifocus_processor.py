"""
OmniFocus Processor

Orchestrates OmniFocus task processing for journaling.

Unlike CalendarProcessor, this is synchronous (AppleScript is local)
and primarily focused on journaling data retrieval rather than
real-time event processing.

Pipeline:
1. Fetch tasks from OmniFocus via AppleScript
2. Normalize to PerceivedEvent
3. Aggregate into daily stats
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.core.events import PerceivedEvent
from src.integrations.apple.omnifocus_client import OmniFocusClient
from src.integrations.apple.omnifocus_models import OmniFocusDailyStats, OmniFocusTask
from src.integrations.apple.omnifocus_normalizer import OmniFocusNormalizer
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("trivelin.omnifocus_processor")


@dataclass
class OmniFocusProcessingResult:
    """Result of processing OmniFocus tasks"""

    success: bool
    tasks_processed: int = 0
    tasks_completed: int = 0
    tasks_created: int = 0
    tasks_due: int = 0
    tasks_overdue: int = 0
    error: Optional[str] = None
    processed_at: datetime = field(default_factory=now_utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "tasks_processed": self.tasks_processed,
            "tasks_completed": self.tasks_completed,
            "tasks_created": self.tasks_created,
            "tasks_due": self.tasks_due,
            "tasks_overdue": self.tasks_overdue,
            "error": self.error,
            "processed_at": self.processed_at.isoformat(),
        }


class OmniFocusProcessor:
    """
    OmniFocus task processor for journaling

    Synchronous processor that retrieves and normalizes OmniFocus
    tasks for journaling purposes. Unlike CalendarProcessor, this
    does not do real-time polling or action execution.

    Usage:
        processor = OmniFocusProcessor()

        # Get daily stats for journaling
        stats = processor.get_daily_stats()

        # Get normalized events for processing
        events = processor.get_completed_today_as_events()
    """

    def __init__(
        self,
        client: Optional[OmniFocusClient] = None,
        normalizer: Optional[OmniFocusNormalizer] = None,
    ) -> None:
        """
        Initialize OmniFocus processor

        Args:
            client: Optional pre-configured OmniFocusClient
            normalizer: Optional pre-configured normalizer
        """
        self.client = client or OmniFocusClient()
        self.normalizer = normalizer or OmniFocusNormalizer()

        # Check if OmniFocus is available
        self._is_available: Optional[bool] = None

        logger.info("OmniFocus processor initialized")

    def is_available(self) -> bool:
        """
        Check if OmniFocus is available on this system

        Returns:
            True if OmniFocus is installed and accessible
        """
        if self._is_available is None:
            self._is_available = self.client.is_available()
            logger.info(f"OmniFocus availability: {self._is_available}")
        return self._is_available

    def get_daily_stats(self, date: Optional[datetime] = None) -> OmniFocusDailyStats:
        """
        Get daily statistics for journaling

        Args:
            date: Date to get stats for (defaults to today)

        Returns:
            OmniFocusDailyStats with all daily metrics
        """
        if not self.is_available():
            logger.warning("OmniFocus not available, returning empty stats")
            return OmniFocusDailyStats(date=date or now_utc())

        logger.info(f"Getting OmniFocus daily stats for {(date or now_utc()).date()}")
        return self.client.get_daily_stats(date)

    def get_completed_today(self) -> list[OmniFocusTask]:
        """
        Get all tasks completed today

        Returns:
            List of OmniFocusTask objects
        """
        if not self.is_available():
            return []

        return self.client.get_completed_tasks_today()

    def get_created_today(self) -> list[OmniFocusTask]:
        """
        Get all tasks created today

        Returns:
            List of OmniFocusTask objects
        """
        if not self.is_available():
            return []

        return self.client.get_created_tasks_today()

    def get_due_today(self) -> list[OmniFocusTask]:
        """
        Get all tasks due today

        Returns:
            List of OmniFocusTask objects
        """
        if not self.is_available():
            return []

        return self.client.get_due_tasks_today()

    def get_overdue(self) -> list[OmniFocusTask]:
        """
        Get all overdue tasks

        Returns:
            List of OmniFocusTask objects
        """
        if not self.is_available():
            return []

        return self.client.get_overdue_tasks()

    def get_completed_today_as_events(self) -> list[PerceivedEvent]:
        """
        Get completed tasks as PerceivedEvents

        Useful for cognitive pipeline processing or journaling.

        Returns:
            List of PerceivedEvent objects
        """
        tasks = self.get_completed_today()
        return [self.normalizer.normalize(task) for task in tasks]

    def get_created_today_as_events(self) -> list[PerceivedEvent]:
        """
        Get created tasks as PerceivedEvents

        Returns:
            List of PerceivedEvent objects
        """
        tasks = self.get_created_today()
        return [self.normalizer.normalize(task) for task in tasks]

    def get_due_today_as_events(self) -> list[PerceivedEvent]:
        """
        Get due tasks as PerceivedEvents

        Returns:
            List of PerceivedEvent objects
        """
        tasks = self.get_due_today()
        return [self.normalizer.normalize(task) for task in tasks]

    def get_overdue_as_events(self) -> list[PerceivedEvent]:
        """
        Get overdue tasks as PerceivedEvents

        Returns:
            List of PerceivedEvent objects
        """
        tasks = self.get_overdue()
        return [self.normalizer.normalize(task) for task in tasks]

    def process_for_journal(self) -> OmniFocusProcessingResult:
        """
        Process OmniFocus data for journaling

        Fetches all relevant task data and returns a summary.

        Returns:
            OmniFocusProcessingResult with aggregated data
        """
        logger.info("Processing OmniFocus for journaling")

        if not self.is_available():
            logger.warning("OmniFocus not available")
            return OmniFocusProcessingResult(
                success=False,
                error="OmniFocus not available",
            )

        try:
            stats = self.get_daily_stats()

            result = OmniFocusProcessingResult(
                success=True,
                tasks_processed=(
                    stats.tasks_completed +
                    stats.tasks_created +
                    stats.tasks_due +
                    stats.tasks_overdue
                ),
                tasks_completed=stats.tasks_completed,
                tasks_created=stats.tasks_created,
                tasks_due=stats.tasks_due,
                tasks_overdue=stats.tasks_overdue,
            )

            logger.info(
                "OmniFocus processing complete",
                extra={
                    "completed": stats.tasks_completed,
                    "created": stats.tasks_created,
                    "due": stats.tasks_due,
                    "overdue": stats.tasks_overdue,
                    "projects_modified": len(stats.projects_modified),
                }
            )

            return result

        except Exception as e:
            logger.error(f"Failed to process OmniFocus: {e}")
            return OmniFocusProcessingResult(
                success=False,
                error=str(e),
            )

    def get_all_events_for_date(
        self,
        date: Optional[datetime] = None,
    ) -> list[PerceivedEvent]:
        """
        Get all OmniFocus events for a date as PerceivedEvents

        Combines completed, created, due, and overdue tasks.

        Args:
            date: Date to get events for (defaults to today)

        Returns:
            List of PerceivedEvent objects, deduplicated
        """
        if not self.is_available():
            return []

        # Get stats which fetches all task types
        stats = self.get_daily_stats(date)

        # Combine all tasks with deduplication
        seen_ids: set[str] = set()
        events: list[PerceivedEvent] = []

        for task in stats.completed_tasks:
            if task.task_id not in seen_ids:
                seen_ids.add(task.task_id)
                events.append(self.normalizer.normalize(task))

        for task in stats.created_tasks:
            if task.task_id not in seen_ids:
                seen_ids.add(task.task_id)
                events.append(self.normalizer.normalize(task))

        for task in stats.due_tasks:
            if task.task_id not in seen_ids:
                seen_ids.add(task.task_id)
                events.append(self.normalizer.normalize(task))

        # Overdue tasks (not in stats, fetch separately)
        overdue_tasks = self.get_overdue()
        for task in overdue_tasks:
            if task.task_id not in seen_ids:
                seen_ids.add(task.task_id)
                events.append(self.normalizer.normalize(task))

        logger.debug(f"Retrieved {len(events)} unique OmniFocus events")
        return events
