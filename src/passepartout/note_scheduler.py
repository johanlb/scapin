"""
Note Scheduler with SM-2 Algorithm

Implements SuperMemo SM-2 spaced repetition algorithm adapted for note review.
Manages scheduling of note reviews with adaptive intervals.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.monitoring.logger import get_logger
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_types import (
    NoteType,
    get_review_config,
)

logger = get_logger("passepartout.note_scheduler")


@dataclass
class SchedulingResult:
    """Result of scheduling calculation"""

    next_review: datetime
    new_easiness_factor: float
    new_interval_hours: float
    new_repetition_number: int
    quality_assessment: str  # Human-readable assessment


class NoteScheduler:
    """
    SM-2 based note review scheduler

    The SM-2 algorithm calculates review intervals based on:
    - Easiness Factor (EF): How easy the note is to maintain (1.3-2.5)
    - Repetition Number: Consecutive successful reviews
    - Quality: Rating of the last review (0-5)

    Quality Scale for Notes:
        5 - No changes needed, content is perfect
        4 - Minor formatting or typo fixes only
        3 - Small content additions or clarifications
        2 - Moderate updates required
        1 - Significant restructuring needed
        0 - Major overhaul or content is obsolete

    Interval Progression:
        - I(1) = BASE_INTERVAL_HOURS (default: 2h)
        - I(2) = SECOND_INTERVAL_HOURS (default: 12h)
        - I(n) = I(n-1) * EF for n > 2
    """

    # SM-2 Constants
    BASE_INTERVAL_HOURS = 2.0
    SECOND_INTERVAL_HOURS = 12.0
    MIN_EASINESS = 1.3
    MAX_EASINESS = 2.5
    DEFAULT_EASINESS = 2.5

    # Quality thresholds
    QUALITY_PASS_THRESHOLD = 3  # Quality >= 3 is a "pass"

    def __init__(self, metadata_store: NoteMetadataStore):
        """
        Initialize scheduler

        Args:
            metadata_store: Store for note metadata
        """
        self.store = metadata_store

    def calculate_next_review(
        self,
        metadata: NoteMetadata,
        quality: int,
    ) -> SchedulingResult:
        """
        Calculate next review date using SM-2 algorithm

        Args:
            metadata: Current note metadata
            quality: Review quality rating (0-5)

        Returns:
            SchedulingResult with new scheduling parameters

        Raises:
            ValueError: If quality is not in range 0-5
        """
        if not 0 <= quality <= 5:
            raise ValueError(f"Quality must be 0-5, got {quality}")

        # Get type-specific configuration
        config = get_review_config(metadata.note_type)
        if config.skip_revision:
            # This type should never be scheduled
            return SchedulingResult(
                next_review=datetime.max.replace(tzinfo=timezone.utc),
                new_easiness_factor=metadata.easiness_factor,
                new_interval_hours=0.0,
                new_repetition_number=metadata.repetition_number,
                quality_assessment="Type exempt from review",
            )

        # Current values
        ef = metadata.easiness_factor
        repetition = metadata.repetition_number

        # SM-2 Easiness Factor update formula
        # EF' = EF + (0.1 - (5 - Q) * (0.08 + (5 - Q) * 0.02))
        ef_delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        new_ef = max(self.MIN_EASINESS, min(self.MAX_EASINESS, ef + ef_delta))

        # Calculate new interval
        if quality < self.QUALITY_PASS_THRESHOLD:
            # Failed review - reset to beginning
            new_interval = config.base_interval_hours
            new_repetition = 0
            assessment = self._get_quality_assessment(quality, reset=True)
        else:
            # Successful review - progress interval
            new_repetition = repetition + 1

            if new_repetition == 1:
                new_interval = config.base_interval_hours
            elif new_repetition == 2:
                new_interval = self.SECOND_INTERVAL_HOURS
            else:
                new_interval = metadata.interval_hours * new_ef

            # Apply max interval cap
            max_interval_hours = config.max_interval_days * 24
            new_interval = min(new_interval, max_interval_hours)

            assessment = self._get_quality_assessment(quality, reset=False)

        # Calculate next review datetime
        now = datetime.now(timezone.utc)
        next_review = now + timedelta(hours=new_interval)

        logger.debug(
            f"Scheduled note {metadata.note_id}: "
            f"quality={quality}, EF={ef:.2f}→{new_ef:.2f}, "
            f"interval={new_interval:.1f}h, next={next_review.isoformat()}"
        )

        return SchedulingResult(
            next_review=next_review,
            new_easiness_factor=new_ef,
            new_interval_hours=new_interval,
            new_repetition_number=new_repetition,
            quality_assessment=assessment,
        )

    def _get_quality_assessment(self, quality: int, reset: bool) -> str:
        """Generate human-readable quality assessment"""
        assessments = {
            5: "Parfait - aucune modification nécessaire",
            4: "Excellent - corrections mineures seulement",
            3: "Bon - petits ajouts ou clarifications",
            2: "Moyen - mises à jour modérées requises",
            1: "Faible - restructuration significative nécessaire",
            0: "Insuffisant - refonte majeure requise",
        }
        base = assessments.get(quality, "Inconnu")
        if reset:
            base += " (intervalle réinitialisé)"
        return base

    def record_review(
        self,
        note_id: str,
        quality: int,
    ) -> NoteMetadata | None:
        """
        Record a review and update scheduling

        Args:
            note_id: Note identifier
            quality: Review quality (0-5)

        Returns:
            Updated NoteMetadata or None if not found

        Raises:
            ValueError: If quality is not in range 0-5
        """
        # Validate quality bounds early with note context
        if not 0 <= quality <= 5:
            raise ValueError(
                f"Quality must be 0-5, got {quality} for note {note_id}"
            )

        metadata = self.store.get(note_id)
        if metadata is None:
            logger.warning(f"Cannot record review: note {note_id} not found")
            return None

        result = self.calculate_next_review(metadata, quality)

        # Update metadata
        metadata.reviewed_at = datetime.now(timezone.utc)
        metadata.next_review = result.next_review
        metadata.easiness_factor = result.new_easiness_factor
        metadata.interval_hours = result.new_interval_hours
        metadata.repetition_number = result.new_repetition_number
        metadata.last_quality = quality
        metadata.review_count += 1

        self.store.save(metadata)

        logger.info(
            f"Recorded review for {note_id}: Q={quality}, "
            f"next in {result.new_interval_hours:.1f}h"
        )

        return metadata

    def get_notes_due(
        self,
        limit: int = 50,
        note_types: list[NoteType] | None = None,
    ) -> list[NoteMetadata]:
        """
        Get notes due for review

        Args:
            limit: Maximum notes to return
            note_types: Filter by types (None = all reviewable types)

        Returns:
            List of notes due for review, ordered by priority
        """
        # Exclude types that skip revision
        if note_types is None:
            note_types = [
                t
                for t in NoteType
                if not get_review_config(t).skip_revision
            ]
        else:
            note_types = [
                t
                for t in note_types
                if not get_review_config(t).skip_revision
            ]

        return self.store.get_due_for_review(
            limit=limit,
            note_types=note_types,
        )

    def trigger_immediate_review(self, note_id: str) -> bool:
        """
        Force a note to be reviewed immediately

        Useful when external changes are detected.

        Args:
            note_id: Note identifier

        Returns:
            True if updated, False if note not found
        """
        metadata = self.store.get(note_id)
        if metadata is None:
            return False

        metadata.next_review = datetime.now(timezone.utc)
        self.store.save(metadata)

        logger.info(f"Triggered immediate review for {note_id}")
        return True

    def postpone_review(
        self,
        note_id: str,
        hours: float = 24.0,
    ) -> bool:
        """
        Postpone a note's review

        Args:
            note_id: Note identifier
            hours: Hours to postpone

        Returns:
            True if updated, False if note not found
        """
        metadata = self.store.get(note_id)
        if metadata is None:
            return False

        now = datetime.now(timezone.utc)
        current_next = metadata.next_review or now
        metadata.next_review = max(current_next, now) + timedelta(hours=hours)
        self.store.save(metadata)

        logger.info(f"Postponed review for {note_id} by {hours}h")
        return True

    def get_review_stats(self) -> dict:
        """
        Get scheduling statistics

        Returns:
            Dictionary with scheduling stats
        """
        stats = self.store.get_stats()

        # Add scheduling-specific stats
        due_notes = self.get_notes_due(limit=1000)

        stats["scheduling"] = {
            "total_due": len(due_notes),
            "today_completed": self.store.count_reviews_today(),
            "by_type_due": {},
        }

        # Count due by type
        for metadata in due_notes:
            type_name = metadata.note_type.value
            if type_name not in stats["scheduling"]["by_type_due"]:
                stats["scheduling"]["by_type_due"][type_name] = 0
            stats["scheduling"]["by_type_due"][type_name] += 1

        return stats

    def estimate_workload(self, days: int = 7) -> dict:
        """
        Estimate review workload for upcoming days

        Args:
            days: Number of days to forecast

        Returns:
            Dictionary with daily review counts
        """
        all_metadata = self.store.list_all(limit=10000)
        now = datetime.now(timezone.utc)

        workload = {}
        for day_offset in range(days):
            day_start = (now + timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)

            count = sum(
                1
                for m in all_metadata
                if m.next_review
                and day_start <= m.next_review < day_end
            )
            workload[day_start.strftime("%Y-%m-%d")] = count

        return workload


def create_scheduler(data_dir: Path | str = "data") -> NoteScheduler:
    """
    Create a scheduler with default configuration

    Args:
        data_dir: Directory for data storage

    Returns:
        Configured NoteScheduler instance
    """
    data_path = Path(data_dir)
    db_path = data_path / "notes_meta.db"

    store = NoteMetadataStore(db_path)
    return NoteScheduler(store)
