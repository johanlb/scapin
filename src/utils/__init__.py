"""
Utility Functions

Common helper functions for the PKM system.
"""

from .file_utils import (
    ensure_dir,
    safe_read_file,
    safe_write_file,
    atomic_write,
    list_files,
    get_file_hash,
)

from .string_utils import (
    truncate,
    sanitize_filename,
    extract_email,
    extract_urls,
    slugify,
    normalize_whitespace,
)

from .date_utils import (
    now_utc,
    parse_date,
    format_datetime,
    time_ago,
    is_business_hours,
    next_business_day,
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
