"""
Microsoft Calendar Client

High-level client for Calendar operations using Microsoft Graph API.
Provides methods for fetching, creating, and managing calendar events.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.integrations.microsoft.calendar_models import CalendarEvent
from src.integrations.microsoft.graph_client import GraphClient
from src.monitoring.logger import get_logger

logger = get_logger("integrations.microsoft.calendar_client")


@dataclass
class CalendarClient:
    """
    Microsoft Calendar Client

    High-level client for calendar operations using GraphClient.
    Reuses the GraphClient infrastructure for API calls.

    Usage:
        auth = MicrosoftAuthenticator(config, cache_dir)
        graph = GraphClient(auth)
        calendar = CalendarClient(graph)

        # Get upcoming events
        events = await calendar.get_events(days_ahead=7)

        # Get briefing for today
        briefing = await calendar.get_upcoming_events(hours_ahead=24)

        # Create event (use timezone-aware datetime)
        now = datetime.now(timezone.utc)
        event = await calendar.create_event(
            subject="Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
    """

    graph: GraphClient

    async def get_calendars(self) -> list[dict[str, Any]]:
        """
        List all calendars for the user

        Returns:
            List of calendar objects from Graph API
        """
        logger.debug("Fetching user calendars")
        calendars = await self.graph.get_all_pages("/me/calendars")
        logger.info(f"Found {len(calendars)} calendars")
        return calendars

    async def get_default_calendar(self) -> dict[str, Any]:
        """
        Get the user's default calendar

        Returns:
            Default calendar object from Graph API
        """
        logger.debug("Fetching default calendar")
        return await self.graph.get("/me/calendar")

    async def get_events(
        self,
        days_ahead: int = 7,
        days_behind: int = 0,
        calendar_id: Optional[str] = None,
        limit: int = 100,
        include_cancelled: bool = False,
    ) -> list[CalendarEvent]:
        """
        Fetch calendar events in a date range

        Args:
            days_ahead: Number of days in the future to fetch
            days_behind: Number of days in the past to fetch
            calendar_id: Specific calendar ID (default: primary calendar)
            limit: Maximum number of events to fetch
            include_cancelled: Whether to include cancelled events

        Returns:
            List of CalendarEvent objects
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days_behind)
        end_date = now + timedelta(days=days_ahead)

        logger.debug(
            f"Fetching events from {start_date.isoformat()} to {end_date.isoformat()}"
        )

        # Build endpoint
        endpoint = f"/me/calendars/{calendar_id}/events" if calendar_id else "/me/calendar/events"

        # Build filter query
        # Use calendarView for better date range handling
        # But events endpoint with filter works for simple cases
        params = {
            "$filter": (
                f"start/dateTime ge '{start_date.strftime('%Y-%m-%dT%H:%M:%S')}' "
                f"and end/dateTime le '{end_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
            ),
            "$orderby": "start/dateTime",
            "$top": str(min(limit, 100)),  # Graph API max is 100 per page
            "$select": ",".join([
                "id", "subject", "bodyPreview", "body",
                "start", "end", "location", "organizer", "attendees",
                "categories", "importance", "sensitivity", "showAs",
                "isOnlineMeeting", "onlineMeeting", "onlineMeetingProvider",
                "isReminderOn", "reminderMinutesBeforeStart",
                "responseStatus", "isCancelled", "isAllDay",
                "recurrence", "seriesMasterId", "webLink",
            ]),
        }

        # Fetch events
        data = await self.graph.get(endpoint, params=params)
        events_data = data.get("value", [])

        # Parse events
        cal_id = calendar_id or "primary"
        events = [CalendarEvent.from_api(e, cal_id) for e in events_data]

        # Filter cancelled if needed
        if not include_cancelled:
            events = [e for e in events if not e.is_cancelled]

        logger.info(f"Fetched {len(events)} events")
        return events

    async def get_calendar_view(
        self,
        start: datetime,
        end: datetime,
        calendar_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[CalendarEvent]:
        """
        Get calendar view (expands recurring events)

        Uses the calendarView endpoint which automatically expands
        recurring events into individual instances.

        Args:
            start: Start of the time range
            end: End of the time range
            calendar_id: Specific calendar ID (default: primary)
            limit: Maximum events to fetch

        Returns:
            List of CalendarEvent objects
        """
        logger.debug(
            f"Fetching calendar view from {start.isoformat()} to {end.isoformat()}"
        )

        # Build endpoint
        if calendar_id:
            endpoint = f"/me/calendars/{calendar_id}/calendarView"
        else:
            endpoint = "/me/calendarView"

        params = {
            "startDateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "$orderby": "start/dateTime",
            "$top": str(min(limit, 100)),
            "$select": ",".join([
                "id", "subject", "bodyPreview", "body",
                "start", "end", "location", "organizer", "attendees",
                "categories", "importance", "sensitivity", "showAs",
                "isOnlineMeeting", "onlineMeeting", "onlineMeetingProvider",
                "isReminderOn", "reminderMinutesBeforeStart",
                "responseStatus", "isCancelled", "isAllDay",
                "recurrence", "seriesMasterId", "webLink",
            ]),
        }

        # Fetch all pages
        events_data = await self.graph.get_all_pages(endpoint, params=params)

        # Parse events
        cal_id = calendar_id or "primary"
        events = [CalendarEvent.from_api(e, cal_id) for e in events_data]

        logger.info(f"Fetched {len(events)} events from calendar view")
        return events

    async def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        include_in_progress: bool = True,
    ) -> list[CalendarEvent]:
        """
        Get upcoming events for briefing

        Fetches events starting within the specified hours.
        Useful for daily briefings or pre-meeting preparation.

        Args:
            hours_ahead: Number of hours to look ahead
            include_in_progress: Include events currently in progress

        Returns:
            List of CalendarEvent objects sorted by start time
        """
        now = datetime.now(timezone.utc)

        # Include events that started up to 2 hours ago if include_in_progress
        start = now - timedelta(hours=2) if include_in_progress else now
        end = now + timedelta(hours=hours_ahead)

        logger.debug(f"Fetching upcoming events for next {hours_ahead} hours")

        events = await self.get_calendar_view(start=start, end=end, limit=50)

        # Filter to only upcoming or in-progress
        if include_in_progress:
            # Include if not ended yet
            events = [e for e in events if e.end > now]
        else:
            # Only include if not started yet
            events = [e for e in events if e.start > now]

        logger.info(f"Found {len(events)} upcoming events")
        return events

    async def get_event(self, event_id: str) -> CalendarEvent:
        """
        Get a single event by ID

        Args:
            event_id: The event ID

        Returns:
            CalendarEvent object
        """
        logger.debug(f"Fetching event {event_id}")

        data = await self.graph.get(f"/me/events/{event_id}")
        return CalendarEvent.from_api(data, "primary")

    async def create_event(
        self,
        subject: str,
        start: datetime,
        end: datetime,
        body: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list[str]] = None,
        is_online: bool = False,
        importance: str = "normal",
        reminder_minutes: int = 15,
        calendar_id: Optional[str] = None,
    ) -> CalendarEvent:
        """
        Create a new calendar event

        Args:
            subject: Event subject/title
            start: Start datetime (must be timezone-aware)
            end: End datetime (must be timezone-aware)
            body: Event body/description (HTML supported)
            location: Location display name
            attendees: List of attendee email addresses
            is_online: Create as Teams meeting
            importance: Importance level (low, normal, high)
            reminder_minutes: Minutes before event for reminder
            calendar_id: Calendar to create event in (default: primary)

        Returns:
            Created CalendarEvent object
        """
        logger.info(f"Creating event: {subject}")

        # Build event data
        event_data: dict[str, Any] = {
            "subject": subject,
            "start": {
                "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            },
            "importance": importance,
            "isReminderOn": True,
            "reminderMinutesBeforeStart": reminder_minutes,
        }

        if body:
            event_data["body"] = {
                "contentType": "HTML",
                "content": body,
            }

        if location:
            event_data["location"] = {
                "displayName": location,
            }

        if attendees:
            event_data["attendees"] = [
                {
                    "emailAddress": {"address": email},
                    "type": "required",
                }
                for email in attendees
            ]

        if is_online:
            event_data["isOnlineMeeting"] = True
            event_data["onlineMeetingProvider"] = "teamsForBusiness"

        # Build endpoint
        endpoint = f"/me/calendars/{calendar_id}/events" if calendar_id else "/me/events"

        # Create event
        data = await self.graph.post(endpoint, json_data=event_data)

        cal_id = calendar_id or "primary"
        event = CalendarEvent.from_api(data, cal_id)

        logger.info(f"Created event {event.event_id}: {subject}")
        return event

    async def update_event(
        self,
        event_id: str,
        subject: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        body: Optional[str] = None,
        location: Optional[str] = None,
    ) -> CalendarEvent:
        """
        Update an existing event

        Args:
            event_id: Event ID to update
            subject: New subject (optional)
            start: New start time (optional)
            end: New end time (optional)
            body: New body content (optional)
            location: New location (optional)

        Returns:
            Updated CalendarEvent object
        """
        logger.info(f"Updating event {event_id}")

        # Build update data (only include fields being updated)
        update_data: dict[str, Any] = {}

        if subject is not None:
            update_data["subject"] = subject

        if start is not None:
            update_data["start"] = {
                "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            }

        if end is not None:
            update_data["end"] = {
                "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            }

        if body is not None:
            update_data["body"] = {
                "contentType": "HTML",
                "content": body,
            }

        if location is not None:
            update_data["location"] = {
                "displayName": location,
            }

        if not update_data:
            # Nothing to update, just return current event
            return await self.get_event(event_id)

        # PATCH the event
        data = await self.graph.patch(f"/me/events/{event_id}", json_data=update_data)
        event = CalendarEvent.from_api(data, "primary")

        logger.info(f"Updated event {event_id}")
        return event

    async def respond_to_event(
        self,
        event_id: str,
        response: str,
        comment: Optional[str] = None,
        send_response: bool = True,
    ) -> bool:
        """
        Respond to a meeting invitation

        Args:
            event_id: Event ID to respond to
            response: Response type - "accept", "tentativelyAccept", "decline"
            comment: Optional comment to include
            send_response: Whether to send response to organizer

        Returns:
            True if successful
        """
        valid_responses = {"accept", "tentativelyAccept", "decline"}
        if response not in valid_responses:
            raise ValueError(f"Response must be one of: {valid_responses}")

        logger.info(f"Responding to event {event_id}: {response}")

        endpoint = f"/me/events/{event_id}/{response}"

        body: dict[str, Any] = {
            "sendResponse": send_response,
        }
        if comment:
            body["comment"] = comment

        await self.graph.post(endpoint, json_data=body)

        logger.info(f"Successfully responded {response} to event {event_id}")
        return True

    async def delete_event(self, event_id: str) -> bool:
        """
        Delete a calendar event

        Args:
            event_id: Event ID to delete

        Returns:
            True if successful
        """
        logger.info(f"Deleting event {event_id}")

        await self.graph.delete(f"/me/events/{event_id}")

        logger.info(f"Deleted event {event_id}")
        return True

    async def get_free_busy(
        self,
        emails: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get free/busy information for users

        Args:
            emails: List of email addresses to check
            start: Start of time range
            end: End of time range

        Returns:
            Dict mapping email to list of busy time slots
        """
        logger.debug(f"Getting free/busy for {len(emails)} users")

        endpoint = "/me/calendar/getSchedule"

        body = {
            "schedules": emails,
            "startTime": {
                "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            },
            "endTime": {
                "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            },
            "availabilityViewInterval": 30,  # 30 minute intervals
        }

        data = await self.graph.post(endpoint, json_data=body)
        schedules = data.get("value", [])

        # Parse into dict
        result: dict[str, list[dict[str, Any]]] = {}
        for schedule in schedules:
            email = schedule.get("scheduleId", "")
            items = schedule.get("scheduleItems", [])
            result[email] = items

        logger.info(f"Retrieved free/busy for {len(result)} users")
        return result
