"""
Scapin Core Models

This module contains core data models for Workflow v2.1.
"""

from src.core.models.v2_models import (
    AnalysisResult,
    ContextNote,
    EnrichmentResult,
    Extraction,
    NoteResult,
)

__all__ = [
    "Extraction",
    "AnalysisResult",
    "EnrichmentResult",
    "ContextNote",
    "NoteResult",
]
