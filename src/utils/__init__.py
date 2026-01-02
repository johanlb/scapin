"""
Utility Functions

Common helper functions for the PKM system.
"""

from .date_utils import (
    format_datetime,
    is_business_hours,
    next_business_day,
    now_utc,
    parse_date,
    time_ago,
)
from .file_utils import (
    atomic_write,
    ensure_dir,
    get_file_hash,
    list_files,
    safe_read_file,
    safe_write_file,
)
from .string_utils import (
    extract_email,
    extract_urls,
    normalize_whitespace,
    sanitize_filename,
    slugify,
    truncate,
)

__all__ = [
    # File utils
    "ensure_dir",
    "safe_read_file",
    "safe_write_file",
    "atomic_write",
    "list_files",
    "get_file_hash",
    # String utils
    "truncate",
    "sanitize_filename",
    "extract_email",
    "extract_urls",
    "slugify",
    "normalize_whitespace",
    # Date utils
    "now_utc",
    "parse_date",
    "format_datetime",
    "time_ago",
    "is_business_hours",
    "next_business_day",
]
