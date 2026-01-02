"""
Sganarelle Pattern Store

Gère le stockage, la récupération et la mise à jour des patterns appris.
Les patterns représentent des comportements récurrents qui peuvent être
utilisés pour suggérer des actions futures.

Thread-safe avec persistence sur disque.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from src.core.events.universal_event import PerceivedEvent, now_utc
from src.figaro.actions.base import Action
from src.sganarelle.constants import (
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MIN_OCCURRENCES,
    DEFAULT_MIN_SUCCESS_RATE,
    PATTERN_CONFIDENCE_FAILURE_PENALTY,
    PATTERN_CONFIDENCE_SUCCESS_BOOST,
    PATTERN_PRUNE_MIN_OCCURRENCES_MULTIPLIER,
    PATTERN_PRUNE_SUCCESS_RATE_THRESHOLD,
    RELEVANCE_BASE_WEIGHT,
    RELEVANCE_OCCURRENCE_MULTIPLIER,
    RELEVANCE_OCCURRENCE_WEIGHT,
    RELEVANCE_RECENCY_MIN_FACTOR,
    RELEVANCE_RECENCY_WEIGHT,
)
from src.sganarelle.types import Pattern, PatternType

logger = logging.getLogger(__name__)


class PatternStoreError(Exception):
    """Erreur dans le pattern store"""
    pass


class PatternStore:
    """
    Gestionnaire de patterns appris

    Store et récupère les patterns de manière thread-safe.
    Supporte la persistence sur disque au format JSON.

    Thread-safe: Utilise verrous pour accès concurrent.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        min_occurrences: int = DEFAULT_MIN_OCCURRENCES,
        min_success_rate: float = DEFAULT_MIN_SUCCESS_RATE,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
        auto_save: bool = True
    ):
        """
        Initialize pattern store

        Args:
            storage_path: Chemin fichier JSON pour persistence (None = memory only)
            min_occurrences: Occurrences minimales pour pattern valide
            min_success_rate: Success rate minimal pour suggestions (0-1)
            max_age_days: Age max pattern (jours) avant pruning
            auto_save: Si True, save après chaque modification

        Raises:
            ValueError: Si paramètres invalides
        """
        if min_occurrences < 1:
            raise ValueError(f"min_occurrences doit être >= 1, got {min_occurrences}")
        if not (0 <= min_success_rate <= 1):
            raise ValueError(
                f"min_success_rate doit être 0-1, got {min_success_rate}"
            )
        if max_age_days < 1:
            raise ValueError(f"max_age_days doit être >= 1, got {max_age_days}")

        self.storage_path = storage_path
        self.min_occurrences = min_occurrences
        self.min_success_rate = min_success_rate
        self.max_age_days = max_age_days
        self.auto_save = auto_save

        # Thread-safe storage
        self._patterns: dict[str, Pattern] = {}
        self._lock = Lock()

        # Load existing patterns
        if storage_path and storage_path.exists():
            self._load_from_disk()

        logger.info(
            "PatternStore initialized",
            extra={
                "storage_path": str(storage_path) if storage_path else "memory",
                "min_occurrences": min_occurrences,
                "min_success_rate": min_success_rate,
                "patterns_loaded": len(self._patterns)
            }
        )

    def add_pattern(self, pattern: Pattern) -> None:
        """
        Ajoute un nouveau pattern

        Args:
            pattern: Pattern à ajouter

        Raises:
            PatternStoreError: Si pattern déjà existe
        """
        with self._lock:
            if pattern.pattern_id in self._patterns:
                raise PatternStoreError(
                    f"Pattern {pattern.pattern_id} already exists"
                )

            self._patterns[pattern.pattern_id] = pattern

            logger.debug(
                "Pattern added",
                extra={
                    "pattern_id": pattern.pattern_id,
                    "type": pattern.pattern_type.value,
                    "confidence": pattern.confidence
                }
            )

            if self.auto_save:
                self._save_to_disk()

    def update_pattern(
        self,
        pattern_id: str,
        success: bool,
        confidence_adjustment: Optional[float] = None
    ) -> Pattern:
        """
        Met à jour un pattern avec nouveau résultat

        Args:
            pattern_id: ID du pattern
            success: Si l'application du pattern a réussi
            confidence_adjustment: Ajustement confiance (optionnel)

        Returns:
            Pattern mis à jour

        Raises:
            PatternStoreError: Si pattern non trouvé
        """
        with self._lock:
            if pattern_id not in self._patterns:
                raise PatternStoreError(f"Pattern {pattern_id} not found")

            old_pattern = self._patterns[pattern_id]

            # Calculate new success rate
            total_attempts = old_pattern.occurrences + 1
            old_successes = int(old_pattern.success_rate * old_pattern.occurrences)
            new_successes = old_successes + (1 if success else 0)
            new_success_rate = new_successes / total_attempts

            # Adjust confidence
            new_confidence = old_pattern.confidence
            if confidence_adjustment is not None:
                new_confidence = max(0.0, min(1.0, new_confidence + confidence_adjustment))
            elif success:
                # Small confidence boost on success
                new_confidence = min(1.0, new_confidence * PATTERN_CONFIDENCE_SUCCESS_BOOST)
            else:
                # Larger confidence penalty on failure
                new_confidence = new_confidence * PATTERN_CONFIDENCE_FAILURE_PENALTY

            # Create updated pattern (immutable)
            new_pattern = Pattern(
                pattern_id=old_pattern.pattern_id,
                pattern_type=old_pattern.pattern_type,
                conditions=old_pattern.conditions,
                suggested_actions=old_pattern.suggested_actions,
                confidence=new_confidence,
                success_rate=new_success_rate,
                occurrences=total_attempts,
                last_seen=now_utc(),
                created_at=old_pattern.created_at
            )

            self._patterns[pattern_id] = new_pattern

            logger.debug(
                "Pattern updated",
                extra={
                    "pattern_id": pattern_id,
                    "success": success,
                    "new_success_rate": new_success_rate,
                    "new_confidence": new_confidence,
                    "occurrences": total_attempts
                }
            )

            if self.auto_save:
                self._save_to_disk()

            return new_pattern

    def find_matching_patterns(
        self,
        event: PerceivedEvent,
        context: Optional[dict[str, Any]] = None,
        min_confidence: Optional[float] = None
    ) -> list[Pattern]:
        """
        Trouve les patterns qui matchent l'événement et contexte

        Args:
            event: Événement à matcher
            context: Contexte additionnel (optionnel)
            min_confidence: Confiance minimale (override default)

        Returns:
            Liste de patterns matchant, triés par pertinence
        """
        if context is None:
            context = {}

        min_conf = min_confidence if min_confidence is not None else self.min_success_rate

        # Copy patterns list while holding lock (thread-safe)
        with self._lock:
            patterns_snapshot = list(self._patterns.values())

        # Work on snapshot without lock (patterns are immutable)
        matching = []
        for pattern in patterns_snapshot:
            # Check minimum requirements
            if pattern.occurrences < self.min_occurrences:
                continue
            if pattern.success_rate < min_conf:
                continue

            # Check if pattern matches event and context
            if pattern.matches(event, context):
                matching.append(pattern)

        # Sort by relevance score
        matching.sort(key=lambda p: self._calculate_relevance_score(p), reverse=True)

        logger.debug(
            "Found matching patterns",
            extra={
                "event_id": event.event_id,
                "matches_found": len(matching),
                "total_patterns": len(self._patterns)
            }
        )

        return matching

    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """
        Récupère un pattern par ID

        Args:
            pattern_id: ID du pattern

        Returns:
            Pattern ou None si non trouvé
        """
        with self._lock:
            return self._patterns.get(pattern_id)

    def get_all_patterns(
        self,
        pattern_type: Optional[PatternType] = None,
        min_confidence: Optional[float] = None
    ) -> list[Pattern]:
        """
        Récupère tous les patterns (avec filtres optionnels)

        Args:
            pattern_type: Filtrer par type (optionnel)
            min_confidence: Confiance minimale (optionnel)

        Returns:
            Liste de patterns
        """
        with self._lock:
            patterns = list(self._patterns.values())

        # Apply filters
        if pattern_type is not None:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        if min_confidence is not None:
            patterns = [p for p in patterns if p.confidence >= min_confidence]

        return patterns

    def prune_old_patterns(self) -> int:
        """
        Supprime les patterns trop vieux ou inefficaces

        Returns:
            Nombre de patterns supprimés
        """
        cutoff_date = now_utc() - timedelta(days=self.max_age_days)
        removed = 0

        with self._lock:
            to_remove = []

            for pattern_id, pattern in self._patterns.items():
                # Remove if too old
                if pattern.last_seen < cutoff_date:
                    to_remove.append(pattern_id)
                    continue

                # Remove if success rate too low (and enough data)
                if (pattern.occurrences >= self.min_occurrences * PATTERN_PRUNE_MIN_OCCURRENCES_MULTIPLIER and
                    pattern.success_rate < self.min_success_rate * PATTERN_PRUNE_SUCCESS_RATE_THRESHOLD):
                    to_remove.append(pattern_id)

            # Remove
            for pattern_id in to_remove:
                del self._patterns[pattern_id]
                removed += 1

            logger.info(
                "Pruned old patterns",
                extra={
                    "removed": removed,
                    "remaining": len(self._patterns)
                }
            )

            if removed > 0 and self.auto_save:
                self._save_to_disk()

        return removed

    def get_stats(self) -> dict[str, Any]:
        """
        Statistiques sur le pattern store

        Returns:
            Dict avec statistiques
        """
        with self._lock:
            patterns = list(self._patterns.values())

        if not patterns:
            return {
                "total_patterns": 0,
                "by_type": {},
                "avg_confidence": 0.0,
                "avg_success_rate": 0.0,
                "avg_occurrences": 0.0
            }

        by_type = {}
        for pattern in patterns:
            ptype = pattern.pattern_type.value
            by_type[ptype] = by_type.get(ptype, 0) + 1

        return {
            "total_patterns": len(patterns),
            "by_type": by_type,
            "avg_confidence": sum(p.confidence for p in patterns) / len(patterns),
            "avg_success_rate": sum(p.success_rate for p in patterns) / len(patterns),
            "avg_occurrences": sum(p.occurrences for p in patterns) / len(patterns),
            "min_occurrences": min(p.occurrences for p in patterns),
            "max_occurrences": max(p.occurrences for p in patterns)
        }

    def save(self) -> None:
        """Force save to disk"""
        if self.storage_path:
            self._save_to_disk()

    def clear(self) -> None:
        """Clear all patterns (for testing)"""
        with self._lock:
            self._patterns.clear()

            logger.warning("All patterns cleared")

            if self.auto_save:
                self._save_to_disk()

    # Private methods

    def _calculate_relevance_score(self, pattern: Pattern) -> float:
        """
        Calculate relevance score for ranking

        Combines confidence, success rate, and recency.

        Returns:
            Score 0-1
        """
        # Base score from confidence and success rate
        base_score = (pattern.confidence + pattern.success_rate) / 2

        # Recency bonus (patterns used recently are more relevant)
        age_days = (now_utc() - pattern.last_seen).days
        recency_factor = max(RELEVANCE_RECENCY_MIN_FACTOR, 1.0 - (age_days / self.max_age_days))

        # Occurrence bonus (more data = more reliable)
        occurrence_factor = min(1.0, pattern.occurrences / (self.min_occurrences * RELEVANCE_OCCURRENCE_MULTIPLIER))

        # Weighted combination
        relevance = (
            base_score * RELEVANCE_BASE_WEIGHT +
            recency_factor * RELEVANCE_RECENCY_WEIGHT +
            occurrence_factor * RELEVANCE_OCCURRENCE_WEIGHT
        )

        return max(0.0, min(1.0, relevance))

    def _save_to_disk(self) -> None:
        """Save patterns to disk (JSON)"""
        if not self.storage_path:
            return

        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert patterns to dict
            data = {
                "version": "1.0",
                "timestamp": now_utc().isoformat(),
                "patterns": [
                    pattern.to_dict()
                    for pattern in self._patterns.values()
                ]
            }

            # Write atomically (write to temp, then rename)
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.storage_path)

            logger.debug(
                "Patterns saved to disk",
                extra={
                    "path": str(self.storage_path),
                    "count": len(self._patterns)
                }
            )

        except Exception as e:
            logger.error(
                "Failed to save patterns",
                extra={"path": str(self.storage_path), "error": str(e)},
                exc_info=True
            )

    def _load_from_disk(self) -> None:
        """Load patterns from disk (JSON)"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, encoding='utf-8') as f:
                data = json.load(f)

            # Parse patterns
            for pattern_data in data.get("patterns", []):
                pattern = self._pattern_from_dict(pattern_data)
                self._patterns[pattern.pattern_id] = pattern

            logger.info(
                "Patterns loaded from disk",
                extra={
                    "path": str(self.storage_path),
                    "count": len(self._patterns)
                }
            )

        except Exception as e:
            logger.error(
                "Failed to load patterns",
                extra={"path": str(self.storage_path), "error": str(e)},
                exc_info=True
            )

    def _pattern_from_dict(self, data: dict[str, Any]) -> Pattern:
        """Reconstruct Pattern from dict"""
        return Pattern(
            pattern_id=data["pattern_id"],
            pattern_type=PatternType(data["pattern_type"]),
            conditions=data["conditions"],
            suggested_actions=data["suggested_actions"],
            confidence=data["confidence"],
            success_rate=data["success_rate"],
            occurrences=data["occurrences"],
            last_seen=datetime.fromisoformat(data["last_seen"]),
            created_at=datetime.fromisoformat(data["created_at"])
        )


def create_pattern_from_execution(
    event: PerceivedEvent,
    actions: list[Action],
    context: dict[str, Any],
    success: bool,
    initial_confidence: float = 0.6
) -> Pattern:
    """
    Helper pour créer un pattern depuis une exécution réussie

    Args:
        event: Événement traité
        actions: Actions exécutées
        context: Contexte de l'exécution
        success: Si l'exécution a réussi
        initial_confidence: Confiance initiale

    Returns:
        Nouveau Pattern
    """
    # Build conditions from event
    conditions = {
        "event_type": event.event_type.value,
        "min_urgency": event.urgency.value
    }

    # Add entity requirements if present
    if event.entities:
        conditions["required_entities"] = [e.type for e in event.entities]

    # Add context conditions (e.g., time of day)
    if "time_of_day" in context:
        conditions["context"] = {"time_of_day": context["time_of_day"]}

    # Extract action types
    suggested_actions = [action.action_type for action in actions]

    # Generate pattern ID
    pattern_id = f"pattern_{event.event_type.value}_{hash(str(conditions)) % 10000}"

    return Pattern(
        pattern_id=pattern_id,
        pattern_type=PatternType.CONTEXT_TRIGGER,
        conditions=conditions,
        suggested_actions=suggested_actions,
        confidence=initial_confidence,
        success_rate=1.0 if success else 0.0,
        occurrences=1,
        last_seen=now_utc(),
        created_at=now_utc()
    )
