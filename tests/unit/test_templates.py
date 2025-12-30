"""
Unit Tests for Template Manager

Tests Jinja2 template rendering and management.
"""

import pytest
from pathlib import Path
from src.ai.templates import TemplateManager


class TestTemplateManager:
    """Test template manager functionality"""

    def test_template_manager_initialization(self, tmp_templates_dir: Path):
        """Test template manager initializes correctly"""
        manager = TemplateManager(templates_dir=tmp_templates_dir)
        assert manager.templates_dir == tmp_templates_dir
        assert manager.env is not None

    def test_template_manager_default_path(self):
        """Test template manager uses default path"""
        manager = TemplateManager()
        expected_path = Path(__file__).parent.parent.parent / "templates"
        assert manager.templates_dir == expected_path

    def test_render_email_analysis_template(self, tmp_templates_dir: Path):
        """Test rendering email analysis template"""
        # Create template file
        template_file = tmp_templates_dir / "test_analysis.j2"
        template_file.write_text(
            "Subject: {{ subject }}\n"
            "From: {{ from_address }}\n"
            "Category: {{ category }}"
        )

        manager = TemplateManager(templates_dir=tmp_templates_dir)
        result = manager.render(
            "test_analysis.j2",
            subject="Test Email",
            from_address="test@example.com",
            category="work"
        )

        assert "Subject: Test Email" in result
        assert "From: test@example.com" in result
        assert "Category: work" in result

    def test_render_with_loops(self, tmp_templates_dir: Path):
        """Test rendering template with loops"""
        template_file = tmp_templates_dir / "test_loop.j2"
        template_file.write_text(
            "{% for item in items %}\n"
            "- {{ item }}\n"
            "{% endfor %}"
        )

        manager = TemplateManager(templates_dir=tmp_templates_dir)
        result = manager.render("test_loop.j2", items=["one", "two", "three"])

        assert "- one" in result
        assert "- two" in result
        assert "- three" in result

    def test_render_with_conditionals(self, tmp_templates_dir: Path):
        """Test rendering template with conditionals"""
        template_file = tmp_templates_dir / "test_conditional.j2"
        template_file.write_text(
            "{% if has_attachments %}\n"
            "Attachments: Yes\n"
            "{% else %}\n"
            "Attachments: No\n"
            "{% endif %}"
        )

        manager = TemplateManager(templates_dir=tmp_templates_dir)

        result_with = manager.render("test_conditional.j2", has_attachments=True)
        assert "Attachments: Yes" in result_with

        result_without = manager.render("test_conditional.j2", has_attachments=False)
        assert "Attachments: No" in result_without

    def test_truncate_smart_filter(self, tmp_templates_dir: Path):
        """Test truncate_smart custom filter"""
        template_file = tmp_templates_dir / "test_truncate.j2"
        template_file.write_text("{{ text | truncate_smart(20) }}")

        manager = TemplateManager(templates_dir=tmp_templates_dir)

        # Short text - no truncation
        result = manager.render("test_truncate.j2", text="Short text")
        assert result == "Short text"

        # Long text - truncate at word boundary
        long_text = "This is a very long text that should be truncated"
        result = manager.render("test_truncate.j2", text=long_text)
        assert len(result) <= 23  # 20 + "..."
        assert result.endswith("...")
        assert not result.endswith(" ...")  # No trailing space before ...

    def test_template_not_found(self, tmp_templates_dir: Path):
        """Test handling of missing template"""
        manager = TemplateManager(templates_dir=tmp_templates_dir)

        with pytest.raises(Exception):  # Jinja2 TemplateNotFound
            manager.render("nonexistent.j2")

    def test_render_with_missing_variables(self, tmp_templates_dir: Path):
        """Test rendering with missing variables"""
        template_file = tmp_templates_dir / "test_missing.j2"
        template_file.write_text("{{ required_var }}")

        manager = TemplateManager(templates_dir=tmp_templates_dir)

        # Jinja2 by default renders undefined as empty string
        result = manager.render("test_missing.j2")
        assert result == ""

    def test_trim_blocks_and_lstrip(self, tmp_templates_dir: Path):
        """Test that trim_blocks and lstrip_blocks work"""
        template_file = tmp_templates_dir / "test_trim.j2"
        template_file.write_text(
            "Line 1\n"
            "{% if true %}\n"
            "Line 2\n"
            "{% endif %}\n"
            "Line 3"
        )

        manager = TemplateManager(templates_dir=tmp_templates_dir)
        result = manager.render("test_trim.j2")

        # Should have clean output without extra blank lines
        lines = result.strip().split('\n')
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    def test_autoescape_disabled(self, tmp_templates_dir: Path):
        """Test that autoescape is disabled for our use case"""
        template_file = tmp_templates_dir / "test_escape.j2"
        template_file.write_text("{{ html }}")

        manager = TemplateManager(templates_dir=tmp_templates_dir)
        result = manager.render("test_escape.j2", html="<b>Bold</b>")

        # HTML should not be escaped
        assert result == "<b>Bold</b>"

    def test_render_real_email_analysis_template(self):
        """Test rendering actual email_analysis.j2 template"""
        manager = TemplateManager()  # Use default path

        # Check if template exists
        template_path = manager.templates_dir / "email_analysis.j2"
        if not template_path.exists():
            pytest.skip("email_analysis.j2 template not found")

        result = manager.render(
            "email_analysis.j2",
            subject="Meeting Tomorrow",
            from_address="boss@company.com",
            to_addresses=["me@company.com"],
            date="2025-01-15",
            body="Let's meet tomorrow at 2pm to discuss the project.",
            has_attachments=False,
            category_hint="work",
        )

        assert "Meeting Tomorrow" in result
        assert "boss@company.com" in result
        assert len(result) > 100  # Template should generate substantial content
