"""
Action Utilities

Shared utility functions for Figaro actions.
"""

import re


def sanitize_id_component(text: str, max_length: int = 30) -> str:
    """
    Sanitize text for use in action IDs.

    Removes special characters and limits length to prevent
    injection attacks or malformed IDs.

    Args:
        text: Text to sanitize
        max_length: Maximum length of sanitized text

    Returns:
        Sanitized text safe for use in action IDs
    """
    if not text:
        return "unknown"

    # Remove all characters except alphanumeric, spaces, underscores, and hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9_ -]", "", text)

    # Collapse multiple spaces/underscores
    sanitized = re.sub(r"[\s_-]+", "_", sanitized)

    # Strip leading/trailing underscores and whitespace
    sanitized = sanitized.strip("_ ")

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Ensure non-empty
    return sanitized if sanitized else "unknown"
