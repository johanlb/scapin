"""
Tests for VectorStore (FAISS-based semantic search)

Coverage:
- Initialization and configuration
- Add/remove documents  
- Semantic search with filtering
- Batch operations
- Persistence (save/load)
- Error handling
- Thread safety
"""

from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

from src.passepartout.vector_store import VectorStore


class TestVectorStoreInit:
    """Test VectorStore initialization"""

    def test_init_with_defaults(self):
        """Test default initialization"""
        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)

        store = VectorStore(dimension=384, embedder=embedder)

        assert store.dimension == 384
        assert store.metric == "L2"
        stats = store.get_stats()
        assert stats["total_docs"] == 0
        assert stats["active_docs"] == 0

    def test_init_with_cosine_metric(self):
        """Test initialization with cosine similarity"""
        embedder = Mock()
        embedder.model_name = "mock-model"
        store = VectorStore(dimension=384, embedder=embedder, metric="cosine")

        assert store.metric == "cosine"

    def test_init_invalid_dimension(self):
        """Test error on invalid dimension"""
        embedder = Mock()
        embedder.model_name = "mock-model"

        with pytest.raises(ValueError, match="Dimension must be positive"):
            VectorStore(dimension=0, embedder=embedder)

        with pytest.raises(ValueError, match="Dimension must be positive"):
            VectorStore(dimension=-10, embedder=embedder)

    def test_init_invalid_metric(self):
        """Test error on unsupported metric"""
        embedder = Mock()
        embedder.model_name = "mock-model"

        with pytest.raises(ValueError, match="Unsupported metric"):
            VectorStore(dimension=384, embedder=embedder, metric="manhattan")


class TestAddDocument:
    """Test adding documents"""

    @pytest.fixture
    def store(self):
        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)
        return VectorStore(dimension=384, embedder=embedder)

    def test_add_single_document(self, store):
        """Test adding single document"""
        index_id = store.add(
            doc_id="doc1",
            text="Test document",
            metadata={"type": "test"}
        )

        assert index_id == 0
        stats = store.get_stats()
        assert stats["total_docs"] == 1
        assert stats["active_docs"] == 1

    def test_add_duplicate_doc_id_raises(self, store):
        """Test error on duplicate doc_id"""
        store.add("doc1", "Text 1")

        with pytest.raises(ValueError, match="already exists"):
            store.add("doc1", "Text 2")

    def test_add_empty_text_raises(self, store):
        """Test error on empty text"""
        with pytest.raises(ValueError, match="Cannot add document with empty text"):
            store.add("doc1", "")

        with pytest.raises(ValueError, match="Cannot add document with empty text"):
            store.add("doc1", "   ")

    def test_add_batch_documents(self, store):
        """Test batch adding documents"""
        store.embedder.embed_batch.return_value = np.random.rand(3, 384).astype(np.float32)

        docs = [
            ("doc1", "Text 1", {"cat": "A"}),
            ("doc2", "Text 2", {"cat": "B"}),
            ("doc3", "Text 3", {"cat": "A"})
        ]

        index_ids = store.add_batch(docs)

        assert len(index_ids) == 3
        assert index_ids == [0, 1, 2]
        assert store.get_stats()["total_docs"] == 3


class TestSearch:
    """Test semantic search"""

    @pytest.fixture
    def populated_store(self):
        embedder = Mock()
        embedder.model_name = "mock-model"
        # Return different embeddings for different texts
        def mock_embed(text, **kwargs):
            # Simple hash-based embedding for reproducibility
            np.random.seed(hash(text) % 2**32)
            return np.random.rand(384).astype(np.float32)

        embedder.embed_text.side_effect = mock_embed
        embedder.embed_batch.side_effect = lambda texts, **kwargs: np.array([
            mock_embed(t) for t in texts
        ])

        store = VectorStore(dimension=384, embedder=embedder)

        # Add test documents
        store.add("doc1", "Python programming language")
        store.add("doc2", "JavaScript web development")
        store.add("doc3", "Machine learning with Python")

        return store

    def test_search_basic(self, populated_store):
        """Test basic search"""
        results = populated_store.search("Python", top_k=2)

        assert len(results) <= 2
        assert all(len(r) == 3 for r in results)  # (doc_id, score, metadata)
        assert all(isinstance(r[0], str) for r in results)  # doc_id
        assert all(isinstance(r[1], float) for r in results)  # score

    def test_search_with_filter(self, populated_store):
        """Test search with metadata filter"""
        # Add metadata
        populated_store.add("doc4", "Python tutorial", {"category": "tutorial"})
        populated_store.add("doc5", "Python guide", {"category": "guide"})

        def tutorial_filter(metadata):
            return metadata.get("category") == "tutorial"

        results = populated_store.search("Python", top_k=10, filter_fn=tutorial_filter)

        # Should only return documents with category=tutorial
        for doc_id, score, metadata in results:
            if "category" in metadata:
                assert metadata["category"] == "tutorial"

    def test_search_empty_store(self):
        """Test search on empty store returns empty list"""
        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)
        store = VectorStore(dimension=384, embedder=embedder)

        results = store.search("query", top_k=5)
        assert results == []

    def test_search_empty_query_raises(self, populated_store):
        """Test error on empty query"""
        with pytest.raises(ValueError, match="Cannot search with empty query"):
            populated_store.search("")

    def test_search_invalid_top_k_raises(self, populated_store):
        """Test error on invalid top_k"""
        with pytest.raises(ValueError, match="top_k must be positive"):
            populated_store.search("query", top_k=0)


class TestRemoveAndRebuild:
    """Test document removal and index rebuilding"""

    @pytest.fixture
    def store(self):
        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)
        embedder.model_name = "mock-model"
        s = VectorStore(dimension=384, embedder=embedder)
        s.add("doc1", "Text 1")
        s.add("doc2", "Text 2")
        return s

    def test_remove_document(self, store):
        """Test removing document"""
        success = store.remove("doc1")
        assert success is True

        # Document no longer accessible via get_document
        doc = store.get_document("doc1")
        assert doc is None

        # But internally tracked as deleted (for stats and rebuild)
        stats = store.get_stats()
        assert stats["deleted_docs"] == 1
        assert stats["active_docs"] == 1  # doc2 still active

    def test_remove_nonexistent_returns_false(self, store):
        """Test removing nonexistent document returns False"""
        success = store.remove("nonexistent")
        assert success is False

    def test_rebuild_removes_deleted(self, store):
        """Test rebuild removes deleted documents"""
        # Setup embed_batch mock for rebuild
        store.embedder.embed_batch.return_value = np.random.rand(1, 384).astype(np.float32)

        store.remove("doc1")

        stats_before = store.get_stats()
        assert stats_before["deleted_docs"] == 1

        store.rebuild()

        stats_after = store.get_stats()
        assert stats_after["deleted_docs"] == 0
        assert stats_after["active_docs"] == 1


class TestPersistence:
    """Test save/load functionality"""

    def test_save_and_load(self, tmp_path):
        """Test saving and loading vector store"""
        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)

        # Create and populate store
        store1 = VectorStore(dimension=384, embedder=embedder)
        store1.add("doc1", "Test document 1", {"meta": "data1"})
        store1.add("doc2", "Test document 2", {"meta": "data2"})

        # Save
        save_path = tmp_path / "vector_store"
        store1.save(save_path)

        # Load into new store
        store2 = VectorStore(dimension=384, embedder=embedder)
        store2.load(save_path)

        # Verify data restored
        stats = store2.get_stats()
        assert stats["total_docs"] == 2

        doc1 = store2.get_document("doc1")
        assert doc1 is not None
        assert doc1["text"] == "Test document 1"
        assert doc1["metadata"]["meta"] == "data1"

    def test_load_nonexistent_raises(self):
        """Test loading from nonexistent path raises error"""
        embedder = Mock()
        embedder.model_name = "mock-model"
        store = VectorStore(dimension=384, embedder=embedder)

        with pytest.raises(FileNotFoundError):
            store.load(Path("/nonexistent/path"))


class TestGetDocument:
    """Test document retrieval"""

    @pytest.fixture
    def store(self):
        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)
        s = VectorStore(dimension=384, embedder=embedder)
        s.add("doc1", "Test text", {"key": "value"})
        return s

    def test_get_document_success(self, store):
        """Test getting document by ID"""
        doc = store.get_document("doc1")

        assert doc is not None
        assert doc["doc_id"] == "doc1"
        assert doc["text"] == "Test text"
        assert doc["metadata"]["key"] == "value"

    def test_get_document_nonexistent_returns_none(self, store):
        """Test getting nonexistent document returns None"""
        doc = store.get_document("nonexistent")
        assert doc is None


class TestStats:
    """Test statistics"""

    def test_stats_empty_store(self):
        """Test stats on empty store"""
        embedder = Mock()
        embedder.model_name = "mock-model"
        store = VectorStore(dimension=384, embedder=embedder)

        stats = store.get_stats()
        assert stats["total_docs"] == 0
        assert stats["active_docs"] == 0
        assert stats["deleted_docs"] == 0
        assert stats["dimension"] == 384

    def test_stats_with_documents(self):
        """Test stats with documents"""
        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)
        store = VectorStore(dimension=384, embedder=embedder)

        store.add("doc1", "Text 1")
        store.add("doc2", "Text 2")
        store.remove("doc1")

        stats = store.get_stats()
        assert stats["total_docs"] == 2
        assert stats["active_docs"] == 1
        assert stats["deleted_docs"] == 1


class TestThreadSafety:
    """Test thread safety (basic - FAISS operations are mostly read-only after setup)"""

    def test_concurrent_search(self):
        """Test concurrent search operations"""
        import threading

        embedder = Mock()
        embedder.model_name = "mock-model"
        embedder.embed_text.return_value = np.random.rand(384).astype(np.float32)
        store = VectorStore(dimension=384, embedder=embedder)

        # Populate store
        for i in range(10):
            store.add(f"doc{i}", f"Text {i}")

        errors = []

        def searcher():
            try:
                results = store.search("Text", top_k=5)
                assert len(results) <= 5
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=searcher) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
