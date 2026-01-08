"""
Base protocol for source adapters.

Defines the interface that all source adapters must implement
to be used with CrossSourceEngine.
"""

from typing import Any, Protocol, runtime_checkable

from src.passepartout.cross_source.models import SourceItem


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
