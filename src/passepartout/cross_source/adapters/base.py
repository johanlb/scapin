"""
Base protocol for source adapters.

Defines the interface that all source adapters must implement
to be used with CrossSourceEngine.

Includes standardized error handling utilities for consistent
behavior across all adapters.
"""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any, Callable, Protocol, TypeVar, runtime_checkable

from src.passepartout.cross_source.models import SourceItem

if TYPE_CHECKING:
    from collections.abc import Awaitable

logger = logging.getLogger("scapin.cross_source.adapters")

T = TypeVar("T")


@runtime_checkable
class SourceAdapter(Protocol):
    """
    Protocol for data source adapters.

    All adapters must implement this interface to be compatible
    with CrossSourceEngine. The protocol defines the minimal set
    of properties and methods required.

    Adapters are responsible for:
    - Connecting to their respective data source
    - Executing searches with the given query
    - Converting results to SourceItem format
    - Handling errors gracefully (return empty list on failure)

    Example implementation:
    ```python
    class MyAdapter:
        @property
        def source_name(self) -> str:
            return "my_source"

        @property
        def is_available(self) -> bool:
            return self._check_connection()

        async def search(
            self,
            query: str,
            max_results: int = 20,
            context: dict[str, Any] | None = None,
        ) -> list[SourceItem]:
            # Search implementation
            return results
    ```
    """

    @property
    def source_name(self) -> str:
        """
        The name of this source.

        Used for identification in results and logging.
        Should be lowercase, e.g., 'email', 'calendar', 'teams'.
        """
        ...

    @property
    def is_available(self) -> bool:
        """
        Whether this source is currently available.

        Should check if the source is properly configured and
        accessible. If False, CrossSourceEngine will skip this
        adapter during searches.
        """
        ...

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search this source for relevant items.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context dict with additional filters
                    (e.g., linked_sources, date ranges)

        Returns:
            List of SourceItem objects matching the query.
            Returns empty list on error (don't raise exceptions).

        The context dict may contain:
        - `linked_sources`: List of LinkedSource for targeted search
        - `date_from`: datetime for date range filtering
        - `date_to`: datetime for date range filtering
        - `contact`: str for filtering by contact/sender
        - Source-specific filters
        """
        ...


class BaseAdapter:
    """
    Base class for source adapters with common functionality.

    Provides helper methods and default implementations that
    concrete adapters can inherit and override.
    """

    _source_name: str = "base"
    _is_available: bool = False

    @property
    def source_name(self) -> str:
        """Get the source name."""
        return self._source_name

    @property
    def is_available(self) -> bool:
        """Check if the source is available."""
        return self._is_available

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search implementation - must be overridden.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context dict

        Returns:
            List of SourceItem objects
        """
        raise NotImplementedError("Subclasses must implement search()")

    def _truncate_content(self, content: str, max_length: int = 500) -> str:
        """
        Truncate content to max length with ellipsis.

        Args:
            content: The content to truncate
            max_length: Maximum length

        Returns:
            Truncated content string
        """
        if len(content) <= max_length:
            return content
        return content[: max_length - 3] + "..."

    def _normalize_query(self, query: str) -> str:
        """
        Normalize a search query.

        Args:
            query: The raw query string

        Returns:
            Normalized query
        """
        return query.strip().lower()


# --- Standardized Error Handling Utilities ---


class AdapterError(Exception):
    """Base exception for adapter errors."""

    def __init__(
        self,
        message: str,
        source: str = "unknown",
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.source = source
        self.original_error = original_error


class AdapterConnectionError(AdapterError):
    """Raised when adapter cannot connect to its data source."""

    pass


class AdapterTimeoutError(AdapterError):
    """Raised when adapter operation times out."""

    pass


class AdapterAuthenticationError(AdapterError):
    """Raised when adapter fails to authenticate."""

    pass


class AdapterRateLimitError(AdapterError):
    """Raised when adapter is rate limited."""

    pass


def safe_search(
    default_return: list[SourceItem] | None = None,
) -> Callable[[Callable[..., Awaitable[list[SourceItem]]]], Callable[..., Awaitable[list[SourceItem]]]]:
    """
    Decorator for safe error handling in adapter search methods.

    Catches all exceptions, logs them appropriately, and returns
    empty list (or specified default) instead of raising.

    Args:
        default_return: Value to return on error (default: empty list)

    Example:
        @safe_search()
        async def search(self, query: str, ...) -> list[SourceItem]:
            # Exceptions will be caught and logged
            return results
    """
    if default_return is None:
        default_return = []

    def decorator(
        func: Callable[..., Awaitable[list[SourceItem]]],
    ) -> Callable[..., Awaitable[list[SourceItem]]]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> list[SourceItem]:
            source_name = getattr(self, "source_name", "unknown")
            try:
                return await func(self, *args, **kwargs)
            except AdapterConnectionError as e:
                logger.warning(
                    "[%s] Connection error: %s",
                    source_name,
                    str(e),
                )
            except AdapterTimeoutError as e:
                logger.warning(
                    "[%s] Timeout: %s",
                    source_name,
                    str(e),
                )
            except AdapterAuthenticationError as e:
                logger.error(
                    "[%s] Authentication failed: %s",
                    source_name,
                    str(e),
                )
            except AdapterRateLimitError as e:
                logger.warning(
                    "[%s] Rate limited: %s",
                    source_name,
                    str(e),
                )
            except AdapterError as e:
                logger.error(
                    "[%s] Adapter error: %s",
                    source_name,
                    str(e),
                )
            except Exception as e:
                # Log type only to prevent sensitive data leakage
                logger.error(
                    "[%s] Unexpected error: %s",
                    source_name,
                    type(e).__name__,
                )
            return default_return

        return wrapper

    return decorator


def log_search_metrics(
    func: Callable[..., Awaitable[list[SourceItem]]],
) -> Callable[..., Awaitable[list[SourceItem]]]:
    """
    Decorator to log search metrics (duration, result count).

    Example:
        @log_search_metrics
        @safe_search()
        async def search(self, query: str, ...) -> list[SourceItem]:
            return results
    """
    import time

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> list[SourceItem]:
        source_name = getattr(self, "source_name", "unknown")
        query = args[0] if args else kwargs.get("query", "")
        start_time = time.perf_counter()

        results = await func(self, *args, **kwargs)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(
            "[%s] Search completed: query='%s' results=%d duration=%.0fms",
            source_name,
            query[:50] if query else "",
            len(results),
            duration_ms,
        )

        return results

    return wrapper
