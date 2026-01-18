"""
iCloud Calendar Client

CalDAV-based client for interacting with iCloud Calendar.
Uses the standard CalDAV protocol for calendar access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

from src.integrations.apple.calendar_models import (
    ICloudAttendee,
    ICloudAttendeeStatus,
    ICloudCalendar,
    ICloudCalendarEvent,
    ICloudEventStatus,
)
from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    import caldav

logger = get_logger("integrations.apple.calendar")


@dataclass
class ICloudCalendarConfig:
    """Configuration for iCloud Calendar connection"""

    username: str  # Apple ID email
    app_specific_password: str  # App-specific password from appleid.apple.com
    server_url: str = "https://caldav.icloud.com"


class ICloudCalendarClient:
    """
    Client for interacting with iCloud Calendar via CalDAV.

    Uses the standard CalDAV protocol to access iCloud Calendar.
    Requires an app-specific password generated from appleid.apple.com.

    Example:
        config = ICloudCalendarConfig(
            username="user@icloud.com",
            app_specific_password="xxxx-xxxx-xxxx-xxxx"
        )
        client = ICloudCalendarClient(config)
        events = client.get_events(days_ahead=7)
    """

    def __init__(self, config: Optional[ICloudCalendarConfig] = None) -> None:
        """
        Initialize the iCloud Calendar client.

        Args:
            config: Configuration with credentials. If None, client
                   will be unavailable until configure() is called.
        """
        self._config = config
        self._client: Optional[caldav.DAVClient] = None
        self._principal: Optional[caldav.Principal] = None
        self._available: Optional[bool] = None

    def configure(self, config: ICloudCalendarConfig) -> None:
        """
        Configure the client with credentials.

        Args:
            config: iCloud Calendar configuration
        """
        self._config = config
        self._client = None
        self._principal = None
        self._available = None

    @property
    def is_configured(self) -> bool:
        """Check if client is configured with credentials"""
        return self._config is not None

    def is_available(self) -> bool:
        """
        Check if iCloud Calendar is available and accessible.

        Returns:
            True if connection can be established
        """
        if self._available is not None:
            return self._available

        if not self._config:
            self._available = False
            return False

        try:
            self._connect()
            self._available = True
        except Exception as e:
            logger.warning(f"iCloud Calendar not available: {e}")
            self._available = False

        return self._available

    def _connect(self) -> None:
        """Establish connection to iCloud CalDAV server"""
        if self._client is not None and self._principal is not None:
            return

        if not self._config:
            raise RuntimeError("Client not configured. Call configure() first.")

        try:
            import caldav
        except ImportError as e:
            raise RuntimeError("caldav package not installed. Run: pip install caldav") from e

        self._client = caldav.DAVClient(
            url=self._config.server_url,
            username=self._config.username,
            password=self._config.app_specific_password,
        )
        self._principal = self._client.principal()
        logger.info("Connected to iCloud Calendar")

    def _ensure_connected(self) -> None:
        """Ensure client is connected, raise if not possible"""
        if not self.is_configured:
            raise RuntimeError("Client not configured")
        self._connect()

    def get_calendars(self) -> list[ICloudCalendar]:
        """
        Get all calendars from iCloud.

        Returns:
            List of ICloudCalendar objects
        """
        self._ensure_connected()

        calendars = []
        try:
            for cal in self._principal.calendars():
                calendars.append(
                    ICloudCalendar(
                        name=cal.name or "Unnamed",
                        uid=str(cal.url) if cal.url else "",
                        is_writable=True,  # CalDAV doesn't expose this easily
                    )
                )
        except Exception as e:
            logger.error(f"Failed to get calendars: {e}")

        return calendars

    def get_events(
        self,
        days_ahead: int = 30,
        days_behind: int = 7,
        calendar_names: list[str] | None = None,
    ) -> list[ICloudCalendarEvent]:
        """
        Get events from iCloud Calendar within a date range.

        Args:
            days_ahead: Number of days to look ahead from today
            days_behind: Number of days to look behind from today
            calendar_names: Optional list of calendar names to search
                           (None = all calendars)

        Returns:
            List of ICloudCalendarEvent objects sorted by start date
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days_behind)
        end_date = now + timedelta(days=days_ahead)

        return self.get_events_in_range(start_date, end_date, calendar_names)

    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_names: list[str] | None = None,
    ) -> list[ICloudCalendarEvent]:
        """
        Get events within a specific date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range
            calendar_names: Optional list of calendar names to filter

        Returns:
            List of ICloudCalendarEvent objects sorted by start date
        """
        self._ensure_connected()

        events = []
        calendar_names_lower = {n.lower() for n in calendar_names} if calendar_names else None

        try:
            for cal in self._principal.calendars():
                cal_name = cal.name or "Unnamed"

                # Filter by calendar name if specified
                if calendar_names_lower and cal_name.lower() not in calendar_names_lower:
                    continue

                try:
                    cal_events = cal.search(
                        start=start_date,
                        end=end_date,
                        event=True,
                        expand=True,
                    )

                    for event in cal_events:
                        parsed = self._parse_caldav_event(event, cal_name)
                        if parsed:
                            events.append(parsed)
                except Exception as e:
                    logger.warning(f"Failed to get events from calendar {cal_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to get events: {e}")

        # Sort by start date
        events.sort(key=lambda e: e.start_date)
        return events

    def get_event_by_uid(self, uid: str) -> Optional[ICloudCalendarEvent]:
        """
        Get a specific event by its UID.

        Args:
            uid: The unique identifier of the event

        Returns:
            ICloudCalendarEvent or None if not found
        """
        self._ensure_connected()

        try:
            for cal in self._principal.calendars():
                try:
                    event = cal.event_by_uid(uid)
                    if event:
                        return self._parse_caldav_event(event, cal.name or "Unnamed")
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Failed to get event {uid}: {e}")

        return None

    def search_events(
        self,
        query: str,
        days_ahead: int = 30,
        days_behind: int = 30,
        calendar_names: list[str] | None = None,
        max_results: int = 50,
    ) -> list[ICloudCalendarEvent]:
        """
        Search events by query string.

        Searches in summary (title), description, and location.

        Args:
            query: Search query string
            days_ahead: Number of days to look ahead
            days_behind: Number of days to look behind
            calendar_names: Optional calendar filter
            max_results: Maximum number of results

        Returns:
            List of matching events
        """
        # Get all events in range
        events = self.get_events(days_ahead, days_behind, calendar_names)

        # Filter by query
        query_lower = query.lower()
        matching = []

        for event in events:
            searchable = f"{event.summary} {event.description} {event.location}".lower()
            if query_lower in searchable:
                matching.append(event)
                if len(matching) >= max_results:
                    break

        return matching

    def get_today_events(self) -> list[ICloudCalendarEvent]:
        """
        Get all events for today.

        Returns:
            List of today's events sorted by start time
        """
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return self.get_events_in_range(today, tomorrow)

    def get_upcoming_events(self, hours: int = 24) -> list[ICloudCalendarEvent]:
        """
        Get events in the next N hours.

        Args:
            hours: Number of hours to look ahead

        Returns:
            List of upcoming events
        """
        now = datetime.now(timezone.utc)
        end = now + timedelta(hours=hours)
        events = self.get_events_in_range(now, end)
        return [e for e in events if not e.is_past]

    def _parse_caldav_event(
        self,
        event: Any,
        calendar_name: str,
    ) -> ICloudCalendarEvent | None:
        """
        Parse a CalDAV event into ICloudCalendarEvent.

        Args:
            event: caldav.Event object
            calendar_name: Name of the calendar containing this event

        Returns:
            ICloudCalendarEvent or None if parsing fails
        """
        try:
            # Get the iCalendar component
            ical = event.icalendar_component

            uid = str(ical.get("uid", ""))
            summary = str(ical.get("summary", ""))

            # Parse dates
            dtstart = ical.get("dtstart")
            dtend = ical.get("dtend")

            if not dtstart:
                logger.warning(f"Event missing start date: {summary}")
                return None

            start_date = self._parse_ical_datetime(dtstart.dt)
            end_date = self._parse_ical_datetime(dtend.dt) if dtend else start_date

            # Check if all-day event (date vs datetime)
            is_all_day = not hasattr(dtstart.dt, "hour")

            # Parse other fields
            description = str(ical.get("description", "") or "")
            location = str(ical.get("location", "") or "")
            url = str(ical.get("url", "") or "")

            # Parse status
            status_str = str(ical.get("status", "CONFIRMED"))
            status = self._parse_status(status_str)

            # Parse recurrence
            rrule = ical.get("rrule")
            recurrence_rule = str(rrule.to_ical().decode()) if rrule else ""

            # Parse attendees
            attendees = []
            organizer = None

            for attendee in ical.get("attendee", []):
                parsed_attendee = self._parse_attendee(attendee)
                if parsed_attendee:
                    attendees.append(parsed_attendee)

            org = ical.get("organizer")
            if org:
                organizer = self._parse_attendee(org, is_organizer=True)

            # Parse timestamps
            created = ical.get("created")
            modified = ical.get("last-modified")

            created_at = self._parse_ical_datetime(created.dt) if created else None
            modified_at = self._parse_ical_datetime(modified.dt) if modified else None

            return ICloudCalendarEvent(
                uid=uid,
                summary=summary,
                start_date=start_date,
                end_date=end_date,
                is_all_day=is_all_day,
                calendar_name=calendar_name,
                description=description,
                location=location,
                url=url,
                status=status,
                attendees=attendees,
                organizer=organizer,
                recurrence_rule=recurrence_rule,
                created_at=created_at,
                modified_at=modified_at,
            )

        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            return None

    def _parse_ical_datetime(self, dt: Any) -> datetime:
        """
        Parse an iCalendar datetime to Python datetime.

        Args:
            dt: Date or datetime from iCalendar

        Returns:
            datetime object (with UTC timezone if applicable)
        """
        from datetime import date

        if isinstance(dt, datetime):
            # Ensure timezone awareness
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        elif isinstance(dt, date):
            # All-day event - convert date to datetime at midnight
            return datetime.combine(dt, datetime.min.time(), tzinfo=timezone.utc)
        else:
            raise ValueError(f"Unexpected date type: {type(dt)}")

    def _parse_status(self, status_str: str) -> ICloudEventStatus:
        """Parse event status string"""
        status_str = status_str.upper().strip()

        status_map = {
            "CONFIRMED": ICloudEventStatus.CONFIRMED,
            "TENTATIVE": ICloudEventStatus.TENTATIVE,
            "CANCELLED": ICloudEventStatus.CANCELLED,
            "CANCELED": ICloudEventStatus.CANCELLED,
        }

        return status_map.get(status_str, ICloudEventStatus.CONFIRMED)

    def _parse_attendee(
        self,
        attendee: Any,
        is_organizer: bool = False,
    ) -> ICloudAttendee | None:
        """
        Parse an iCalendar attendee.

        Args:
            attendee: vCalAddress object
            is_organizer: Whether this is the organizer

        Returns:
            ICloudAttendee or None
        """
        try:
            # Get email from mailto: URI
            email = str(attendee).replace("mailto:", "").lower()

            # Get common name (display name)
            name = attendee.params.get("CN", email)

            # Get participation status
            partstat = attendee.params.get("PARTSTAT", "NEEDS-ACTION")
            status = self._parse_partstat(partstat)

            return ICloudAttendee(
                name=str(name),
                email=email,
                status=status,
                is_organizer=is_organizer,
            )
        except Exception as e:
            logger.debug(f"Failed to parse attendee: {e}")
            return None

    def _parse_partstat(self, partstat: str) -> ICloudAttendeeStatus:
        """Parse participation status"""
        partstat = partstat.upper()

        status_map = {
            "ACCEPTED": ICloudAttendeeStatus.ACCEPTED,
            "DECLINED": ICloudAttendeeStatus.DECLINED,
            "TENTATIVE": ICloudAttendeeStatus.TENTATIVE,
            "NEEDS-ACTION": ICloudAttendeeStatus.PENDING,
            "DELEGATED": ICloudAttendeeStatus.PENDING,
        }

        return status_map.get(partstat, ICloudAttendeeStatus.UNKNOWN)

    def close(self) -> None:
        """Close the CalDAV connection"""
        self._client = None
        self._principal = None
        logger.debug("Closed iCloud Calendar connection")
