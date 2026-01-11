"""
Integration tests for Multi-Pass v2.2 Analysis System

Tests the full integration of:
- MultiPassAnalyzer orchestration
- ContextSearcher coordination
- TemplateRenderer rendering
- Convergence logic
- Model escalation
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.events.universal_event import Entity
from src.sancho.context_searcher import (
    ContextSearchConfig,
    ContextSearcher,
    NoteContextBlock,
    StructuredContext,
)
from src.sancho.convergence import (
    AnalysisContext,
    DecomposedConfidence,
    Extraction,
    MultiPassConfig,
    PassResult,
    PassType,
    is_high_stakes,
    select_model,
    should_stop,
)
from src.sancho.model_selector import ModelTier
from src.sancho.template_renderer import TemplateRenderer


class TestMultiPassConvergence:
    """Test convergence behavior across multiple passes"""

    def test_high_confidence_stops_early(self):
        """Analysis stops when confidence >= 95%"""
        config = MultiPassConfig()

        # Pass 1 with high confidence
        pass1 = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="claude-3-5-haiku",
            extractions=[
                Extraction(
                    info="Marc sera en réunion lundi",
                    type="evenement",
                    importance="haute",
                )
            ],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.96),
            changes_made=["Initial extraction"],
        )

        stop, reason = should_stop(pass1, None, config)
        assert stop is True
        assert "confidence" in reason

    def test_escalation_path_haiku_to_sonnet(self):
        """Model escalates from Haiku to Sonnet at pass 4"""
        config = MultiPassConfig()
        context = AnalysisContext()

        # Pass 1-3: Haiku
        for pass_num in [1, 2, 3]:
            tier, _ = select_model(pass_num, 0.70, context, config)
            assert tier == ModelTier.HAIKU

        # Pass 4: Should escalate to Sonnet if confidence < 80%
        tier, reason = select_model(4, 0.70, context, config)
        assert tier == ModelTier.SONNET
        assert reason == "low_confidence"

    def test_escalation_path_sonnet_to_opus(self):
        """Model escalates from Sonnet to Opus at pass 5"""
        config = MultiPassConfig()
        context = AnalysisContext()

        # Pass 5: Should escalate to Opus if confidence < 75%
        tier, _ = select_model(5, 0.70, context, config)
        assert tier == ModelTier.OPUS

    def test_high_stakes_triggers_opus(self):
        """High stakes content triggers Opus escalation"""
        config = MultiPassConfig()
        context = AnalysisContext(high_stakes=True)

        # Even at pass 5 with good confidence, high stakes triggers Opus
        tier, _ = select_model(5, 0.80, context, config)
        assert tier == ModelTier.OPUS

    def test_no_changes_stops_iteration(self):
        """Analysis stops when no changes between passes"""
        config = MultiPassConfig()

        pass1 = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="test",
            extractions=[Extraction(info="Fact 1", type="fait", importance="moyenne")],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.80),
            changes_made=["Initial extraction"],
        )

        pass2 = PassResult(
            pass_number=2,
            pass_type=PassType.CONTEXTUAL_REFINEMENT,
            model_used="haiku",
            model_id="test",
            extractions=[Extraction(info="Fact 1", type="fait", importance="moyenne")],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.80),
            changes_made=[],  # No changes
        )

        stop, reason = should_stop(pass2, pass1, config)
        assert stop is True
        assert "change" in reason.lower()


class TestContextSearchIntegration:
    """Test ContextSearcher integration with NoteManager"""

    @pytest.mark.asyncio
    async def test_search_with_note_manager_builds_profiles(self):
        """ContextSearcher builds entity profiles from notes"""
        # Mock NoteManager
        mock_note_manager = MagicMock()
        mock_note = MagicMock()
        mock_note.id = "note-marc"
        mock_note.title = "Marc Dupont"
        mock_note.type = "personne"
        mock_note.summary = "Tech Lead chez Acme"
        mock_note.content = "Marc est le Tech Lead.\n[[Projet Alpha]]\nExpert Python."
        mock_note.modified_at = datetime.now()
        mock_note.tags = ["important"]
        mock_note.metadata = {"role": "Tech Lead"}

        mock_note_manager.search_notes.return_value = [(mock_note, 0.9)]

        searcher = ContextSearcher(note_manager=mock_note_manager)
        config = ContextSearchConfig(max_notes=5, min_relevance=0.3)
        context = await searcher.search_for_entities(["Marc Dupont"], config=config)

        assert "notes" in context.sources_searched
        assert len(context.notes) == 1
        assert context.notes[0].title == "Marc Dupont"
        assert "Marc Dupont" in context.entity_profiles
        assert context.entity_profiles["Marc Dupont"].role == "Tech Lead"

    @pytest.mark.asyncio
    async def test_context_to_prompt_format(self):
        """StructuredContext generates valid prompt format"""
        context = StructuredContext(
            query_entities=["Marc Dupont"],
            search_timestamp=datetime.now(),
            sources_searched=["notes"],
            notes=[
                NoteContextBlock(
                    note_id="n1",
                    title="Marc Dupont",
                    note_type="personne",
                    summary="Tech Lead chez Acme",
                    relevance=0.9,
                )
            ],
        )

        prompt = context.to_prompt_format()
        assert "Notes PKM Pertinentes" in prompt
        assert "Marc Dupont" in prompt
        assert "Tech Lead" in prompt


class TestTemplateIntegration:
    """Test template rendering integration"""

    def test_pass1_template_produces_valid_prompt(self):
        """Pass 1 template produces a prompt with required sections"""
        renderer = TemplateRenderer()

        # Create realistic event using mock to match template expectations
        mock_event = MagicMock()
        mock_event.title = "Réunion projet Alpha lundi"
        mock_event.content = "Bonjour,\n\nJe confirme notre réunion lundi 15h pour le projet Alpha.\n\nMarc"
        mock_event.timestamp = datetime.now().isoformat()
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.display_name = "Marc Dupont"
        mock_event.sender.email = "marc@example.com"
        mock_event.entities = [
            Entity(type="person", value="Marc Dupont", confidence=0.9),
            Entity(type="project", value="Projet Alpha", confidence=0.85),
        ]

        prompt = renderer.render_pass1(event=mock_event, max_content_chars=8000)

        # Check for required sections
        assert "EXTRACTION" in prompt
        assert "confiance" in prompt.lower()
        assert "projet alpha" in prompt.lower()

    def test_pass2_template_includes_context(self):
        """Pass 2 template includes context and previous results"""
        renderer = TemplateRenderer()

        event = MagicMock()
        event.title = "Re: Projet Alpha"
        event.content = "Ok pour lundi"
        event.timestamp = "2026-01-15T10:00:00"
        event.source_type = "email"
        event.sender = MagicMock()
        event.sender.display_name = "Marc"
        event.sender.email = "marc@example.com"

        previous_result = {
            "extractions": [{"info": "Réunion confirmée", "type": "evenement"}],
            "action": "archive",
            "confidence": {
                "entity_confidence": 0.70,
                "action_confidence": 0.75,
                "extraction_confidence": 0.80,
                "completeness": 0.65,
                "overall": 0.65,
            },
            "entities_discovered": ["Marc Dupont"],
        }

        mock_context = MagicMock()
        mock_context.to_prompt_format.return_value = (
            "### Profils\n**Marc Dupont** - Tech Lead"
        )
        mock_context.is_empty = False

        prompt = renderer.render_pass2(
            event=event,
            previous_result=previous_result,
            context=mock_context,
            max_content_chars=8000,
        )

        assert "context" in prompt.lower() or "CONTEXTE" in prompt


class TestHighStakesDetection:
    """Test high stakes detection logic"""

    def test_large_amount_is_high_stakes(self):
        """Amounts > 10k are high stakes"""
        config = MultiPassConfig()
        extractions = [
            Extraction(
                info="50 000 €",
                type="montant",
                importance="haute",
            )
        ]
        context = AnalysisContext()

        assert is_high_stakes(extractions, context, config) is True

    def test_vip_sender_is_high_stakes(self):
        """VIP sender is high stakes"""
        config = MultiPassConfig()
        extractions = []
        context = AnalysisContext(sender_importance="vip")

        assert is_high_stakes(extractions, context, config) is True

    def test_critical_decision_is_high_stakes(self):
        """High importance decision is high stakes"""
        config = MultiPassConfig()
        extractions = [
            Extraction(
                info="Validation du budget annuel",
                type="decision",
                importance="haute",
            )
        ]
        context = AnalysisContext()

        assert is_high_stakes(extractions, context, config) is True

    def test_routine_email_not_high_stakes(self):
        """Routine emails are not high stakes"""
        config = MultiPassConfig()
        extractions = [
            Extraction(
                info="Newsletter hebdomadaire",
                type="fait",
                importance="basse",
            )
        ]
        context = AnalysisContext()

        assert is_high_stakes(extractions, context, config) is False


class TestDecomposedConfidenceIntegration:
    """Test confidence decomposition across passes"""

    def test_weakest_dimension_drives_overall(self):
        """Overall confidence equals weakest dimension"""
        conf = DecomposedConfidence(
            entity_confidence=0.95,
            action_confidence=0.90,
            extraction_confidence=0.85,
            completeness=0.60,  # Weakest
        )

        assert conf.overall == 0.60
        dim, score = conf.weakest_dimension
        assert dim == "completeness"
        assert score == 0.60

    def test_needs_improvement_identifies_weak_dimensions(self):
        """needs_improvement identifies dimensions below threshold"""
        conf = DecomposedConfidence(
            entity_confidence=0.90,
            action_confidence=0.70,  # Below 0.85
            extraction_confidence=0.88,
            completeness=0.75,  # Below 0.85
        )

        weak = conf.needs_improvement(threshold=0.85)
        assert "action" in weak
        assert "completeness" in weak
        assert "entity" not in weak
        assert "extraction" not in weak

    def test_from_single_score_uniform_distribution(self):
        """from_single_score creates uniform confidence"""
        conf = DecomposedConfidence.from_single_score(0.80)

        assert conf.entity_confidence == 0.80
        assert conf.action_confidence == 0.80
        assert conf.extraction_confidence == 0.80
        assert conf.completeness == 0.80
        assert conf.overall == 0.80


class TestPassResultSerialization:
    """Test PassResult serialization for logging/API"""

    def test_to_dict_includes_all_fields(self):
        """to_dict includes all pass result fields"""
        result = PassResult(
            pass_number=2,
            pass_type=PassType.CONTEXTUAL_REFINEMENT,
            model_used="haiku",
            model_id="claude-3-5-haiku",
            extractions=[
                Extraction(
                    info="Marc confirme la réunion",
                    type="evenement",
                    importance="haute",
                    note_cible="Marc Dupont",
                    calendar=True,
                    date="2026-01-20",
                    time="15:00",
                )
            ],
            action="flag",
            confidence=DecomposedConfidence(
                entity_confidence=0.85,
                action_confidence=0.80,
                extraction_confidence=0.90,
                completeness=0.75,
            ),
            entities_discovered={"Marc Dupont", "Projet Alpha"},
            changes_made=["Added calendar event", "Resolved entity"],
            reasoning="High confidence after context enrichment",
            tokens_used=1234,
            duration_ms=456.78,
        )

        d = result.to_dict()

        assert d["pass_number"] == 2
        assert d["pass_type"] == "refine"
        assert d["model_used"] == "haiku"
        assert len(d["extractions"]) == 1
        assert d["extractions"][0]["calendar"] is True
        assert d["action"] == "flag"
        assert d["confidence"]["overall"] == 0.75
        assert "Marc Dupont" in d["entities_discovered"]
        assert len(d["changes_made"]) == 2
        assert d["tokens_used"] == 1234


class TestEndToEndScenarios:
    """End-to-end scenario tests"""

    def test_simple_email_converges_fast(self):
        """Simple newsletter converges in 1 pass"""
        config = MultiPassConfig()

        # Simple newsletter - high confidence on first pass
        pass1 = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="test",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.95),
            changes_made=["Initial extraction"],
        )

        stop, _ = should_stop(pass1, None, config)
        assert stop is True

    def test_complex_email_needs_escalation(self):
        """Complex email with low confidence needs escalation"""
        config = MultiPassConfig()
        context = AnalysisContext()

        # Complex email - low confidence after 3 passes
        pass3_conf = DecomposedConfidence(
            entity_confidence=0.65,
            action_confidence=0.60,
            extraction_confidence=0.70,
            completeness=0.55,
        )

        pass3 = PassResult(
            pass_number=3,
            pass_type=PassType.CONTEXTUAL_REFINEMENT,
            model_used="haiku",
            model_id="test",
            extractions=[Extraction(info="Unclear", type="fait", importance="moyenne")],
            action="queue",
            confidence=pass3_conf,
            changes_made=["Minor clarification"],
        )

        # Should not stop at pass 3 with low confidence
        stop, _ = should_stop(pass3, None, config)
        assert stop is False

        # Pass 4 should escalate to Sonnet
        tier, _ = select_model(4, pass3_conf.overall, context, config)
        assert tier == ModelTier.SONNET

    def test_vip_email_always_gets_opus(self):
        """VIP sender always triggers Opus for pass 5"""
        config = MultiPassConfig()
        context = AnalysisContext(sender_importance="vip", high_stakes=True)

        # Even with decent confidence, VIP gets Opus
        tier, reason = select_model(5, 0.80, context, config)
        assert tier == ModelTier.OPUS
        assert "high_stakes" in reason
