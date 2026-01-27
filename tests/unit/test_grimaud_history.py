"""Tests for Grimaud History Manager."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.grimaud.history import GrimaudHistoryManager
from src.grimaud.models import GrimaudActionType, GrimaudSnapshot


@pytest.fixture
def history_dir():
    """Crée un répertoire temporaire pour les snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def history_manager(history_dir):
    """Crée un HistoryManager avec répertoire temporaire."""
    return GrimaudHistoryManager(snapshots_dir=history_dir)


class TestGrimaudHistoryManager:
    """Tests for GrimaudHistoryManager."""

    def test_save_snapshot_creates_file(self, history_manager, history_dir):
        """save_snapshot crée un fichier gzip."""
        snapshot = GrimaudSnapshot(
            note_id="test-note",
            note_title="Test Note",
            action_type=GrimaudActionType.ENRICHISSEMENT,
            content_before="# Test\n\nOriginal content",
        )

        history_manager.save_snapshot(snapshot)

        # Vérifie qu'un fichier existe
        files = list(history_dir.glob("*.json.gz"))
        assert len(files) == 1

    def test_get_snapshot_returns_saved(self, history_manager):
        """get_snapshot retourne un snapshot sauvegardé."""
        snapshot = GrimaudSnapshot(
            note_id="note-123",
            note_title="Ma Note",
            action_type=GrimaudActionType.FUSION,
            content_before="Contenu avant",
        )

        history_manager.save_snapshot(snapshot)
        restored = history_manager.get_snapshot(snapshot.snapshot_id)

        assert restored is not None
        assert restored.note_id == "note-123"
        assert restored.content_before == "Contenu avant"

    def test_get_snapshot_returns_none_for_unknown(self, history_manager):
        """get_snapshot retourne None si snapshot inexistant."""
        result = history_manager.get_snapshot("snap_unknown")
        assert result is None

    def test_list_snapshots_for_note(self, history_manager):
        """list_snapshots_for_note retourne les snapshots d'une note."""
        # Créer plusieurs snapshots pour la même note
        for i in range(3):
            snapshot = GrimaudSnapshot(
                note_id="note-A",
                note_title=f"Note A v{i}",
                action_type=GrimaudActionType.ENRICHISSEMENT,
                content_before=f"Content v{i}",
            )
            history_manager.save_snapshot(snapshot)

        # Créer un snapshot pour une autre note
        other = GrimaudSnapshot(
            note_id="note-B",
            note_title="Note B",
            action_type=GrimaudActionType.LIAISON,
            content_before="Other content",
        )
        history_manager.save_snapshot(other)

        # Vérifier
        snapshots = history_manager.list_snapshots_for_note("note-A")
        assert len(snapshots) == 3
        assert all(s.note_id == "note-A" for s in snapshots)

    def test_delete_snapshot(self, history_manager, history_dir):
        """delete_snapshot supprime le fichier."""
        snapshot = GrimaudSnapshot(
            note_id="to-delete",
            note_title="To Delete",
            action_type=GrimaudActionType.ARCHIVAGE,
            content_before="Will be deleted",
        )

        history_manager.save_snapshot(snapshot)
        assert len(list(history_dir.glob("*.json.gz"))) == 1

        deleted = history_manager.delete_snapshot(snapshot.snapshot_id)

        assert deleted is True
        assert len(list(history_dir.glob("*.json.gz"))) == 0

    def test_purge_old_snapshots(self, history_manager, history_dir):
        """purge_old_snapshots supprime les snapshots > 30 jours."""
        # Créer un snapshot "vieux"
        old_snapshot = GrimaudSnapshot(
            note_id="old-note",
            note_title="Old Note",
            action_type=GrimaudActionType.ENRICHISSEMENT,
            content_before="Old content",
        )
        # Modifier le timestamp pour simuler 35 jours
        old_snapshot.timestamp = datetime.now(timezone.utc) - timedelta(days=35)
        history_manager.save_snapshot(old_snapshot)

        # Créer un snapshot récent
        new_snapshot = GrimaudSnapshot(
            note_id="new-note",
            note_title="New Note",
            action_type=GrimaudActionType.ENRICHISSEMENT,
            content_before="New content",
        )
        history_manager.save_snapshot(new_snapshot)

        # Purger
        purged = history_manager.purge_old_snapshots(max_age_days=30)

        assert purged == 1
        assert len(list(history_dir.glob("*.json.gz"))) == 1
        # Le nouveau snapshot existe toujours
        assert history_manager.get_snapshot(new_snapshot.snapshot_id) is not None

    def test_get_recent_history(self, history_manager):
        """get_recent_history retourne les N derniers snapshots."""
        for i in range(10):
            snapshot = GrimaudSnapshot(
                note_id=f"note-{i}",
                note_title=f"Note {i}",
                action_type=GrimaudActionType.ENRICHISSEMENT,
                content_before=f"Content {i}",
            )
            history_manager.save_snapshot(snapshot)

        recent = history_manager.get_recent_history(limit=5)

        assert len(recent) == 5
        # Triés par timestamp décroissant
        for i in range(len(recent) - 1):
            assert recent[i].timestamp >= recent[i + 1].timestamp
