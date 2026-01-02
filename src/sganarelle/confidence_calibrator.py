"""
Sganarelle Confidence Calibrator

Calibre les scores de confiance prédits pour mieux refléter la probabilité
réelle de correctness. Utilise le feedback historique pour ajuster.

Thread-safe avec persistence des paramètres de calibration.
"""

import json
import logging
import statistics
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Optional

from src.core.events.universal_event import now_utc
from src.sganarelle.types import FeedbackAnalysis

logger = logging.getLogger(__name__)


class CalibrationError(Exception):
    """Erreur de calibration"""
    pass


class ConfidenceCalibrator:
    """
    Calibrateur de confiance

    Apprend à mapper les confidences prédites → probabilités réelles
    de correctness en utilisant le feedback historique.

    Utilise une approche simple de binning avec smoothing.
    Thread-safe avec persistence.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        num_bins: int = 10,
        min_samples_per_bin: int = 5,
        smoothing_factor: float = 0.1,
        auto_save: bool = True
    ):
        """
        Initialize confidence calibrator

        Args:
            storage_path: Chemin fichier JSON pour persistence
            num_bins: Nombre de bins de confiance (default: 10)
            min_samples_per_bin: Échantillons minimum pour calibration fiable
            smoothing_factor: Facteur de lissage (0-1, plus petit = plus lisse)
            auto_save: Si True, save après chaque update

        Raises:
            ValueError: Si paramètres invalides
        """
        if num_bins < 2:
            raise ValueError(f"num_bins doit être >= 2, got {num_bins}")
        if min_samples_per_bin < 1:
            raise ValueError(
                f"min_samples_per_bin doit être >= 1, got {min_samples_per_bin}"
            )
        if not (0 <= smoothing_factor <= 1):
            raise ValueError(
                f"smoothing_factor doit être 0-1, got {smoothing_factor}"
            )

        self.storage_path = storage_path
        self.num_bins = num_bins
        self.min_samples_per_bin = min_samples_per_bin
        self.smoothing_factor = smoothing_factor
        self.auto_save = auto_save

        # Bin edges (0.0, 0.1, 0.2, ..., 1.0)
        self.bin_edges = [i / num_bins for i in range(num_bins + 1)]

        # Storage: bin_index → deque of (predicted, actual) pairs
        # Limited to prevent memory leaks (max 1000 samples per bin)
        MAX_SAMPLES_PER_BIN = 1000
        self._calibration_data: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=MAX_SAMPLES_PER_BIN)
        )

        # Cached calibration map: predicted → calibrated
        # Recalculated when data changes
        self._calibration_map: Optional[dict[float, float]] = None

        # Statistics
        self._total_samples = 0
        self._last_calibration: Optional[datetime] = None

        self._lock = RLock()

        # Load existing calibration
        if storage_path and storage_path.exists():
            self._load_from_disk()

        logger.info(
            "ConfidenceCalibrator initialized",
            extra={
                "storage_path": str(storage_path) if storage_path else "memory",
                "num_bins": num_bins,
                "samples": self._total_samples
            }
        )

    def add_observation(
        self,
        predicted_confidence: float,
        actual_correctness: float
    ) -> None:
        """
        Ajoute une observation pour calibration

        Args:
            predicted_confidence: Confiance prédite (0-1)
            actual_correctness: Correctness réelle (0-1)

        Raises:
            ValueError: Si valeurs invalides
        """
        if not (0 <= predicted_confidence <= 1):
            raise ValueError(
                f"predicted_confidence doit être 0-1, got {predicted_confidence}"
            )
        if not (0 <= actual_correctness <= 1):
            raise ValueError(
                f"actual_correctness doit être 0-1, got {actual_correctness}"
            )

        # Determine bin
        bin_idx = self._get_bin_index(predicted_confidence)

        with self._lock:
            self._calibration_data[bin_idx].append(
                (predicted_confidence, actual_correctness)
            )
            self._total_samples += 1

            # Invalidate cache
            self._calibration_map = None

            logger.debug(
                "Calibration observation added",
                extra={
                    "predicted": predicted_confidence,
                    "actual": actual_correctness,
                    "bin": bin_idx,
                    "total_samples": self._total_samples
                }
            )

            if self.auto_save and self._total_samples % 10 == 0:
                # Save every 10 samples
                self._save_to_disk()

    def add_from_feedback(
        self,
        predicted_confidence: float,
        feedback_analysis: FeedbackAnalysis
    ) -> None:
        """
        Ajoute observation depuis FeedbackAnalysis

        Args:
            predicted_confidence: Confiance prédite
            feedback_analysis: Analyse du feedback
        """
        # Use correctness_score as proxy for actual correctness
        actual_correctness = feedback_analysis.correctness_score

        self.add_observation(predicted_confidence, actual_correctness)

    def calibrate(self, predicted_confidence: float) -> float:
        """
        Calibre une confiance prédite

        Args:
            predicted_confidence: Confiance brute du modèle (0-1)

        Returns:
            Confiance calibrée (0-1)

        Raises:
            ValueError: Si confiance invalide
        """
        if not (0 <= predicted_confidence <= 1):
            raise ValueError(
                f"predicted_confidence doit être 0-1, got {predicted_confidence}"
            )

        with self._lock:
            # Build calibration map if needed
            if self._calibration_map is None:
                self._build_calibration_map()

            # If not enough data, return original
            if self._total_samples < self.min_samples_per_bin:
                logger.debug(
                    "Insufficient data for calibration",
                    extra={"samples": self._total_samples}
                )
                return predicted_confidence

            # Find nearest calibrated value
            calibrated = self._lookup_calibration(predicted_confidence)

            logger.debug(
                "Confidence calibrated",
                extra={
                    "predicted": predicted_confidence,
                    "calibrated": calibrated,
                    "adjustment": calibrated - predicted_confidence
                }
            )

            return calibrated

    def calibrate_batch(
        self,
        confidences: list[float]
    ) -> list[float]:
        """
        Calibre un batch de confidences

        Args:
            confidences: Liste de confidences brutes

        Returns:
            Liste de confidences calibrées
        """
        return [self.calibrate(conf) for conf in confidences]

    def get_calibration_error(self) -> float:
        """
        Calculate expected calibration error (ECE)

        ECE mesure l'écart entre confiance prédite et accuracy réelle.
        Plus petit = meilleure calibration.

        Returns:
            ECE (0-1, plus petit est mieux)
        """
        with self._lock:
            if self._total_samples == 0:
                return 0.0

            total_error = 0.0
            total_weight = 0

            for bin_idx in range(self.num_bins):
                if bin_idx not in self._calibration_data:
                    continue

                data = self._calibration_data[bin_idx]
                if not data:
                    continue

                # Average predicted and actual for this bin
                avg_predicted = statistics.mean(p for p, _ in data)
                avg_actual = statistics.mean(a for _, a in data)

                # Weighted by number of samples
                weight = len(data)
                error = abs(avg_predicted - avg_actual) * weight

                total_error += error
                total_weight += weight

            if total_weight == 0:
                return 0.0

            ece = total_error / total_weight

            return ece

    def get_stats(self) -> dict[str, Any]:
        """
        Statistiques de calibration

        Returns:
            Dict avec statistiques
        """
        with self._lock:
            ece = self.get_calibration_error()

            # Per-bin stats
            bin_stats = []
            for bin_idx in range(self.num_bins):
                if bin_idx not in self._calibration_data:
                    continue

                data = self._calibration_data[bin_idx]
                if not data:
                    continue

                bin_stats.append({
                    "bin_index": bin_idx,
                    "bin_range": (self.bin_edges[bin_idx], self.bin_edges[bin_idx + 1]),
                    "samples": len(data),
                    "avg_predicted": statistics.mean(p for p, _ in data),
                    "avg_actual": statistics.mean(a for _, a in data),
                    "error": abs(
                        statistics.mean(p for p, _ in data) -
                        statistics.mean(a for _, a in data)
                    )
                })

            return {
                "total_samples": self._total_samples,
                "expected_calibration_error": ece,
                "last_calibration": (
                    self._last_calibration.isoformat()
                    if self._last_calibration
                    else None
                ),
                "bin_stats": bin_stats,
                "is_well_calibrated": ece < 0.1  # Threshold
            }

    def reset(self) -> None:
        """Reset calibration (pour testing ou nouveau départ)"""
        with self._lock:
            self._calibration_data.clear()
            self._calibration_map = None
            self._total_samples = 0
            self._last_calibration = None

            logger.warning("Calibration data reset")

            if self.auto_save:
                self._save_to_disk()

    def save(self) -> None:
        """Force save to disk"""
        if self.storage_path:
            self._save_to_disk()

    # Private methods

    def _get_bin_index(self, confidence: float) -> int:
        """Get bin index for confidence value"""
        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        # Find bin
        for i in range(self.num_bins):
            if confidence <= self.bin_edges[i + 1]:
                return i

        # Should not reach here, but handle edge case
        return self.num_bins - 1

    def _build_calibration_map(self) -> None:
        """Build calibration lookup map"""
        calibration_map = {}

        for bin_idx in range(self.num_bins):
            if bin_idx not in self._calibration_data:
                # No data for this bin, use identity mapping
                bin_center = (self.bin_edges[bin_idx] + self.bin_edges[bin_idx + 1]) / 2
                calibration_map[bin_center] = bin_center
                continue

            data = self._calibration_data[bin_idx]
            if len(data) < self.min_samples_per_bin:
                # Insufficient data, use identity with smoothing
                bin_center = (self.bin_edges[bin_idx] + self.bin_edges[bin_idx + 1]) / 2
                avg_actual = statistics.mean(a for _, a in data) if data else bin_center
                # Smooth towards identity
                calibrated = (
                    self.smoothing_factor * bin_center +
                    (1 - self.smoothing_factor) * avg_actual
                )
                calibration_map[bin_center] = calibrated
            else:
                # Sufficient data, use average actual
                bin_center = (self.bin_edges[bin_idx] + self.bin_edges[bin_idx + 1]) / 2
                avg_actual = statistics.mean(a for _, a in data)
                calibration_map[bin_center] = avg_actual

        self._calibration_map = calibration_map
        self._last_calibration = now_utc()

        logger.debug(
            "Calibration map built",
            extra={
                "bins": len(calibration_map),
                "samples": self._total_samples
            }
        )

    def _lookup_calibration(self, predicted: float) -> float:
        """Lookup calibrated value from map"""
        if self._calibration_map is None:
            return predicted

        # Find nearest bin center
        bin_idx = self._get_bin_index(predicted)
        bin_center = (self.bin_edges[bin_idx] + self.bin_edges[bin_idx + 1]) / 2

        calibrated = self._calibration_map.get(bin_center, predicted)

        return max(0.0, min(1.0, calibrated))

    def _save_to_disk(self) -> None:
        """Save calibration data to disk (JSON)"""
        if not self.storage_path:
            return

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert calibration data to serializable format
            serializable_data = {}
            for bin_idx, data in self._calibration_data.items():
                serializable_data[str(bin_idx)] = [
                    {"predicted": p, "actual": a}
                    for p, a in data
                ]

            data = {
                "version": "1.0",
                "timestamp": now_utc().isoformat(),
                "total_samples": self._total_samples,
                "last_calibration": (
                    self._last_calibration.isoformat()
                    if self._last_calibration
                    else None
                ),
                "calibration_data": serializable_data
            }

            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            temp_path.replace(self.storage_path)

            logger.debug(
                "Calibration data saved",
                extra={
                    "path": str(self.storage_path),
                    "samples": self._total_samples
                }
            )

        except Exception as e:
            logger.error(
                "Failed to save calibration data",
                extra={"path": str(self.storage_path), "error": str(e)},
                exc_info=True
            )

    def _load_from_disk(self) -> None:
        """Load calibration data from disk (JSON)"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, encoding='utf-8') as f:
                data = json.load(f)

            self._total_samples = data.get("total_samples", 0)

            if data.get("last_calibration"):
                self._last_calibration = datetime.fromisoformat(
                    data["last_calibration"]
                )

            # Load calibration data
            calibration_data = data.get("calibration_data", {})
            for bin_idx_str, entries in calibration_data.items():
                bin_idx = int(bin_idx_str)
                self._calibration_data[bin_idx] = [
                    (entry["predicted"], entry["actual"])
                    for entry in entries
                ]

            # Invalidate cache
            self._calibration_map = None

            logger.info(
                "Calibration data loaded",
                extra={
                    "path": str(self.storage_path),
                    "samples": self._total_samples
                }
            )

        except Exception as e:
            logger.error(
                "Failed to load calibration data",
                extra={"path": str(self.storage_path), "error": str(e)},
                exc_info=True
            )


class TemperatureScaling:
    """
    Alternative calibration: Temperature scaling

    Plus simple que binning, juste un paramètre de température.
    Utile pour calibration rapide avec peu de données.
    """

    def __init__(self, initial_temperature: float = 1.0):
        """
        Initialize temperature scaling

        Args:
            initial_temperature: Température initiale (1.0 = pas de scaling)
        """
        self.temperature = initial_temperature
        self._observations: list[tuple[float, float]] = []

    def add_observation(
        self,
        predicted_confidence: float,
        actual_correctness: float
    ) -> None:
        """Add observation"""
        self._observations.append((predicted_confidence, actual_correctness))

    def fit(self) -> float:
        """
        Fit temperature parameter

        Returns:
            Optimal temperature
        """
        if len(self._observations) < 5:
            return self.temperature

        # Simple approach: find temperature that minimizes calibration error
        # In practice, would use gradient descent on log likelihood

        best_temp = 1.0
        best_error = float('inf')

        for temp in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            error = self._calculate_error_for_temp(temp)
            if error < best_error:
                best_error = error
                best_temp = temp

        self.temperature = best_temp
        return best_temp

    def calibrate(self, confidence: float) -> float:
        """Calibrate with temperature"""
        # Temperature scaling: p' = p^(1/T)
        # Higher T → lower confidence
        # Lower T → higher confidence
        if self.temperature <= 0:
            self.temperature = 1.0

        calibrated = confidence ** (1.0 / self.temperature)
        return max(0.0, min(1.0, calibrated))

    def _calculate_error_for_temp(self, temp: float) -> float:
        """Calculate calibration error for given temperature"""
        if not self._observations:
            return 0.0

        total_error = 0.0
        for predicted, actual in self._observations:
            calibrated = predicted ** (1.0 / temp)
            error = abs(calibrated - actual)
            total_error += error

        return total_error / len(self._observations)
