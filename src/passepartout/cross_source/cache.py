"""
TTL Cache for CrossSourceEngine.

Provides a time-limited cache for cross-source search results,
reducing redundant searches within the same work session.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cachetools import TTLCache

if TYPE_CHECKING:
    from src.passepartout.cross_source.models import CrossSourceResult

logger = logging.getLogger("scapin.cross_source.cache")


class CrossSourceCache:
    """
    TTL cache for cross-source search results.

    Caches search results for a configurable duration (default 15 minutes)
    to avoid redundant searches during a typical work session.

    Thread-safe via cachetools.TTLCache internals.
    """

    def __init__(
        self,
        ttl_seconds: int = 900,  # 15 minutes
        max_size: int = 100,
    ) -> None:
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries in the cache
        """
        self._cache: TTLCache[str, CrossSourceResult] = TTLCache(
            maxsize=max_size,
            ttl=ttl_seconds,
        )
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        logger.debug(
            "CrossSourceCache initialized (ttl=%ds, max_size=%d)",
            ttl_seconds,
            max_size,
        )

    def _make_key(self, query: str, sources: list[str]) -> str:
        """
        Generate a cache key from query and sources.

        Args:
            query: The search query
            sources: List of source names searched

        Returns:
            Cache key string
        """
        # Normalize query and sort sources for consistent keys
        normalized_query = query.lower().strip()
        sources_str = ",".join(sorted(sources))
        return f"{normalized_query}|{sources_str}"

    def get(self, query: str, sources: list[str]) -> CrossSourceResult | None:
        """
        Get a cached result if available.

        Args:
            query: The search query
            sources: List of source names to match

        Returns:
            Cached CrossSourceResult or None if not found/expired
        """
        key = self._make_key(query, sources)
        result = self._cache.get(key)

        if result is not None:
            logger.debug("Cache HIT for query: %s", query[:50])
            # Mark result as coming from cache
            result.from_cache = True
        else:
            logger.debug("Cache MISS for query: %s", query[:50])

        return result

    def set(
        self,
        query: str,
        sources: list[str],
        result: CrossSourceResult,
    ) -> None:
        """
        Store a result in the cache.

        Args:
            query: The search query
            sources: List of source names searched
            result: The CrossSourceResult to cache
        """
        key = self._make_key(query, sources)
        self._cache[key] = result
        logger.debug(
            "Cached result for query: %s (%d items)",
            query[:50],
            len(result.items),
        )

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with current size and max size
        """
        return {
            "current_size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl_seconds,
        }

    @property
    def size(self) -> int:
        """Current number of entries in the cache."""
        return len(self._cache)
