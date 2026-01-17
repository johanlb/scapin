"""
Context Engine for Cognitive Reasoning

Retrieves relevant context from the knowledge base to enrich reasoning.
Used by Sancho Pass 2 to improve understanding with historical knowledge.
"""

import asyncio
import atexit
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

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
CONTEXT_TYPE_LINKED = "linked"  # New context type for graph expansion

# Memory and performance bounds
MAX_CONTEXT_CANDIDATES = 200  # Cap items before ranking to bound memory
DEFAULT_RETRIEVAL_TIMEOUT_SECONDS = 10.0  # Timeout for retrieval operations
MAX_SEMANTIC_QUERY_LENGTH = 5000  # Maximum characters for semantic search query

# Module-level executor for sync wrapper (reused across calls)
_sync_executor: Optional[ThreadPoolExecutor] = None


def _cleanup_executor() -> None:
    """Clean up the module-level executor at program exit"""
    global _sync_executor
    if _sync_executor is not None:
        _sync_executor.shutdown(wait=False)
        _sync_executor = None
        logger.debug("Cleaned up sync executor")


# Register cleanup handler to prevent resource leaks
atexit.register(_cleanup_executor)


@dataclass
class ContextRetrievalResult:
    """
    Result of context retrieval

    Contains all context items retrieved and metadata about the retrieval.
    Uses slots=True for memory efficiency.
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
            "metadata": self.metadata,
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
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

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
                    "thread": thread_weight,
                },
                "timeout_seconds": timeout_seconds,
                "max_candidates": max_candidates,
            },
        )

    async def _retrieve_graph_expansion(
        self,
        initial_candidates: list[tuple[ContextItem, float]],
        graph_weight: float = 0.5,  # Weight factor for linked notes relative to parent
    ) -> list[tuple[ContextItem, float]]:
        """
        Expand context by following outgoing links from initial candidates.
        """
        if not initial_candidates:
            return []

        # Collect all linked note titles
        # Use a set to duplicate titles
        linked_titles = set()
        for item, _ in initial_candidates:
            # outgoing_links should be in metadata if NoteManager captured them
            links = item.metadata.get("outgoing_links", [])
            linked_titles.update(links)

        if not linked_titles:
            return []

        # Batch fetch linked notes by title
        # NoteManager doesn't have a direct "get_notes_by_titles" but has "get_note_by_title"
        # We can implement a batch lookup or loop. For v1, loop is fine as N is small (max 20 candidates * ~3 links)
        # Efficient batch Retrieval if possible, or parallel loop
        # Since we are in async context, we can run this potentially in parallel if NoteManager supports it,
        # but NoteManager methods are sync (disk I/O).
        # We'll run in executor to avoid blocking.

        loop = asyncio.get_running_loop()

        def fetch_linked_notes():
            results = []
            for title in linked_titles:
                # Note: get_note_by_title searches all notes, which might be slow if many notes.
                # Optimally NoteManager should index titles.
                # For now, we assume it's acceptable or we should upgrade NoteManager later.
                note = self.note_manager.get_note_by_title(title)
                if note:
                    # Calculate score: parent_score * graph_weight?
                    # No, determining "parent" is hard if multiple parents link to it.
                    # We assign a fixed high relevance for explicit links, dampened by graph_weight.

                    # Actually, 2nd degree notes are usually "context", so they are valuable.
                    # Let's assign a base relevance and apply the graph_weight in the main ranking loop.

                    ctx_item = ContextItem(
                        source=CONTEXT_SOURCE_KB,
                        type=CONTEXT_TYPE_LINKED,
                        content=f"# {note.title}\n\n{note.content}",
                        relevance_score=0.8,  # Base relevance for explicitly linked content
                        metadata={
                            "note_id": note.note_id,
                            "tags": note.tags,
                            "created_at": note.created_at.isoformat(),
                            "outgoing_links": note.outgoing_links,
                        },
                    )
                    results.append((ctx_item, graph_weight))
            return results

        return await loop.run_in_executor(None, fetch_linked_notes)

    async def retrieve_context(
        self, event: PerceivedEvent, top_k: int = 5, min_relevance: float = 0.5
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
                timeout=self.timeout_seconds,
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
                },
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
                },
            )

    async def _retrieve_context_internal(
        self, event: PerceivedEvent, top_k: int, min_relevance: float
    ) -> ContextRetrievalResult:
        """
        Internal context retrieval logic (async)

        Runs I/O-bound retrieval methods in parallel using thread executor.
        """
        start_time = time.time()
        loop = asyncio.get_running_loop()

        context_candidates: list[tuple[ContextItem, float]] = []
        sources_used = []

        # Prepare parallel retrieval tasks
        tasks = []
        task_sources = []

        # 1. Entity-based retrieval
        # Note: Capture entities explicitly to avoid closure issues with loop variables
        if self.entity_weight > 0 and event.entities:
            entities = event.entities  # Capture for lambda
            tasks.append(
                loop.run_in_executor(
                    None, lambda ents=entities: self._retrieve_by_entities(ents, top_k=10)
                )
            )
            task_sources.append(("entity", self.entity_weight))

        # 2. Semantic retrieval
        if self.semantic_weight > 0:
            tasks.append(
                loop.run_in_executor(None, lambda e=event: self._retrieve_by_semantic(e, top_k=10))
            )
            task_sources.append(("semantic", self.semantic_weight))

        # 3. Thread-based retrieval
        if self.thread_weight > 0 and event.thread_id:
            thread_id = event.thread_id  # Capture for lambda
            tasks.append(
                loop.run_in_executor(
                    None, lambda tid=thread_id: self._retrieve_by_thread(tid, top_k=5)
                )
            )
            task_sources.append(("thread", self.thread_weight))

        # Fast-path: no retrieval tasks to run
        if not tasks:
            duration = time.time() - start_time
            logger.debug(
                "No retrieval sources available",
                extra={"event_id": event.event_id, "duration_seconds": duration},
            )
            return ContextRetrievalResult(
                context_items=[],
                total_retrieved=0,
                sources_used=[],
                retrieval_duration_seconds=duration,
                metadata={"event_id": event.event_id, "event_title": event.title},
            )

        # Execute all retrievals in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (source_name, weight), result in zip(task_sources, results):
            if isinstance(result, Exception):
                logger.warning(
                    "Context source retrieval failed",
                    extra={"source": source_name, "error": str(result)},
                )
                continue

            contexts = result
            # Apply memory bound while collecting
            remaining = self.max_candidates - len(context_candidates)
            for ctx in contexts[:remaining]:
                context_candidates.append((ctx, weight))
            if contexts:
                sources_used.append(source_name)

        # Log if we hit memory bound
        if len(context_candidates) >= self.max_candidates:
            logger.debug(
                "Context candidates capped at max_candidates",
                extra={"max_candidates": self.max_candidates},
            )

        # --- GRAPH EXPANSION (Step 2) ---
        # Fetch notes linked from the initial candidates
        # Only do this if we have candidates and enough time left
        # (Could add a check for elapsed time vs timeout)

        # We use a dedicated weight for graph expansion (can be configured in init later)
        GRAPH_WEIGHT = 0.2

        try:
            linked_candidates = await self._retrieve_graph_expansion(
                context_candidates, graph_weight=GRAPH_WEIGHT
            )
            if linked_candidates:
                context_candidates.extend(linked_candidates)
                sources_used.append("graph_expansion")
                logger.debug(
                    "Graph expansion added candidates", extra={"count": len(linked_candidates)}
                )
        except Exception as e:
            logger.warning("Graph expansion failed", extra={"error": str(e)})

        # 4. Rank and deduplicate

        # 4. Rank and deduplicate
        ranked_contexts = self._rank_and_deduplicate(
            context_candidates, top_k=top_k, min_relevance=min_relevance
        )

        duration = time.time() - start_time

        result = ContextRetrievalResult(
            context_items=ranked_contexts,
            total_retrieved=len(context_candidates),
            sources_used=sources_used,
            retrieval_duration_seconds=duration,
            metadata={"event_id": event.event_id, "event_title": event.title},
        )

        logger.info(
            "Context retrieval complete",
            extra={
                "event_id": event.event_id,
                "contexts_found": len(ranked_contexts),
                "total_candidates": len(context_candidates),
                "duration_seconds": duration,
                "sources": sources_used,
            },
        )

        return result

    def retrieve_context_sync(
        self, event: PerceivedEvent, top_k: int = 5, min_relevance: float = 0.5
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
        global _sync_executor

        try:
            # Try to get existing event loop
            asyncio.get_running_loop()
            # If we're already in an async context, run in executor
            # Reuse module-level executor for performance
            if _sync_executor is None:
                _sync_executor = ThreadPoolExecutor(
                    max_workers=2, thread_name_prefix="context_sync"
                )
            future = _sync_executor.submit(
                asyncio.run, self.retrieve_context(event, top_k, min_relevance)
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
            relevance = np.exp(-(distance**2) / temperature)
            return min(1.0, max(0.0, relevance))

    def _retrieve_by_entities(self, entities: list[Entity], top_k: int = 10) -> list[ContextItem]:
        """
        Retrieve context based on entities

        Uses a two-phase approach:
        1. Exact alias matching (high precision)
        2. Semantic vector search (broader coverage)

        Args:
            entities: List of entities to search for
            top_k: Maximum results per entity

        Returns:
            List of ContextItem objects
        """
        context_items = []
        seen_note_ids: set[str] = set()  # Track seen notes to avoid duplicates

        for entity in entities:
            try:
                # Phase 1: Try exact alias matching first (high precision)
                # This catches cases like "Marc" -> "Marc Dupont" via aliases
                alias_match = self.note_manager.find_note_by_alias(entity.value)
                if alias_match and alias_match.note_id not in seen_note_ids:
                    seen_note_ids.add(alias_match.note_id)
                    context_item = ContextItem(
                        source=CONTEXT_SOURCE_KB,
                        type=CONTEXT_TYPE_ENTITY,
                        content=f"# {alias_match.title}\n\n{alias_match.content}",
                        relevance_score=entity.confidence,  # High relevance for exact match
                        metadata={
                            "note_id": alias_match.note_id,
                            "entity_type": entity.type,
                            "entity_value": entity.value,
                            "entity_confidence": entity.confidence,
                            "match_type": "alias_exact",
                            "matched_alias": entity.value,
                            "tags": alias_match.tags,
                            "created_at": alias_match.created_at.isoformat(),
                        },
                    )
                    context_items.append(context_item)
                    logger.debug(
                        "Alias match found",
                        extra={
                            "entity": entity.value,
                            "matched_note": alias_match.title,
                        },
                    )

                # Phase 2: Semantic vector search (broader coverage)
                # Get notes with similarity scores
                notes_with_scores = self.note_manager.get_notes_by_entity(
                    entity, top_k=top_k, return_scores=True
                )

                for note, distance in notes_with_scores:
                    # Skip if already added via alias match
                    if note.note_id in seen_note_ids:
                        continue
                    seen_note_ids.add(note.note_id)
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
                            "match_type": "semantic",
                            "similarity_score": similarity_relevance,
                            "tags": note.tags,
                            "created_at": note.created_at.isoformat(),
                        },
                    )
                    context_items.append(context_item)

            except Exception as e:
                logger.warning(
                    "Entity retrieval failed", extra={"entity_value": entity.value, "error": str(e)}
                )
                continue

        # Count alias vs semantic matches for logging
        alias_matches = sum(1 for c in context_items if c.metadata.get("match_type") == "alias_exact")
        semantic_matches = len(context_items) - alias_matches

        logger.debug(
            "Entity retrieval complete",
            extra={
                "items_found": len(context_items),
                "alias_matches": alias_matches,
                "semantic_matches": semantic_matches,
                "entities": [e.value for e in entities],
            },
        )

        return context_items

    def _retrieve_by_semantic(self, event: PerceivedEvent, top_k: int = 10) -> list[ContextItem]:
        """
        Retrieve context based on semantic similarity

        Args:
            event: Event to find similar content for
            top_k: Maximum results

        Returns:
            List of ContextItem objects
        """
        # Create search query from event, limiting size for embedding performance
        query = f"{event.title}\n{event.content}"
        if len(query) > MAX_SEMANTIC_QUERY_LENGTH:
            query = query[:MAX_SEMANTIC_QUERY_LENGTH]
            logger.debug(
                "Semantic query truncated",
                extra={"original_length": len(event.title) + len(event.content) + 1},
            )

        try:
            # Get notes with similarity scores
            notes_with_scores = self.note_manager.search_notes(
                query=query, top_k=top_k, return_scores=True
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
                        "similarity_distance": float(distance),  # Store raw distance for debugging
                    },
                )
                context_items.append(context_item)

            logger.debug(
                "Semantic retrieval complete",
                extra={
                    "items_found": len(context_items),
                    "query_preview": query[:50],
                    "top_score": context_items[0].relevance_score if context_items else 0.0,
                },
            )

            return context_items

        except Exception as e:
            logger.warning("Semantic retrieval failed", extra={"error": str(e)})
            return []

    def _retrieve_by_thread(self, thread_id: str, top_k: int = 5) -> list[ContextItem]:
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
                            "created_at": note.created_at.isoformat(),
                        },
                    )
                    context_items.append(context_item)

            logger.debug(
                "Thread retrieval complete",
                extra={"items_found": len(context_items), "thread_id": thread_id},
            )

            return context_items

        except Exception as e:
            logger.warning(
                "Thread retrieval failed", extra={"thread_id": thread_id, "error": str(e)}
            )
            return []

    def _rank_and_deduplicate(
        self, candidates: list[tuple[ContextItem, float]], top_k: int, min_relevance: float
    ) -> list[ContextItem]:
        """
        Rank context candidates and remove duplicates

        Args:
            candidates: List of (ContextItem, weight) tuples
            top_k: Maximum results to return
            min_relevance: Minimum relevance threshold (applied to base score)

        Returns:
            Ranked and deduplicated list of ContextItem objects
        """
        if not candidates:
            return []

        # Aggregate scores for items from multiple sources
        # Use weight as a boost factor, not a multiplier that reduces score
        aggregated: dict[
            str, tuple[ContextItem, float, float]
        ] = {}  # note_id -> (item, max_score, weight_sum)

        for context_item, weight in candidates:
            note_id = context_item.metadata.get("note_id", id(context_item))
            base_score = context_item.relevance_score

            if note_id in aggregated:
                existing_item, existing_score, existing_weight = aggregated[note_id]
                # Keep highest score, accumulate weights for ranking boost
                if base_score > existing_score:
                    aggregated[note_id] = (context_item, base_score, existing_weight + weight)
                else:
                    aggregated[note_id] = (existing_item, existing_score, existing_weight + weight)
            else:
                aggregated[note_id] = (context_item, base_score, weight)

        # Filter by minimum relevance (on BASE score, not weighted)
        # Then calculate final ranking score using weight as boost
        scored_items: list[tuple[ContextItem, float]] = []

        for _note_id, (context_item, base_score, weight_sum) in aggregated.items():
            if base_score >= min_relevance:
                # Ranking score: base_score boosted by weight coverage
                # weight_sum can be >1 if item found by multiple strategies
                ranking_score = base_score * (1 + weight_sum * 0.5)
                context_item.relevance_score = base_score  # Keep original score
                scored_items.append((context_item, ranking_score))

        # Sort by ranking score (descending)
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # Return top K
        result = [item for item, _score in scored_items[:top_k]]

        logger.debug(
            "Ranking complete",
            extra={
                "input_candidates": len(candidates),
                "after_dedup": len(aggregated),
                "after_filter": len(scored_items),
                "returned": len(result),
                "top_scores": [round(item.relevance_score, 2) for item in result[:3]],
            },
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
                "thread": self.thread_weight,
            },
            "note_manager": repr(self.note_manager),
        }

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"ContextEngine("
            f"entity={self.entity_weight}, "
            f"semantic={self.semantic_weight}, "
            f"thread={self.thread_weight})"
        )
