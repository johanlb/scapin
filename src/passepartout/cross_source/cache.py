"""
TTL Cache for CrossSourceEngine.

Provides a time-limited cache for cross-source search results,
reducing redundant searches within the same work session.

Supports per-source TTL for different freshness requirements
(e.g., web results cached longer than email results).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.passepartout.cross_source.models import CrossSourceResult

logger = logging.getLogger("scapin.cross_source.cache")

# Default TTL values per source (in seconds)
DEFAULT_SOURCE_TTLS: dict[str, int] = {
    "email": 600,         # 10 min - emails change frequently
    "calendar": 1800,     # 30 min - calendar is relatively stable
    "icloud_calendar": 1800,
    "teams": 300,         # 5 min - chat messages change quickly
    "whatsapp": 300,      # 5 min
    "files": 3600,        # 1 hour - local files rarely change
    "web": 7200,          # 2 hours - web results stable
    "notes": 1800,        # 30 min
}


@dataclass
class CacheEntry:
    """A cached result with expiry timestamp."""
    result: CrossSourceResult
    expires_at: float  # Unix timestamp


class CrossSourceCache:
    """
    TTL cache for cross-source search results.

    Caches search results with per-source TTL support:
    - Web results cached longer (2 hours) - stable external data
    - Email/Teams cached shorter (5-10 min) - frequently changing
    - Calendar cached medium (30 min) - relatively stable

    Thread-safe for typical use cases.
    """

    def __init__(
        self,
        ttl_seconds: int = 900,  # Default TTL (15 minutes)
        max_size: int = 100,
        source_ttls: dict[str, int] | None = None,
    ) -> None:
        """
        Initialize the cache.

        Args:
            ttl_seconds: Default TTL for cache entries (when source-specific not found)
            max_size: Maximum number of entries in the cache
            source_ttls: Per-source TTL values (optional, uses DEFAULT_SOURCE_TTLS if None)
        """
        self._entries: dict[str, CacheEntry] = {}
        self._default_ttl = ttl_seconds
        self._max_size = max_size
        self._source_ttls = {**DEFAULT_SOURCE_TTLS, **(source_ttls or {})}

        # Stats tracking
        self._hits = 0
        self._misses = 0

        logger.debug(
            "CrossSourceCache initialized (default_ttl=%ds, max_size=%d, per_source_ttl=enabled)",
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

    def _calculate_ttl(self, sources: list[str]) -> int:
        """
        Calculate TTL for a cache entry based on sources searched.

        Uses the minimum TTL among all sources to ensure freshness.
        If a query searches both email (10min) and files (1hr),
        we use 10min to ensure email freshness.

        Args:
            sources: List of source names

        Returns:
            TTL in seconds
        """
        if not sources:
            return self._default_ttl

        # Get TTL for each source, use minimum
        source_ttls = [
            self._source_ttls.get(source, self._default_ttl)
            for source in sources
        ]
        return min(source_ttls)

    def _cleanup_expired(self) -> None:
        """Remove expired entries from the cache."""
        now = time.time()
        expired_keys = [
            key for key, entry in self._entries.items()
            if entry.expires_at <= now
        ]
        for key in expired_keys:
            del self._entries[key]

    def _evict_oldest(self) -> None:
        """Evict oldest entries if cache is full."""
        if len(self._entries) < self._max_size:
            return

        # Sort by expiry time and remove oldest
        sorted_entries = sorted(
            self._entries.items(),
            key=lambda x: x[1].expires_at
        )
        # Remove oldest 10% or at least 1
        to_remove = max(1, len(sorted_entries) // 10)
        for key, _ in sorted_entries[:to_remove]:
            del self._entries[key]

    def get(self, query: str, sources: list[str]) -> CrossSourceResult | None:
        """
        Get a cached result if available and not expired.

        Args:
            query: The search query
            sources: List of source names to match

        Returns:
            Cached CrossSourceResult or None if not found/expired
        """
        key = self._make_key(query, sources)
        entry = self._entries.get(key)

        if entry is None:
            self._misses += 1
            logger.debug("Cache MISS for query: %s", query[:50])
            return None

        # Check if expired
        if entry.expires_at <= time.time():
            del self._entries[key]
            self._misses += 1
            logger.debug("Cache EXPIRED for query: %s", query[:50])
            return None

        self._hits += 1
        logger.debug("Cache HIT for query: %s", query[:50])

        # Mark result as coming from cache
        result = entry.result
        result.from_cache = True
        return result

    def set(
        self,
        query: str,
        sources: list[str],
        result: CrossSourceResult,
    ) -> None:
        """
        Store a result in the cache with per-source TTL.

        Args:
            query: The search query
            sources: List of source names searched
            result: The CrossSourceResult to cache
        """
        # Cleanup and evict if needed
        self._cleanup_expired()
        self._evict_oldest()

        key = self._make_key(query, sources)
        ttl = self._calculate_ttl(sources)
        expires_at = time.time() + ttl

        self._entries[key] = CacheEntry(result=result, expires_at=expires_at)

        logger.debug(
            "Cached result for query: %s (%d items, ttl=%ds)",
            query[:50],
            len(result.items),
            ttl,
        )

    def clear(self) -> None:
        """Clear all cached results."""
        self._entries.clear()
        self._hits = 0
        self._misses = 0
        logger.debug("Cache cleared")

    def stats(self) -> dict[str, int | float]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats including hit ratio
        """
        total_requests = self._hits + self._misses
        hit_ratio = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "current_size": len(self._entries),
            "max_size": self._max_size,
            "default_ttl_seconds": self._default_ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(hit_ratio, 3),
        }

    @property
    def size(self) -> int:
        """Current number of entries in the cache."""
        return len(self._entries)
