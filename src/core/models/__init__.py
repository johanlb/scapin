"""
Scapin Core Models

This module contains core data models for Workflow v2.1 and Péripéties v2.4.
"""

from src.core.models.peripetie import (
    ErrorType,
    PeripetieError,
    PeripetieResolution,
    PeripetieSnooze,
    PeripetieState,
    PeripetieTimestamps,
    ResolutionType,
    ResolvedBy,
    migrate_legacy_status,
    state_to_tab,
)
from src.core.models.v2_models import (
    AnalysisResult,
    ContextNote,
    EnrichmentResult,
    Extraction,
    NoteResult,
)

__all__ = [
    # v2.1 models
    "Extraction",
    "AnalysisResult",
    "EnrichmentResult",
    "ContextNote",
    "NoteResult",
    # v2.4 Péripéties models
    "PeripetieState",
    "ResolutionType",
    "ErrorType",
    "ResolvedBy",
    "PeripetieResolution",
    "PeripetieSnooze",
    "PeripetieError",
    "PeripetieTimestamps",
    "migrate_legacy_status",
    "state_to_tab",
]
