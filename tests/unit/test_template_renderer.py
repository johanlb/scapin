"""
Tests for template_renderer.py — Four Valets v3.0 Jinja2 templates

Tests cover:
- TemplateRenderer initialization
- Custom Jinja2 filters (truncate_smart, format_date, format_confidence)
- Template rendering
- Valet-specific render methods (Grimaud, Bazin, Planchet, Mousqueton)
- Cache-optimized split prompts
- Singleton pattern
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from jinja2 import TemplateNotFound

from src.sancho.template_renderer import (
    DEFAULT_TEMPLATE_DIR,
    TemplateRenderer,
    get_template_renderer,
)


class TestTemplateRendererInit:
    """Tests for TemplateRenderer initialization"""

    def test_init_default_dir(self):
        """Initialize with default template directory"""
        renderer = TemplateRenderer()
        assert renderer.template_dir == DEFAULT_TEMPLATE_DIR
        assert renderer.template_dir.exists()

    def test_init_custom_dir(self, tmp_path):
        """Initialize with custom template directory"""
        # Create custom template dir
        custom_dir = tmp_path / "templates"
        custom_dir.mkdir()

        renderer = TemplateRenderer(template_dir=custom_dir)
        assert renderer.template_dir == custom_dir

    def test_init_creates_missing_dir(self, tmp_path):
        """Creates template directory if it doesn't exist"""
        new_dir = tmp_path / "new_templates"
        assert not new_dir.exists()

        renderer = TemplateRenderer(template_dir=new_dir)
        assert new_dir.exists()
        assert renderer.template_dir == new_dir

    def test_list_templates(self):
        """List available templates"""
        renderer = TemplateRenderer()
        templates = renderer.list_templates()
        # Should include our Four Valets v3.0 templates
        assert "pass1_grimaud.j2" in templates
        assert "pass2_bazin.j2" in templates
        assert "pass3_planchet.j2" in templates
        assert "pass4_mousqueton.j2" in templates
        # Cache-optimized split templates
        assert "pass1_grimaud_system.j2" in templates
        assert "pass1_grimaud_user.j2" in templates


class TestCustomFilters:
    """Tests for custom Jinja2 filters"""

    def test_truncate_smart_short_text(self):
        """Short text not truncated"""
        result = TemplateRenderer._truncate_smart("Hello world", 100)
        assert result == "Hello world"

    def test_truncate_smart_at_word_boundary(self):
        """Truncate at word boundary"""
        text = "This is a long text that needs to be truncated"
        result = TemplateRenderer._truncate_smart(text, 25)
        # Should truncate at space before position 25
        assert result.endswith("...")
        assert len(result) <= 28  # 25 + "..."
        assert " " not in result[-4:]  # No cut mid-word

    def test_truncate_smart_custom_suffix(self):
        """Custom truncation suffix"""
        text = "This is a very long text"
        result = TemplateRenderer._truncate_smart(text, 15, suffix=" [...]")
        assert result.endswith(" [...]")

    def test_format_date_valid(self):
        """Format valid ISO date"""
        result = TemplateRenderer._format_date("2026-01-15")
        # Default format: %d %B %Y
        assert "15" in result
        assert "2026" in result

    def test_format_date_invalid(self):
        """Invalid date returns original string"""
        result = TemplateRenderer._format_date("not-a-date")
        assert result == "not-a-date"

    def test_format_date_custom_format(self):
        """Custom date format"""
        result = TemplateRenderer._format_date("2026-01-15", format_str="%Y/%m/%d")
        assert result == "2026/01/15"

    def test_format_confidence(self):
        """Format confidence as percentage"""
        assert TemplateRenderer._format_confidence(0.95) == "95%"
        assert TemplateRenderer._format_confidence(0.75) == "75%"
        assert TemplateRenderer._format_confidence(1.0) == "100%"
        assert TemplateRenderer._format_confidence(0.0) == "0%"


class TestTemplateRendering:
    """Tests for template rendering"""

    def test_render_with_extension(self, tmp_path):
        """Render template with .j2 extension"""
        # Create test template
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Hello {{ name }}!")

        renderer = TemplateRenderer(template_dir=template_dir)
        result = renderer.render("test.j2", name="World")
        assert result == "Hello World!"

    def test_render_without_extension(self, tmp_path):
        """Render template without .j2 extension (auto-added)"""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Hello {{ name }}!")

        renderer = TemplateRenderer(template_dir=template_dir)
        result = renderer.render("test", name="World")
        assert result == "Hello World!"

    def test_render_not_found(self, tmp_path):
        """TemplateNotFound raised for missing template"""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        renderer = TemplateRenderer(template_dir=template_dir)
        with pytest.raises(TemplateNotFound):
            renderer.render("nonexistent")

    def test_render_with_filters(self, tmp_path):
        """Custom filters available in templates"""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "filters.j2"
        template_file.write_text("{{ value | format_confidence }}")

        renderer = TemplateRenderer(template_dir=template_dir)
        result = renderer.render("filters", value=0.85)
        assert result == "85%"


class TestValetRenderMethods:
    """Tests for valet-specific render methods (Four Valets v3.0)"""

    def test_render_grimaud(self):
        """Render Grimaud (Pass 1) template - Silent extraction"""
        renderer = TemplateRenderer()

        # Create mock event with all attributes the template expects
        mock_event = MagicMock()
        mock_event.title = "Test Subject"
        mock_event.content = "Test content about Project Alpha"
        mock_event.timestamp = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.name = "Test Sender"
        mock_event.sender.email = "test@example.com"
        mock_event.entities = []

        result = renderer.render_grimaud(event=mock_event, max_content_chars=8000)

        # Should contain the event content
        assert "Test content" in result
        # Should be a valid prompt with extraction instructions
        assert len(result) > 100

    def test_render_bazin(self):
        """Render Bazin (Pass 2) template - Contextual enrichment"""
        renderer = TemplateRenderer()

        # Create mock event
        mock_event = MagicMock()
        mock_event.title = "Test Subject"
        mock_event.content = "Test content"
        mock_event.timestamp = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.name = "Test Sender"
        mock_event.sender.email = "test@example.com"

        # Grimaud result with full confidence structure
        grimaud_result = {
            "extractions": [{"info": "Test info", "type": "fait"}],
            "action": "archive",
            "confidence": {
                "entity_confidence": 0.75,
                "action_confidence": 0.70,
                "extraction_confidence": 0.80,
                "completeness": 0.65,
                "overall": 0.65,
            },
            "entities_discovered": ["Marc Dupont"],
        }

        mock_context = MagicMock()
        mock_context.to_prompt_format.return_value = "## Context\nTest context"
        mock_context.is_empty = False
        mock_context.notes = []

        result = renderer.render_bazin(
            event=mock_event,
            grimaud_result=grimaud_result,
            context=mock_context,
            max_content_chars=8000,
            max_context_notes=5,
        )

        assert len(result) > 100

    def test_render_mousqueton(self):
        """Render Mousqueton (Pass 4) template - Final arbitration"""
        renderer = TemplateRenderer()

        # Create mock event
        mock_event = MagicMock()
        mock_event.title = "Complex Subject"
        mock_event.content = "Complex content requiring deep analysis"
        mock_event.timestamp = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.name = "VIP Sender"
        mock_event.sender.email = "vip@example.com"

        # Results from previous passes
        grimaud_result = {
            "extractions": [{"info": "Fact 1", "type": "fait"}],
            "action": "archive",
            "confidence": {"overall": 0.6},
        }
        bazin_result = {
            "extractions": [{"info": "Fact 1"}, {"info": "Fact 2"}],
            "action": "archive",
            "confidence": {"overall": 0.7},
            "changes_made": ["Added context"],
        }
        planchet_result = {
            "critique": {
                "extraction_issues": ["Minor issue"],
                "action_issues": [],
                "age_concerns": [],
                "contradictions": [],
            },
            "recommendations": ["Review extraction"],
            "questions_for_mousqueton": ["Is this correct?"],
            "confidence_assessment": {"can_proceed": True},
        }

        mock_context = MagicMock()
        mock_context.notes = []
        mock_context.conflicts = []

        result = renderer.render_mousqueton(
            event=mock_event,
            grimaud_result=grimaud_result,
            bazin_result=bazin_result,
            planchet_result=planchet_result,
            context=mock_context,
        )

        assert len(result) > 100


class TestSplitPromptMethods:
    """Tests for cache-optimized split prompt rendering"""

    def test_render_grimaud_split(self):
        """Render Grimaud with split system/user prompts"""
        from src.sancho.template_renderer import SplitPrompt

        renderer = TemplateRenderer()

        mock_event = MagicMock()
        mock_event.title = "Test Subject"
        mock_event.content = "Test content"
        mock_event.timestamp = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.name = "Test Sender"
        mock_event.sender.email = "test@example.com"

        result = renderer.render_grimaud_split(event=mock_event, max_content_chars=8000)

        assert isinstance(result, SplitPrompt)
        assert len(result.system) > 50  # System prompt has instructions
        assert len(result.user) > 50  # User prompt has event data
        assert "Test content" in result.user
        assert "Grimaud" in result.system

    def test_split_prompt_combined(self):
        """SplitPrompt.combined returns system + user"""
        from src.sancho.template_renderer import SplitPrompt

        split = SplitPrompt(system="System instructions", user="User data")
        combined = split.combined

        assert "System instructions" in combined
        assert "User data" in combined
        assert "---" in combined  # Separator


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_template_renderer_returns_same_instance(self):
        """Singleton returns same instance"""
        # Reset singleton for test
        import src.sancho.template_renderer as module
        module._renderer = None

        renderer1 = get_template_renderer()
        renderer2 = get_template_renderer()

        assert renderer1 is renderer2

    def test_get_template_renderer_type(self):
        """Singleton returns TemplateRenderer instance"""
        import src.sancho.template_renderer as module
        module._renderer = None

        renderer = get_template_renderer()
        assert isinstance(renderer, TemplateRenderer)


class TestTemplateContent:
    """Tests for actual template content"""

    def test_grimaud_template_structure(self):
        """Grimaud (Pass 1) template has correct structure"""
        renderer = TemplateRenderer()
        templates = renderer.list_templates()
        assert "pass1_grimaud.j2" in templates

        # Read template content
        template_path = renderer.template_dir / "pass1_grimaud.j2"
        content = template_path.read_text()

        # Check for key elements
        assert "grimaud" in content.lower()
        assert "extraction" in content.lower()

    def test_bazin_template_structure(self):
        """Bazin (Pass 2) template has correct structure"""
        renderer = TemplateRenderer()
        template_path = renderer.template_dir / "pass2_bazin.j2"
        content = template_path.read_text()

        # Should reference context and previous result
        assert "bazin" in content.lower()
        assert "context" in content.lower() or "contexte" in content.lower()

    def test_mousqueton_template_structure(self):
        """Mousqueton (Pass 4) template has correct structure"""
        renderer = TemplateRenderer()
        template_path = renderer.template_dir / "pass4_mousqueton.j2"
        content = template_path.read_text()

        # Should be for final arbitration
        assert "mousqueton" in content.lower()
        assert "arbitr" in content.lower() or "décision" in content.lower()

    def test_split_templates_exist(self):
        """Cache-optimized split templates exist for all valets"""
        renderer = TemplateRenderer()
        templates = renderer.list_templates()

        # All valets should have system and user templates
        for valet in ["grimaud", "bazin", "planchet", "mousqueton"]:
            pass_num = {"grimaud": 1, "bazin": 2, "planchet": 3, "mousqueton": 4}[valet]
            system_name = f"pass{pass_num}_{valet}_system.j2"
            user_name = f"pass{pass_num}_{valet}_user.j2"
            assert system_name in templates, f"Missing {system_name}"
            assert user_name in templates, f"Missing {user_name}"
