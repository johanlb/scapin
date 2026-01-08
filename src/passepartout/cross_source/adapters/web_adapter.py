"""
Web adapter for CrossSourceEngine.

Provides web search functionality using the Tavily API for intelligent
web searches with AI-powered result ranking.

Tavily is optimized for AI agents and provides structured, relevant results
without the noise of traditional search engines.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

logger = logging.getLogger("scapin.cross_source.web")

TAVILY_API_URL = "https://api.tavily.com/search"


class WebAdapter(BaseAdapter):
    """
    Web search adapter using Tavily API.

    Tavily provides AI-optimized web search results with:
    - Intelligent result ranking
    - Content extraction and summarization
    - Structured response format
    - Domain filtering capabilities

    Requires TAVILY_API_KEY environment variable or explicit key.
    """

    _source_name = "web"

    def __init__(
        self,
        api_key: str | None = None,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False,
        max_tokens: int = 4000,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> None:
        """
        Initialize the Web adapter.

        Args:
            api_key: Tavily API key (default: from TAVILY_API_KEY env var)
            search_depth: "basic" or "advanced" (advanced is slower but better)
            include_answer: Whether to include AI-generated answer
            include_raw_content: Whether to include raw HTML content
            max_tokens: Maximum tokens for content extraction
            include_domains: Only search these domains
            exclude_domains: Exclude these domains from results
        """
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self._search_depth = search_depth
        self._include_answer = include_answer
        self._include_raw_content = include_raw_content
        self._max_tokens = max_tokens
        self._include_domains = include_domains or []
        self._exclude_domains = exclude_domains or []

    @property
    def is_available(self) -> bool:
        """Check if Tavily API is configured."""
        return self._api_key is not None and len(self._api_key) > 0

    async def search(
        self,
        query: str,
        max_results: int = 10,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search the web for relevant content.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context with additional filters
                    - include_domains: list of domains to include
                    - exclude_domains: list of domains to exclude
                    - search_depth: "basic" or "advanced"
                    - topic: "general" or "news"

        Returns:
            List of SourceItem objects representing web search results
        """
        if not self.is_available:
            logger.warning("Web adapter not available (no API key), skipping search")
            return []

        try:
            # Get filter options from context
            include_domains = self._include_domains.copy()
            exclude_domains = self._exclude_domains.copy()
            search_depth = self._search_depth
            topic = "general"

            if context:
                if context.get("include_domains"):
                    include_domains.extend(context["include_domains"])
                if context.get("exclude_domains"):
                    exclude_domains.extend(context["exclude_domains"])
                if context.get("search_depth"):
                    search_depth = context["search_depth"]
                if context.get("topic"):
                    topic = context["topic"]

            # Build request payload
            payload: dict[str, Any] = {
                "api_key": self._api_key,
                "query": query,
                "search_depth": search_depth,
                "include_answer": self._include_answer,
                "include_raw_content": self._include_raw_content,
                "max_results": max_results,
                "topic": topic,
            }

            if include_domains:
                payload["include_domains"] = include_domains
            if exclude_domains:
                payload["exclude_domains"] = exclude_domains

            # Make API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(TAVILY_API_URL, json=payload)
                response.raise_for_status()
                data = response.json()

            # Parse results
            results = self._parse_results(data, query)

            logger.debug(
                "Web search found %d results for '%s'",
                len(results),
                query[:50],
            )

            return results

        except httpx.HTTPStatusError as e:
            logger.error("Tavily API error: %s - %s", e.response.status_code, e.response.text)
            return []
        except httpx.RequestError as e:
            logger.error("Web search request failed: %s", e)
            return []
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return []

    def _parse_results(
        self,
        data: dict[str, Any],
        query: str,
    ) -> list[SourceItem]:
        """
        Parse Tavily API response into SourceItems.

        Args:
            data: Tavily API response
            query: Original search query

        Returns:
            List of SourceItem objects
        """
        results = []

        # Handle AI-generated answer if present
        answer = data.get("answer")
        if answer and self._include_answer:
            results.append(
                SourceItem(
                    source="web",
                    type="answer",
                    title="AI Summary",
                    content=answer,
                    timestamp=datetime.now(timezone.utc),
                    relevance_score=0.95,  # AI answer is highly relevant
                    url=None,
                    metadata={
                        "type": "ai_answer",
                        "query": query,
                    },
                )
            )

        # Parse individual results
        for item in data.get("results", []):
            result = self._result_to_source_item(item, query)
            if result:
                results.append(result)

        return results

    def _result_to_source_item(
        self,
        item: dict[str, Any],
        _query: str,
    ) -> SourceItem | None:
        """
        Convert a Tavily result to SourceItem.

        Args:
            item: Tavily result item
            query: Original search query

        Returns:
            SourceItem or None if invalid
        """
        title = item.get("title", "")
        url = item.get("url", "")
        content = item.get("content", "")

        if not title and not content:
            return None

        # Build content with metadata
        content_parts = []

        # Add URL
        if url:
            content_parts.append(f"URL: {url}")

        # Add published date if available
        published_date = item.get("published_date")
        if published_date:
            content_parts.append(f"Published: {published_date}")

        # Add main content
        if content:
            content_parts.append("")
            content_parts.append(content[:500])

        full_content = "\n".join(content_parts)

        # Parse timestamp
        timestamp = datetime.now(timezone.utc)
        if published_date:
            try:
                # Try common date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
                    try:
                        timestamp = datetime.strptime(published_date, fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Calculate relevance from Tavily score
        score = item.get("score", 0.7)
        relevance = min(max(float(score), 0.0), 0.95)

        return SourceItem(
            source="web",
            type="web_result",
            title=title,
            content=full_content,
            timestamp=timestamp,
            relevance_score=relevance,
            url=url,
            metadata={
                "domain": self._extract_domain(url),
                "published_date": published_date,
                "tavily_score": score,
            },
        )

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain string
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""


class DuckDuckGoAdapter(BaseAdapter):
    """
    Alternative web search adapter using DuckDuckGo.

    This is a fallback adapter when Tavily API is not available.
    Uses the duckduckgo-search library.

    Note: Rate limited and may be less reliable than Tavily.
    """

    _source_name = "web"

    def __init__(self) -> None:
        """Initialize DuckDuckGo adapter."""
        self._duckduckgo_available: bool | None = None

    @property
    def is_available(self) -> bool:
        """Check if duckduckgo-search is installed."""
        if self._duckduckgo_available is None:
            try:
                from duckduckgo_search import DDGS  # noqa: F401
                self._duckduckgo_available = True
            except ImportError:
                self._duckduckgo_available = False
        return self._duckduckgo_available

    async def search(
        self,
        query: str,
        max_results: int = 10,
        _context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum results
            context: Optional context

        Returns:
            List of SourceItem objects
        """
        if not self.is_available:
            logger.warning("DuckDuckGo adapter not available, skipping search")
            return []

        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                # Perform text search
                for item in ddgs.text(query, max_results=max_results):
                    result = SourceItem(
                        source="web",
                        type="web_result",
                        title=item.get("title", ""),
                        content=item.get("body", ""),
                        timestamp=datetime.now(timezone.utc),
                        relevance_score=0.7,  # DuckDuckGo doesn't provide scores
                        url=item.get("href", ""),
                        metadata={
                            "domain": self._extract_domain(item.get("href", "")),
                        },
                    )
                    results.append(result)

            logger.debug(
                "DuckDuckGo search found %d results for '%s'",
                len(results),
                query[:50],
            )

            return results

        except Exception as e:
            logger.error("DuckDuckGo search failed: %s", e)
            return []

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""


def create_web_adapter() -> BaseAdapter:
    """
    Create the best available web adapter.

    Returns WebAdapter (Tavily) if API key is set,
    otherwise DuckDuckGoAdapter if available,
    otherwise a disabled stub adapter.

    Returns:
        WebAdapter, DuckDuckGoAdapter, or stub
    """
    # Try Tavily first
    tavily_adapter = WebAdapter()
    if tavily_adapter.is_available:
        logger.info("Using Tavily web adapter")
        return tavily_adapter

    # Try DuckDuckGo
    ddg_adapter = DuckDuckGoAdapter()
    if ddg_adapter.is_available:
        logger.info("Using DuckDuckGo web adapter (fallback)")
        return ddg_adapter

    # Return disabled adapter
    logger.warning("No web adapter available")
    return WebAdapter()  # Will have is_available=False
