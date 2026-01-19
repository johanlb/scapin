"""
Multi-Source Aggregator

Combines all source providers into a single interface for journal generation.
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from src.frontin.journal.generator import JsonFileHistoryProvider
from src.frontin.journal.providers.calendar_provider import CalendarHistoryProvider
from src.frontin.journal.providers.omnifocus_provider import OmniFocusHistoryProvider
from src.frontin.journal.providers.teams_provider import TeamsHistoryProvider
from src.monitoring.logger import get_logger

logger = get_logger("frontin.journal.providers.aggregator")


@dataclass
class MultiSourceAggregator:
    """
    Aggregates all source providers into a unified interface

    Implements the MultiSourceHistoryProvider protocol by delegating
    to specialized providers for each data source.

    Usage:
        aggregator = MultiSourceAggregator()
        emails = aggregator.get_processed_emails(date.today())
        teams = aggregator.get_teams_messages(date.today())
        calendar = aggregator.get_calendar_events(date.today())
        omnifocus = aggregator.get_omnifocus_items(date.today())
    """
    data_dir: Path = field(default_factory=lambda: Path("data"))

    # Individual providers
    _email_provider: Optional[JsonFileHistoryProvider] = None
    _teams_provider: Optional[TeamsHistoryProvider] = None
    _calendar_provider: Optional[CalendarHistoryProvider] = None
    _omnifocus_provider: Optional[OmniFocusHistoryProvider] = None

    def __post_init__(self) -> None:
        """Initialize all providers"""
        if self._email_provider is None:
            self._email_provider = JsonFileHistoryProvider(data_dir=self.data_dir)
        if self._teams_provider is None:
            self._teams_provider = TeamsHistoryProvider(data_dir=self.data_dir)
        if self._calendar_provider is None:
            self._calendar_provider = CalendarHistoryProvider(data_dir=self.data_dir)
        if self._omnifocus_provider is None:
            self._omnifocus_provider = OmniFocusHistoryProvider()

        logger.debug("Multi-source aggregator initialized")

    # Email methods (delegated to email provider)
    def get_processed_emails(self, target_date: date) -> list[dict[str, Any]]:
        """Get emails processed on the target date"""
        return self._email_provider.get_processed_emails(target_date)

    def get_created_tasks(self, target_date: date) -> list[dict[str, Any]]:
        """Get tasks created on the target date"""
        return self._email_provider.get_created_tasks(target_date)

    def get_decisions(self, target_date: date) -> list[dict[str, Any]]:
        """Get automated decisions on the target date"""
        return self._email_provider.get_decisions(target_date)

    def get_known_entities(self) -> set[str]:
        """Get set of known entity identifiers"""
        return self._email_provider.get_known_entities()

    # Teams methods
    def get_teams_messages(self, target_date: date) -> list[dict[str, Any]]:
        """Get Teams messages processed on the target date"""
        return self._teams_provider.get_teams_messages(target_date)

    # Calendar methods
    def get_calendar_events(self, target_date: date) -> list[dict[str, Any]]:
        """Get Calendar events on the target date"""
        return self._calendar_provider.get_calendar_events(target_date)

    # OmniFocus methods
    def get_omnifocus_items(self, target_date: date) -> list[dict[str, Any]]:
        """Get OmniFocus task activity on the target date"""
        return self._omnifocus_provider.get_omnifocus_items(target_date)

    def get_all_sources(
        self,
        target_date: date,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get data from all sources in one call

        Returns:
            Dict with keys: emails, tasks, decisions, teams, calendar, omnifocus
        """
        return {
            "emails": self.get_processed_emails(target_date),
            "tasks": self.get_created_tasks(target_date),
            "decisions": self.get_decisions(target_date),
            "teams": self.get_teams_messages(target_date),
            "calendar": self.get_calendar_events(target_date),
            "omnifocus": self.get_omnifocus_items(target_date),
        }

    def get_source_summary(self, target_date: date) -> dict[str, int]:
        """
        Get count summary for all sources

        Returns:
            Dict with counts for each source type
        """
        data = self.get_all_sources(target_date)
        return {
            "emails": len(data["emails"]),
            "tasks": len(data["tasks"]),
            "decisions": len(data["decisions"]),
            "teams": len(data["teams"]),
            "calendar": len(data["calendar"]),
            "omnifocus": len(data["omnifocus"]),
        }
