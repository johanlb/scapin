"""
Sganarelle Knowledge Updater

Applique les mises à jour de connaissances à la base PKM (Passepartout)
en fonction de l'apprentissage depuis les décisions et le feedback.

Thread-safe avec transactions atomiques.
"""

import logging
from collections import deque
from threading import Lock
from typing import Any, Optional

from src.core.events.universal_event import PerceivedEvent, now_utc
from src.core.memory.working_memory import WorkingMemory
from src.figaro.actions.base import Action
from src.sganarelle.types import FeedbackAnalysis, KnowledgeUpdate, UpdateType

logger = logging.getLogger(__name__)


class KnowledgeUpdateError(Exception):
    """Erreur lors d'une mise à jour de connaissances"""
    pass


class KnowledgeUpdater:
    """
    Gestionnaire de mises à jour de la base de connaissances

    Applique les KnowledgeUpdate au PKM de manière atomique et thread-safe.
    Gère les conflits, la validation, et le rollback en cas d'erreur.

    Thread-safe: Utilise verrous pour accès concurrent aux notes.
    """

    def __init__(
        self,
        min_confidence_threshold: float = 0.7,
        auto_apply: bool = False,
        max_updates_per_cycle: int = 50
    ):
        """
        Initialize knowledge updater

        Args:
            min_confidence_threshold: Confiance minimale pour auto-apply (0-1)
            auto_apply: Si True, applique automatiquement updates > threshold
            max_updates_per_cycle: Maximum updates par cycle (protection)

        Raises:
            ValueError: Si paramètres invalides
        """
        if not (0 <= min_confidence_threshold <= 1):
            raise ValueError(
                f"min_confidence_threshold doit être 0-1, got {min_confidence_threshold}"
            )
        if max_updates_per_cycle < 1:
            raise ValueError(
                f"max_updates_per_cycle doit être >= 1, got {max_updates_per_cycle}"
            )

        self.min_confidence_threshold = min_confidence_threshold
        self.auto_apply = auto_apply
        self.max_updates_per_cycle = max_updates_per_cycle

        # Placeholder for future Passepartout integration
        self._note_manager = None
        self._entity_manager = None

        # Thread-safe tracking with memory limit
        self._lock = Lock()
        self._applied_updates: deque = deque(maxlen=1000)  # Keep last 1000
        self._failed_updates: deque = deque(maxlen=1000)  # Keep last 1000

        logger.info(
            "KnowledgeUpdater initialized",
            extra={
                "min_confidence": min_confidence_threshold,
                "auto_apply": auto_apply,
                "max_updates_per_cycle": max_updates_per_cycle
            }
        )

    def generate_updates_from_execution(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory,
        actions: list[Action],
        feedback_analysis: Optional[FeedbackAnalysis] = None
    ) -> list[KnowledgeUpdate]:
        """
        Génère les mises à jour de connaissances depuis une exécution

        Analyse l'événement, le raisonnement, les actions et le feedback
        pour déterminer quelles connaissances devraient être mises à jour.

        Args:
            event: Événement traité
            working_memory: Mémoire de travail du raisonnement
            actions: Actions exécutées
            feedback_analysis: Analyse du feedback (optionnel)

        Returns:
            Liste de KnowledgeUpdate à appliquer

        Thread-safe: Pure function, pas de side effects
        """
        updates = []

        # 1. Update entities from event
        entity_updates = self._generate_entity_updates(
            event, working_memory, feedback_analysis
        )
        updates.extend(entity_updates)

        # 2. Create notes for significant decisions
        note_updates = self._generate_note_updates(
            event, working_memory, actions, feedback_analysis
        )
        updates.extend(note_updates)

        # 3. Update relationships
        relationship_updates = self._generate_relationship_updates(
            event, working_memory
        )
        updates.extend(relationship_updates)

        # 4. Update tags/categories
        tag_updates = self._generate_tag_updates(
            event, working_memory, feedback_analysis
        )
        updates.extend(tag_updates)

        logger.info(
            "Generated knowledge updates",
            extra={
                "event_id": event.event_id,
                "total_updates": len(updates),
                "entity_updates": len(entity_updates),
                "note_updates": len(note_updates),
                "relationship_updates": len(relationship_updates),
                "tag_updates": len(tag_updates)
            }
        )

        return updates

    def apply_updates(
        self,
        updates: list[KnowledgeUpdate],
        dry_run: bool = False
    ) -> tuple[int, int]:
        """
        Applique les mises à jour à la base de connaissances

        Args:
            updates: Liste de mises à jour à appliquer
            dry_run: Si True, valide sans appliquer

        Returns:
            (updates_applied, updates_failed)

        Raises:
            KnowledgeUpdateError: Si erreur critique
        """
        if len(updates) > self.max_updates_per_cycle:
            logger.warning(
                "Too many updates in cycle",
                extra={
                    "updates_count": len(updates),
                    "max_allowed": self.max_updates_per_cycle
                }
            )
            # Truncate to max
            updates = updates[:self.max_updates_per_cycle]

        applied = 0
        failed = 0

        for update in updates:
            try:
                # Validate
                self._validate_update(update)

                # Check confidence threshold
                if update.confidence < self.min_confidence_threshold and not self.auto_apply:
                    logger.debug(
                        "Skipping low-confidence update",
                        extra={
                            "update_id": update.update_id,
                            "confidence": update.confidence,
                            "threshold": self.min_confidence_threshold
                        }
                    )
                    continue

                # Apply
                if not dry_run:
                    self._apply_single_update(update)
                    with self._lock:
                        self._applied_updates.append(update)

                applied += 1

                logger.debug(
                    "Update applied",
                    extra={
                        "update_id": update.update_id,
                        "type": update.update_type.value,
                        "confidence": update.confidence
                    }
                )

            except Exception as e:
                failed += 1
                with self._lock:
                    self._failed_updates.append((update, e))

                logger.error(
                    "Update failed",
                    extra={
                        "update_id": update.update_id,
                        "error": str(e)
                    },
                    exc_info=True
                )

        logger.info(
            "Updates batch processed",
            extra={
                "applied": applied,
                "failed": failed,
                "total": len(updates),
                "dry_run": dry_run
            }
        )

        return applied, failed

    def rollback_last_batch(self) -> bool:
        """
        Rollback du dernier batch d'updates appliqués

        Returns:
            True si rollback réussi

        Raises:
            NotImplementedError: Rollback requires Passepartout integration

        Note: Fonctionnalité non implémentée (nécessite Passepartout git)
        """
        raise NotImplementedError(
            "Rollback functionality requires Passepartout integration. "
            "Cannot rollback updates without git-backed PKM."
        )

    def get_update_stats(self) -> dict[str, Any]:
        """
        Statistiques sur les updates appliqués

        Returns:
            Dict avec statistiques
        """
        with self._lock:
            applied_count = len(self._applied_updates)
            failed_count = len(self._failed_updates)
            total = applied_count + failed_count

            return {
                "applied_count": applied_count,
                "failed_count": failed_count,
                "success_rate": (
                    applied_count / total
                    if total > 0
                    else 0.0
                ),
                "by_type": self._count_by_type(list(self._applied_updates)),
                "failed_reasons": [
                    {"update_id": u.update_id, "error": str(e)}
                    for u, e in list(self._failed_updates)
                ]
            }

    # Private methods

    def _generate_entity_updates(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory,
        feedback_analysis: Optional[FeedbackAnalysis]
    ) -> list[KnowledgeUpdate]:
        """Generate entity updates from event"""
        updates = []

        # Confidence for entity updates
        # Si feedback positif → haute confiance
        # Si pas de feedback → confiance du raisonnement
        base_confidence = working_memory.overall_confidence
        if feedback_analysis and feedback_analysis.correctness_score > 0.8:
            base_confidence = min(1.0, base_confidence * 1.2)

        for entity in event.entities:
            # Add/update entity in knowledge base
            # Generate target_id from type and value
            target_id = f"{entity.type}:{entity.value}"
            updates.append(KnowledgeUpdate(
                update_type=UpdateType.ENTITY_ADDED,
                target_id=target_id,
                changes={
                    "entity_type": entity.type,
                    "value": entity.value,
                    "source_event": event.event_id,
                    "first_seen": now_utc().isoformat()
                },
                confidence=base_confidence,
                source="learning_from_execution"
            ))

        return updates

    def _generate_note_updates(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory,
        actions: list[Action],
        feedback_analysis: Optional[FeedbackAnalysis]
    ) -> list[KnowledgeUpdate]:
        """Generate note creation/updates"""
        updates = []

        # Créer note si décision significative
        # Critères: multiple passes OU feedback négatif OU actions multiples
        is_significant = (
            len(working_memory.reasoning_passes) >= 3 or
            (feedback_analysis and feedback_analysis.correctness_score < 0.6) or
            len(actions) >= 2
        )

        if not is_significant:
            return updates

        # Generate note ID from event
        note_id = f"decision_{event.event_id}"

        # Build note content
        note_content = self._build_note_content(
            event, working_memory, actions, feedback_analysis
        )

        # Determine confidence
        confidence = working_memory.overall_confidence
        if feedback_analysis:
            # Adjust based on correctness
            confidence = (confidence + feedback_analysis.correctness_score) / 2

        updates.append(KnowledgeUpdate(
            update_type=UpdateType.NOTE_CREATED,
            target_id=note_id,
            changes={
                "title": f"Decision: {event.title or event.event_type.value}",
                "content": note_content,
                "tags": self._extract_tags(event, working_memory),
                "entities": [f"{e.type}:{e.value}" for e in event.entities],
                "metadata": {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "passes": len(working_memory.reasoning_passes),
                    "actions_count": len(actions),
                    "confidence": confidence,
                    "timestamp": now_utc().isoformat()
                }
            },
            confidence=confidence,
            source="learning_from_execution"
        ))

        return updates

    def _generate_relationship_updates(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory
    ) -> list[KnowledgeUpdate]:
        """Generate relationship updates between entities"""
        updates = []

        # Create relationships between entities in same event
        entities = event.entities
        if len(entities) < 2:
            return updates

        # Pairwise relationships
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Generate entity identifiers from type:value
                entity1_id = f"{entity1.type}:{entity1.value}"
                entity2_id = f"{entity2.type}:{entity2.value}"
                relationship_id = f"rel_{entity1_id}_{entity2_id}"

                updates.append(KnowledgeUpdate(
                    update_type=UpdateType.RELATIONSHIP_CREATED,
                    target_id=relationship_id,
                    changes={
                        "entity1": entity1_id,
                        "entity2": entity2_id,
                        "type": "co_occurrence",
                        "context": event.event_id,
                        "strength": 0.5  # Base strength
                    },
                    confidence=working_memory.overall_confidence,
                    source="learning_from_execution"
                ))

        return updates

    def _generate_tag_updates(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory,
        _feedback_analysis: Optional[FeedbackAnalysis]
    ) -> list[KnowledgeUpdate]:
        """Generate tag additions"""
        updates = []

        # Extract tags from event and context
        tags = self._extract_tags(event, working_memory)

        for tag in tags:
            updates.append(KnowledgeUpdate(
                update_type=UpdateType.TAG_ADDED,
                target_id=event.event_id,
                changes={
                    "tag": tag,
                    "source": "auto_learning"
                },
                confidence=working_memory.overall_confidence,
                source="learning_from_execution"
            ))

        return updates

    def _build_note_content(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory,
        actions: list[Action],
        feedback_analysis: Optional[FeedbackAnalysis]
    ) -> str:
        """Build markdown content for decision note"""
        lines = []

        # Header
        lines.append(f"# Decision: {event.title or event.event_type.value}")
        lines.append("")

        # Event summary
        lines.append("## Event")
        lines.append(f"- Type: {event.event_type.value}")
        lines.append(f"- Urgency: {event.urgency.value}")
        if event.entities:
            lines.append(f"- Entities: {', '.join(e.value for e in event.entities)}")
        lines.append("")

        # Reasoning summary
        lines.append("## Reasoning")
        lines.append(f"- Passes: {len(working_memory.reasoning_passes)}")
        lines.append(f"- Final confidence: {working_memory.overall_confidence:.2f}")
        if working_memory.current_best_hypothesis:
            hyp = working_memory.get_hypothesis(working_memory.current_best_hypothesis)
            if hyp:
                lines.append(f"- Best hypothesis: {hyp.description}")
        lines.append("")

        # Actions
        if actions:
            lines.append("## Actions")
            for action in actions:
                lines.append(f"- {action.action_type}: {action.action_id}")
            lines.append("")

        # Feedback
        if feedback_analysis:
            lines.append("## Feedback")
            lines.append(f"- Correctness: {feedback_analysis.correctness_score:.2f}")
            lines.append(f"- Action quality: {feedback_analysis.action_quality_score:.2f}")
            lines.append(f"- Reasoning quality: {feedback_analysis.reasoning_quality_score:.2f}")
            if feedback_analysis.suggested_improvements:
                lines.append("\n### Improvements")
                for improvement in feedback_analysis.suggested_improvements:
                    lines.append(f"- {improvement}")
            lines.append("")

        return "\n".join(lines)

    def _extract_tags(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory
    ) -> list[str]:
        """Extract relevant tags from event and reasoning"""
        tags = []

        # Event type as tag
        tags.append(event.event_type.value)

        # Urgency as tag
        tags.append(f"urgency_{event.urgency.value}")

        # Number of passes as tag (complexity indicator)
        passes = len(working_memory.reasoning_passes)
        if passes == 1:
            tags.append("simple_decision")
        elif passes >= 3:
            tags.append("complex_decision")

        # Confidence level
        confidence = working_memory.overall_confidence
        if confidence > 0.9:
            tags.append("high_confidence")
        elif confidence < 0.6:
            tags.append("low_confidence")

        return tags

    def _validate_update(self, update: KnowledgeUpdate) -> None:
        """
        Validate update before application

        Raises:
            KnowledgeUpdateError: Si update invalide
        """
        # Already validated in __post_init__ but double-check
        if not (0 <= update.confidence <= 1):
            raise KnowledgeUpdateError(
                f"Invalid confidence {update.confidence}"
            )

        if not update.target_id:
            raise KnowledgeUpdateError("Missing target_id")

        if not update.changes:
            raise KnowledgeUpdateError("Empty changes dict")

        # Type-specific validation
        if update.update_type == UpdateType.NOTE_CREATED and (
            "title" not in update.changes or "content" not in update.changes
        ):
            raise KnowledgeUpdateError("Note update missing title or content")

        elif update.update_type == UpdateType.ENTITY_ADDED and (
            "entity_type" not in update.changes or "value" not in update.changes
        ):
            raise KnowledgeUpdateError("Entity update missing entity_type or value")

    def _apply_single_update(self, update: KnowledgeUpdate) -> None:
        """
        Apply single update to knowledge base

        Note: Placeholder pour l'instant. Sera complété quand Passepartout disponible.
        """
        # Pour l'instant, juste log
        logger.info(
            "Applying update (placeholder)",
            extra={
                "update_id": update.update_id,
                "type": update.update_type.value,
                "target": update.target_id
            }
        )

        # TODO: Vraie implémentation avec Passepartout
        # if update.update_type == UpdateType.NOTE_CREATED:
        #     self._note_manager.create_note(...)
        # elif update.update_type == UpdateType.ENTITY_ADDED:
        #     self._entity_manager.add_entity(...)
        # ...

    def _count_by_type(self, updates: list[KnowledgeUpdate]) -> dict[str, int]:
        """Count updates by type"""
        counts = {}
        for update in updates:
            update_type = update.update_type.value
            counts[update_type] = counts.get(update_type, 0) + 1
        return counts
