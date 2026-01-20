"""
API Utilities

Shared utility functions for API routers.
"""

from datetime import datetime


def parse_datetime(value: str | None) -> datetime | None:
    """
    Parse ISO datetime string to datetime object.

    Handles both standard ISO format and JavaScript's 'Z' suffix.

    Args:
        value: ISO datetime string (e.g., "2024-01-15T10:30:00Z")

    Returns:
        datetime object or None if parsing fails
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
