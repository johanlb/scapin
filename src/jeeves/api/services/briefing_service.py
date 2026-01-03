"""
Briefing Service

Async wrapper around BriefingGenerator for API use.
"""

from dataclasses import dataclass

from src.core.config_manager import PKMConfig
from src.jeeves.briefing.generator import BriefingGenerator
from src.jeeves.briefing.models import MorningBriefing, PreMeetingBriefing
from src.monitoring.logger import get_logger

logger = get_logger("jeeves.api.services.briefing")


@dataclass
class BriefingService:
    """
    Briefing service for API endpoints

    Wraps BriefingGenerator with API-specific logic.
    """

    config: PKMConfig

    async def generate_morning_briefing(
        self,
        hours_ahead: int = 24,
    ) -> MorningBriefing:
        """
        Generate morning briefing

        Args:
            hours_ahead: Hours ahead to look for calendar events

        Returns:
            MorningBriefing with all aggregated data
        """
        logger.info(f"Generating morning briefing (hours_ahead={hours_ahead})")

        # Create generator with updated config
        briefing_config = self.config.briefing.model_copy(
            update={"morning_hours_ahead": hours_ahead}
        )
        generator = BriefingGenerator(config=briefing_config)

        briefing = await generator.generate_morning_briefing()
        logger.info(
            f"Morning briefing generated: {briefing.urgent_count} urgent, "
            f"{briefing.total_items} total"
        )
        return briefing

    async def generate_pre_meeting_briefing(
        self,
        event_id: str,
    ) -> PreMeetingBriefing:
        """
        Generate pre-meeting briefing for a calendar event

        Args:
            event_id: Calendar event ID

        Returns:
            PreMeetingBriefing with attendee context
        """
        logger.info(f"Generating pre-meeting briefing for event {event_id}")

        # Get the calendar event (already normalized to PerceivedEvent)
        from src.trivelin.calendar_processor import CalendarProcessor

        processor = CalendarProcessor()
        perceived_event = await processor.get_event(event_id)

        if perceived_event is None:
            raise ValueError(f"Calendar event not found: {event_id}")

        # Generate briefing
        generator = BriefingGenerator(config=self.config.briefing)
        briefing = await generator.generate_pre_meeting_briefing(perceived_event)

        logger.info(
            f"Pre-meeting briefing generated: {len(briefing.attendees)} attendees"
        )
        return briefing
