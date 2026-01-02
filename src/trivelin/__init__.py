"""
Trivelin - Event Perception Module

The perception and triage valet of Scapin's architecture.

Named after Trivelin from commedia dell'arte - an astute and observant valet
who notices details others miss.

Trivelin handles:
- Email perception and normalization
- Event triage and prioritization
- Cognitive pipeline orchestration (Phase 1.0)
- Future: Multi-source event intake (Teams, chat, documents, etc.)
"""

from src.trivelin.action_factory import ActionFactory
from src.trivelin.cognitive_pipeline import (
    CognitivePipeline,
    CognitivePipelineResult,
    CognitiveTimeoutError,
)
from src.trivelin.processor import EmailProcessor

__all__ = [
    "ActionFactory",
    "CognitivePipeline",
    "CognitivePipelineResult",
    "CognitiveTimeoutError",
    "EmailProcessor",
]
