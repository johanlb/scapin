"""
Grimaud — Gardien du PKM

Module de maintenance proactive des notes. Scanne continuellement le PKM,
detecte les problemes (fragmentation, incompletude, obsolescence) et agit
automatiquement si la confiance est suffisante.

Remplace l'ancien systeme Retouche avec une interface unifiee.

Composants:
- Scanner: Selection et priorisation des notes a analyser
- Analyzer: Detection des problemes via pre-analyse + IA
- Executor: Application des actions avec snapshots
- History: Gestion des snapshots et de la corbeille (30 jours)
"""

from src.grimaud.history import GrimaudHistoryManager
from src.grimaud.models import (
    CONFIDENCE_THRESHOLDS,
    GrimaudAction,
    GrimaudActionType,
    GrimaudScanResult,
    GrimaudSnapshot,
    GrimaudStats,
)
from src.grimaud.scanner import GrimaudScanner, NotePriority

__all__ = [
    # Constants
    "CONFIDENCE_THRESHOLDS",
    # Models
    "GrimaudAction",
    "GrimaudActionType",
    "GrimaudScanResult",
    "GrimaudSnapshot",
    "GrimaudStats",
    # History
    "GrimaudHistoryManager",
    # Scanner
    "GrimaudScanner",
    "NotePriority",
]
