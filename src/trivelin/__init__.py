"""
Trivelin - Event Perception Module

The perception and triage valet of Scapin's architecture.

Named after Trivelin from commedia dell'arte - an astute and observant valet
who notices details others miss.

Trivelin handles:
- Email perception and normalization
- Event triage and prioritization
- Multi-source event intake (Teams, Calendar, OmniFocus, etc.)
- V2 Workflow processing with CrossSource, Patterns, and Clarification
"""

from src.trivelin.action_factory import ActionFactory
from src.trivelin.omnifocus_processor import OmniFocusProcessor
from src.trivelin.processor import EmailProcessor
from src.trivelin.v2_processor import (
    V2EmailProcessor,
    V2ProcessingResult,
    create_v2_processor,
)

__all__ = [
    "ActionFactory",
    "EmailProcessor",
    "OmniFocusProcessor",
    # V2 Workflow (recommended)
    "V2EmailProcessor",
    "V2ProcessingResult",
    "create_v2_processor",
]
