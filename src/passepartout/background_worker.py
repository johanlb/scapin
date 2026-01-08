"""
Background Worker for Note Review

24/7 background process that handles note reviews according to SM-2 scheduling.
Designed to run without blocking the frontend or API.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager
from src.passepartout.note_metadata import NoteMetadataStore
from src.passepartout.note_reviewer import NoteReviewer, ReviewResult
from src.passepartout.note_scheduler import NoteScheduler

if TYPE_CHECKING:
    from src.passepartout.cross_source import CrossSourceEngine

logger = get_logger("passepartout.background_worker")


class WorkerState(str, Enum):
    """Worker states"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class WorkerStats:
    """Statistics for worker operation"""

    reviews_today: int = 0
    reviews_total: int = 0
    actions_applied: int = 0
    actions_pending: int = 0
    errors_today: int = 0
    last_review_at: datetime | None = None
    session_start: datetime | None = None
    average_review_seconds: float = 0.0


@dataclass
class WorkerConfig:
    """Configuration for background worker"""

    # Daily limits
    max_daily_reviews: int = 50
    max_session_minutes: int = 5

    # Timing
    sleep_between_reviews_seconds: float = 10.0
    sleep_when_idle_seconds: float = 300.0  # 5 minutes
    sleep_on_error_seconds: float = 60.0

    # Throttling
    cpu_throttle_threshold: float = 80.0  # Pause if CPU > 80%
    pause_on_rate_limit: bool = True

    # Notifications
    notify_on_high_confidence: bool = True
    notify_threshold: float = 0.9


class BackgroundWorker:
    """
    Background worker for 24/7 note review

    Constraints:
    - Max 50 reviews per day
    - Max 5 minutes per session
    - Throttling if system is under load
    - Pause on API rate limiting

    Usage:
        worker = BackgroundWorker(notes_dir=Path("data/notes"))
        await worker.run()  # Runs continuously
    """

    def __init__(
        self,
        notes_dir: Path,
        data_dir: Path | None = None,
        config: WorkerConfig | None = None,
        cross_source_engine: "CrossSourceEngine | None" = None,
        on_review_complete: Callable[[ReviewResult], None] | None = None,
        on_state_change: Callable[[WorkerState], None] | None = None,
    ):
        """
        Initialize background worker

        Args:
            notes_dir: Directory containing notes
            data_dir: Directory for data storage (default: data/)
            config: Worker configuration
            cross_source_engine: CrossSourceEngine for multi-source context retrieval
            on_review_complete: Callback when review completes
            on_state_change: Callback when state changes
        """
        self.notes_dir = Path(notes_dir)
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.config = config or WorkerConfig()
        self._cross_source_engine = cross_source_engine

        # Callbacks
        self.on_review_complete = on_review_complete
        self.on_state_change = on_state_change

        # State
        self._state = WorkerState.STOPPED
        self._stats = WorkerStats()
        self._stop_requested = False
        self._pause_requested = False
        self._session_start: datetime | None = None

        # Components (lazy init)
        self._note_manager: NoteManager | None = None
        self._metadata_store: NoteMetadataStore | None = None
        self._scheduler: NoteScheduler | None = None
        self._reviewer: NoteReviewer | None = None

    @property
    def state(self) -> WorkerState:
        return self._state

    @property
    def stats(self) -> WorkerStats:
        return self._stats

    def _set_state(self, state: WorkerState) -> None:
        """Update state and notify"""
        if state != self._state:
            self._state = state
            logger.info(f"Worker state changed to: {state.value}")
            if self.on_state_change:
                self.on_state_change(state)

    def _init_components(self) -> None:
        """Initialize worker components"""
        if self._note_manager is None:
            self._note_manager = NoteManager(
                notes_dir=self.notes_dir,
                auto_index=True,
                git_enabled=True,
            )

        if self._metadata_store is None:
            db_path = self.data_dir / "notes_meta.db"
            self._metadata_store = NoteMetadataStore(db_path)

        if self._scheduler is None:
            self._scheduler = NoteScheduler(self._metadata_store)

        if self._reviewer is None:
            self._reviewer = NoteReviewer(
                note_manager=self._note_manager,
                metadata_store=self._metadata_store,
                scheduler=self._scheduler,
                cross_source_engine=self._cross_source_engine,
            )

    def _remaining_today(self) -> int:
        """Calculate remaining reviews for today"""
        return max(0, self.config.max_daily_reviews - self._stats.reviews_today)

    def _session_timeout(self) -> bool:
        """Check if session has timed out"""
        if self._session_start is None:
            return False

        elapsed = (datetime.now(timezone.utc) - self._session_start).total_seconds()
        return elapsed >= self.config.max_session_minutes * 60

    def _should_pause(self) -> bool:
        """Check if worker should pause"""
        if self._pause_requested:
            return True

        if self._remaining_today() <= 0:
            logger.info("Daily review limit reached")
            return True

        # Check CPU usage (simplified - would use psutil in production)
        # For now, always return False
        return False

    def _reset_daily_stats(self) -> None:
        """Reset daily statistics at midnight"""
        now = datetime.now(timezone.utc)

        if self._stats.last_review_at:
            last_day = self._stats.last_review_at.date()
            current_day = now.date()

            if current_day > last_day:
                logger.info("New day detected, resetting daily stats")
                self._stats.reviews_today = 0
                self._stats.errors_today = 0

    async def run(self) -> None:
        """
        Main worker loop

        Runs continuously until stopped.
        """
        logger.info("Starting background worker")
        self._init_components()
        self._set_state(WorkerState.RUNNING)
        self._stop_requested = False

        while not self._stop_requested:
            try:
                # Reset daily stats if needed
                self._reset_daily_stats()

                # Check if should pause
                if self._should_pause():
                    self._set_state(WorkerState.PAUSED)
                    await asyncio.sleep(self.config.sleep_on_error_seconds)
                    continue

                self._set_state(WorkerState.RUNNING)

                # Get notes due for review
                assert self._scheduler is not None
                due_notes = self._scheduler.get_notes_due(
                    limit=min(10, self._remaining_today())
                )

                if not due_notes:
                    self._set_state(WorkerState.IDLE)
                    logger.debug("No notes due, sleeping")
                    await asyncio.sleep(self.config.sleep_when_idle_seconds)
                    continue

                # Start session
                self._session_start = datetime.now(timezone.utc)
                self._stats.session_start = self._session_start

                # Process each note
                for metadata in due_notes:
                    if self._stop_requested:
                        break

                    if self._session_timeout():
                        logger.info("Session timeout reached")
                        break

                    await self._process_note(metadata.note_id)
                    await asyncio.sleep(self.config.sleep_between_reviews_seconds)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                self._stats.errors_today += 1
                await asyncio.sleep(self.config.sleep_on_error_seconds)

        self._set_state(WorkerState.STOPPED)
        logger.info("Background worker stopped")

    async def _process_note(self, note_id: str) -> ReviewResult | None:
        """Process a single note review"""
        logger.info(f"Processing note: {note_id}")
        start_time = time.time()

        try:
            assert self._reviewer is not None
            result = await self._reviewer.review_note(note_id)

            # Update stats
            elapsed = time.time() - start_time
            self._stats.reviews_today += 1
            self._stats.reviews_total += 1
            self._stats.actions_applied += len(result.applied_actions)
            self._stats.actions_pending += len(result.pending_actions)
            self._stats.last_review_at = datetime.now(timezone.utc)

            # Update average review time
            total = self._stats.reviews_total
            self._stats.average_review_seconds = (
                (self._stats.average_review_seconds * (total - 1) + elapsed) / total
            )

            # Notify if callback registered
            if self.on_review_complete:
                self.on_review_complete(result)

            logger.info(
                f"Review complete for {note_id}: "
                f"Q={result.quality}, applied={len(result.applied_actions)}, "
                f"pending={len(result.pending_actions)}, time={elapsed:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Error reviewing note {note_id}: {e}")
            self._stats.errors_today += 1
            return None

    def stop(self) -> None:
        """Request worker to stop"""
        logger.info("Stop requested")
        self._stop_requested = True

    def pause(self) -> None:
        """Request worker to pause"""
        logger.info("Pause requested")
        self._pause_requested = True

    def resume(self) -> None:
        """Resume from pause"""
        logger.info("Resume requested")
        self._pause_requested = False

    def get_status(self) -> dict[str, Any]:
        """Get current worker status"""
        return {
            "state": self._state.value,
            "stats": {
                "reviews_today": self._stats.reviews_today,
                "reviews_total": self._stats.reviews_total,
                "actions_applied": self._stats.actions_applied,
                "actions_pending": self._stats.actions_pending,
                "errors_today": self._stats.errors_today,
                "last_review_at": (
                    self._stats.last_review_at.isoformat()
                    if self._stats.last_review_at
                    else None
                ),
                "average_review_seconds": round(
                    self._stats.average_review_seconds, 2
                ),
            },
            "config": {
                "max_daily_reviews": self.config.max_daily_reviews,
                "max_session_minutes": self.config.max_session_minutes,
                "remaining_today": self._remaining_today(),
            },
        }


class BackgroundWorkerManager:
    """
    Manager for background worker process

    Handles starting, stopping, and monitoring the worker.
    """

    _instance: "BackgroundWorkerManager | None" = None
    _worker: BackgroundWorker | None = None
    _task: asyncio.Task | None = None

    @classmethod
    def get_instance(cls) -> "BackgroundWorkerManager":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._worker = None
        self._task = None

    async def start(
        self,
        notes_dir: Path,
        data_dir: Path | None = None,
        config: WorkerConfig | None = None,
    ) -> None:
        """Start the background worker"""
        if self._worker and self._worker.state == WorkerState.RUNNING:
            logger.warning("Worker already running")
            return

        self._worker = BackgroundWorker(
            notes_dir=notes_dir,
            data_dir=data_dir,
            config=config,
        )

        self._task = asyncio.create_task(self._worker.run())
        logger.info("Background worker started")

    async def stop(self) -> None:
        """Stop the background worker"""
        if self._worker:
            self._worker.stop()

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Worker did not stop gracefully, cancelling")
                self._task.cancel()

        self._worker = None
        self._task = None
        logger.info("Background worker stopped")

    def pause(self) -> None:
        """Pause the worker"""
        if self._worker:
            self._worker.pause()

    def resume(self) -> None:
        """Resume the worker"""
        if self._worker:
            self._worker.resume()

    def get_status(self) -> dict[str, Any]:
        """Get worker status"""
        if self._worker:
            return self._worker.get_status()
        return {"state": "not_started"}
