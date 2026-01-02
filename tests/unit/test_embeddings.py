"""
Unit Tests for Embedding Generator

Tests semantic embedding generation with caching and batch processing.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.passepartout.embeddings import EmbeddingGenerator, get_embedding_generator


class TestEmbeddingGeneratorInit:
    """Test EmbeddingGenerator initialization"""

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_init_with_defaults(self, mock_st):
        """Test initialization with default parameters"""
        # Mock model
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.cache_size == 10000
        assert embedder.embedding_dimension == 384
        assert len(embedder._cache) == 0
        mock_st.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2", device=None)

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_init_with_custom_model(self, mock_st):
        """Test initialization with custom model"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator(
            model_name="custom-model",
            cache_size=5000,
            device="cpu"
        )

        assert embedder.model_name == "custom-model"
        assert embedder.cache_size == 5000
        assert embedder.embedding_dimension == 768
        mock_st.assert_called_once_with("custom-model", device="cpu")

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_init_model_load_failure(self, mock_st):
        """Test initialization fails gracefully when model cannot load"""
        mock_st.side_effect = Exception("Model not found")

        with pytest.raises(ValueError, match="Cannot load embedding model"):
            EmbeddingGenerator()


class TestEmbedText:
    """Test single text embedding"""

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_text_success(self, mock_st):
        """Test embedding single text"""
        # Setup mock
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = mock_embedding
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()
        result = embedder.embed_text("Hello world")

        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)
        mock_model.encode.assert_called_once()

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_text_empty_raises(self, mock_st):
        """Test embedding empty text raises ValueError"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        with pytest.raises(ValueError, match="Cannot embed empty text"):
            embedder.embed_text("")

        with pytest.raises(ValueError, match="Cannot embed empty text"):
            embedder.embed_text("   ")

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_text_caching(self, mock_st):
        """Test embedding caching works"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = mock_embedding
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        # First call - cache miss
        result1 = embedder.embed_text("Hello world")
        assert embedder._cache_misses == 1
        assert embedder._cache_hits == 0

        # Second call - cache hit
        result2 = embedder.embed_text("Hello world")
        assert embedder._cache_misses == 1
        assert embedder._cache_hits == 1

        # Results should be identical
        np.testing.assert_array_equal(result1, result2)

        # Model.encode should only be called once
        assert mock_model.encode.call_count == 1

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_text_normalization(self, mock_st):
        """Test text normalization before caching"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = mock_embedding
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        # These should all hit the same cache entry
        embedder.embed_text("Hello world")
        embedder.embed_text("  Hello world  ")
        embedder.embed_text("Hello world")

        # Should only generate embedding once
        assert mock_model.encode.call_count == 1
        assert embedder._cache_hits == 2


class TestEmbedBatch:
    """Test batch embedding"""

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_batch_success(self, mock_st):
        """Test batch embedding"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_embeddings = np.random.rand(3, 384).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()
        texts = ["Text 1", "Text 2", "Text 3"]
        result = embedder.embed_batch(texts)

        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 384)
        mock_model.encode.assert_called_once()

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_batch_empty_raises(self, mock_st):
        """Test batch embedding with empty list raises"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        with pytest.raises(ValueError, match="Cannot embed empty text list"):
            embedder.embed_batch([])

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_batch_with_empty_text_raises(self, mock_st):
        """Test batch embedding with empty text in list raises"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        with pytest.raises(ValueError, match="Text at index 1 is empty"):
            embedder.embed_batch(["Text 1", "", "Text 3"])

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_embed_batch_partial_cache(self, mock_st):
        """Test batch embedding uses cache for some texts"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"

        # First return 2 embeddings, then 1 embedding
        mock_model.encode.side_effect = [
            np.random.rand(2, 384).astype(np.float32),
            np.random.rand(1, 384).astype(np.float32),
        ]
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        # First batch - all cache misses
        texts1 = ["Text 1", "Text 2"]
        result1 = embedder.embed_batch(texts1)
        assert result1.shape == (2, 384)
        assert embedder._cache_misses == 2

        # Second batch - one cached, one new
        texts2 = ["Text 1", "Text 3"]
        result2 = embedder.embed_batch(texts2)
        assert result2.shape == (2, 384)
        assert embedder._cache_hits == 1
        assert embedder._cache_misses == 3

        # First embedding should match
        np.testing.assert_array_equal(result1[0], result2[0])


class TestCacheManagement:
    """Test cache management"""

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_cache_eviction(self, mock_st):
        """Test cache eviction when full"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_model.encode.return_value = np.random.rand(384).astype(np.float32)
        mock_st.return_value = mock_model

        # Small cache for testing
        embedder = EmbeddingGenerator(cache_size=2)

        # Fill cache
        embedder.embed_text("Text 1")
        embedder.embed_text("Text 2")
        assert len(embedder._cache) == 2

        # Add third - should evict oldest
        embedder.embed_text("Text 3")
        assert len(embedder._cache) == 2

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_clear_cache(self, mock_st):
        """Test clearing cache"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_model.encode.return_value = np.random.rand(384).astype(np.float32)
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()
        embedder.embed_text("Text 1")
        embedder.embed_text("Text 2")

        assert len(embedder._cache) == 2
        assert embedder._cache_misses == 2

        embedder.clear_cache()

        assert len(embedder._cache) == 0
        assert embedder._cache_hits == 0
        assert embedder._cache_misses == 0

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_cache_stats(self, mock_st):
        """Test cache statistics"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_model.encode.return_value = np.random.rand(384).astype(np.float32)
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator(cache_size=100)

        # Generate some embeddings
        embedder.embed_text("Text 1")
        embedder.embed_text("Text 1")  # Cache hit
        embedder.embed_text("Text 2")

        stats = embedder.get_cache_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["size"] == 2
        assert stats["max_size"] == 100
        assert stats["hit_rate"] == pytest.approx(1/3)


class TestUtilityMethods:
    """Test utility methods"""

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_get_dimension(self, mock_st):
        """Test get_dimension method"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()
        assert embedder.get_dimension() == 384

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_repr(self, mock_st):
        """Test string representation"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()
        repr_str = repr(embedder)

        assert "EmbeddingGenerator" in repr_str
        assert "384" in repr_str
        assert "sentence-transformers/all-MiniLM-L6-v2" in repr_str


class TestGetEmbeddingGenerator:
    """Test factory function"""

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_get_embedding_generator(self, mock_st):
        """Test get_embedding_generator factory"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        embedder = get_embedding_generator()

        assert isinstance(embedder, EmbeddingGenerator)
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.cache_size == 10000


class TestThreadSafety:
    """Test thread safety of cache operations (P0-1 Critical Fix)"""

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_concurrent_cache_access(self, mock_st):
        """Test concurrent read/write to cache doesn't corrupt data"""
        import threading

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        # Return unique embeddings each time
        mock_model.encode.side_effect = lambda *args, **kwargs: np.random.rand(384).astype(np.float32)
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator(cache_size=50)
        errors = []

        def worker(worker_id: int):
            """Worker thread that hammers the cache"""
            try:
                for i in range(30):
                    # Mix of shared and unique keys
                    text = f"Worker {worker_id % 5} text {i % 3}"
                    embedding = embedder.embed_text(text)

                    # Verify integrity
                    assert embedding.shape == (384,)
                    assert not np.any(np.isnan(embedding))
            except Exception as e:
                errors.append((worker_id, e))

        # Launch 10 concurrent workers
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0, f"Thread errors: {errors}"

        # Verify cache integrity
        stats = embedder.get_cache_stats()
        assert stats["size"] <= embedder.cache_size
        assert stats["hits"] + stats["misses"] == 10 * 30  # Total accesses

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_concurrent_batch_operations(self, mock_st):
        """Test concurrent batch operations are thread-safe"""
        import threading

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_model.encode.side_effect = lambda texts, **kwargs: np.random.rand(
            len(texts) if isinstance(texts, list) else 1, 384
        ).astype(np.float32)
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator(cache_size=100)
        errors = []

        def batch_worker(worker_id: int):
            try:
                for i in range(10):
                    texts = [f"Batch {worker_id} item {j}" for j in range(5)]
                    embeddings = embedder.embed_batch(texts)
                    assert embeddings.shape == (5, 384)
            except Exception as e:
                errors.append((worker_id, e))

        threads = [threading.Thread(target=batch_worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert embedder.get_cache_stats()["size"] <= embedder.cache_size

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_race_condition_same_key(self, mock_st):
        """Test race condition when multiple threads access same key"""
        import threading

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        # Always return same embedding for determinism
        fixed_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = fixed_embedding
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()
        errors = []
        barrier = threading.Barrier(10)  # Synchronize threads

        def racer(thread_id: int):
            try:
                # Wait for all threads to be ready
                barrier.wait()

                # All threads hit same key simultaneously
                for i in range(20):
                    text = f"Shared key {i % 3}"
                    embedding = embedder.embed_text(text)
                    assert embedding.shape == (384,)
            except Exception as e:
                errors.append((thread_id, e))

        threads = [threading.Thread(target=racer, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # Cache should have exactly 3 entries (the 3 unique keys)
        assert embedder.get_cache_stats()["size"] == 3

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_lru_eviction_thread_safe(self, mock_st):
        """Test LRU eviction doesn't corrupt cache under concurrent load"""
        import threading

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_model.encode.side_effect = lambda *args, **kwargs: np.random.rand(384).astype(np.float32)
        mock_st.return_value = mock_model

        # Small cache to force evictions
        embedder = EmbeddingGenerator(cache_size=10)
        errors = []

        def evictor_worker(worker_id: int):
            try:
                # Generate many unique keys to force evictions
                for i in range(50):
                    text = f"Worker {worker_id} unique {i}"
                    embedding = embedder.embed_text(text)
                    assert embedding.shape == (384,)
            except Exception as e:
                errors.append((worker_id, e))

        threads = [threading.Thread(target=evictor_worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # Cache should be at capacity
        stats = embedder.get_cache_stats()
        assert stats["size"] == 10
        assert stats["misses"] == 5 * 50  # All cache misses (unique keys)

    @patch('src.passepartout.embeddings.SentenceTransformer')
    def test_stats_increment_thread_safe(self, mock_st):
        """Test hit/miss counters are thread-safe"""
        import threading

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.device = "cpu"
        mock_model.encode.return_value = np.random.rand(384).astype(np.float32)
        mock_st.return_value = mock_model

        embedder = EmbeddingGenerator()

        def counter_worker():
            # First access - miss
            embedder.embed_text("Shared")
            # Second access - hit
            embedder.embed_text("Shared")

        threads = [threading.Thread(target=counter_worker) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = embedder.get_cache_stats()
        # Should have exactly 40 total accesses (20 threads * 2 accesses)
        assert stats["hits"] + stats["misses"] == 40
        # At least 1 miss (first access), rest are hits
        assert stats["misses"] >= 1
        assert stats["hits"] >= 39
