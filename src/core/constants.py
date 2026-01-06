"""
Constants

Centralized constants for the Scapin codebase.
Eliminates magic numbers and provides documentation for each value.
"""

from typing import Final

# =============================================================================
# Processing Limits
# =============================================================================

# Maximum items per batch to prevent overwhelming the system
DEFAULT_PROCESSING_LIMIT: Final[int] = 20

# Maximum content size for email bodies (prevent memory issues)
MAX_EMAIL_CONTENT_SIZE: Final[int] = 200_000  # 200KB

# Minimum content length to consider valid
MIN_CONTENT_LENGTH: Final[int] = 10

# Maximum characters to extract from email content
MAX_CONTENT_CHARS: Final[int] = 10_000

# Preview text lengths for display
PREVIEW_SHORT: Final[int] = 80
PREVIEW_MEDIUM: Final[int] = 150
PREVIEW_LONG: Final[int] = 200

# =============================================================================
# Rate Limiting & Retries
# =============================================================================

# Maximum wait time for exponential backoff (seconds)
MAX_BACKOFF_SECONDS: Final[int] = 60

# Connection retry backoff maximum (seconds)
CONNECTION_BACKOFF_MAX: Final[int] = 30

# Rate limiter window size (seconds)
RATE_LIMIT_WINDOW_SECONDS: Final[int] = 60

# API rate limit (requests per minute)
DEFAULT_API_RATE_LIMIT: Final[int] = 50

# =============================================================================
# Calendar & Time
# =============================================================================

# Calendar urgency thresholds (hours until event)
CALENDAR_URGENCY_URGENT_HOURS: Final[int] = 2
CALENDAR_URGENCY_HIGH_HOURS: Final[int] = 6
CALENDAR_URGENCY_MEDIUM_HOURS: Final[int] = 12
CALENDAR_URGENCY_LOW_HOURS: Final[int] = 24

# Conflict detection - minimum gap for travel (minutes)
CONFLICT_MIN_TRAVEL_GAP_MINUTES: Final[int] = 30

# =============================================================================
# Notes & Review (SM-2 Algorithm)
# =============================================================================

# Maximum daily reviews to prevent cognitive overload
MAX_DAILY_REVIEWS: Final[int] = 50

# Review session duration (minutes)
MAX_SESSION_DURATION_MINUTES: Final[int] = 5

# Minimum pattern occurrences for significance
MIN_PATTERN_OCCURRENCES: Final[int] = 3

# Confidence threshold for auto-applying changes
AUTO_APPLY_CONFIDENCE_THRESHOLD: Final[float] = 0.90

# =============================================================================
# Journal & Questions
# =============================================================================

# Maximum questions per category
MAX_LOW_CONFIDENCE_QUESTIONS: Final[int] = 5
MAX_HIGH_CONFIDENCE_QUESTIONS: Final[int] = 3
MAX_DECISION_QUESTIONS: Final[int] = 2
MAX_PRIORITY_QUESTIONS: Final[int] = 1
MAX_PATTERN_QUESTIONS: Final[int] = 5

# Pattern detection thresholds
PATTERN_APPROVAL_THRESHOLD: Final[float] = 0.8
PATTERN_MIN_COUNT: Final[int] = 3

# =============================================================================
# Caching
# =============================================================================

# Embedding cache size (number of embeddings)
EMBEDDING_CACHE_SIZE: Final[int] = 10_000

# Search result cache TTL (seconds)
SEARCH_CACHE_TTL_SECONDS: Final[int] = 60

# =============================================================================
# WebSocket
# =============================================================================

# Maximum recent events to keep in client
WS_MAX_RECENT_EVENTS: Final[int] = 50

# Reconnection delay (milliseconds)
WS_RECONNECT_DELAY_MS: Final[int] = 3_000

# Ping interval (milliseconds)
WS_PING_INTERVAL_MS: Final[int] = 30_000

# =============================================================================
# Text Processing
# =============================================================================

# ASCII printable range for content filtering
ASCII_PRINTABLE_START: Final[int] = 0x20  # Space
ASCII_PRINTABLE_END: Final[int] = 0x7E  # Tilde

# Maximum filename length
MAX_FILENAME_LENGTH: Final[int] = 255

# =============================================================================
# API Response
# =============================================================================

# Default page size for paginated responses
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100

# Request timeout (seconds)
DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[int] = 30
LONG_REQUEST_TIMEOUT_SECONDS: Final[int] = 120

# =============================================================================
# UI/Display
# =============================================================================

# Terminal display widths
TERMINAL_MIN_WIDTH: Final[int] = 80
TERMINAL_DEFAULT_WIDTH: Final[int] = 120

# Table column widths
TABLE_SUBJECT_WIDTH: Final[int] = 40
TABLE_FROM_WIDTH: Final[int] = 25
TABLE_DATE_WIDTH: Final[int] = 16
