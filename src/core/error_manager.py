"""
Error Management System

Centralized error handling, tracking, and recovery for the PKM system.
Provides structured error representation, persistence, and automatic recovery.

Architecture:
    ErrorManager → ErrorStore (SQLite)
                → RecoveryEngine (retry/fix logic)
                → ErrorAnalyzer (pattern detection)

Usage:
    from src.core.error_manager import get_error_manager, ErrorCategory, ErrorSeverity

    error_manager = get_error_manager()

    try:
        # ... risky operation ...
    except Exception as e:
        error = error_manager.record_error(
            exception=e,
            category=ErrorCategory.IMAP,
            context={"email_id": 123, "folder": "INBOX"}
        )

        # Try recovery
        if error_manager.can_recover(error):
            error_manager.attempt_recovery(error)
"""

import json
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.core.error_store import ErrorStore
from src.utils import now_utc

logger = get_logger("error_manager")


def sanitize_context(context: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize context dictionary to ensure JSON serializability

    Converts non-serializable objects to strings to prevent crashes
    during error storage or JSON serialization.

    Args:
        context: Raw context dictionary that may contain non-serializable objects

    Returns:
        Sanitized dictionary with only JSON-serializable values

    Example:
        >>> import threading
        >>> ctx = {"id": 123, "thread": threading.current_thread(), "data": [1, 2, 3]}
        >>> sanitized = sanitize_context(ctx)
        >>> json.dumps(sanitized)  # Won't crash
        '{"id": 123, "thread": "<Thread(...)>", "data": [1, 2, 3]}'
    """
    if not context:
        return {}

    sanitized = {}

    for key, value in context.items():
        try:
            # Test if value is JSON serializable
            json.dumps(value)
            sanitized[key] = value
        except (TypeError, ValueError, OverflowError):
            # Not serializable - convert to string
            try:
                sanitized[key] = str(value)
            except Exception:
                # Even str() failed - use type name
                sanitized[key] = f"<{type(value).__name__}>"

    return sanitized


class ErrorCategory(str, Enum):
    """Categories of errors"""

    IMAP = "imap"  # IMAP connection/operation errors
    AI = "ai"  # AI API errors (rate limit, timeout, invalid response)
    VALIDATION = "validation"  # Schema validation errors
    FILESYSTEM = "filesystem"  # File I/O errors
    DATABASE = "database"  # SQLite errors
    NETWORK = "network"  # Network connectivity errors
    CONFIGURATION = "configuration"  # Config errors
    PARSING = "parsing"  # Email/content parsing errors
    INTEGRATION = "integration"  # External service errors (OmniFocus, etc.)
    UNKNOWN = "unknown"  # Uncategorized errors


class ErrorSeverity(str, Enum):
    """Severity levels for errors"""

    LOW = "low"  # Minor issue, doesn't block processing
    MEDIUM = "medium"  # Significant issue, may skip item
    HIGH = "high"  # Critical issue, blocks processing
    CRITICAL = "critical"  # System-level failure, requires immediate attention


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error types"""

    RETRY = "retry"  # Simple retry after delay
    RECONNECT = "reconnect"  # Reconnect to service
    SKIP = "skip"  # Skip problematic item and continue
    FALLBACK = "fallback"  # Use fallback mechanism
    MANUAL = "manual"  # Requires manual intervention
    NONE = "none"  # No recovery possible


@dataclass
class SystemError:
    """
    Structured representation of a system error

    Contains all information needed to understand, track, and recover from errors.
    """

    # Identity
    id: str  # Unique error ID (timestamp-based)
    timestamp: datetime

    # Classification
    category: ErrorCategory
    severity: ErrorSeverity

    # Error details
    exception_type: str  # e.g., "ConnectionError", "ValueError"
    exception_message: str
    traceback: str

    # Context
    component: str  # e.g., "EmailProcessor", "IMAPClient"
    operation: str  # e.g., "fetch_emails", "analyze_email"
    context: dict[str, Any] = field(default_factory=dict)  # Additional context

    # Recovery
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE
    recovery_attempted: bool = False
    recovery_successful: Optional[bool] = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3

    # Metadata
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "severity": self.severity.value,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "traceback": self.traceback,
            "component": self.component,
            "operation": self.operation,
            "context": self.context,
            "recovery_strategy": self.recovery_strategy.value,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "recovery_attempts": self.recovery_attempts,
            "max_recovery_attempts": self.max_recovery_attempts,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SystemError":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            category=ErrorCategory(data["category"]),
            severity=ErrorSeverity(data["severity"]),
            exception_type=data["exception_type"],
            exception_message=data["exception_message"],
            traceback=data["traceback"],
            component=data["component"],
            operation=data["operation"],
            context=data.get("context", {}),
            recovery_strategy=RecoveryStrategy(data.get("recovery_strategy", "none")),
            recovery_attempted=data.get("recovery_attempted", False),
            recovery_successful=data.get("recovery_successful"),
            recovery_attempts=data.get("recovery_attempts", 0),
            max_recovery_attempts=data.get("max_recovery_attempts", 3),
            resolved=data.get("resolved", False),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            notes=data.get("notes", ""),
        )

    def __str__(self) -> str:
        """Human-readable representation"""
        return (
            f"[{self.severity.value.upper()}] {self.category.value}: "
            f"{self.exception_type} in {self.component}.{self.operation}() - "
            f"{self.exception_message}"
        )


class ErrorManager:
    """
    Centralized error management system

    Responsibilities:
    - Record errors with full context
    - Classify errors by category and severity
    - Store errors for analysis
    - Attempt automatic recovery
    - Track error patterns
    """

    def __init__(
        self,
        error_store: Optional["ErrorStore"] = None,
        max_in_memory_errors: int = 1000
    ):
        """
        Initialize error manager

        Args:
            error_store: Optional ErrorStore for persistence (will create default if None)
            max_in_memory_errors: Maximum number of errors to keep in memory (prevents unbounded growth)
        """
        self.error_store = error_store
        self.recovery_handlers: dict[ErrorCategory, Callable] = {}
        self.error_count = 0
        self.errors_by_category: dict[ErrorCategory, int] = {}
        self.max_in_memory_errors = max_in_memory_errors
        self._recent_errors: list[SystemError] = []  # LRU cache for recent errors

        # Register default recovery handlers
        self._register_default_recovery_handlers()

        logger.info(
            "ErrorManager initialized",
            extra={"max_in_memory_errors": max_in_memory_errors}
        )

    def record_error(
        self,
        exception: Exception,
        category: ErrorCategory,
        component: str,
        operation: str,
        severity: Optional[ErrorSeverity] = None,
        context: Optional[dict[str, Any]] = None,
        recovery_strategy: Optional[RecoveryStrategy] = None,
    ) -> SystemError:
        """
        Record an error with full context

        Args:
            exception: The exception that occurred
            category: Error category
            component: Component where error occurred
            operation: Operation that failed
            severity: Error severity (auto-detected if None)
            context: Additional context
            recovery_strategy: Recovery strategy (auto-detected if None)

        Returns:
            SystemError object

        Example:
            try:
                self.imap_client.connect()
            except ConnectionError as e:
                error = error_manager.record_error(
                    exception=e,
                    category=ErrorCategory.IMAP,
                    component="IMAPClient",
                    operation="connect",
                    context={"host": "imap.gmail.com", "port": 993}
                )
        """
        # Generate error ID
        error_id = f"{category.value}_{int(now_utc().timestamp() * 1000)}"

        # Auto-detect severity if not provided
        if severity is None:
            severity = self._detect_severity(exception, category)

        # Auto-detect recovery strategy if not provided
        if recovery_strategy is None:
            recovery_strategy = self._detect_recovery_strategy(exception, category)

        # Sanitize context to ensure JSON serializability
        sanitized_context = sanitize_context(context or {})

        # Create SystemError
        error = SystemError(
            id=error_id,
            timestamp=now_utc(),
            category=category,
            severity=severity,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback=traceback.format_exc(),
            component=component,
            operation=operation,
            context=sanitized_context,
            recovery_strategy=recovery_strategy,
        )

        # Update stats
        self.error_count += 1
        self.errors_by_category[category] = self.errors_by_category.get(category, 0) + 1

        # Add to in-memory cache (LRU)
        self._recent_errors.append(error)
        if len(self._recent_errors) > self.max_in_memory_errors:
            # Remove oldest error when limit exceeded
            self._recent_errors.pop(0)

        # Store error in persistent storage
        if self.error_store:
            self.error_store.save_error(error)

        # Log error
        logger.error(
            f"Error recorded: {error}",
            extra={
                "error_id": error.id,
                "category": category.value,
                "severity": severity.value,
                "component": component,
                "operation": operation,
                "exception_type": type(exception).__name__,
            },
        )

        return error

    def can_recover(self, error: SystemError) -> bool:
        """
        Check if error can be recovered

        Args:
            error: SystemError to check

        Returns:
            True if recovery is possible
        """
        # Check if recovery attempts exhausted
        if error.recovery_attempts >= error.max_recovery_attempts:
            logger.debug(f"Error {error.id} exhausted recovery attempts")
            return False

        # Check if already resolved
        if error.resolved:
            return False

        # Check if recovery strategy exists
        if error.recovery_strategy == RecoveryStrategy.NONE:
            return False

        # Check if manual intervention required
        return error.recovery_strategy != RecoveryStrategy.MANUAL

    def attempt_recovery(self, error: SystemError) -> bool:
        """
        Attempt to recover from error

        Args:
            error: SystemError to recover from

        Returns:
            True if recovery successful

        Example:
            if error_manager.can_recover(error):
                success = error_manager.attempt_recovery(error)
                if success:
                    print("Recovered from error!")
        """
        if not self.can_recover(error):
            logger.warning(f"Cannot recover from error {error.id}")
            return False

        # Update recovery attempt count
        error.recovery_attempted = True
        error.recovery_attempts += 1

        logger.info(
            f"Attempting recovery for error {error.id} "
            f"(attempt {error.recovery_attempts}/{error.max_recovery_attempts})",
            extra={
                "error_id": error.id,
                "strategy": error.recovery_strategy.value,
                "attempt": error.recovery_attempts,
            },
        )

        # Get recovery handler
        handler = self.recovery_handlers.get(error.category)

        if not handler:
            logger.warning(f"No recovery handler for category {error.category.value}")
            error.recovery_successful = False
            return False

        # Attempt recovery
        try:
            success = handler(error)
            error.recovery_successful = success

            if success:
                error.resolved = True
                error.resolved_at = now_utc()
                logger.info(f"Successfully recovered from error {error.id}")
            else:
                logger.warning(f"Recovery failed for error {error.id}")

            # Update in store
            if self.error_store:
                self.error_store.update_error(error)

            return success

        except Exception as e:
            logger.error(
                f"Recovery attempt failed with exception: {e}",
                exc_info=True,
                extra={"error_id": error.id},
            )
            error.recovery_successful = False
            return False

    def register_recovery_handler(
        self, category: ErrorCategory, handler: Callable[[SystemError], bool]
    ) -> None:
        """
        Register a recovery handler for an error category

        Args:
            category: Error category
            handler: Recovery function that takes SystemError and returns bool

        Example:
            def recover_imap(error: SystemError) -> bool:
                # Reconnect to IMAP
                return reconnect_imap(error.context)

            error_manager.register_recovery_handler(ErrorCategory.IMAP, recover_imap)
        """
        self.recovery_handlers[category] = handler
        logger.debug(f"Registered recovery handler for {category.value}")

    def _register_default_recovery_handlers(self) -> None:
        """Register default recovery handlers"""
        # Placeholder - will be implemented in RecoveryEngine
        pass

    def _detect_severity(
        self, exception: Exception, category: ErrorCategory
    ) -> ErrorSeverity:
        """
        Auto-detect error severity

        Args:
            exception: The exception
            category: Error category

        Returns:
            Detected severity
        """
        exception_type = type(exception).__name__

        # Critical errors
        if exception_type in ["SystemExit", "KeyboardInterrupt", "MemoryError"]:
            return ErrorSeverity.CRITICAL

        # High severity errors
        if exception_type in ["ConnectionError", "TimeoutError", "PermissionError"]:
            return ErrorSeverity.HIGH

        # Category-based severity
        if category == ErrorCategory.IMAP:
            if "authentication" in str(exception).lower():
                return ErrorSeverity.CRITICAL
            return ErrorSeverity.HIGH

        if category == ErrorCategory.AI:
            if "rate limit" in str(exception).lower():
                return ErrorSeverity.MEDIUM
            return ErrorSeverity.HIGH

        # Default to medium
        return ErrorSeverity.MEDIUM

    def _detect_recovery_strategy(
        self, exception: Exception, category: ErrorCategory
    ) -> RecoveryStrategy:
        """
        Auto-detect recovery strategy

        Args:
            exception: The exception
            category: Error category

        Returns:
            Detected recovery strategy
        """
        exception_type = type(exception).__name__

        # Connection errors → reconnect
        if exception_type in ["ConnectionError", "TimeoutError"]:
            return RecoveryStrategy.RECONNECT

        # Rate limit → retry
        if "rate limit" in str(exception).lower():
            return RecoveryStrategy.RETRY

        # Category-based strategies
        if category == ErrorCategory.IMAP:
            return RecoveryStrategy.RECONNECT

        if category == ErrorCategory.AI:
            return RecoveryStrategy.RETRY

        if category == ErrorCategory.VALIDATION:
            return RecoveryStrategy.SKIP

        # Default to manual
        return RecoveryStrategy.MANUAL

    def get_error_stats(self) -> dict[str, Any]:
        """
        Get error statistics

        Returns:
            Dictionary with error stats
        """
        return {
            "total_errors": self.error_count,
            "errors_by_category": {
                cat.value: count for cat, count in self.errors_by_category.items()
            },
            "in_memory_errors": len(self._recent_errors),
            "memory_limit": self.max_in_memory_errors,
        }

    def get_recent_errors(self, limit: int = 10) -> list[SystemError]:
        """
        Get recent errors from in-memory cache

        Fast access to recent errors without database query.
        For older errors, use error_store.get_recent_errors() directly.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent SystemError objects (newest first)
        """
        # Return from in-memory cache (newest first)
        return list(reversed(self._recent_errors[-limit:]))

    def reset_stats(self) -> None:
        """
        Reset in-memory statistics

        Clears error counts and in-memory cache.
        Persistent storage in database is NOT affected.

        Use this to prevent unbounded memory growth in long-running processes.
        """
        self.error_count = 0
        self.errors_by_category.clear()
        self._recent_errors.clear()
        logger.info("Error statistics reset")


# Global error manager instance (singleton)
_error_manager: Optional[ErrorManager] = None
_error_manager_lock = threading.Lock()


def get_error_manager() -> ErrorManager:
    """
    Get the global error manager instance (singleton)

    Thread-safe singleton with double-check locking pattern.

    Returns:
        The global ErrorManager instance

    Example:
        error_manager = get_error_manager()
        error_manager.record_error(...)
    """
    global _error_manager

    # Fast path: already initialized
    if _error_manager is not None:
        return _error_manager

    # Slow path: need to initialize
    with _error_manager_lock:
        # Double-check inside lock (another thread might have initialized)
        if _error_manager is None:
            # Import here to avoid circular dependency
            from src.core.error_store import get_error_store

            error_store = get_error_store()
            _error_manager = ErrorManager(error_store=error_store)
            logger.info("Created global error manager instance")

    return _error_manager


def reset_error_manager() -> None:
    """
    Reset the global error manager instance

    Only used in tests to ensure clean state.
    """
    global _error_manager
    _error_manager = None
    logger.debug("Reset global error manager instance")
