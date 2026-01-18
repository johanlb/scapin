"""
Performance Test Configuration and Fixtures

Provides:
- Timing decorators and context managers
- Large dataset fixtures
- Benchmark assertion helpers
- Memory profiling utilities
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.events.universal_event import Entity, PerceivedEvent, Sender
from src.sancho.convergence import (
    DecomposedConfidence,
    Extraction,
    MultiPassConfig,
    PassResult,
    PassType,
)


# ============================================================================
# Performance Metrics
# ============================================================================


@dataclass
class PerformanceMetrics:
    """Capture performance metrics for a test"""

    name: str
    duration_ms: float
    iterations: int = 1
    memory_mb: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def avg_duration_ms(self) -> float:
        """Average duration per iteration"""
        return self.duration_ms / self.iterations if self.iterations > 0 else 0

    def assert_under(self, max_ms: float, msg: str = "") -> None:
        """Assert duration is under threshold"""
        if self.avg_duration_ms > max_ms:
            raise AssertionError(
                f"{self.name}: {self.avg_duration_ms:.2f}ms > {max_ms}ms threshold. {msg}"
            )


@contextmanager
def measure_time(name: str = "operation") -> Generator[PerformanceMetrics, None, None]:
    """
    Context manager to measure execution time.

    Usage:
        with measure_time("context_retrieval") as metrics:
            result = await engine.retrieve_context(entities)
        metrics.assert_under(200, "Context retrieval too slow")
    """
    metrics = PerformanceMetrics(name=name, duration_ms=0)
    start = time.perf_counter()
    try:
        yield metrics
    finally:
        metrics.duration_ms = (time.perf_counter() - start) * 1000


def benchmark(iterations: int = 10, warmup: int = 2):
    """
    Decorator for benchmark tests.

    Args:
        iterations: Number of iterations to run
        warmup: Number of warmup iterations (not counted)
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Warmup
            for _ in range(warmup):
                await func(*args, **kwargs)

            # Benchmark
            total_time = 0
            for _ in range(iterations):
                start = time.perf_counter()
                await func(*args, **kwargs)
                total_time += (time.perf_counter() - start) * 1000

            return PerformanceMetrics(
                name=func.__name__,
                duration_ms=total_time,
                iterations=iterations,
            )

        return wrapper

    return decorator


# ============================================================================
# Performance Thresholds
# ============================================================================


class PerformanceThresholds:
    """Performance budgets for different operations"""

    # Multi-pass analysis
    PASS1_BLIND_MAX_MS = 2000  # 2 seconds for simple extraction
    PASS2_CONTEXT_MAX_MS = 3000  # 3 seconds with context
    FULL_PIPELINE_SIMPLE_MAX_MS = 5000  # 5 seconds for simple email
    FULL_PIPELINE_COMPLEX_MAX_MS = 15000  # 15 seconds for complex analysis

    # Context retrieval
    CONTEXT_SEARCH_MAX_MS = 500  # 500ms for entity-based search
    SEMANTIC_SEARCH_MAX_MS = 200  # 200ms for embedding search
    CROSS_SOURCE_SEARCH_MAX_MS = 1000  # 1 second for all sources

    # Queue operations
    QUEUE_LIST_MAX_MS = 100  # 100ms for listing
    QUEUE_APPROVE_MAX_MS = 2000  # 2 seconds including enrichments

    # Notes operations
    NOTES_TREE_MAX_MS = 100  # 100ms for tree structure
    NOTES_LIST_MAX_MS = 50  # 50ms for filtered list
    NOTES_SEARCH_MAX_MS = 200  # 200ms for search


# ============================================================================
# Large Dataset Fixtures
# ============================================================================


@pytest.fixture
def large_note_dataset():
    """Generate a large dataset of mock notes (1000 notes)"""

    def _generate(count: int = 1000):
        notes = []
        note_types = ["personne", "projet", "concept", "souvenir", "reference"]
        tags = ["important", "urgent", "work", "personal", "tech", "finance"]

        for i in range(count):
            note_type = note_types[i % len(note_types)]
            note = MagicMock()
            note.id = f"note-{i:04d}"
            note.title = f"Note {i}: {note_type.capitalize()} Entry"
            note.type = note_type
            note.summary = f"This is a summary for note {i} about {note_type}"
            note.content = f"Full content of note {i}. " * 50  # ~500 chars
            note.modified_at = datetime.now(timezone.utc) - timedelta(days=i % 365)
            note.tags = [tags[i % len(tags)], tags[(i + 1) % len(tags)]]
            note.metadata = {"created_by": "test"}
            notes.append(note)

        return notes

    return _generate


@pytest.fixture
def large_event_dataset():
    """Generate a large dataset of mock events (100 events)"""

    def _generate(count: int = 100):
        events = []
        actions = ["archive", "flag", "reply", "task", "delete"]
        categories = ["work", "personal", "finance", "newsletter"]

        for i in range(count):
            event = PerceivedEvent(
                event_id=f"event-{i:04d}",
                event_type="email",
                source="imap",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                sender=Sender(
                    name=f"Sender {i}",
                    email=f"sender{i}@example.com",
                    is_known=i % 3 == 0,
                ),
                title=f"Email Subject {i}",
                content=f"Email content {i}. " * 100,  # ~1500 chars
                entities=[
                    Entity(
                        value=f"Person {i}",
                        type=person,
                        confidence=0.85,
                    ),
                    Entity(
                        value=f"2026-01-{(i % 28) + 1:02d}",
                        type=EntityType.DATE,
                        confidence=0.9,
                    ),
                ],
            )
            events.append(event)

        return events

    return _generate


@pytest.fixture
def large_extraction_dataset():
    """Generate a large dataset of mock extractions (50 extractions)"""

    def _generate(count: int = 50):
        extractions = []
        types = [
            "fait",
            "decision",
            "engagement",
            "deadline",
            "relation",
            "evenement",
            "montant",
        ]
        importances = ["haute", "moyenne", "basse"]

        for i in range(count):
            extraction = Extraction(
                info=f"Extraction {i}: Important information about the topic",
                type=types[i % len(types)],
                importance=importances[i % len(importances)],
                note_cible=f"Note Target {i % 10}",
                note_action="enrichir" if i % 2 == 0 else "creer",
                omnifocus=i % 5 == 0,
                calendar=i % 7 == 0,
                date=f"2026-01-{(i % 28) + 1:02d}" if i % 3 == 0 else None,
            )
            extractions.append(extraction)

        return extractions

    return _generate


# ============================================================================
# Mock Fixtures for Performance Tests
# ============================================================================


@pytest.fixture
def mock_ai_router_fast():
    """
    Mock AI router that returns fast responses.

    Simulates typical API latency (100-200ms) without actual API calls.
    """
    router = AsyncMock()

    async def mock_call(prompt: str, model: Any = None, **kwargs):
        # Simulate API latency
        await asyncio.sleep(0.1)  # 100ms simulated latency

        return MagicMock(
            content="""{"action": "archive", "confidence": 85, "extractions": [
                {"info": "Test fact", "type": "fait", "importance": "moyenne"}
            ], "reasoning": "Test reasoning"}""",
            tokens_used=500,
            model_id="claude-3-5-haiku",
        )

    router.call.side_effect = mock_call
    router.call_async = mock_call
    return router


@pytest.fixture
def mock_context_searcher_fast():
    """
    Mock context searcher that returns fast responses.

    Simulates typical search latency (50-100ms).
    """
    from src.sancho.context_searcher import (
        NoteContextBlock,
        StructuredContext,
    )

    searcher = AsyncMock()

    async def mock_search(entities: list[str], **kwargs):
        # Simulate search latency
        await asyncio.sleep(0.05)  # 50ms simulated latency

        return StructuredContext(
            query_entities=entities,
            sources_searched=["notes", "calendar"],
            total_results=len(entities),
            notes=[
                NoteContextBlock(
                    note_id=f"note-{i}",
                    title=f"Note for {entity}",
                    note_type="personne",
                    summary=f"Information about {entity}",
                    relevance=0.85 - (i * 0.1),
                )
                for i, entity in enumerate(entities[:3])
            ],
            calendar=[],
            tasks=[],
            emails=[],
            entity_profiles={},
            conflicts=[],
        )

    searcher.search_for_entities.side_effect = mock_search
    return searcher


@pytest.fixture
def sample_perceived_event():
    """Create a sample PerceivedEvent for testing"""
    return PerceivedEvent(
        event_id="test-event-001",
        event_type="email",
        source="imap",
        timestamp=datetime.now(timezone.utc),
        sender=Sender(
            name="Marc Dupont",
            email="marc.dupont@acme.com",
            is_known=True,
        ),
        title="Re: Budget Q1 - Validation requise",
        content="""
        Bonjour Johan,

        Suite à notre discussion de ce matin, je te confirme que le budget Q1
        de 15 000€ a été validé par la direction.

        La deadline pour la livraison du projet Alpha est fixée au 31 janvier.

        Merci de me confirmer que tu as bien reçu cette information.

        Cordialement,
        Marc Dupont
        Tech Lead - Acme Corp
        """,
        entities=[
            Entity(value="Marc Dupont", type=person, confidence=0.95),
            Entity(value="15000", type=EntityType.MONEY, confidence=0.9),
            Entity(value="2026-01-31", type=EntityType.DATE, confidence=0.85),
            Entity(value="Projet Alpha", type=EntityType.PROJECT, confidence=0.8),
        ],
    )


@pytest.fixture
def sample_pass_result():
    """Create a sample PassResult for testing"""
    return PassResult(
        pass_number=1,
        pass_type=PassType.BLIND_EXTRACTION,
        model_used="haiku",
        model_id="claude-3-5-haiku",
        extractions=[
            Extraction(
                info="Budget Q1 de 15k€ validé",
                type="decision",
                importance="haute",
                note_cible="Projet Alpha",
                note_action="enrichir",
            ),
            Extraction(
                info="Deadline projet: 31 janvier",
                type="deadline",
                importance="haute",
                note_cible="Projet Alpha",
                date="2026-01-31",
                omnifocus=True,
            ),
        ],
        action="archive",
        confidence=DecomposedConfidence.from_single_score(0.82),
        changes_made=["Initial extraction"],
        entities_discovered={"Marc Dupont", "Projet Alpha"},
        reasoning="Email de validation de budget avec deadline",
        tokens_used=450,
        duration_ms=1200,
    )


@pytest.fixture
def multi_pass_config():
    """Create a MultiPassConfig for testing"""
    return MultiPassConfig(
        max_passes=5,
        target_confidence=0.95,
        escalation_threshold_pass4=0.80,
        escalation_threshold_pass5=0.75,
        high_stakes_amount_threshold=10000,
        high_stakes_deadline_hours=48,
    )


# Import asyncio for async fixtures
import asyncio
