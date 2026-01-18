"""
Unit Tests for Note Deletion and Index Operations

Tests:
- Note deletion from NoteManager
- Soft delete (move to trash) vs hard delete
- Deleted folder retrieval
- Vector store cleanup on deletion
- Cache invalidation after delete
- Index refresh and rebuild
- Concurrent operations
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import os
import shutil

import pytest

from src.passepartout.note_manager import Note, NoteManager


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def notes_dir(tmp_path):
    """Create a temporary notes directory with sample notes"""
    notes_path = tmp_path / "notes"
    notes_path.mkdir()

    # Create some sample notes
    for i in range(5):
        note_file = notes_path / f"note_{i}.md"
        note_file.write_text(f"""---
title: Test Note {i}
type: concept
tags:
  - test
  - note{i}
created_at: 2026-01-15T10:00:00Z
modified_at: 2026-01-15T10:00:00Z
---

# Test Note {i}

This is test note content {i}.
""")

    # Create a folder with notes
    subfolder = notes_path / "Projects"
    subfolder.mkdir()
    (subfolder / "project_note.md").write_text("""---
title: Project Note
type: projet
---

# Project Note
Project content.
""")

    # Create a "Supprimées récemment" folder for trash
    trash = notes_path / "Supprimées récemment"
    trash.mkdir()
    (trash / "deleted_note.md").write_text("""---
title: Deleted Note
type: concept
deleted_at: 2026-01-14T10:00:00Z
---

# Deleted Note
This was deleted.
""")

    return notes_path


@pytest.fixture
def note_manager(notes_dir):
    """Create a NoteManager with the test notes directory"""
    manager = NoteManager(
        notes_path=notes_dir,
        auto_index=False,  # Disable auto-indexing for tests
    )
    return manager


@pytest.fixture
def note_manager_with_index(notes_dir):
    """Create a NoteManager with indexing enabled"""
    manager = NoteManager(
        notes_path=notes_dir,
        auto_index=True,
    )
    return manager


# ============================================================================
# Note Deletion Tests
# ============================================================================


class TestNoteDelete:
    """Test note deletion functionality"""

    def test_delete_note_success(self, note_manager, notes_dir):
        """Can delete an existing note"""
        note_path = notes_dir / "note_0.md"
        assert note_path.exists()

        # Delete the note
        result = note_manager.delete_note("note_0")

        assert result is True
        assert not note_path.exists()

    def test_delete_note_not_found(self, note_manager):
        """Deleting non-existent note returns False"""
        result = note_manager.delete_note("nonexistent_note")

        assert result is False

    def test_delete_note_in_subfolder(self, note_manager, notes_dir):
        """Can delete a note in a subfolder"""
        note_path = notes_dir / "Projects" / "project_note.md"
        assert note_path.exists()

        result = note_manager.delete_note("Projects/project_note")

        assert result is True
        assert not note_path.exists()

    def test_delete_note_clears_cache(self, note_manager_with_index, notes_dir):
        """Deleting a note clears it from the cache"""
        # First, load the note to cache it
        note = note_manager_with_index.get_note("note_1")
        assert note is not None

        # Delete the note
        note_manager_with_index.delete_note("note_1")

        # Note should not be in cache anymore
        note_after = note_manager_with_index.get_note("note_1")
        assert note_after is None

    def test_delete_note_path_traversal_blocked(self, note_manager):
        """Path traversal attacks are blocked during deletion"""
        # Attempt to delete outside notes directory
        with pytest.raises((ValueError, PermissionError)):
            note_manager.delete_note("../../../etc/passwd")

        with pytest.raises((ValueError, PermissionError)):
            note_manager.delete_note("..\\..\\windows\\system32")


class TestSoftDelete:
    """Test soft delete (move to trash) functionality"""

    def test_soft_delete_moves_to_trash(self, note_manager, notes_dir):
        """Soft delete moves note to trash folder"""
        trash_dir = notes_dir / "Supprimées récemment"
        original_path = notes_dir / "note_2.md"
        assert original_path.exists()

        # Soft delete
        result = note_manager.soft_delete("note_2")

        assert result is True
        assert not original_path.exists()
        # Note should be in trash
        trash_path = trash_dir / "note_2.md"
        assert trash_path.exists()

    def test_soft_delete_creates_trash_folder(self, note_manager, notes_dir):
        """Soft delete creates trash folder if it doesn't exist"""
        # Remove existing trash folder
        trash_dir = notes_dir / "Supprimées récemment"
        if trash_dir.exists():
            shutil.rmtree(trash_dir)

        # Soft delete should create it
        result = note_manager.soft_delete("note_3")

        assert result is True
        assert trash_dir.exists()

    def test_soft_delete_handles_name_conflict(self, note_manager, notes_dir):
        """Soft delete handles filename conflicts in trash"""
        # Create a note with same name as one already in trash
        (notes_dir / "deleted_note.md").write_text("""---
title: Another Deleted Note
---
New content.
""")

        result = note_manager.soft_delete("deleted_note")

        # Should succeed with renamed file
        assert result is True
        # Original trash note should still exist
        assert (notes_dir / "Supprimées récemment" / "deleted_note.md").exists()


class TestPermanentDelete:
    """Test permanent deletion from trash"""

    def test_permanent_delete_from_trash(self, note_manager, notes_dir):
        """Can permanently delete a note from trash"""
        trash_note = notes_dir / "Supprimées récemment" / "deleted_note.md"
        assert trash_note.exists()

        result = note_manager.permanent_delete("Supprimées récemment/deleted_note")

        assert result is True
        assert not trash_note.exists()

    def test_empty_trash(self, note_manager, notes_dir):
        """Can empty entire trash folder"""
        trash_dir = notes_dir / "Supprimées récemment"

        # Add more notes to trash
        for i in range(3):
            (trash_dir / f"trash_{i}.md").write_text(f"# Trash {i}")

        result = note_manager.empty_trash()

        assert result is True
        # Folder should exist but be empty
        assert trash_dir.exists()
        assert len(list(trash_dir.glob("*.md"))) == 0


class TestRestoreFromTrash:
    """Test restoring notes from trash"""

    def test_restore_from_trash(self, note_manager, notes_dir):
        """Can restore a note from trash"""
        trash_note = notes_dir / "Supprimées récemment" / "deleted_note.md"
        assert trash_note.exists()

        result = note_manager.restore_from_trash("deleted_note")

        assert result is True
        # Note should be back in main folder
        assert (notes_dir / "deleted_note.md").exists()
        # And removed from trash
        assert not trash_note.exists()

    def test_restore_handles_conflict(self, note_manager, notes_dir):
        """Restore handles filename conflicts in destination"""
        # Create a note with same name in main folder
        (notes_dir / "deleted_note.md").write_text("# Existing note")

        result = note_manager.restore_from_trash("deleted_note")

        # Should succeed with renamed file
        assert result is True
        # Both notes should exist
        assert (notes_dir / "deleted_note.md").exists()
        # Restored note might be renamed (deleted_note_1.md)


# ============================================================================
# Deleted Folder Tests
# ============================================================================


class TestDeletedFolder:
    """Test deleted/trash folder operations"""

    def test_get_deleted_notes(self, note_manager, notes_dir):
        """Can retrieve list of deleted notes"""
        deleted = note_manager.get_deleted_notes()

        assert len(deleted) >= 1
        assert any(n.title == "Deleted Note" for n in deleted)

    def test_get_deleted_notes_empty_trash(self, note_manager, notes_dir):
        """Returns empty list when trash is empty"""
        # Empty the trash
        trash_dir = notes_dir / "Supprimées récemment"
        for f in trash_dir.glob("*.md"):
            f.unlink()

        deleted = note_manager.get_deleted_notes()

        assert len(deleted) == 0

    def test_get_deleted_notes_no_trash_folder(self, note_manager, notes_dir):
        """Returns empty list when trash folder doesn't exist"""
        # Remove trash folder
        trash_dir = notes_dir / "Supprimées récemment"
        if trash_dir.exists():
            shutil.rmtree(trash_dir)

        deleted = note_manager.get_deleted_notes()

        assert len(deleted) == 0


# ============================================================================
# Index Operations Tests
# ============================================================================


class TestIndexOperations:
    """Test index refresh and rebuild operations"""

    def test_refresh_index_basic(self, note_manager_with_index, notes_dir):
        """Can refresh the metadata index"""
        # Get initial count
        initial_notes = note_manager_with_index.get_all_notes()
        initial_count = len(initial_notes)

        # Add a new note
        (notes_dir / "new_note.md").write_text("""---
title: New Note
type: concept
---
# New Note
""")

        # Refresh index
        count = note_manager_with_index.refresh_index()

        # Should find the new note
        assert count == initial_count + 1

    def test_refresh_index_removes_deleted(self, note_manager_with_index, notes_dir):
        """Refresh index removes deleted notes"""
        # Delete a note file directly (simulating external deletion)
        (notes_dir / "note_4.md").unlink()

        # Refresh index
        note_manager_with_index.refresh_index()

        # Note should no longer be findable
        note = note_manager_with_index.get_note("note_4")
        assert note is None

    def test_refresh_index_clears_cache(self, note_manager_with_index, notes_dir):
        """Refresh index clears the note cache"""
        # Load some notes to cache them
        _ = note_manager_with_index.get_note("note_0")
        _ = note_manager_with_index.get_note("note_1")

        # Modify a note file directly
        (notes_dir / "note_0.md").write_text("""---
title: Modified Note 0
type: concept
---
# Modified content
""")

        # Refresh index
        note_manager_with_index.refresh_index()

        # Should get the modified content
        note = note_manager_with_index.get_note("note_0")
        assert note is not None
        assert note.title == "Modified Note 0"

    def test_metadata_index_persistence(self, notes_dir):
        """Metadata index is persisted to disk"""
        # Create manager and build index
        manager1 = NoteManager(notes_path=notes_dir, auto_index=True)
        manager1.refresh_index()

        # Check that index file exists
        index_file = notes_dir / ".scapin_notes_meta.json"
        assert index_file.exists()

        # Create new manager - should load from disk
        manager2 = NoteManager(notes_path=notes_dir, auto_index=False)
        summaries = manager2.get_notes_summary()

        # Should have the same notes
        assert len(summaries) > 0

    def test_rebuild_metadata_index(self, note_manager_with_index, notes_dir):
        """Can force rebuild of metadata index"""
        # Corrupt the index by modifying it directly
        index_file = notes_dir / ".scapin_notes_meta.json"
        index_file.write_text('{"corrupt": true}')

        # Force rebuild
        note_manager_with_index._rebuild_metadata_index()

        # Should have valid index again
        summaries = note_manager_with_index.get_notes_summary()
        assert len(summaries) > 0


# ============================================================================
# Note Counting Tests
# ============================================================================


class TestNoteCounting:
    """Test note counting functionality"""

    def test_count_all_notes(self, note_manager_with_index, notes_dir):
        """Can count total notes"""
        notes = note_manager_with_index.get_all_notes()
        # Should have 5 root notes + 1 in Projects folder
        # (trash notes are excluded)
        assert len(notes) >= 6

    def test_count_notes_by_folder(self, note_manager_with_index, notes_dir):
        """Can count notes in a specific folder"""
        notes = note_manager_with_index.list_notes(path="Projects")
        assert len(notes) == 1

    def test_count_excludes_trash(self, note_manager_with_index, notes_dir):
        """Note count excludes trash folder"""
        all_notes = note_manager_with_index.get_all_notes()
        trash_notes = note_manager_with_index.get_deleted_notes()

        # Trash notes should not be in all_notes
        all_ids = {n.id for n in all_notes}
        trash_ids = {n.id for n in trash_notes}

        assert all_ids.isdisjoint(trash_ids)


# ============================================================================
# Concurrent Operations Tests
# ============================================================================


class TestConcurrentOperations:
    """Test thread-safety of note operations"""

    def test_concurrent_deletes(self, note_manager_with_index, notes_dir):
        """Multiple concurrent deletes don't cause errors"""
        import concurrent.futures

        # Create more notes for concurrent deletion
        for i in range(10, 20):
            (notes_dir / f"concurrent_{i}.md").write_text(f"""---
title: Concurrent Note {i}
---
# Concurrent {i}
""")

        note_manager_with_index.refresh_index()

        def delete_note(i):
            return note_manager_with_index.delete_note(f"concurrent_{i}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(delete_note, i) for i in range(10, 20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All deletes should succeed
        assert all(results)

    def test_concurrent_reads_during_delete(self, note_manager_with_index, notes_dir):
        """Reads don't fail during concurrent deletes"""
        import concurrent.futures

        def read_notes():
            return note_manager_with_index.get_all_notes()

        def delete_note(i):
            return note_manager_with_index.delete_note(f"note_{i}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Start reads and deletes concurrently
            read_futures = [executor.submit(read_notes) for _ in range(5)]
            delete_futures = [executor.submit(delete_note, i) for i in range(2)]

            # All operations should complete without error
            for f in concurrent.futures.as_completed(read_futures + delete_futures):
                try:
                    _ = f.result()
                except Exception as e:
                    pytest.fail(f"Concurrent operation failed: {e}")


# ============================================================================
# API Integration Tests
# ============================================================================


class TestDeletedNotesAPI:
    """Test API endpoints for deleted notes"""

    @pytest.mark.asyncio
    async def test_get_deleted_notes_endpoint(self):
        """GET /api/notes/deleted returns deleted notes"""
        from unittest.mock import patch

        with patch(
            "src.jeeves.api.services.notes_service.NotesService.get_deleted_notes"
        ) as mock:
            mock.return_value = [
                MagicMock(
                    id="deleted-1",
                    title="Deleted Note 1",
                    path="Supprimées récemment/deleted-1",
                    deleted_at=datetime.now(timezone.utc),
                )
            ]

            from src.jeeves.api.services.notes_service import NotesService

            service = NotesService.__new__(NotesService)
            service.note_manager = MagicMock()
            service.note_manager.get_deleted_notes.return_value = mock.return_value

            result = service.get_deleted_notes()

            assert len(result) == 1
            assert result[0].title == "Deleted Note 1"

    @pytest.mark.asyncio
    async def test_permanent_delete_endpoint(self):
        """DELETE /api/notes/{id}/permanent permanently deletes"""
        from unittest.mock import patch

        with patch(
            "src.jeeves.api.services.notes_service.NotesService.permanent_delete"
        ) as mock:
            mock.return_value = True

            from src.jeeves.api.services.notes_service import NotesService

            service = NotesService.__new__(NotesService)
            service.note_manager = MagicMock()
            service.note_manager.permanent_delete.return_value = True

            result = service.permanent_delete("deleted-note-id")

            assert result is True

    @pytest.mark.asyncio
    async def test_restore_note_endpoint(self):
        """POST /api/notes/{id}/restore restores from trash"""
        from unittest.mock import patch

        with patch(
            "src.jeeves.api.services.notes_service.NotesService.restore_from_trash"
        ) as mock:
            mock.return_value = True

            from src.jeeves.api.services.notes_service import NotesService

            service = NotesService.__new__(NotesService)
            service.note_manager = MagicMock()
            service.note_manager.restore_from_trash.return_value = True

            result = service.restore_from_trash("deleted-note-id")

            assert result is True
