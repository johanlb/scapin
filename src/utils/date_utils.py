"""
Date/Time Utility Functions

Helper functions for date and time operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import re


def now_utc() -> datetime:
    """
    Get current UTC datetime

    Returns:
        Current datetime in UTC with timezone info
    """
    return datetime.now(tz=timezone.utc)


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse date string to datetime

    Supports multiple formats:
    - ISO 8601: 2025-01-15T10:30:00Z
    - Date only: 2025-01-15
    - Common formats: 15 Jan 2025, Jan 15 2025

    Args:
        date_string: Date string to parse

    Returns:
        Datetime object or None if parsing fails
    """
    if not date_string:
        return None

    # Common date formats to try
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",      # ISO 8601 with timezone
        "%Y-%m-%dT%H:%M:%SZ",        # ISO 8601 UTC
        "%Y-%m-%dT%H:%M:%S",         # ISO 8601 no timezone
        "%Y-%m-%d %H:%M:%S",         # MySQL datetime
        "%Y-%m-%d",                  # Date only
        "%d %b %Y",                  # 15 Jan 2025
        "%b %d %Y",                  # Jan 15 2025
        "%d/%m/%Y",                  # 15/01/2025
        "%m/%d/%Y",                  # 01/15/2025
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_string.strip(), fmt)
            # Add UTC timezone if none present
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return None


def format_datetime(
    dt: datetime,
    format_type: str = "iso"
) -> str:
    """
    Format datetime to string

    Args:
        dt: Datetime object
        format_type: Format type (iso, friendly, date_only, time_only)

    Returns:
        Formatted datetime string
    """
    if format_type == "iso":
        return dt.isoformat()
    elif format_type == "friendly":
        return dt.strftime("%B %d, %Y at %I:%M %p")
    elif format_type == "date_only":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time_only":
        return dt.strftime("%H:%M:%S")
    else:
        return dt.isoformat()


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string

    Args:
        dt: Datetime object

    Returns:
        Human-readable time ago (e.g., "5 minutes ago", "2 hours ago")
    """
    now = now_utc()

    # Ensure datetime has timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    delta = now - dt

    if delta < timedelta(seconds=60):
        return "just now"
    elif delta < timedelta(minutes=60):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta < timedelta(hours=24):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif delta < timedelta(days=30):
        weeks = int(delta.days / 7)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif delta < timedelta(days=365):
        months = int(delta.days / 30)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(delta.days / 365)
        return f"{years} year{'s' if years != 1 else ''} ago"


def is_business_hours(
    dt: Optional[datetime] = None,
    start_hour: int = 9,
    end_hour: int = 17,
    weekdays_only: bool = True
) -> bool:
    """
    Check if datetime is within business hours

    Args:
        dt: Datetime to check (default: now)
        start_hour: Business hours start (24h format)
        end_hour: Business hours end (24h format)
        weekdays_only: Only count weekdays as business days

    Returns:
        True if within business hours
    """
    if dt is None:
        dt = now_utc()

    # Check if weekday (Monday = 0, Sunday = 6)
    if weekdays_only and dt.weekday() >= 5:
        return False

    # Check hour
    return start_hour <= dt.hour < end_hour


def next_business_day(
    dt: Optional[datetime] = None,
    skip_weekends: bool = True
) -> datetime:
    """
    Get next business day

    Args:
        dt: Starting datetime (default: now)
        skip_weekends: Skip Saturday and Sunday

    Returns:
        Next business day datetime
    """
    if dt is None:
        dt = now_utc()

    next_day = dt + timedelta(days=1)

    if skip_weekends:
        # If Saturday, skip to Monday
        if next_day.weekday() == 5:
            next_day += timedelta(days=2)
        # If Sunday, skip to Monday
        elif next_day.weekday() == 6:
            next_day += timedelta(days=1)

    return next_day


def add_business_days(
    dt: datetime,
    days: int,
    skip_weekends: bool = True
) -> datetime:
    """
    Add business days to datetime

    Args:
        dt: Starting datetime
        days: Number of business days to add
        skip_weekends: Skip Saturday and Sunday

    Returns:
        Datetime after adding business days
    """
    current = dt
    days_added = 0

    while days_added < days:
        current += timedelta(days=1)

        # Skip weekends if requested
        if skip_weekends and current.weekday() >= 5:
            continue

        days_added += 1

    return current


def get_date_range(
    start: datetime,
    end: datetime,
    step: timedelta = timedelta(days=1)
) -> list[datetime]:
    """
    Generate list of datetimes in range

    Args:
        start: Start datetime
        end: End datetime
        step: Step size (default: 1 day)

    Returns:
        List of datetimes in range
    """
    dates = []
    current = start

    while current <= end:
        dates.append(current)
        current += step

    return dates


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """
    Check if two datetimes are on the same day

    Args:
        dt1: First datetime
        dt2: Second datetime

    Returns:
        True if same day
    """
    return (
        dt1.year == dt2.year
        and dt1.month == dt2.month
        and dt1.day == dt2.day
    )


def start_of_day(dt: datetime) -> datetime:
    """
    Get start of day (midnight)

    Args:
        dt: Datetime

    Returns:
        Datetime at start of day
    """
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    """
    Get end of day (23:59:59.999999)

    Args:
        dt: Datetime

    Returns:
        Datetime at end of day
    """
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def start_of_week(dt: datetime) -> datetime:
    """
    Get start of week (Monday)

    Args:
        dt: Datetime

    Returns:
        Datetime at start of week
    """
    days_since_monday = dt.weekday()
    monday = dt - timedelta(days=days_since_monday)
    return start_of_day(monday)


def end_of_week(dt: datetime) -> datetime:
    """
    Get end of week (Sunday)

    Args:
        dt: Datetime

    Returns:
        Datetime at end of week
    """
    days_until_sunday = 6 - dt.weekday()
    sunday = dt + timedelta(days=days_until_sunday)
    return end_of_day(sunday)
