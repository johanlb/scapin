"""
Calendar Event Processor

Orchestrates Calendar event processing through the cognitive pipeline.

Pipeline:
1. Fetch events from Calendar API
2. Normalize to PerceivedEvent
3. Process through CognitivePipeline (if enabled)
4. Execute actions
5. Update state
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.core.config_manager import CalendarConfig, get_config
from src.core.events import PerceivedEvent
from src.core.state_manager import get_state_manager
from src.integrations.microsoft.auth import MicrosoftAuthenticator
from src.integrations.microsoft.calendar_client import CalendarClient
from src.integrations.microsoft.calendar_models import CalendarEvent
from src.integrations.microsoft.calendar_normalizer import CalendarNormalizer
from src.integrations.microsoft.graph_client import GraphClient
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("trivelin.calendar_processor")

# Default limit for processing - prevents overwhelming the system
# Items are always processed oldest-first to handle backlog chronologically
DEFAULT_PROCESSING_LIMIT = 50


@dataclass
class CalendarProcessingResult:
    """Result of processing a single Calendar event"""

    event_id: str
    success: bool
    skipped: bool = False
    reason: Optional[str] = None
    actions_taken: list[str] = field(default_factory=list)
    confidence: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "success": self.success,
            "skipped": self.skipped,
            "reason": self.reason,
            "actions_taken": self.actions_taken,
            "confidence": self.confidence,
            "error": self.error,
        }


@dataclass
class CalendarProcessingSummary:
    """Summary of a Calendar processing batch"""

    total: int
    successful: int
    failed: int
    skipped: int
    results: list[CalendarProcessingResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=now_utc)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": [r.to_dict() for r in self.results],
        }


class CalendarProcessor:
    """
    Calendar event processor

    Orchestrates the Calendar event processing pipeline:
    1. Fetch events from CalendarClient
    2. Normalize via CalendarNormalizer
    3. Process via CognitivePipeline (if enabled)
    4. Execute actions via ActionOrchestrator

    Usage:
        processor = CalendarProcessor()
        summary = await processor.poll_and_process()

        # Or get briefing
        briefing = await processor.get_briefing(hours_ahead=24)
    """

    def __init__(
        self,
        calendar_client: Optional[CalendarClient] = None,
        normalizer: Optional[CalendarNormalizer] = None,
        config: Optional[CalendarConfig] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize Calendar processor

        Args:
            calendar_client: Optional pre-configured CalendarClient
            normalizer: Optional pre-configured normalizer
            config: Optional Calendar configuration
            data_dir: Directory for token cache and state
        """
        self.config = config or get_config().calendar
        self.data_dir = data_dir or Path("data")
        self.state_manager = get_state_manager()
        self._last_poll: Optional[datetime] = None

        # Initialize client if not provided
        if calendar_client:
            self.calendar_client = calendar_client
        else:
            self.calendar_client = self._create_calendar_client()

        # Initialize normalizer
        self.normalizer = normalizer or CalendarNormalizer()

        logger.info(
            "Calendar processor initialized",
            extra={
                "poll_interval": self.config.poll_interval_seconds,
                "days_ahead": self.config.days_ahead,
            }
        )

    def _create_calendar_client(self) -> CalendarClient:
        """Create Calendar client from configuration"""
        if not self.config.account:
            raise ValueError(
                "Microsoft account not configured. "
                "Set CALENDAR__ACCOUNT__CLIENT_ID and CALENDAR__ACCOUNT__TENANT_ID"
            )

        authenticator = MicrosoftAuthenticator(
            config=self.config.account,
            cache_dir=self.data_dir,
        )
        graph_client = GraphClient(authenticator=authenticator)
        return CalendarClient(graph=graph_client)

    async def poll_and_process(
        self,
        limit: int = DEFAULT_PROCESSING_LIMIT,
    ) -> CalendarProcessingSummary:
        """
        Poll for events and process them

        Args:
            limit: Maximum events to process (default: 20)

        Returns:
            Summary of processing results
        """
        logger.info("Polling Calendar for events")

        summary = CalendarProcessingSummary(
            total=0,
            successful=0,
            failed=0,
            skipped=0,
        )

        try:
            # Fetch events
            events = await self.calendar_client.get_events(
                days_ahead=self.config.days_ahead,
                days_behind=self.config.days_behind,
                limit=limit or 100,
                include_cancelled=False,
            )

            # Update last poll time
            self._last_poll = now_utc()

            logger.info(f"Found {len(events)} events to process")
            summary.total = len(events)

            # Process each event
            for event in events:
                result = await self._process_event(event)
                summary.results.append(result)

                if result.skipped:
                    summary.skipped += 1
                elif result.success:
                    summary.successful += 1
                else:
                    summary.failed += 1

            summary.completed_at = now_utc()

            logger.info(
                f"Processing complete: {summary.successful} successful, "
                f"{summary.failed} failed, {summary.skipped} skipped"
            )

        except Exception as e:
            logger.error(f"Error during Calendar polling: {e}")
            raise

        return summary

    async def _process_event(
        self,
        event: CalendarEvent,
    ) -> CalendarProcessingResult:
        """
        Process a single Calendar event

        Args:
            event: CalendarEvent to process

        Returns:
            CalendarProcessingResult
        """
        logger.debug(f"Processing event {event.event_id}")

        try:
            # Normalize to PerceivedEvent
            perceived_event = self.normalizer.normalize(event)

            # Check if already processed
            if self._is_processed(perceived_event.event_id):
                logger.debug(f"Event {event.event_id} already processed")
                return CalendarProcessingResult(
                    event_id=event.event_id,
                    success=True,
                    skipped=True,
                    reason="Already processed",
                )

            # Basic processing - mark as processed
            # Note: For advanced analysis, use V2EmailProcessor with Calendar normalization
            logger.info(f"Processed event {event.event_id}")
            self._mark_processed(perceived_event.event_id, {"mode": "basic"})

            return CalendarProcessingResult(
                event_id=event.event_id,
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
            return CalendarProcessingResult(
                event_id=event.event_id,
                success=False,
                error=str(e),
            )

    def _is_processed(self, event_id: str) -> bool:
        """Check if an event has already been processed"""
        try:
            state = self.state_manager.get_state()
            processed_ids = state.get("processed_calendar_events", set())
            return event_id in processed_ids
        except Exception:
            return False

    def _mark_processed(self, event_id: str, _result: dict[str, Any]) -> None:
        """Mark an event as processed"""
        try:
            state = self.state_manager.get_state()
            processed_ids = state.get("processed_calendar_events", set())
            processed_ids.add(event_id)
            self.state_manager.update_state({"processed_calendar_events": processed_ids})
        except Exception as e:
            logger.warning(f"Failed to mark event as processed: {e}")

    async def get_briefing(
        self,
        hours_ahead: Optional[int] = None,
    ) -> list[PerceivedEvent]:
        """
        Get briefing of upcoming events

        Returns normalized PerceivedEvents for display/review.

        Args:
            hours_ahead: Hours to look ahead (default: config value)

        Returns:
            List of PerceivedEvent objects for upcoming events
        """
        hours = hours_ahead or self.config.briefing_hours_ahead

        logger.info(f"Generating briefing for next {hours} hours")

        events = await self.calendar_client.get_upcoming_events(
            hours_ahead=hours,
            include_in_progress=True,
        )

        # Normalize all events
        perceived_events = [self.normalizer.normalize(e) for e in events]

        logger.info(f"Briefing contains {len(perceived_events)} events")
        return perceived_events

    async def get_event(
        self,
        event_id: str,
    ) -> PerceivedEvent:
        """
        Get a single event as PerceivedEvent

        Args:
            event_id: Calendar event ID

        Returns:
            PerceivedEvent
        """
        event = await self.calendar_client.get_event(event_id)
        return self.normalizer.normalize(event)

    async def process_single_event(
        self,
        event_id: str,
    ) -> CalendarProcessingResult:
        """
        Process a specific event by ID

        Args:
            event_id: Event identifier

        Returns:
            CalendarProcessingResult
        """
        logger.info(f"Processing single event {event_id}")

        event = await self.calendar_client.get_event(event_id)
        return await self._process_event(event)

    def reset_poll_state(self) -> None:
        """Reset poll state to process all events again"""
        self._last_poll = None
        logger.info("Poll state reset - will fetch all events on next poll")
