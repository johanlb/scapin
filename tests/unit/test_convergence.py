"""
Tests for convergence.py — Multi-Pass v2.2 convergence logic

Tests cover:
- DecomposedConfidence calculations
- PassResult creation and serialization
- should_stop() convergence criteria
- select_model() escalation logic
- is_high_stakes() detection
"""


from src.sancho.convergence import (
    AnalysisContext,
    DecomposedConfidence,
    Extraction,
    MultiPassConfig,
    PassResult,
    PassType,
    get_pass_type,
    get_pass_ui_name,
    get_status_message,
    is_high_stakes,
    select_model,
    should_stop,
    targeted_escalation,
)
from src.sancho.model_selector import ModelTier


class TestDecomposedConfidence:
    """Tests for DecomposedConfidence dataclass"""

    def test_overall_returns_minimum(self):
        """Overall confidence is the minimum of all dimensions"""
        conf = DecomposedConfidence(
            entity_confidence=0.9,
            action_confidence=0.7,
            extraction_confidence=0.85,
            completeness=0.8,
        )
        assert conf.overall == 0.7  # Minimum

    def test_weakest_dimension(self):
        """weakest_dimension returns the lowest dimension"""
        conf = DecomposedConfidence(
            entity_confidence=0.9,
            action_confidence=0.7,
            extraction_confidence=0.85,
            completeness=0.8,
        )
        dim, score = conf.weakest_dimension
        assert dim == "action"
        assert score == 0.7

    def test_needs_improvement(self):
        """needs_improvement returns dimensions below threshold"""
        conf = DecomposedConfidence(
            entity_confidence=0.9,
            action_confidence=0.7,
            extraction_confidence=0.85,
            completeness=0.8,
        )
        weak = conf.needs_improvement(threshold=0.85)
        assert "action" in weak
        assert "completeness" in weak
        assert "entity" not in weak

    def test_from_single_score(self):
        """from_single_score creates uniform confidence"""
        conf = DecomposedConfidence.from_single_score(0.75)
        assert conf.entity_confidence == 0.75
        assert conf.action_confidence == 0.75
        assert conf.extraction_confidence == 0.75
        assert conf.completeness == 0.75
        assert conf.overall == 0.75

    def test_to_dict(self):
        """to_dict includes all dimensions and overall"""
        conf = DecomposedConfidence(
            entity_confidence=0.9,
            action_confidence=0.8,
            extraction_confidence=0.85,
            completeness=0.88,
        )
        d = conf.to_dict()
        assert d["entity_confidence"] == 0.9
        assert d["action_confidence"] == 0.8
        assert d["extraction_confidence"] == 0.85
        assert d["completeness"] == 0.88
        assert d["overall"] == 0.8  # Minimum


class TestPassResult:
    """Tests for PassResult dataclass"""

    def test_pass_result_creation(self):
        """PassResult can be created with required fields"""
        result = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="claude-3-haiku-20240307",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.75),
        )
        assert result.pass_number == 1
        assert result.pass_type == PassType.BLIND_EXTRACTION
        assert result.model_used == "haiku"

    def test_pass_result_to_dict(self):
        """to_dict includes all fields"""
        result = PassResult(
            pass_number=2,
            pass_type=PassType.CONTEXTUAL_REFINEMENT,
            model_used="haiku",
            model_id="claude-3-haiku-20240307",
            extractions=[
                Extraction(
                    info="Test extraction",
                    type="fait",
                    importance="haute",
                    note_cible="Test Note",
                )
            ],
            action="flag",
            confidence=DecomposedConfidence.from_single_score(0.85),
            entities_discovered={"Marc", "Projet Alpha"},
            changes_made=["Added context"],
            reasoning="Test reasoning",
        )
        d = result.to_dict()
        assert d["pass_number"] == 2
        assert d["pass_type"] == "refine"
        assert len(d["extractions"]) == 1
        assert d["action"] == "flag"
        assert "entity_confidence" in d["confidence"]


class TestShouldStop:
    """Tests for should_stop() convergence criteria"""

    def test_stop_on_high_confidence(self):
        """Stop when confidence >= 95%"""
        config = MultiPassConfig()
        current = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="test",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.96),
        )
        stop, reason = should_stop(current, None, config)
        assert stop is True
        assert "confidence" in reason.lower()

    def test_stop_on_no_changes(self):
        """Stop when no changes between passes"""
        config = MultiPassConfig()
        prev = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="test",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.85),
            changes_made=[],
        )
        current = PassResult(
            pass_number=2,
            pass_type=PassType.CONTEXTUAL_REFINEMENT,
            model_used="haiku",
            model_id="test",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.85),
            changes_made=[],  # No changes
        )
        stop, reason = should_stop(current, prev, config)
        assert stop is True
        assert "changement" in reason.lower() or "change" in reason.lower()

    def test_continue_on_low_confidence(self):
        """Continue when confidence < 95%"""
        config = MultiPassConfig()
        current = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="test",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.70),
            changes_made=["Something changed"],
        )
        stop, _ = should_stop(current, None, config)
        assert stop is False

    def test_stop_on_max_passes(self):
        """Stop when max passes reached"""
        config = MultiPassConfig(max_passes=5)
        current = PassResult(
            pass_number=5,
            pass_type=PassType.EXPERT_ANALYSIS,
            model_used="opus",
            model_id="test",
            extractions=[],
            action="queue",
            confidence=DecomposedConfidence.from_single_score(0.70),
            changes_made=["Still changing"],
        )
        stop, reason = should_stop(current, None, config)
        assert stop is True
        assert "max" in reason.lower()


class TestSelectModel:
    """Tests for select_model() escalation logic"""

    def test_haiku_for_early_passes(self):
        """Use Haiku for passes 1-3"""
        config = MultiPassConfig()
        context = AnalysisContext()

        for pass_num in [1, 2, 3]:
            tier, _ = select_model(pass_num, 0.7, context, config)
            assert tier == ModelTier.HAIKU

    def test_sonnet_escalation(self):
        """Escalate to Sonnet in pass 4 when confidence < 80%"""
        config = MultiPassConfig()
        context = AnalysisContext()

        tier, reason = select_model(4, 0.75, context, config)
        assert tier == ModelTier.SONNET
        assert reason == "low_confidence"

    def test_opus_escalation_low_confidence(self):
        """Escalate to Opus in pass 5 when confidence < 75%"""
        config = MultiPassConfig()
        context = AnalysisContext()

        tier, reason = select_model(5, 0.70, context, config)
        assert tier == ModelTier.OPUS

    def test_opus_escalation_high_stakes(self):
        """Escalate to Opus when high_stakes is True"""
        config = MultiPassConfig()
        context = AnalysisContext(high_stakes=True)

        tier, _ = select_model(5, 0.85, context, config)
        assert tier == ModelTier.OPUS


class TestIsHighStakes:
    """Tests for is_high_stakes() detection"""

    def test_high_stakes_large_amount(self):
        """Detect high stakes when amount > 10k"""
        config = MultiPassConfig()
        extractions = [
            Extraction(
                info="15 000 €",  # Amount must be parseable
                type="montant",
                importance="haute",
                note_cible="Client X",
            )
        ]
        context = AnalysisContext()

        result = is_high_stakes(extractions, context, config)
        assert result is True

    def test_high_stakes_vip_sender(self):
        """Detect high stakes when sender is VIP"""
        config = MultiPassConfig()
        extractions = []
        context = AnalysisContext(sender_importance="vip")

        result = is_high_stakes(extractions, context, config)
        assert result is True

    def test_not_high_stakes_normal(self):
        """Normal cases are not high stakes"""
        config = MultiPassConfig()
        extractions = [
            Extraction(
                info="Meeting confirmé",
                type="evenement",
                importance="moyenne",
                note_cible="Projet Y",
            )
        ]
        context = AnalysisContext()

        result = is_high_stakes(extractions, context, config)
        assert result is False


class TestPassTypeHelpers:
    """Tests for pass type helper functions"""

    def test_get_pass_type(self):
        """get_pass_type returns correct type"""
        assert get_pass_type(1) == PassType.BLIND_EXTRACTION
        assert get_pass_type(2) == PassType.CONTEXTUAL_REFINEMENT
        assert get_pass_type(3) == PassType.CONTEXTUAL_REFINEMENT
        assert get_pass_type(4) == PassType.DEEP_REASONING
        assert get_pass_type(5) == PassType.EXPERT_ANALYSIS

    def test_get_pass_ui_name(self):
        """get_pass_ui_name returns French names"""
        assert "œil" in get_pass_ui_name(1).lower() or "oeil" in get_pass_ui_name(1).lower()
        assert get_pass_ui_name(4)  # Should return something

    def test_get_status_message(self):
        """get_status_message returns messages with Sancho"""
        msg = get_status_message(1)
        assert "Sancho" in msg or "sancho" in msg.lower()


class TestTargetedEscalation:
    """Tests for targeted_escalation()"""

    def test_escalation_for_weak_entity(self):
        """Escalate when entity confidence is weak"""
        conf = DecomposedConfidence(
            entity_confidence=0.6,
            action_confidence=0.9,
            extraction_confidence=0.9,
            completeness=0.9,
        )
        strategies = targeted_escalation(conf)
        assert "entity" in strategies
        assert strategies["entity"]["action"] == "search_more_context"

    def test_no_escalation_when_strong(self):
        """No escalation needed when all dimensions are strong"""
        conf = DecomposedConfidence(
            entity_confidence=0.9,
            action_confidence=0.9,
            extraction_confidence=0.9,
            completeness=0.9,
        )
        strategies = targeted_escalation(conf)
        assert strategies == {}


class TestExtraction:
    """Tests for Extraction dataclass"""

    def test_extraction_defaults(self):
        """Extraction has sensible defaults"""
        ext = Extraction(
            info="Test info",
            type="fait",
            importance="moyenne",
        )
        assert ext.note_action == "enrichir"
        assert ext.omnifocus is False
        assert ext.calendar is False
        assert ext.date is None

    def test_extraction_all_fields(self):
        """Extraction can have all fields set"""
        ext = Extraction(
            info="Meeting with CEO",
            type="evenement",
            importance="haute",
            note_cible="CEO",
            note_action="creer",
            omnifocus=True,
            calendar=True,
            date="2026-01-15",
            time="14:00",
            timezone="Europe/Paris",
            duration=60,
        )
        assert ext.omnifocus is True
        assert ext.calendar is True
        assert ext.duration == 60
