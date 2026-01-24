"""
Tests for last_synced_at field in NoteMetadata

Tests the new sync tracking field:
- Database migration v3 to v4
- Save and read of last_synced_at
- API response includes field
"""

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore


class TestLastSyncedAtField:
    """Tests for last_synced_at metadata field."""

    def test_metadata_has_last_synced_at_field(self) -> None:
        """NoteMetadata dataclass has last_synced_at field."""
        metadata = NoteMetadata(note_id="test-note")
        assert hasattr(metadata, "last_synced_at")
        assert metadata.last_synced_at is None  # Default value

    def test_save_and_read_last_synced_at(self) -> None:
        """Save and read last_synced_at value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_metadata.db"
            store = NoteMetadataStore(db_path)

            # Create metadata with last_synced_at
            now = datetime.now(timezone.utc)
            metadata = NoteMetadata(
                note_id="test-note-1",
                last_synced_at=now,
            )
            store.save(metadata)

            # Read it back
            loaded = store.get("test-note-1")
            assert loaded is not None
            assert loaded.last_synced_at is not None
            # Compare timestamps (allow 1 second tolerance for rounding)
            assert abs((loaded.last_synced_at - now).total_seconds()) < 1

    def test_save_without_last_synced_at(self) -> None:
        """Save note without last_synced_at (should be None)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_metadata.db"
            store = NoteMetadataStore(db_path)

            # Create metadata without last_synced_at
            metadata = NoteMetadata(note_id="test-note-2")
            store.save(metadata)

            # Read it back
            loaded = store.get("test-note-2")
            assert loaded is not None
            assert loaded.last_synced_at is None

    def test_update_last_synced_at(self) -> None:
        """Update last_synced_at on existing metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_metadata.db"
            store = NoteMetadataStore(db_path)

            # Create metadata without sync time
            metadata = NoteMetadata(note_id="test-note-3")
            store.save(metadata)

            # Update with sync time
            now = datetime.now(timezone.utc)
            loaded = store.get("test-note-3")
            assert loaded is not None
            loaded.last_synced_at = now
            store.save(loaded)

            # Read again and verify
            reloaded = store.get("test-note-3")
            assert reloaded is not None
            assert reloaded.last_synced_at is not None
            assert abs((reloaded.last_synced_at - now).total_seconds()) < 1

    def test_migration_v3_to_v4_adds_column(self) -> None:
        """Migration from v3 to v4 adds last_synced_at column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_metadata.db"

            # Create a v3 database manually
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE schema_version (version INTEGER)
            """
            )
            cursor.execute("INSERT INTO schema_version VALUES (3)")

            # Create table without last_synced_at (v3 schema)
            cursor.execute(
                """
                CREATE TABLE note_metadata (
                    note_id TEXT PRIMARY KEY,
                    note_type TEXT DEFAULT 'autre',
                    created_at TEXT,
                    updated_at TEXT,
                    reviewed_at TEXT,
                    next_review TEXT,
                    easiness_factor REAL DEFAULT 2.5,
                    repetition_number INTEGER DEFAULT 0,
                    interval_hours REAL DEFAULT 24,
                    review_count INTEGER DEFAULT 0,
                    last_quality INTEGER,
                    content_hash TEXT,
                    importance TEXT DEFAULT 'normal',
                    auto_enrich INTEGER DEFAULT 1,
                    web_search_enabled INTEGER DEFAULT 0,
                    enrichment_history TEXT DEFAULT '[]',
                    retouche_ef REAL DEFAULT 2.5,
                    retouche_rep INTEGER DEFAULT 0,
                    retouche_interval REAL DEFAULT 168,
                    retouche_next TEXT,
                    retouche_last TEXT,
                    retouche_count INTEGER DEFAULT 0,
                    lecture_ef REAL DEFAULT 2.5,
                    lecture_rep INTEGER DEFAULT 0,
                    lecture_interval REAL DEFAULT 72,
                    lecture_next TEXT,
                    lecture_last TEXT,
                    lecture_count INTEGER DEFAULT 0,
                    quality_score INTEGER,
                    questions_pending INTEGER DEFAULT 0,
                    questions_count INTEGER DEFAULT 0,
                    pending_actions TEXT DEFAULT '[]',
                    obsolete_flag INTEGER DEFAULT 0,
                    obsolete_reason TEXT,
                    merge_target_id TEXT
                )
            """
            )
            conn.commit()
            conn.close()

            # Open store - should trigger migration
            _ = NoteMetadataStore(db_path)

            # Verify column exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(note_metadata)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()

            assert "last_synced_at" in columns

            # Verify version updated
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version")
            version = cursor.fetchone()[0]
            conn.close()

            assert version == 4

    def test_batch_save_with_last_synced_at(self) -> None:
        """Batch save works with last_synced_at field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_metadata.db"
            store = NoteMetadataStore(db_path)

            now = datetime.now(timezone.utc)
            metadata_list = [
                NoteMetadata(note_id="batch-1", last_synced_at=now),
                NoteMetadata(note_id="batch-2", last_synced_at=None),
                NoteMetadata(note_id="batch-3", last_synced_at=now),
            ]

            saved = store.save_batch(metadata_list)
            assert saved == 3

            # Verify
            m1 = store.get("batch-1")
            m2 = store.get("batch-2")
            m3 = store.get("batch-3")

            assert m1 is not None and m1.last_synced_at is not None
            assert m2 is not None and m2.last_synced_at is None
            assert m3 is not None and m3.last_synced_at is not None
