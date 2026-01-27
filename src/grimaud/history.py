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
                        extra={
                            "snapshot_id": data["snapshot_id"],
                            "age_days": (datetime.now(timezone.utc) - timestamp).days,
                        },
                    )
            except (json.JSONDecodeError, OSError, KeyError):
                continue

        if purged > 0:
            logger.info(
                "Purged old snapshots",
                extra={"count": purged, "max_age_days": max_age_days},
            )

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
        by_action: dict[str, int] = {}
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
