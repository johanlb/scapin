"""
Base Provider Protocol

Extended protocol for multi-source journal data providers.
"""

from datetime import date
from typing import Any, Protocol


class MultiSourceHistoryProvider(Protocol):
    """
    Extended protocol for multi-source processing history

    Builds on ProcessingHistoryProvider with additional methods
    for Teams, Calendar, and OmniFocus data.

    Implementations can fetch from:
    - State manager (in-memory)
    - Database (SQLite/Postgres)
    - Log files
    - JSON files
    - External APIs
    """

    # Email (original methods)
    def get_processed_emails(self, target_date: date) -> list[dict[str, Any]]:
        """Get emails processed on the target date"""
        ...

    def get_created_tasks(self, target_date: date) -> list[dict[str, Any]]:
        """Get tasks created on the target date"""
        ...

    def get_decisions(self, target_date: date) -> list[dict[str, Any]]:
        """Get automated decisions on the target date"""
        ...

    def get_known_entities(self) -> set[str]:
        """Get set of known entity identifiers (emails, names)"""
        ...

    # Teams
    def get_teams_messages(self, target_date: date) -> list[dict[str, Any]]:
        """Get Teams messages processed on the target date"""
        ...

    # Calendar
    def get_calendar_events(self, target_date: date) -> list[dict[str, Any]]:
        """Get Calendar events on the target date"""
        ...

    # OmniFocus
    def get_omnifocus_items(self, target_date: date) -> list[dict[str, Any]]:
        """Get OmniFocus task activity on the target date"""
        ...
