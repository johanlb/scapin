"""Models for Grimaud — PKM Guardian."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class GrimaudActionType(str, Enum):
    """Types d'actions Grimaud."""

    FUSION = "fusion"  # Combiner 2+ notes
    LIAISON = "liaison"  # Creer wikilink entre notes
    RESTRUCTURATION = "restructuration"  # Reorganiser selon template
    ENRICHISSEMENT = "enrichissement"  # Completer sections vides
    ENRICHISSEMENT_WEB = "enrichissement_web"  # Ajouter infos web
    METADONNEES = "metadonnees"  # Corriger frontmatter
    ARCHIVAGE = "archivage"  # Marquer obsolete


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
    """Action proposee par Grimaud."""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: GrimaudActionType = GrimaudActionType.ENRICHISSEMENT
    note_id: str = ""
    note_title: str = ""
    confidence: float = 0.0
    reasoning: str = ""

    # Champs optionnels selon type d'action
    target_note_id: str | None = None
    target_note_title: str | None = None
    content_diff: str | None = None
    new_content: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    applied: bool = False
    applied_at: datetime | None = None

    def should_auto_apply(self) -> bool:
        """Verifie si l'action doit etre appliquee automatiquement."""
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GrimaudAction":
        """Cree depuis un dictionnaire."""
        return cls(
            action_id=data["action_id"],
            action_type=GrimaudActionType(data["action_type"]),
            note_id=data["note_id"],
            note_title=data["note_title"],
            confidence=float(data["confidence"]),
            reasoning=data["reasoning"],
            target_note_id=data.get("target_note_id"),
            target_note_title=data.get("target_note_title"),
            content_diff=data.get("content_diff"),
            new_content=data.get("new_content"),
            created_at=datetime.fromisoformat(data["created_at"]),
            applied=data["applied"],
            applied_at=datetime.fromisoformat(data["applied_at"]) if data.get("applied_at") else None,
        )


@dataclass
class GrimaudSnapshot:
    """Snapshot d'une note avant modification."""

    snapshot_id: str = field(
        default_factory=lambda: f"snap_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    )
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
        """Cree depuis un dictionnaire."""
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
    """Resultat d'un scan de note."""

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
        """Retourne True si des problemes ont ete detectes."""
        return len(self.problems_detected) > 0


@dataclass
class GrimaudStats:
    """Statistiques globales Grimaud."""

    total_notes: int = 0
    health_score: float = 0.0  # 0-100%
    pending_actions: int = 0
    fusions_this_month: int = 0
    enrichments_this_month: int = 0
    last_scan_at: datetime | None = None
    notes_scanned_today: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dictionnaire pour API."""
        return {
            "total_notes": self.total_notes,
            "health_score": self.health_score,
            "pending_actions": self.pending_actions,
            "fusions_this_month": self.fusions_this_month,
            "enrichments_this_month": self.enrichments_this_month,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "notes_scanned_today": self.notes_scanned_today,
        }
