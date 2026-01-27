"""
JSON Utilities for AI Response Parsing

Functions for cleaning and repairing JSON responses from LLM APIs.
Extracted from router.py to avoid circular imports.
"""

import re

from src.monitoring.logger import get_logger

logger = get_logger("sancho.json_utils")


def clean_json_string(json_str: str) -> str:
    """
    Clean a JSON string by fixing common issues from LLM responses.

    Handles:
    - Trailing commas before ] or }
    - Missing commas between properties/elements
    - Single-line comments (// ...)
    - Multi-line comments (/* ... */)
    - Markdown code blocks (```json ... ```)
    - Extra text before/after JSON

    Args:
        json_str: Raw JSON string that might be malformed

    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks if present
    json_str = re.sub(r"```json\s*", "", json_str)
    json_str = re.sub(r"```\s*$", "", json_str)
    json_str = re.sub(r"```", "", json_str)

    # Remove single-line comments (// ...)
    json_str = re.sub(r"//[^\n]*", "", json_str)

    # Remove multi-line comments (/* ... */)
    json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

    # Remove trailing commas before ] or }
    # Pattern: comma followed by optional whitespace, then ] or }
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

    # Fix missing commas between properties (any whitespace including spaces):
    # Pattern: "value" followed by any whitespace then "key"
    # e.g., '"value"   "key"' or '"value"\n    "key"' → '"value", "key"'
    json_str = re.sub(r'"\s+(")', r'", \1', json_str)

    # Fix missing commas after numbers/booleans/null before "
    # e.g., '95   "reasoning"' or '95\n    "reasoning"' → '95, "reasoning"'
    json_str = re.sub(r'(\d+)\s+(")', r"\1, \2", json_str)
    json_str = re.sub(r'(true|false|null)\s+(")', r"\1, \2", json_str)

    # Fix missing commas after ] or } before " or [ or {
    # e.g., ']   "key"' or '}\n    "key"' → '], "key"'
    json_str = re.sub(r'(\])\s+("|\[|\{)', r"\1, \2", json_str)
    json_str = re.sub(r'(\})\s+("|\[|\{)', r"\1, \2", json_str)

    # Fix missing commas between array elements (objects in arrays):
    # e.g., '}\n    {' → '}, {'  (between objects in an array)
    json_str = re.sub(r"(\})\s*\n\s*(\{)", r"\1, \2", json_str)
    json_str = re.sub(r"(\])\s*\n\s*(\[)", r"\1, \2", json_str)

    return json_str


def repair_json_with_library(json_str: str) -> tuple[str, bool]:
    """
    Use json-repair library for robust JSON repair.

    This handles complex cases like:
    - Missing commas in nested structures
    - Unquoted strings
    - Trailing commas
    - Single quotes instead of double quotes

    Args:
        json_str: Malformed JSON string

    Returns:
        Tuple of (repaired JSON string, success boolean)
    """
    try:
        from json_repair import repair_json

        repaired = repair_json(json_str)
        return repaired, True
    except ImportError:
        logger.warning("json-repair library not installed, falling back to regex")
        return json_str, False
    except Exception as e:
        logger.warning(f"json-repair failed: {e}")
        return json_str, False
