"""
Unit Tests for Four Valets v3.0 Architecture

Tests the Four Valets multi-pass pipeline:
- Grimaud (Pass 1) — Silent extraction
- Bazin (Pass 2) — Contextual enrichment
- Planchet (Pass 3) — Critique and validation
- Mousqueton (Pass 4) — Final arbitrage

Tests cover:
- Configuration and data models
- Pipeline routing and stopping logic
- Valet-specific behavior
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sancho.convergence import (
    DecomposedConfidence,
    Extraction,
    FourValetsConfig,
    MultiPassConfig,
    PassResult,
    PassType,
    ValetType,
)
from src.sancho.model_selector import ModelTier
from src.sancho.multi_pass_analyzer import MultiPassAnalyzer, MultiPassResult
from tests.performance.conftest import create_test_event


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def four_valets_config():
    """Default FourValetsConfig for testing"""
    return FourValetsConfig()


@pytest.fixture
def multi_pass_config():
    """MultiPassConfig with Four Valets enabled"""
    return MultiPassConfig()


@pytest.fixture
def mock_ai_router():
    """Mock AI router for testing"""
    router = MagicMock()
    return router


@pytest.fixture
def mock_template_renderer():
    """Mock template renderer with Four Valets methods"""
    renderer = MagicMock()
    renderer.render_grimaud.return_value = "Grimaud prompt"
    renderer.render_bazin.return_value = "Bazin prompt"
    renderer.render_planchet.return_value = "Planchet prompt"
    renderer.render_mousqueton.return_value = "Mousqueton prompt"
    renderer._get_briefing.return_value = ""
    return renderer


@pytest.fixture
def sample_event():
    """Create a sample PerceivedEvent for testing"""
    return create_test_event(
        event_id="test-four-valets-001",
        title="Test Email for Four Valets",
        content="This is a test email with important information.",
        from_person="test@example.com",
    )


@pytest.fixture
def grimaud_result():
    """Sample PassResult from Grimaud (Pass 1)"""
    return PassResult(
        pass_number=1,
        pass_type=PassType.GRIMAUD,
        model_used="haiku",
        model_id="claude-3-haiku-20240307",
        extractions=[
            Extraction(
                info="Test fact extracted by Grimaud",
                type="fait",
                importance="moyenne",
            )
        ],
        action="archive",
        confidence=DecomposedConfidence(
            entity_confidence=0.9,
            action_confidence=0.85,
            extraction_confidence=0.88,
            completeness=0.87,
        ),
        entities_discovered={"Test Person"},
        valet=ValetType.GRIMAUD,
        early_stop=False,
        needs_mousqueton=True,
    )


@pytest.fixture
def grimaud_early_stop_result():
    """Grimaud result requesting early stop (ephemeral content)"""
    return PassResult(
        pass_number=1,
        pass_type=PassType.GRIMAUD,
        model_used="haiku",
        model_id="claude-3-haiku-20240307",
        extractions=[],
        action="delete",
        confidence=DecomposedConfidence(
            entity_confidence=0.98,
            action_confidence=0.97,
            extraction_confidence=0.96,
            completeness=0.99,
        ),
        entities_discovered=set(),
        valet=ValetType.GRIMAUD,
        early_stop=True,
        early_stop_reason="OTP verification code - ephemeral content",
        needs_mousqueton=False,
    )


@pytest.fixture
def planchet_confident_result():
    """Planchet result that can conclude without Mousqueton"""
    return PassResult(
        pass_number=3,
        pass_type=PassType.PLANCHET,
        model_used="haiku",
        model_id="claude-3-haiku-20240307",
        extractions=[
            Extraction(
                info="Validated fact by Planchet",
                type="fait",
                importance="moyenne",
                note_cible="Test Note",
            )
        ],
        action="archive",
        confidence=DecomposedConfidence(
            entity_confidence=0.95,
            action_confidence=0.92,
            extraction_confidence=0.94,
            completeness=0.93,
        ),
        entities_discovered={"Test Person"},
        valet=ValetType.PLANCHET,
        early_stop=False,
        needs_mousqueton=False,
        critique={"validation": "approved", "confidence_boost": 0.05},
    )


@pytest.fixture
def planchet_needs_mousqueton_result():
    """Planchet result that needs Mousqueton arbitrage"""
    return PassResult(
        pass_number=3,
        pass_type=PassType.PLANCHET,
        model_used="haiku",
        model_id="claude-3-haiku-20240307",
        extractions=[
            Extraction(
                info="Uncertain fact needing arbitrage",
                type="decision",
                importance="haute",
            )
        ],
        action="queue",
        confidence=DecomposedConfidence(
            entity_confidence=0.75,
            action_confidence=0.70,
            extraction_confidence=0.72,
            completeness=0.78,
        ),
        entities_discovered={"Test Person", "Unknown Entity"},
        valet=ValetType.PLANCHET,
        early_stop=False,
        needs_mousqueton=True,
        critique={"issues": ["Low action confidence", "Entity ambiguity"]},
    )


# ============================================================================
# Configuration Tests
# ============================================================================


class TestFourValetsConfig:
    """Tests for FourValetsConfig dataclass"""

    def test_default_values(self, four_valets_config):
        """Test default configuration values"""
        assert four_valets_config.enabled is True
        assert four_valets_config.grimaud_max_chars == 8000
        assert four_valets_config.bazin_max_chars == 4000
        assert four_valets_config.bazin_max_notes == 5
        assert four_valets_config.planchet_max_chars == 4000

    def test_stopping_rules(self, four_valets_config):
        """Test stopping rule thresholds"""
        assert four_valets_config.grimaud_early_stop_confidence == 0.95
        assert four_valets_config.planchet_stop_confidence == 0.90
        assert four_valets_config.mousqueton_queue_confidence == 0.90

    def test_default_models(self, four_valets_config):
        """Test default model assignments per valet"""
        assert four_valets_config.models["grimaud"] == "haiku"
        assert four_valets_config.models["bazin"] == "haiku"
        assert four_valets_config.models["planchet"] == "haiku"
        assert four_valets_config.models["mousqueton"] == "sonnet"

    def test_api_params(self, four_valets_config):
        """Test API parameters per valet"""
        assert four_valets_config.api_params["grimaud"]["temperature"] == 0.1
        assert four_valets_config.api_params["mousqueton"]["max_tokens"] == 2500

    def test_fallback_enabled(self, four_valets_config):
        """Test fallback to legacy is enabled by default"""
        assert four_valets_config.fallback_to_legacy is True


class TestMultiPassConfigIntegration:
    """Tests for MultiPassConfig with Four Valets"""

    def test_four_valets_config_present(self, multi_pass_config):
        """Test Four Valets config is present in MultiPassConfig"""
        assert hasattr(multi_pass_config, "four_valets")
        assert isinstance(multi_pass_config.four_valets, FourValetsConfig)

    def test_four_valets_enabled_property(self, multi_pass_config):
        """Test four_valets_enabled property"""
        assert multi_pass_config.four_valets_enabled is True

    def test_four_valets_can_be_disabled(self):
        """Test Four Valets can be disabled via config"""
        config = MultiPassConfig(four_valets=FourValetsConfig(enabled=False))
        assert config.four_valets_enabled is False


# ============================================================================
# Data Model Tests
# ============================================================================


class TestValetType:
    """Tests for ValetType enum"""

    def test_valet_values(self):
        """Test all valet types have correct values"""
        assert ValetType.GRIMAUD.value == "grimaud"
        assert ValetType.BAZIN.value == "bazin"
        assert ValetType.PLANCHET.value == "planchet"
        assert ValetType.MOUSQUETON.value == "mousqueton"

    def test_valet_is_string_enum(self):
        """Test ValetType is a string enum"""
        assert isinstance(ValetType.GRIMAUD, str)
        assert ValetType.GRIMAUD == "grimaud"


class TestPassType:
    """Tests for PassType with Four Valets values"""

    def test_four_valets_pass_types_exist(self):
        """Test Four Valets pass types are defined"""
        assert PassType.GRIMAUD.value == "grimaud"
        assert PassType.BAZIN.value == "bazin"
        assert PassType.PLANCHET.value == "planchet"
        assert PassType.MOUSQUETON.value == "mousqueton"

    def test_legacy_pass_types_still_exist(self):
        """Test legacy pass types are preserved"""
        assert PassType.BLIND_EXTRACTION.value == "blind"
        assert PassType.CONTEXTUAL_REFINEMENT.value == "refine"
        assert PassType.DEEP_REASONING.value == "deep"
        assert PassType.EXPERT_ANALYSIS.value == "expert"


class TestPassResultFourValets:
    """Tests for PassResult Four Valets fields"""

    def test_four_valets_fields_present(self, grimaud_result):
        """Test Four Valets fields are present in PassResult"""
        assert hasattr(grimaud_result, "valet")
        assert hasattr(grimaud_result, "early_stop")
        assert hasattr(grimaud_result, "early_stop_reason")
        assert hasattr(grimaud_result, "needs_mousqueton")
        assert hasattr(grimaud_result, "notes_used")
        assert hasattr(grimaud_result, "notes_ignored")
        assert hasattr(grimaud_result, "critique")
        assert hasattr(grimaud_result, "arbitrage")
        assert hasattr(grimaud_result, "memory_hint")

    def test_to_dict_includes_four_valets(self, grimaud_result):
        """Test to_dict includes Four Valets fields"""
        result_dict = grimaud_result.to_dict()
        assert "valet" in result_dict
        assert result_dict["valet"] == "grimaud"
        assert "early_stop" in result_dict
        assert "needs_mousqueton" in result_dict


class TestMultiPassResultFourValets:
    """Tests for MultiPassResult Four Valets fields"""

    def test_stopped_at_field(self):
        """Test stopped_at field in MultiPassResult"""
        result = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.9),
            entities_discovered=set(),
            passes_count=3,
            total_duration_ms=1500.0,
            total_tokens=500,
            final_model="haiku",
            escalated=False,
            stopped_at="planchet",
        )
        assert result.stopped_at == "planchet"

    def test_four_valets_mode_property(self):
        """Test four_valets_mode property"""
        # With stopped_at set
        result_with = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.9),
            entities_discovered=set(),
            passes_count=3,
            total_duration_ms=1500.0,
            total_tokens=500,
            final_model="haiku",
            escalated=False,
            stopped_at="planchet",
        )
        assert result_with.four_valets_mode is True

        # Without stopped_at (legacy mode)
        result_without = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.9),
            entities_discovered=set(),
            passes_count=3,
            total_duration_ms=1500.0,
            total_tokens=500,
            final_model="haiku",
            escalated=False,
        )
        assert result_without.four_valets_mode is False

    def test_to_dict_includes_stopped_at(self):
        """Test to_dict includes stopped_at and four_valets_mode"""
        result = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.9),
            entities_discovered=set(),
            passes_count=4,
            total_duration_ms=2000.0,
            total_tokens=800,
            final_model="sonnet",
            escalated=True,
            stopped_at="mousqueton",
        )
        result_dict = result.to_dict()
        assert result_dict["stopped_at"] == "mousqueton"
        assert result_dict["four_valets_mode"] is True


# ============================================================================
# Stopping Logic Tests
# ============================================================================


class TestEarlyStopLogic:
    """Tests for _should_early_stop method"""

    def test_early_stop_with_delete_high_confidence(
        self, mock_ai_router, mock_template_renderer, grimaud_early_stop_result
    ):
        """Test early stop is triggered for delete action with high confidence"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        assert analyzer._should_early_stop(grimaud_early_stop_result) is True

    def test_no_early_stop_without_flag(
        self, mock_ai_router, mock_template_renderer, grimaud_result
    ):
        """Test no early stop when early_stop flag is False"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        assert analyzer._should_early_stop(grimaud_result) is False

    def test_no_early_stop_for_archive(
        self, mock_ai_router, mock_template_renderer, grimaud_early_stop_result
    ):
        """Test no early stop when action is archive (not delete)"""
        grimaud_early_stop_result.action = "archive"
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        assert analyzer._should_early_stop(grimaud_early_stop_result) is False

    def test_no_early_stop_low_confidence(
        self, mock_ai_router, mock_template_renderer
    ):
        """Test no early stop when confidence is below threshold"""
        result = PassResult(
            pass_number=1,
            pass_type=PassType.GRIMAUD,
            model_used="haiku",
            model_id="claude-3-haiku-20240307",
            extractions=[],
            action="delete",
            confidence=DecomposedConfidence.from_single_score(0.80),
            entities_discovered=set(),
            valet=ValetType.GRIMAUD,
            early_stop=True,
            early_stop_reason="Newsletter",
        )
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        assert analyzer._should_early_stop(result) is False


class TestPlanchetCanConclude:
    """Tests for _planchet_can_conclude method"""

    def test_planchet_concludes_when_confident(
        self, mock_ai_router, mock_template_renderer, planchet_confident_result
    ):
        """Test Planchet can conclude with high confidence and no Mousqueton needed"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        assert analyzer._planchet_can_conclude(planchet_confident_result) is True

    def test_planchet_needs_mousqueton(
        self, mock_ai_router, mock_template_renderer, planchet_needs_mousqueton_result
    ):
        """Test Planchet cannot conclude when needs_mousqueton is True"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        assert analyzer._planchet_can_conclude(planchet_needs_mousqueton_result) is False

    def test_planchet_low_confidence_needs_mousqueton(
        self, mock_ai_router, mock_template_renderer
    ):
        """Test Planchet cannot conclude even with needs_mousqueton=False if low confidence"""
        result = PassResult(
            pass_number=3,
            pass_type=PassType.PLANCHET,
            model_used="haiku",
            model_id="claude-3-haiku-20240307",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.85),  # Below 0.90
            entities_discovered=set(),
            valet=ValetType.PLANCHET,
            needs_mousqueton=False,
        )
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        assert analyzer._planchet_can_conclude(result) is False


# ============================================================================
# Model Selection Tests
# ============================================================================


class TestGetValetModel:
    """Tests for _get_valet_model method"""

    def test_get_grimaud_model(self, mock_ai_router, mock_template_renderer):
        """Test getting model for Grimaud"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        model = analyzer._get_valet_model("grimaud")
        assert model == ModelTier.HAIKU

    def test_get_mousqueton_model(self, mock_ai_router, mock_template_renderer):
        """Test getting model for Mousqueton (Sonnet by default)"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        model = analyzer._get_valet_model("mousqueton")
        assert model == ModelTier.SONNET

    def test_get_unknown_valet_defaults_to_haiku(
        self, mock_ai_router, mock_template_renderer
    ):
        """Test unknown valet defaults to Haiku"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )
        model = analyzer._get_valet_model("unknown")
        assert model == ModelTier.HAIKU


# ============================================================================
# Pipeline Routing Tests
# ============================================================================


class TestPipelineRouting:
    """Tests for analyze() pipeline routing"""

    @pytest.mark.asyncio
    async def test_four_valets_routing_when_enabled(
        self, mock_ai_router, mock_template_renderer, sample_event
    ):
        """Test analyze routes to Four Valets when enabled"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )

        # Mock _run_four_valets_pipeline to verify it's called
        with patch.object(
            analyzer, "_run_four_valets_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            mock_pipeline.return_value = MultiPassResult(
                extractions=[],
                action="archive",
                confidence=DecomposedConfidence.from_single_score(0.9),
                entities_discovered=set(),
                passes_count=3,
                total_duration_ms=1000.0,
                total_tokens=300,
                final_model="haiku",
                escalated=False,
                stopped_at="planchet",
            )

            result = await analyzer.analyze(sample_event, use_four_valets=True)

            mock_pipeline.assert_called_once()
            assert result.four_valets_mode is True

    @pytest.mark.asyncio
    async def test_legacy_routing_when_disabled(
        self, mock_ai_router, mock_template_renderer, sample_event
    ):
        """Test analyze routes to legacy when Four Valets disabled"""
        config = MultiPassConfig(four_valets=FourValetsConfig(enabled=False))
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
            config=config,
        )

        # Mock _run_pass1 (legacy path)
        with patch.object(
            analyzer, "_run_pass1", new_callable=AsyncMock
        ) as mock_pass1:
            mock_pass1.return_value = PassResult(
                pass_number=1,
                pass_type=PassType.BLIND_EXTRACTION,
                model_used="haiku",
                model_id="claude-3-haiku-20240307",
                extractions=[],
                action="archive",
                confidence=DecomposedConfidence.from_single_score(0.96),
                entities_discovered=set(),
            )

            # Also mock _build_result
            with patch.object(
                analyzer, "_build_result", new_callable=AsyncMock
            ) as mock_build:
                mock_build.return_value = MultiPassResult(
                    extractions=[],
                    action="archive",
                    confidence=DecomposedConfidence.from_single_score(0.96),
                    entities_discovered=set(),
                    passes_count=1,
                    total_duration_ms=500.0,
                    total_tokens=150,
                    final_model="haiku",
                    escalated=False,
                )

                result = await analyzer.analyze(sample_event, use_four_valets=True)

                mock_pass1.assert_called_once()
                assert result.four_valets_mode is False

    @pytest.mark.asyncio
    async def test_fallback_on_four_valets_error(
        self, mock_ai_router, mock_template_renderer, sample_event
    ):
        """Test fallback to legacy when Four Valets fails"""
        analyzer = MultiPassAnalyzer(
            ai_router=mock_ai_router,
            template_renderer=mock_template_renderer,
        )

        # Make Four Valets fail
        with patch.object(
            analyzer,
            "_run_four_valets_pipeline",
            side_effect=Exception("Four Valets error"),
        ):
            # Mock legacy path
            with patch.object(
                analyzer, "_run_pass1", new_callable=AsyncMock
            ) as mock_pass1:
                mock_pass1.return_value = PassResult(
                    pass_number=1,
                    pass_type=PassType.BLIND_EXTRACTION,
                    model_used="haiku",
                    model_id="claude-3-haiku-20240307",
                    extractions=[],
                    action="archive",
                    confidence=DecomposedConfidence.from_single_score(0.96),
                    entities_discovered=set(),
                )

                with patch.object(
                    analyzer, "_build_result", new_callable=AsyncMock
                ) as mock_build:
                    mock_build.return_value = MultiPassResult(
                        extractions=[],
                        action="archive",
                        confidence=DecomposedConfidence.from_single_score(0.96),
                        entities_discovered=set(),
                        passes_count=1,
                        total_duration_ms=500.0,
                        total_tokens=150,
                        final_model="haiku",
                        escalated=False,
                    )

                    result = await analyzer.analyze(sample_event)

                    # Fallback should use legacy
                    mock_pass1.assert_called_once()
