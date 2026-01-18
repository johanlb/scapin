"""
Unit Tests for MultiPassAnalyzer Orchestration

Tests the core orchestration logic of the multi-pass analyzer:
- Pass iteration and loop control
- Model escalation decisions
- Context integration
- Convergence detection
- Result building with context transparency (v2.2.2)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.events.universal_event import Entity
from src.sancho.context_searcher import (
    EntityProfile,
    NoteContextBlock,
    StructuredContext,
)
from src.sancho.convergence import (
    DecomposedConfidence,
    Extraction,
    MultiPassConfig,
    PassResult,
    PassType,
)
from src.sancho.model_selector import ModelTier
from src.sancho.multi_pass_analyzer import (
    APICallError,
    MultiPassAnalyzer,
    MultiPassAnalyzerError,
    MultiPassResult,
    ParseError,
)
from tests.performance.conftest import create_test_event

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_ai_router():
    """Mock AI router for testing"""
    router = AsyncMock()
    return router


@pytest.fixture
def mock_context_searcher():
    """Mock context searcher for testing"""
    searcher = AsyncMock()
    return searcher


@pytest.fixture
def mock_template_renderer():
    """Mock template renderer for testing"""
    renderer = MagicMock()
    renderer.render_pass1.return_value = "Pass 1 prompt"
    renderer.render_pass2.return_value = "Pass 2 prompt"
    renderer.render_pass4.return_value = "Pass 4 prompt"
    return renderer


@pytest.fixture
def sample_event():
    """Create a sample PerceivedEvent"""
    return create_test_event(
        event_id="test-001",
        title="Test Email Subject",
        content="Test email content with important information.",
        from_person="test@example.com",
        entities=[
            Entity(value="Test Person", type="person", confidence=0.9),
        ],
    )


@pytest.fixture
def high_confidence_response():
    """AI response with high confidence (should stop early) - returns tuple (content, usage)"""
    content = """{
        "action": "archive",
        "confidence": 96,
        "extractions": [
            {"info": "Test fact", "type": "fait", "importance": "moyenne"}
        ],
        "reasoning": "Clear and simple email"
    }"""
    usage = {"input_tokens": 100, "output_tokens": 200}
    return (content, usage)


@pytest.fixture
def low_confidence_response():
    """AI response with low confidence (should continue) - returns tuple (content, usage)"""
    content = """{
        "action": "flag",
        "confidence": 65,
        "extractions": [
            {"info": "Unclear fact", "type": "fait", "importance": "moyenne"}
        ],
        "reasoning": "Need more context"
    }"""
    usage = {"input_tokens": 150, "output_tokens": 200}
    return (content, usage)


@pytest.fixture
def medium_confidence_response():
    """AI response with medium confidence - returns tuple (content, usage)"""
    content = """{
        "action": "archive",
        "confidence": 82,
        "extractions": [
            {"info": "Budget validé", "type": "decision", "importance": "haute"}
        ],
        "reasoning": "Budget confirmation email",
        "context_influence": {
            "notes_used": ["Marc Dupont"],
            "explanation": "La note confirme le rôle de Marc",
            "confirmations": ["Marc est Tech Lead"],
            "contradictions": [],
            "missing_info": []
        }
    }"""
    usage = {"input_tokens": 200, "output_tokens": 200}
    return (content, usage)


@pytest.fixture
def sample_context():
    """Create sample structured context"""
    from datetime import datetime, timezone

    return StructuredContext(
        query_entities=["Marc Dupont", "Projet Alpha"],
        search_timestamp=datetime.now(timezone.utc),
        sources_searched=["notes", "calendar"],
        notes=[
            NoteContextBlock(
                note_id="note-marc",
                title="Marc Dupont",
                note_type="personne",
                summary="Tech Lead chez Acme Corp",
                relevance=0.92,
                tags=["contact", "tech"],
            ),
            NoteContextBlock(
                note_id="note-alpha",
                title="Projet Alpha",
                note_type="projet",
                summary="Projet de développement Q1",
                relevance=0.85,
                tags=["projet", "2026"],
            ),
        ],
        calendar=[],
        tasks=[],
        emails=[],
        entity_profiles={
            "Marc Dupont": EntityProfile(
                name="Marc Dupont",
                canonical_name="Marc Dupont",
                entity_type="person",
                role="Tech Lead",
                relationship="Contact professionnel",
            )
        },
        conflicts=[],
    )


# ============================================================================
# Initialization Tests
# ============================================================================


class TestMultiPassAnalyzerInit:
    """Test MultiPassAnalyzer initialization"""

    def test_init_with_minimal_args(self, mock_ai_router):
        """Analyzer can be created with just AI router"""
        analyzer = MultiPassAnalyzer(ai_router=mock_ai_router)

        assert analyzer.ai_router is mock_ai_router
        assert analyzer._context_searcher is None
        assert analyzer.config is not None
        assert analyzer.config.max_passes == 5

    def test_init_with_all_args(
        self, mock_ai_router, mock_context_searcher, mock_template_renderer
    ):
        """Analyzer can be created with all arguments"""
        config = MultiPassConfig(max_passes=3)

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            context_searcher=mock_context_searcher,
            template_renderer=mock_template_renderer,
            config=config,
        )

        assert analyzer.context_searcher is mock_context_searcher
        assert analyzer.config.max_passes == 3

    def test_template_renderer_lazy_load(self, mock_ai_router):
        """Template renderer is lazily loaded if not provided"""
        analyzer = MultiPassAnalyzer(ai_router=mock_ai_router)

        # Access should trigger lazy load
        renderer = analyzer.template_renderer
        assert renderer is not None

    def test_coherence_service_disabled(self, mock_ai_router):
        """Coherence service is None when disabled"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            enable_coherence_pass=False,
        )

        assert analyzer.coherence_service is None


# ============================================================================
# Pass Execution Tests
# ============================================================================


class TestPassExecution:
    """Test individual pass execution"""

    @pytest.mark.asyncio
    async def test_pass1_blind_extraction(
        self, mock_ai_router, mock_template_renderer, sample_event, high_confidence_response
    ):
        """Pass 1 runs blind extraction without context"""
        mock_ai_router._call_claude = MagicMock(return_value=high_confidence_response)

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )

        result = await analyzer._run_pass1(sample_event)

        assert result.pass_number == 1
        assert result.pass_type == PassType.BLIND_EXTRACTION
        assert result.model_used == "haiku"
        mock_template_renderer.render_pass1.assert_called_once()

    @pytest.mark.asyncio
    async def test_pass2_with_context(
        self,
        mock_ai_router,
        mock_template_renderer,
        sample_event,
        medium_confidence_response,
        sample_context,
    ):
        """Pass 2 uses context for refinement"""
        mock_ai_router._call_claude = MagicMock(return_value=medium_confidence_response)

        # Create a previous pass result
        previous = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="test",
            extractions=[],
            action="flag",
            confidence=DecomposedConfidence.from_single_score(0.70),
            changes_made=["Initial"],
        )

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )

        result = await analyzer._run_pass2(
            sample_event,
            previous,
            sample_context,
            pass_number=2,
            model_tier=ModelTier.HAIKU,
        )

        assert result.pass_number == 2
        assert result.pass_type == PassType.CONTEXTUAL_REFINEMENT
        mock_template_renderer.render_pass2.assert_called_once()

    @pytest.mark.asyncio
    async def test_pass4_deep_reasoning(
        self,
        mock_ai_router,
        mock_template_renderer,
        sample_event,
        medium_confidence_response,
        sample_context,
    ):
        """Pass 4 uses Sonnet for deep reasoning"""
        mock_ai_router._call_claude = MagicMock(return_value=medium_confidence_response)

        pass_history = [
            PassResult(
                pass_number=i,
                pass_type=PassType.BLIND_EXTRACTION,
                model_used="haiku",
                model_id="test",
                extractions=[],
                action="flag",
                confidence=DecomposedConfidence.from_single_score(0.70),
                changes_made=[],
            )
            for i in range(1, 4)
        ]

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )

        result = await analyzer._run_pass4(
            sample_event,
            pass_history,
            sample_context,
            pass_number=4,
            model_tier=ModelTier.SONNET,
        )

        assert result.pass_number == 4
        assert result.pass_type == PassType.DEEP_REASONING
        mock_template_renderer.render_pass4.assert_called_once()


# ============================================================================
# Orchestration Tests
# ============================================================================


class TestOrchestration:
    """Test the full analysis orchestration"""

    @pytest.mark.skip(reason="Requires comprehensive mocking of coherence pass - TODO refactor")
    @pytest.mark.asyncio
    async def test_early_stop_high_confidence(
        self, mock_ai_router, mock_template_renderer, sample_event, high_confidence_response
    ):
        """Analysis stops early when Pass 1 achieves high confidence"""
        mock_ai_router._call_claude = MagicMock(return_value=high_confidence_response)

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(sample_event)

        assert result.passes_count == 1
        assert "confidence" in result.stop_reason
        assert result.escalated is False

    @pytest.mark.skip(reason="Requires comprehensive mocking of context searcher - TODO refactor")
    @pytest.mark.asyncio
    async def test_context_retrieval_after_pass1(
        self,
        mock_ai_router,
        mock_context_searcher,
        mock_template_renderer,
        sample_event,
        low_confidence_response,
        medium_confidence_response,
        sample_context,
    ):
        """Context is retrieved after Pass 1 if not converged"""
        # Pass 1: low confidence, Pass 2: high enough to stop
        mock_ai_router._call_claude = MagicMock(side_effect=[
            low_confidence_response,
            (
                '{"action": "archive", "confidence": 95, "extractions": [], "reasoning": "Now clear with context"}',
                {"input_tokens": 200, "output_tokens": 200},
            ),
        ])
        mock_context_searcher.search_for_entities.return_value = sample_context

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            context_searcher=mock_context_searcher,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(sample_event)

        # Context should have been searched
        mock_context_searcher.search_for_entities.assert_called()
        assert result.passes_count >= 2

    @pytest.mark.skip(reason="Requires comprehensive mocking of multi-pass loop - TODO refactor")
    @pytest.mark.asyncio
    async def test_escalation_to_sonnet(
        self, mock_ai_router, mock_template_renderer, sample_event
    ):
        """Model escalates to Sonnet at Pass 4 if confidence stays low"""
        # All passes return low confidence
        low_response = (
            '{"action": "flag", "confidence": 65, "extractions": [], "reasoning": "Still uncertain"}',
            {"input_tokens": 150, "output_tokens": 150},
        )

        sonnet_response = (
            '{"action": "archive", "confidence": 92, "extractions": [], "reasoning": "Now clear with Sonnet"}',
            {"input_tokens": 400, "output_tokens": 400},
        )

        mock_ai_router._call_claude = MagicMock(side_effect=[
            low_response,  # Pass 1
            low_response,  # Pass 2
            low_response,  # Pass 3
            sonnet_response,  # Pass 4 (Sonnet)
        ])

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(sample_event)

        assert result.escalated is True
        assert result.final_model == "sonnet"

    @pytest.mark.skip(reason="Requires comprehensive mocking of multi-pass loop - TODO refactor")
    @pytest.mark.asyncio
    async def test_max_passes_reached(self, mock_ai_router, mock_template_renderer, sample_event):
        """Analysis stops at max passes even without convergence"""
        low_response = (
            '{"action": "flag", "confidence": 70, "extractions": [{"info": "new fact", "type": "fait", "importance": "basse"}], "reasoning": "Still working on it"}',
            {"input_tokens": 150, "output_tokens": 150},
        )

        # Return same response for all passes
        mock_ai_router._call_claude = MagicMock(return_value=low_response)

        config = MultiPassConfig(max_passes=3)
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
            config=config,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(sample_event)

        assert result.passes_count == 3
        assert "max_passes" in result.stop_reason


# ============================================================================
# Context Transparency Tests (v2.2.2)
# ============================================================================


class TestContextTransparency:
    """Test context transparency features (v2.2.2)"""

    @pytest.mark.skip(reason="Requires comprehensive mocking of context searcher - TODO refactor")
    @pytest.mark.asyncio
    async def test_retrieved_context_serialized(
        self,
        mock_ai_router,
        mock_context_searcher,
        mock_template_renderer,
        sample_event,
        sample_context,
    ):
        """Retrieved context is serialized in result"""
        # Pass 1 low, Pass 2 high
        mock_ai_router._call_claude = MagicMock(side_effect=[
            (
                '{"action": "flag", "confidence": 70, "extractions": [], "reasoning": "Need context"}',
                {"input_tokens": 150, "output_tokens": 150},
            ),
            (
                '{"action": "archive", "confidence": 95, "extractions": [], "reasoning": "Clear now"}',
                {"input_tokens": 200, "output_tokens": 200},
            ),
        ])
        mock_context_searcher.search_for_entities.return_value = sample_context

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            context_searcher=mock_context_searcher,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(sample_event)

        # Check retrieved_context is populated
        assert result.retrieved_context is not None
        assert result.retrieved_context["entities_searched"] == ["Marc Dupont", "Projet Alpha"]
        assert result.retrieved_context["sources_searched"] == ["notes", "calendar"]
        assert len(result.retrieved_context["notes"]) == 2

        # Check note structure
        note = result.retrieved_context["notes"][0]
        assert note["note_id"] == "note-marc"
        assert note["title"] == "Marc Dupont"
        assert note["note_type"] == "personne"
        assert "relevance" in note

    @pytest.mark.skip(reason="Requires comprehensive mocking of context searcher - TODO refactor")
    @pytest.mark.asyncio
    async def test_context_influence_extracted(
        self,
        mock_ai_router,
        mock_context_searcher,
        mock_template_renderer,
        sample_event,
        sample_context,
    ):
        """Context influence is extracted from AI response"""
        # Pass 1 low, Pass 2 with context_influence
        mock_ai_router._call_claude = MagicMock(side_effect=[
            (
                '{"action": "flag", "confidence": 70, "extractions": [], "reasoning": "Need context"}',
                {"input_tokens": 150, "output_tokens": 150},
            ),
            (
                '{"action": "archive", "confidence": 95, "extractions": [], "reasoning": "Clear now", "context_influence": {"notes_used": ["Marc Dupont", "Projet Alpha"], "explanation": "Les notes confirment l\'identité et le projet", "confirmations": ["Marc est Tech Lead"], "contradictions": [], "missing_info": ["Budget exact non trouvé"]}}',
                {"input_tokens": 200, "output_tokens": 200},
            ),
        ])
        mock_context_searcher.search_for_entities.return_value = sample_context

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            context_searcher=mock_context_searcher,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(sample_event)

        # Check context_influence is populated
        assert result.context_influence is not None
        assert result.context_influence["notes_used"] == ["Marc Dupont", "Projet Alpha"]
        assert "confirment" in result.context_influence["explanation"]
        assert len(result.context_influence["confirmations"]) == 1
        assert len(result.context_influence["missing_info"]) == 1

    @pytest.mark.asyncio
    async def test_no_context_when_early_stop(
        self, mock_ai_router, mock_template_renderer, sample_event
    ):
        """No context data when analysis stops at Pass 1"""
        mock_ai_router._call_claude = MagicMock(return_value=(
            '{"action": "archive", "confidence": 98, "extractions": [], "reasoning": "Very clear"}',
            {"input_tokens": 100, "output_tokens": 100},
        ))

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(sample_event)

        assert result.passes_count == 1
        assert result.retrieved_context is None
        assert result.context_influence is None


# ============================================================================
# Result Building Tests
# ============================================================================


class TestResultBuilding:
    """Test MultiPassResult construction"""

    def test_result_to_dict_serialization(self):
        """MultiPassResult can be serialized to dict"""
        result = MultiPassResult(
            extractions=[
                Extraction(info="Test", type="fait", importance="moyenne"),
            ],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.90),
            entities_discovered={"Person 1", "Project A"},
            passes_count=2,
            total_duration_ms=1500.5,
            total_tokens=800,
            final_model="haiku",
            escalated=False,
            stop_reason="high_confidence",
            retrieved_context={
                "entities_searched": ["Person 1"],
                "notes": [],
            },
            context_influence={
                "notes_used": ["Note 1"],
                "explanation": "Test explanation",
            },
        )

        d = result.to_dict()

        assert d["action"] == "archive"
        assert d["passes_count"] == 2
        assert d["total_duration_ms"] == 1500.5
        assert d["retrieved_context"] is not None
        assert d["context_influence"] is not None
        assert len(d["extractions"]) == 1

    def test_result_high_confidence_property(self):
        """high_confidence property works correctly"""
        result_high = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.92),
            entities_discovered=set(),
            passes_count=1,
            total_duration_ms=1000,
            total_tokens=300,
            final_model="haiku",
            escalated=False,
        )

        result_low = MultiPassResult(
            extractions=[],
            action="flag",
            confidence=DecomposedConfidence.from_single_score(0.75),
            entities_discovered=set(),
            passes_count=3,
            total_duration_ms=3000,
            total_tokens=900,
            final_model="haiku",
            escalated=False,
        )

        assert result_high.high_confidence is True
        assert result_low.high_confidence is False


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in the analyzer"""

    @pytest.mark.asyncio
    async def test_api_error_handling(
        self, mock_ai_router, mock_template_renderer, sample_event
    ):
        """API errors are properly wrapped"""
        mock_ai_router._call_claude = MagicMock(side_effect=Exception("API connection failed"))

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )

        with pytest.raises(APICallError):
            await analyzer.analyze(sample_event)

    @pytest.mark.asyncio
    async def test_parse_error_handling(
        self, mock_ai_router, mock_template_renderer, sample_event
    ):
        """Parse errors are properly handled"""
        mock_ai_router._call_claude = MagicMock(return_value=(
            "This is not valid JSON at all",
            {"input_tokens": 50, "output_tokens": 50},
        ))

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )

        # Should handle gracefully or raise ParseError
        with pytest.raises((ParseError, MultiPassAnalyzerError)):
            await analyzer.analyze(sample_event)


# ============================================================================
# High-Stakes Detection Tests
# ============================================================================


class TestHighStakesDetection:
    """Test high-stakes detection in analysis"""

    @pytest.mark.skip(reason="Requires comprehensive mocking of coherence pass - TODO refactor")
    @pytest.mark.asyncio
    async def test_high_amount_triggers_high_stakes(
        self, mock_ai_router, mock_template_renderer
    ):
        """Large monetary amounts trigger high-stakes flag"""
        event = create_test_event(
            event_id="test-high-stakes",
            title="Contract Approval - 50,000€",
            content="Please approve the contract for 50,000€",
            from_person="cfo@company.com",
            entities=[
                Entity(value="50000", type="money", confidence=0.95),
            ],
        )

        mock_ai_router._call_claude = MagicMock(return_value=(
            """{
                "action": "flag",
                "confidence": 85,
                "extractions": [
                    {"info": "Contrat de 50k€", "type": "montant", "importance": "haute"}
                ],
                "reasoning": "Important contract"
            }""",
            {"input_tokens": 200, "output_tokens": 200},
        ))

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(event)

        assert result.high_stakes is True

    @pytest.mark.skip(reason="Requires comprehensive mocking of coherence pass - TODO refactor")
    @pytest.mark.asyncio
    async def test_vip_sender_triggers_high_stakes(
        self, mock_ai_router, mock_template_renderer
    ):
        """VIP sender triggers high-stakes flag"""
        event = create_test_event(
            event_id="test-vip",
            title="Strategic Update",
            content="Important strategic information",
            from_person="ceo@company.com",
        )

        mock_ai_router._call_claude = MagicMock(return_value=(
            '{"action": "flag", "confidence": 90, "extractions": [], "reasoning": "From CEO"}',
            {"input_tokens": 150, "output_tokens": 150},
        ))

        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
            enable_coherence_pass=False,
        )

        result = await analyzer.analyze(event, sender_importance="vip")

        assert result.high_stakes is True
