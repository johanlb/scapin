"""
Notes Review Service

Async wrapper around NoteScheduler for API use.
Provides SM-2 spaced repetition review functionality.
"""

from dataclasses import dataclass, field
from pathlib import Path

from src.core.config_manager import ScapinConfig
from src.jeeves.api.models.notes import (
    NoteMetadataResponse,
    NotesDueResponse,
    PostponeReviewResponse,
    RecordReviewResponse,
    ReviewConfigResponse,
    ReviewStatsResponse,
    ReviewWorkloadResponse,
    TriggerReviewResponse,
)
from src.monitoring.logger import get_logger
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import NOTE_TYPE_CONFIGS, NoteType

logger = get_logger("jeeves.api.services.notes_review")


def _metadata_to_response(metadata: NoteMetadata) -> NoteMetadataResponse:
    """Convert NoteMetadata to API response"""
    return NoteMetadataResponse(
        note_id=metadata.note_id,
        note_type=metadata.note_type.value,
        easiness_factor=metadata.easiness_factor,
        repetition_number=metadata.repetition_number,
        interval_hours=metadata.interval_hours,
        next_review=metadata.next_review,
        last_quality=metadata.last_quality,
        review_count=metadata.review_count,
        auto_enrich=metadata.auto_enrich,
        importance=metadata.importance.value,
    )


@dataclass
class NotesReviewService:
    """
    Review service for note scheduling API endpoints

    Wraps NoteScheduler with API-specific logic.
    """

    config: ScapinConfig
    _metadata_store: NoteMetadataStore | None = field(default=None, init=False)
    _scheduler: NoteScheduler | None = field(default=None, init=False)

    def _get_store(self) -> NoteMetadataStore:
        """Get or create NoteMetadataStore instance"""
        if self._metadata_store is None:
            # Use database directory for notes metadata
            data_dir = self.config.storage.database_path.parent
            db_path = data_dir / "notes_meta.db"
            self._metadata_store = NoteMetadataStore(db_path)
        return self._metadata_store

    def _get_scheduler(self) -> NoteScheduler:
        """Get or create NoteScheduler instance"""
        if self._scheduler is None:
            store = self._get_store()
            self._scheduler = NoteScheduler(store)
        return self._scheduler

    async def get_notes_due(
        self,
        limit: int = 50,
        note_type: str | None = None,
    ) -> NotesDueResponse:
        """
        Get notes due for review

        Args:
            limit: Maximum notes to return
            note_type: Filter by note type (optional)

        Returns:
            NotesDueResponse with notes due
        """
        logger.info(f"Getting notes due for review (limit={limit}, type={note_type})")
        scheduler = self._get_scheduler()

        # Convert type filter if provided
        note_types = None
        if note_type:
            try:
                note_types = [NoteType(note_type)]
            except ValueError:
                logger.warning(f"Invalid note type filter: {note_type}")
                return NotesDueResponse(notes=[], total=0)

        due_notes = scheduler.get_notes_due(limit=limit, note_types=note_types)

        return NotesDueResponse(
            notes=[_metadata_to_response(m) for m in due_notes],
            total=len(due_notes),
        )

    async def get_note_metadata(self, note_id: str) -> NoteMetadataResponse | None:
        """
        Get metadata for a specific note

        Args:
            note_id: Note identifier

        Returns:
            NoteMetadataResponse or None if not found
        """
        store = self._get_store()
        metadata = store.get(note_id)
        if metadata is None:
            return None
        return _metadata_to_response(metadata)

    async def record_review(
        self,
        note_id: str,
        quality: int,
    ) -> RecordReviewResponse | None:
        """
        Record a review and update scheduling

        Args:
            note_id: Note identifier
            quality: Review quality (0-5)

        Returns:
            RecordReviewResponse or None if note not found
        """
        logger.info(f"Recording review for {note_id} with quality {quality}")
        scheduler = self._get_scheduler()
        store = self._get_store()

        # Get current metadata
        metadata = store.get(note_id)
        if metadata is None:
            logger.warning(f"Note not found for review: {note_id}")
            return None

        # Calculate new scheduling
        result = scheduler.calculate_next_review(metadata, quality)

        # Record the review
        updated = scheduler.record_review(note_id, quality)
        if updated is None:
            return None

        return RecordReviewResponse(
            note_id=note_id,
            quality=quality,
            new_easiness_factor=result.new_easiness_factor,
            new_interval_hours=result.new_interval_hours,
            new_repetition_number=result.new_repetition_number,
            next_review=result.next_review,
            quality_assessment=result.quality_assessment,
        )

    async def postpone_review(
        self,
        note_id: str,
        hours: float,
    ) -> PostponeReviewResponse | None:
        """
        Postpone a note's review

        Args:
            note_id: Note identifier
            hours: Hours to postpone

        Returns:
            PostponeReviewResponse or None if note not found
        """
        logger.info(f"Postponing review for {note_id} by {hours}h")
        scheduler = self._get_scheduler()
        store = self._get_store()

        success = scheduler.postpone_review(note_id, hours)
        if not success:
            return None

        # Get updated metadata
        metadata = store.get(note_id)
        if metadata is None or metadata.next_review is None:
            return None

        return PostponeReviewResponse(
            note_id=note_id,
            hours_postponed=hours,
            new_next_review=metadata.next_review,
        )

    async def trigger_immediate_review(
        self,
        note_id: str,
    ) -> TriggerReviewResponse | None:
        """
        Trigger immediate review for a note

        Args:
            note_id: Note identifier

        Returns:
            TriggerReviewResponse or None if note not found
        """
        logger.info(f"Triggering immediate review for {note_id}")
        scheduler = self._get_scheduler()
        store = self._get_store()

        success = scheduler.trigger_immediate_review(note_id)
        if not success:
            return None

        # Get updated metadata
        metadata = store.get(note_id)
        if metadata is None or metadata.next_review is None:
            return None

        return TriggerReviewResponse(
            note_id=note_id,
            triggered=True,
            next_review=metadata.next_review,
        )

    async def get_review_stats(self) -> ReviewStatsResponse:
        """
        Get review statistics

        Returns:
            ReviewStatsResponse with scheduling statistics
        """
        logger.info("Getting review stats")
        scheduler = self._get_scheduler()

        stats = scheduler.get_review_stats()

        # Calculate average easiness factor
        all_notes = self._get_store().list_all(limit=10000)
        avg_ef = sum(m.easiness_factor for m in all_notes) / len(all_notes) if all_notes else 2.5

        return ReviewStatsResponse(
            total_notes=stats["total"],
            by_type=stats.get("by_type", {}),
            by_importance=stats.get("by_importance", {}),
            total_due=stats.get("scheduling", {}).get("total_due", 0),
            reviewed_today=stats.get("scheduling", {}).get("today_completed", 0),
            avg_easiness_factor=round(avg_ef, 2),
        )

    async def estimate_workload(self, days: int = 7) -> ReviewWorkloadResponse:
        """
        Estimate review workload for upcoming days

        Args:
            days: Number of days to forecast

        Returns:
            ReviewWorkloadResponse with daily counts
        """
        logger.info(f"Estimating workload for {days} days")
        scheduler = self._get_scheduler()

        workload = scheduler.estimate_workload(days=days)
        total = sum(workload.values())

        return ReviewWorkloadResponse(
            workload=workload,
            total_upcoming=total,
        )

    async def get_review_configs(self) -> list[ReviewConfigResponse]:
        """
        Get review configuration for all note types

        Returns:
            List of ReviewConfigResponse for each type
        """
        configs = []
        for note_type, config in NOTE_TYPE_CONFIGS.items():
            configs.append(
                ReviewConfigResponse(
                    note_type=note_type.value,
                    base_interval_hours=config.base_interval_hours,
                    max_interval_days=config.max_interval_days,
                    easiness_factor=config.easiness_factor,
                    auto_enrich=config.auto_enrich,
                    skip_revision=config.skip_revision,
                )
            )
        return configs

    async def ensure_metadata_exists(
        self,
        note_id: str,
        note_type: str = "autre",
        content: str = "",
    ) -> NoteMetadataResponse:
        """
        Ensure metadata exists for a note, creating if needed

        Args:
            note_id: Note identifier
            note_type: Note type (default: "autre")
            content: Note content for hash calculation

        Returns:
            NoteMetadataResponse for the note
        """
        store = self._get_store()
        metadata = store.get(note_id)

        if metadata is None:
            try:
                note_type_enum = NoteType(note_type)
            except ValueError:
                note_type_enum = NoteType.AUTRE

            metadata = store.create_for_note(
                note_id=note_id,
                note_type=note_type_enum,
                content=content,
            )
            logger.info(f"Created metadata for note {note_id}")

        return _metadata_to_response(metadata)
