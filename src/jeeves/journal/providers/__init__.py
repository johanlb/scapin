"""
Journal Providers Module

Multi-source data providers for journal generation.
Providers fetch processing history from different sources:
- Email (existing JsonFileHistoryProvider)
- Teams (Microsoft Teams messages)
- Calendar (Microsoft Calendar events)
- OmniFocus (macOS task manager)
"""

from src.jeeves.journal.providers.base import MultiSourceHistoryProvider
from src.jeeves.journal.providers.calendar_provider import CalendarHistoryProvider
from src.jeeves.journal.providers.multi_source_aggregator import (
    MultiSourceAggregator,
)
from src.jeeves.journal.providers.omnifocus_provider import OmniFocusHistoryProvider
from src.jeeves.journal.providers.teams_provider import TeamsHistoryProvider

__all__ = [
    "MultiSourceHistoryProvider",
    "TeamsHistoryProvider",
    "CalendarHistoryProvider",
    "OmniFocusHistoryProvider",
    "MultiSourceAggregator",
]
