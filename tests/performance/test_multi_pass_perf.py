"""
Performance Tests for Multi-Pass Analysis Pipeline

Tests performance budgets for:
- Individual pass execution
- Full pipeline latency
- Context retrieval integration
- Model escalation scenarios
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.events.universal_event import Entity
from tests.performance.conftest import create_test_event
from src.sancho.convergence import (
    DecomposedConfidence,
    Extraction,
    MultiPassConfig,
    PassResult,
    PassType,
)
from src.sancho.model_selector import ModelTier
from tests.performance.conftest import PerformanceThresholds, measure_time


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def simple_event():
    """A simple email event that should converge quickly"""
    return create_test_event(
        event_id="simple-001",
        title="Weekly Newsletter - January 2026",
        content="This is your weekly newsletter. Read the latest updates.",
        from_person="news@example.com",
        entities=[],
    )


@pytest.fixture
def complex_event():
    """A complex email event requiring multiple passes"""
    return create_test_event(
        event_id="complex-001",
        title="Re: Budget Q1 - Urgent Decision Required",
        content="""
        Bonjour Johan,

        Suite aux discussions de ce matin avec l'équipe Finance:

        1. Le budget projet Alpha est validé à 15,000€
        2. Marie confirmera les détails techniques d'ici vendredi
        3. La deadline finale est fixée au 31 janvier

        Points en suspens:
        - Validation du scope par Pierre (en attente)
        - Confirmation de la disponibilité de l'équipe
        - Réservation de la salle pour le kickoff

        Jean m'a également mentionné que le projet Beta pourrait
        être impacté si nous dépassons le budget initial.

        Pouvez-vous confirmer que vous avez bien reçu ces informations
        et valider la prochaine étape ?

        Cordialement,
        Marc Dupont
        Tech Lead - Acme Corp
        """,
        from_person="marc.dupont@acme.com",
        entities=[
            Entity(value="Marc Dupont", type="person", confidence=0.95),
            Entity(value="Marie", type="person", confidence=0.85),
            Entity(value="Pierre", type="person", confidence=0.80),
            Entity(value="Jean", type="person", confidence=0.80),
            Entity(value="15000", type="money", confidence=0.90),
            Entity(value="2026-01-31", type="date", confidence=0.85),
            Entity(value="Projet Alpha", type="project", confidence=0.90),
            Entity(value="Projet Beta", type="project", confidence=0.75),
        ],
    )


@pytest.fixture
def mock_ai_response_fast():
    """Fast AI response (simulates ~100ms API latency)"""

    async def create_response(confidence: int, delay_ms: int = 100):
        await asyncio.sleep(delay_ms / 1000)
        return MagicMock(
            content=f"""{{"action": "archive", "confidence": {confidence},
                "extractions": [{{"info": "Test", "type": "fait", "importance": "moyenne"}}],
                "reasoning": "Test reasoning"}}""",
            tokens_used=400,
            model_id="claude-3-5-haiku",
        )

    return create_response


@pytest.fixture
def mock_context_fast():
    """Fast context retrieval (simulates ~50ms search)"""
    from src.sancho.context_searcher import NoteContextBlock, StructuredContext

    async def search_context(entities, **kwargs):
        await asyncio.sleep(0.05)  # 50ms
        return StructuredContext(
            query_entities=entities,
            sources_searched=["notes"],
            total_results=len(entities),
            notes=[
                NoteContextBlock(
                    note_id=f"note-{i}",
                    title=entity,
                    note_type="personne",
                    summary=f"Info about {entity}",
                    relevance=0.85,
                )
                for i, entity in enumerate(entities[:3])
            ],
            calendar=[],
            tasks=[],
            emails=[],
            entity_profiles={},
            conflicts=[],
        )

    return search_context


# ============================================================================
# Pass Execution Performance Tests
# ============================================================================


class TestPassExecutionPerformance:
    """Test individual pass execution performance"""

    @pytest.mark.asyncio
    async def test_pass1_latency(self, simple_event, mock_ai_response_fast):
        """Pass 1 (blind extraction) should complete within budget"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

        mock_router = AsyncMock()
        mock_router.call.return_value = await mock_ai_response_fast(confidence=95)

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            enable_coherence_pass=False,
        )

        with measure_time("pass1_blind") as metrics:
            result = await analyzer._run_pass1(simple_event)

        metrics.assert_under(
            PerformanceThresholds.PASS1_BLIND_MAX_MS,
            "Pass 1 exceeded budget",
        )

    @pytest.mark.asyncio
    async def test_pass2_with_context_latency(
        self, complex_event, mock_ai_response_fast, mock_context_fast
    ):
        """Pass 2 (contextual refinement) should complete within budget"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

        mock_router = AsyncMock()
        mock_router.call.return_value = await mock_ai_response_fast(confidence=85)

        mock_searcher = AsyncMock()
        mock_searcher.search_for_entities.side_effect = mock_context_fast

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            context_searcher=mock_searcher,
            enable_coherence_pass=False,
        )

        # Create previous pass result
        previous = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="test",
            extractions=[],
            action="flag",
            confidence=DecomposedConfidence.from_single_score(0.70),
            changes_made=["Initial"],
            entities_discovered={"Marc Dupont"},
        )

        context = await mock_context_fast(["Marc Dupont"])

        with measure_time("pass2_context") as metrics:
            result = await analyzer._run_pass2(
                complex_event,
                previous,
                context,
                pass_number=2,
                model_tier=ModelTier.HAIKU,
            )

        metrics.assert_under(
            PerformanceThresholds.PASS2_CONTEXT_MAX_MS,
            "Pass 2 exceeded budget",
        )


# ============================================================================
# Full Pipeline Performance Tests
# ============================================================================


class TestFullPipelinePerformance:
    """Test full analysis pipeline performance"""

    @pytest.mark.asyncio
    async def test_simple_email_pipeline(self, simple_event, mock_ai_response_fast):
        """Simple email should converge in 1 pass, under 5 seconds"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

        mock_router = AsyncMock()
        # High confidence on first pass - should stop early
        mock_router.call.return_value = await mock_ai_response_fast(
            confidence=96, delay_ms=200
        )

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            enable_coherence_pass=False,
        )

        with measure_time("simple_pipeline") as metrics:
            result = await analyzer.analyze(simple_event)

        assert result.passes_count == 1
        metrics.assert_under(
            PerformanceThresholds.FULL_PIPELINE_SIMPLE_MAX_MS,
            f"Simple pipeline exceeded budget ({result.passes_count} passes)",
        )

    @pytest.mark.asyncio
    async def test_complex_email_pipeline(
        self, complex_event, mock_ai_response_fast, mock_context_fast
    ):
        """Complex email pipeline should complete within budget"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

        responses = [
            await mock_ai_response_fast(confidence=70, delay_ms=200),  # Pass 1
            await mock_ai_response_fast(confidence=85, delay_ms=200),  # Pass 2
            await mock_ai_response_fast(confidence=95, delay_ms=200),  # Pass 3
        ]

        mock_router = AsyncMock()
        mock_router.call.side_effect = responses

        mock_searcher = AsyncMock()
        mock_searcher.search_for_entities.side_effect = mock_context_fast

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            context_searcher=mock_searcher,
            enable_coherence_pass=False,
        )

        with measure_time("complex_pipeline") as metrics:
            result = await analyzer.analyze(complex_event)

        assert result.passes_count <= 3
        metrics.assert_under(
            PerformanceThresholds.FULL_PIPELINE_COMPLEX_MAX_MS,
            f"Complex pipeline exceeded budget ({result.passes_count} passes)",
        )

    @pytest.mark.asyncio
    async def test_escalation_pipeline_latency(
        self, complex_event, mock_ai_response_fast, mock_context_fast
    ):
        """Pipeline with Sonnet escalation should still complete in time"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

        responses = [
            await mock_ai_response_fast(confidence=65, delay_ms=200),  # Pass 1 Haiku
            await mock_ai_response_fast(confidence=70, delay_ms=200),  # Pass 2 Haiku
            await mock_ai_response_fast(confidence=72, delay_ms=200),  # Pass 3 Haiku
            await mock_ai_response_fast(confidence=92, delay_ms=500),  # Pass 4 Sonnet
        ]

        mock_router = AsyncMock()
        mock_router.call.side_effect = responses

        mock_searcher = AsyncMock()
        mock_searcher.search_for_entities.side_effect = mock_context_fast

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            context_searcher=mock_searcher,
            enable_coherence_pass=False,
        )

        with measure_time("escalation_pipeline") as metrics:
            result = await analyzer.analyze(complex_event)

        assert result.escalated is True
        metrics.assert_under(
            PerformanceThresholds.FULL_PIPELINE_COMPLEX_MAX_MS,
            f"Escalation pipeline exceeded budget ({result.passes_count} passes)",
        )


# ============================================================================
# Context Retrieval Performance Tests
# ============================================================================


class TestContextRetrievalPerformance:
    """Test context retrieval performance"""

    @pytest.mark.asyncio
    async def test_entity_search_latency(self, mock_context_fast):
        """Entity-based context search should be fast"""
        entities = ["Marc Dupont", "Projet Alpha", "Marie"]

        with measure_time("entity_search") as metrics:
            context = await mock_context_fast(entities)

        assert context.total_results > 0
        metrics.assert_under(
            PerformanceThresholds.CONTEXT_SEARCH_MAX_MS,
            "Context search exceeded budget",
        )

    @pytest.mark.asyncio
    async def test_context_search_with_many_entities(self, mock_context_fast):
        """Context search with many entities should still be fast"""
        entities = [f"Entity_{i}" for i in range(10)]

        with measure_time("many_entities_search") as metrics:
            context = await mock_context_fast(entities)

        metrics.assert_under(
            PerformanceThresholds.CONTEXT_SEARCH_MAX_MS * 2,  # Allow 2x for many entities
            "Many entities search exceeded budget",
        )


# ============================================================================
# Throughput Tests
# ============================================================================


class TestThroughput:
    """Test processing throughput"""

    @pytest.mark.asyncio
    async def test_batch_processing_throughput(self, simple_event, mock_ai_response_fast):
        """Should be able to process multiple simple events quickly"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

        mock_router = AsyncMock()
        mock_router.call.return_value = await mock_ai_response_fast(
            confidence=95, delay_ms=100
        )

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            enable_coherence_pass=False,
        )

        # Process 5 events
        events = [simple_event for _ in range(5)]

        with measure_time("batch_5_events") as metrics:
            results = []
            for event in events:
                result = await analyzer.analyze(event)
                results.append(result)

        assert len(results) == 5
        assert all(r.passes_count == 1 for r in results)

        # Calculate throughput
        events_per_second = 5 / (metrics.duration_ms / 1000)
        assert events_per_second >= 2, f"Throughput too low: {events_per_second:.1f} events/sec"

    @pytest.mark.asyncio
    async def test_concurrent_analysis_throughput(
        self, simple_event, mock_ai_response_fast
    ):
        """Concurrent analysis should provide good throughput"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

        mock_router = AsyncMock()
        mock_router.call.return_value = await mock_ai_response_fast(
            confidence=95, delay_ms=100
        )

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            enable_coherence_pass=False,
        )

        # Process 5 events concurrently
        events = [simple_event for _ in range(5)]

        with measure_time("concurrent_5_events") as metrics:
            results = await asyncio.gather(
                *[analyzer.analyze(event) for event in events]
            )

        assert len(results) == 5

        # Concurrent should be faster than sequential
        # (limited by API latency, not CPU)
        metrics.assert_under(
            1000,  # 1 second for 5 concurrent (vs ~0.5s each sequential = 2.5s)
            "Concurrent analysis not providing expected speedup",
        )


# ============================================================================
# Memory Usage Tests (Lightweight)
# ============================================================================


class TestMemoryUsage:
    """Test memory usage patterns"""

    @pytest.mark.asyncio
    async def test_result_memory_footprint(self, complex_event, mock_ai_response_fast):
        """Result objects should have reasonable memory footprint"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer
        import sys

        mock_router = AsyncMock()
        mock_router.call.return_value = await mock_ai_response_fast(confidence=95)

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(complex_event)

        # Check result size is reasonable (< 100KB when serialized)
        result_dict = result.to_dict()
        import json

        result_json = json.dumps(result_dict)
        size_bytes = len(result_json.encode("utf-8"))

        assert size_bytes < 100_000, f"Result too large: {size_bytes} bytes"

    @pytest.mark.asyncio
    async def test_no_memory_leak_in_loop(self, simple_event, mock_ai_response_fast):
        """Multiple analyses should not leak memory"""
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer
        import gc

        mock_router = AsyncMock()
        mock_router.call.return_value = await mock_ai_response_fast(confidence=95)

        analyzer = MultiPassAnalyzer(
            ai_router=mock_router,
            enable_coherence_pass=False,
        )

        # Run garbage collection
        gc.collect()

        # Process many events
        for _ in range(20):
            result = await analyzer.analyze(simple_event)
            # Don't keep references
            del result

        gc.collect()

        # This test mainly ensures no exceptions during repeated analysis
        # Actual memory leak detection would require more sophisticated tooling
