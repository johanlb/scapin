# Grimaud Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implémenter le module Grimaud — Gardien proactif du PKM qui scanne, détecte les problèmes et maintient les notes automatiquement.

**Architecture:** Nouveau module `src/grimaud/` avec Scanner (priorisation), Analyzer (détection IA), Executor (actions + snapshots), History (versioning 30j). Remplace Retouche avec interface unifiée. API REST + UI dashboard.

**Tech Stack:** Python 3.13, FastAPI, SQLite (snapshots), FAISS (similarité), Svelte 5, Pydantic

**Design source:** `docs/plans/2026-01-27-grimaud-guardian-design.md`

---

## Phase 1: Backend Core (Priorité Haute)

### Task 1: Module Structure + Models

**Files:**
- Create: `src/grimaud/__init__.py`
- Create: `src/grimaud/models.py`
- Test: `tests/unit/test_grimaud_models.py`

**Step 1: Create module structure**

```python
# src/grimaud/__init__.py
"""
Grimaud — Gardien du PKM

Module de maintenance proactive des notes. Scanne continuellement le PKM,
détecte les problèmes (fragmentation, incomplétude, obsolescence) et agit
automatiquement si la confiance est suffisante.

Remplace l'ancien système Retouche avec une interface unifiée.

Composants:
- Scanner: Sélection et priorisation des notes à analyser
- Analyzer: Détection des problèmes via pré-analyse + IA
- Executor: Application des actions avec snapshots
- History: Gestion des snapshots et de la corbeille (30 jours)
"""

from src.grimaud.models import (
    GrimaudAction,
    GrimaudActionType,
    GrimaudSnapshot,
    GrimaudScanResult,
    GrimaudStats,
)

__all__ = [
    "GrimaudAction",
    "GrimaudActionType",
    "GrimaudSnapshot",
    "GrimaudScanResult",
    "GrimaudStats",
]
```

**Step 2: Create models**

```python
# src/grimaud/models.py
"""Models for Grimaud — PKM Guardian."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class GrimaudActionType(str, Enum):
    """Types d'actions Grimaud."""
    FUSION = "fusion"           # Combiner 2+ notes
    LIAISON = "liaison"         # Créer wikilink entre notes
    RESTRUCTURATION = "restructuration"  # Réorganiser selon template
    ENRICHISSEMENT = "enrichissement"    # Compléter sections vides
    ENRICHISSEMENT_WEB = "enrichissement_web"  # Ajouter infos web
    METADONNEES = "metadonnees"  # Corriger frontmatter
    ARCHIVAGE = "archivage"     # Marquer obsolète


# Seuils de confiance pour auto-apply
CONFIDENCE_THRESHOLDS: dict[GrimaudActionType, float] = {
    GrimaudActionType.FUSION: 0.95,
    GrimaudActionType.LIAISON: 0.85,
    GrimaudActionType.RESTRUCTURATION: 0.90,
    GrimaudActionType.ENRICHISSEMENT: 0.90,
    GrimaudActionType.ENRICHISSEMENT_WEB: 0.80,
    GrimaudActionType.METADONNEES: 0.85,
    GrimaudActionType.ARCHIVAGE: 0.90,
}


@dataclass
class GrimaudAction:
    """Action proposée par Grimaud."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: GrimaudActionType = GrimaudActionType.ENRICHISSEMENT
    note_id: str = ""
    note_title: str = ""
    confidence: float = 0.0
    reasoning: str = ""

    # Champs optionnels selon type d'action
    target_note_id: Optional[str] = None
    target_note_title: Optional[str] = None
    content_diff: Optional[str] = None
    new_content: Optional[str] = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    applied: bool = False
    applied_at: Optional[datetime] = None

    def should_auto_apply(self) -> bool:
        """Vérifie si l'action doit être appliquée automatiquement."""
        threshold = CONFIDENCE_THRESHOLDS.get(self.action_type, 0.90)
        return self.confidence >= threshold

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dictionnaire pour API/stockage."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "note_id": self.note_id,
            "note_title": self.note_title,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "target_note_id": self.target_note_id,
            "target_note_title": self.target_note_title,
            "content_diff": self.content_diff,
            "new_content": self.new_content,
            "created_at": self.created_at.isoformat(),
            "applied": self.applied,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }


@dataclass
class GrimaudSnapshot:
    """Snapshot d'une note avant modification."""
    snapshot_id: str = field(default_factory=lambda: f"snap_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}")
    note_id: str = ""
    note_title: str = ""
    action_type: GrimaudActionType = GrimaudActionType.ENRICHISSEMENT
    action_detail: str = ""
    confidence: float = 0.0
    content_before: str = ""
    frontmatter_before: dict[str, Any] = field(default_factory=dict)
    triggered_by: str = "grimaud_auto"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dictionnaire pour stockage JSON."""
        return {
            "snapshot_id": self.snapshot_id,
            "note_id": self.note_id,
            "note_title": self.note_title,
            "action_type": self.action_type.value,
            "action_detail": self.action_detail,
            "confidence": self.confidence,
            "content_before": self.content_before,
            "frontmatter_before": self.frontmatter_before,
            "triggered_by": self.triggered_by,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GrimaudSnapshot":
        """Crée depuis un dictionnaire."""
        return cls(
            snapshot_id=data["snapshot_id"],
            note_id=data["note_id"],
            note_title=data["note_title"],
            action_type=GrimaudActionType(data["action_type"]),
            action_detail=data["action_detail"],
            confidence=data["confidence"],
            content_before=data["content_before"],
            frontmatter_before=data.get("frontmatter_before", {}),
            triggered_by=data.get("triggered_by", "grimaud_auto"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class GrimaudScanResult:
    """Résultat d'un scan de note."""
    note_id: str
    note_title: str
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    problems_detected: list[str] = field(default_factory=list)
    actions_proposed: list[GrimaudAction] = field(default_factory=list)
    actions_applied: list[str] = field(default_factory=list)  # action_ids
    scan_duration_ms: float = 0.0
    ai_called: bool = False

    @property
    def has_problems(self) -> bool:
        return len(self.problems_detected) > 0


@dataclass
class GrimaudStats:
    """Statistiques globales Grimaud."""
    total_notes: int = 0
    health_score: float = 0.0  # 0-100%
    pending_actions: int = 0
    fusions_this_month: int = 0
    enrichments_this_month: int = 0
    last_scan_at: Optional[datetime] = None
    notes_scanned_today: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_notes": self.total_notes,
            "health_score": self.health_score,
            "pending_actions": self.pending_actions,
            "fusions_this_month": self.fusions_this_month,
            "enrichments_this_month": self.enrichments_this_month,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "notes_scanned_today": self.notes_scanned_today,
        }
```

**Step 3: Write tests**

```python
# tests/unit/test_grimaud_models.py
"""Tests for Grimaud models."""

from datetime import datetime, timezone

import pytest

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
        """Fusion nécessite la confiance la plus haute."""
        assert CONFIDENCE_THRESHOLDS[GrimaudActionType.FUSION] == 0.95


class TestGrimaudAction:
    """Tests for GrimaudAction dataclass."""

    def test_default_values(self):
        """Action créée avec valeurs par défaut."""
        action = GrimaudAction()
        assert action.action_id is not None
        assert len(action.action_id) == 8
        assert action.applied is False
        assert action.confidence == 0.0

    def test_should_auto_apply_above_threshold(self):
        """Action auto-appliquée si confidence >= seuil."""
        action = GrimaudAction(
            action_type=GrimaudActionType.LIAISON,
            confidence=0.90,
        )
        assert action.should_auto_apply() is True

    def test_should_not_auto_apply_below_threshold(self):
        """Action non auto-appliquée si confidence < seuil."""
        action = GrimaudAction(
            action_type=GrimaudActionType.FUSION,
            confidence=0.80,
        )
        assert action.should_auto_apply() is False

    def test_to_dict_serialization(self):
        """to_dict produit un dict sérialisable."""
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="test-note",
            note_title="Test Note",
            confidence=0.92,
            reasoning="Section vide détectée",
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
        """Conversion dict -> Snapshot -> dict conserve les données."""
        original = GrimaudSnapshot(
            note_id="note-123",
            note_title="Ma Note",
            action_type=GrimaudActionType.FUSION,
            action_detail="Fusionné avec Note X",
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
        """has_problems False si aucun problème."""
        result = GrimaudScanResult(note_id="test", note_title="Test")
        assert result.has_problems is False

    def test_has_problems_when_detected(self):
        """has_problems True si problèmes détectés."""
        result = GrimaudScanResult(
            note_id="test",
            note_title="Test",
            problems_detected=["Section vide", "Lien cassé"],
        )
        assert result.has_problems is True


class TestGrimaudStats:
    """Tests for GrimaudStats dataclass."""

    def test_to_dict_handles_none_datetime(self):
        """to_dict gère last_scan_at None."""
        stats = GrimaudStats()
        data = stats.to_dict()
        assert data["last_scan_at"] is None

    def test_to_dict_formats_datetime(self):
        """to_dict formate les datetime en ISO."""
        now = datetime.now(timezone.utc)
        stats = GrimaudStats(last_scan_at=now)
        data = stats.to_dict()
        assert data["last_scan_at"] == now.isoformat()
```

**Step 4: Run tests**

Run: `pytest tests/unit/test_grimaud_models.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/grimaud/ tests/unit/test_grimaud_models.py
git commit -m "feat(grimaud): add models for PKM guardian module"
```

---

### Task 2: History Manager (Snapshots)

**Files:**
- Create: `src/grimaud/history.py`
- Test: `tests/unit/test_grimaud_history.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_grimaud_history.py
"""Tests for Grimaud History Manager."""

import gzip
import json
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_grimaud_history.py -v`
Expected: FAIL (module not found)

**Step 3: Implement history manager**

```python
# src/grimaud/history.py
"""
History Manager for Grimaud snapshots.

Gère le stockage et la récupération des snapshots de notes avant modification.
Snapshots stockés en JSON compressé (gzip), rétention 30 jours, purge automatique.
"""

import gzip
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.grimaud.models import GrimaudSnapshot
from src.monitoring.logger import get_logger

logger = get_logger("grimaud.history")

DEFAULT_RETENTION_DAYS = 30


class GrimaudHistoryManager:
    """
    Gestionnaire de l'historique des snapshots Grimaud.

    Stocke les snapshots en fichiers JSON compressés (gzip).
    Nom fichier: {snapshot_id}.json.gz
    """

    def __init__(self, snapshots_dir: Path):
        """
        Initialise le gestionnaire d'historique.

        Args:
            snapshots_dir: Répertoire de stockage des snapshots
        """
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Initialized history manager", extra={"dir": str(self.snapshots_dir)})

    def _get_snapshot_path(self, snapshot_id: str) -> Path:
        """Retourne le chemin du fichier snapshot."""
        return self.snapshots_dir / f"{snapshot_id}.json.gz"

    def save_snapshot(self, snapshot: GrimaudSnapshot) -> None:
        """
        Sauvegarde un snapshot en fichier compressé.

        Args:
            snapshot: Snapshot à sauvegarder
        """
        path = self._get_snapshot_path(snapshot.snapshot_id)
        data = json.dumps(snapshot.to_dict(), ensure_ascii=False)

        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(data)

        logger.info(
            "Snapshot saved",
            extra={
                "snapshot_id": snapshot.snapshot_id,
                "note_id": snapshot.note_id,
                "action": snapshot.action_type.value,
            },
        )

    def get_snapshot(self, snapshot_id: str) -> Optional[GrimaudSnapshot]:
        """
        Récupère un snapshot par son ID.

        Args:
            snapshot_id: ID du snapshot

        Returns:
            GrimaudSnapshot ou None si non trouvé
        """
        path = self._get_snapshot_path(snapshot_id)

        if not path.exists():
            return None

        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                data = json.load(f)
            return GrimaudSnapshot.from_dict(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to read snapshot",
                extra={"snapshot_id": snapshot_id, "error": str(e)},
            )
            return None

    def list_snapshots_for_note(self, note_id: str) -> list[GrimaudSnapshot]:
        """
        Liste tous les snapshots d'une note.

        Args:
            note_id: ID de la note

        Returns:
            Liste de snapshots triés par timestamp décroissant
        """
        snapshots = []

        for path in self.snapshots_dir.glob("*.json.gz"):
            try:
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("note_id") == note_id:
                    snapshots.append(GrimaudSnapshot.from_dict(data))
            except (json.JSONDecodeError, OSError):
                continue

        # Trier par timestamp décroissant
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        return snapshots

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Supprime un snapshot.

        Args:
            snapshot_id: ID du snapshot à supprimer

        Returns:
            True si supprimé, False si non trouvé
        """
        path = self._get_snapshot_path(snapshot_id)

        if not path.exists():
            return False

        path.unlink()
        logger.info("Snapshot deleted", extra={"snapshot_id": snapshot_id})
        return True

    def purge_old_snapshots(self, max_age_days: int = DEFAULT_RETENTION_DAYS) -> int:
        """
        Supprime les snapshots plus vieux que max_age_days.

        Args:
            max_age_days: Âge maximum en jours (défaut: 30)

        Returns:
            Nombre de snapshots supprimés
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        purged = 0

        for path in self.snapshots_dir.glob("*.json.gz"):
            try:
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data["timestamp"])

                if timestamp < cutoff:
                    path.unlink()
                    purged += 1
                    logger.debug(
                        "Purged old snapshot",
                        extra={"snapshot_id": data["snapshot_id"], "age_days": (datetime.now(timezone.utc) - timestamp).days},
                    )
            except (json.JSONDecodeError, OSError, KeyError):
                continue

        if purged > 0:
            logger.info("Purged old snapshots", extra={"count": purged, "max_age_days": max_age_days})

        return purged

    def get_recent_history(self, limit: int = 50) -> list[GrimaudSnapshot]:
        """
        Retourne les N derniers snapshots.

        Args:
            limit: Nombre maximum de snapshots à retourner

        Returns:
            Liste de snapshots triés par timestamp décroissant
        """
        snapshots = []

        for path in self.snapshots_dir.glob("*.json.gz"):
            try:
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                snapshots.append(GrimaudSnapshot.from_dict(data))
            except (json.JSONDecodeError, OSError):
                continue

        # Trier par timestamp décroissant et limiter
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        return snapshots[:limit]

    def get_stats(self) -> dict:
        """
        Retourne des statistiques sur les snapshots.

        Returns:
            Dict avec total, par type d'action, espace utilisé
        """
        total = 0
        by_action = {}
        total_size = 0

        for path in self.snapshots_dir.glob("*.json.gz"):
            total += 1
            total_size += path.stat().st_size

            try:
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                action = data.get("action_type", "unknown")
                by_action[action] = by_action.get(action, 0) + 1
            except (json.JSONDecodeError, OSError):
                continue

        return {
            "total": total,
            "by_action": by_action,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
        }
```

**Step 4: Update __init__.py exports**

```python
# Add to src/grimaud/__init__.py
from src.grimaud.history import GrimaudHistoryManager

__all__ = [
    # ... existing exports ...
    "GrimaudHistoryManager",
]
```

**Step 5: Run tests**

Run: `pytest tests/unit/test_grimaud_history.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/grimaud/history.py tests/unit/test_grimaud_history.py
git commit -m "feat(grimaud): add history manager for snapshots"
```

---

### Task 3: Scanner (Note Selection & Prioritization)

**Files:**
- Create: `src/grimaud/scanner.py`
- Test: `tests/unit/test_grimaud_scanner.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_grimaud_scanner.py
"""Tests for Grimaud Scanner."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

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
    """Crée un scanner avec mocks."""
    return GrimaudScanner(
        note_manager=mock_note_manager,
        metadata_store=mock_metadata_store,
    )


class TestNotePriority:
    """Tests for priority calculation."""

    def test_priority_increases_with_importance(self):
        """Notes importantes ont plus haute priorité."""
        high = NotePriority(importance=10, days_since_scan=0, problems=0)
        low = NotePriority(importance=1, days_since_scan=0, problems=0)

        assert high.score > low.score

    def test_priority_increases_with_age(self):
        """Notes non scannées depuis longtemps ont plus haute priorité."""
        old = NotePriority(importance=5, days_since_scan=30, problems=0)
        new = NotePriority(importance=5, days_since_scan=1, problems=0)

        assert old.score > new.score

    def test_priority_increases_with_problems(self):
        """Notes avec problèmes détectés ont plus haute priorité."""
        problems = NotePriority(importance=5, days_since_scan=7, problems=3)
        clean = NotePriority(importance=5, days_since_scan=7, problems=0)

        assert problems.score > clean.score


class TestGrimaudScanner:
    """Tests for GrimaudScanner."""

    def test_select_next_note_returns_highest_priority(self, scanner, mock_note_manager, mock_metadata_store):
        """select_next_note retourne la note avec la plus haute priorité."""
        # Setup mock notes
        mock_notes = [
            MagicMock(note_id="note-1", note_type=MagicMock(value="concept")),
            MagicMock(note_id="note-2", note_type=MagicMock(value="personne")),
        ]
        mock_note_manager.list_all_notes.return_value = mock_notes

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

    def test_select_next_note_skips_recently_scanned(self, scanner, mock_note_manager, mock_metadata_store):
        """select_next_note ignore les notes scannées récemment."""
        mock_notes = [
            MagicMock(note_id="recent", note_type=MagicMock(value="concept")),
        ]
        mock_note_manager.list_all_notes.return_value = mock_notes

        # Scanned yesterday
        meta = MagicMock()
        meta.retouche_last = datetime.now(timezone.utc) - timedelta(hours=12)
        meta.importance = MagicMock(value="normal")
        mock_metadata_store.get.return_value = meta

        result = scanner.select_next_note(min_age_hours=24)

        assert result is None

    def test_should_scan_respects_throttle(self, scanner):
        """should_scan respecte le throttling."""
        # Simuler qu'on a déjà scanné 10 notes cette heure
        scanner._scans_this_hour = 10
        scanner._hour_start = datetime.now(timezone.utc)

        assert scanner.should_scan(max_per_hour=10) is False
        assert scanner.should_scan(max_per_hour=15) is True

    def test_mark_scanned_updates_metadata(self, scanner, mock_metadata_store):
        """mark_scanned met à jour les métadonnées."""
        note_id = "test-note"

        scanner.mark_scanned(note_id)

        # Should call metadata store to update retouche_last
        mock_metadata_store.get.assert_called_once_with(note_id)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_grimaud_scanner.py -v`
Expected: FAIL (module not found)

**Step 3: Implement scanner**

```python
# src/grimaud/scanner.py
"""
Scanner for Grimaud — Note selection and prioritization.

Sélectionne les notes à analyser en fonction de leur priorité.
Score de priorité = (importance × 3) + (ancienneté_scan × 2) + (problèmes × 1)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager
from src.passepartout.note_metadata import NoteMetadataStore
from src.passepartout.note_types import ImportanceLevel

logger = get_logger("grimaud.scanner")

# Configuration throttling
DEFAULT_MAX_PER_HOUR = 10
DEFAULT_MIN_AGE_HOURS = 24 * 7  # 7 jours minimum entre scans


@dataclass
class NotePriority:
    """Calcul de priorité d'une note pour le scan."""
    importance: int  # 1-10
    days_since_scan: int  # max 30
    problems: int  # count

    @property
    def score(self) -> float:
        """Score de priorité (plus élevé = plus prioritaire)."""
        return (self.importance * 3) + (min(self.days_since_scan, 30) * 2) + (self.problems * 1)


# Mapping importance vers score
IMPORTANCE_SCORES = {
    ImportanceLevel.CRITICAL: 10,
    ImportanceLevel.HIGH: 7,
    ImportanceLevel.NORMAL: 4,
    ImportanceLevel.LOW: 2,
    ImportanceLevel.ARCHIVE: 1,
}


class GrimaudScanner:
    """
    Sélectionne les notes à scanner et gère le throttling.

    Priorise les notes selon:
    - Importance (liée à projet actif)
    - Ancienneté du dernier scan
    - Problèmes détectés (pré-analyse rapide)
    """

    def __init__(
        self,
        note_manager: NoteManager,
        metadata_store: NoteMetadataStore,
    ):
        """
        Initialise le scanner.

        Args:
            note_manager: Gestionnaire des notes
            metadata_store: Store des métadonnées
        """
        self.note_manager = note_manager
        self.metadata_store = metadata_store

        # Throttling state
        self._scans_this_hour = 0
        self._hour_start = datetime.now(timezone.utc)

    def _reset_hourly_counter_if_needed(self) -> None:
        """Remet à zéro le compteur horaire si nécessaire."""
        now = datetime.now(timezone.utc)
        if (now - self._hour_start).total_seconds() >= 3600:
            self._scans_this_hour = 0
            self._hour_start = now

    def should_scan(self, max_per_hour: int = DEFAULT_MAX_PER_HOUR) -> bool:
        """
        Vérifie si un scan est autorisé (throttling).

        Args:
            max_per_hour: Maximum de scans par heure

        Returns:
            True si scan autorisé
        """
        self._reset_hourly_counter_if_needed()
        return self._scans_this_hour < max_per_hour

    def _calculate_priority(self, note_id: str) -> Optional[NotePriority]:
        """
        Calcule la priorité d'une note.

        Args:
            note_id: ID de la note

        Returns:
            NotePriority ou None si erreur
        """
        metadata = self.metadata_store.get(note_id)
        if metadata is None:
            return None

        # Importance
        importance_level = metadata.importance
        if hasattr(importance_level, 'value'):
            importance_level = ImportanceLevel(importance_level.value)
        importance = IMPORTANCE_SCORES.get(importance_level, 4)

        # Ancienneté du scan
        last_scan = metadata.retouche_last
        if last_scan is None:
            days_since_scan = 30  # Jamais scanné = max priorité
        else:
            if last_scan.tzinfo is None:
                last_scan = last_scan.replace(tzinfo=timezone.utc)
            days_since_scan = (datetime.now(timezone.utc) - last_scan).days

        # TODO: Ajouter détection problèmes rapide (liens cassés, sections vides)
        problems = 0

        return NotePriority(
            importance=importance,
            days_since_scan=days_since_scan,
            problems=problems,
        )

    def select_next_note(
        self,
        min_age_hours: int = DEFAULT_MIN_AGE_HOURS,
    ):
        """
        Sélectionne la prochaine note à scanner.

        Args:
            min_age_hours: Âge minimum depuis dernier scan (heures)

        Returns:
            Note à scanner ou None si aucune disponible
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)
        candidates = []

        # Lister toutes les notes
        try:
            all_notes = self.note_manager.list_all_notes()
        except Exception as e:
            logger.error(f"Failed to list notes: {e}")
            return None

        for note in all_notes:
            note_id = note.note_id
            metadata = self.metadata_store.get(note_id)

            if metadata is None:
                # Note sans métadonnées = priorité haute
                candidates.append((note, NotePriority(importance=5, days_since_scan=30, problems=0)))
                continue

            # Vérifier âge minimum
            last_scan = metadata.retouche_last
            if last_scan is not None:
                if last_scan.tzinfo is None:
                    last_scan = last_scan.replace(tzinfo=timezone.utc)
                if last_scan > cutoff:
                    continue  # Trop récent

            priority = self._calculate_priority(note_id)
            if priority:
                candidates.append((note, priority))

        if not candidates:
            logger.debug("No notes available for scanning")
            return None

        # Trier par score décroissant
        candidates.sort(key=lambda x: x[1].score, reverse=True)

        selected = candidates[0][0]
        logger.info(
            "Selected note for scanning",
            extra={
                "note_id": selected.note_id,
                "priority_score": candidates[0][1].score,
            },
        )

        return selected

    def mark_scanned(self, note_id: str) -> None:
        """
        Marque une note comme scannée.

        Args:
            note_id: ID de la note
        """
        metadata = self.metadata_store.get(note_id)
        if metadata:
            metadata.retouche_last = datetime.now(timezone.utc)
            self.metadata_store.save(metadata)

        self._scans_this_hour += 1
        logger.debug("Marked note as scanned", extra={"note_id": note_id})

    def get_scan_stats(self) -> dict:
        """
        Retourne les statistiques de scan.

        Returns:
            Dict avec scans cette heure, notes en attente, etc.
        """
        self._reset_hourly_counter_if_needed()

        return {
            "scans_this_hour": self._scans_this_hour,
            "hour_start": self._hour_start.isoformat(),
            "max_per_hour": DEFAULT_MAX_PER_HOUR,
        }
```

**Step 4: Update __init__.py**

```python
# Add to src/grimaud/__init__.py
from src.grimaud.scanner import GrimaudScanner, NotePriority

__all__ = [
    # ... existing ...
    "GrimaudScanner",
    "NotePriority",
]
```

**Step 5: Run tests**

Run: `pytest tests/unit/test_grimaud_scanner.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/grimaud/scanner.py tests/unit/test_grimaud_scanner.py
git commit -m "feat(grimaud): add scanner for note prioritization"
```

---

### Task 4: Analyzer (Problem Detection)

**Files:**
- Create: `src/grimaud/analyzer.py`
- Test: `tests/unit/test_grimaud_analyzer.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_grimaud_analyzer.py
"""Tests for Grimaud Analyzer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.grimaud.analyzer import GrimaudAnalyzer, ProblemType
from src.grimaud.models import GrimaudAction, GrimaudActionType


@pytest.fixture
def mock_note_manager():
    """Mock NoteManager avec FAISS."""
    manager = MagicMock()
    return manager


@pytest.fixture
def mock_ai_router():
    """Mock AI Router."""
    router = MagicMock()
    router._call_claude_with_cache = AsyncMock(return_value=('{"actions": []}', {"input_tokens": 100}))
    return router


@pytest.fixture
def analyzer(mock_note_manager, mock_ai_router):
    """Crée un analyzer avec mocks."""
    return GrimaudAnalyzer(
        note_manager=mock_note_manager,
        ai_router=mock_ai_router,
    )


class TestProblemDetection:
    """Tests for local problem detection (no AI)."""

    def test_detect_empty_sections(self, analyzer):
        """Détecte les sections vides."""
        content = """# Note

## Section 1
Contenu présent.

## Section 2

## Section 3
Autre contenu.
"""
        problems = analyzer.detect_local_problems(content, frontmatter={})

        assert any(p.problem_type == ProblemType.EMPTY_SECTION for p in problems)

    def test_detect_broken_links(self, analyzer, mock_note_manager):
        """Détecte les liens wikilink cassés."""
        content = """# Note

Voir [[Note Existante]] et [[Note Inexistante]].
"""
        # Mock: seule "Note Existante" existe
        mock_note_manager.get_note.side_effect = lambda note_id: (
            MagicMock() if note_id == "Note Existante" else None
        )

        problems = analyzer.detect_local_problems(content, frontmatter={})

        broken = [p for p in problems if p.problem_type == ProblemType.BROKEN_LINK]
        assert len(broken) == 1
        assert "Note Inexistante" in broken[0].details

    def test_detect_missing_frontmatter(self, analyzer):
        """Détecte le frontmatter incomplet."""
        content = "# Note sans frontmatter"
        frontmatter = {}  # Empty frontmatter

        problems = analyzer.detect_local_problems(content, frontmatter)

        assert any(p.problem_type == ProblemType.MISSING_FRONTMATTER for p in problems)

    def test_no_problems_for_clean_note(self, analyzer, mock_note_manager):
        """Aucun problème pour une note propre."""
        content = """# Note Propre

## Introduction
Contenu de qualité.

## Détails
Plus de contenu.
"""
        frontmatter = {"title": "Note Propre", "type": "concept"}
        mock_note_manager.get_note.return_value = MagicMock()  # Links exist

        problems = analyzer.detect_local_problems(content, frontmatter)

        assert len(problems) == 0


class TestSimilarityDetection:
    """Tests for FAISS-based similarity detection."""

    def test_detect_similar_notes(self, analyzer, mock_note_manager):
        """Détecte les notes similaires via FAISS."""
        # Mock FAISS search
        mock_note_manager.search_similar.return_value = [
            ("similar-note-1", 0.92),
            ("similar-note-2", 0.87),
            ("different-note", 0.45),
        ]

        similar = analyzer.detect_similar_notes(
            note_id="current-note",
            threshold=0.85,
        )

        assert len(similar) == 2
        assert all(score >= 0.85 for _, score in similar)

    def test_similarity_excludes_self(self, analyzer, mock_note_manager):
        """La détection de similarité exclut la note elle-même."""
        mock_note_manager.search_similar.return_value = [
            ("current-note", 1.0),  # Self
            ("other-note", 0.88),
        ]

        similar = analyzer.detect_similar_notes(
            note_id="current-note",
            threshold=0.85,
        )

        assert len(similar) == 1
        assert similar[0][0] == "other-note"


class TestAIAnalysis:
    """Tests for AI-powered analysis."""

    @pytest.mark.asyncio
    async def test_analyze_with_ai_returns_actions(self, analyzer, mock_ai_router):
        """analyze_with_ai retourne des actions proposées."""
        mock_ai_router._call_claude_with_cache.return_value = (
            '''
            {
                "actions": [
                    {
                        "type": "enrichissement",
                        "confidence": 0.92,
                        "reasoning": "Section Contexte est vide",
                        "new_content": "## Contexte\\n\\nÀ compléter."
                    }
                ]
            }
            ''',
            {"input_tokens": 100, "output_tokens": 50},
        )

        actions = await analyzer.analyze_with_ai(
            note_id="test-note",
            note_title="Test Note",
            content="# Test\n\n## Contexte\n\n",
            problems=["Section vide: Contexte"],
        )

        assert len(actions) == 1
        assert actions[0].action_type == GrimaudActionType.ENRICHISSEMENT
        assert actions[0].confidence >= 0.90

    @pytest.mark.asyncio
    async def test_analyze_with_ai_handles_error(self, analyzer, mock_ai_router):
        """analyze_with_ai gère les erreurs IA."""
        mock_ai_router._call_claude_with_cache.side_effect = Exception("API Error")

        actions = await analyzer.analyze_with_ai(
            note_id="test",
            note_title="Test",
            content="Content",
            problems=["Problem"],
        )

        assert actions == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_grimaud_analyzer.py -v`
Expected: FAIL (module not found)

**Step 3: Implement analyzer**

```python
# src/grimaud/analyzer.py
"""
Analyzer for Grimaud — Problem detection and AI analysis.

Détecte les problèmes dans les notes via:
1. Pré-analyse locale (liens cassés, sections vides, frontmatter)
2. Similarité FAISS (fragmentation, doublons)
3. Analyse IA (enrichissement, restructuration)
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.grimaud.models import GrimaudAction, GrimaudActionType
from src.monitoring.logger import get_logger

logger = get_logger("grimaud.analyzer")

# Seuil de similarité pour détecter la fragmentation
DEFAULT_SIMILARITY_THRESHOLD = 0.85


class ProblemType(str, Enum):
    """Types de problèmes détectables."""
    EMPTY_SECTION = "empty_section"
    BROKEN_LINK = "broken_link"
    MISSING_FRONTMATTER = "missing_frontmatter"
    SIMILAR_NOTE = "similar_note"
    OUTDATED = "outdated"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"


@dataclass
class DetectedProblem:
    """Problème détecté dans une note."""
    problem_type: ProblemType
    severity: str = "medium"  # low, medium, high
    details: str = ""


class GrimaudAnalyzer:
    """
    Analyse les notes pour détecter les problèmes et proposer des actions.
    """

    def __init__(
        self,
        note_manager,  # NoteManager
        ai_router,  # AIRouter
    ):
        """
        Initialise l'analyzer.

        Args:
            note_manager: Gestionnaire des notes (pour FAISS et liens)
            ai_router: Router IA (pour analyse Sonnet)
        """
        self.note_manager = note_manager
        self.ai_router = ai_router

    def detect_local_problems(
        self,
        content: str,
        frontmatter: dict[str, Any],
    ) -> list[DetectedProblem]:
        """
        Détecte les problèmes locaux sans appel IA.

        Args:
            content: Contenu markdown de la note
            frontmatter: Métadonnées frontmatter

        Returns:
            Liste des problèmes détectés
        """
        problems = []

        # 1. Sections vides
        problems.extend(self._detect_empty_sections(content))

        # 2. Liens cassés
        problems.extend(self._detect_broken_links(content))

        # 3. Frontmatter incomplet
        if not frontmatter or "title" not in frontmatter:
            problems.append(DetectedProblem(
                problem_type=ProblemType.MISSING_FRONTMATTER,
                severity="medium",
                details="Frontmatter manquant ou incomplet",
            ))

        # 4. Note trop courte
        word_count = len(content.split())
        if word_count < 50:
            problems.append(DetectedProblem(
                problem_type=ProblemType.TOO_SHORT,
                severity="low",
                details=f"Note trop courte ({word_count} mots)",
            ))

        return problems

    def _detect_empty_sections(self, content: str) -> list[DetectedProblem]:
        """Détecte les sections markdown vides."""
        problems = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if line.startswith("##"):
                # Vérifier si la section suivante est vide
                section_content = []
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("##") or lines[j].startswith("# "):
                        break
                    section_content.append(lines[j].strip())

                # Section vide si que des lignes vides
                if all(not line for line in section_content):
                    section_name = line.lstrip("#").strip()
                    problems.append(DetectedProblem(
                        problem_type=ProblemType.EMPTY_SECTION,
                        severity="medium",
                        details=f"Section vide: {section_name}",
                    ))

        return problems

    def _detect_broken_links(self, content: str) -> list[DetectedProblem]:
        """Détecte les wikilinks cassés."""
        problems = []

        # Trouver tous les wikilinks [[...]]
        wikilinks = re.findall(r'\[\[([^\]]+)\]\]', content)

        for link in wikilinks:
            # Nettoyer le lien (retirer alias après |)
            note_id = link.split("|")[0].strip()

            # Vérifier si la note existe
            try:
                note = self.note_manager.get_note(note_id)
                if note is None:
                    problems.append(DetectedProblem(
                        problem_type=ProblemType.BROKEN_LINK,
                        severity="medium",
                        details=f"Lien cassé: [[{note_id}]]",
                    ))
            except Exception:
                # En cas d'erreur, considérer comme cassé
                problems.append(DetectedProblem(
                    problem_type=ProblemType.BROKEN_LINK,
                    severity="medium",
                    details=f"Lien cassé: [[{note_id}]]",
                ))

        return problems

    def detect_similar_notes(
        self,
        note_id: str,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> list[tuple[str, float]]:
        """
        Détecte les notes similaires via FAISS.

        Args:
            note_id: ID de la note à analyser
            threshold: Seuil de similarité minimum

        Returns:
            Liste de tuples (note_id, score) pour les notes similaires
        """
        try:
            # Récupérer la note
            note = self.note_manager.get_note(note_id)
            if note is None:
                return []

            # Chercher les notes similaires
            results = self.note_manager.search_similar(
                query=note.content,
                k=10,
            )

            # Filtrer par seuil et exclure self
            similar = [
                (nid, score)
                for nid, score in results
                if nid != note_id and score >= threshold
            ]

            return similar

        except Exception as e:
            logger.warning(f"Failed to detect similar notes: {e}")
            return []

    async def analyze_with_ai(
        self,
        note_id: str,
        note_title: str,
        content: str,
        problems: list[str],
    ) -> list[GrimaudAction]:
        """
        Analyse une note avec l'IA pour proposer des actions.

        Args:
            note_id: ID de la note
            note_title: Titre de la note
            content: Contenu de la note
            problems: Liste des problèmes détectés

        Returns:
            Liste d'actions proposées
        """
        prompt = self._build_analysis_prompt(note_title, content, problems)

        try:
            response, _usage = self.ai_router._call_claude_with_cache(
                user_prompt=prompt,
                system_prompt=GRIMAUD_SYSTEM_PROMPT,
                model="sonnet",
                max_tokens=2048,
            )

            # Parser la réponse JSON
            actions = self._parse_ai_response(response, note_id, note_title)
            return actions

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return []

    def _build_analysis_prompt(
        self,
        note_title: str,
        content: str,
        problems: list[str],
    ) -> str:
        """Construit le prompt pour l'analyse IA."""
        problems_text = "\n".join(f"- {p}" for p in problems) if problems else "Aucun"

        return f"""Analyse cette note et propose des actions d'amélioration.

**Titre**: {note_title}

**Problèmes détectés**:
{problems_text}

**Contenu**:
```markdown
{content[:3000]}
```

Réponds en JSON avec le format:
{{
    "actions": [
        {{
            "type": "enrichissement|restructuration|fusion|liaison|metadonnees|archivage",
            "confidence": 0.0-1.0,
            "reasoning": "Explication courte",
            "new_content": "Nouveau contenu si applicable",
            "target_note_id": "ID note cible si fusion/liaison"
        }}
    ]
}}
"""

    def _parse_ai_response(
        self,
        response: str,
        note_id: str,
        note_title: str,
    ) -> list[GrimaudAction]:
        """Parse la réponse IA en actions."""
        actions = []

        try:
            # Extraire le JSON de la réponse
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return []

            data = json.loads(json_match.group())

            for action_data in data.get("actions", []):
                action_type_str = action_data.get("type", "enrichissement")

                # Mapper vers enum
                type_mapping = {
                    "enrichissement": GrimaudActionType.ENRICHISSEMENT,
                    "restructuration": GrimaudActionType.RESTRUCTURATION,
                    "fusion": GrimaudActionType.FUSION,
                    "liaison": GrimaudActionType.LIAISON,
                    "metadonnees": GrimaudActionType.METADONNEES,
                    "archivage": GrimaudActionType.ARCHIVAGE,
                }
                action_type = type_mapping.get(action_type_str, GrimaudActionType.ENRICHISSEMENT)

                action = GrimaudAction(
                    action_type=action_type,
                    note_id=note_id,
                    note_title=note_title,
                    confidence=float(action_data.get("confidence", 0.5)),
                    reasoning=action_data.get("reasoning", ""),
                    new_content=action_data.get("new_content"),
                    target_note_id=action_data.get("target_note_id"),
                )
                actions.append(action)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse AI response: {e}")

        return actions


# System prompt pour l'analyse Grimaud
GRIMAUD_SYSTEM_PROMPT = """Tu es Grimaud, le gardien silencieux du PKM de Johan.

Ta mission: analyser les notes et proposer des actions d'amélioration avec un niveau de confiance.

Règles:
- Confiance >= 0.95 pour les fusions (combiner des notes)
- Confiance >= 0.90 pour les restructurations (réorganiser selon template)
- Confiance >= 0.85 pour les liaisons (créer des wikilinks)
- Confiance >= 0.85 pour les métadonnées (corriger frontmatter)
- Ne jamais modifier le texte original des souvenirs

Réponds toujours en JSON valide.
"""
```

**Step 4: Update __init__.py**

```python
# Add to src/grimaud/__init__.py
from src.grimaud.analyzer import GrimaudAnalyzer, ProblemType, DetectedProblem

__all__ = [
    # ... existing ...
    "GrimaudAnalyzer",
    "ProblemType",
    "DetectedProblem",
]
```

**Step 5: Run tests**

Run: `pytest tests/unit/test_grimaud_analyzer.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/grimaud/analyzer.py tests/unit/test_grimaud_analyzer.py
git commit -m "feat(grimaud): add analyzer for problem detection and AI analysis"
```

---

### Task 5: Executor (Apply Actions + Snapshots)

**Files:**
- Create: `src/grimaud/executor.py`
- Test: `tests/unit/test_grimaud_executor.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_grimaud_executor.py
"""Tests for Grimaud Executor."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.grimaud.executor import GrimaudExecutor
from src.grimaud.history import GrimaudHistoryManager
from src.grimaud.models import GrimaudAction, GrimaudActionType


@pytest.fixture
def mock_note_manager():
    """Mock NoteManager."""
    manager = MagicMock()
    note = MagicMock()
    note.content = "# Original\n\nContent"
    note.metadata = {"title": "Original", "type": "concept"}
    manager.get_note.return_value = note
    return manager


@pytest.fixture
def history_dir():
    """Répertoire temporaire pour snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def executor(mock_note_manager, history_dir):
    """Crée un executor avec mocks."""
    history = GrimaudHistoryManager(snapshots_dir=history_dir)
    return GrimaudExecutor(
        note_manager=mock_note_manager,
        history_manager=history,
    )


class TestGrimaudExecutor:
    """Tests for GrimaudExecutor."""

    def test_execute_creates_snapshot_before_action(self, executor, history_dir):
        """execute crée un snapshot avant d'appliquer l'action."""
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="test-note",
            note_title="Test Note",
            confidence=0.92,
            new_content="# Test\n\n## Nouvelle Section\n\nContenu enrichi.",
        )

        executor.execute(action)

        # Vérifier qu'un snapshot a été créé
        snapshots = list(history_dir.glob("*.json.gz"))
        assert len(snapshots) == 1

    def test_execute_updates_note_content(self, executor, mock_note_manager):
        """execute met à jour le contenu de la note."""
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="test-note",
            note_title="Test Note",
            confidence=0.92,
            new_content="# Test\n\n## Enrichi\n\nNouveau contenu.",
        )

        executor.execute(action)

        mock_note_manager.update_note.assert_called_once()
        call_args = mock_note_manager.update_note.call_args
        assert "Nouveau contenu" in call_args[1]["content"]

    def test_execute_marks_action_as_applied(self, executor):
        """execute marque l'action comme appliquée."""
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="test-note",
            note_title="Test Note",
            confidence=0.92,
            new_content="Nouveau",
        )

        assert action.applied is False

        executor.execute(action)

        assert action.applied is True
        assert action.applied_at is not None

    def test_rollback_restores_content(self, executor, mock_note_manager, history_dir):
        """rollback restaure le contenu original."""
        # D'abord exécuter une action
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="test-note",
            note_title="Test Note",
            confidence=0.92,
            new_content="Nouveau contenu",
        )
        executor.execute(action)

        # Récupérer le snapshot ID
        snapshots = list(history_dir.glob("*.json.gz"))
        snapshot_id = snapshots[0].stem.replace(".json", "")

        # Rollback
        result = executor.rollback(snapshot_id)

        assert result is True
        # Le contenu original devrait être restauré
        mock_note_manager.update_note.assert_called()

    def test_execute_fusion_moves_source_to_trash(self, executor, mock_note_manager):
        """execute fusion déplace la note source vers la corbeille."""
        action = GrimaudAction(
            action_type=GrimaudActionType.FUSION,
            note_id="source-note",
            note_title="Source Note",
            target_note_id="target-note",
            target_note_title="Target Note",
            confidence=0.96,
        )

        executor.execute(action)

        # La source devrait être déplacée vers la corbeille
        mock_note_manager.move_to_trash.assert_called_once_with("source-note")

    def test_dry_run_does_not_modify(self, executor, mock_note_manager, history_dir):
        """dry_run ne modifie rien."""
        action = GrimaudAction(
            action_type=GrimaudActionType.ENRICHISSEMENT,
            note_id="test-note",
            note_title="Test Note",
            confidence=0.92,
            new_content="Nouveau",
        )

        result = executor.execute(action, dry_run=True)

        assert result is True
        mock_note_manager.update_note.assert_not_called()
        assert len(list(history_dir.glob("*.json.gz"))) == 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_grimaud_executor.py -v`
Expected: FAIL (module not found)

**Step 3: Implement executor**

```python
# src/grimaud/executor.py
"""
Executor for Grimaud — Apply actions with snapshots.

Applique les actions Grimaud sur les notes avec création de snapshots
pour permettre le rollback.
"""

from datetime import datetime, timezone
from typing import Optional

from src.grimaud.history import GrimaudHistoryManager
from src.grimaud.models import GrimaudAction, GrimaudActionType, GrimaudSnapshot
from src.monitoring.logger import get_logger

logger = get_logger("grimaud.executor")


class GrimaudExecutor:
    """
    Exécute les actions Grimaud avec gestion des snapshots.

    Chaque action crée un snapshot avant modification pour permettre le rollback.
    """

    def __init__(
        self,
        note_manager,  # NoteManager
        history_manager: GrimaudHistoryManager,
    ):
        """
        Initialise l'executor.

        Args:
            note_manager: Gestionnaire des notes
            history_manager: Gestionnaire des snapshots
        """
        self.note_manager = note_manager
        self.history_manager = history_manager

    def execute(
        self,
        action: GrimaudAction,
        dry_run: bool = False,
    ) -> bool:
        """
        Exécute une action Grimaud.

        Args:
            action: Action à exécuter
            dry_run: Si True, ne modifie rien (simulation)

        Returns:
            True si succès, False sinon
        """
        logger.info(
            "Executing action",
            extra={
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "note_id": action.note_id,
                "dry_run": dry_run,
            },
        )

        if dry_run:
            return True

        # 1. Récupérer la note
        note = self.note_manager.get_note(action.note_id)
        if note is None:
            logger.error(f"Note not found: {action.note_id}")
            return False

        # 2. Créer un snapshot avant modification
        snapshot = self._create_snapshot(action, note)
        self.history_manager.save_snapshot(snapshot)

        # 3. Appliquer l'action selon le type
        try:
            if action.action_type == GrimaudActionType.ENRICHISSEMENT:
                self._apply_enrichissement(action, note)
            elif action.action_type == GrimaudActionType.RESTRUCTURATION:
                self._apply_restructuration(action, note)
            elif action.action_type == GrimaudActionType.FUSION:
                self._apply_fusion(action, note)
            elif action.action_type == GrimaudActionType.LIAISON:
                self._apply_liaison(action, note)
            elif action.action_type == GrimaudActionType.METADONNEES:
                self._apply_metadonnees(action, note)
            elif action.action_type == GrimaudActionType.ARCHIVAGE:
                self._apply_archivage(action, note)
            else:
                logger.warning(f"Unknown action type: {action.action_type}")
                return False

            # 4. Marquer comme appliquée
            action.applied = True
            action.applied_at = datetime.now(timezone.utc)

            logger.info(
                "Action executed successfully",
                extra={"action_id": action.action_id, "snapshot_id": snapshot.snapshot_id},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to execute action: {e}", exc_info=True)
            return False

    def _create_snapshot(self, action: GrimaudAction, note) -> GrimaudSnapshot:
        """Crée un snapshot de la note avant modification."""
        # Extraire le frontmatter
        frontmatter = {}
        if hasattr(note, "metadata") and note.metadata:
            frontmatter = dict(note.metadata)

        return GrimaudSnapshot(
            note_id=action.note_id,
            note_title=action.note_title,
            action_type=action.action_type,
            action_detail=action.reasoning,
            confidence=action.confidence,
            content_before=note.content,
            frontmatter_before=frontmatter,
            triggered_by="grimaud_auto",
        )

    def _apply_enrichissement(self, action: GrimaudAction, note) -> None:
        """Applique un enrichissement de contenu."""
        if action.new_content:
            self.note_manager.update_note(
                note_id=action.note_id,
                content=action.new_content,
            )

    def _apply_restructuration(self, action: GrimaudAction, note) -> None:
        """Applique une restructuration."""
        if action.new_content:
            self.note_manager.update_note(
                note_id=action.note_id,
                content=action.new_content,
            )

    def _apply_fusion(self, action: GrimaudAction, note) -> None:
        """Applique une fusion de notes."""
        if not action.target_note_id:
            raise ValueError("Fusion requires target_note_id")

        # Récupérer la note cible
        target = self.note_manager.get_note(action.target_note_id)
        if target is None:
            raise ValueError(f"Target note not found: {action.target_note_id}")

        # Fusionner le contenu (ajouter à la fin de la cible)
        merged_content = f"{target.content}\n\n---\n\n## Fusionné depuis {action.note_title}\n\n{note.content}"

        self.note_manager.update_note(
            note_id=action.target_note_id,
            content=merged_content,
        )

        # Déplacer la source vers la corbeille
        self.note_manager.move_to_trash(action.note_id)

    def _apply_liaison(self, action: GrimaudAction, note) -> None:
        """Applique une liaison (wikilink)."""
        if not action.target_note_id:
            raise ValueError("Liaison requires target_note_id")

        # Ajouter le wikilink si pas déjà présent
        link = f"[[{action.target_note_id}]]"
        if link not in note.content:
            # Ajouter dans une section "Voir aussi"
            updated = note.content
            if "## Voir aussi" not in updated:
                updated += f"\n\n## Voir aussi\n\n- {link}"
            else:
                # Ajouter à la section existante
                updated = updated.replace("## Voir aussi\n", f"## Voir aussi\n- {link}\n")

            self.note_manager.update_note(
                note_id=action.note_id,
                content=updated,
            )

    def _apply_metadonnees(self, action: GrimaudAction, note) -> None:
        """Applique une correction de métadonnées."""
        # TODO: Implémenter la mise à jour du frontmatter
        pass

    def _apply_archivage(self, action: GrimaudAction, note) -> None:
        """Marque une note comme archivée."""
        # Mettre à jour les métadonnées pour marquer comme obsolète
        # TODO: Utiliser metadata_store.update() avec obsolete_flag=True
        pass

    def rollback(self, snapshot_id: str) -> bool:
        """
        Restaure une note depuis un snapshot.

        Args:
            snapshot_id: ID du snapshot à restaurer

        Returns:
            True si succès, False sinon
        """
        snapshot = self.history_manager.get_snapshot(snapshot_id)
        if snapshot is None:
            logger.warning(f"Snapshot not found: {snapshot_id}")
            return False

        try:
            # Restaurer le contenu
            self.note_manager.update_note(
                note_id=snapshot.note_id,
                content=snapshot.content_before,
            )

            # Supprimer le snapshot après restauration
            self.history_manager.delete_snapshot(snapshot_id)

            logger.info(
                "Rollback successful",
                extra={"snapshot_id": snapshot_id, "note_id": snapshot.note_id},
            )
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            return False
```

**Step 4: Update __init__.py**

```python
# Add to src/grimaud/__init__.py
from src.grimaud.executor import GrimaudExecutor

__all__ = [
    # ... existing ...
    "GrimaudExecutor",
]
```

**Step 5: Run tests**

Run: `pytest tests/unit/test_grimaud_executor.py -v`
Expected: All tests PASS (may need to mock move_to_trash)

**Step 6: Commit**

```bash
git add src/grimaud/executor.py tests/unit/test_grimaud_executor.py
git commit -m "feat(grimaud): add executor for applying actions with snapshots"
```

---

## Phase 2: API Endpoints

### Task 6: Grimaud API Router

**Files:**
- Create: `src/frontin/api/routers/grimaud.py`
- Create: `src/frontin/api/services/grimaud_service.py`
- Modify: `src/frontin/api/routers/__init__.py`
- Test: `tests/api/test_grimaud_api.py`

*[Détails similaires pour l'API - à implémenter après Phase 1 backend core]*

---

## Phase 3: Frontend (Dashboard)

### Task 7: Migrate Retouche Components

**Files:**
- Create: `web/src/lib/components/grimaud/`
- Modify: `web/src/routes/memoires/grimaud/+page.svelte`

*[Détails UI - à implémenter après API]*

---

## Verification Checklist

Après chaque phase, vérifier:

```bash
# Backend tests
pytest tests/unit/test_grimaud*.py -v

# Lint
ruff check src/grimaud/

# Types (si applicable)
cd web && npm run check
```

---

## Documentation Updates

Après implémentation complète:

1. `ARCHITECTURE.md` - Ajouter section Grimaud
2. `CLAUDE.md` - Mettre à jour glossaire et liste des valets
3. `docs/user-guide/grimaud.md` - Guide utilisateur

---

*Plan créé le 27 janvier 2026*
