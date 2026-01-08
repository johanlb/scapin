"""
Source adapters for CrossSourceEngine.

Each adapter implements the SourceAdapter protocol to provide
search capabilities for a specific data source.

Use AdapterFactory for centralized adapter creation and management.
"""

from src.passepartout.cross_source.adapters.base import (
    AdapterAuthenticationError,
    AdapterConnectionError,
    AdapterError,
    AdapterRateLimitError,
    AdapterTimeoutError,
    BaseAdapter,
    SourceAdapter,
    log_search_metrics,
    safe_search,
)
from src.passepartout.cross_source.adapters.calendar_adapter import CalendarAdapter
from src.passepartout.cross_source.adapters.email_adapter import EmailAdapter
from src.passepartout.cross_source.adapters.factory import (
    AdapterFactory,
    create_default_factory,
    get_default_factory,
    reset_default_factory,
)
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
    # Error types
    "AdapterAuthenticationError",
    "AdapterConnectionError",
    "AdapterError",
    "AdapterRateLimitError",
    "AdapterTimeoutError",
    # Base classes
    "AdapterFactory",
    "BaseAdapter",
    "SourceAdapter",
    # Decorators
    "log_search_metrics",
    "safe_search",
    # Adapters
    "CalendarAdapter",
    "DuckDuckGoAdapter",
    "EmailAdapter",
    "FilesAdapter",
    "ICloudCalendarAdapter",
    "TeamsAdapter",
    "WebAdapter",
    "WhatsAppAdapter",
    # Factory functions
    "create_default_factory",
    "create_web_adapter",
    "get_default_factory",
    "reset_default_factory",
]
