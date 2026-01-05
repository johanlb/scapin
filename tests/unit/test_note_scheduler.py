"""Tests for note scheduler module"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler, SchedulingResult
from src.passepartout.note_types import NoteType


class TestSchedulingResult:
    """Tests for SchedulingResult dataclass"""

    def test_creation(self):
        """Should create result correctly"""
        result = SchedulingResult(
            next_review=datetime.now(timezone.utc),
            new_easiness_factor=2.3,
            new_interval_hours=24.0,
            new_repetition_number=3,
            quality_assessment="Good",
        )
        assert result.new_interval_hours == 24.0


class TestNoteScheduler:
    """Tests for NoteScheduler class"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def store(self, temp_db):
        """Create a store with temporary database"""
        return NoteMetadataStore(temp_db)

    @pytest.fixture
    def scheduler(self, store):
        """Create a scheduler"""
        return NoteScheduler(store)

    def test_calculate_next_review_quality_5(self, scheduler):
        """Quality 5 should give maximum interval growth"""
        metadata = NoteMetadata(
            note_id="test-001",
            easiness_factor=2.5,
            repetition_number=2,
            interval_hours=12.0,
        )

        result = scheduler.calculate_next_review(metadata, quality=5)

        # Quality 5 shouldn't decrease EF
        assert result.new_easiness_factor >= 2.5
        assert result.new_repetition_number == 3
        assert result.new_interval_hours > 12.0

    def test_calculate_next_review_quality_0(self, scheduler):
        """Quality 0 should reset to beginning"""
        metadata = NoteMetadata(
            note_id="test-001",
            note_type=NoteType.PERSONNE,  # Uses base_interval=2.0
            easiness_factor=2.5,
            repetition_number=5,
            interval_hours=100.0,
        )

        result = scheduler.calculate_next_review(metadata, quality=0)

        # Quality 0 resets repetition
        assert result.new_repetition_number == 0
        # Resets to type-specific base interval (PERSONNE = 2.0h)
        assert result.new_interval_hours == 2.0
        # EF should decrease
        assert result.new_easiness_factor < 2.5

    def test_calculate_next_review_quality_3_threshold(self, scheduler):
        """Quality 3 should be the pass threshold"""
        metadata = NoteMetadata(
            note_id="test-001",
            easiness_factor=2.5,
            repetition_number=3,
            interval_hours=24.0,
        )

        # Quality 3 passes
        result = scheduler.calculate_next_review(metadata, quality=3)
        assert result.new_repetition_number == 4

        # Quality 2 fails
        result = scheduler.calculate_next_review(metadata, quality=2)
        assert result.new_repetition_number == 0

    def test_calculate_next_review_invalid_quality(self, scheduler):
        """Should reject invalid quality values"""
        metadata = NoteMetadata(note_id="test-001")

        with pytest.raises(ValueError):
            scheduler.calculate_next_review(metadata, quality=-1)

        with pytest.raises(ValueError):
            scheduler.calculate_next_review(metadata, quality=6)

    def test_sm2_easiness_factor_bounds(self, scheduler):
        """EF should stay within bounds"""
        metadata = NoteMetadata(
            note_id="test-001",
            easiness_factor=1.3,  # Minimum
            repetition_number=1,
            interval_hours=2.0,
        )

        # Even with quality 0, EF shouldn't go below MIN
        result = scheduler.calculate_next_review(metadata, quality=0)
        assert result.new_easiness_factor >= NoteScheduler.MIN_EASINESS

        # With maximum EF and quality 5
        metadata.easiness_factor = 2.5
        result = scheduler.calculate_next_review(metadata, quality=5)
        assert result.new_easiness_factor <= NoteScheduler.MAX_EASINESS

    def test_first_interval(self, scheduler):
        """First interval should be type-specific base interval"""
        metadata = NoteMetadata(
            note_id="test-001",
            note_type=NoteType.PERSONNE,  # Uses base_interval=2.0
            repetition_number=0,
            interval_hours=0.0,
        )

        result = scheduler.calculate_next_review(metadata, quality=4)
        # PERSONNE type has base_interval_hours=2.0
        assert result.new_interval_hours == 2.0
        assert result.new_repetition_number == 1

    def test_second_interval(self, scheduler):
        """Second interval should be SECOND_INTERVAL"""
        metadata = NoteMetadata(
            note_id="test-001",
            repetition_number=1,
            interval_hours=2.0,
        )

        result = scheduler.calculate_next_review(metadata, quality=4)
        assert result.new_interval_hours == NoteScheduler.SECOND_INTERVAL_HOURS
        assert result.new_repetition_number == 2

    def test_skip_revision_type(self, scheduler):
        """Souvenir type should skip revision"""
        metadata = NoteMetadata(
            note_id="test-001",
            note_type=NoteType.SOUVENIR,
        )

        result = scheduler.calculate_next_review(metadata, quality=5)
        assert result.quality_assessment == "Type exempt from review"

    def test_record_review(self, scheduler, store):
        """Should record review and update metadata"""
        # Create initial metadata
        metadata = store.create_for_note(
            note_id="review-test",
            note_type=NoteType.PERSONNE,
            content="Test content",
        )

        # Record a review
        updated = scheduler.record_review("review-test", quality=4)

        assert updated is not None
        assert updated.review_count == 1
        assert updated.last_quality == 4
        assert updated.reviewed_at is not None
        assert updated.repetition_number == 1

    def test_record_review_nonexistent(self, scheduler):
        """Should return None for nonexistent note"""
        result = scheduler.record_review("nonexistent", quality=4)
        assert result is None

    def test_get_notes_due(self, scheduler, store):
        """Should return notes due for review"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(days=1)

        # Due note
        due = NoteMetadata(
            note_id="due-note",
            note_type=NoteType.PERSONNE,
            next_review=past,
        )
        store.save(due)

        # Not due
        not_due = NoteMetadata(
            note_id="not-due",
            note_type=NoteType.PERSONNE,
            next_review=future,
        )
        store.save(not_due)

        due_notes = scheduler.get_notes_due()
        assert len(due_notes) == 1
        assert due_notes[0].note_id == "due-note"

    def test_get_notes_due_excludes_skip_types(self, scheduler, store):
        """Should exclude types that skip revision"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        souvenir = NoteMetadata(
            note_id="souvenir",
            note_type=NoteType.SOUVENIR,
            next_review=past,
        )
        store.save(souvenir)

        due_notes = scheduler.get_notes_due()
        assert len(due_notes) == 0

    def test_trigger_immediate_review(self, scheduler, store):
        """Should set next_review to now"""
        future = datetime.now(timezone.utc) + timedelta(days=10)
        metadata = NoteMetadata(note_id="trigger-test", next_review=future)
        store.save(metadata)

        result = scheduler.trigger_immediate_review("trigger-test")
        assert result is True

        updated = store.get("trigger-test")
        assert updated.is_due_for_review() is True

    def test_postpone_review(self, scheduler, store):
        """Should postpone next_review"""
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(note_id="postpone-test", next_review=now)
        store.save(metadata)

        result = scheduler.postpone_review("postpone-test", hours=24)
        assert result is True

        updated = store.get("postpone-test")
        # Should be approximately 24 hours in the future
        delta = updated.next_review - now
        assert 23 < delta.total_seconds() / 3600 < 25

    def test_get_review_stats(self, scheduler, store):
        """Should return statistics"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        store.save(
            NoteMetadata(
                note_id="stat-test", note_type=NoteType.PROJET, next_review=past
            )
        )

        stats = scheduler.get_review_stats()
        assert "total" in stats
        assert "scheduling" in stats
        assert stats["scheduling"]["total_due"] >= 1

    def test_estimate_workload(self, scheduler, store):
        """Should estimate workload for upcoming days"""
        now = datetime.now(timezone.utc)

        # Create notes with different due dates
        for i in range(5):
            metadata = NoteMetadata(
                note_id=f"workload-{i}",
                next_review=now + timedelta(days=i),
            )
            store.save(metadata)

        workload = scheduler.estimate_workload(days=7)
        assert len(workload) == 7
        # First day should have at least 1 note
        first_day = list(workload.keys())[0]
        assert workload[first_day] >= 1
