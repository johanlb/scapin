"""
Background Worker for Note Review

24/7 background process that handles note reviews according to SM-2 scheduling.
Includes Memory Cycles v2: Retouche (AI) and Filage (briefing).
Designed to run without blocking the frontend or API.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from src.monitoring.logger import get_logger
from src.passepartout.janitor import NoteJanitor
from src.passepartout.note_manager import NoteManager
from src.passepartout.note_metadata import NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import CycleType

if TYPE_CHECKING:
    from src.passepartout.cross_source import CrossSourceEngine
    from src.passepartout.filage_service import Filage, FilageService
    from src.passepartout.retouche_reviewer import RetoucheResult, RetoucheReviewer
    from src.sancho.processor import NoteProcessor

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
    last_janitor_run: datetime | None = None
    janitor_repairs_total: int = 0
    last_index_refresh: datetime | None = None

    # Memory Cycles v2 stats
    retouches_today: int = 0
    retouches_total: int = 0
    last_retouche_at: datetime | None = None
    filage_prepared_today: bool = False
    last_filage_at: datetime | None = None


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
    ingestion_interval_seconds: float = 60.0  # Check for modified notes every minute
    janitor_interval_hours: float = 24.0  # Run janitor once per day
    index_refresh_interval_minutes: float = 30.0  # Refresh metadata index every 30 min

    # Throttling
    cpu_throttle_threshold: float = 80.0  # Pause if CPU > 80%
    pause_on_rate_limit: bool = True

    # Notifications
    notify_on_high_confidence: bool = True
    notify_threshold: float = 0.9

    # Memory Cycles v2
    max_daily_retouches: int = 100  # More retouches allowed (AI-driven)
    retouche_batch_size: int = 10  # Notes to retouche per cycle
    quiet_hours_start: int = 23  # No retouche after 23h
    quiet_hours_end: int = 7  # No retouche before 7h
    filage_hour: int = 6  # Prepare Filage at 6h
    filage_max_lectures: int = 20  # Max lectures in Filage


class BackgroundWorker:
    """
    Background worker for 24/7 note review and ingestion

    Constraints:
    - Max 50 reviews per day
    - Max 5 minutes per session
    - Throttling if system is under load
    - Pause on rate limiting

    Usage:
        worker = BackgroundWorker(notes_dir=Path("data/notes"))
        await worker.run()  # Runs continuously
    """

    def __init__(
        self,
        notes_dir: Path,
        data_dir: Path | None = None,
        config: WorkerConfig | None = None,
        cross_source_engine: CrossSourceEngine | None = None,
        on_review_complete: Callable[[RetoucheResult | None, None]] = None,
        on_state_change: Callable[[WorkerState | None, None]] = None,
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
        self._last_ingestion_check: float = 0

        # Components (lazy init)
        self._note_manager: NoteManager | None = None
        self._metadata_store: NoteMetadataStore | None = None
        self._scheduler: NoteScheduler | None = None
        # Note: _reviewer removed - using _retouche_reviewer for all reviews
        self._processor: NoteProcessor | None = None
        self._janitor: NoteJanitor | None = None

        # Memory Cycles v2 components
        self._retouche_reviewer: RetoucheReviewer | None = None
        self._filage_service: FilageService | None = None
        self._current_filage: Filage | None = None

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

        if self._processor is None:
            from src.sancho.processor import NoteProcessor

            self._processor = NoteProcessor(
                note_manager=self._note_manager,
            )

        # Memory Cycles v2 components (unified reviewer)
        if self._retouche_reviewer is None:
            from src.passepartout.retouche_reviewer import RetoucheReviewer

            self._retouche_reviewer = RetoucheReviewer(
                note_manager=self._note_manager,
                metadata_store=self._metadata_store,
                scheduler=self._scheduler,
                cross_source_engine=self._cross_source_engine,
            )

        if self._filage_service is None:
            from src.passepartout.filage_service import FilageService

            self._filage_service = FilageService(
                note_manager=self._note_manager,
                metadata_store=self._metadata_store,
                scheduler=self._scheduler,
                cross_source_engine=self._cross_source_engine,
            )

        # Notes hygiene
        if self._janitor is None:
            self._janitor = NoteJanitor(self.notes_dir)

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
            # Even if review limit reached, we might want to continue ingestion?
            # For now, pause applies to everything to respect "do not disturb" logic.
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
                # Memory Cycles v2
                self._stats.retouches_today = 0
                self._stats.filage_prepared_today = False

    async def run(self) -> None:
        """
        Main worker loop

        Runs continuously until stopped.
        """
        logger.info("Starting background worker")
        self._init_components()
        self._set_state(WorkerState.RUNNING)
        self._stop_requested = False

        # Initial ingestion check lookback (e.g., last 1 hour on startup)
        # This catches changes made while offline
        self._last_ingestion_check = time.time() - 3600

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

                # 1. Janitor / Hygiene check (daily)
                await self._check_janitor()

                # 1b. Index refresh (every 30 minutes)
                await self._check_index_refresh()

                # 2. Ingestion / Change Detection
                if (
                    time.time() - self._last_ingestion_check
                    > self.config.ingestion_interval_seconds
                ):
                    await self._check_ingestion()
                    self._last_ingestion_check = time.time()

                # 2. Memory Cycles v2: Filage (morning briefing)
                if self._is_filage_hour() and not self._stats.filage_prepared_today:
                    await self._prepare_filage()

                # 3. Memory Cycles v2: Retouche (AI improvement)
                if not self._is_quiet_hours() and self._remaining_retouches_today() > 0:
                    await self._run_retouche_cycle()

                # 4. Regular SM-2 Reviews
                # Get notes due for review
                assert self._scheduler is not None
                due_notes = self._scheduler.get_notes_due(limit=min(10, self._remaining_today()))

                if not due_notes:
                    self._set_state(WorkerState.IDLE)
                    # Use shorter sleep to remain responsive to ingestion needs
                    sleep_time = min(
                        self.config.sleep_when_idle_seconds, self.config.ingestion_interval_seconds
                    )

                    # Log only if sleeping long
                    if sleep_time > 10:
                        logger.debug(f"No notes due, sleeping {sleep_time}s")

                    await asyncio.sleep(sleep_time)
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

                    # Check for ingestion again if session is long?
                    # Usually session is 5 mins, so maybe not critical.

                    await self._process_note(metadata.note_id)
                    await asyncio.sleep(self.config.sleep_between_reviews_seconds)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                self._stats.errors_today += 1
                await asyncio.sleep(self.config.sleep_on_error_seconds)

    async def _check_janitor(self) -> None:
        """Run janitor if enough time has passed since last run"""
        if not self._janitor:
            return

        # Check if janitor should run
        now = datetime.now(timezone.utc)
        interval_seconds = self.config.janitor_interval_hours * 3600

        if self._stats.last_janitor_run:
            elapsed = (now - self._stats.last_janitor_run).total_seconds()
            if elapsed < interval_seconds:
                return  # Not time yet

        try:
            logger.info("Running janitor hygiene check...")
            stats = self._janitor.clean_directory(dry_run=False)

            self._stats.last_janitor_run = now
            self._stats.janitor_repairs_total += stats.get("repaired", 0)

            if stats["repaired"] > 0:
                logger.info(
                    f"Janitor completed: scanned={stats['scanned']}, "
                    f"repaired={stats['repaired']}, errors={stats['errors']}"
                )
            else:
                logger.debug(f"Janitor completed: all {stats['scanned']} notes valid")

        except Exception as e:
            logger.error(f"Janitor failed: {e}", exc_info=True)

    async def _check_index_refresh(self) -> None:
        """Refresh metadata index periodically (every 30 minutes by default)"""
        if not self._note_manager:
            return

        now = datetime.now(timezone.utc)
        interval_seconds = self.config.index_refresh_interval_minutes * 60

        if self._stats.last_index_refresh:
            elapsed = (now - self._stats.last_index_refresh).total_seconds()
            if elapsed < interval_seconds:
                return  # Not time yet

        try:
            logger.info("Running periodic metadata index refresh...")
            # Run in thread pool to avoid blocking
            count = await asyncio.to_thread(self._note_manager.refresh_index)
            self._stats.last_index_refresh = now
            logger.info(f"Index refresh completed: {count} notes indexed")

        except Exception as e:
            logger.error(f"Index refresh failed: {e}", exc_info=True)

    async def _check_ingestion(self) -> None:
        """Check for recently modified notes and trigger analysis"""
        if not self._note_manager:
            return

        try:
            # Look for notes modified since last check
            since = datetime.fromtimestamp(self._last_ingestion_check, tz=timezone.utc)
            modified_notes = self._note_manager.get_recently_modified_notes(since)

            if modified_notes:
                logger.info(
                    f"Detected {len(modified_notes)} modified notes",
                    extra={"notes": [n.title for n in modified_notes]},
                )

                for note in modified_notes:
                    # Trigger review/ingestion
                    # For now, we reuse review_note but this might change to ingest_note later
                    # Phase 1: Just log detection
                    logger.info(f"Ingesting modified note: {note.title} ({note.note_id})")

                    if self._processor:
                        await self._processor.process_note(note.note_id)

        except Exception as e:
            logger.error(f"Ingestion check failed: {e}", exc_info=True)

    # === Memory Cycles v2: Retouche & Filage ===

    def _is_quiet_hours(self) -> bool:
        """Check if we're in quiet hours (no Retouche)"""
        now = datetime.now(timezone.utc)
        # Simple UTC-based check (would use local timezone in production)
        local_hour = (now.hour + 1) % 24  # UTC+1 for Paris (simplified)
        return (
            local_hour >= self.config.quiet_hours_start
            or local_hour < self.config.quiet_hours_end
        )

    def _is_filage_hour(self) -> bool:
        """Check if it's time to prepare the Filage"""
        now = datetime.now(timezone.utc)
        local_hour = (now.hour + 1) % 24  # UTC+1 for Paris (simplified)
        return local_hour == self.config.filage_hour

    def _remaining_retouches_today(self) -> int:
        """Calculate remaining retouches for today"""
        return max(0, self.config.max_daily_retouches - self._stats.retouches_today)

    async def _run_retouche_cycle(self) -> None:
        """Run a Retouche cycle (AI improvement of notes)"""
        if self._retouche_reviewer is None or self._scheduler is None:
            return

        try:
            # Get notes due for Retouche
            batch_size = min(
                self.config.retouche_batch_size,
                self._remaining_retouches_today(),
            )
            due_notes = self._scheduler.get_notes_due(
                limit=batch_size,
                cycle_type=CycleType.RETOUCHE,
            )

            if not due_notes:
                return

            logger.info(f"Starting Retouche cycle with {len(due_notes)} notes")

            for metadata in due_notes:
                if self._stop_requested:
                    break

                try:
                    result = await self._retouche_reviewer.review_note(metadata.note_id)

                    # Update stats
                    self._stats.retouches_today += 1
                    self._stats.retouches_total += 1
                    self._stats.last_retouche_at = datetime.now(timezone.utc)

                    logger.info(
                        f"Retouche complete for {metadata.note_id}: "
                        f"quality={result.quality_before}→{result.quality_after}, "
                        f"actions={len(result.actions)}, model={result.model_used}"
                    )

                    # Small delay between retouches
                    await asyncio.sleep(2.0)

                except Exception as e:
                    logger.error(f"Retouche failed for {metadata.note_id}: {e}")
                    self._stats.errors_today += 1

        except Exception as e:
            logger.error(f"Retouche cycle failed: {e}", exc_info=True)

    async def _prepare_filage(self) -> None:
        """Prepare the daily Filage (morning briefing)"""
        if self._filage_service is None:
            return

        try:
            logger.info("Preparing daily Filage")

            filage = await self._filage_service.generate_filage(
                max_lectures=self.config.filage_max_lectures,
            )

            self._current_filage = filage
            self._stats.filage_prepared_today = True
            self._stats.last_filage_at = datetime.now(timezone.utc)

            logger.info(
                f"Filage prepared: {filage.total_lectures} lectures, "
                f"{filage.events_today} events, "
                f"{filage.notes_with_questions} with questions"
            )

            # TODO: Emit WebSocket event for Filage ready

        except Exception as e:
            logger.error(f"Filage preparation failed: {e}", exc_info=True)

    def get_current_filage(self) -> Filage | None:
        """Get the current day's Filage"""
        return self._current_filage

    # === End Memory Cycles v2 ===

    def _on_worker_stop(self) -> None:
        """Called when worker stops"""
        self._set_state(WorkerState.STOPPED)
        logger.info("Background worker stopped")

    async def _process_note(self, note_id: str) -> RetoucheResult | None:
        """Process a single note review using RetoucheReviewer"""
        logger.info(f"Processing note: {note_id}")
        start_time = time.time()

        try:
            assert self._retouche_reviewer is not None
            result = await self._retouche_reviewer.review_note(note_id)

            # Update stats
            elapsed = time.time() - start_time
            self._stats.reviews_today += 1
            self._stats.reviews_total += 1

            # Count applied vs pending actions
            applied = [a for a in result.actions if a.applied]
            pending = [a for a in result.actions if a.requires_confirmation]
            self._stats.actions_applied += len(applied)
            self._stats.actions_pending += len(pending)
            self._stats.last_review_at = datetime.now(timezone.utc)

            # Update average review time
            total = self._stats.reviews_total
            self._stats.average_review_seconds = (
                self._stats.average_review_seconds * (total - 1) + elapsed
            ) / total

            # Notify if callback registered
            if self.on_review_complete:
                self.on_review_complete(result)

            logger.info(
                f"Review complete for {note_id}: "
                f"Q={result.quality_after}, applied={len(applied)}, "
                f"pending={len(pending)}, time={elapsed:.2f}s"
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
                    self._stats.last_review_at.isoformat() if self._stats.last_review_at else None
                ),
                "average_review_seconds": round(self._stats.average_review_seconds, 2),
                # Memory Cycles v2
                "retouches_today": self._stats.retouches_today,
                "retouches_total": self._stats.retouches_total,
                "last_retouche_at": (
                    self._stats.last_retouche_at.isoformat()
                    if self._stats.last_retouche_at
                    else None
                ),
                "filage_prepared_today": self._stats.filage_prepared_today,
                "last_filage_at": (
                    self._stats.last_filage_at.isoformat() if self._stats.last_filage_at else None
                ),
                # Notes hygiene
                "last_janitor_run": (
                    self._stats.last_janitor_run.isoformat()
                    if self._stats.last_janitor_run
                    else None
                ),
                "janitor_repairs_total": self._stats.janitor_repairs_total,
                # Index refresh
                "last_index_refresh": (
                    self._stats.last_index_refresh.isoformat()
                    if self._stats.last_index_refresh
                    else None
                ),
            },
            "config": {
                "max_daily_reviews": self.config.max_daily_reviews,
                "max_session_minutes": self.config.max_session_minutes,
                "remaining_today": self._remaining_today(),
                # Memory Cycles v2
                "max_daily_retouches": self.config.max_daily_retouches,
                "remaining_retouches_today": self._remaining_retouches_today(),
                "quiet_hours": f"{self.config.quiet_hours_start}h-{self.config.quiet_hours_end}h",
                "filage_hour": self.config.filage_hour,
                # Notes hygiene
                "janitor_interval_hours": self.config.janitor_interval_hours,
                # Index refresh
                "index_refresh_interval_minutes": self.config.index_refresh_interval_minutes,
            },
            "memory_cycles": {
                "is_quiet_hours": self._is_quiet_hours(),
                "is_filage_hour": self._is_filage_hour(),
                "current_filage_lectures": (
                    self._current_filage.total_lectures if self._current_filage else 0
                ),
            },
        }


class BackgroundWorkerManager:
    """
    Manager for background worker process

    Handles starting, stopping, and monitoring the worker.
    """

    _instance: BackgroundWorkerManager | None = None
    _worker: BackgroundWorker | None = None
    _task: asyncio.Task | None = None

    @classmethod
    def get_instance(cls) -> BackgroundWorkerManager:
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
