"""
Tests pour EventAnalyzer — Workflow v2.1

Ce module teste l'analyseur d'événements avec escalade de modèle.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.core.config_manager import WorkflowV2Config

# PerceivedEvent has many required fields, so we use MagicMock in tests
from src.core.models.v2_models import (
    ContextNote,
    EmailAction,
    ExtractionType,
    ImportanceLevel,
    NoteAction,
)
from src.sancho.analyzer import (
    EventAnalyzer,
    ParseError,
    PromptRenderError,
    create_analyzer,
)
from src.sancho.router import AIModel


@pytest.fixture
def mock_router():
    """Create a mock AIRouter"""
    router = MagicMock()
    router._call_claude = MagicMock()
    return router


@pytest.fixture
def config():
    """Create a test config"""
    return WorkflowV2Config(
        enabled=True,
        default_model="haiku",
        escalation_model="sonnet",
        escalation_threshold=0.7,
        context_notes_count=3,
        context_note_max_chars=300,
        event_content_max_chars=2000,
    )


@pytest.fixture
def analyzer(mock_router, config):
    """Create an analyzer with mocked dependencies"""
    return EventAnalyzer(ai_router=mock_router, config=config)


@pytest.fixture
def sample_event():
    """Create a mock PerceivedEvent for testing"""
    event = MagicMock()
    event.event_id = "test_event_123"
    event.event_type = MagicMock()
    event.event_type.value = "information"
    event.source = "test@example.com"
    event.title = "Budget validé pour Projet Alpha"
    event.content = "Après discussion, nous validons le budget de 50k€ pour le projet Alpha. Marc s'engage à livrer le MVP pour le 15 mars."
    event.timestamp = MagicMock()
    event.timestamp.strftime = MagicMock(return_value="2026-01-11 10:00")
    event.metadata = {
        "from_name": "Jean Dupont",
        "from_address": "jean@example.com",
        "to_addresses": "team@example.com",
    }
    return event


@pytest.fixture
def sample_context_notes():
    """Create sample context notes"""
    return [
        ContextNote(
            title="Projet Alpha",
            type="projet",
            content_summary="Projet de refonte de l'application mobile...",
            relevance=0.85,
            note_id="projets/alpha",
        ),
        ContextNote(
            title="Marc Martin",
            type="personne",
            content_summary="Développeur senior, expert React...",
            relevance=0.72,
            note_id="personnes/marc",
        ),
    ]


class TestEventAnalyzerInit:
    """Tests pour l'initialisation de EventAnalyzer"""

    def test_init_with_config(self, mock_router, config):
        """Test initialisation avec config"""
        analyzer = EventAnalyzer(ai_router=mock_router, config=config)

        assert analyzer.ai_router == mock_router
        assert analyzer.config == config
        assert analyzer.config.escalation_threshold == 0.7

    def test_init_without_config(self, mock_router):
        """Test initialisation sans config (utilise defaults)"""
        analyzer = EventAnalyzer(ai_router=mock_router)

        assert analyzer.config is not None
        assert analyzer.config.default_model == "haiku"
        assert analyzer.config.escalation_threshold == 0.7

    def test_lazy_template_manager(self, analyzer):
        """Test que le template manager est chargé paresseusement"""
        # _template_manager should be None initially
        assert analyzer._template_manager is None

        # Accessing the property should load it
        with patch("src.sancho.templates.get_template_manager") as mock_get_tm:
            mock_tm = MagicMock()
            mock_get_tm.return_value = mock_tm

            tm = analyzer.template_manager

            mock_get_tm.assert_called_once()
            assert tm == mock_tm


class TestAnalyze:
    """Tests pour la méthode analyze"""

    @pytest.mark.asyncio
    async def test_analyze_high_confidence_no_escalation(
        self, analyzer, sample_event, sample_context_notes, mock_router
    ):
        """Test analyse avec haute confiance (pas d'escalade)"""
        # Mock response with high confidence
        response_json = json.dumps(
            {
                "extractions": [
                    {
                        "info": "Budget de 50k€ validé",
                        "type": "decision",
                        "importance": "haute",
                        "note_cible": "Projet Alpha",
                        "note_action": "enrichir",
                        "omnifocus": False,
                    }
                ],
                "action": "archive",
                "confidence": 0.92,
                "raisonnement": "Décision budgétaire importante",
            }
        )

        mock_router._call_claude.return_value = (
            response_json,
            {"total_tokens": 500, "input_tokens": 400, "output_tokens": 100},
        )

        # Mock template rendering by setting _template_manager directly
        mock_tm = MagicMock()
        mock_tm.render.return_value = "Rendered prompt"
        analyzer._template_manager = mock_tm

        result = await analyzer.analyze(sample_event, sample_context_notes)

        # Should only call Haiku (no escalation)
        assert mock_router._call_claude.call_count == 1
        call_args = mock_router._call_claude.call_args
        assert call_args[1]["model"] == AIModel.CLAUDE_HAIKU

        # Verify result
        assert result.confidence == 0.92
        assert result.escalated is False
        assert result.action == EmailAction.ARCHIVE
        assert len(result.extractions) == 1
        assert result.extractions[0].type == ExtractionType.DECISION

    @pytest.mark.asyncio
    async def test_analyze_low_confidence_triggers_escalation(
        self, analyzer, sample_event, mock_router
    ):
        """Test analyse avec basse confiance (escalade vers Sonnet)"""
        # First call: Haiku with low confidence
        haiku_response = json.dumps(
            {
                "extractions": [],
                "action": "queue",
                "confidence": 0.5,
                "raisonnement": "Incertain",
            }
        )

        # Second call: Sonnet with higher confidence
        sonnet_response = json.dumps(
            {
                "extractions": [
                    {
                        "info": "Budget validé",
                        "type": "decision",
                        "importance": "haute",
                        "note_cible": "Projet Alpha",
                        "note_action": "enrichir",
                        "omnifocus": False,
                    }
                ],
                "action": "archive",
                "confidence": 0.88,
                "raisonnement": "Après analyse approfondie",
            }
        )

        mock_router._call_claude.side_effect = [
            (haiku_response, {"total_tokens": 400}),
            (sonnet_response, {"total_tokens": 800}),
        ]

        # Mock template rendering
        mock_tm = MagicMock()
        mock_tm.render.return_value = "Rendered prompt"
        analyzer._template_manager = mock_tm

        result = await analyzer.analyze(sample_event)

        # Should call both Haiku and Sonnet
        assert mock_router._call_claude.call_count == 2

        # First call should be Haiku
        first_call = mock_router._call_claude.call_args_list[0]
        assert first_call[1]["model"] == AIModel.CLAUDE_HAIKU

        # Second call should be Sonnet
        second_call = mock_router._call_claude.call_args_list[1]
        assert second_call[1]["model"] == AIModel.CLAUDE_SONNET

        # Result should be from Sonnet
        assert result.confidence == 0.88
        assert result.escalated is True
        assert len(result.extractions) == 1

    @pytest.mark.asyncio
    async def test_analyze_empty_extractions(self, analyzer, sample_event, mock_router):
        """Test analyse sans extractions (newsletter)"""
        response_json = json.dumps(
            {
                "extractions": [],
                "action": "delete",
                "confidence": 0.95,
                "raisonnement": "Newsletter sans valeur permanente",
            }
        )

        mock_router._call_claude.return_value = (response_json, {"total_tokens": 300})

        # Mock template rendering
        mock_tm = MagicMock()
        mock_tm.render.return_value = "Rendered prompt"
        analyzer._template_manager = mock_tm

        result = await analyzer.analyze(sample_event)

        assert result.has_extractions is False
        assert result.action == EmailAction.DELETE
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_analyze_with_omnifocus_task(
        self, analyzer, sample_event, mock_router
    ):
        """Test analyse avec tâche OmniFocus"""
        response_json = json.dumps(
            {
                "extractions": [
                    {
                        "info": "MVP à livrer pour le 15 mars",
                        "type": "deadline",
                        "importance": "haute",
                        "note_cible": "Projet Alpha",
                        "note_action": "enrichir",
                        "omnifocus": True,
                    }
                ],
                "action": "archive",
                "confidence": 0.9,
                "raisonnement": "Deadline importante",
            }
        )

        mock_router._call_claude.return_value = (response_json, {"total_tokens": 400})

        # Mock template rendering
        mock_tm = MagicMock()
        mock_tm.render.return_value = "Rendered prompt"
        analyzer._template_manager = mock_tm

        result = await analyzer.analyze(sample_event)

        assert result.omnifocus_tasks_count == 1
        assert result.extractions[0].omnifocus is True
        assert result.extractions[0].type == ExtractionType.DEADLINE


class TestParseResponse:
    """Tests pour le parsing des réponses"""

    def test_parse_valid_response(self, analyzer):
        """Test parsing réponse valide"""
        response = json.dumps(
            {
                "extractions": [
                    {
                        "info": "Test info",
                        "type": "decision",
                        "importance": "haute",
                        "note_cible": "Test Note",
                        "note_action": "enrichir",
                        "omnifocus": False,
                    }
                ],
                "action": "archive",
                "confidence": 0.85,
                "raisonnement": "Test reason",
            }
        )

        result = analyzer._parse_response(
            response=response,
            model="claude-3-5-haiku-20241022",
            usage={"total_tokens": 100},
            duration_ms=500.0,
        )

        assert result.confidence == 0.85
        assert result.action == EmailAction.ARCHIVE
        assert len(result.extractions) == 1

    def test_parse_response_with_markdown_wrapper(self, analyzer):
        """Test parsing avec markdown code block"""
        response = """Here's the analysis:

```json
{
    "extractions": [],
    "action": "delete",
    "confidence": 0.9,
    "raisonnement": "Spam"
}
```

That's my analysis."""

        result = analyzer._parse_response(
            response=response,
            model="haiku",
            usage={"total_tokens": 100},
            duration_ms=300.0,
        )

        assert result.action == EmailAction.DELETE
        assert result.confidence == 0.9

    def test_parse_response_clamps_confidence(self, analyzer):
        """Test que confidence est clampée à [0, 1]"""
        # Test > 1
        response_high = json.dumps(
            {
                "extractions": [],
                "action": "archive",
                "confidence": 1.5,
                "raisonnement": "",
            }
        )

        result_high = analyzer._parse_response(
            response=response_high,
            model="haiku",
            usage={"total_tokens": 100},
            duration_ms=100.0,
        )
        assert result_high.confidence == 1.0

        # Test < 0
        response_low = json.dumps(
            {
                "extractions": [],
                "action": "archive",
                "confidence": -0.5,
                "raisonnement": "",
            }
        )

        result_low = analyzer._parse_response(
            response=response_low,
            model="haiku",
            usage={"total_tokens": 100},
            duration_ms=100.0,
        )
        assert result_low.confidence == 0.0

    def test_parse_response_invalid_json(self, analyzer):
        """Test parsing JSON invalide"""
        # JSON with syntax error (missing quotes)
        with pytest.raises(ParseError):
            analyzer._parse_response(
                response="{invalid: json, missing: quotes}",
                model="haiku",
                usage={},
                duration_ms=100.0,
            )

    def test_parse_response_no_json_found(self, analyzer):
        """Test réponse sans JSON"""
        with pytest.raises(ParseError, match="No JSON object found"):
            analyzer._parse_response(
                response="Just text without any braces",
                model="haiku",
                usage={},
                duration_ms=100.0,
            )

    def test_parse_response_unknown_action_fallback(self, analyzer):
        """Test action inconnue → fallback vers 'rien'"""
        response = json.dumps(
            {
                "extractions": [],
                "action": "unknown_action",
                "confidence": 0.8,
                "raisonnement": "",
            }
        )

        result = analyzer._parse_response(
            response=response,
            model="haiku",
            usage={"total_tokens": 100},
            duration_ms=100.0,
        )

        assert result.action == EmailAction.RIEN


class TestParseExtractions:
    """Tests pour le parsing des extractions"""

    def test_parse_all_extraction_types(self, analyzer):
        """Test parsing de tous les types d'extraction"""
        extractions_data = [
            {
                "info": "Decision",
                "type": "decision",
                "importance": "haute",
                "note_cible": "Note1",
                "note_action": "enrichir",
            },
            {
                "info": "Engagement",
                "type": "engagement",
                "importance": "moyenne",
                "note_cible": "Note2",
                "note_action": "creer",
            },
            {
                "info": "Fait",
                "type": "fait",
                "importance": "haute",
                "note_cible": "Note3",
                "note_action": "enrichir",
            },
            {
                "info": "Deadline",
                "type": "deadline",
                "importance": "haute",
                "note_cible": "Note4",
                "note_action": "enrichir",
                "omnifocus": True,
            },
            {
                "info": "Relation",
                "type": "relation",
                "importance": "moyenne",
                "note_cible": "Note5",
                "note_action": "creer",
            },
        ]

        extractions = analyzer._parse_extractions(extractions_data)

        assert len(extractions) == 5
        assert extractions[0].type == ExtractionType.DECISION
        assert extractions[1].type == ExtractionType.ENGAGEMENT
        assert extractions[2].type == ExtractionType.FAIT
        assert extractions[3].type == ExtractionType.DEADLINE
        assert extractions[3].omnifocus is True
        assert extractions[4].type == ExtractionType.RELATION

    def test_parse_extractions_skips_empty_info(self, analyzer):
        """Test que les extractions avec info vide sont ignorées"""
        extractions_data = [
            {
                "info": "",
                "type": "decision",
                "importance": "haute",
                "note_cible": "Note1",
                "note_action": "enrichir",
            },
            {
                "info": "Valid info",
                "type": "fait",
                "importance": "moyenne",
                "note_cible": "Note2",
                "note_action": "enrichir",
            },
        ]

        extractions = analyzer._parse_extractions(extractions_data)

        assert len(extractions) == 1
        assert extractions[0].info == "Valid info"

    def test_parse_extractions_skips_empty_note_cible(self, analyzer):
        """Test que les extractions sans note_cible sont ignorées"""
        extractions_data = [
            {
                "info": "Some info",
                "type": "decision",
                "importance": "haute",
                "note_cible": "",
                "note_action": "enrichir",
            },
        ]

        extractions = analyzer._parse_extractions(extractions_data)

        assert len(extractions) == 0

    def test_parse_extractions_unknown_type_fallback(self, analyzer):
        """Test type inconnu → fallback vers 'fait'"""
        extractions_data = [
            {
                "info": "Some info",
                "type": "unknown_type",
                "importance": "haute",
                "note_cible": "Note1",
                "note_action": "enrichir",
            },
        ]

        extractions = analyzer._parse_extractions(extractions_data)

        assert len(extractions) == 1
        assert extractions[0].type == ExtractionType.FAIT

    def test_parse_extractions_unknown_importance_fallback(self, analyzer):
        """Test importance inconnue → fallback vers 'moyenne'"""
        extractions_data = [
            {
                "info": "Some info",
                "type": "decision",
                "importance": "unknown",
                "note_cible": "Note1",
                "note_action": "enrichir",
            },
        ]

        extractions = analyzer._parse_extractions(extractions_data)

        assert extractions[0].importance == ImportanceLevel.MOYENNE

    def test_parse_extractions_unknown_action_fallback(self, analyzer):
        """Test note_action inconnue → fallback vers 'enrichir'"""
        extractions_data = [
            {
                "info": "Some info",
                "type": "decision",
                "importance": "haute",
                "note_cible": "Note1",
                "note_action": "unknown",
            },
        ]

        extractions = analyzer._parse_extractions(extractions_data)

        assert extractions[0].note_action == NoteAction.ENRICHIR


class TestRenderPrompt:
    """Tests pour le rendu du prompt"""

    def test_render_prompt_success(self, analyzer, sample_event, sample_context_notes):
        """Test rendu réussi du prompt"""
        # Mock template manager by setting _template_manager directly
        mock_tm = MagicMock()
        mock_tm.render.return_value = "Rendered prompt content"
        analyzer._template_manager = mock_tm

        prompt = analyzer._render_prompt(sample_event, sample_context_notes)

        assert prompt == "Rendered prompt content"
        mock_tm.render.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_tm.render.call_args[1]
        assert call_kwargs["event"] == sample_event
        assert len(call_kwargs["context"]) == 2
        assert call_kwargs["max_content_chars"] == 2000

    def test_render_prompt_template_error(self, analyzer, sample_event):
        """Test erreur de rendu template"""
        # Mock template manager with error
        mock_tm = MagicMock()
        mock_tm.render.side_effect = Exception("Template error")
        analyzer._template_manager = mock_tm

        with pytest.raises(PromptRenderError, match="Template rendering failed"):
            analyzer._render_prompt(sample_event, [])


class TestCreateAnalyzer:
    """Tests pour la factory function"""

    def test_create_analyzer_with_router(self, mock_router, config):
        """Test création avec router fourni"""
        analyzer = create_analyzer(ai_router=mock_router, config=config)

        assert analyzer.ai_router == mock_router
        assert analyzer.config == config

    def test_create_analyzer_with_config_only(self, config):
        """Test création avec seulement la config (crée un router par défaut)"""
        # This test verifies the factory function signature
        # Full integration test would require actual API keys
        with patch("src.core.config_manager.get_config") as mock_get_config:
            mock_app_config = MagicMock()
            mock_app_config.ai = MagicMock()
            mock_app_config.ai.anthropic_api_key = "test-key"
            mock_app_config.ai.rate_limit_per_minute = 40
            mock_get_config.return_value = mock_app_config

            # create_analyzer without router will try to create one
            # Just verify the function signature works
            analyzer = create_analyzer(config=config)

            assert analyzer.config == config


class TestModelMapping:
    """Tests pour le mapping des modèles"""

    def test_model_map_contains_expected_models(self):
        """Test que le mapping contient les modèles attendus"""
        assert "haiku" in EventAnalyzer.MODEL_MAP
        assert "sonnet" in EventAnalyzer.MODEL_MAP
        assert "opus" in EventAnalyzer.MODEL_MAP

        assert EventAnalyzer.MODEL_MAP["haiku"] == AIModel.CLAUDE_HAIKU
        assert EventAnalyzer.MODEL_MAP["sonnet"] == AIModel.CLAUDE_SONNET
        assert EventAnalyzer.MODEL_MAP["opus"] == AIModel.CLAUDE_OPUS
