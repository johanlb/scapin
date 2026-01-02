"""
Embedding Generator for Semantic Search

Generates vector embeddings from text using sentence-transformers.
Includes caching for performance and batch processing support.
"""

import hashlib
import threading
from collections import OrderedDict
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from src.monitoring.logger import get_logger

logger = get_logger("passepartout.embeddings")


class EmbeddingGenerator:
    """
    Generate semantic embeddings from text using sentence-transformers

    Features:
    - Caching with hash-based lookup
    - Batch processing for efficiency
    - L2 normalization for cosine similarity
    - Configurable model selection

    Usage:
        embedder = EmbeddingGenerator()
        vector = embedder.embed_text("Hello world")
        vectors = embedder.embed_batch(["Text 1", "Text 2"])
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_size: int = 10000,
        device: Optional[str] = None
    ):
        """
        Initialize embedding generator

        Args:
            model_name: HuggingFace model identifier
                       Default: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
            cache_size: Maximum number of embeddings to cache
            device: Device for computation ('cuda', 'cpu', or None for auto)

        Raises:
            ImportError: If sentence-transformers not installed
            ValueError: If model cannot be loaded
        """
        self.model_name = model_name
        self.cache_size = cache_size
        # Thread-safe LRU cache using OrderedDict
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._cache_lock = threading.Lock()
        # Separate lock for statistics to minimize contention
        self._stats_lock = threading.Lock()
        self._cache_hits = 0
        self._cache_misses = 0

        try:
            self.model = SentenceTransformer(model_name, device=device)
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"Loaded embedding model: {model_name}",
                extra={
                    "dimension": self.embedding_dimension,
                    "device": self.model.device
                }
            )
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}", exc_info=True)
            raise ValueError(f"Cannot load embedding model {model_name}: {e}") from e

    def embed_text(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for single text (thread-safe with LRU cache)

        Args:
            text: Input text to embed
            normalize: Whether to L2-normalize the embedding (for cosine similarity)

        Returns:
            Embedding vector as numpy array (shape: [embedding_dimension])

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        # Normalize text
        text_normalized = text.strip()
        cache_key = self._get_cache_key(text_normalized)

        # Check cache (thread-safe)
        with self._cache_lock:
            if cache_key in self._cache:
                # Move to end (mark as recently used)
                self._cache.move_to_end(cache_key)
                embedding = self._cache[cache_key].copy()  # Copy to avoid shared reference
                with self._stats_lock:
                    self._cache_hits += 1
                logger.debug(f"Cache hit for text: {text_normalized[:50]}...")
                return embedding

        # Cache miss - update stats
        with self._stats_lock:
            self._cache_misses += 1

        # Generate embedding (outside lock - expensive operation)
        try:
            embedding = self.model.encode(
                text_normalized,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )

            # Cache result (thread-safe with LRU eviction)
            self._add_to_cache(cache_key, embedding)

            logger.debug(
                f"Generated embedding for text: {text_normalized[:50]}...",
                extra={"dimension": embedding.shape[0]}
            )

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    def embed_batch(
        self,
        texts: list[str],
        normalize: bool = True,
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently

        Args:
            texts: List of texts to embed
            normalize: Whether to L2-normalize embeddings
            batch_size: Number of texts to process at once
            show_progress: Show progress bar (useful for large batches)

        Returns:
            Embedding matrix as numpy array (shape: [num_texts, embedding_dimension])

        Raises:
            ValueError: If texts is empty or contains empty strings
        """
        if not texts:
            raise ValueError("Cannot embed empty text list")

        # Validate all texts
        texts_normalized = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} is empty")
            texts_normalized.append(text.strip())

        # Check cache for each text (thread-safe)
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts_normalized):
            cache_key = self._get_cache_key(text)

            with self._cache_lock:
                if cache_key in self._cache:
                    # Move to end (LRU)
                    self._cache.move_to_end(cache_key)
                    embedding = self._cache[cache_key].copy()
                    embeddings.append((i, embedding))
                    with self._stats_lock:
                        self._cache_hits += 1
                else:
                    with self._stats_lock:
                        self._cache_misses += 1
                    uncached_texts.append(text)
                    uncached_indices.append(i)

        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                new_embeddings = self.model.encode(
                    uncached_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=normalize,
                    batch_size=batch_size,
                    show_progress_bar=show_progress
                )

                # Cache new embeddings
                for text, embedding in zip(uncached_texts, new_embeddings):
                    cache_key = self._get_cache_key(text)
                    self._add_to_cache(cache_key, embedding)

                # Add to results
                for idx, embedding in zip(uncached_indices, new_embeddings):
                    embeddings.append((idx, embedding))

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}", exc_info=True)
                raise RuntimeError(f"Batch embedding generation failed: {e}") from e

        # Sort by original index and extract embeddings
        embeddings.sort(key=lambda x: x[0])
        result = np.array([emb for _, emb in embeddings])

        logger.info(
            "Generated batch embeddings",
            extra={
                "total": len(texts),
                "cached": self._cache_hits,
                "generated": len(uncached_texts),
                "shape": result.shape
            }
        )

        return result

    def get_dimension(self) -> int:
        """
        Get embedding dimension

        Returns:
            Embedding vector dimension
        """
        return self.embedding_dimension

    def clear_cache(self) -> None:
        """
        Clear embedding cache (thread-safe)

        Useful for freeing memory or resetting cache statistics.
        """
        with self._cache_lock:
            cache_size = len(self._cache)
            self._cache.clear()

        with self._stats_lock:
            self._cache_hits = 0
            self._cache_misses = 0

        logger.info(f"Cleared embedding cache ({cache_size} entries)")

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache performance statistics (thread-safe)

        Returns:
            Dictionary with cache hits, misses, size, and hit rate
        """
        with self._stats_lock:
            total = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total if total > 0 else 0.0
            hits = self._cache_hits
            misses = self._cache_misses

        with self._cache_lock:
            cache_size = len(self._cache)

        return {
            "hits": hits,
            "misses": misses,
            "size": cache_size,
            "max_size": self.cache_size,
            "hit_rate": hit_rate
        }

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key from text using hash

        Args:
            text: Normalized text

        Returns:
            Hash string for cache lookup
        """
        # Use SHA256 for collision resistance
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _add_to_cache(self, key: str, embedding: np.ndarray) -> None:
        """
        Add embedding to cache with LRU eviction (thread-safe)

        Args:
            key: Cache key
            embedding: Embedding vector
        """
        with self._cache_lock:
            # Update or add (move to end if exists)
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = embedding

            # Evict least recently used if over limit
            if len(self._cache) > self.cache_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug(f"Evicted LRU cache entry: {evicted_key[:16]}...")

    def __repr__(self) -> str:
        """String representation"""
        stats = self.get_cache_stats()
        return (
            f"EmbeddingGenerator(model={self.model_name}, "
            f"dim={self.embedding_dimension}, "
            f"cache={stats['size']}/{stats['max_size']}, "
            f"hit_rate={stats['hit_rate']:.1%})"
        )


def get_embedding_generator(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    cache_size: int = 10000
) -> EmbeddingGenerator:
    """
    Get or create global embedding generator (singleton pattern)

    Args:
        model_name: HuggingFace model identifier
        cache_size: Maximum cache size

    Returns:
        EmbeddingGenerator instance
    """
    # For now, just create new instance
    # In production, could use singleton pattern
    return EmbeddingGenerator(model_name=model_name, cache_size=cache_size)
