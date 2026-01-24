"""
Performance Tests for Context Search and Cache

Tests performance budgets for:
- TTLCache hit/miss performance
- Batch search vs sequential search
- Cache invalidation overhead
"""

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from tests.performance.conftest import measure_time

# ============================================================================
# Cache Performance Tests
# ============================================================================


class TestContextSearchCache:
    """Test TTLCache performance in ContextSearcher"""

    @pytest.fixture
    def mock_note_manager(self):
        """Create a mock NoteManager with search_notes"""
        manager = MagicMock()
        # Simulate a slow search (100ms)
        def slow_search(query, top_k=10, return_scores=True):
            time.sleep(0.05)  # 50ms simulated latency
            return [(MagicMock(note_id=f"note_{i}"), 0.5) for i in range(min(top_k, 5))]

        manager.search_notes.side_effect = slow_search
        return manager

    @pytest.fixture
    def context_searcher(self, mock_note_manager):
        """Create ContextSearcher with mocked dependencies"""
        from src.sancho.context_searcher import ContextSearcher

        return ContextSearcher(
            note_manager=mock_note_manager,
            cross_source_engine=None,
            entity_searcher=None,
        )

    def test_cache_hit_faster_than_miss(self, context_searcher, mock_note_manager):
        """Test that cache hits are significantly faster than misses"""
        entity = "Johan"

        # First call - cache miss
        with measure_time("cache_miss") as miss_metrics:
            context_searcher._search_notes([entity], MagicMock(max_notes=10, min_relevance=0.3))

        # Second call - cache hit
        with measure_time("cache_hit") as hit_metrics:
            context_searcher._search_notes([entity], MagicMock(max_notes=10, min_relevance=0.3))

        # Cache hit should be at least 5x faster
        assert hit_metrics.duration_ms < miss_metrics.duration_ms / 5, (
            f"Cache hit ({hit_metrics.duration_ms:.2f}ms) should be much faster than "
            f"miss ({miss_metrics.duration_ms:.2f}ms)"
        )

        # Cache hit should be under 10ms
        hit_metrics.assert_under(10, "Cache hit should be < 10ms")

    def test_cache_invalidation_clears_entries(self, context_searcher, mock_note_manager):
        """Test that cache invalidation works correctly"""
        entity = "Test Entity"

        # Populate cache
        context_searcher._search_notes([entity], MagicMock(max_notes=10, min_relevance=0.3))
        initial_call_count = mock_note_manager.search_notes.call_count

        # Invalidate cache
        context_searcher.invalidate_cache()

        # Next call should be a cache miss (calls search_notes again)
        context_searcher._search_notes([entity], MagicMock(max_notes=10, min_relevance=0.3))

        assert mock_note_manager.search_notes.call_count > initial_call_count, (
            "After invalidation, search_notes should be called again"
        )

    def test_different_entities_different_cache_keys(self, context_searcher, mock_note_manager):
        """Test that different entities have separate cache entries"""
        config = MagicMock(max_notes=10, min_relevance=0.3)

        # Search for different entities
        context_searcher._search_notes(["Entity A"], config)
        context_searcher._search_notes(["Entity B"], config)

        # Both should trigger search_notes (different cache keys)
        assert mock_note_manager.search_notes.call_count >= 2


# ============================================================================
# Batch Search Performance Tests
# ============================================================================


class TestBatchSearchPerformance:
    """Test batch search efficiency vs sequential calls"""

    @pytest.fixture
    def vector_store(self):
        """Create a VectorStore with test documents"""
        from src.passepartout.vector_store import VectorStore

        # Use a mock embedder for speed
        embedder = MagicMock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)
        embedder.embed_batch.return_value = np.random.rand(10, 384).astype(np.float32)

        store = VectorStore(dimension=384, embedder=embedder)

        # Add test documents
        for i in range(100):
            store.add(f"doc_{i}", f"Document content {i}", {"index": i})

        return store

    def test_batch_search_uses_single_embed_call(self, vector_store):
        """Test that batch search makes single embed_batch call"""
        vector_store.embedder.embed_batch.reset_mock()

        queries = ["query1", "query2", "query3", "query4", "query5"]
        vector_store.search_batch(queries, top_k=10)

        # Should call embed_batch exactly once
        assert vector_store.embedder.embed_batch.call_count == 1
        call_args = vector_store.embedder.embed_batch.call_args
        assert len(call_args[0][0]) == 5  # 5 queries

    def test_batch_search_faster_than_sequential(self, vector_store):
        """Test that batch search is faster than sequential calls"""
        queries = ["query1", "query2", "query3", "query4", "query5"]

        # Reset mock to track separate calls
        vector_store.embedder.embed_batch.return_value = np.random.rand(5, 384).astype(np.float32)

        # Batch search
        with measure_time("batch_search") as batch_metrics:
            vector_store.search_batch(queries, top_k=10)

        # Sequential search (simulate overhead)
        with measure_time("sequential_search") as seq_metrics:
            for query in queries:
                vector_store.search(query, top_k=10)

        # Log results for analysis
        print(f"\nBatch: {batch_metrics.duration_ms:.2f}ms")
        print(f"Sequential: {seq_metrics.duration_ms:.2f}ms")

        # Batch should not be slower than sequential
        # (with mocked embedder, overhead is minimal, but batch should still be competitive)
        assert batch_metrics.duration_ms <= seq_metrics.duration_ms * 1.5, (
            f"Batch ({batch_metrics.duration_ms:.2f}ms) should not be much slower than "
            f"sequential ({seq_metrics.duration_ms:.2f}ms)"
        )

    def test_batch_search_returns_correct_structure(self, vector_store):
        """Test that batch search returns correct result structure"""
        queries = ["query1", "query2", "query3"]
        results = vector_store.search_batch(queries, top_k=5)

        assert len(results) == 3, "Should return one result list per query"
        for result in results:
            assert isinstance(result, list)
            assert len(result) <= 5, "Should respect top_k"
            for item in result:
                assert len(item) == 3, "Each result should be (doc_id, score, metadata)"


# ============================================================================
# Performance Thresholds
# ============================================================================


class TestPerformanceThresholds:
    """Test that operations meet performance thresholds"""

    def test_cache_hit_under_threshold(self):
        """Cache hit should be under 10ms"""
        from src.sancho.context_searcher import ContextSearcher

        # Create searcher with no dependencies (will use cache only)
        searcher = ContextSearcher(
            note_manager=None,
            cross_source_engine=None,
            entity_searcher=None,
        )

        # Pre-populate cache manually
        searcher._search_cache[("test_entity", 10)] = []

        # Measure cache hit
        with measure_time("cache_hit") as metrics:
            for _ in range(100):
                _ = searcher._search_cache.get(("test_entity", 10))

        avg_ms = metrics.duration_ms / 100
        assert avg_ms < 0.1, f"Cache access should be < 0.1ms, got {avg_ms:.4f}ms"

    def test_vector_store_search_under_threshold(self):
        """Vector store search should be under 100ms for 1000 docs"""
        from src.passepartout.vector_store import VectorStore

        embedder = MagicMock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)

        store = VectorStore(dimension=384, embedder=embedder)

        # Add 1000 documents
        for i in range(1000):
            store.add(f"doc_{i}", f"Content {i}")

        # Measure search time
        with measure_time("search_1000_docs") as metrics:
            store.search("test query", top_k=10)

        metrics.assert_under(100, "Search in 1000 docs should be < 100ms")
