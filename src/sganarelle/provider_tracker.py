"""
Sganarelle Provider Tracker

Suit les performances des AI providers pour optimiser la sélection
et calibrer les coûts/latence/qualité.

Thread-safe avec persistence.
"""

import json
import logging
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from src.core.events.universal_event import now_utc
from src.sganarelle.types import ProviderScore

logger = logging.getLogger(__name__)


class ProviderTrackerError(Exception):
    """Erreur dans le provider tracker"""
    pass


class ProviderTracker:
    """
    Gestionnaire de métriques AI providers

    Track performance, quality, latency, et cost par provider/tier.
    Thread-safe avec persistence.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        auto_save: bool = True,
        max_history_days: int = 30
    ):
        """
        Initialize provider tracker

        Args:
            storage_path: Chemin fichier JSON pour persistence
            auto_save: Si True, save après chaque update
            max_history_days: Jours d'historique à conserver
        """
        self.storage_path = storage_path
        self.auto_save = auto_save
        self.max_history_days = max_history_days

        # Thread-safe storage
        # Key: (provider_name, model_tier)
        self._scores: dict[tuple[str, str], ProviderScore] = {}

        # Detailed call history for percentile calculations (limited to prevent memory leaks)
        # Key: (provider_name, model_tier), Value: deque of (timestamp, latency_ms, cost, success, confidence, actual_quality)
        # Limited to last 10000 calls per provider to prevent memory issues
        MAX_HISTORY_PER_PROVIDER = 10000
        self._call_history: dict[tuple[str, str], deque] = defaultdict(
            lambda: deque(maxlen=MAX_HISTORY_PER_PROVIDER)
        )

        self._lock = Lock()

        # Counter for efficient pruning (prune only every 100 calls)
        self._total_calls = 0

        # Load existing data
        if storage_path and storage_path.exists():
            self._load_from_disk()

        logger.info(
            "ProviderTracker initialized",
            extra={
                "storage_path": str(storage_path) if storage_path else "memory",
                "providers_tracked": len(self._scores)
            }
        )

    def record_call(
        self,
        provider_name: str,
        model_tier: str,
        latency_ms: float,
        cost_usd: float,
        success: bool,
        predicted_confidence: float = 0.0,
        actual_quality: Optional[float] = None
    ) -> None:
        """
        Enregistre un appel provider

        Args:
            provider_name: Nom du provider (e.g., "anthropic")
            model_tier: Tier du modèle (e.g., "haiku", "sonnet", "opus")
            latency_ms: Latence en millisecondes
            cost_usd: Coût en USD
            success: Si l'appel a réussi
            predicted_confidence: Confiance prédite par le modèle (0-1)
            actual_quality: Qualité réelle observée (0-1, optionnel)

        Raises:
            ValueError: Si paramètres invalides
        """
        if latency_ms < 0:
            raise ValueError(f"latency_ms doit être >= 0, got {latency_ms}")
        if cost_usd < 0:
            raise ValueError(f"cost_usd doit être >= 0, got {cost_usd}")
        if not (0 <= predicted_confidence <= 1):
            raise ValueError(
                f"predicted_confidence doit être 0-1, got {predicted_confidence}"
            )
        if actual_quality is not None and not (0 <= actual_quality <= 1):
            raise ValueError(f"actual_quality doit être 0-1, got {actual_quality}")

        key = (provider_name, model_tier)

        with self._lock:
            # Add to call history
            timestamp = now_utc()
            actual_q = actual_quality if actual_quality is not None else predicted_confidence
            self._call_history[key].append(
                (timestamp, latency_ms, cost_usd, success, predicted_confidence, actual_q)
            )

            # Prune old history only every 100 calls (performance optimization)
            # deque with maxlen already handles size limit automatically
            self._total_calls += 1
            if self._total_calls % 100 == 0:
                # Prune all providers when threshold reached
                for provider_key in list(self._call_history.keys()):
                    self._prune_old_history(provider_key)

            # Update or create score
            if key in self._scores:
                self._update_existing_score(
                    key, latency_ms, cost_usd, success, predicted_confidence, actual_q
                )
            else:
                self._create_new_score(
                    key, provider_name, model_tier, latency_ms, cost_usd,
                    success, predicted_confidence, actual_q
                )

            logger.debug(
                "Provider call recorded",
                extra={
                    "provider": provider_name,
                    "tier": model_tier,
                    "latency_ms": latency_ms,
                    "cost_usd": cost_usd,
                    "success": success
                }
            )

            if self.auto_save:
                self._save_to_disk()

    def get_score(
        self,
        provider_name: str,
        model_tier: str
    ) -> Optional[ProviderScore]:
        """
        Récupère le score d'un provider/tier

        Args:
            provider_name: Nom du provider
            model_tier: Tier du modèle

        Returns:
            ProviderScore ou None si pas de données
        """
        key = (provider_name, model_tier)
        with self._lock:
            return self._scores.get(key)

    def get_all_scores(self) -> list[ProviderScore]:
        """
        Récupère tous les scores

        Returns:
            Liste de tous les ProviderScore
        """
        with self._lock:
            return list(self._scores.values())

    def get_best_provider(
        self,
        optimize_for: str = "balanced",
        min_calls: int = 10
    ) -> Optional[tuple[str, str, ProviderScore]]:
        """
        Trouve le meilleur provider selon critère

        Args:
            optimize_for: "speed", "cost", "quality", "balanced"
            min_calls: Nombre minimum d'appels requis

        Returns:
            (provider_name, model_tier, score) ou None
        """
        with self._lock:
            # Filter providers with enough data
            candidates = [
                (key, score)
                for key, score in self._scores.items()
                if score.total_calls >= min_calls
            ]

            if not candidates:
                return None

            # Score each candidate
            scored = [
                (key, score, self._calculate_optimization_score(score, optimize_for))
                for key, score in candidates
            ]

            # Sort by optimization score
            scored.sort(key=lambda x: x[2], reverse=True)

            best_key, best_score, best_opt_score = scored[0]
            provider_name, model_tier = best_key

            logger.debug(
                "Best provider selected",
                extra={
                    "provider": provider_name,
                    "tier": model_tier,
                    "optimize_for": optimize_for,
                    "score": best_opt_score
                }
            )

            return (provider_name, model_tier, best_score)

    def get_stats(self) -> dict[str, Any]:
        """
        Statistiques globales

        Returns:
            Dict avec statistiques
        """
        with self._lock:
            scores = list(self._scores.values())

            if not scores:
                return {
                    "total_providers": 0,
                    "total_calls": 0,
                    "total_cost_usd": 0.0
                }

            total_calls = sum(s.total_calls for s in scores)
            total_cost = sum(s.total_cost_usd for s in scores)
            avg_success_rate = sum(s.success_rate for s in scores) / len(scores)

            return {
                "total_providers": len(scores),
                "total_calls": total_calls,
                "total_cost_usd": total_cost,
                "avg_success_rate": avg_success_rate,
                "by_provider": self._stats_by_provider(),
                "by_tier": self._stats_by_tier()
            }

    def reset_stats(
        self,
        provider_name: Optional[str] = None,
        model_tier: Optional[str] = None
    ) -> None:
        """
        Reset statistics (pour testing ou nouveau départ)

        Args:
            provider_name: Reset ce provider uniquement (None = tous)
            model_tier: Reset ce tier uniquement (None = tous)
        """
        with self._lock:
            if provider_name is None and model_tier is None:
                # Reset tout
                self._scores.clear()
                self._call_history.clear()
                logger.warning("All provider stats reset")

            else:
                # Reset sélectif
                to_remove = [
                    key for key in self._scores
                    if (provider_name is None or key[0] == provider_name) and
                       (model_tier is None or key[1] == model_tier)
                ]

                for key in to_remove:
                    del self._scores[key]
                    if key in self._call_history:
                        del self._call_history[key]

                logger.info(
                    "Provider stats reset",
                    extra={
                        "provider": provider_name,
                        "tier": model_tier,
                        "removed": len(to_remove)
                    }
                )

            if self.auto_save:
                self._save_to_disk()

    def save(self) -> None:
        """Force save to disk"""
        if self.storage_path:
            self._save_to_disk()

    # Private methods

    def _update_existing_score(
        self,
        key: tuple[str, str],
        latency_ms: float,
        cost_usd: float,
        success: bool,
        predicted_confidence: float,
        actual_quality: float
    ) -> None:
        """Update existing score with new call"""
        old_score = self._scores[key]

        # Calculate new totals
        new_total_calls = old_score.total_calls + 1
        new_successful_calls = old_score.successful_calls + (1 if success else 0)
        new_failed_calls = old_score.failed_calls + (0 if success else 1)

        # Update averages (incremental mean)
        n = new_total_calls
        old_n = old_score.total_calls

        new_avg_confidence = (
            (old_score.avg_confidence * old_n + predicted_confidence) / n
        )

        # Update calibration error
        calibration_error = abs(predicted_confidence - actual_quality)
        new_calibration_error = (
            (old_score.calibration_error * old_n + calibration_error) / n
        )

        # Update latency (use call history for p95)
        history = self._call_history[key]
        latencies = [h[1] for h in history]

        # Guard against empty latencies
        if not latencies:
            new_avg_latency = latency_ms
            new_p95_latency = latency_ms
        else:
            new_avg_latency = statistics.mean(latencies)
            new_p95_latency = (
                statistics.quantiles(latencies, n=20)[18]  # 95th percentile
                if len(latencies) >= 20
                else max(latencies)
            )

        # Update cost
        new_total_cost = old_score.total_cost_usd + cost_usd

        # Create updated score (immutable)
        new_score = ProviderScore(
            provider_name=old_score.provider_name,
            model_tier=old_score.model_tier,
            total_calls=new_total_calls,
            successful_calls=new_successful_calls,
            failed_calls=new_failed_calls,
            avg_confidence=new_avg_confidence,
            calibration_error=new_calibration_error,
            avg_latency_ms=new_avg_latency,
            p95_latency_ms=new_p95_latency,
            total_cost_usd=new_total_cost,
            updated_at=now_utc()
        )

        self._scores[key] = new_score

    def _create_new_score(
        self,
        key: tuple[str, str],
        provider_name: str,
        model_tier: str,
        latency_ms: float,
        cost_usd: float,
        success: bool,
        predicted_confidence: float,
        actual_quality: float
    ) -> None:
        """Create new score for provider/tier"""
        calibration_error = abs(predicted_confidence - actual_quality)

        score = ProviderScore(
            provider_name=provider_name,
            model_tier=model_tier,
            total_calls=1,
            successful_calls=1 if success else 0,
            failed_calls=0 if success else 1,
            avg_confidence=predicted_confidence,
            calibration_error=calibration_error,
            avg_latency_ms=latency_ms,
            p95_latency_ms=latency_ms,  # Only one data point
            total_cost_usd=cost_usd,
            updated_at=now_utc()
        )

        self._scores[key] = score

    def _prune_old_history(self, key: tuple[str, str]) -> None:
        """Remove history older than max_history_days"""
        if key not in self._call_history:
            return

        cutoff = now_utc() - timedelta(days=self.max_history_days)
        # CRITICAL: Preserve deque with maxlen to prevent memory leak
        filtered = [
            entry for entry in self._call_history[key]
            if entry[0] > cutoff
        ]
        MAX_HISTORY_PER_PROVIDER = 10000
        self._call_history[key] = deque(filtered, maxlen=MAX_HISTORY_PER_PROVIDER)

    def _calculate_optimization_score(
        self,
        score: ProviderScore,
        optimize_for: str
    ) -> float:
        """
        Calculate optimization score for provider selection

        Returns:
            Score 0-1 (higher is better)
        """
        if optimize_for == "speed":
            # Prefer low latency
            # Normalize: 1000ms = 0.5, 100ms = 0.95
            latency_score = max(0.0, 1.0 - (score.avg_latency_ms / 2000))
            return latency_score * score.success_rate

        elif optimize_for == "cost":
            # Prefer low cost per success
            # Normalize: $0.01 = 0.9, $0.10 = 0.1
            if score.cost_per_success_usd == 0:
                cost_score = 1.0
            else:
                cost_score = max(0.0, 1.0 - (score.cost_per_success_usd / 0.1))
            return cost_score * score.success_rate

        elif optimize_for == "quality":
            # Prefer high confidence and low calibration error
            confidence_score = score.avg_confidence
            calibration_score = max(0.0, 1.0 - score.calibration_error)
            quality_score = (confidence_score + calibration_score) / 2
            return quality_score * score.success_rate

        else:  # "balanced"
            # Balance speed, cost, quality
            latency_score = max(0.0, 1.0 - (score.avg_latency_ms / 2000))

            if score.cost_per_success_usd == 0:
                cost_score = 1.0
            else:
                cost_score = max(0.0, 1.0 - (score.cost_per_success_usd / 0.1))

            confidence_score = score.avg_confidence
            calibration_score = max(0.0, 1.0 - score.calibration_error)
            quality_score = (confidence_score + calibration_score) / 2

            balanced = (
                latency_score * 0.3 +
                cost_score * 0.2 +
                quality_score * 0.5
            )

            return balanced * score.success_rate

    def _stats_by_provider(self) -> dict[str, dict[str, Any]]:
        """Statistics grouped by provider"""
        by_provider = defaultdict(lambda: {
            "total_calls": 0,
            "total_cost_usd": 0.0,
            "avg_success_rate": 0.0,
            "tiers": []
        })

        for (provider, tier), score in self._scores.items():
            by_provider[provider]["total_calls"] += score.total_calls
            by_provider[provider]["total_cost_usd"] += score.total_cost_usd
            by_provider[provider]["tiers"].append(tier)

        # Calculate average success rates
        for provider in by_provider:
            provider_scores = [
                score for (p, _), score in self._scores.items()
                if p == provider
            ]
            by_provider[provider]["avg_success_rate"] = (
                sum(s.success_rate for s in provider_scores) / len(provider_scores)
                if provider_scores else 0.0
            )

        return dict(by_provider)

    def _stats_by_tier(self) -> dict[str, dict[str, Any]]:
        """Statistics grouped by tier"""
        by_tier = defaultdict(lambda: {
            "total_calls": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "providers": []
        })

        for (provider, tier), score in self._scores.items():
            by_tier[tier]["total_calls"] += score.total_calls
            by_tier[tier]["total_cost_usd"] += score.total_cost_usd
            by_tier[tier]["providers"].append(provider)

        # Calculate average latencies
        for tier in by_tier:
            tier_scores = [
                score for (_, t), score in self._scores.items()
                if t == tier
            ]
            by_tier[tier]["avg_latency_ms"] = (
                sum(s.avg_latency_ms for s in tier_scores) / len(tier_scores)
                if tier_scores else 0.0
            )

        return dict(by_tier)

    def _save_to_disk(self) -> None:
        """Save scores to disk (JSON)"""
        if not self.storage_path:
            return

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": "1.0",
                "timestamp": now_utc().isoformat(),
                "scores": [
                    score.to_dict()
                    for score in self._scores.values()
                ],
                # Don't save full call history (too large), just current scores
            }

            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            temp_path.replace(self.storage_path)

            logger.debug(
                "Provider scores saved",
                extra={"path": str(self.storage_path), "count": len(self._scores)}
            )

        except Exception as e:
            logger.error(
                "Failed to save provider scores",
                extra={"path": str(self.storage_path), "error": str(e)},
                exc_info=True
            )

    def _load_from_disk(self) -> None:
        """Load scores from disk (JSON)"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, encoding='utf-8') as f:
                data = json.load(f)

            for score_data in data.get("scores", []):
                score = ProviderScore(
                    provider_name=score_data["provider_name"],
                    model_tier=score_data["model_tier"],
                    total_calls=score_data["total_calls"],
                    successful_calls=score_data["successful_calls"],
                    failed_calls=score_data["failed_calls"],
                    avg_confidence=score_data["avg_confidence"],
                    calibration_error=score_data["calibration_error"],
                    avg_latency_ms=score_data["avg_latency_ms"],
                    p95_latency_ms=score_data["p95_latency_ms"],
                    total_cost_usd=score_data["total_cost_usd"],
                    updated_at=datetime.fromisoformat(score_data["updated_at"])
                )

                key = (score.provider_name, score.model_tier)
                self._scores[key] = score

            logger.info(
                "Provider scores loaded",
                extra={"path": str(self.storage_path), "count": len(self._scores)}
            )

        except Exception as e:
            logger.error(
                "Failed to load provider scores",
                extra={"path": str(self.storage_path), "error": str(e)},
                exc_info=True
            )
