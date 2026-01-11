"""
Tests for template_renderer.py — Multi-Pass v2.2 Jinja2 templates

Tests cover:
- TemplateRenderer initialization
- Custom Jinja2 filters (truncate_smart, format_date, format_confidence)
- Template rendering
- Pass-specific render methods
- Singleton pattern
"""

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
        # Should include our v2.2 templates
        assert "pass1_blind_extraction.j2" in templates
        assert "pass2_contextual_refinement.j2" in templates
        assert "pass4_deep_reasoning.j2" in templates


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


class TestPassRenderMethods:
    """Tests for pass-specific render methods"""

    def test_render_pass1(self):
        """Render Pass 1 template"""
        renderer = TemplateRenderer()

        # Create mock event with all attributes the template expects
        mock_event = MagicMock()
        mock_event.title = "Test Subject"
        mock_event.content = "Test content about Project Alpha"
        mock_event.timestamp = "2026-01-15T10:00:00"
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.display_name = "Test Sender"
        mock_event.sender.email = "test@example.com"
        mock_event.entities = []

        result = renderer.render_pass1(event=mock_event, max_content_chars=8000)

        # Should contain the event content
        assert "Test content" in result
        # Should be a valid prompt with extraction instructions
        assert len(result) > 100
        assert "extraction" in result.lower()

    def test_render_pass2(self):
        """Render Pass 2 template"""
        renderer = TemplateRenderer()

        # Create mock event
        mock_event = MagicMock()
        mock_event.title = "Test Subject"
        mock_event.content = "Test content"
        mock_event.timestamp = "2026-01-15T10:00:00"
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.display_name = "Test Sender"
        mock_event.sender.email = "test@example.com"

        # Previous result with full confidence structure
        previous_result = {
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

        result = renderer.render_pass2(
            event=mock_event,
            previous_result=previous_result,
            context=mock_context,
            max_content_chars=8000,
            max_context_notes=5,
        )

        assert len(result) > 100
        assert "context" in result.lower()

    def test_render_pass4(self):
        """Render Pass 4 template"""
        renderer = TemplateRenderer()

        # Create mock event
        mock_event = MagicMock()
        mock_event.title = "Complex Subject"
        mock_event.content = "Complex content requiring deep analysis"
        mock_event.timestamp = "2026-01-15T10:00:00"
        mock_event.source_type = "email"
        mock_event.sender = MagicMock()
        mock_event.sender.display_name = "VIP Sender"
        mock_event.sender.email = "vip@example.com"

        # Passes with full confidence structure
        passes = [
            {
                "pass_number": 1,
                "extractions": [{"info": "Fact 1", "type": "fait"}],
                "confidence": {
                    "entity_confidence": 0.6,
                    "action_confidence": 0.6,
                    "extraction_confidence": 0.6,
                    "completeness": 0.6,
                    "overall": 0.6,
                },
            },
            {
                "pass_number": 2,
                "extractions": [{"info": "Fact 1"}, {"info": "Fact 2"}],
                "confidence": {
                    "entity_confidence": 0.7,
                    "action_confidence": 0.7,
                    "extraction_confidence": 0.7,
                    "completeness": 0.7,
                    "overall": 0.7,
                },
            },
        ]

        mock_context = MagicMock()
        mock_context.to_prompt_format.return_value = "## Full Context\nNotes and history"

        unresolved_issues = [
            "Ambiguité sur l'identité de Marc",
            "Date de la réunion incertaine",
        ]

        result = renderer.render_pass4(
            event=mock_event,
            passes=passes,
            full_context=mock_context,
            unresolved_issues=unresolved_issues,
        )

        assert len(result) > 100
        assert "Ambiguité" in result or "raisonnement" in result.lower()


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

    def test_pass1_template_structure(self):
        """Pass 1 template has correct structure"""
        renderer = TemplateRenderer()
        templates = renderer.list_templates()
        assert "pass1_blind_extraction.j2" in templates

        # Read template content
        template_path = renderer.template_dir / "pass1_blind_extraction.j2"
        content = template_path.read_text()

        # Check for key elements
        assert "extraction" in content.lower()
        assert "confiance" in content.lower() or "confidence" in content.lower()

    def test_pass2_template_structure(self):
        """Pass 2 template has correct structure"""
        renderer = TemplateRenderer()
        template_path = renderer.template_dir / "pass2_contextual_refinement.j2"
        content = template_path.read_text()

        # Should reference context and previous result
        assert "context" in content.lower()
        assert "previous" in content.lower() or "précédent" in content.lower()

    def test_pass4_template_structure(self):
        """Pass 4 template has correct structure"""
        renderer = TemplateRenderer()
        template_path = renderer.template_dir / "pass4_deep_reasoning.j2"
        content = template_path.read_text()

        # Should be for deep reasoning
        assert "reasoning" in content.lower() or "raisonnement" in content.lower()
