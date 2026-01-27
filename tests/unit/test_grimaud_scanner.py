"""Tests for Grimaud Scanner."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.grimaud.scanner import GrimaudScanner, NotePriority


@pytest.fixture
def mock_note_manager():
    """Mock NoteManager."""
    manager = MagicMock()
    return manager


@pytest.fixture
def mock_metadata_store():
    """Mock NoteMetadataStore."""
    store = MagicMock()
    return store


@pytest.fixture
def scanner(mock_note_manager, mock_metadata_store):
    """Cree un scanner avec mocks."""
    return GrimaudScanner(
        note_manager=mock_note_manager,
        metadata_store=mock_metadata_store,
    )


class TestNotePriority:
    """Tests for priority calculation."""

    def test_priority_increases_with_importance(self):
        """Notes importantes ont plus haute priorite."""
        high = NotePriority(importance=10, days_since_scan=0, problems=0)
        low = NotePriority(importance=1, days_since_scan=0, problems=0)

        assert high.score > low.score

    def test_priority_increases_with_age(self):
        """Notes non scannees depuis longtemps ont plus haute priorite."""
        old = NotePriority(importance=5, days_since_scan=30, problems=0)
        new = NotePriority(importance=5, days_since_scan=1, problems=0)

        assert old.score > new.score

    def test_priority_increases_with_problems(self):
        """Notes avec problemes detectes ont plus haute priorite."""
        problems = NotePriority(importance=5, days_since_scan=7, problems=3)
        clean = NotePriority(importance=5, days_since_scan=7, problems=0)

        assert problems.score > clean.score

    def test_priority_score_formula(self):
        """Score de priorite suit la formule documentee."""
        # Score = (importance × 3) + (days_since_scan × 2) + (problems × 1)
        p = NotePriority(importance=5, days_since_scan=10, problems=2)
        expected = (5 * 3) + (10 * 2) + (2 * 1)
        assert p.score == expected

    def test_days_since_scan_capped_at_30(self):
        """Anciennete est plafonnee a 30 jours."""
        p1 = NotePriority(importance=5, days_since_scan=30, problems=0)
        p2 = NotePriority(importance=5, days_since_scan=100, problems=0)

        assert p1.score == p2.score


class TestGrimaudScanner:
    """Tests for GrimaudScanner."""

    def test_select_next_note_returns_highest_priority(
        self, scanner, mock_note_manager, mock_metadata_store
    ):
        """select_next_note retourne la note avec la plus haute priorite."""
        # Setup mock notes
        mock_notes = [
            MagicMock(note_id="note-1", note_type=MagicMock(value="concept")),
            MagicMock(note_id="note-2", note_type=MagicMock(value="personne")),
        ]
        mock_note_manager.get_all_notes.return_value = mock_notes

        # Setup mock metadata (note-2 not scanned recently)
        def get_metadata(note_id):
            if note_id == "note-1":
                meta = MagicMock()
                meta.retouche_last = datetime.now(timezone.utc) - timedelta(days=1)
                meta.importance = MagicMock(value="normal")
                return meta
            else:
                meta = MagicMock()
                meta.retouche_last = datetime.now(timezone.utc) - timedelta(days=20)
                meta.importance = MagicMock(value="high")
                return meta

        mock_metadata_store.get.side_effect = get_metadata

        # Test
        result = scanner.select_next_note()

        # note-2 should be selected (higher priority: older + higher importance)
        assert result is not None
        assert result.note_id == "note-2"

    def test_select_next_note_skips_recently_scanned(
        self, scanner, mock_note_manager, mock_metadata_store
    ):
        """select_next_note ignore les notes scannees recemment."""
        mock_notes = [
            MagicMock(note_id="recent", note_type=MagicMock(value="concept")),
        ]
        mock_note_manager.get_all_notes.return_value = mock_notes

        # Scanned 12 hours ago
        meta = MagicMock()
        meta.retouche_last = datetime.now(timezone.utc) - timedelta(hours=12)
        meta.importance = MagicMock(value="normal")
        mock_metadata_store.get.return_value = meta

        result = scanner.select_next_note(min_age_hours=24)

        assert result is None

    def test_select_next_note_includes_notes_without_metadata(
        self, scanner, mock_note_manager, mock_metadata_store
    ):
        """Notes sans metadonnees sont incluses avec priorite haute."""
        mock_notes = [
            MagicMock(note_id="no-meta", note_type=MagicMock(value="concept")),
        ]
        mock_note_manager.get_all_notes.return_value = mock_notes

        # No metadata for this note
        mock_metadata_store.get.return_value = None

        result = scanner.select_next_note()

        assert result is not None
        assert result.note_id == "no-meta"

    def test_should_scan_respects_throttle(self, scanner):
        """should_scan respecte le throttling."""
        # Simuler qu'on a deja scanne 10 notes cette heure
        scanner._scans_this_hour = 10
        scanner._hour_start = datetime.now(timezone.utc)

        assert scanner.should_scan(max_per_hour=10) is False
        assert scanner.should_scan(max_per_hour=15) is True

    def test_should_scan_resets_hourly_counter(self, scanner):
        """should_scan remet a zero le compteur apres une heure."""
        scanner._scans_this_hour = 10
        scanner._hour_start = datetime.now(timezone.utc) - timedelta(hours=2)

        # Should reset counter because more than 1 hour has passed
        assert scanner.should_scan(max_per_hour=10) is True
        assert scanner._scans_this_hour == 0

    def test_mark_scanned_updates_metadata(self, scanner, mock_metadata_store):
        """mark_scanned met a jour les metadonnees."""
        note_id = "test-note"
        mock_meta = MagicMock()
        mock_metadata_store.get.return_value = mock_meta

        result = scanner.mark_scanned(note_id)

        # Should call metadata store to update retouche_last
        assert result is True
        mock_metadata_store.get.assert_called_once_with(note_id)
        mock_metadata_store.save.assert_called_once_with(mock_meta)
        assert mock_meta.retouche_last is not None

    def test_mark_scanned_increments_counter(self, scanner, mock_metadata_store):
        """mark_scanned incremente le compteur horaire."""
        mock_metadata_store.get.return_value = MagicMock()

        initial_count = scanner._scans_this_hour
        scanner.mark_scanned("note-1")

        assert scanner._scans_this_hour == initial_count + 1

    def test_mark_scanned_returns_false_without_metadata(self, scanner, mock_metadata_store):
        """mark_scanned retourne False si pas de metadata."""
        mock_metadata_store.get.return_value = None

        initial_count = scanner._scans_this_hour
        result = scanner.mark_scanned("note-without-meta")

        assert result is False
        assert scanner._scans_this_hour == initial_count  # Counter not incremented
        mock_metadata_store.save.assert_not_called()

    def test_get_scan_stats_returns_correct_data(self, scanner):
        """get_scan_stats retourne les statistiques correctes."""
        scanner._scans_this_hour = 5

        stats = scanner.get_scan_stats()

        assert stats["scans_this_hour"] == 5
        assert "hour_start" in stats
        assert "max_per_hour" in stats

    def test_select_next_note_returns_none_when_all_recent(
        self, scanner, mock_note_manager, mock_metadata_store
    ):
        """select_next_note retourne None si toutes les notes sont recentes."""
        mock_notes = [
            MagicMock(note_id="note-1", note_type=MagicMock(value="concept")),
            MagicMock(note_id="note-2", note_type=MagicMock(value="personne")),
        ]
        mock_note_manager.get_all_notes.return_value = mock_notes

        # All notes scanned recently
        meta = MagicMock()
        meta.retouche_last = datetime.now(timezone.utc) - timedelta(hours=1)
        meta.importance = MagicMock(value="normal")
        mock_metadata_store.get.return_value = meta

        result = scanner.select_next_note(min_age_hours=24)

        assert result is None

    def test_select_next_note_handles_exception(
        self, scanner, mock_note_manager, mock_metadata_store
    ):
        """select_next_note gere les erreurs gracieusement."""
        mock_note_manager.get_all_notes.side_effect = Exception("DB error")

        result = scanner.select_next_note()

        assert result is None
