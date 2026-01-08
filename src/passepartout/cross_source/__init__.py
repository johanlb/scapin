"""
CrossSourceEngine - Unified search across all data sources.

This module provides intelligent cross-source searching capabilities for Scapin,
allowing retrieval of relevant information from emails, calendar, Teams,
WhatsApp, files, and web search.
"""

from src.passepartout.cross_source.cache import CrossSourceCache
from src.passepartout.cross_source.config import CrossSourceConfig
from src.passepartout.cross_source.engine import CrossSourceEngine
from src.passepartout.cross_source.models import (
    CrossSourceRequest,
    CrossSourceResult,
    LinkedSource,
    SourceItem,
)

__all__ = [
    "CrossSourceCache",
    "CrossSourceConfig",
    "CrossSourceEngine",
    "CrossSourceRequest",
    "CrossSourceResult",
    "LinkedSource",
    "SourceItem",
]
