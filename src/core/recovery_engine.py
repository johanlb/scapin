"""
Recovery Engine - Automatic Error Recovery

Implements recovery strategies for different error types:
- IMAP: Reconnect, retry with backoff
- AI: Retry with exponential backoff, fallback models
- Network: Retry with backoff
- Validation: Skip and continue

Each recovery strategy is implemented as a handler function that:
1. Analyzes the error context
2. Attempts recovery
3. Returns True if successful, False otherwise

Usage:
    from src.core.recovery_engine import RecoveryEngine
    from src.core.error_manager import get_error_manager

    engine = RecoveryEngine()
    error_manager = get_error_manager()

    # Register recovery handlers
    engine.register_handlers(error_manager)

    # Errors will now be automatically recovered when possible
"""

import time
from typing import Optional, Any
from src.core.error_manager import (
    SystemError,
    ErrorCategory,
    RecoveryStrategy,
    get_error_manager,
)
from src.monitoring.logger import get_logger
from src.utils.timeout import timeout_context, TimeoutError

logger = get_logger("recovery_engine")


class RecoveryEngine:
    """
    Automatic error recovery engine

    Implements recovery strategies for different error categories.
    """

    def __init__(self, default_timeout: int = 30):
        """
        Initialize recovery engine

        Args:
            default_timeout: Default timeout for recovery operations (seconds)
        """
        self.max_retry_delay = 60  # Maximum retry delay in seconds
        self.base_retry_delay = 1  # Base retry delay in seconds
        self.default_timeout = default_timeout  # Timeout for recovery operations

        logger.info(
            "RecoveryEngine initialized",
            extra={"default_timeout": default_timeout}
        )

    def register_handlers(self, error_manager: Optional[Any] = None) -> None:
        """
        Register recovery handlers with error manager

        Args:
            error_manager: ErrorManager instance (uses global if None)
        """
        if error_manager is None:
            error_manager = get_error_manager()

        # Register handlers for each category
        error_manager.register_recovery_handler(ErrorCategory.IMAP, self.recover_imap)
        error_manager.register_recovery_handler(ErrorCategory.AI, self.recover_ai)
        error_manager.register_recovery_handler(
            ErrorCategory.NETWORK, self.recover_network
        )
        error_manager.register_recovery_handler(
            ErrorCategory.VALIDATION, self.recover_validation
        )

        logger.info("Registered recovery handlers with ErrorManager")

    def recover_imap(self, error: SystemError) -> bool:
        """
        Recover from IMAP errors

        Strategies:
        - Connection errors: Reconnect with exponential backoff
        - Authentication errors: Cannot auto-recover (manual intervention needed)
        - Timeout errors: Retry with backoff
        - Parse errors: Skip and continue

        Args:
            error: SystemError with IMAP category

        Returns:
            True if recovery successful
        """
        logger.info(
            f"Attempting IMAP recovery for error {error.id}",
            extra={
                "error_id": error.id,
                "operation": error.operation,
                "exception_type": error.exception_type,
            },
        )

        # Authentication errors cannot be auto-recovered
        if "authentication" in error.exception_message.lower() or error.exception_type == "PermissionError":
            logger.warning("Authentication error - manual intervention required")
            return False

        # Connection/timeout errors - retry with backoff
        if error.exception_type in ["ConnectionError", "TimeoutError", "OSError"]:
            return self._retry_with_backoff(error, self._imap_reconnect)

        # Parse errors - skip
        if error.exception_type in ["ValueError", "UnicodeDecodeError"]:
            logger.info(f"Skipping unparseable item in {error.operation}")
            return True  # Consider "success" = skip and continue

        # Default: try reconnect
        return self._retry_with_backoff(error, self._imap_reconnect)

    def recover_ai(self, error: SystemError) -> bool:
        """
        Recover from AI API errors

        Strategies:
        - Rate limit: Retry with exponential backoff
        - Timeout: Retry with backoff
        - Invalid response: Retry (might be transient)
        - API errors: Retry with backoff

        Args:
            error: SystemError with AI category

        Returns:
            True if recovery successful
        """
        logger.info(
            f"Attempting AI recovery for error {error.id}",
            extra={
                "error_id": error.id,
                "operation": error.operation,
                "exception_type": error.exception_type,
            },
        )

        # Rate limit errors - wait longer
        if "rate limit" in error.exception_message.lower():
            delay = self._calculate_backoff_delay(error, base=5)
            logger.info(f"Rate limit hit, waiting {delay}s before retry")
            time.sleep(delay)
            return True  # Recovery = wait completed

        # Timeout/connection errors - retry
        if error.exception_type in ["TimeoutError", "ConnectionError"]:
            return self._retry_with_backoff(error, None)

        # Invalid JSON/response - retry (might be transient)
        if error.exception_type in ["ValueError", "JSONDecodeError"]:
            return self._retry_with_backoff(error, None)

        # Default: retry with backoff
        return self._retry_with_backoff(error, None)

    def recover_network(self, error: SystemError) -> bool:
        """
        Recover from network errors

        Strategy: Retry with exponential backoff

        Args:
            error: SystemError with NETWORK category

        Returns:
            True if recovery successful
        """
        logger.info(f"Attempting network recovery for error {error.id}")
        return self._retry_with_backoff(error, None)

    def recover_validation(self, error: SystemError) -> bool:
        """
        Recover from validation errors

        Strategy: Skip invalid item and continue

        Args:
            error: SystemError with VALIDATION category

        Returns:
            True (always succeeds by skipping)
        """
        logger.info(
            f"Skipping invalid item in {error.operation}",
            extra={"error_id": error.id, "operation": error.operation},
        )
        # Recovery = skip and continue
        return True

    def _retry_with_backoff(
        self, error: SystemError, reconnect_fn: Optional[callable] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Retry with exponential backoff and timeout protection

        Waits with exponential backoff and calls reconnect function with timeout.
        Prevents infinite hangs during recovery.

        Args:
            error: SystemError to recover from
            reconnect_fn: Optional function to call for reconnection
            timeout: Timeout in seconds (uses default if None)

        Returns:
            True if retry should proceed (after waiting)
        """
        delay = self._calculate_backoff_delay(error)

        logger.info(
            f"Retry attempt {error.recovery_attempts + 1} after {delay}s delay",
            extra={
                "error_id": error.id,
                "delay": delay,
                "attempt": error.recovery_attempts + 1,
            },
        )

        # Wait
        time.sleep(delay)

        # Call reconnect function if provided (with timeout)
        if reconnect_fn:
            timeout_val = timeout or self.default_timeout

            try:
                # Wrap reconnect in timeout context
                with timeout_context(
                    timeout_val,
                    f"Recovery operation timed out after {timeout_val}s"
                ):
                    reconnect_fn(error)

                logger.debug(
                    f"Reconnect completed within timeout",
                    extra={"error_id": error.id, "timeout": timeout_val}
                )

            except TimeoutError as e:
                logger.error(
                    f"Reconnect timed out after {timeout_val}s",
                    extra={"error_id": error.id, "timeout": timeout_val}
                )
                return False

            except Exception as e:
                logger.error(
                    f"Reconnect failed: {e}",
                    exc_info=True,
                    extra={"error_id": error.id}
                )
                return False

        return True  # Recovery = wait + reconnect completed

    def _calculate_backoff_delay(
        self, error: SystemError, base: Optional[float] = None
    ) -> float:
        """
        Calculate exponential backoff delay

        Args:
            error: SystemError (uses recovery_attempts)
            base: Base delay in seconds (uses default if None)

        Returns:
            Delay in seconds
        """
        if base is None:
            base = self.base_retry_delay

        # Exponential backoff: base * 2^attempts
        delay = base * (2 ** error.recovery_attempts)

        # Cap at max delay
        delay = min(delay, self.max_retry_delay)

        return delay

    def _imap_reconnect(self, error: SystemError) -> None:
        """
        Reconnect to IMAP server

        This is a placeholder that logs the reconnection attempt.
        Actual reconnection is handled by IMAPClient when operations are retried.

        Args:
            error: SystemError with IMAP context
        """
        logger.info(
            f"IMAP reconnection will be attempted on next operation",
            extra={
                "error_id": error.id,
                "host": error.context.get("host"),
                "port": error.context.get("port"),
            },
        )

        # Note: Actual reconnection happens when IMAPClient.connect() is called again
        # We don't force reconnection here to avoid circular dependencies
        # The connection will be re-established on the next operation


def init_recovery_engine() -> RecoveryEngine:
    """
    Initialize and register recovery engine

    Returns:
        RecoveryEngine instance

    Example:
        # In main initialization
        engine = init_recovery_engine()
        # Now errors will be automatically recovered
    """
    engine = RecoveryEngine()
    engine.register_handlers()
    logger.info("Recovery engine initialized and handlers registered")
    return engine
