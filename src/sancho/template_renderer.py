"""
Jinja2 Template Renderer for Multi-Pass Analysis

Loads and renders Jinja2 templates for the multi-pass extraction system.
Templates are stored in templates/ai/v2/ directory.

Part of Sancho's multi-pass extraction system (v2.2).
See ADR-005 in MULTI_PASS_SPEC.md for design decisions.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from src.monitoring.logger import get_logger

logger = get_logger("template_renderer")

# Default template directory (relative to project root)
DEFAULT_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "ai" / "v2"


class TemplateRenderer:
    """
    Jinja2 template renderer for multi-pass prompts.

    Usage:
        renderer = TemplateRenderer()
        prompt = renderer.render("pass1_blind_extraction", event=event, max_content_chars=8000)
    """

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        auto_reload: bool = True,
    ) -> None:
        """
        Initialize the template renderer.

        Args:
            template_dir: Directory containing Jinja2 templates
            auto_reload: Whether to auto-reload templates on change (dev mode)
        """
        self._template_dir = template_dir or DEFAULT_TEMPLATE_DIR

        # Ensure template directory exists
        if not self._template_dir.exists():
            logger.warning("Template directory does not exist: %s", self._template_dir)
            self._template_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            auto_reload=auto_reload,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self._env.filters["truncate_smart"] = self._truncate_smart
        self._env.filters["format_date"] = self._format_date
        self._env.filters["format_confidence"] = self._format_confidence

        # Initialize ContextLoader for briefing injection (v2.5)
        self._briefing_context: Optional[str] = None
        try:
            from src.passepartout.context_loader import ContextLoader
            context_loader = ContextLoader()
            self._briefing_context = context_loader.load_context()
            if self._briefing_context:
                logger.info("Briefing context loaded (%d chars)", len(self._briefing_context))
            else:
                logger.warning("No briefing context found")
        except Exception as e:
            logger.warning("Failed to load briefing context: %s", e)

        logger.info(
            "TemplateRenderer initialized (dir=%s, auto_reload=%s)",
            self._template_dir,
            auto_reload,
        )

    @property
    def template_dir(self) -> Path:
        """Get the template directory path"""
        return self._template_dir

    def list_templates(self) -> list[str]:
        """List all available templates"""
        return self._env.list_templates()

    def render(
        self,
        template_name: str,
        **context: Any,
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Template name (without .j2 extension)
            **context: Variables to pass to the template

        Returns:
            Rendered template string

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        # Add .j2 extension if not present
        if not template_name.endswith(".j2"):
            template_name = f"{template_name}.j2"

        # Add 'now' to context for age calculations
        context["now"] = datetime.now(timezone.utc)

        # Add briefing context if available (v2.5)
        if self._briefing_context and "briefing" not in context:
            context["briefing"] = self._briefing_context

        try:
            template = self._env.get_template(template_name)
            rendered = template.render(**context)
            logger.debug(
                "Rendered template %s (%d chars)",
                template_name,
                len(rendered),
            )
            return rendered
        except TemplateNotFound:
            logger.error("Template not found: %s", template_name)
            raise

    def render_pass1(
        self,
        event: Any,
        max_content_chars: int = 8000,
    ) -> str:
        """
        Render Pass 1 (Blind Extraction) template.

        Args:
            event: PerceivedEvent to analyze
            max_content_chars: Maximum content length

        Returns:
            Rendered prompt string
        """
        return self.render(
            "pass1_blind_extraction",
            event=event,
            max_content_chars=max_content_chars,
        )

    def render_pass2(
        self,
        event: Any,
        previous_result: dict,
        context: Any,
        max_content_chars: int = 8000,
        max_context_notes: int = 5,
    ) -> str:
        """
        Render Pass 2+ (Contextual Refinement) template.

        Args:
            event: PerceivedEvent to analyze
            previous_result: Result from previous pass
            context: StructuredContext with notes, calendar, etc.
            max_content_chars: Maximum content length
            max_context_notes: Maximum notes to include

        Returns:
            Rendered prompt string
        """
        return self.render(
            "pass2_contextual_refinement",
            event=event,
            previous_result=previous_result,
            context=context,
            max_content_chars=max_content_chars,
            max_context_notes=max_context_notes,
        )

    def render_pass4(
        self,
        event: Any,
        passes: list[dict],
        full_context: Any,
        unresolved_issues: list[str],
    ) -> str:
        """
        Render Pass 4-5 (Deep Reasoning) template.

        Args:
            event: PerceivedEvent to analyze
            passes: List of previous pass results
            full_context: Full StructuredContext
            unresolved_issues: List of unresolved issues

        Returns:
            Rendered prompt string
        """
        return self.render(
            "pass4_deep_reasoning",
            event=event,
            passes=passes,
            full_context=full_context,
            unresolved_issues=unresolved_issues,
        )

    # Custom Jinja2 filters

    @staticmethod
    def _truncate_smart(text: str, length: int, suffix: str = "...") -> str:
        """Truncate text at word boundary"""
        if len(text) <= length:
            return text
        # Find last space before length
        truncated = text[:length]
        last_space = truncated.rfind(" ")
        if last_space > length * 0.8:  # Only use if > 80% of length
            truncated = truncated[:last_space]
        return truncated + suffix

    @staticmethod
    def _format_date(date_str: str, format_str: str = "%d %B %Y") -> str:
        """Format a date string"""
        from datetime import datetime

        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime(format_str)
        except (ValueError, TypeError):
            return date_str

    @staticmethod
    def _format_confidence(value: float) -> str:
        """Format confidence as percentage"""
        return f"{value * 100:.0f}%"


# Singleton instance
_renderer: Optional[TemplateRenderer] = None


def get_template_renderer() -> TemplateRenderer:
    """Get the singleton template renderer instance"""
    global _renderer
    if _renderer is None:
        _renderer = TemplateRenderer()
    return _renderer
