"""
Error Handling Utilities

Provides reusable error handling patterns to reduce code duplication.
Replaces 273+ repetitive `except Exception as e:` blocks across the codebase.
"""

import asyncio
import functools
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from logging import Logger
from typing import Optional, ParamSpec, TypeVar

from src.core.exceptions import ScapinError
from src.monitoring.logger import get_logger

T = TypeVar("T")
P = ParamSpec("P")

# Default logger for this module
_logger = get_logger("core.error_handling")


@dataclass
class ErrorResult:
    """Result of an operation that may have failed."""

    success: bool
    error: Optional[str] = None
    exception: Optional[Exception] = None

    @classmethod
    def ok(cls) -> "ErrorResult":
        """Create a successful result."""
        return cls(success=True)

    @classmethod
    def fail(cls, error: str, exception: Optional[Exception] = None) -> "ErrorResult":
        """Create a failed result."""
        return cls(success=False, error=error, exception=exception)


@contextmanager
def safe_operation(
    operation: str,
    logger: Optional[Logger] = None,
    log_level: str = "error",
    reraise: bool = False,
    reraise_types: tuple[type[Exception], ...] = (),
) -> Generator[None, None, None]:
    """
    Context manager for safe exception handling with logging.

    Usage:
        with safe_operation("fetch email", logger):
            result = imap_client.fetch(uid)
            # If exception occurs, it's logged and swallowed

        # With specific exceptions to reraise:
        with safe_operation("save note", logger, reraise_types=(ValidationError,)):
            note_manager.save(note)

    Args:
        operation: Description of the operation (for logging)
        logger: Logger to use (defaults to module logger)
        log_level: Log level for errors ("error", "warning", "debug")
        reraise: If True, reraise all exceptions after logging
        reraise_types: Tuple of exception types to always reraise
    """
    log = logger or _logger

    try:
        yield
    except reraise_types:
        # Always reraise these specific types
        raise
    except Exception as e:
        # Log the error
        log_func = getattr(log, log_level, log.error)
        log_func(f"Failed to {operation}: {e}", exc_info=log_level == "error")

        if reraise:
            raise


def with_error_handling(
    operation: str,
    logger: Optional[Logger] = None,
    default: T = None,  # type: ignore
    log_level: str = "error",
    reraise_types: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for functions that should catch and log exceptions.

    Usage:
        @with_error_handling("parse email", logger, default=[])
        def parse_emails(raw_data: bytes) -> list[Email]:
            ...

    Args:
        operation: Description of the operation
        logger: Logger to use
        default: Default value to return on error
        log_level: Log level for errors
        reraise_types: Exception types to reraise (not catch)
    """
    log = logger or _logger

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except reraise_types:
                raise
            except Exception as e:
                log_func = getattr(log, log_level, log.error)
                log_func(f"Failed to {operation}: {e}", exc_info=log_level == "error")
                return default  # type: ignore

        return wrapper

    return decorator


def with_async_error_handling(
    operation: str,
    logger: Optional[Logger] = None,
    default: T = None,  # type: ignore
    log_level: str = "error",
    reraise_types: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for async functions that should catch and log exceptions.

    Usage:
        @with_async_error_handling("fetch from API", logger, default={})
        async def fetch_data() -> dict:
            ...
    """
    log = logger or _logger

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)  # type: ignore
            except reraise_types:
                raise
            except Exception as e:
                log_func = getattr(log, log_level, log.error)
                log_func(f"Failed to {operation}: {e}", exc_info=log_level == "error")
                return default  # type: ignore

        return wrapper  # type: ignore

    return decorator


def safe_get(
    func: Callable[[], T],
    default: T,
    operation: str = "get value",
    logger: Optional[Logger] = None,
) -> T:
    """
    Safely call a function and return default on exception.

    Replaces the common pattern:
        try:
            value = some_function()
        except Exception:
            value = default_value

    Usage:
        confidence = safe_get(
            lambda: state.get_average_confidence(),
            default=0.0,
            operation="get confidence",
            logger=logger
        )
    """
    log = logger or _logger

    try:
        return func()
    except Exception as e:
        log.debug(f"Failed to {operation}: {e}")
        return default


async def safe_async_get(
    func: Callable[[], T],
    default: T,
    operation: str = "get value",
    logger: Optional[Logger] = None,
) -> T:
    """
    Async version of safe_get.

    Usage:
        data = await safe_async_get(
            lambda: client.fetch_data(),
            default={},
            operation="fetch data"
        )
    """
    log = logger or _logger

    try:
        result = func()
        if asyncio.iscoroutine(result):
            return await result
        return result  # type: ignore
    except Exception as e:
        log.debug(f"Failed to {operation}: {e}")
        return default


class ErrorCollector:
    """
    Collect multiple errors during a batch operation without stopping.

    Usage:
        collector = ErrorCollector("process emails")
        for email in emails:
            with collector.catch(f"email {email.id}"):
                process_email(email)

        if collector.has_errors:
            logger.warning(f"Completed with {collector.error_count} errors")
            for error in collector.errors:
                logger.debug(f"  - {error}")
    """

    def __init__(self, operation: str, logger: Optional[Logger] = None):
        self.operation = operation
        self.logger = logger or _logger
        self.errors: list[str] = []

    @contextmanager
    def catch(self, item_description: str) -> Generator[None, None, None]:
        """Catch and collect errors for a single item."""
        try:
            yield
        except Exception as e:
            error_msg = f"{item_description}: {e}"
            self.errors.append(error_msg)
            self.logger.debug(f"Error in {self.operation} - {error_msg}")

    @property
    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        """Get number of collected errors."""
        return len(self.errors)

    def summarize(self) -> str:
        """Get a summary of collected errors."""
        if not self.errors:
            return f"{self.operation}: completed successfully"
        return f"{self.operation}: {self.error_count} error(s) - {', '.join(self.errors[:5])}"


def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    logger: Optional[Logger] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that retries a function on exception.

    Usage:
        @retry_on_exception(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        def fetch_with_retry():
            return requests.get(url)
    """
    import time

    log = logger or _logger

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        log.warning(
                            f"Attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff

            # All attempts failed
            log.error(f"All {max_attempts} attempts failed: {last_exception}")
            raise last_exception  # type: ignore

        return wrapper

    return decorator


def map_exception(
    from_type: type[Exception],
    to_type: type[ScapinError],
    message_prefix: str = "",
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that converts one exception type to another.

    Useful for converting library exceptions to domain exceptions.

    Usage:
        @map_exception(imaplib.IMAP4.error, IMAPError, "IMAP operation failed")
        def fetch_email(uid: str) -> Email:
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except from_type as e:
                msg = f"{message_prefix}: {e}" if message_prefix else str(e)
                raise to_type(msg) from e

        return wrapper

    return decorator


def ensure_not_none(
    value: Optional[T],
    error_message: str = "Value cannot be None",
    exception_type: type[Exception] = ValueError,
) -> T:
    """
    Ensure a value is not None, raising an exception if it is.

    Usage:
        user = ensure_not_none(get_user(id), f"User {id} not found")
    """
    if value is None:
        raise exception_type(error_message)
    return value
