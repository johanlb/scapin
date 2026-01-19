"""
Status Service

Provides real-time system operational status.
"""

import time
from datetime import datetime, timezone

from src.core.config_manager import get_config
from src.core.state_manager import ProcessingState, get_state_manager
from src.frontin.api.models.responses import (
    ComponentStatus,
    SessionStatsResponse,
    SystemStatusResponse,
)
from src.frontin.api.websocket.manager import get_connection_manager
from src.monitoring.logger import get_logger

logger = get_logger("api.status_service")

# Track server start time
_start_time = time.time()


class StatusService:
    """Service for providing real-time system status"""

    def __init__(self) -> None:
        """Initialize status service"""
        self._config = get_config()
        self._state = get_state_manager()

    async def get_status(self) -> SystemStatusResponse:
        """
        Get current system status

        Returns:
            SystemStatusResponse with real-time operational state
        """
        logger.debug("Getting system status")

        # Get processing state
        processing_state = self._state.processing_state
        state_str = processing_state.value

        # Get current task description
        current_task = self._get_current_task(processing_state)

        # Get WebSocket connection count
        ws_manager = get_connection_manager()
        active_connections = ws_manager.active_connection_count

        # Build component statuses
        components = await self._build_component_statuses()

        # Get session stats
        session_stats = self._get_session_stats()

        # Get last activity
        last_activity = self._get_last_activity()

        uptime = time.time() - _start_time

        return SystemStatusResponse(
            state=state_str,
            current_task=current_task,
            active_connections=active_connections,
            components=components,
            session_stats=session_stats,
            uptime_seconds=uptime,
            last_activity=last_activity,
        )

    def _get_current_task(self, state: ProcessingState) -> str | None:
        """Get description of current task based on state"""
        if state == ProcessingState.IDLE:
            return None

        if state == ProcessingState.RUNNING:
            # Check what's being processed
            current_email = self._state.get("current_email_subject")
            if current_email:
                return f"Processing email: {current_email[:50]}..."

            current_source = self._state.get("processing_source")
            if current_source:
                return f"Processing {current_source}"

            return "Processing..."

        if state == ProcessingState.PAUSED:
            return "Processing paused"

        if state == ProcessingState.ERROR:
            error_msg = self._state.get("last_error")
            if error_msg:
                return f"Error: {error_msg[:100]}"
            return "Error occurred"

        return None

    async def _build_component_statuses(self) -> list[ComponentStatus]:
        """Build status for each system component"""
        components: list[ComponentStatus] = []

        # Email component
        email_accounts = self._config.email.get_enabled_accounts()
        if email_accounts:
            last_email_poll = self._state.get("email_last_poll")
            components.append(
                ComponentStatus(
                    name="email",
                    state="active" if email_accounts else "disabled",
                    last_activity=self._parse_datetime(last_email_poll),
                    details=f"{len(email_accounts)} account(s) configured",
                )
            )
        else:
            components.append(
                ComponentStatus(
                    name="email",
                    state="disabled",
                    last_activity=None,
                    details="No accounts configured",
                )
            )

        # Teams component
        if self._config.teams.enabled:
            last_teams_poll = self._state.get("teams_last_poll")
            teams_state = "active"
            if self._state.get("teams_error"):
                teams_state = "error"
            components.append(
                ComponentStatus(
                    name="teams",
                    state=teams_state,
                    last_activity=self._parse_datetime(last_teams_poll),
                    details=None,
                )
            )
        else:
            components.append(
                ComponentStatus(
                    name="teams",
                    state="disabled",
                    last_activity=None,
                    details="Integration disabled",
                )
            )

        # Calendar component
        if self._config.calendar.enabled:
            last_calendar_poll = self._state.get("calendar_last_poll")
            calendar_state = "active"
            if self._state.get("calendar_error"):
                calendar_state = "error"
            components.append(
                ComponentStatus(
                    name="calendar",
                    state=calendar_state,
                    last_activity=self._parse_datetime(last_calendar_poll),
                    details=None,
                )
            )
        else:
            components.append(
                ComponentStatus(
                    name="calendar",
                    state="disabled",
                    last_activity=None,
                    details="Integration disabled",
                )
            )

        # Notes component (always available)
        notes_state = "active"
        last_notes_activity = self._state.get("notes_last_activity")
        components.append(
            ComponentStatus(
                name="notes",
                state=notes_state,
                last_activity=self._parse_datetime(last_notes_activity),
                details=None,
            )
        )

        # Queue component
        queue_size = self._state.get("queue_size", 0) or 0
        components.append(
            ComponentStatus(
                name="queue",
                state="active" if queue_size > 0 else "idle",
                last_activity=None,
                details=f"{queue_size} items pending" if queue_size > 0 else "Empty",
            )
        )

        return components

    def _get_session_stats(self) -> SessionStatsResponse:
        """Get current session statistics"""
        stats = self._state.stats

        actions_taken = stats.archived + stats.deleted + stats.referenced

        return SessionStatsResponse(
            emails_processed=stats.emails_processed,
            emails_skipped=stats.emails_skipped,
            actions_taken=actions_taken,
            tasks_created=stats.tasks_created,
            average_confidence=stats.confidence_avg,
            session_duration_minutes=stats.duration_minutes,
        )

    def _get_last_activity(self) -> datetime | None:
        """Get the most recent activity timestamp"""
        timestamps: list[datetime] = []

        # Check various last activity timestamps
        for key in [
            "last_activity",
            "email_last_poll",
            "teams_last_poll",
            "calendar_last_poll",
            "notes_last_activity",
        ]:
            ts = self._parse_datetime(self._state.get(key))
            if ts:
                timestamps.append(ts)

        if not timestamps:
            return None

        return max(timestamps)

    def _parse_datetime(self, value: object) -> datetime | None:
        """Parse datetime from various formats"""
        if value is None:
            return None
        if isinstance(value, datetime):
            # Ensure UTC timezone
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None
