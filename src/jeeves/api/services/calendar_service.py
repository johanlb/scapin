"""
Calendar Service

Async service wrapper for calendar operations.
"""

from datetime import datetime, timedelta
from typing import Any

from src.core.config_manager import get_config
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("api.calendar_service")


class CalendarService:
    """Async service for calendar operations"""

    def __init__(self) -> None:
        """Initialize calendar service"""
        self._config = get_config()
        self._processor = None

    def _get_processor(self) -> Any:
        """Lazy load calendar processor"""
        if self._processor is None:
            from src.trivelin.calendar_processor import CalendarProcessor

            self._processor = CalendarProcessor()
        return self._processor

    async def get_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get calendar events

        Args:
            start_date: Start of date range (default: now)
            end_date: End of date range (default: 7 days from now)
            limit: Maximum events to return

        Returns:
            List of calendar events
        """
        if not self._config.calendar.enabled:
            return []

        processor = self._get_processor()

        start = start_date or now_utc()
        end = end_date or (start + timedelta(days=self._config.calendar.days_ahead))

        try:
            # Use calendar_view for proper date range support
            events = await processor.calendar_client.get_calendar_view(
                start=start,
                end=end,
                limit=limit,
            )

            return [self._event_to_dict(e) for e in events]
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        """
        Get single calendar event

        Args:
            event_id: Event ID

        Returns:
            Event dict or None if not found
        """
        if not self._config.calendar.enabled:
            return None

        processor = self._get_processor()

        try:
            event = await processor.calendar_client.get_event(event_id)
            return self._event_to_dict(event) if event else None
        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            return None

    async def get_today_events(self) -> dict[str, Any]:
        """
        Get today's calendar events

        Returns:
            Dictionary with today's events summary
        """
        now = now_utc()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        events = await self.get_events(
            start_date=start_of_day,
            end_date=end_of_day,
            limit=50,
        )

        meetings = [e for e in events if not e.get("is_all_day", False)]
        all_day = [e for e in events if e.get("is_all_day", False)]

        return {
            "date": now.date().isoformat(),
            "total_events": len(events),
            "meetings": len(meetings),
            "all_day_events": len(all_day),
            "events": events,
        }

    async def respond_to_event(
        self,
        event_id: str,
        response: str,
        message: str | None = None,
    ) -> bool:
        """
        Respond to a calendar event invitation

        Args:
            event_id: Event ID
            response: Response type (accept, decline, tentative)
            message: Optional message to organizer

        Returns:
            True if response was sent successfully
        """
        if not self._config.calendar.enabled:
            return False

        processor = self._get_processor()

        try:
            success = await processor.calendar_client.respond_to_event(
                event_id=event_id,
                response=response,
                message=message,
            )
            return success
        except Exception as e:
            logger.error(f"Failed to respond to event {event_id}: {e}")
            return False

    async def poll(self) -> dict[str, Any]:
        """
        Poll calendar for updates

        Returns:
            Poll result summary
        """
        if not self._config.calendar.enabled:
            return {
                "events_fetched": 0,
                "events_new": 0,
                "events_updated": 0,
                "polled_at": now_utc().isoformat(),
            }

        processor = self._get_processor()

        try:
            summary = await processor.poll_and_process()
            return {
                "events_fetched": summary.total,
                "events_new": summary.successful,
                "events_updated": 0,  # Would need state tracking to know updates
                "polled_at": now_utc().isoformat(),
            }
        except Exception as e:
            logger.error(f"Calendar poll failed: {e}")
            return {
                "events_fetched": 0,
                "events_new": 0,
                "events_updated": 0,
                "polled_at": now_utc().isoformat(),
                "error": str(e),
            }

    async def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        location: str | None = None,
        description: str | None = None,
        attendees: list[str] | None = None,
        is_online: bool = False,
        reminder_minutes: int = 15,
    ) -> dict[str, Any] | None:
        """
        Create a new calendar event

        Args:
            title: Event title
            start: Start datetime
            end: End datetime
            location: Event location
            description: Event description/body
            attendees: List of attendee email addresses
            is_online: Create as Teams meeting
            reminder_minutes: Reminder before event

        Returns:
            Created event dict or None if failed
        """
        if not self._config.calendar.enabled:
            return None

        processor = self._get_processor()

        try:
            event = await processor.calendar_client.create_event(
                subject=title,
                start=start,
                end=end,
                body=description,
                location=location,
                attendees=attendees,
                is_online=is_online,
                reminder_minutes=reminder_minutes,
            )

            return {
                "id": event.event_id,
                "title": event.subject,
                "start": event.start.isoformat() if event.start else None,
                "end": event.end.isoformat() if event.end else None,
                "web_link": event.web_link,
                "meeting_url": event.online_meeting_url,
            }
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    async def update_event(
        self,
        event_id: str,
        title: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        location: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Update an existing calendar event

        Args:
            event_id: Event ID to update
            title: New title (optional)
            start: New start time (optional)
            end: New end time (optional)
            location: New location (optional)
            description: New description (optional)

        Returns:
            Updated event dict or None if failed
        """
        if not self._config.calendar.enabled:
            return None

        processor = self._get_processor()

        try:
            event = await processor.calendar_client.update_event(
                event_id=event_id,
                subject=title,
                start=start,
                end=end,
                body=description,
                location=location,
            )

            return self._event_to_dict(event)
        except Exception as e:
            logger.error(f"Failed to update event {event_id}: {e}")
            return None

    async def delete_event(self, event_id: str) -> bool:
        """
        Delete a calendar event

        Args:
            event_id: Event ID to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._config.calendar.enabled:
            return False

        processor = self._get_processor()

        try:
            return await processor.calendar_client.delete_event(event_id)
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            return False

    def _event_to_dict(self, event: Any) -> dict[str, Any]:
        """Convert CalendarEvent to dictionary"""
        return {
            "id": event.event_id if hasattr(event, "event_id") else event.id,
            "title": event.subject,
            "start": event.start.isoformat() if event.start else None,
            "end": event.end.isoformat() if event.end else None,
            "location": event.location,
            "is_online": event.is_online,
            "meeting_url": event.online_meeting_url,
            "organizer": event.organizer.email if event.organizer else None,
            "attendees": [
                {
                    "email": a.email,
                    "name": a.name,
                    "response_status": a.response_status.value if hasattr(a.response_status, "value") else str(a.response_status),
                    "is_organizer": a.is_organizer,
                }
                for a in (event.attendees or [])
            ],
            "is_all_day": event.is_all_day,
            "is_recurring": event.is_recurring,
            "description": event.body_preview,
            "status": "confirmed",
        }
