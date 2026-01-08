"""
Source adapters for CrossSourceEngine.

Each adapter implements the SourceAdapter protocol to provide
search capabilities for a specific data source.
"""

from src.passepartout.cross_source.adapters.base import BaseAdapter, SourceAdapter
from src.passepartout.cross_source.adapters.calendar_adapter import CalendarAdapter
from src.passepartout.cross_source.adapters.email_adapter import EmailAdapter
from src.passepartout.cross_source.adapters.teams_adapter import TeamsAdapter

__all__ = [
    "BaseAdapter",
    "CalendarAdapter",
    "EmailAdapter",
    "SourceAdapter",
    "TeamsAdapter",
]
