"""
Sganarelle Learning Engine

Orchestrateur principal du module d'apprentissage.
Ferme la boucle cognitive en apprenant de chaque décision et feedback.

Thread-safe et optimisé pour performance.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from src.core.events.universal_event import PerceivedEvent, now_utc
from src.core.memory.working_memory import WorkingMemory
from src.figaro.actions.base import Action
from src.sganarelle.confidence_calibrator import ConfidenceCalibrator
from src.sganarelle.constants import (
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MAX_HISTORY_DAYS,
    DEFAULT_MIN_CONFIDENCE_FOR_UPDATES,
    DEFAULT_MIN_OCCURRENCES,
    DEFAULT_MIN_SAMPLES_PER_BIN,
    DEFAULT_MIN_SUCCESS_RATE,
    DEFAULT_NUM_BINS,
    DEFAULT_SMOOTHING_FACTOR,
    EXPLICIT_FEEDBACK_WEIGHT,
    IMPLICIT_FEEDBACK_WEIGHT,
    PATTERN_MATCHING_MIN_CONFIDENCE,
    PATTERN_SUCCESS_CORRECTNESS_THRESHOLD,
    PATTERN_SUCCESS_THRESHOLD,
    PATTERN_SUGGESTION_MIN_CONFIDENCE,
    PROVIDER_QUALITY_FAILURE_FALLBACK,
    PROVIDER_QUALITY_SUCCESS_FALLBACK,
    UPDATE_BATCH_SIZE_DEFAULT,
)
from src.sganarelle.feedback_processor import FeedbackProcessor
from src.sganarelle.knowledge_updater import KnowledgeUpdater
from src.sganarelle.pattern_store import (
    PatternStore,
    PatternStoreError,
    create_pattern_from_execution,
)
from src.sganarelle.provider_tracker import ProviderTracker
from src.sganarelle.types import (
    FeedbackAnalysis,
    KnowledgeUpdate,
    LearningResult,
    Pattern,
    ProviderScore,
    UserFeedback,
)

logger = logging.getLogger(__name__)


@dataclass
class LearningContext:
    """
    Context for a learning cycle.

    Groups all the inputs needed for the learn() method,
    making it easier to pass around and test.
    """

    event: "PerceivedEvent"
    working_memory: "WorkingMemory"
    actions: list["Action"]
    execution_success: bool
    user_feedback: Optional["UserFeedback"] = None
    provider_name: str = "anthropic"
    model_tier: str = "haiku"
    ai_latency_ms: float = 0.0
    ai_cost_usd: float = 0.0


class LearningEngineError(Exception):
    """Erreur dans le learning engine"""
    pass


class LearningEngine:
    """
    Moteur d'apprentissage principal

    Coordonne tous les composants de Sganarelle pour fermer la boucle cognitive:
    1. Feedback Processing → analyse qualité décision
    2. Knowledge Updates → enrichit Scapin
    3. Pattern Learning → identifie comportements récurrents
    4. Provider Tracking → optimise sélection AI
    5. Confidence Calibration → améliore prédictions

    Thread-safe et async-ready.
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        enable_knowledge_updates: bool = True,
        enable_pattern_learning: bool = True,
        enable_provider_tracking: bool = True,
        enable_confidence_calibration: bool = True,
        min_confidence_for_updates: float = DEFAULT_MIN_CONFIDENCE_FOR_UPDATES
    ):
        """
        Initialize learning engine

        Args:
            storage_dir: Répertoire pour persistence (None = memory only)
            enable_knowledge_updates: Enable Scapin knowledge updates
            enable_pattern_learning: Enable pattern identification
            enable_provider_tracking: Enable AI provider metrics
            enable_confidence_calibration: Enable confidence tuning
            min_confidence_for_updates: Confiance minimale pour auto-updates

        Raises:
            ValueError: Si paramètres invalides
        """
        if min_confidence_for_updates < 0 or min_confidence_for_updates > 1:
            raise ValueError(
                f"min_confidence_for_updates doit être 0-1, got {min_confidence_for_updates}"
            )

        self.storage_dir = storage_dir
        self.enable_knowledge_updates = enable_knowledge_updates
        self.enable_pattern_learning = enable_pattern_learning
        self.enable_provider_tracking = enable_provider_tracking
        self.enable_confidence_calibration = enable_confidence_calibration
        self.min_confidence_for_updates = min_confidence_for_updates

        # Initialize storage directory
        if storage_dir:
            storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.feedback_processor = FeedbackProcessor(
            implicit_weight=IMPLICIT_FEEDBACK_WEIGHT,
            explicit_weight=EXPLICIT_FEEDBACK_WEIGHT
        )

        self.knowledge_updater = KnowledgeUpdater(
            min_confidence_threshold=min_confidence_for_updates,
            auto_apply=False,  # Manual control for safety
            max_updates_per_cycle=UPDATE_BATCH_SIZE_DEFAULT
        )

        self.pattern_store = PatternStore(
            storage_path=(
                storage_dir / "patterns.json"
                if storage_dir
                else None
            ),
            min_occurrences=DEFAULT_MIN_OCCURRENCES,
            min_success_rate=DEFAULT_MIN_SUCCESS_RATE,
            max_age_days=DEFAULT_MAX_AGE_DAYS,
            auto_save=True
        )

        self.provider_tracker = ProviderTracker(
            storage_path=(
                storage_dir / "provider_scores.json"
                if storage_dir
                else None
            ),
            auto_save=True,
            max_history_days=DEFAULT_MAX_HISTORY_DAYS
        )

        self.confidence_calibrator = ConfidenceCalibrator(
            storage_path=(
                storage_dir / "calibration.json"
                if storage_dir
                else None
            ),
            num_bins=DEFAULT_NUM_BINS,
            min_samples_per_bin=DEFAULT_MIN_SAMPLES_PER_BIN,
            smoothing_factor=DEFAULT_SMOOTHING_FACTOR,
            auto_save=True
        )

        # Statistics (thread-safe)
        self._stats_lock = Lock()
        self._total_learning_cycles = 0
        self._total_learning_time = 0.0
        self._last_learning: Optional[datetime] = None

        logger.info(
            "LearningEngine initialized",
            extra={
                "storage_dir": str(storage_dir) if storage_dir else "memory",
                "knowledge_updates": enable_knowledge_updates,
                "pattern_learning": enable_pattern_learning,
                "provider_tracking": enable_provider_tracking,
                "confidence_calibration": enable_confidence_calibration
            }
        )

    def learn(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory,
        actions: list[Action],
        execution_success: bool,
        user_feedback: Optional[UserFeedback] = None,
        provider_name: str = "anthropic",
        model_tier: str = "haiku",
        ai_latency_ms: float = 0.0,
        ai_cost_usd: float = 0.0
    ) -> LearningResult:
        """
        Apprentissage complet depuis une décision

        C'est le point d'entrée principal pour l'apprentissage.
        Coordonne tous les composants pour mettre à jour le système.

        Args:
            event: Événement traité
            working_memory: Mémoire de travail du raisonnement
            actions: Actions exécutées
            execution_success: Si l'exécution a réussi
            user_feedback: Feedback utilisateur (optionnel)
            provider_name: Nom du provider AI utilisé
            model_tier: Tier du modèle AI
            ai_latency_ms: Latence totale AI (ms)
            ai_cost_usd: Coût total AI (USD)

        Returns:
            LearningResult avec toutes les mises à jour

        Thread-safe: Peut être appelé en parallèle (lock interne)
        """
        start_time = time.time()

        logger.info(
            "Learning cycle started",
            extra={
                "event_id": event.event_id,
                "has_feedback": user_feedback is not None,
                "actions_count": len(actions),
                "execution_success": execution_success
            }
        )

        try:
            # 1. Analyze feedback (if available)
            feedback_analysis = None
            if user_feedback:
                feedback_analysis = self.feedback_processor.analyze_feedback(
                    user_feedback, working_memory, actions
                )
                logger.debug(
                    "Feedback analyzed",
                    extra={
                        "correctness_score": feedback_analysis.correctness_score,
                        "action_quality": feedback_analysis.action_quality_score,
                        "reasoning_quality": feedback_analysis.reasoning_quality_score
                    }
                )

            # 2. Update knowledge base
            knowledge_updates: list[KnowledgeUpdate] = []
            updates_applied = 0
            updates_failed = 0

            if self.enable_knowledge_updates:
                knowledge_updates = self.knowledge_updater.generate_updates_from_execution(
                    event, working_memory, actions, feedback_analysis
                )

                updates_applied, updates_failed = self.knowledge_updater.apply_updates(
                    knowledge_updates,
                    dry_run=False  # Real application
                )

                logger.info(
                    "Knowledge updates applied",
                    extra={
                        "generated": len(knowledge_updates),
                        "applied": updates_applied,
                        "failed": updates_failed
                    }
                )

            # 3. Learn patterns
            pattern_updates: list[Pattern] = []

            if self.enable_pattern_learning and execution_success:
                # Only learn patterns from successful executions
                pattern = self._learn_pattern(
                    event, working_memory, actions, feedback_analysis
                )
                if pattern:
                    pattern_updates.append(pattern)

                # Update existing matching patterns
                matching_patterns = self.pattern_store.find_matching_patterns(
                    event, context={}, min_confidence=PATTERN_MATCHING_MIN_CONFIDENCE
                )

                for pattern in matching_patterns:
                    # Determine if pattern application was successful
                    pattern_success = execution_success and (
                        feedback_analysis is None or
                        feedback_analysis.correctness_score > PATTERN_SUCCESS_CORRECTNESS_THRESHOLD
                    )

                    updated_pattern = self.pattern_store.update_pattern(
                        pattern.pattern_id,
                        success=pattern_success
                    )
                    pattern_updates.append(updated_pattern)

                logger.info(
                    "Patterns learned",
                    extra={
                        "new_patterns": 1 if pattern else 0,
                        "updated_patterns": len(matching_patterns)
                    }
                )

            # 4. Track provider performance
            provider_scores: dict[str, ProviderScore] = {}

            if self.enable_provider_tracking:
                # Determine actual quality from feedback or execution
                actual_quality = (
                    feedback_analysis.correctness_score
                    if feedback_analysis
                    else (PROVIDER_QUALITY_SUCCESS_FALLBACK if execution_success else PROVIDER_QUALITY_FAILURE_FALLBACK)
                )

                self.provider_tracker.record_call(
                    provider_name=provider_name,
                    model_tier=model_tier,
                    latency_ms=ai_latency_ms,
                    cost_usd=ai_cost_usd,
                    success=execution_success,
                    predicted_confidence=working_memory.overall_confidence,
                    actual_quality=actual_quality
                )

                # Get updated score
                score = self.provider_tracker.get_score(provider_name, model_tier)
                if score:
                    provider_scores[f"{provider_name}_{model_tier}"] = score

                logger.debug(
                    "Provider performance tracked",
                    extra={
                        "provider": provider_name,
                        "tier": model_tier,
                        "latency_ms": ai_latency_ms,
                        "cost_usd": ai_cost_usd
                    }
                )

            # 5. Calibrate confidence
            confidence_adjustments: dict[str, float] = {}

            if self.enable_confidence_calibration and feedback_analysis:
                # Add observation for calibration
                self.confidence_calibrator.add_from_feedback(
                    working_memory.overall_confidence,
                    feedback_analysis
                )

                # Calculate adjustment
                calibrated = self.confidence_calibrator.calibrate(
                    working_memory.overall_confidence
                )
                adjustment = calibrated - working_memory.overall_confidence

                confidence_adjustments["overall"] = adjustment

                logger.debug(
                    "Confidence calibrated",
                    extra={
                        "original": working_memory.overall_confidence,
                        "calibrated": calibrated,
                        "adjustment": adjustment
                    }
                )

            # 6. Build result
            duration = time.time() - start_time

            result = LearningResult(
                knowledge_updates=knowledge_updates,
                pattern_updates=pattern_updates,
                provider_scores=provider_scores,
                confidence_adjustments=confidence_adjustments,
                duration=duration,
                updates_applied=updates_applied,
                updates_failed=updates_failed,
                metadata={
                    "event_id": event.event_id,
                    "has_feedback": user_feedback is not None,
                    "execution_success": execution_success,
                    "reasoning_passes": len(working_memory.reasoning_passes),
                    "actions_count": len(actions),
                    "components_enabled": {
                        "knowledge_updates": self.enable_knowledge_updates,
                        "pattern_learning": self.enable_pattern_learning,
                        "provider_tracking": self.enable_provider_tracking,
                        "confidence_calibration": self.enable_confidence_calibration
                    }
                }
            )

            # Update statistics (thread-safe)
            with self._stats_lock:
                self._total_learning_cycles += 1
                self._total_learning_time += duration
                self._last_learning = now_utc()

            logger.info(
                "Learning cycle completed",
                extra={
                    "event_id": event.event_id,
                    "duration": duration,
                    "success": result.success,
                    "total_updates": result.total_updates
                }
            )

            return result

        except (PatternStoreError, ValueError, TypeError) as e:
            # Known recoverable errors - log and return partial result
            logger.error(
                "Learning cycle failed with known error",
                extra={"event_id": event.event_id, "error": str(e), "error_type": type(e).__name__},
                exc_info=True
            )

            # Return minimal result on error
            duration = time.time() - start_time
            return LearningResult(
                knowledge_updates=[],
                pattern_updates=[],
                provider_scores={},
                confidence_adjustments={},
                duration=duration,
                updates_applied=0,
                updates_failed=1,
                metadata={"error": str(e), "error_type": type(e).__name__}
            )
        except Exception as e:
            # Unexpected errors - log with full traceback and re-raise
            logger.critical(
                "Learning cycle failed with unexpected error",
                extra={"event_id": event.event_id, "error": str(e)},
                exc_info=True
            )
            # Re-raise to make debugging easier
            raise LearningEngineError(
                f"Unexpected error in learning cycle: {str(e)}"
            ) from e

    def get_stats(self) -> dict[str, Any]:
        """
        Statistiques globales du learning engine

        Returns:
            Dict avec toutes les statistiques
        """
        with self._stats_lock:
            learning_cycles = self._total_learning_cycles
            total_time = self._total_learning_time
            last_learning = self._last_learning

        return {
            "learning_cycles": learning_cycles,
            "total_learning_time": total_time,
            "avg_learning_time": (
                total_time / learning_cycles
                if learning_cycles > 0
                else 0.0
            ),
            "last_learning": (
                last_learning.isoformat()
                if last_learning
                else None
            ),
            "knowledge_updater": self.knowledge_updater.get_update_stats(),
            "pattern_store": self.pattern_store.get_stats(),
            "provider_tracker": self.provider_tracker.get_stats(),
            "confidence_calibrator": self.confidence_calibrator.get_stats()
        }

    def get_suggestions_for_event(
        self,
        event: PerceivedEvent,
        context: Optional[dict[str, Any]] = None
    ) -> list[Pattern]:
        """
        Obtenir suggestions de patterns pour un événement

        Args:
            event: Événement à analyser
            context: Contexte additionnel

        Returns:
            Liste de patterns applicables, triés par pertinence
        """
        if not self.enable_pattern_learning:
            return []

        patterns = self.pattern_store.find_matching_patterns(
            event,
            context=context or {},
            min_confidence=PATTERN_SUGGESTION_MIN_CONFIDENCE
        )

        logger.debug(
            "Pattern suggestions retrieved",
            extra={
                "event_id": event.event_id,
                "patterns_found": len(patterns)
            }
        )

        return patterns

    def prune_old_data(self) -> dict[str, int]:
        """
        Nettoyage des données anciennes/obsolètes

        Returns:
            Dict avec nombre d'items supprimés par composant
        """
        logger.info("Pruning old data")

        pruned = {}

        if self.enable_pattern_learning:
            patterns_removed = self.pattern_store.prune_old_patterns()
            pruned["patterns"] = patterns_removed

        # Note: Provider tracker et calibrator gèrent leur pruning automatiquement

        logger.info("Pruning completed", extra=pruned)

        return pruned

    def save_all(self) -> None:
        """Force save de tous les composants avec persistence"""
        logger.info("Saving all learning data")

        if self.enable_pattern_learning:
            self.pattern_store.save()

        if self.enable_provider_tracking:
            self.provider_tracker.save()

        if self.enable_confidence_calibration:
            self.confidence_calibrator.save()

        logger.info("All learning data saved")

    # Private methods

    def _learn_pattern(
        self,
        event: PerceivedEvent,
        working_memory: WorkingMemory,
        actions: list[Action],
        feedback_analysis: Optional[FeedbackAnalysis]
    ) -> Optional[Pattern]:
        """
        Apprend un nouveau pattern depuis l'exécution

        Returns:
            Pattern créé ou None si pas de pattern détecté
        """
        # Only create pattern if decision was successful
        success = feedback_analysis is None or feedback_analysis.correctness_score > PATTERN_SUCCESS_THRESHOLD

        if not success:
            return None

        # Don't create pattern if too few actions
        if len(actions) == 0:
            return None

        # Build context
        context = {
            "reasoning_passes": len(working_memory.reasoning_passes),
            "confidence": working_memory.overall_confidence
        }

        # Create pattern
        pattern = create_pattern_from_execution(
            event=event,
            actions=actions,
            context=context,
            success=success,
            initial_confidence=working_memory.overall_confidence
        )

        # Check if similar pattern exists
        existing = self.pattern_store.get_pattern(pattern.pattern_id)

        if existing:
            # Update existing instead of creating new
            self.pattern_store.update_pattern(
                pattern.pattern_id,
                success=success
            )
            return existing
        else:
            # Add new pattern
            self.pattern_store.add_pattern(pattern)
            return pattern
