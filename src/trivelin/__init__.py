"""
Trivelin - Event Perception Module

The perception and triage valet of Scapin's architecture.

Named after Trivelin from commedia dell'arte - an astute and observant valet
who notices details others miss.

Trivelin handles:
- Email perception and normalization
- Event triage and prioritization
- Future: Multi-source event intake (Teams, chat, documents, etc.)
"""

from src.trivelin.processor import EmailProcessor

__all__ = [
    "EmailProcessor",
]
