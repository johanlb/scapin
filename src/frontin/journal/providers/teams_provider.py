"""
Teams History Provider

Provides Teams message history for journal generation.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("frontin.journal.providers.teams")


@dataclass
class TeamsHistoryProvider:
    """
    Provides Teams message history from JSON log files

    Reads from daily Teams processing logs stored in data directory.
    Format: data/logs/teams_YYYY-MM-DD.json
    """
    data_dir: Path = field(default_factory=lambda: Path("data"))

    def get_teams_messages(self, target_date: date) -> list[dict[str, Any]]:
        """
        Get Teams messages processed on the target date

        Returns list of dicts with:
        - message_id
        - chat_name
        - sender
        - preview
        - action
        - confidence
        - processed_at
        """
        log_file = self._get_log_file(target_date)
        if not log_file.exists():
            logger.debug(f"No Teams log found for {target_date}")
            return []

        try:
            data = json.loads(log_file.read_text())
            messages = data.get("messages", [])

            # Ensure all required fields are present
            result = []
            for msg in messages:
                if all(k in msg for k in ("message_id", "chat_name", "sender")):
                    # Set defaults for optional fields
                    msg.setdefault("preview", "")
                    msg.setdefault("action", "read")
                    msg.setdefault("confidence", 80)
                    msg.setdefault("processed_at", now_utc().isoformat())
                    result.append(msg)

            logger.debug(f"Found {len(result)} Teams messages for {target_date}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Teams log: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to read Teams log: {e}")
            return []

    def _get_log_file(self, target_date: date) -> Path:
        """Get path to Teams log file for date"""
        return self.data_dir / "logs" / f"teams_{target_date.isoformat()}.json"

    # Stub methods to satisfy protocol (actual data from other providers)
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

    def get_calendar_events(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use calendar provider"""
        return []

    def get_omnifocus_items(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use omnifocus provider"""
        return []
