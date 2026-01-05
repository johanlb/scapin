"""Tests for note metadata module"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.passepartout.note_metadata import (
    EnrichmentRecord,
    NoteMetadata,
    NoteMetadataStore,
)
from src.passepartout.note_types import ImportanceLevel, NoteType


class TestEnrichmentRecord:
    """Tests for EnrichmentRecord dataclass"""

    def test_to_dict(self):
        """Should convert to dictionary correctly"""
        record = EnrichmentRecord(
            timestamp=datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc),
            action_type="add",
            target="Section A",
            content="New content",
            confidence=0.95,
            applied=True,
            reasoning="Test reason",
        )

        d = record.to_dict()
        assert d["action_type"] == "add"
        assert d["target"] == "Section A"
        assert d["confidence"] == 0.95
        assert d["applied"] is True

    def test_from_dict(self):
        """Should create from dictionary correctly"""
        data = {
            "timestamp": "2026-01-05T12:00:00+00:00",
            "action_type": "update",
            "target": "Title",
            "content": "Updated",
            "confidence": 0.8,
            "applied": False,
            "reasoning": "Needs review",
        }

        record = EnrichmentRecord.from_dict(data)
        assert record.action_type == "update"
        assert record.confidence == 0.8
        assert record.applied is False


class TestNoteMetadata:
    """Tests for NoteMetadata dataclass"""

    def test_default_values(self):
        """Should have sensible defaults"""
        metadata = NoteMetadata(note_id="test-001")
        assert metadata.note_type == NoteType.AUTRE
        assert metadata.easiness_factor == 2.5
        assert metadata.repetition_number == 0
        assert metadata.auto_enrich is True
        assert metadata.web_search_enabled is False

    def test_is_due_for_review_no_next_review(self):
        """Should be due if next_review is None"""
        metadata = NoteMetadata(note_id="test-001", next_review=None)
        assert metadata.is_due_for_review() is True

    def test_is_due_for_review_past(self):
        """Should be due if next_review is in the past"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        metadata = NoteMetadata(note_id="test-001", next_review=past)
        assert metadata.is_due_for_review() is True

    def test_is_due_for_review_future(self):
        """Should not be due if next_review is in the future"""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        metadata = NoteMetadata(note_id="test-001", next_review=future)
        assert metadata.is_due_for_review() is False

    def test_days_until_review(self):
        """Should calculate days correctly"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=3)
        metadata = NoteMetadata(note_id="test-001", next_review=future)

        days = metadata.days_until_review(now)
        assert 2.9 < days < 3.1  # Allow for small timing differences


class TestNoteMetadataStore:
    """Tests for NoteMetadataStore class"""

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

    def test_init_creates_database(self, temp_db):
        """Should create database file on init"""
        store = NoteMetadataStore(temp_db)
        assert temp_db.exists()
        # Check tables exist
        import sqlite3

        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='note_metadata'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_save_and_get(self, store):
        """Should save and retrieve metadata"""
        metadata = NoteMetadata(
            note_id="test-001",
            note_type=NoteType.PERSONNE,
            easiness_factor=2.3,
            importance=ImportanceLevel.HIGH,
        )

        store.save(metadata)
        retrieved = store.get("test-001")

        assert retrieved is not None
        assert retrieved.note_id == "test-001"
        assert retrieved.note_type == NoteType.PERSONNE
        assert retrieved.easiness_factor == 2.3
        assert retrieved.importance == ImportanceLevel.HIGH

    def test_get_nonexistent(self, store):
        """Should return None for nonexistent note"""
        assert store.get("nonexistent") is None

    def test_delete(self, store):
        """Should delete metadata"""
        metadata = NoteMetadata(note_id="test-001")
        store.save(metadata)

        assert store.delete("test-001") is True
        assert store.get("test-001") is None

    def test_delete_nonexistent(self, store):
        """Should return False when deleting nonexistent"""
        assert store.delete("nonexistent") is False

    def test_get_due_for_review(self, store):
        """Should return notes due for review"""
        # Create some test metadata
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(days=1)

        due = NoteMetadata(
            note_id="due-001",
            next_review=past,
            importance=ImportanceLevel.HIGH,
        )
        not_due = NoteMetadata(note_id="not-due-001", next_review=future)

        store.save(due)
        store.save(not_due)

        due_notes = store.get_due_for_review()
        assert len(due_notes) == 1
        assert due_notes[0].note_id == "due-001"

    def test_get_due_for_review_excludes_archived(self, store):
        """Should exclude archived notes"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        archived = NoteMetadata(
            note_id="archived-001",
            next_review=past,
            importance=ImportanceLevel.ARCHIVE,
        )
        store.save(archived)

        due_notes = store.get_due_for_review()
        assert len(due_notes) == 0

    def test_get_by_type(self, store):
        """Should filter by note type"""
        store.save(NoteMetadata(note_id="person-001", note_type=NoteType.PERSONNE))
        store.save(NoteMetadata(note_id="project-001", note_type=NoteType.PROJET))

        persons = store.get_by_type(NoteType.PERSONNE)
        assert len(persons) == 1
        assert persons[0].note_id == "person-001"

    def test_get_stats(self, store):
        """Should return correct statistics"""
        store.save(NoteMetadata(note_id="p1", note_type=NoteType.PERSONNE))
        store.save(NoteMetadata(note_id="p2", note_type=NoteType.PERSONNE))
        store.save(
            NoteMetadata(
                note_id="proj1",
                note_type=NoteType.PROJET,
                importance=ImportanceLevel.CRITICAL,
            )
        )

        stats = store.get_stats()
        assert stats["total"] == 3
        assert stats["by_type"]["personne"] == 2
        assert stats["by_type"]["projet"] == 1

    def test_create_for_note(self, store):
        """Should create metadata with correct defaults"""
        metadata = store.create_for_note(
            note_id="new-001",
            note_type=NoteType.PROJET,
            content="Test content",
        )

        assert metadata.note_id == "new-001"
        assert metadata.note_type == NoteType.PROJET
        assert metadata.content_hash != ""
        assert metadata.next_review is not None

    def test_update_content_hash(self, store):
        """Should update hash when content changes"""
        store.create_for_note(
            note_id="hash-test",
            note_type=NoteType.AUTRE,
            content="Original content",
        )

        changed = store.update_content_hash("hash-test", "New content")
        assert changed is True

        not_changed = store.update_content_hash("hash-test", "New content")
        assert not_changed is False

    def test_enrichment_history_persistence(self, store):
        """Should persist enrichment history"""
        record = EnrichmentRecord(
            timestamp=datetime.now(timezone.utc),
            action_type="add",
            target="Section",
            content="Content",
            confidence=0.9,
            applied=True,
        )

        metadata = NoteMetadata(
            note_id="history-test", enrichment_history=[record]
        )
        store.save(metadata)

        retrieved = store.get("history-test")
        assert len(retrieved.enrichment_history) == 1
        assert retrieved.enrichment_history[0].action_type == "add"
