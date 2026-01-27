"""
Scanner for Grimaud — Note selection and prioritization.

Selectionne les notes a analyser en fonction de leur priorite.
Score de priorite = (importance x 3) + (anciennete_scan x 2) + (problemes x 1)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.monitoring.logger import get_logger
from src.passepartout.note_types import ImportanceLevel

if TYPE_CHECKING:
    from src.passepartout.note_manager import Note, NoteManager
    from src.passepartout.note_metadata import NoteMetadataStore

logger = get_logger("grimaud.scanner")

# Configuration throttling
DEFAULT_MAX_PER_HOUR = 10
DEFAULT_MIN_AGE_HOURS = 24 * 7  # 7 jours minimum entre scans


@dataclass
class NotePriority:
    """Calcul de priorite d'une note pour le scan."""

    importance: int  # 1-10
    days_since_scan: int  # max 30
    problems: int  # count

    @property
    def score(self) -> float:
        """
        Score de priorite (plus eleve = plus prioritaire).

        Formule: (importance x 3) + (days_since_scan x 2) + (problems x 1)
        Le days_since_scan est plafonne a 30 pour eviter que les anciennes notes
        dominent indefiniment.
        """
        return (self.importance * 3) + (min(self.days_since_scan, 30) * 2) + (self.problems * 1)


# Mapping importance vers score
IMPORTANCE_SCORES: dict[ImportanceLevel, int] = {
    ImportanceLevel.CRITICAL: 10,
    ImportanceLevel.HIGH: 7,
    ImportanceLevel.NORMAL: 4,
    ImportanceLevel.LOW: 2,
    ImportanceLevel.ARCHIVE: 1,
}


class GrimaudScanner:
    """
    Selectionne les notes a scanner et gere le throttling.

    Priorise les notes selon:
    - Importance (liee a projet actif)
    - Anciennete du dernier scan
    - Problemes detectes (pre-analyse rapide)
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
            metadata_store: Store des metadonnees
        """
        self.note_manager = note_manager
        self.metadata_store = metadata_store

        # Throttling state
        self._scans_this_hour = 0
        self._hour_start = datetime.now(timezone.utc)

    def _reset_hourly_counter_if_needed(self) -> None:
        """Remet a zero le compteur horaire si necessaire."""
        now = datetime.now(timezone.utc)
        if (now - self._hour_start).total_seconds() >= 3600:
            self._scans_this_hour = 0
            self._hour_start = now

    def should_scan(self, max_per_hour: int = DEFAULT_MAX_PER_HOUR) -> bool:
        """
        Verifie si un scan est autorise (throttling).

        Args:
            max_per_hour: Maximum de scans par heure

        Returns:
            True si scan autorise
        """
        self._reset_hourly_counter_if_needed()
        return self._scans_this_hour < max_per_hour

    def _calculate_priority(self, note_id: str) -> NotePriority | None:
        """
        Calcule la priorite d'une note.

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
        if hasattr(importance_level, "value"):
            try:
                importance_level = ImportanceLevel(importance_level.value)
            except ValueError:
                importance_level = ImportanceLevel.NORMAL
        importance = IMPORTANCE_SCORES.get(importance_level, 4)

        # Anciennete du scan
        last_scan = metadata.retouche_last
        if last_scan is None:
            days_since_scan = 30  # Jamais scanne = max priorite
        else:
            if last_scan.tzinfo is None:
                last_scan = last_scan.replace(tzinfo=timezone.utc)
            days_since_scan = (datetime.now(timezone.utc) - last_scan).days

        # TODO: Ajouter detection problemes rapide (liens casses, sections vides)
        problems = 0

        return NotePriority(
            importance=importance,
            days_since_scan=days_since_scan,
            problems=problems,
        )

    def select_next_note(
        self,
        min_age_hours: int = DEFAULT_MIN_AGE_HOURS,
    ) -> Note | None:
        """
        Selectionne la prochaine note a scanner.

        Args:
            min_age_hours: Age minimum depuis dernier scan (heures)

        Returns:
            Note a scanner ou None si aucune disponible
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)
        candidates: list[tuple[Note, NotePriority]] = []

        # Lister toutes les notes
        try:
            all_notes = self.note_manager.get_all_notes()
        except Exception as e:
            logger.error(f"Failed to list notes: {e}")
            return None

        for note in all_notes:
            note_id = note.note_id
            metadata = self.metadata_store.get(note_id)

            if metadata is None:
                # Note sans metadonnees = priorite haute
                candidates.append(
                    (note, NotePriority(importance=5, days_since_scan=30, problems=0))
                )
                continue

            # Verifier age minimum
            last_scan = metadata.retouche_last
            if last_scan is not None:
                if last_scan.tzinfo is None:
                    last_scan = last_scan.replace(tzinfo=timezone.utc)
                if last_scan > cutoff:
                    continue  # Trop recent

            priority = self._calculate_priority(note_id)
            if priority:
                candidates.append((note, priority))

        if not candidates:
            logger.debug("No notes available for scanning")
            return None

        # Trier par score decroissant
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

    def mark_scanned(self, note_id: str) -> bool:
        """
        Marque une note comme scannee.

        Args:
            note_id: ID de la note

        Returns:
            True si la note a ete marquee, False si metadata inexistante
        """
        metadata = self.metadata_store.get(note_id)
        if metadata is None:
            logger.warning("Cannot mark note as scanned: no metadata", extra={"note_id": note_id})
            return False

        metadata.retouche_last = datetime.now(timezone.utc)
        self.metadata_store.save(metadata)
        self._scans_this_hour += 1
        logger.debug("Marked note as scanned", extra={"note_id": note_id})
        return True

    def get_scan_stats(self) -> dict[str, Any]:
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
