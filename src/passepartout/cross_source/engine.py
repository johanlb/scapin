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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.passepartout.cross_source.cache import CrossSourceCache
from src.passepartout.cross_source.config import CrossSourceConfig
from src.passepartout.cross_source.models import (
    CrossSourceRequest,
    CrossSourceResult,
    LinkedSource,
    SourceItem,
)


@dataclass
class AdapterHealth:
    """Track health status for a source adapter (circuit breaker pattern)."""

    failures: int = 0
    last_failure: datetime | None = None
    open_until: datetime | None = None  # Circuit is open (failing) until this time
    consecutive_successes: int = 0

    # Circuit breaker thresholds
    failure_threshold: int = 3  # Open circuit after N failures
    recovery_timeout: int = 60  # Seconds before trying again
    success_threshold: int = 2  # Successes needed to fully close circuit

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
        self._adapter_health: dict[str, AdapterHealth] = {}  # Circuit breaker state

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

        # Create search tasks (skip adapters with open circuit)
        tasks = []
        source_names = []
        skipped_sources: list[str] = []

        for source_name in sources:
            adapter = self._adapters.get(source_name)
            if adapter and adapter.is_available:
                # Check circuit breaker
                if self._is_circuit_open(source_name):
                    logger.debug("Skipping %s (circuit open)", source_name)
                    skipped_sources.append(source_name)
                    continue

                task = self._search_with_timeout(
                    adapter,
                    request.query,
                    context.get(source_name, {}),
                )
                tasks.append(task)
                source_names.append(source_name)

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and update circuit breaker state
        all_items: list[SourceItem] = []
        sources_searched: list[str] = []
        sources_failed: list[str] = []

        for source_name, result in zip(source_names, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("Search failed for %s: %s", source_name, result)
                sources_failed.append(source_name)
                self._record_failure(source_name)
            elif isinstance(result, list):
                all_items.extend(result)
                sources_searched.append(source_name)
                self._record_success(source_name)
            else:
                sources_failed.append(source_name)
                self._record_failure(source_name)

        # Add skipped sources to failed list
        sources_failed.extend(skipped_sources)

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

        Uses multi-level deduplication:
        1. URL-based (exact match for web results)
        2. Content hash-based (similar content across sources)
        3. Title normalization (fuzzy title matching)

        When duplicates found across sources, boosts score instead of discarding.

        Args:
            items: Raw items from all sources

        Returns:
            Sorted, deduplicated items with final_score
        """
        if not items:
            return []

        # Step 1: Normalize relevance scores per source
        self._normalize_scores_per_source(items)

        # Step 2: Deduplicate with cross-source merging
        merged_items = self._deduplicate_with_merge(items)

        # Step 3: Calculate final scores
        for item in merged_items:
            item.final_score = self._calculate_score(item)

        # Step 4: Sort by final score (descending)
        merged_items.sort(key=lambda x: x.final_score, reverse=True)

        return merged_items

    def _deduplicate_with_merge(
        self,
        items: list[SourceItem],
    ) -> list[SourceItem]:
        """
        Deduplicate items with cross-source merging.

        When the same content appears in multiple sources, keeps the
        highest-scored version but boosts its relevance score.

        Args:
            items: Raw items from all sources

        Returns:
            Deduplicated items with boosted scores for cross-source matches
        """
        # Track seen items by multiple keys
        seen_urls: dict[str, SourceItem] = {}
        seen_content_hashes: dict[str, SourceItem] = {}
        seen_titles: dict[str, SourceItem] = {}

        for item in items:
            # URL deduplication (for web results)
            if item.url:
                url_key = item.url.lower().rstrip("/")
                if url_key in seen_urls:
                    self._merge_duplicate(seen_urls[url_key], item)
                    continue
                seen_urls[url_key] = item

            # Content hash deduplication
            content_hash = self._compute_content_hash(item)
            if content_hash in seen_content_hashes:
                existing = seen_content_hashes[content_hash]
                # Only merge if from different sources
                if existing.source != item.source:
                    self._merge_duplicate(existing, item)
                    continue
            seen_content_hashes[content_hash] = item

            # Title normalization deduplication (fuzzy)
            title_key = self._normalize_title(item.title)
            if title_key in seen_titles:
                existing = seen_titles[title_key]
                # Only merge if similar content and different sources
                if (
                    existing.source != item.source
                    and self._is_similar_content(existing, item)
                ):
                    self._merge_duplicate(existing, item)
                    continue
            seen_titles[title_key] = item

        # Return unique items (prefer content_hash as primary key)
        return list(seen_content_hashes.values())

    def _compute_content_hash(self, item: SourceItem) -> str:
        """
        Compute a hash for content deduplication.

        Uses normalized content to detect similar items.

        Args:
            item: Source item

        Returns:
            Content hash string
        """
        # Normalize content for hashing
        content = item.content.lower()
        # Remove extra whitespace
        content = " ".join(content.split())
        # Take first 200 chars (enough for uniqueness)
        content = content[:200]

        # Create hash using built-in hash for speed
        return f"{hash(content)}:{item.source}"

    def _normalize_title(self, title: str) -> str:
        """
        Normalize title for fuzzy matching.

        Args:
            title: Raw title

        Returns:
            Normalized title key
        """
        # Lowercase and remove punctuation
        normalized = title.lower()
        # Remove common prefixes like "Re:", "Fwd:", etc.
        prefixes = ["re:", "fwd:", "fw:", "aw:", "sv:"]
        for prefix in prefixes:
            while normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        return normalized

    def _is_similar_content(self, item1: SourceItem, item2: SourceItem) -> bool:
        """
        Check if two items have similar content.

        Uses simple token overlap for speed.

        Args:
            item1: First item
            item2: Second item

        Returns:
            True if content is similar (>50% token overlap)
        """
        # Tokenize content
        tokens1 = set(item1.content.lower().split()[:100])
        tokens2 = set(item2.content.lower().split()[:100])

        if not tokens1 or not tokens2:
            return False

        # Calculate Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union > 0.5

    def _merge_duplicate(
        self,
        existing: SourceItem,
        duplicate: SourceItem,
    ) -> None:
        """
        Merge a duplicate item into an existing one.

        Boosts the relevance score when content appears in multiple sources.

        Args:
            existing: Item to keep and update
            duplicate: Duplicate item (will be discarded)
        """
        # Boost score by 10% for each additional source (max 30% boost)
        boost = 0.1
        max_total_boost = 0.3

        # Track merged sources in metadata
        merged_sources = existing.metadata.get("merged_sources", [existing.source])
        if duplicate.source not in merged_sources:
            merged_sources.append(duplicate.source)
            existing.metadata["merged_sources"] = merged_sources

            # Apply boost (capped at max)
            current_boost = (len(merged_sources) - 1) * boost
            actual_boost = min(current_boost, max_total_boost)
            existing.relevance_score = min(1.0, existing.relevance_score * (1 + actual_boost))

            logger.debug(
                "Merged duplicate: '%s' from %s into %s (boost=%.0f%%)",
                existing.title[:30],
                duplicate.source,
                existing.source,
                actual_boost * 100,
            )

    def _normalize_scores_per_source(
        self,
        items: list[SourceItem],
    ) -> None:
        """
        Normalize relevance scores within each source to 0-1 range.

        This ensures fair comparison when combining results from different
        sources that may have different scoring distributions.

        Args:
            items: Items to normalize (modified in place)
        """
        # Group items by source
        by_source: dict[str, list[SourceItem]] = {}
        for item in items:
            if item.source not in by_source:
                by_source[item.source] = []
            by_source[item.source].append(item)

        # Normalize each source independently
        for source_items in by_source.values():
            if len(source_items) < 2:
                # Single item, no normalization needed
                continue

            # Find min/max scores for this source
            scores = [item.relevance_score for item in source_items]
            min_score = min(scores)
            max_score = max(scores)

            # Skip if all scores are identical (avoid division by zero)
            if max_score == min_score:
                continue

            # Normalize to 0.3-1.0 range (preserve some differentiation)
            # We use 0.3 as floor to avoid very low scores for the worst item
            score_range = max_score - min_score
            for item in source_items:
                normalized = (item.relevance_score - min_score) / score_range
                item.relevance_score = 0.3 + (normalized * 0.7)

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

    # --- Circuit Breaker Methods ---

    def _get_adapter_health(self, source_name: str) -> AdapterHealth:
        """Get or create health tracker for an adapter."""
        if source_name not in self._adapter_health:
            self._adapter_health[source_name] = AdapterHealth()
        return self._adapter_health[source_name]

    def _is_circuit_open(self, source_name: str) -> bool:
        """
        Check if circuit breaker is open (adapter should be skipped).

        Args:
            source_name: Name of the source adapter

        Returns:
            True if circuit is open (skip this adapter)
        """
        health = self._get_adapter_health(source_name)

        if health.open_until is None:
            return False

        now = datetime.now(timezone.utc)
        if now >= health.open_until:
            # Recovery period passed - allow a trial request (half-open state)
            logger.info("Circuit half-open for %s, allowing trial request", source_name)
            return False

        return True

    def _record_failure(self, source_name: str) -> None:
        """Record a failure for an adapter (may open circuit)."""
        health = self._get_adapter_health(source_name)

        health.failures += 1
        health.consecutive_successes = 0
        health.last_failure = datetime.now(timezone.utc)

        # Check if we should open the circuit
        if health.failures >= health.failure_threshold:
            health.open_until = datetime.now(timezone.utc) + timedelta(
                seconds=health.recovery_timeout
            )
            logger.warning(
                "Circuit OPEN for %s (failures=%d, retry in %ds)",
                source_name,
                health.failures,
                health.recovery_timeout,
            )

    def _record_success(self, source_name: str) -> None:
        """Record a success for an adapter (may close circuit)."""
        health = self._get_adapter_health(source_name)

        health.consecutive_successes += 1

        # If in half-open state and enough successes, close the circuit
        if (
            health.open_until is not None
            and health.consecutive_successes >= health.success_threshold
        ):
            logger.info("Circuit CLOSED for %s (recovered)", source_name)
            health.failures = 0
            health.open_until = None
            health.consecutive_successes = 0

    def get_adapter_health_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get health statistics for all adapters.

        Returns:
            Dict mapping source name to health stats
        """
        stats = {}
        for source_name, health in self._adapter_health.items():
            stats[source_name] = {
                "failures": health.failures,
                "last_failure": health.last_failure.isoformat() if health.last_failure else None,
                "circuit_open": self._is_circuit_open(source_name),
                "open_until": health.open_until.isoformat() if health.open_until else None,
            }
        return stats
