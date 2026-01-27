"""Tests for Grimaud models."""

from datetime import datetime, timezone

from src.grimaud.models import (
    CONFIDENCE_THRESHOLDS,
    GrimaudAction,
    GrimaudActionType,
    GrimaudScanResult,
    GrimaudSnapshot,
    GrimaudStats,
)


class TestGrimaudActionType:
    """Tests for GrimaudActionType enum."""

    def test_all_types_have_thresholds(self):
        """Chaque type d'action doit avoir un seuil de confiance."""
        for action_type in GrimaudActionType:
            assert action_type in CONFIDENCE_THRESHOLDS

    def test_fusion_has_highest_threshold(self):
        """Fusion necessite la confiance la plus haute."""
        assert CONFIDENCE_THRESHOLDS[GrimaudActionType.FUSION] == 0.95


class TestGrimaudAction:
    """Tests for GrimaudAction dataclass."""

    def test_default_values(self):
        """Action creee avec valeurs par defaut."""
        action = GrimaudAction()
        assert action.action_id is not None
        assert len(action.action_id) == 8
        assert action.applied is False
        assert action.confidence == 0.0

    def test_should_auto_apply_above_threshold(self):
        """Action auto-appliquee si confidence >= seuil."""
        action = GrimaudAction(
            action_type=GrimaudActionType.LIAISON,
            confidence=0.90,
        )
        assert action.should_auto_apply() is True

    def test_should_not_auto_apply_below_threshold(self):
        """Action non auto-appliquee si confidence < seuil."""
        action = GrimaudAction(
            action_type=GrimaudActionType.FUSION,
            confidence=0.80,
        )
        assert action.should_auto_apply() is False

    def test_to_dict_serialization(self):
        """to_dict produit un dict serialisable."""
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="test-note",
            note_title="Test Note",
            confidence=0.92,
            reasoning="Section vide detectee",
        )
        data = action.to_dict()

        assert data["action_type"] == "enrichissement"
        assert data["note_id"] == "test-note"
        assert data["confidence"] == 0.92
        assert "created_at" in data


class TestGrimaudSnapshot:
    """Tests for GrimaudSnapshot dataclass."""

    def test_snapshot_id_format(self):
        """ID snapshot a le bon format."""
        snapshot = GrimaudSnapshot()
        assert snapshot.snapshot_id.startswith("snap_")
        parts = snapshot.snapshot_id.split("_")
        assert len(parts) == 4  # snap_YYYYMMDD_HHMMSS_hash

    def test_to_dict_and_from_dict_roundtrip(self):
        """Conversion dict -> Snapshot -> dict conserve les donnees."""
        original = GrimaudSnapshot(
            note_id="note-123",
            note_title="Ma Note",
            action_type=GrimaudActionType.FUSION,
            action_detail="Fusionne avec Note X",
            confidence=0.96,
            content_before="# Ma Note\n\nContenu original",
            frontmatter_before={"title": "Ma Note", "type": "concept"},
        )

        data = original.to_dict()
        restored = GrimaudSnapshot.from_dict(data)

        assert restored.note_id == original.note_id
        assert restored.action_type == original.action_type
        assert restored.content_before == original.content_before
        assert restored.frontmatter_before == original.frontmatter_before


class TestGrimaudScanResult:
    """Tests for GrimaudScanResult dataclass."""

    def test_has_problems_when_empty(self):
        """has_problems False si aucun probleme."""
        result = GrimaudScanResult(note_id="test", note_title="Test")
        assert result.has_problems is False

    def test_has_problems_when_detected(self):
        """has_problems True si problemes detectes."""
        result = GrimaudScanResult(
            note_id="test",
            note_title="Test",
            problems_detected=["Section vide", "Lien casse"],
        )
        assert result.has_problems is True


class TestGrimaudStats:
    """Tests for GrimaudStats dataclass."""

    def test_to_dict_handles_none_datetime(self):
        """to_dict gere last_scan_at None."""
        stats = GrimaudStats()
        data = stats.to_dict()
        assert data["last_scan_at"] is None

    def test_to_dict_formats_datetime(self):
        """to_dict formate les datetime en ISO."""
        now = datetime.now(timezone.utc)
        stats = GrimaudStats(last_scan_at=now)
        data = stats.to_dict()
        assert data["last_scan_at"] == now.isoformat()
