"""
Context Engine for Cognitive Reasoning

Retrieves relevant context from the knowledge base to enrich reasoning.
Used by Sancho Pass 2 to improve understanding with historical knowledge.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.core.events import Entity, PerceivedEvent
from src.core.memory.working_memory import ContextItem
from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager

logger = get_logger("passepartout.context_engine")

# Context source constants
CONTEXT_SOURCE_KB = "knowledge_base"
CONTEXT_SOURCE_HISTORY = "conversation_history"

# Context type constants
CONTEXT_TYPE_ENTITY = "entity"
CONTEXT_TYPE_SEMANTIC = "semantic"
CONTEXT_TYPE_THREAD = "thread"

# Memory and performance bounds
MAX_CONTEXT_CANDIDATES = 200  # Cap items before ranking to bound memory
DEFAULT_RETRIEVAL_TIMEOUT_SECONDS = 10.0  # Timeout for retrieval operations


@dataclass
class ContextRetrievalResult:
    """
    Result of context retrieval

    Contains all context items retrieved and metadata about the retrieval.
    """
    context_items: list[ContextItem]
    total_retrieved: int
    sources_used: list[str]
    retrieval_duration_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "context_items": [item.to_dict() for item in self.context_items],
            "total_retrieved": self.total_retrieved,
            "sources_used": self.sources_used,
            "retrieval_duration_seconds": self.retrieval_duration_seconds,
            "metadata": self.metadata
        }


class ContextEngine:
    """
    Retrieve relevant context for cognitive reasoning

    Strategies:
    1. Entity-based: Find notes mentioning same entities
    2. Semantic: Find notes similar in meaning
    3. Thread-based: Find related conversations/emails
    4. Ranking: Combine and rank all results by relevance

    Usage:
        engine = ContextEngine(note_manager)
        result = engine.retrieve_context(perceived_event, top_k=5)
        for item in result.context_items:
            print(f"Context: {item.content[:100]}...")
    """

    def __init__(
        self,
        note_manager: NoteManager,
        entity_weight: float = 0.4,
        semantic_weight: float = 0.4,
        thread_weight: float = 0.2,
        timeout_seconds: float = DEFAULT_RETRIEVAL_TIMEOUT_SECONDS,
        max_candidates: int = MAX_CONTEXT_CANDIDATES,
    ):
        """
        Initialize context engine

        Args:
            note_manager: NoteManager instance
            entity_weight: Weight for entity-based retrieval (0-1)
            semantic_weight: Weight for semantic similarity (0-1)
            thread_weight: Weight for thread-based retrieval (0-1)
            timeout_seconds: Timeout for retrieval operations
            max_candidates: Maximum candidates before ranking (memory bound)

        Raises:
            ValueError: If weights don't sum to 1.0
        """
        total_weight = entity_weight + semantic_weight + thread_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0, got {total_weight}"
            )

        self.note_manager = note_manager
        self.entity_weight = entity_weight
        self.semantic_weight = semantic_weight
        self.thread_weight = thread_weight
        self.timeout_seconds = timeout_seconds
        self.max_candidates = max_candidates

        logger.info(
            "Initialized ContextEngine",
            extra={
                "weights": {
                    "entity": entity_weight,
                    "semantic": semantic_weight,
                    "thread": thread_weight
                },
                "timeout_seconds": timeout_seconds,
                "max_candidates": max_candidates,
            }
        )

    async def retrieve_context(
        self,
        event: PerceivedEvent,
        top_k: int = 5,
        min_relevance: float = 0.5
    ) -> ContextRetrievalResult:
        """
        Retrieve relevant context for event (async with timeout)

        Args:
            event: PerceivedEvent to get context for
            top_k: Maximum number of context items to return
            min_relevance: Minimum relevance score (0-1)

        Returns:
            ContextRetrievalResult with ranked context items
        """
        start_time = time.time()

        try:
            # Run retrieval with timeout
            result = await asyncio.wait_for(
                self._retrieve_context_internal(event, top_k, min_relevance),
                timeout=self.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.warning(
                "Context retrieval timed out",
                extra={
                    "event_id": event.event_id,
                    "timeout_seconds": self.timeout_seconds,
                    "duration_seconds": duration,
                }
            )
            # Return empty result on timeout
            return ContextRetrievalResult(
                context_items=[],
                total_retrieved=0,
                sources_used=[],
                retrieval_duration_seconds=duration,
                metadata={
                    "event_id": event.event_id,
                    "event_title": event.title,
                    "timed_out": True,
                }
            )

    async def _retrieve_context_internal(
        self,
        event: PerceivedEvent,
        top_k: int,
        min_relevance: float
    ) -> ContextRetrievalResult:
        """
        Internal context retrieval logic (async)

        Runs I/O-bound retrieval methods in thread executor to avoid blocking.
        """
        start_time = time.time()
        loop = asyncio.get_event_loop()

        context_candidates: list[tuple[ContextItem, float]] = []
        sources_used = []

        # 1. Entity-based retrieval (run in thread to avoid blocking)
        if self.entity_weight > 0 and event.entities:
            entity_contexts = await loop.run_in_executor(
                None,
                lambda: self._retrieve_by_entities(event.entities, top_k=10)
            )
            # Apply memory bound while collecting
            remaining = self.max_candidates - len(context_candidates)
            for ctx in entity_contexts[:remaining]:
                context_candidates.append((ctx, self.entity_weight))
            if entity_contexts:
                sources_used.append("entity")

        # 2. Semantic retrieval (run in thread to avoid blocking)
        if self.semantic_weight > 0 and len(context_candidates) < self.max_candidates:
            semantic_contexts = await loop.run_in_executor(
                None,
                lambda: self._retrieve_by_semantic(event, top_k=10)
            )
            # Apply memory bound while collecting
            remaining = self.max_candidates - len(context_candidates)
            for ctx in semantic_contexts[:remaining]:
                context_candidates.append((ctx, self.semantic_weight))
            if semantic_contexts:
                sources_used.append("semantic")

        # 3. Thread-based retrieval (run in thread to avoid blocking)
        if self.thread_weight > 0 and event.thread_id and len(context_candidates) < self.max_candidates:
            thread_contexts = await loop.run_in_executor(
                None,
                lambda: self._retrieve_by_thread(event.thread_id, top_k=5)
            )
            # Apply memory bound while collecting
            remaining = self.max_candidates - len(context_candidates)
            for ctx in thread_contexts[:remaining]:
                context_candidates.append((ctx, self.thread_weight))
            if thread_contexts:
                sources_used.append("thread")

        # Log if we hit memory bound
        if len(context_candidates) >= self.max_candidates:
            logger.debug(
                "Context candidates capped at %d items",
                self.max_candidates
            )

        # 4. Rank and deduplicate
        ranked_contexts = self._rank_and_deduplicate(
            context_candidates,
            top_k=top_k,
            min_relevance=min_relevance
        )

        duration = time.time() - start_time

        result = ContextRetrievalResult(
            context_items=ranked_contexts,
            total_retrieved=len(context_candidates),
            sources_used=sources_used,
            retrieval_duration_seconds=duration,
            metadata={
                "event_id": event.event_id,
                "event_title": event.title
            }
        )

        logger.info(
            "Context retrieval complete",
            extra={
                "event_id": event.event_id,
                "contexts_found": len(ranked_contexts),
                "total_candidates": len(context_candidates),
                "duration_seconds": duration,
                "sources": sources_used
            }
        )

        return result

    def retrieve_context_sync(
        self,
        event: PerceivedEvent,
        top_k: int = 5,
        min_relevance: float = 0.5
    ) -> ContextRetrievalResult:
        """
        Synchronous wrapper for retrieve_context (for backward compatibility)

        Uses asyncio.run() to execute the async method from sync code.
        For new code, prefer the async retrieve_context() method.

        Args:
            event: PerceivedEvent to get context for
            top_k: Maximum number of context items to return
            min_relevance: Minimum relevance score (0-1)

        Returns:
            ContextRetrievalResult with ranked context items
        """
        try:
            # Try to get existing event loop
            asyncio.get_running_loop()
            # If we're already in an async context, run in executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.retrieve_context(event, top_k, min_relevance)
                )
                return future.result()
        except RuntimeError:
            # No event loop running, use asyncio.run()
            return asyncio.run(self.retrieve_context(event, top_k, min_relevance))

    def _distance_to_relevance(self, distance: float) -> float:
        """
        Convert FAISS distance to relevance score (0-1)

        Args:
            distance: FAISS distance (L2 or cosine)

        Returns:
            Relevance score between 0 and 1 (higher is better)
        """
        metric = self.note_manager.vector_store.metric

        if metric == "cosine":
            # For cosine with IndexFlatIP on normalized vectors:
            # Score is inner product, range [0, 1], higher is better
            # Already in relevance format
            return min(1.0, max(0.0, distance))

        else:  # L2
            # For L2 distance: 0 = perfect match, higher = worse
            # Convert to relevance using exponential decay
            # relevance = exp(-distance^2 / temperature)
            # Temperature controls how quickly relevance drops
            temperature = 2.0
            relevance = np.exp(-(distance ** 2) / temperature)
            return min(1.0, max(0.0, relevance))

    def _retrieve_by_entities(
        self,
        entities: list[Entity],
        top_k: int = 10
    ) -> list[ContextItem]:
        """
        Retrieve context based on entities

        Args:
            entities: List of entities to search for
            top_k: Maximum results per entity

        Returns:
            List of ContextItem objects
        """
        context_items = []

        for entity in entities:
            try:
                # Get notes with similarity scores
                notes_with_scores = self.note_manager.get_notes_by_entity(
                    entity, top_k=top_k, return_scores=True
                )

                for note, distance in notes_with_scores:
                    # Combine entity confidence with similarity score
                    similarity_relevance = self._distance_to_relevance(distance)
                    combined_relevance = entity.confidence * similarity_relevance

                    context_item = ContextItem(
                        source=CONTEXT_SOURCE_KB,
                        type=CONTEXT_TYPE_ENTITY,
                        content=f"# {note.title}\n\n{note.content}",
                        relevance_score=combined_relevance,
                        metadata={
                            "note_id": note.note_id,
                            "entity_type": entity.type,
                            "entity_value": entity.value,
                            "entity_confidence": entity.confidence,
                            "similarity_score": similarity_relevance,
                            "tags": note.tags,
                            "created_at": note.created_at.isoformat()
                        }
                    )
                    context_items.append(context_item)

            except Exception as e:
                logger.warning(f"Entity retrieval failed for {entity.value}: {e}")
                continue

        logger.debug(
            f"Entity retrieval: {len(context_items)} items",
            extra={"entities": [e.value for e in entities]}
        )

        return context_items

    def _retrieve_by_semantic(
        self,
        event: PerceivedEvent,
        top_k: int = 10
    ) -> list[ContextItem]:
        """
        Retrieve context based on semantic similarity

        Args:
            event: Event to find similar content for
            top_k: Maximum results

        Returns:
            List of ContextItem objects
        """
        # Create search query from event
        query = f"{event.title}\n{event.content}"

        try:
            # Get notes with similarity scores
            notes_with_scores = self.note_manager.search_notes(
                query=query,
                top_k=top_k,
                return_scores=True
            )

            context_items = []
            for note, distance in notes_with_scores:
                # Convert FAISS distance to relevance score (0-1)
                relevance = self._distance_to_relevance(distance)

                context_item = ContextItem(
                    source=CONTEXT_SOURCE_KB,
                    type=CONTEXT_TYPE_SEMANTIC,
                    content=f"# {note.title}\n\n{note.content}",
                    relevance_score=relevance,
                    metadata={
                        "note_id": note.note_id,
                        "tags": note.tags,
                        "created_at": note.created_at.isoformat(),
                        "similarity_distance": float(distance)  # Store raw distance for debugging
                    }
                )
                context_items.append(context_item)

            logger.debug(
                f"Semantic retrieval: {len(context_items)} items",
                extra={
                    "query": query[:50],
                    "top_score": context_items[0].relevance_score if context_items else 0.0
                }
            )

            return context_items

        except Exception as e:
            logger.warning(f"Semantic retrieval failed: {e}")
            return []

    def _retrieve_by_thread(
        self,
        thread_id: str,
        top_k: int = 5
    ) -> list[ContextItem]:
        """
        Retrieve context from same thread/conversation

        Args:
            thread_id: Thread identifier
            top_k: Maximum results

        Returns:
            List of ContextItem objects
        """
        # Search for notes with this thread_id in metadata
        try:
            # For now, do a semantic search with thread_id
            # In full implementation, would have indexed thread_id in metadata
            notes = self.note_manager.search_notes(f"thread:{thread_id}", top_k=top_k)

            context_items = []
            for note in notes:
                # Check if note actually has this thread_id
                if note.metadata.get("thread_id") == thread_id:
                    context_item = ContextItem(
                        source=CONTEXT_SOURCE_HISTORY,
                        type=CONTEXT_TYPE_THREAD,
                        content=f"# {note.title}\n\n{note.content}",
                        relevance_score=0.9,  # High relevance for same thread
                        metadata={
                            "note_id": note.note_id,
                            "thread_id": thread_id,
                            "created_at": note.created_at.isoformat()
                        }
                    )
                    context_items.append(context_item)

            logger.debug(
                f"Thread retrieval: {len(context_items)} items",
                extra={"thread_id": thread_id}
            )

            return context_items

        except Exception as e:
            logger.warning(f"Thread retrieval failed: {e}")
            return []

    def _rank_and_deduplicate(
        self,
        candidates: list[tuple[ContextItem, float]],
        top_k: int,
        min_relevance: float
    ) -> list[ContextItem]:
        """
        Rank context candidates and remove duplicates

        Args:
            candidates: List of (ContextItem, weight) tuples
            top_k: Maximum results to return
            min_relevance: Minimum relevance threshold

        Returns:
            Ranked and deduplicated list of ContextItem objects
        """
        if not candidates:
            return []

        # Calculate final scores (base relevance * strategy weight)
        scored_items: list[tuple[ContextItem, float]] = []
        seen_note_ids = set()

        for context_item, weight in candidates:
            # Deduplicate by note_id
            note_id = context_item.metadata.get("note_id")
            if note_id and note_id in seen_note_ids:
                continue

            # Calculate final score
            final_score = context_item.relevance_score * weight

            # Filter by minimum relevance
            if final_score >= min_relevance:
                # Update context item with final score
                context_item.relevance_score = final_score
                scored_items.append((context_item, final_score))

                if note_id:
                    seen_note_ids.add(note_id)

        # Sort by score (descending)
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # Return top K
        result = [item for item, score in scored_items[:top_k]]

        logger.debug(
            f"Ranking: {len(result)}/{len(candidates)} items",
            extra={
                "top_scores": [round(score, 2) for _, score in scored_items[:3]]
            }
        )

        return result

    def get_stats(self) -> dict[str, Any]:
        """
        Get context engine statistics

        Returns:
            Statistics dictionary
        """
        return {
            "weights": {
                "entity": self.entity_weight,
                "semantic": self.semantic_weight,
                "thread": self.thread_weight
            },
            "note_manager": repr(self.note_manager)
        }

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"ContextEngine("
            f"entity={self.entity_weight}, "
            f"semantic={self.semantic_weight}, "
            f"thread={self.thread_weight})"
        )
