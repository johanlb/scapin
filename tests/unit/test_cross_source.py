"""
Unit tests for CrossSourceEngine.

Tests the core cross-source search functionality including
models, cache, configuration, and engine orchestration.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.passepartout.cross_source.cache import CrossSourceCache
from src.passepartout.cross_source.config import (
    CrossSourceConfig,
    EmailAdapterConfig,
    FilesAdapterConfig,
)
from src.passepartout.cross_source.engine import CrossSourceEngine
from src.passepartout.cross_source.models import (
    CrossSourceRequest,
    CrossSourceResult,
    LinkedSource,
    SourceItem,
    parse_linked_sources,
)


# =============================================================================
# Model Tests
# =============================================================================


class TestSourceItem:
    """Tests for SourceItem model."""

    def test_create_basic(self):
        """Test basic SourceItem creation."""
        item = SourceItem(
            source="email",
            type="message",
            title="Test Email",
            content="This is the content",
            timestamp=datetime.now(timezone.utc),
            relevance_score=0.9,
        )

        assert item.source == "email"
        assert item.type == "message"
        assert item.title == "Test Email"
        assert item.relevance_score == 0.9
        assert item.final_score == 0.0  # Not yet calculated

    def test_content_truncation(self):
        """Test that content is truncated to 500 chars."""
        long_content = "x" * 600
        item = SourceItem(
            source="email",
            type="message",
            title="Test",
            content=long_content,
            timestamp=datetime.now(timezone.utc),
            relevance_score=0.5,
        )

        assert len(item.content) == 500
        assert item.content.endswith("...")

    def test_relevance_score_clamped(self):
        """Test that relevance_score is clamped to 0-1."""
        item1 = SourceItem(
            source="email",
            type="message",
            title="Test",
            content="Test",
            timestamp=datetime.now(timezone.utc),
            relevance_score=1.5,  # Over max
        )
        assert item1.relevance_score == 1.0

        item2 = SourceItem(
            source="email",
            type="message",
            title="Test",
            content="Test",
            timestamp=datetime.now(timezone.utc),
            relevance_score=-0.5,  # Under min
        )
        assert item2.relevance_score == 0.0


class TestCrossSourceResult:
    """Tests for CrossSourceResult model."""

    def test_create_with_items(self):
        """Test result creation with items."""
        items = [
            SourceItem(
                source="email",
                type="message",
                title="Email 1",
                content="Content",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.9,
            ),
            SourceItem(
                source="calendar",
                type="event",
                title="Meeting",
                content="Content",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.8,
            ),
        ]

        result = CrossSourceResult(
            query="test query",
            items=items,
            sources_searched=["email", "calendar"],
        )

        assert result.query == "test query"
        assert len(result.items) == 2
        assert result.total_results == 2
        assert "email" in result.sources_searched

    def test_total_results_computed(self):
        """Test that total_results is computed from items."""
        items = [
            SourceItem(
                source="email",
                type="message",
                title="Test",
                content="Content",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.5,
            )
        ]

        result = CrossSourceResult(query="test", items=items)
        assert result.total_results == 1


class TestLinkedSource:
    """Tests for LinkedSource model."""

    def test_create_from_frontmatter(self):
        """Test creation from frontmatter dict."""
        frontmatter_item = {
            "type": "folder",
            "path": "~/Documents/Projects/Alpha",
            "priority": 1,
        }

        ls = LinkedSource.from_frontmatter(frontmatter_item)

        assert ls.type == "folder"
        assert ls.identifier == "~/Documents/Projects/Alpha"
        assert ls.priority == 1

    def test_parse_linked_sources(self):
        """Test parsing multiple linked sources from frontmatter."""
        frontmatter = {
            "title": "Project Alpha",
            "linked_sources": [
                {"type": "folder", "path": "~/Documents/Alpha"},
                {"type": "whatsapp", "contact": "Team Alpha"},
                {"type": "email", "filter": "from:@alpha.com"},
            ],
        }

        sources = parse_linked_sources(frontmatter)

        assert len(sources) == 3
        assert sources[0].type == "folder"
        assert sources[1].type == "whatsapp"
        assert sources[2].type == "email"

    def test_parse_linked_sources_empty(self):
        """Test parsing empty frontmatter."""
        sources = parse_linked_sources({})
        assert sources == []

    def test_parse_linked_sources_sorted_by_priority(self):
        """Test that sources are sorted by priority."""
        frontmatter = {
            "linked_sources": [
                {"type": "folder", "path": "path1", "priority": 3},
                {"type": "whatsapp", "contact": "x", "priority": 1},
                {"type": "email", "filter": "x", "priority": 2},
            ],
        }

        sources = parse_linked_sources(frontmatter)

        assert sources[0].priority == 1
        assert sources[1].priority == 2
        assert sources[2].priority == 3


class TestCrossSourceRequest:
    """Tests for CrossSourceRequest model."""

    def test_get_sources_to_search_default(self):
        """Test default source filtering."""
        request = CrossSourceRequest(query="test")
        available = ["email", "calendar", "teams", "web"]

        sources = request.get_sources_to_search(available)

        # Web should be excluded by default
        assert "web" not in sources
        assert "email" in sources

    def test_get_sources_to_search_with_web(self):
        """Test including web search."""
        request = CrossSourceRequest(query="test", include_web=True)
        available = ["email", "web"]

        sources = request.get_sources_to_search(available)

        assert "web" in sources

    def test_get_sources_to_search_with_exclusions(self):
        """Test excluding specific sources."""
        request = CrossSourceRequest(
            query="test",
            exclude_sources=["teams"],
        )
        available = ["email", "teams", "calendar"]

        sources = request.get_sources_to_search(available)

        assert "teams" not in sources
        assert "email" in sources
        assert "calendar" in sources

    def test_get_sources_to_search_with_preferred(self):
        """Test preferring specific sources."""
        request = CrossSourceRequest(
            query="test",
            preferred_sources=["calendar"],
        )
        available = ["email", "calendar", "teams"]

        sources = request.get_sources_to_search(available)

        # Calendar should be first
        assert sources[0] == "calendar"


# =============================================================================
# Cache Tests
# =============================================================================


class TestCrossSourceCache:
    """Tests for CrossSourceCache."""

    def test_set_and_get(self):
        """Test basic cache set and get."""
        cache = CrossSourceCache(ttl_seconds=60)

        result = CrossSourceResult(
            query="test",
            items=[],
            sources_searched=["email"],
        )

        cache.set("test", ["email"], result)
        cached = cache.get("test", ["email"])

        assert cached is not None
        assert cached.query == "test"
        assert cached.from_cache is True

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = CrossSourceCache()
        cached = cache.get("nonexistent", ["email"])
        assert cached is None

    def test_cache_key_normalization(self):
        """Test that cache keys are normalized."""
        cache = CrossSourceCache()

        result = CrossSourceResult(query="test", items=[])
        cache.set("  TEST  ", ["email", "calendar"], result)

        # Should match with different case and whitespace
        cached = cache.get("test", ["calendar", "email"])  # Different order
        assert cached is not None

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = CrossSourceCache(ttl_seconds=60, max_size=100)
        stats = cache.stats()

        assert stats["default_ttl_seconds"] == 60
        assert stats["max_size"] == 100
        assert stats["current_size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = CrossSourceCache()
        cache.set("test", ["email"], CrossSourceResult(query="test", items=[]))

        assert cache.size == 1
        cache.clear()
        assert cache.size == 0


# =============================================================================
# Config Tests
# =============================================================================


class TestCrossSourceConfig:
    """Tests for CrossSourceConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CrossSourceConfig()

        assert config.enabled is True
        assert config.cache_ttl_seconds == 900  # 15 minutes
        assert config.max_total_results == 50
        assert config.auto_trigger_confidence_threshold == 0.75

    def test_get_enabled_sources(self):
        """Test getting enabled sources."""
        config = CrossSourceConfig()
        config.teams.enabled = False

        sources = config.get_enabled_sources()

        assert "email" in sources
        assert "teams" not in sources

    def test_get_source_weight(self):
        """Test getting source weights."""
        config = CrossSourceConfig()

        assert config.get_source_weight("email") == 1.0
        assert config.get_source_weight("web") == 0.6
        assert config.get_source_weight("unknown") == 0.5  # Default

    def test_adapter_configs(self):
        """Test per-adapter configurations."""
        config = CrossSourceConfig()

        assert isinstance(config.email, EmailAdapterConfig)
        assert config.email.search_body is True

        assert isinstance(config.files, FilesAdapterConfig)
        assert ".md" in config.files.extensions_tier1


# =============================================================================
# Engine Tests
# =============================================================================


class TestCrossSourceEngine:
    """Tests for CrossSourceEngine."""

    def test_init_default(self):
        """Test engine initialization with defaults."""
        engine = CrossSourceEngine()

        assert engine.config.enabled is True
        assert len(engine.available_sources) == 0  # No adapters registered

    def test_register_adapter(self):
        """Test adapter registration."""
        engine = CrossSourceEngine()

        # Create mock adapter
        adapter = MagicMock()
        adapter.source_name = "test_source"
        adapter.is_available = True

        engine.register_adapter(adapter)

        assert "test_source" in engine.available_sources

    def test_unregister_adapter(self):
        """Test adapter unregistration."""
        engine = CrossSourceEngine()

        adapter = MagicMock()
        adapter.source_name = "test_source"
        adapter.is_available = True

        engine.register_adapter(adapter)
        engine.unregister_adapter("test_source")

        assert "test_source" not in engine.available_sources

    @pytest.mark.asyncio
    async def test_search_disabled(self):
        """Test search when engine is disabled."""
        config = CrossSourceConfig(enabled=False)
        engine = CrossSourceEngine(config)

        result = await engine.search("test query")

        assert result.total_results == 0
        assert len(result.sources_searched) == 0

    @pytest.mark.asyncio
    async def test_search_cache_hit(self):
        """Test that cached results are returned."""
        engine = CrossSourceEngine()

        # Create mock adapter
        adapter = AsyncMock()
        adapter.source_name = "email"
        adapter.is_available = True
        adapter.search.return_value = [
            SourceItem(
                source="email",
                type="message",
                title="Test Email",
                content="Content",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.9,
            )
        ]

        engine.register_adapter(adapter)

        # First search - should call adapter
        result1 = await engine.search("test query")
        assert adapter.search.call_count == 1
        assert result1.from_cache is False

        # Second search - should use cache
        result2 = await engine.search("test query")
        assert adapter.search.call_count == 1  # Not called again
        assert result2.from_cache is True

    @pytest.mark.asyncio
    async def test_search_parallel_execution(self):
        """Test that multiple adapters are searched in parallel."""
        engine = CrossSourceEngine()

        # Create two mock adapters
        adapter1 = AsyncMock()
        adapter1.source_name = "email"
        adapter1.is_available = True
        adapter1.search.return_value = [
            SourceItem(
                source="email",
                type="message",
                title="Email",
                content="Content",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.9,
            )
        ]

        adapter2 = AsyncMock()
        adapter2.source_name = "calendar"
        adapter2.is_available = True
        adapter2.search.return_value = [
            SourceItem(
                source="calendar",
                type="event",
                title="Meeting",
                content="Content",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.8,
            )
        ]

        engine.register_adapter(adapter1)
        engine.register_adapter(adapter2)

        result = await engine.search("test query")

        assert adapter1.search.called
        assert adapter2.search.called
        assert result.total_results == 2
        assert "email" in result.sources_searched
        assert "calendar" in result.sources_searched

    @pytest.mark.asyncio
    async def test_search_handles_adapter_failure(self):
        """Test that engine handles adapter failures gracefully."""
        engine = CrossSourceEngine()

        # Adapter that fails
        failing_adapter = AsyncMock()
        failing_adapter.source_name = "failing"
        failing_adapter.is_available = True
        failing_adapter.search.side_effect = Exception("Search failed")

        # Adapter that works
        working_adapter = AsyncMock()
        working_adapter.source_name = "working"
        working_adapter.is_available = True
        working_adapter.search.return_value = [
            SourceItem(
                source="working",
                type="message",
                title="Result",
                content="Content",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.9,
            )
        ]

        engine.register_adapter(failing_adapter)
        engine.register_adapter(working_adapter)

        result = await engine.search("test")

        assert "failing" in result.sources_failed
        assert "working" in result.sources_searched
        assert result.total_results == 1

    @pytest.mark.asyncio
    async def test_search_result_scoring(self):
        """Test that results are scored and sorted."""
        engine = CrossSourceEngine()

        adapter = AsyncMock()
        adapter.source_name = "email"
        adapter.is_available = True
        adapter.search.return_value = [
            SourceItem(
                source="email",
                type="message",
                title="Old Email",
                content="This is old content from a while back about the project",
                timestamp=datetime.now(timezone.utc) - timedelta(days=60),
                relevance_score=0.8,  # Same base relevance
            ),
            SourceItem(
                source="email",
                type="message",
                title="New Email",
                content="This is new content that just arrived with updates",
                timestamp=datetime.now(timezone.utc),
                relevance_score=0.8,  # Same base relevance
            ),
        ]

        engine.register_adapter(adapter)
        result = await engine.search("test")

        # New email should be first due to freshness (equal relevance, newer wins)
        assert result.items[0].title == "New Email"
        assert result.items[0].final_score > 0
        # Old email should have lower score due to freshness decay
        assert result.items[1].title == "Old Email"
        assert result.items[0].final_score > result.items[1].final_score

    @pytest.mark.asyncio
    async def test_search_with_linked_sources(self):
        """Test search with linked sources context."""
        engine = CrossSourceEngine()

        adapter = AsyncMock()
        adapter.source_name = "files"
        adapter.is_available = True
        adapter.search.return_value = []

        engine.register_adapter(adapter)

        linked_sources = [
            LinkedSource(type="folder", identifier="~/Documents/Projects"),
        ]

        await engine.search("test", linked_sources=linked_sources)

        # Check that context was passed to adapter
        call_args = adapter.search.call_args
        context = call_args.kwargs.get("context", {})
        assert "paths" in context

    def test_freshness_calculation(self):
        """Test freshness factor calculation."""
        engine = CrossSourceEngine()

        # Recent item - full freshness
        recent = datetime.now(timezone.utc)
        assert engine._calculate_freshness(recent) == 1.0

        # Old item - reduced freshness
        old = datetime.now(timezone.utc) - timedelta(days=60)
        freshness = engine._calculate_freshness(old)
        assert 0.5 <= freshness < 1.0

    def test_clear_cache(self):
        """Test cache clearing via engine."""
        engine = CrossSourceEngine()
        engine.clear_cache()

        stats = engine.get_cache_stats()
        assert stats["current_size"] == 0


# =============================================================================
# Integration-like Tests
# =============================================================================


class TestCrossSourceIntegration:
    """Higher-level integration-like tests."""

    @pytest.mark.asyncio
    async def test_full_search_flow(self):
        """Test complete search flow from request to result."""
        # Setup
        config = CrossSourceConfig(
            cache_ttl_seconds=60,
            max_total_results=10,
        )
        engine = CrossSourceEngine(config)

        # Create mock adapters
        email_adapter = AsyncMock()
        email_adapter.source_name = "email"
        email_adapter.is_available = True
        email_adapter.search.return_value = [
            SourceItem(
                source="email",
                type="message",
                title="Budget Q1 Report",
                content="Here is the Q1 budget report...",
                timestamp=datetime.now(timezone.utc) - timedelta(days=5),
                relevance_score=0.95,
            ),
            SourceItem(
                source="email",
                type="message",
                title="Re: Budget Discussion",
                content="Thanks for the budget update...",
                timestamp=datetime.now(timezone.utc) - timedelta(days=10),
                relevance_score=0.85,
            ),
        ]

        calendar_adapter = AsyncMock()
        calendar_adapter.source_name = "calendar"
        calendar_adapter.is_available = True
        calendar_adapter.search.return_value = [
            SourceItem(
                source="calendar",
                type="event",
                title="Budget Review Meeting",
                content="Quarterly budget review with finance team",
                timestamp=datetime.now(timezone.utc) + timedelta(days=2),
                relevance_score=0.90,
            ),
        ]

        engine.register_adapter(email_adapter)
        engine.register_adapter(calendar_adapter)

        # Execute search
        result = await engine.search(
            "budget Q1",
            preferred_sources=["email"],
        )

        # Verify
        assert result.total_results == 3
        assert len(result.sources_searched) == 2
        assert len(result.sources_failed) == 0
        assert result.search_duration_ms >= 0  # Can be 0 for fast mocked tests

        # All items should have final scores
        for item in result.items:
            assert item.final_score > 0
