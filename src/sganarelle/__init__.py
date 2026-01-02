"""
Sganarelle - Learning Engine

Ferme la boucle cognitive en apprenant de chaque décision.
Met à jour la base de connaissances, calibre la confiance, et identifie des patterns.
"""

from src.sganarelle.confidence_calibrator import ConfidenceCalibrator
from src.sganarelle.feedback_processor import FeedbackProcessor
from src.sganarelle.knowledge_updater import KnowledgeUpdater
from src.sganarelle.learning_engine import LearningEngine
from src.sganarelle.pattern_store import PatternStore
from src.sganarelle.provider_tracker import ProviderTracker
from src.sganarelle.types import (
    FeedbackAnalysis,
    KnowledgeUpdate,
    LearningResult,
    Pattern,
    ProviderScore,
    UserFeedback,
)

__all__ = [
    # Types
    "UserFeedback",
    "KnowledgeUpdate",
    "Pattern",
    "ProviderScore",
    "LearningResult",
    "FeedbackAnalysis",
    # Classes
    "LearningEngine",
    "FeedbackProcessor",
    "KnowledgeUpdater",
    "PatternStore",
    "ProviderTracker",
    "ConfidenceCalibrator",
]

__version__ = "0.1.0"
