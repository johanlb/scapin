"""
Stats Service

Aggregates statistics from all sources (email, teams, calendar, queue, notes).
"""

import time
from datetime import datetime
from typing import Any

from src.core.config_manager import get_config
from src.core.state_manager import get_state_manager
from src.jeeves.api.models.calendar import CalendarStatsResponse
from src.jeeves.api.models.email import EmailStatsResponse
from src.jeeves.api.models.notes import ReviewStatsResponse
from src.jeeves.api.models.queue import QueueStatsResponse
from src.jeeves.api.models.stats import StatsBySourceResponse, StatsOverviewResponse
from src.jeeves.api.models.teams import TeamsStatsResponse
from src.jeeves.api.services.email_service import EmailService
from src.jeeves.api.services.notes_review_service import NotesReviewService
from src.jeeves.api.services.queue_service import QueueService
from src.jeeves.api.services.teams_service import TeamsService
from src.monitoring.logger import get_logger

logger = get_logger("api.stats_service")

# Track server start time (shared with system router)
_start_time = time.time()


class StatsService:
    """Service for aggregating statistics from all sources"""

    def __init__(self) -> None:
        """Initialize stats service"""
        self._config = get_config()
        self._state = get_state_manager()

    async def get_overview(self) -> StatsOverviewResponse:
        """
        Get aggregated overview statistics

        Returns:
            StatsOverviewResponse with totals from all sources
        """
        logger.info("Getting stats overview")

        # Fetch stats from each service
        email_stats = await self._get_email_stats()
        teams_stats = await self._get_teams_stats()
        calendar_stats = await self._get_calendar_stats()
        queue_stats = await self._get_queue_stats()
        notes_stats = await self._get_notes_stats()

        # Calculate totals
        total_processed = (
            email_stats.get("emails_processed", 0)
            + teams_stats.get("messages_processed", 0)
        )
        total_pending = (
            queue_stats.get("total", 0)
            + teams_stats.get("unread_chats", 0)
            + notes_stats.get("total_due", 0)
        )

        # Count active sources
        sources_active = sum([
            bool(self._config.email.get_enabled_accounts()),
            self._config.teams.enabled,
            self._config.calendar.enabled,
            True,  # Notes are always available
        ])

        # Find most recent activity
        last_activity = self._get_most_recent_activity(
            email_stats, teams_stats, calendar_stats
        )

        uptime = time.time() - _start_time

        return StatsOverviewResponse(
            total_processed=total_processed,
            total_pending=total_pending,
            sources_active=sources_active,
            uptime_seconds=uptime,
            last_activity=last_activity,
            email_processed=email_stats.get("emails_processed", 0),
            email_queued=queue_stats.get("total", 0),
            teams_messages=teams_stats.get("messages_processed", 0),
            teams_unread=teams_stats.get("unread_chats", 0),
            calendar_events_today=calendar_stats.get("events_today", 0),
            calendar_events_week=calendar_stats.get("events_week", 0),
            notes_due=notes_stats.get("total_due", 0),
            notes_reviewed_today=notes_stats.get("reviewed_today", 0),
        )

    async def get_by_source(self) -> StatsBySourceResponse:
        """
        Get detailed statistics per source

        Returns:
            StatsBySourceResponse with stats from each source
        """
        logger.info("Getting stats by source")

        # Build response models for each source
        email_response = await self._build_email_stats()
        teams_response = await self._build_teams_stats()
        calendar_response = await self._build_calendar_stats()
        queue_response = await self._build_queue_stats()
        notes_response = await self._build_notes_stats()

        return StatsBySourceResponse(
            email=email_response,
            teams=teams_response,
            calendar=calendar_response,
            queue=queue_response,
            notes=notes_response,
        )

    # --- Private helpers to fetch raw stats ---

    async def _get_email_stats(self) -> dict[str, Any]:
        """Get email stats as dict"""
        try:
            service = EmailService()
            return await service.get_stats()
        except Exception as e:
            logger.warning(f"Failed to get email stats: {e}")
            return {}

    async def _get_teams_stats(self) -> dict[str, Any]:
        """Get teams stats as dict"""
        try:
            if not self._config.teams.enabled:
                return {}
            service = TeamsService()
            return await service.get_stats()
        except Exception as e:
            logger.warning(f"Failed to get teams stats: {e}")
            return {}

    async def _get_calendar_stats(self) -> dict[str, Any]:
        """Get calendar stats from state"""
        try:
            if not self._config.calendar.enabled:
                return {}
            # Calendar stats are stored in state manager
            return {
                "events_today": self._state.get("calendar_events_today", 0),
                "events_week": self._state.get("calendar_events_week", 0),
                "meetings_online": self._state.get("calendar_meetings_online", 0),
                "meetings_in_person": self._state.get("calendar_meetings_in_person", 0),
                "last_poll": self._state.get("calendar_last_poll"),
            }
        except Exception as e:
            logger.warning(f"Failed to get calendar stats: {e}")
            return {}

    async def _get_queue_stats(self) -> dict[str, Any]:
        """Get queue stats as dict"""
        try:
            service = QueueService()
            return await service.get_stats()
        except Exception as e:
            logger.warning(f"Failed to get queue stats: {e}")
            return {}

    async def _get_notes_stats(self) -> dict[str, Any]:
        """Get notes review stats as dict"""
        try:
            service = NotesReviewService()
            stats = await service.get_review_stats()
            return {
                "total_notes": stats.total_notes,
                "by_type": stats.by_type,
                "by_importance": stats.by_importance,
                "total_due": stats.total_due,
                "reviewed_today": stats.reviewed_today,
                "avg_easiness_factor": stats.avg_easiness_factor,
            }
        except Exception as e:
            logger.warning(f"Failed to get notes stats: {e}")
            return {}

    # --- Private helpers to build response models ---

    async def _build_email_stats(self) -> EmailStatsResponse | None:
        """Build EmailStatsResponse"""
        stats = await self._get_email_stats()
        if not stats:
            return None
        return EmailStatsResponse(
            emails_processed=stats.get("emails_processed", 0),
            emails_auto_executed=stats.get("emails_auto_executed", 0),
            emails_archived=stats.get("emails_archived", 0),
            emails_deleted=stats.get("emails_deleted", 0),
            emails_queued=stats.get("emails_queued", 0),
            emails_skipped=stats.get("emails_skipped", 0),
            tasks_created=stats.get("tasks_created", 0),
            average_confidence=stats.get("average_confidence", 0.0),
            processing_mode=stats.get("processing_mode", "unknown"),
        )

    async def _build_teams_stats(self) -> TeamsStatsResponse | None:
        """Build TeamsStatsResponse"""
        if not self._config.teams.enabled:
            return None
        stats = await self._get_teams_stats()
        if not stats:
            return None
        return TeamsStatsResponse(
            total_chats=stats.get("total_chats", 0),
            unread_chats=stats.get("unread_chats", 0),
            messages_processed=stats.get("messages_processed", 0),
            messages_flagged=stats.get("messages_flagged", 0),
            last_poll=self._parse_datetime(stats.get("last_poll")),
        )

    async def _build_calendar_stats(self) -> CalendarStatsResponse | None:
        """Build CalendarStatsResponse"""
        if not self._config.calendar.enabled:
            return None
        stats = await self._get_calendar_stats()
        if not stats:
            return None
        return CalendarStatsResponse(
            events_today=stats.get("events_today", 0),
            events_week=stats.get("events_week", 0),
            meetings_online=stats.get("meetings_online", 0),
            meetings_in_person=stats.get("meetings_in_person", 0),
            last_poll=self._parse_datetime(stats.get("last_poll")),
        )

    async def _build_queue_stats(self) -> QueueStatsResponse | None:
        """Build QueueStatsResponse"""
        stats = await self._get_queue_stats()
        if not stats:
            return None
        return QueueStatsResponse(
            total=stats.get("total", 0),
            by_status=stats.get("by_status", {}),
            by_account=stats.get("by_account", {}),
            oldest_item=self._parse_datetime(stats.get("oldest_item")),
            newest_item=self._parse_datetime(stats.get("newest_item")),
        )

    async def _build_notes_stats(self) -> ReviewStatsResponse | None:
        """Build ReviewStatsResponse"""
        stats = await self._get_notes_stats()
        if not stats:
            return None
        return ReviewStatsResponse(
            total_notes=stats.get("total_notes", 0),
            by_type=stats.get("by_type", {}),
            by_importance=stats.get("by_importance", {}),
            total_due=stats.get("total_due", 0),
            reviewed_today=stats.get("reviewed_today", 0),
            avg_easiness_factor=stats.get("avg_easiness_factor", 2.5),
        )

    # --- Utility methods ---

    def _parse_datetime(self, value: Any) -> datetime | None:
        """Parse datetime from various formats"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None

    def _get_most_recent_activity(
        self,
        email_stats: dict[str, Any],
        teams_stats: dict[str, Any],
        calendar_stats: dict[str, Any],
    ) -> datetime | None:
        """Find the most recent activity timestamp"""
        timestamps: list[datetime] = []

        # Check various timestamps
        for stats in [email_stats, teams_stats, calendar_stats]:
            for key in ["last_poll", "last_activity", "last_processed"]:
                ts = self._parse_datetime(stats.get(key))
                if ts:
                    timestamps.append(ts)

        # Also check state manager
        state_ts = self._parse_datetime(self._state.get("last_activity"))
        if state_ts:
            timestamps.append(state_ts)

        if not timestamps:
            return None

        return max(timestamps)
