"""
Sganarelle Feedback Processor

Analyse le feedback utilisateur (explicite et implicite) pour générer des insights
permettant l'apprentissage et l'amélioration continue des décisions.

Thread-safe et optimisé pour performance.
"""

import logging
from typing import Any

from src.core.memory.working_memory import WorkingMemory
from src.figaro.actions.base import Action
from src.sganarelle.constants import (
    ACTION_APPROVAL_BOOST,
    ACTION_EXECUTED_SCORE,
    ACTION_MODIFICATION_PENALTY,
    ACTION_NO_ACTIONS_SCORE,
    ACTION_NOT_EXECUTED_SCORE,
    ACTION_QUALITY_LOW_THRESHOLD,
    ACTION_REJECTION_PENALTY,
    BASE_SCORE_APPROVED,
    BASE_SCORE_REJECTED,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_LOW_THRESHOLD,
    CORRECTION_PENALTY,
    CORRECTNESS_LOW_THRESHOLD,
    CORRECTNESS_MEDIUM_THRESHOLD,
    EXCELLENT_DECISION_THRESHOLD,
    EXPLICIT_FEEDBACK_WEIGHT,
    HIGH_SCORES_THRESHOLD,
    IMPLICIT_FEEDBACK_WEIGHT,
    LEARNING_CONFIDENCE_ERROR_THRESHOLD,
    LEARNING_CORRECTNESS_THRESHOLD,
    LEARNING_PERFECT_CONFIRMATION_SCORE,
    LEARNING_PERFECT_TIME_THRESHOLD,
    LEARNING_REASONING_QUALITY_THRESHOLD,
    MANY_PASSES_PENALTY,
    MANY_PASSES_THRESHOLD,
    MODIFICATION_PENALTY,
    OVERCONFIDENCE_PENALTY,
    REASONING_QUALITY_LOW_THRESHOLD,
    SINGLE_PASS_BONUS,
    TIME_FAST_BOOST,
    TIME_FAST_IMPLICIT_THRESHOLD,
    UNDERCONFIDENCE_BOOST,
    clamp,
    rating_to_score,
)
from src.sganarelle.types import FeedbackAnalysis, UserFeedback

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """
    Processeur de feedback utilisateur

    Analyse le feedback (explicite et implicite) pour extraire des insights
    sur la qualité des décisions et générer des suggestions d'amélioration.

    Thread-safe: Toutes les méthodes sont pure functions sur données immutables.
    """

    def __init__(
        self,
        implicit_weight: float = IMPLICIT_FEEDBACK_WEIGHT,
        explicit_weight: float = EXPLICIT_FEEDBACK_WEIGHT
    ):
        """
        Initialize feedback processor

        Args:
            implicit_weight: Poids du feedback implicite (0-1)
            explicit_weight: Poids du feedback explicite (0-1)

        Raises:
            ValueError: Si poids invalides
        """
        if not (0 <= implicit_weight <= 1):
            raise ValueError(f"implicit_weight doit être 0-1, got {implicit_weight}")
        if not (0 <= explicit_weight <= 1):
            raise ValueError(f"explicit_weight doit être 0-1, got {explicit_weight}")
        if abs((implicit_weight + explicit_weight) - 1.0) > 0.001:
            raise ValueError(
                f"Poids doivent sommer à 1.0, got {implicit_weight + explicit_weight}"
            )

        self.implicit_weight = implicit_weight
        self.explicit_weight = explicit_weight

        logger.info(
            "FeedbackProcessor initialized",
            extra={
                "implicit_weight": implicit_weight,
                "explicit_weight": explicit_weight
            }
        )

    def analyze_feedback(
        self,
        feedback: UserFeedback,
        working_memory: WorkingMemory,
        executed_actions: list[Action]
    ) -> FeedbackAnalysis:
        """
        Analyse complète du feedback

        Combine feedback explicite et implicite pour générer une analyse
        complète avec scores de qualité et suggestions d'amélioration.

        Args:
            feedback: Feedback utilisateur
            working_memory: Mémoire de travail de la décision
            executed_actions: Actions exécutées

        Returns:
            FeedbackAnalysis avec tous les scores et suggestions

        Thread-safe: Pure function sur données immutables
        """
        logger.debug(
            "Analyzing feedback",
            extra={
                "feedback_id": feedback.feedback_id,
                "approval": feedback.approval,
                "has_rating": feedback.rating is not None
            }
        )

        # Calculate individual scores
        correctness_score = self._calculate_correctness_score(
            feedback, working_memory, executed_actions
        )

        action_quality_score = self._calculate_action_quality_score(
            feedback, executed_actions
        )

        reasoning_quality_score = self._calculate_reasoning_quality_score(
            feedback, working_memory
        )

        confidence_error = self._calculate_confidence_error(
            feedback, working_memory
        )

        suggested_improvements = self._generate_improvement_suggestions(
            feedback, working_memory, executed_actions,
            correctness_score, action_quality_score, reasoning_quality_score
        )

        # Build metadata
        metadata = {
            "passes_executed": len(working_memory.reasoning_passes),
            "actions_count": len(executed_actions),
            "time_to_action": feedback.time_to_action,
            "implicit_score": feedback.implicit_quality_score,
            "has_correction": feedback.correction is not None,
            "has_modification": feedback.modification is not None,
            "weights": {
                "implicit": self.implicit_weight,
                "explicit": self.explicit_weight
            }
        }

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=correctness_score,
            suggested_improvements=suggested_improvements,
            confidence_error=confidence_error,
            action_quality_score=action_quality_score,
            reasoning_quality_score=reasoning_quality_score,
            metadata=metadata
        )

        logger.info(
            "Feedback analysis complete",
            extra={
                "feedback_id": feedback.feedback_id,
                "correctness_score": correctness_score,
                "action_quality_score": action_quality_score,
                "reasoning_quality_score": reasoning_quality_score,
                "improvements_count": len(suggested_improvements)
            }
        )

        return analysis

    def _calculate_correctness_score(
        self,
        feedback: UserFeedback,
        _working_memory: WorkingMemory,
        _executed_actions: list[Action]
    ) -> float:
        """
        Calculate correctness score (0-1)

        Combine explicit approval, rating, et implicit signals pour
        estimer si la décision était correcte.

        Returns:
            Score 0-1, 1 = décision parfaite
        """
        # Start with base score from approval
        base_score = BASE_SCORE_REJECTED if not feedback.approval else BASE_SCORE_APPROVED

        # Adjust with explicit rating if available
        if feedback.rating is not None:
            rating_score = rating_to_score(feedback.rating)
            base_score = (base_score + rating_score) / 2

        # Adjust with implicit signals
        implicit_score = feedback.implicit_quality_score

        # Weighted combination (ensure stays in [0, 1])
        final_score = (
            self.explicit_weight * base_score +
            self.implicit_weight * implicit_score
        )
        final_score = clamp(final_score)

        # Penalize if correction provided (clear error)
        if feedback.correction is not None:
            final_score *= CORRECTION_PENALTY

        # Penalize if modification needed
        if feedback.modification is not None:
            final_score *= MODIFICATION_PENALTY

        return clamp(final_score)

    def _calculate_action_quality_score(
        self,
        feedback: UserFeedback,
        executed_actions: list[Action]
    ) -> float:
        """
        Calculate action quality score (0-1)

        Évalue la qualité des actions proposées/exécutées.

        Returns:
            Score 0-1
        """
        if not executed_actions:
            # No actions → neutral
            return ACTION_NO_ACTIONS_SCORE

        # Start with base score from execution
        if feedback.action_executed:
            base_score = ACTION_EXECUTED_SCORE
        else:
            base_score = ACTION_NOT_EXECUTED_SCORE

        # Adjust with modification
        if feedback.modification is not None:
            base_score *= ACTION_MODIFICATION_PENALTY

        # Adjust with approval
        if feedback.approval:
            base_score = min(1.0, base_score * ACTION_APPROVAL_BOOST)
        else:
            base_score *= ACTION_REJECTION_PENALTY

        return clamp(base_score)

    def _calculate_reasoning_quality_score(
        self,
        feedback: UserFeedback,
        working_memory: WorkingMemory
    ) -> float:
        """
        Calculate reasoning quality score (0-1)

        Évalue la qualité du processus de raisonnement.

        Returns:
            Score 0-1
        """
        # Base score from final confidence
        confidence_score = working_memory.overall_confidence

        # Penalize if low confidence but user approved (underconfident)
        if feedback.approval and confidence_score < CONFIDENCE_LOW_THRESHOLD:
            confidence_score = min(1.0, confidence_score * UNDERCONFIDENCE_BOOST)

        # Penalize if high confidence but user rejected (overconfident)
        if not feedback.approval and confidence_score > CONFIDENCE_HIGH_THRESHOLD:
            confidence_score *= OVERCONFIDENCE_PENALTY

        # Consider number of passes
        passes = len(working_memory.reasoning_passes)
        if passes == 1 and feedback.approval:
            # Quick convergence on correct answer → excellent
            pass_bonus = SINGLE_PASS_BONUS
        elif passes >= MANY_PASSES_THRESHOLD and not feedback.approval:
            # Many passes but still wrong → poor
            pass_bonus = MANY_PASSES_PENALTY
        else:
            pass_bonus = 1.0

        final_score = confidence_score * pass_bonus

        return clamp(final_score)

    def _calculate_confidence_error(
        self,
        feedback: UserFeedback,
        working_memory: WorkingMemory
    ) -> float:
        """
        Calculate confidence error

        Différence entre confiance prédite et réalité observée.
        Positif = overconfident, Négatif = underconfident

        Returns:
            Error in range [-1, 1]
        """
        predicted_confidence = working_memory.overall_confidence

        # Estimate actual correctness from feedback
        if feedback.approval:
            if feedback.rating is not None:
                actual_correctness = rating_to_score(feedback.rating)
            else:
                # Approval → likely correct (but not certain)
                actual_correctness = ACTION_EXECUTED_SCORE
        else:
            # Rejection → likely incorrect
            actual_correctness = BASE_SCORE_REJECTED

        # Adjust with implicit signals
        if feedback.action_executed and feedback.time_to_action < TIME_FAST_IMPLICIT_THRESHOLD:
            # Quick execution → likely correct
            actual_correctness = min(1.0, actual_correctness * TIME_FAST_BOOST)

        if feedback.modification is not None:
            # Needed modification → less correct
            actual_correctness *= MODIFICATION_PENALTY

        # Error = predicted - actual
        error = predicted_confidence - actual_correctness

        return clamp(error, min_val=-1.0, max_val=1.0)

    def _generate_improvement_suggestions(
        self,
        feedback: UserFeedback,
        working_memory: WorkingMemory,
        _executed_actions: list[Action],
        correctness_score: float,
        action_quality_score: float,
        reasoning_quality_score: float
    ) -> list[str]:
        """
        Generate improvement suggestions

        Analyse les scores et feedback pour suggérer des améliorations
        concrètes au système.

        Returns:
            Liste de suggestions en français
        """
        suggestions = []

        # Correctness issues
        if correctness_score < CORRECTNESS_LOW_THRESHOLD:
            suggestions.append(
                "Décision incorrecte détectée. Revoir le processus de raisonnement."
            )

            if feedback.correction:
                suggestions.append(
                    f"Correction utilisateur: {feedback.correction}"
                )

        # Action quality issues
        if action_quality_score < ACTION_QUALITY_LOW_THRESHOLD:
            if not feedback.action_executed:
                suggestions.append(
                    "Actions non exécutées. Revoir la pertinence des actions proposées."
                )

            if feedback.modification:
                suggestions.append(
                    "Action modifiée par utilisateur. Analyser la modification pour apprentissage."
                )

        # Reasoning quality issues
        if reasoning_quality_score < REASONING_QUALITY_LOW_THRESHOLD:
            passes = len(working_memory.reasoning_passes)
            confidence = working_memory.overall_confidence

            if confidence > CONFIDENCE_HIGH_THRESHOLD and not feedback.approval:
                suggestions.append(
                    f"Overconfidence détectée (confiance {confidence:.2f} mais rejetée). "
                    "Calibrer le modèle de confiance."
                )

            if confidence < CONFIDENCE_LOW_THRESHOLD and feedback.approval:
                suggestions.append(
                    f"Underconfidence détectée (confiance {confidence:.2f} mais approuvée). "
                    "Augmenter confiance pour cas similaires."
                )

            if passes >= MANY_PASSES_THRESHOLD and not feedback.approval:
                suggestions.append(
                    f"Convergence lente ({passes} passes) vers mauvaise décision. "
                    "Revoir stratégie de raisonnement itératif."
                )

        # Time to action issues
        if feedback.time_to_action > LEARNING_PERFECT_TIME_THRESHOLD * 2:
            suggestions.append(
                f"Temps de réponse lent ({feedback.time_to_action:.1f}s). "
                "Optimiser performance du pipeline."
            )

        # Context issues (inferred)
        if correctness_score < CORRECTNESS_MEDIUM_THRESHOLD and len(working_memory.reasoning_passes) >= 2:
            # Multiple passes but still incorrect → context issue?
            suggestions.append(
                "Décision incorrecte malgré passes multiples. "
                "Vérifier qualité du contexte récupéré (Pass 2)."
            )

        # Add user comment if provided
        if feedback.comment:
            suggestions.append(f"Commentaire utilisateur: {feedback.comment}")

        # If all scores are high but no approval, something subtle is wrong
        if (correctness_score > HIGH_SCORES_THRESHOLD and action_quality_score > HIGH_SCORES_THRESHOLD and
            reasoning_quality_score > HIGH_SCORES_THRESHOLD and not feedback.approval):
            suggestions.append(
                "Scores techniques élevés mais décision rejetée. "
                "Possible désalignement avec préférences utilisateur."
            )

        # If no suggestions yet but feedback is negative
        if not suggestions and not feedback.approval:
            suggestions.append(
                "Décision rejetée sans cause claire identifiée. "
                "Nécessite analyse manuelle."
            )

        # If everything is perfect, acknowledge it
        if not suggestions and feedback.approval and correctness_score > EXCELLENT_DECISION_THRESHOLD:
            suggestions.append("Décision excellente. Maintenir ce niveau de qualité.")

        return suggestions

    def extract_correction_actions(
        self,
        feedback: UserFeedback
    ) -> list[dict[str, Any]]:
        """
        Extract actionable corrections from feedback

        Parse la correction textuelle pour extraire des actions
        concrètes à appliquer.

        Args:
            feedback: Feedback avec correction

        Returns:
            Liste de corrections structurées

        Note: Version simple pour l'instant, peut être amélioré avec NLP
        """
        corrections = []

        if feedback.correction:
            # Simple parsing pour l'instant
            correction_text = feedback.correction.strip().lower()

            # Detect common correction patterns
            if "archive" in correction_text:
                corrections.append({
                    "type": "action_correction",
                    "action": "archive",
                    "reason": feedback.correction
                })

            if "delete" in correction_text or "supprimer" in correction_text:
                corrections.append({
                    "type": "action_correction",
                    "action": "delete",
                    "reason": feedback.correction
                })

            if "task" in correction_text or "tâche" in correction_text:
                corrections.append({
                    "type": "action_correction",
                    "action": "create_task",
                    "reason": feedback.correction
                })

            # If no specific pattern matched, keep as generic
            if not corrections:
                corrections.append({
                    "type": "generic_correction",
                    "text": feedback.correction
                })

        if feedback.modification:
            corrections.append({
                "type": "action_modification",
                "modified_action": feedback.modification.action_type,
                "reason": "User modified action parameters"
            })

        return corrections

    def should_trigger_learning(
        self,
        feedback: UserFeedback,
        analysis: FeedbackAnalysis
    ) -> bool:
        """
        Determine if feedback should trigger learning update

        Pas tout le feedback nécessite apprentissage (e.g., perfect
        decision confirmée). Cette méthode filtre le bruit.

        Args:
            feedback: Feedback utilisateur
            analysis: Analyse du feedback

        Returns:
            True si learning devrait être triggered
        """
        # Always learn from explicit corrections
        if feedback.correction is not None:
            return True

        # Always learn from modifications
        if feedback.modification is not None:
            return True

        # Learn from low correctness
        if analysis.correctness_score < LEARNING_CORRECTNESS_THRESHOLD:
            return True

        # Learn from confidence errors
        if abs(analysis.confidence_error) > LEARNING_CONFIDENCE_ERROR_THRESHOLD:
            return True

        # Learn from poor reasoning quality
        if analysis.reasoning_quality_score < LEARNING_REASONING_QUALITY_THRESHOLD:
            return True

        # Learn from ratings (explicit signal)
        if feedback.rating is not None:
            return True

        # Don't learn from perfect confirmations (no new info)
        # Default: learn from everything except perfect confirmations
        return not (
            feedback.approval
            and analysis.correctness_score > LEARNING_PERFECT_CONFIRMATION_SCORE
            and feedback.action_executed
            and feedback.time_to_action < LEARNING_PERFECT_TIME_THRESHOLD
        )
