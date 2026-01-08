"""
Source adapters for CrossSourceEngine.

Each adapter implements the SourceAdapter protocol to provide
search capabilities for a specific data source.
"""

from src.passepartout.cross_source.adapters.base import BaseAdapter, SourceAdapter
from src.passepartout.cross_source.adapters.calendar_adapter import CalendarAdapter
from src.passepartout.cross_source.adapters.email_adapter import EmailAdapter
from src.passepartout.cross_source.adapters.files_adapter import FilesAdapter
from src.passepartout.cross_source.adapters.icloud_calendar_adapter import (
    ICloudCalendarAdapter,
)
from src.passepartout.cross_source.adapters.teams_adapter import TeamsAdapter
from src.passepartout.cross_source.adapters.web_adapter import (
    DuckDuckGoAdapter,
    WebAdapter,
    create_web_adapter,
)
from src.passepartout.cross_source.adapters.whatsapp_adapter import WhatsAppAdapter

__all__ = [
    "BaseAdapter",
    "CalendarAdapter",
    "DuckDuckGoAdapter",
    "EmailAdapter",
    "FilesAdapter",
    "ICloudCalendarAdapter",
    "SourceAdapter",
    "TeamsAdapter",
    "WebAdapter",
    "WhatsAppAdapter",
    "create_web_adapter",
]
