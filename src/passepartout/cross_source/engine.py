"""
CrossSourceEngine - Unified search across all data sources.

The main engine that orchestrates cross-source searches,
combining results from multiple adapters with intelligent
scoring and caching.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.passepartout.cross_source.cache import CrossSourceCache
from src.passepartout.cross_source.config import CrossSourceConfig
from src.passepartout.cross_source.models import (
    CrossSourceRequest,
    CrossSourceResult,
    LinkedSource,
    SourceItem,
)

if TYPE_CHECKING:
    from src.passepartout.cross_source.adapters.base import SourceAdapter

logger = logging.getLogger("scapin.cross_source.engine")


class CrossSourceEngine:
    """
    Unified cross-source search engine.

    Orchestrates searches across multiple data sources (email, calendar,
    Teams, WhatsApp, files, web) with parallel execution, result
    aggregation, scoring, and caching.

    Example usage:
    ```python
    engine = CrossSourceEngine(config)
    engine.register_adapter(email_adapter)
    engine.register_adapter(calendar_adapter)

    result = await engine.search("project budget Q1")
    for item in result.items:
        print(f"{item.source}: {item.title} ({item.final_score:.2f})")
    ```
    """

    def __init__(
        self,
        config: CrossSourceConfig | None = None,
    ) -> None:
        """
        Initialize the CrossSourceEngine.

        Args:
            config: Engine configuration (uses defaults if None)
        """
        self._config = config or CrossSourceConfig()
        self._cache = CrossSourceCache(
            ttl_seconds=self._config.cache_ttl_seconds,
            max_size=self._config.cache_max_size,
        )
        self._adapters: dict[str, SourceAdapter] = {}

        logger.info(
            "CrossSourceEngine initialized (cache_ttl=%ds, max_results=%d)",
            self._config.cache_ttl_seconds,
            self._config.max_total_results,
        )

    @property
    def config(self) -> CrossSourceConfig:
        """Get the engine configuration."""
        return self._config

    @property
    def available_sources(self) -> list[str]:
        """Get list of available (registered and working) source names."""
        return [
            name
            for name, adapter in self._adapters.items()
            if adapter.is_available
        ]

    def register_adapter(self, adapter: SourceAdapter) -> None:
        """
        Register a source adapter.

        Args:
            adapter: The adapter to register
        """
        source_name = adapter.source_name
        self._adapters[source_name] = adapter
        logger.debug(
            "Registered adapter: %s (available=%s)",
            source_name,
            adapter.is_available,
        )

    def unregister_adapter(self, source_name: str) -> None:
        """
        Unregister a source adapter.

        Args:
            source_name: Name of the source to unregister
        """
        if source_name in self._adapters:
            del self._adapters[source_name]
            logger.debug("Unregistered adapter: %s", source_name)

    async def search(
        self,
        query: str,
        preferred_sources: list[str] | None = None,
        exclude_sources: list[str] | None = None,
        include_web: bool = False,
        max_results: int | None = None,
        context_note_id: str | None = None,
        linked_sources: list[LinkedSource] | None = None,
    ) -> CrossSourceResult:
        """
        Search across all available sources.

        Args:
            query: The search query string
            preferred_sources: Sources to prioritize (searched first)
            exclude_sources: Sources to exclude from search
            include_web: Whether to include web search
            max_results: Maximum total results (uses config default if None)
            context_note_id: Note ID for linked_sources lookup
            linked_sources: Explicit linked sources for targeted search

        Returns:
            CrossSourceResult with aggregated, scored items
        """
        if not self._config.enabled:
            logger.warning("CrossSourceEngine is disabled")
            return CrossSourceResult(
                query=query,
                sources_searched=[],
                sources_failed=[],
            )

        # Build request
        request = CrossSourceRequest(
            query=query,
            preferred_sources=preferred_sources,
            exclude_sources=exclude_sources,
            include_web=include_web,
            max_results=max_results or self._config.max_total_results,
            context_note_id=context_note_id,
        )

        # Determine sources to search
        sources_to_search = request.get_sources_to_search(self.available_sources)

        # Check cache
        cached_result = self._cache.get(query, sources_to_search)
        if cached_result is not None:
            return cached_result

        # Execute search
        start_time = time.time()
        result = await self._execute_search(
            request,
            sources_to_search,
            linked_sources,
        )
        result.search_duration_ms = int((time.time() - start_time) * 1000)

        # Cache result
        self._cache.set(query, sources_to_search, result)

        logger.info(
            "Cross-source search completed: %d results from %d sources in %dms",
            result.total_results,
            len(result.sources_searched),
            result.search_duration_ms,
        )

        return result

    async def search_with_request(
        self,
        request: CrossSourceRequest,
        linked_sources: list[LinkedSource] | None = None,
    ) -> CrossSourceResult:
        """
        Search using a CrossSourceRequest object.

        Args:
            request: The search request
            linked_sources: Optional linked sources

        Returns:
            CrossSourceResult
        """
        return await self.search(
            query=request.query,
            preferred_sources=request.preferred_sources,
            exclude_sources=request.exclude_sources,
            include_web=request.include_web,
            max_results=request.max_results,
            context_note_id=request.context_note_id,
            linked_sources=linked_sources,
        )

    async def _execute_search(
        self,
        request: CrossSourceRequest,
        sources: list[str],
        linked_sources: list[LinkedSource] | None,
    ) -> CrossSourceResult:
        """
        Execute parallel search across sources.

        Args:
            request: The search request
            sources: List of source names to search
            linked_sources: Optional linked sources for context

        Returns:
            Aggregated CrossSourceResult
        """
        # Build context for adapters
        context = self._build_adapter_context(linked_sources)

        # Create search tasks
        tasks = []
        source_names = []
        for source_name in sources:
            adapter = self._adapters.get(source_name)
            if adapter and adapter.is_available:
                task = self._search_with_timeout(
                    adapter,
                    request.query,
                    context.get(source_name, {}),
                )
                tasks.append(task)
                source_names.append(source_name)

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        all_items: list[SourceItem] = []
        sources_searched: list[str] = []
        sources_failed: list[str] = []

        for source_name, result in zip(source_names, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("Search failed for %s: %s", source_name, result)
                sources_failed.append(source_name)
            elif isinstance(result, list):
                all_items.extend(result)
                sources_searched.append(source_name)
            else:
                sources_failed.append(source_name)

        # Aggregate and score results
        scored_items = self._aggregate_results(all_items)

        return CrossSourceResult(
            query=request.query,
            items=scored_items[: request.max_results],
            sources_searched=sources_searched,
            sources_failed=sources_failed,
            total_results=len(scored_items),
        )

    async def _search_with_timeout(
        self,
        adapter: SourceAdapter,
        query: str,
        context: dict[str, Any],
    ) -> list[SourceItem]:
        """
        Execute adapter search with timeout.

        Args:
            adapter: The source adapter
            query: Search query
            context: Adapter context

        Returns:
            List of SourceItem or raises TimeoutError
        """
        try:
            return await asyncio.wait_for(
                adapter.search(
                    query,
                    max_results=self._config.max_results_per_source,
                    context=context,
                ),
                timeout=self._config.adapter_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Search timeout for %s (%.1fs)",
                adapter.source_name,
                self._config.adapter_timeout_seconds,
            )
            raise

    def _build_adapter_context(
        self,
        linked_sources: list[LinkedSource] | None,
    ) -> dict[str, dict[str, Any]]:
        """
        Build per-adapter context from linked sources.

        Args:
            linked_sources: List of linked sources from note

        Returns:
            Dict mapping source name to context dict
        """
        context: dict[str, dict[str, Any]] = {}

        if not linked_sources:
            return context

        for ls in linked_sources:
            source_type = ls.type.lower()

            # Map linked source types to adapter names
            if source_type == "folder":
                ctx = context.setdefault("files", {})
                ctx.setdefault("paths", []).append(ls.identifier)
            elif source_type == "whatsapp":
                ctx = context.setdefault("whatsapp", {})
                ctx["contact"] = ls.identifier
            elif source_type == "email":
                ctx = context.setdefault("email", {})
                ctx["email_filter"] = ls.identifier
            elif source_type == "teams":
                ctx = context.setdefault("teams", {})
                ctx["chat"] = ls.identifier

        return context

    def _aggregate_results(
        self,
        items: list[SourceItem],
    ) -> list[SourceItem]:
        """
        Aggregate, score, and deduplicate results.

        Args:
            items: Raw items from all sources

        Returns:
            Sorted, deduplicated items with final_score
        """
        # Calculate final scores
        for item in items:
            item.final_score = self._calculate_score(item)

        # Sort by final score (descending)
        items.sort(key=lambda x: x.final_score, reverse=True)

        # Deduplicate (keep highest scored version)
        seen_titles: set[str] = set()
        deduplicated: list[SourceItem] = []

        for item in items:
            # Create dedup key from title and source
            dedup_key = f"{item.title.lower()}:{item.source}"
            if dedup_key not in seen_titles:
                seen_titles.add(dedup_key)
                deduplicated.append(item)

        return deduplicated

    def _calculate_score(self, item: SourceItem) -> float:
        """
        Calculate final score for an item.

        Combines relevance score with source weight and freshness.

        Args:
            item: The source item

        Returns:
            Final score (0.0 - 1.0)
        """
        # Get source weight
        source_weight = self._config.get_source_weight(item.source)

        # Calculate freshness factor
        freshness_factor = self._calculate_freshness(item.timestamp)

        # Combine: relevance * source_weight * freshness
        return item.relevance_score * source_weight * freshness_factor

    def _calculate_freshness(self, timestamp: datetime) -> float:
        """
        Calculate freshness factor for an item.

        Items older than freshness_decay_days get penalized.

        Args:
            timestamp: Item timestamp

        Returns:
            Freshness factor (0.5 - 1.0)
        """
        now = datetime.now(timezone.utc)

        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        days_old = (now - timestamp).days

        # No penalty for recent items
        if days_old <= 0:
            return 1.0

        # Linear decay over freshness_decay_days, bottoming at 0.5
        decay_rate = days_old / self._config.freshness_decay_days
        return max(0.5, 1.0 - decay_rate * 0.5)

    def clear_cache(self) -> None:
        """Clear the search cache."""
        self._cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        return self._cache.stats()
