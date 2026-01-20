"""
Tests for Apple Notes Sync — Protected Fields

Tests that Scapin-specific frontmatter fields are preserved during sync.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.integrations.apple.notes_models import AppleNote
from src.integrations.apple.notes_sync import AppleNotesSync


@pytest.fixture
def temp_notes_dir():
    """Create a temporary directory for notes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_apple_client():
    """Create a mock Apple Notes client."""
    client = MagicMock()
    client.get_folders.return_value = []
    client.get_notes_in_folder.return_value = []
    return client


@pytest.fixture
def sync_service(temp_notes_dir, mock_apple_client):
    """Create a sync service with mocked client."""
    return AppleNotesSync(temp_notes_dir, client=mock_apple_client)


@pytest.fixture
def sample_apple_note():
    """Create a sample Apple note for testing."""
    return AppleNote(
        id="apple-123",
        name="Test Note",
        folder="Notes",
        body_html="<p>Hello World</p>",
        body_text="Hello World",
        body_markdown="Hello World",
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        modified_at=datetime(2026, 1, 17, 14, 30, 0, tzinfo=timezone.utc),
    )


class TestProtectedFields:
    """Tests for protected Scapin fields during sync."""

    def test_protected_fields_constant_defined(self, sync_service):
        """Verify PROTECTED_SCAPIN_FIELDS constant exists and has expected fields."""
        assert hasattr(AppleNotesSync, "PROTECTED_SCAPIN_FIELDS")
        protected = AppleNotesSync.PROTECTED_SCAPIN_FIELDS

        # Check critical fields are protected
        assert "type" in protected
        assert "aliases" in protected
        assert "importance" in protected
        assert "pending_updates" in protected
        assert "linked_sources" in protected
        assert "relation" in protected  # Personne
        assert "stakeholders" in protected  # Projet
        assert "contacts" in protected  # Entité

    def test_apple_system_fields_constant_defined(self, sync_service):
        """Verify APPLE_SYSTEM_FIELDS constant exists."""
        assert hasattr(AppleNotesSync, "APPLE_SYSTEM_FIELDS")
        system = AppleNotesSync.APPLE_SYSTEM_FIELDS

        # Check Apple fields
        assert "title" in system
        assert "source" in system
        assert "apple_id" in system
        assert "synced" in system

    def test_no_overlap_between_protected_and_system(self):
        """Verify no field is both protected and system."""
        overlap = AppleNotesSync.PROTECTED_SCAPIN_FIELDS & AppleNotesSync.APPLE_SYSTEM_FIELDS
        assert len(overlap) == 0, f"Fields in both sets: {overlap}"


class TestFormatScapinNote:
    """Tests for _format_scapin_note method."""

    def test_new_note_has_apple_fields(self, sync_service, sample_apple_note):
        """New note should have Apple system fields."""
        result = sync_service._format_scapin_note(sample_apple_note)

        assert "title: Test Note" in result
        assert "source: apple_notes" in result
        assert "apple_id: apple-123" in result
        assert "apple_folder: Notes" in result

    def test_new_note_has_frontmatter_format(self, sync_service, sample_apple_note):
        """New note should have proper frontmatter format."""
        result = sync_service._format_scapin_note(sample_apple_note)

        assert result.startswith("---\n")
        assert "\n---\n\n" in result
        assert result.endswith("Hello World")

    def test_existing_note_preserves_scapin_fields(
        self, sync_service, sample_apple_note, temp_notes_dir
    ):
        """Existing Scapin fields should be preserved during update."""
        # Create existing note with Scapin fields
        existing_path = temp_notes_dir / "test_note.md"
        existing_content = """---
title: Old Title
source: apple_notes
apple_id: apple-123
type: personne
aliases:
  - Marc
  - Marcus
importance: haute
relation: collegue
organization: "[[Acme Corp]]"
pending_updates:
  - field: phone
    value: "+33612345678"
    source: email_signature
    confidence: 0.9
---

Old content
"""
        existing_path.write_text(existing_content)

        # Format note with Smart Merge
        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # Apple fields should be updated
        assert "title: Test Note" in result  # Updated by Apple
        assert "apple_id: apple-123" in result

        # Scapin fields should be PRESERVED
        assert "type: personne" in result
        assert "- Marc" in result
        assert "- Marcus" in result
        assert "importance: haute" in result
        assert "relation: collegue" in result
        assert "organization:" in result  # Key preserved
        assert "pending_updates:" in result

    def test_existing_note_updates_only_apple_fields(
        self, sync_service, sample_apple_note, temp_notes_dir
    ):
        """Only Apple system fields should be updated."""
        existing_path = temp_notes_dir / "test_note.md"
        existing_content = """---
title: Old Title
source: apple_notes
apple_id: apple-123
apple_folder: Old Folder
modified: "2026-01-01T00:00:00+00:00"
synced: "2026-01-01T00:00:00+00:00"
type: projet
status: actif
---

Content
"""
        existing_path.write_text(existing_content)

        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # Apple fields should be updated
        assert "title: Test Note" in result
        assert "apple_folder: Notes" in result
        # Note: modified is updated to Apple's new value
        assert "2026-01-17" in result  # New modified date

        # Scapin fields should NOT change
        assert "type: projet" in result
        assert "status: actif" in result

    def test_preserves_unknown_fields(self, sync_service, sample_apple_note, temp_notes_dir):
        """Unknown fields (not in either set) should be preserved."""
        existing_path = temp_notes_dir / "test_note.md"
        existing_content = """---
title: Old Title
source: apple_notes
apple_id: apple-123
custom_field: custom_value
another_field: 42
---

Content
"""
        existing_path.write_text(existing_content)

        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # Unknown fields should be preserved
        assert "custom_field: custom_value" in result
        assert "another_field: 42" in result

    def test_handles_malformed_frontmatter_gracefully(
        self, sync_service, sample_apple_note, temp_notes_dir
    ):
        """Malformed frontmatter should not crash, fall back to Apple fields."""
        existing_path = temp_notes_dir / "test_note.md"
        existing_content = """---
title: Old Title
this is not valid yaml: [
---

Content
"""
        existing_path.write_text(existing_content)

        # Should not raise, should fall back to Apple metadata
        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # Apple fields should be present
        assert "title: Test Note" in result
        assert "source: apple_notes" in result

    def test_handles_missing_file_gracefully(self, sync_service, sample_apple_note, temp_notes_dir):
        """Non-existent file should not crash."""
        non_existent = temp_notes_dir / "does_not_exist.md"

        result = sync_service._format_scapin_note(sample_apple_note, non_existent)

        # Should return valid note with Apple fields
        assert "title: Test Note" in result
        assert "source: apple_notes" in result


class TestProtectedFieldsComprehensive:
    """Comprehensive tests for all protected field categories."""

    def test_personne_fields_protected(self, sync_service, sample_apple_note, temp_notes_dir):
        """All Personne-specific fields should be protected."""
        existing_path = temp_notes_dir / "person.md"
        existing_content = """---
title: Marc Dupont
type: personne
first_name: Marc
last_name: Dupont
relation: collegue
relationship_strength: forte
organization: "[[Acme]]"
email: marc@example.com
phone: "+33612345678"
projects:
  - "[[Projet Alpha]]"
last_contact: "2026-01-15T10:00:00"
mention_count: 42
---

Notes about Marc
"""
        existing_path.write_text(existing_content)

        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # All Personne fields preserved
        assert "type: personne" in result
        assert "first_name: Marc" in result
        assert "last_name: Dupont" in result
        assert "relation: collegue" in result
        assert "relationship_strength: forte" in result
        assert "email: marc@example.com" in result
        assert "phone:" in result
        assert "projects:" in result
        assert "mention_count: 42" in result

    def test_projet_fields_protected(self, sync_service, sample_apple_note, temp_notes_dir):
        """All Projet-specific fields should be protected."""
        existing_path = temp_notes_dir / "project.md"
        existing_content = """---
title: Projet Alpha
type: projet
status: actif
priority: haute
domain: tech
start_date: "2026-01-01"
target_date: "2026-06-30"
stakeholders:
  - person: "[[Marc Dupont]]"
    role: lead
budget_range: "50-100k"
---

Project notes
"""
        existing_path.write_text(existing_content)

        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # All Projet fields preserved
        assert "type: projet" in result
        assert "status: actif" in result
        assert "priority: haute" in result
        assert "domain: tech" in result
        assert "stakeholders:" in result
        assert "budget_range:" in result

    def test_pending_updates_preserved(self, sync_service, sample_apple_note, temp_notes_dir):
        """pending_updates (AI suggestions queue) must be preserved."""
        existing_path = temp_notes_dir / "note.md"
        existing_content = """---
title: Test
pending_updates:
  - field: phone
    value: "+33612345678"
    source: email_signature
    source_ref: msg-123
    detected_at: "2026-01-15T10:00:00"
    confidence: 0.92
  - field: organization
    value: "[[New Corp]]"
    source: email_content
    confidence: 0.85
---

Content
"""
        existing_path.write_text(existing_content)

        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # pending_updates must be fully preserved
        assert "pending_updates:" in result
        assert "field: phone" in result
        assert "confidence: 0.92" in result
        assert "field: organization" in result

    def test_linked_sources_preserved(self, sync_service, sample_apple_note, temp_notes_dir):
        """linked_sources (background enrichment config) must be preserved."""
        existing_path = temp_notes_dir / "note.md"
        existing_content = """---
title: Test
linked_sources:
  - type: folder
    path: ~/Documents/Marc
    priority: 1
  - type: whatsapp
    contact: Marc Dupont
    priority: 2
---

Content
"""
        existing_path.write_text(existing_content)

        result = sync_service._format_scapin_note(sample_apple_note, existing_path)

        # linked_sources must be preserved
        assert "linked_sources:" in result
        assert "type: folder" in result
        assert "type: whatsapp" in result


class TestSyncDeletionBehavior:
    """Tests for sync deletion behavior with trash folder."""

    def test_excluded_folders_includes_trash(self, sync_service):
        """Verify _Supprimées is in excluded folders."""
        assert "_Supprimées" in AppleNotesSync.EXCLUDED_FOLDERS
        assert "Recently Deleted" in AppleNotesSync.EXCLUDED_FOLDERS

    def test_execute_delete_scapin_moves_to_trash(self, sync_service, temp_notes_dir):
        """Test that deleting Scapin note moves it to trash instead of hard delete."""
        from src.integrations.apple.notes_models import SyncDirection, SyncResult
        from src.passepartout.note_manager import TRASH_FOLDER

        # Create a note file
        note_path = temp_notes_dir / "test-note.md"
        note_path.write_text("""---
title: Test Note
---

Content
""")

        # Execute delete
        result = SyncResult(success=True, direction=SyncDirection.BIDIRECTIONAL)
        sync_service._execute_delete(
            "test-note",
            {"scapin_path": note_path, "direction": "delete_scapin"},
            result,
        )

        # Verify file moved to trash, not deleted
        assert not note_path.exists()
        trash_path = temp_notes_dir / TRASH_FOLDER / "test-note.md"
        assert trash_path.exists()
        assert "test-note" in result.deleted

    def test_execute_delete_apple_calls_client(self, sync_service, sample_apple_note):
        """Test that deleting Apple note calls the client delete method."""
        from src.integrations.apple.notes_models import SyncDirection, SyncResult

        # Execute delete
        result = SyncResult(success=True, direction=SyncDirection.BIDIRECTIONAL)
        sync_service.client.delete_note.return_value = True

        sync_service._execute_delete(
            "apple-123",
            {"apple_note": sample_apple_note, "direction": "delete_apple"},
            result,
        )

        # Verify client method was called
        sync_service.client.delete_note.assert_called_once_with("apple-123")
        assert "Test Note" in result.deleted

    def test_scapin_trash_notes_excluded_from_sync(self, sync_service, temp_notes_dir):
        """Test that notes in Scapin's trash folder are excluded from sync."""
        from src.passepartout.note_manager import TRASH_FOLDER

        # Create trash folder with a note
        trash_dir = temp_notes_dir / TRASH_FOLDER
        trash_dir.mkdir()
        (trash_dir / "deleted-note.md").write_text("""---
title: Deleted Note
---

Content
""")

        # Also create a normal note
        (temp_notes_dir / "normal-note.md").write_text("""---
title: Normal Note
---

Content
""")

        # Get Scapin notes
        scapin_notes = sync_service._get_scapin_notes()

        # Verify trash note is excluded
        paths = list(scapin_notes.keys())
        assert any("normal-note" in p for p in paths)
        # The excluded folders check uses folder.name, not full path
        # So notes directly inside notes_dir with "_Supprimées" as subfolder should be excluded
        for p in paths:
            assert TRASH_FOLDER not in p, f"Trash note found in sync: {p}"
