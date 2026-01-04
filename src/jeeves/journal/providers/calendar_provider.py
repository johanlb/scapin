"""
Calendar History Provider

Provides Calendar event history for journal generation.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("jeeves.journal.providers.calendar")


@dataclass
class CalendarHistoryProvider:
    """
    Provides Calendar event history from JSON log files

    Reads from daily Calendar logs stored in data directory.
    Format: data/logs/calendar_YYYY-MM-DD.json
    """
    data_dir: Path = field(default_factory=lambda: Path("data"))

    def get_calendar_events(self, target_date: date) -> list[dict[str, Any]]:
        """
        Get Calendar events on the target date

        Returns list of dicts with:
        - event_id
        - title
        - start_time
        - end_time
        - action
        - attendees
        - location
        - is_online
        - response_status
        - processed_at
        """
        log_file = self._get_log_file(target_date)
        if not log_file.exists():
            logger.debug(f"No Calendar log found for {target_date}")
            return []

        try:
            data = json.loads(log_file.read_text())
            events = data.get("events", [])

            # Ensure all required fields are present
            result = []
            for event in events:
                if all(k in event for k in ("event_id", "title", "start_time", "end_time")):
                    # Set defaults for optional fields
                    event.setdefault("action", "attended")
                    event.setdefault("attendees", [])
                    event.setdefault("location", None)
                    event.setdefault("is_online", False)
                    event.setdefault("notes", None)
                    event.setdefault("response_status", None)
                    event.setdefault("processed_at", now_utc().isoformat())
                    result.append(event)

            logger.debug(f"Found {len(result)} Calendar events for {target_date}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Calendar log: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to read Calendar log: {e}")
            return []

    def _get_log_file(self, target_date: date) -> Path:
        """Get path to Calendar log file for date"""
        return self.data_dir / "logs" / f"calendar_{target_date.isoformat()}.json"

    # Stub methods to satisfy protocol
    def get_processed_emails(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use email provider"""
        return []

    def get_created_tasks(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use email provider"""
        return []

    def get_decisions(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use email provider"""
        return []

    def get_known_entities(self) -> set[str]:
        """Not implemented - use email provider"""
        return set()

    def get_teams_messages(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use teams provider"""
        return []

    def get_omnifocus_items(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use omnifocus provider"""
        return []
