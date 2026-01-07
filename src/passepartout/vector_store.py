"""
Vector Store for Semantic Search

FAISS-based vector store for efficient similarity search over embeddings.
Supports adding documents, searching, persistence, and filtering.
"""

import hashlib
import hmac
import json
import threading
from pathlib import Path
from typing import Any, Callable, Optional

import faiss
import numpy as np

from src.monitoring.logger import get_logger
from src.passepartout.embeddings import EmbeddingGenerator

logger = get_logger("passepartout.vector_store")


class VectorStore:
    """
    FAISS-based vector store for semantic search

    Features:
    - Efficient similarity search using FAISS L2 index
    - Document metadata storage
    - Persistence (save/load)
    - Optional filtering on search results
    - Thread-safe operations

    Usage:
        store = VectorStore(dimension=384)
        store.add("doc1", "This is a document", {"type": "email"})
        results = store.search("find documents", top_k=5)
    """

    def __init__(
        self,
        dimension: int = 384,
        embedder: Optional[EmbeddingGenerator] = None,
        metric: str = "L2"
    ):
        """
        Initialize vector store

        Args:
            dimension: Embedding vector dimension
            embedder: EmbeddingGenerator instance (creates new if None)
            metric: Distance metric ("L2" or "cosine")

        Raises:
            ValueError: If dimension invalid or metric unsupported
        """
        if dimension <= 0:
            raise ValueError(f"Dimension must be positive, got {dimension}")

        if metric not in ["L2", "cosine"]:
            raise ValueError(f"Unsupported metric: {metric}. Use 'L2' or 'cosine'")

        self.dimension = dimension
        self.metric = metric

        # Initialize FAISS index
        if metric == "L2":
            self.index = faiss.IndexFlatL2(dimension)
        else:  # cosine
            # For cosine similarity, use inner product with normalized vectors
            self.index = faiss.IndexFlatIP(dimension)

        # Metadata storage: index_id → document info
        self.id_to_doc: dict[int, dict[str, Any]] = {}

        # Document ID mapping: doc_id → index_id
        self.doc_id_to_index_id: dict[str, int] = {}

        # Counter for index IDs
        self._next_index_id = 0

        # Embedder
        self.embedder = embedder if embedder is not None else EmbeddingGenerator()

        # Thread-safety lock (reentrant for nested calls)
        self._store_lock = threading.RLock()

        logger.info(
            "Initialized VectorStore",
            extra={
                "dimension": dimension,
                "metric": metric,
                "embedder_model": self.embedder.model_name
            }
        )

    def add(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> int:
        """
        Add document to vector store (thread-safe)

        Args:
            doc_id: Unique document identifier
            text: Document text to embed
            metadata: Optional metadata dictionary

        Returns:
            Index ID assigned to document

        Raises:
            ValueError: If doc_id already exists or text is empty
        """
        if not text or not text.strip():
            raise ValueError("Cannot add document with empty text")

        # Generate embedding BEFORE acquiring lock (embedder is thread-safe)
        # This minimizes lock contention for expensive embedding operation
        try:
            embedding = self.embedder.embed_text(text, normalize=(self.metric == "cosine"))
        except Exception as e:
            logger.error(f"Failed to generate embedding for doc '{doc_id}': {e}", exc_info=True)
            raise RuntimeError(f"Embedding generation failed: {e}") from e

        # Validate dimension
        if embedding.shape[0] != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {embedding.shape[0]}"
            )

        # Now acquire lock for store modifications
        with self._store_lock:
            if doc_id in self.doc_id_to_index_id:
                raise ValueError(f"Document ID '{doc_id}' already exists in store")

            # Add to FAISS index
            embedding_2d = embedding.reshape(1, -1).astype(np.float32)
            self.index.add(embedding_2d)

            # Store metadata
            index_id = self._next_index_id
            self.id_to_doc[index_id] = {
                "doc_id": doc_id,
                "text": text,
                "metadata": metadata or {},
                "embedding": embedding  # Store for later use
            }

            self.doc_id_to_index_id[doc_id] = index_id
            self._next_index_id += 1

            logger.debug(
                "Added document to vector store",
                extra={
                    "doc_id": doc_id,
                    "index_id": index_id,
                    "text_length": len(text),
                    "total_docs": len(self.id_to_doc)
                }
            )

            return index_id

    def add_batch(
        self,
        documents: list[tuple[str, str, Optional[dict[str, Any]]]]
    ) -> list[int]:
        """
        Add multiple documents efficiently (thread-safe)

        Args:
            documents: List of (doc_id, text, metadata) tuples

        Returns:
            List of index IDs assigned to documents

        Raises:
            ValueError: If any doc_id already exists or text is empty
        """
        if not documents:
            raise ValueError("Cannot add empty document list")

        # Validate inputs first (before lock)
        for doc_id, text, _ in documents:
            if not text or not text.strip():
                raise ValueError(f"Document '{doc_id}' has empty text")

        # Generate embeddings in batch BEFORE lock (expensive operation)
        texts = [text for _, text, _ in documents]
        try:
            embeddings = self.embedder.embed_batch(
                texts,
                normalize=(self.metric == "cosine")
            )
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}", exc_info=True)
            raise RuntimeError(f"Batch embedding generation failed: {e}") from e

        # Now acquire lock for store modifications
        with self._store_lock:
            # Validate doc_ids don't exist (inside lock for consistency)
            for doc_id, _, _ in documents:
                if doc_id in self.doc_id_to_index_id:
                    raise ValueError(f"Document ID '{doc_id}' already exists in store")

            # Add all embeddings to index
            embeddings_float32 = embeddings.astype(np.float32)
            self.index.add(embeddings_float32)

            # Store metadata for all documents
            index_ids = []
            for (doc_id, text, metadata), embedding in zip(documents, embeddings):
                index_id = self._next_index_id
                self.id_to_doc[index_id] = {
                    "doc_id": doc_id,
                    "text": text,
                    "metadata": metadata or {},
                    "embedding": embedding
                }
                self.doc_id_to_index_id[doc_id] = index_id
                index_ids.append(index_id)
                self._next_index_id += 1

            logger.info(
                "Added batch to vector store",
                extra={
                    "count": len(documents),
                    "total_docs": len(self.id_to_doc)
                }
            )

            return index_ids

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_fn: Optional[Callable[[dict[str, Any]], bool]] = None
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """
        Search for similar documents (thread-safe)

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_fn: Optional filter function on metadata
                      Should return True to include document

        Returns:
            List of (doc_id, score, metadata) tuples, sorted by relevance
            Score interpretation:
            - L2 metric: lower is better (0 = exact match)
            - Cosine metric: higher is better (1 = exact match)

        Raises:
            ValueError: If query is empty or top_k invalid
        """
        if not query or not query.strip():
            raise ValueError("Cannot search with empty query")

        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")

        # Generate query embedding BEFORE lock (expensive operation)
        try:
            query_embedding = self.embedder.embed_text(
                query,
                normalize=(self.metric == "cosine")
            )
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}", exc_info=True)
            raise RuntimeError(f"Query embedding generation failed: {e}") from e

        # Acquire lock for reading store state and searching
        with self._store_lock:
            if len(self.id_to_doc) == 0:
                logger.warning("Search called on empty vector store")
                return []

            # Search in FAISS
            # Request more results if filtering
            search_k = min(top_k * 3 if filter_fn else top_k, len(self.id_to_doc))

            query_2d = query_embedding.reshape(1, -1).astype(np.float32)
            distances, indices = self.index.search(query_2d, search_k)

            # Convert to results
            results = []
            for distance, index_id in zip(distances[0], indices[0]):
                # FAISS returns -1 for not found
                if index_id == -1:
                    continue

                index_id = int(index_id)
                doc_info = self.id_to_doc.get(index_id)
                if doc_info is None:
                    logger.warning(f"Index ID {index_id} not found in metadata store")
                    continue

                # Skip deleted documents
                if doc_info.get("_deleted", False):
                    continue

                # Apply filter
                if filter_fn and not filter_fn(doc_info["metadata"]):
                    continue

                results.append((
                    doc_info["doc_id"],
                    float(distance),
                    doc_info["metadata"]
                ))

                # Stop if we have enough results
                if len(results) >= top_k:
                    break

            logger.debug(
                "Search completed",
                extra={
                    "query": query[:50],
                    "results_count": len(results),
                    "total_docs": len(self.id_to_doc)
                }
            )

            return results

    def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        """
        Get document by ID

        Args:
            doc_id: Document identifier

        Returns:
            Document info dict or None if not found
        """
        index_id = self.doc_id_to_index_id.get(doc_id)
        if index_id is None:
            return None
        return self.id_to_doc.get(index_id)

    def remove(self, doc_id: str) -> bool:
        """
        Remove document from store (thread-safe)

        Note: FAISS doesn't support removal efficiently, so we just
        mark as deleted in metadata. Use rebuild() to compact.

        Args:
            doc_id: Document identifier

        Returns:
            True if removed, False if not found
        """
        with self._store_lock:
            index_id = self.doc_id_to_index_id.get(doc_id)
            if index_id is None:
                return False

            # Mark as deleted
            if index_id in self.id_to_doc:
                self.id_to_doc[index_id]["_deleted"] = True

            logger.debug(f"Marked document as deleted: {doc_id}")
            return True

    def rebuild(self) -> None:
        """
        Rebuild index removing deleted documents (thread-safe)

        This creates a new FAISS index without deleted documents.
        Use periodically if many documents are removed.
        """
        with self._store_lock:
            # Get non-deleted documents with their embeddings
            active_docs = []
            active_embeddings = []

            for doc_info in self.id_to_doc.values():
                if not doc_info.get("_deleted", False):
                    active_docs.append((
                        doc_info["doc_id"],
                        doc_info["text"],
                        doc_info["metadata"]
                    ))
                    active_embeddings.append(doc_info["embedding"])

            if not active_docs:
                logger.warning("Rebuild called but no active documents")
                return

            old_count = len(self.id_to_doc)

            # Create new FAISS index
            if self.metric == "L2":
                new_index = faiss.IndexFlatL2(self.dimension)
            else:  # cosine
                new_index = faiss.IndexFlatIP(self.dimension)

            # Add all active embeddings in one batch
            if active_embeddings:
                embeddings_array = np.array(active_embeddings).astype(np.float32)
                new_index.add(embeddings_array)

            # Rebuild metadata mappings
            new_id_to_doc = {}
            new_doc_id_to_index_id = {}

            for idx, (doc_id, text, metadata) in enumerate(active_docs):
                new_id_to_doc[idx] = {
                    "doc_id": doc_id,
                    "text": text,
                    "metadata": metadata,
                    "embedding": active_embeddings[idx]
                }
                new_doc_id_to_index_id[doc_id] = idx

            # Atomic swap of all data structures
            self.index = new_index
            self.id_to_doc = new_id_to_doc
            self.doc_id_to_index_id = new_doc_id_to_index_id
            self._next_index_id = len(active_docs)

            logger.info(
                "Rebuilt vector store",
                extra={
                    "old_count": old_count,
                    "new_count": len(self.id_to_doc),
                    "removed": old_count - len(self.id_to_doc)
                }
            )

    def save(self, path: Path) -> None:
        """
        Save vector store to disk

        Args:
            path: Directory path to save to

        Raises:
            IOError: If save fails
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        try:
            # Save FAISS index
            index_path = path / "index.faiss"
            faiss.write_index(self.index, str(index_path))

            # Prepare metadata for JSON serialization
            # Convert numpy arrays to lists for JSON compatibility
            serializable_id_to_doc = {}
            for idx, doc_info in self.id_to_doc.items():
                serializable_doc = {
                    "doc_id": doc_info["doc_id"],
                    "text": doc_info["text"],
                    "metadata": doc_info["metadata"],
                    "_deleted": doc_info.get("_deleted", False),
                    # Store embedding as list for JSON
                    "embedding": doc_info["embedding"].tolist()
                    if isinstance(doc_info["embedding"], np.ndarray)
                    else doc_info["embedding"],
                }
                serializable_id_to_doc[str(idx)] = serializable_doc

            metadata = {
                "id_to_doc": serializable_id_to_doc,
                "doc_id_to_index_id": self.doc_id_to_index_id,
                "next_index_id": self._next_index_id,
                "dimension": self.dimension,
                "metric": self.metric,
            }

            # Save as JSON (safer than pickle - no code execution risk)
            metadata_path = path / "metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # Also save integrity hash
            content_hash = hashlib.sha256(
                json.dumps(metadata, sort_keys=True).encode()
            ).hexdigest()
            hash_path = path / "metadata.sha256"
            hash_path.write_text(content_hash)

            logger.info(f"Saved vector store to {path}")

        except Exception as e:
            logger.error(f"Failed to save vector store: {e}", exc_info=True)
            raise OSError(f"Save failed: {e}") from e

    def load(self, path: Path) -> None:
        """
        Load vector store from disk

        Args:
            path: Directory path to load from

        Raises:
            IOError: If load fails
            FileNotFoundError: If files not found
            ValueError: If integrity check fails
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Vector store path not found: {path}")

        try:
            # Load FAISS index
            index_path = path / "index.faiss"
            if not index_path.exists():
                raise FileNotFoundError(f"Index file not found: {index_path}")

            self.index = faiss.read_index(str(index_path))

            # Load metadata from JSON (safer than pickle)
            metadata_path = path / "metadata.json"

            # Fallback to pickle for backward compatibility
            if not metadata_path.exists():
                pickle_path = path / "metadata.pkl"
                if pickle_path.exists():
                    logger.warning(
                        "Found legacy pickle metadata - migrating to JSON. "
                        "Please re-save to use secure JSON format."
                    )
                    import pickle
                    with open(pickle_path, "rb") as f:
                        metadata = pickle.load(f)
                    # Migrate: save as JSON after load
                    self._migrate_pickle_metadata(metadata, path)
                else:
                    raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
            else:
                # Verify integrity if hash exists
                hash_path = path / "metadata.sha256"
                with open(metadata_path, encoding="utf-8") as f:
                    content = f.read()
                    metadata = json.loads(content)

                if hash_path.exists():
                    expected_hash = hash_path.read_text().strip()
                    actual_hash = hashlib.sha256(
                        json.dumps(metadata, sort_keys=True).encode()
                    ).hexdigest()
                    if not hmac.compare_digest(expected_hash, actual_hash):
                        raise ValueError(
                            "Metadata integrity check failed - file may be corrupted"
                        )

            # Restore data structures
            # Convert string keys back to int for id_to_doc
            self.id_to_doc = {}
            for str_idx, doc_info in metadata["id_to_doc"].items():
                idx = int(str_idx)
                self.id_to_doc[idx] = {
                    "doc_id": doc_info["doc_id"],
                    "text": doc_info["text"],
                    "metadata": doc_info["metadata"],
                    "_deleted": doc_info.get("_deleted", False),
                    # Convert list back to numpy array
                    "embedding": np.array(doc_info["embedding"], dtype=np.float32),
                }

            self.doc_id_to_index_id = metadata["doc_id_to_index_id"]
            self._next_index_id = metadata["next_index_id"]
            self.dimension = metadata["dimension"]
            self.metric = metadata["metric"]

            logger.info(
                f"Loaded vector store from {path}",
                extra={"doc_count": len(self.id_to_doc)}
            )

        except Exception as e:
            logger.error(f"Failed to load vector store: {e}", exc_info=True)
            raise OSError(f"Load failed: {e}") from e

    def _migrate_pickle_metadata(self, metadata: dict, path: Path) -> None:
        """Migrate legacy pickle metadata to JSON format"""
        # Convert numpy arrays in id_to_doc
        for _idx, doc_info in metadata.get("id_to_doc", {}).items():
            if isinstance(doc_info.get("embedding"), np.ndarray):
                doc_info["embedding"] = doc_info["embedding"].tolist()

        # Temporarily set attributes for save
        self.id_to_doc = metadata.get("id_to_doc", {})
        self.doc_id_to_index_id = metadata.get("doc_id_to_index_id", {})
        self._next_index_id = metadata.get("next_index_id", 0)
        self.dimension = metadata.get("dimension", self.dimension)
        self.metric = metadata.get("metric", self.metric)

        # Re-save as JSON
        self.save(path)
        logger.info("Migrated pickle metadata to JSON format")

    def get_stats(self) -> dict[str, Any]:
        """
        Get vector store statistics

        Returns:
            Dictionary with store statistics
        """
        deleted_count = sum(
            1 for doc in self.id_to_doc.values()
            if doc.get("_deleted", False)
        )

        return {
            "total_docs": len(self.id_to_doc),
            "active_docs": len(self.id_to_doc) - deleted_count,
            "deleted_docs": deleted_count,
            "dimension": self.dimension,
            "metric": self.metric,
            "index_size": self.index.ntotal,
            "embedder_cache_stats": self.embedder.get_cache_stats()
        }

    def __repr__(self) -> str:
        """String representation"""
        stats = self.get_stats()
        return (
            f"VectorStore(docs={stats['active_docs']}/{stats['total_docs']}, "
            f"dim={self.dimension}, metric={self.metric})"
        )
