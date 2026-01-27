"""Tests for Grimaud Executor."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.grimaud.executor import GrimaudExecutor
from src.grimaud.history import GrimaudHistoryManager
from src.grimaud.models import GrimaudAction, GrimaudActionType, GrimaudSnapshot


@pytest.fixture
def history_dir():
    """Cree un repertoire temporaire pour les snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def history_manager(history_dir):
    """Cree un HistoryManager avec repertoire temporaire."""
    return GrimaudHistoryManager(snapshots_dir=history_dir)


@pytest.fixture
def mock_note_manager():
    """Mock NoteManager."""
    manager = MagicMock()
    return manager


@pytest.fixture
def executor(mock_note_manager, history_manager):
    """Cree un Executor avec mocks."""
    return GrimaudExecutor(
        note_manager=mock_note_manager,
        history_manager=history_manager,
    )


class TestExecuteCreatesSnapshot:
    """Tests for snapshot creation before action."""

    def test_execute_creates_snapshot_before_action(
        self, executor, mock_note_manager, history_dir
    ):
        """execute cree un snapshot avant d'appliquer l'action."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-123"
        mock_note.title = "Ma Note"
        mock_note.content = "Contenu original"
        mock_note.metadata = {"title": "Ma Note", "tags": ["test"]}
        mock_note_manager.get_note.return_value = mock_note

        # Create action
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-123",
            note_title="Ma Note",
            confidence=0.90,
            reasoning="Section vide a completer",
            new_content="# Ma Note\n\nContenu enrichi",
        )

        # Execute
        result = executor.execute(action)

        # Verify snapshot was created
        assert result is True
        snapshots = list(history_dir.glob("*.json.gz"))
        assert len(snapshots) == 1

    def test_snapshot_contains_original_content(
        self, executor, mock_note_manager, history_manager
    ):
        """Le snapshot contient le contenu original de la note."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-456"
        mock_note.title = "Test Note"
        mock_note.content = "Contenu original a sauvegarder"
        mock_note.metadata = {"title": "Test Note"}
        mock_note_manager.get_note.return_value = mock_note

        # Create action
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-456",
            note_title="Test Note",
            confidence=0.85,
            new_content="Nouveau contenu",
        )

        # Execute
        executor.execute(action)

        # Get snapshot and verify content
        snapshots = history_manager.list_snapshots_for_note("note-456")
        assert len(snapshots) == 1
        assert snapshots[0].content_before == "Contenu original a sauvegarder"
        assert snapshots[0].note_id == "note-456"


class TestExecuteEnrichissement:
    """Tests for enrichissement action execution."""

    def test_execute_updates_note_content(self, executor, mock_note_manager):
        """execute met a jour le contenu de la note."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-abc"
        mock_note.title = "Note a enrichir"
        mock_note.content = "Contenu initial"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        # Create enrichissement action
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-abc",
            note_title="Note a enrichir",
            confidence=0.92,
            new_content="# Note a enrichir\n\nContenu enrichi avec details",
        )

        # Execute
        result = executor.execute(action)

        # Verify note was updated
        assert result is True
        mock_note_manager.update_note.assert_called_once_with(
            "note-abc",
            content="# Note a enrichir\n\nContenu enrichi avec details",
        )

    def test_execute_restructuration_updates_content(self, executor, mock_note_manager):
        """execute restructuration met a jour le contenu."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-xyz"
        mock_note.title = "Note a restructurer"
        mock_note.content = "Contenu desorganise"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        # Create restructuration action
        action = GrimaudAction(
            action_type=GrimaudActionType.RESTRUCTURATION,
            note_id="note-xyz",
            note_title="Note a restructurer",
            confidence=0.88,
            new_content="# Note a restructurer\n\n## Section 1\n\nOrganise",
        )

        # Execute
        result = executor.execute(action)

        # Verify note was updated
        assert result is True
        mock_note_manager.update_note.assert_called_once()


class TestExecuteMarksActionApplied:
    """Tests for marking action as applied."""

    def test_execute_marks_action_as_applied(self, executor, mock_note_manager):
        """execute marque l'action comme appliquee."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-mark"
        mock_note.title = "Test"
        mock_note.content = "Content"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        # Create action (not applied)
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-mark",
            note_title="Test",
            confidence=0.90,
            new_content="New content",
        )
        assert action.applied is False
        assert action.applied_at is None

        # Execute
        before_execute = datetime.now(timezone.utc)
        result = executor.execute(action)
        after_execute = datetime.now(timezone.utc)

        # Verify action is marked as applied
        assert result is True
        assert action.applied is True
        assert action.applied_at is not None
        assert before_execute <= action.applied_at <= after_execute


class TestExecuteFusion:
    """Tests for fusion action execution."""

    def test_execute_fusion_moves_source_to_trash(self, executor, mock_note_manager):
        """execute fusion deplace la note source vers la corbeille."""
        # Setup mock notes
        source_note = MagicMock()
        source_note.note_id = "note-source"
        source_note.title = "Note Source"
        source_note.content = "Contenu source a fusionner"
        source_note.metadata = {}

        target_note = MagicMock()
        target_note.note_id = "note-target"
        target_note.title = "Note Target"
        target_note.content = "Contenu target"
        target_note.metadata = {}

        # get_note returns source or target based on ID
        def get_note_side_effect(note_id):
            if note_id == "note-source":
                return source_note
            if note_id == "note-target":
                return target_note
            return None

        mock_note_manager.get_note.side_effect = get_note_side_effect

        # Create fusion action
        action = GrimaudAction(
            action_type=GrimaudActionType.FUSION,
            note_id="note-source",
            note_title="Note Source",
            target_note_id="note-target",
            target_note_title="Note Target",
            confidence=0.95,
            new_content="# Note Target\n\nContenu fusionne",
        )

        # Execute
        result = executor.execute(action)

        # Verify target was updated and source was deleted
        assert result is True
        mock_note_manager.update_note.assert_called_once_with(
            "note-target",
            content="# Note Target\n\nContenu fusionne",
        )
        mock_note_manager.delete_note.assert_called_once_with("note-source")


class TestExecuteLiaison:
    """Tests for liaison action execution."""

    def test_execute_liaison_adds_wikilink(self, executor, mock_note_manager):
        """execute liaison ajoute un wikilink dans la section Voir aussi."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-link"
        mock_note.title = "Note Principale"
        mock_note.content = "# Note Principale\n\nContenu de la note."
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        # Create liaison action
        action = GrimaudAction(
            action_type=GrimaudActionType.LIAISON,
            note_id="note-link",
            note_title="Note Principale",
            target_note_id="note-related",
            target_note_title="Note Reliee",
            confidence=0.88,
            reasoning="Ces notes traitent du meme sujet",
        )

        # Execute
        result = executor.execute(action)

        # Verify link was added
        assert result is True
        # Should have called update_note with content containing wikilink
        call_args = mock_note_manager.update_note.call_args
        assert call_args is not None
        content_arg = call_args[1].get("content") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("content")
        assert "[[Note Reliee]]" in content_arg
        assert "Voir aussi" in content_arg

    def test_execute_liaison_appends_to_existing_voir_aussi(
        self, executor, mock_note_manager
    ):
        """execute liaison ajoute a une section Voir aussi existante."""
        # Setup mock note with existing Voir aussi section
        mock_note = MagicMock()
        mock_note.note_id = "note-with-section"
        mock_note.title = "Note Avec Section"
        mock_note.content = """# Note Avec Section

Contenu de la note.

## Voir aussi

- [[Note Existante]]
"""
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        # Create liaison action
        action = GrimaudAction(
            action_type=GrimaudActionType.LIAISON,
            note_id="note-with-section",
            note_title="Note Avec Section",
            target_note_id="note-new-link",
            target_note_title="Nouvelle Note Liee",
            confidence=0.85,
        )

        # Execute
        result = executor.execute(action)

        # Verify both links are present
        assert result is True
        call_args = mock_note_manager.update_note.call_args
        content_arg = call_args[1].get("content")
        assert "[[Note Existante]]" in content_arg
        assert "[[Nouvelle Note Liee]]" in content_arg


class TestDryRun:
    """Tests for dry_run mode."""

    def test_dry_run_does_not_modify_anything(
        self, executor, mock_note_manager, history_dir
    ):
        """dry_run ne modifie rien."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-dry"
        mock_note.title = "Note Dry"
        mock_note.content = "Original content"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        # Create action
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-dry",
            note_title="Note Dry",
            confidence=0.90,
            new_content="New content",
        )

        # Execute with dry_run=True
        result = executor.execute(action, dry_run=True)

        # Verify nothing was modified
        assert result is True
        mock_note_manager.update_note.assert_not_called()
        mock_note_manager.delete_note.assert_not_called()
        # No snapshot created
        snapshots = list(history_dir.glob("*.json.gz"))
        assert len(snapshots) == 0
        # Action not marked as applied
        assert action.applied is False

    def test_dry_run_returns_true_for_valid_action(self, executor, mock_note_manager):
        """dry_run retourne True pour une action valide."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-valid"
        mock_note.title = "Valid Note"
        mock_note.content = "Content"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-valid",
            note_title="Valid Note",
            confidence=0.90,
            new_content="New content",
        )

        result = executor.execute(action, dry_run=True)

        assert result is True


class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_restores_content(self, executor, mock_note_manager, history_manager):
        """rollback restaure le contenu original."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-rollback"
        mock_note.title = "Note Rollback"
        mock_note.content = "Contenu modifie"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        # Create and save a snapshot manually
        snapshot = GrimaudSnapshot(
            note_id="note-rollback",
            note_title="Note Rollback",
            action_type=GrimaudActionType.ENRICHISSEMENT,
            content_before="Contenu original avant modification",
        )
        history_manager.save_snapshot(snapshot)

        # Rollback
        result = executor.rollback(snapshot.snapshot_id)

        # Verify content was restored
        assert result is True
        mock_note_manager.update_note.assert_called_once_with(
            "note-rollback",
            content="Contenu original avant modification",
        )

    def test_rollback_deletes_snapshot(self, executor, history_manager, history_dir, mock_note_manager):
        """rollback supprime le snapshot apres restauration."""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-del-snap"
        mock_note.content = "Current content"
        mock_note_manager.get_note.return_value = mock_note

        # Create snapshot
        snapshot = GrimaudSnapshot(
            note_id="note-del-snap",
            note_title="Note Del Snap",
            action_type=GrimaudActionType.ENRICHISSEMENT,
            content_before="Original",
        )
        history_manager.save_snapshot(snapshot)
        assert len(list(history_dir.glob("*.json.gz"))) == 1

        # Rollback
        executor.rollback(snapshot.snapshot_id)

        # Snapshot should be deleted
        assert len(list(history_dir.glob("*.json.gz"))) == 0

    def test_rollback_returns_false_if_snapshot_not_found(self, executor):
        """rollback retourne False si snapshot non trouve."""
        result = executor.rollback("snap_unknown_id")

        assert result is False


class TestErrorHandling:
    """Tests for error handling."""

    def test_execute_returns_false_if_note_not_found(self, executor, mock_note_manager):
        """execute retourne False si note non trouvee."""
        mock_note_manager.get_note.return_value = None

        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-missing",
            note_title="Missing Note",
            confidence=0.90,
            new_content="Content",
        )

        result = executor.execute(action)

        assert result is False
        # Action should not be marked as applied
        assert action.applied is False

    def test_execute_returns_false_if_update_fails(self, executor, mock_note_manager):
        """execute retourne False si update_note echoue."""
        mock_note = MagicMock()
        mock_note.note_id = "note-fail"
        mock_note.title = "Fail Note"
        mock_note.content = "Content"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note
        mock_note_manager.update_note.return_value = False

        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="note-fail",
            note_title="Fail Note",
            confidence=0.90,
            new_content="New content",
        )

        result = executor.execute(action)

        assert result is False
        # Action should not be marked as applied on failure
        assert action.applied is False


class TestPlaceholderActions:
    """Tests for placeholder action types."""

    def test_execute_metadonnees_is_placeholder(self, executor, mock_note_manager):
        """execute metadonnees est un placeholder (retourne True sans modifier)."""
        mock_note = MagicMock()
        mock_note.note_id = "note-meta"
        mock_note.title = "Meta Note"
        mock_note.content = "Content"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        action = GrimaudAction(
            action_type=GrimaudActionType.METADONNEES,
            note_id="note-meta",
            note_title="Meta Note",
            confidence=0.85,
        )

        result = executor.execute(action)

        # Placeholder should succeed without updating content
        assert result is True
        mock_note_manager.update_note.assert_not_called()

    def test_execute_archivage_is_placeholder(self, executor, mock_note_manager):
        """execute archivage est un placeholder (retourne True sans modifier)."""
        mock_note = MagicMock()
        mock_note.note_id = "note-archive"
        mock_note.title = "Archive Note"
        mock_note.content = "Content"
        mock_note.metadata = {}
        mock_note_manager.get_note.return_value = mock_note

        action = GrimaudAction(
            action_type=GrimaudActionType.ARCHIVAGE,
            note_id="note-archive",
            note_title="Archive Note",
            confidence=0.90,
        )

        result = executor.execute(action)

        # Placeholder should succeed without updating content
        assert result is True
        mock_note_manager.update_note.assert_not_called()
