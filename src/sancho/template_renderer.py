"""
Jinja2 Template Renderer for Multi-Pass Analysis

Loads and renders Jinja2 templates for the multi-pass extraction system.
Templates are stored in templates/ai/v2/ directory.

Part of Sancho's multi-pass extraction system (v2.2).
See ADR-005 in MULTI_PASS_SPEC.md for design decisions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.passepartout.context_loader import BriefingStatus

logger = get_logger("template_renderer")


@dataclass
class SplitPrompt:
    """
    A prompt split into system and user parts for cache optimization.

    The system prompt contains static instructions (cacheable by Anthropic API).
    The user prompt contains dynamic data (event, context, previous results).
    """

    system: str
    user: str

    @property
    def combined(self) -> str:
        """Get the combined prompt (for backwards compatibility)."""
        return f"{self.system}\n\n---\n\n{self.user}"


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
        # v3.2: Also store briefing status for visibility
        self._briefing_context: Optional[str] = None
        self._briefing_status: Optional[BriefingStatus] = None
        try:
            from src.passepartout.context_loader import ContextLoader

            context_loader = ContextLoader()
            self._briefing_context, self._briefing_status = context_loader.load_context_with_status()
            if self._briefing_context:
                logger.info(
                    "Briefing context loaded (%d chars, status: %s)",
                    len(self._briefing_context),
                    self._briefing_status.completeness.value if self._briefing_status else "unknown",
                )
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

    # ==================== Four Valets v3.0 ====================

    def _get_briefing(self) -> str:
        """
        Get briefing context for Four Valets prompts.

        Returns:
            Briefing string or empty string if not available.
        """
        return self._briefing_context or ""

    def get_briefing_status(self) -> Optional["BriefingStatus"]:
        """
        Get the briefing status (v3.2).

        Returns:
            BriefingStatus with completeness and file details, or None if not loaded.
        """
        return self._briefing_status

    def render_grimaud(
        self,
        event: Any,
        max_content_chars: int = 8000,
    ) -> str:
        """
        Render Grimaud (Pass 1) template - Extraction silencieuse.

        Grimaud extracts raw information without context, like Athos's
        silent servant who observes without speaking.

        Args:
            event: PerceivedEvent to analyze
            max_content_chars: Maximum content length

        Returns:
            Rendered prompt string
        """
        return self.render(
            "pass1_grimaud",
            event=event,
            max_content_chars=max_content_chars,
            briefing=self._get_briefing(),
        )

    def render_bazin(
        self,
        event: Any,
        grimaud_result: dict,
        context: Any,
        max_content_chars: int = 8000,
        max_context_notes: int = 5,
    ) -> str:
        """
        Render Bazin (Pass 2) template - Enrichissement contextuel.

        Bazin enriches extractions with context from PKM notes, like
        Aramis's pious servant who adds wisdom and context.

        Args:
            event: PerceivedEvent to analyze
            grimaud_result: Result from Grimaud pass
            context: StructuredContext with notes, calendar, etc.
            max_content_chars: Maximum content length
            max_context_notes: Maximum notes to include

        Returns:
            Rendered prompt string
        """
        return self.render(
            "pass2_bazin",
            event=event,
            previous_result=grimaud_result,  # Template expects previous_result
            context=context,
            max_content_chars=max_content_chars,
            max_context_notes=max_context_notes,
            briefing=self._get_briefing(),
        )

    def render_planchet(
        self,
        event: Any,
        grimaud_result: dict,
        bazin_result: dict,
        context: Any,
        max_content_chars: int = 8000,
    ) -> str:
        """
        Render Planchet (Pass 3) template - Critique et validation.

        Planchet critiques and validates the extractions, like
        d'Artagnan's resourceful servant who questions everything.

        Args:
            event: PerceivedEvent to analyze
            grimaud_result: Result from Grimaud pass
            bazin_result: Result from Bazin pass
            context: StructuredContext with notes, calendar, etc.
            max_content_chars: Maximum characters of content to include

        Returns:
            Rendered prompt string
        """
        return self.render(
            "pass3_planchet",
            event=event,
            previous_passes=[grimaud_result, bazin_result],  # Template expects previous_passes
            context=context,
            max_content_chars=max_content_chars,
            briefing=self._get_briefing(),
        )

    def render_mousqueton(
        self,
        event: Any,
        grimaud_result: dict,
        bazin_result: dict,
        planchet_result: dict,
        context: Any,
    ) -> str:
        """
        Render Mousqueton (Pass 4) template - Arbitrage final.

        Mousqueton makes the final decision when there's disagreement,
        like Porthos's practical servant who settles disputes.

        Args:
            event: PerceivedEvent to analyze
            grimaud_result: Result from Grimaud pass
            bazin_result: Result from Bazin pass
            planchet_result: Result from Planchet pass
            context: StructuredContext with notes, calendar, etc.

        Returns:
            Rendered prompt string
        """
        return self.render(
            "pass4_mousqueton",
            event=event,
            previous_passes=[
                grimaud_result,
                bazin_result,
                planchet_result,
            ],  # Template expects previous_passes
            full_context=context,  # Template expects full_context
            briefing=self._get_briefing(),
        )

    # ==================== Cache-Optimized Rendering (v3.1) ====================
    #
    # These methods return SplitPrompt with separate system/user prompts
    # to enable Anthropic API prompt caching.
    #
    # System prompt: Static instructions (cacheable, ~70% of tokens)
    # User prompt: Dynamic data (event, context, previous results)

    def render_grimaud_split(
        self,
        event: Any,
        max_content_chars: int = 8000,
    ) -> SplitPrompt:
        """
        Render Grimaud (Pass 1) with cache optimization.

        Returns separate system and user prompts for Anthropic cache.

        Args:
            event: PerceivedEvent to analyze
            max_content_chars: Maximum content length

        Returns:
            SplitPrompt with system and user parts
        """
        system = self.render("pass1_grimaud_system")
        user = self.render(
            "pass1_grimaud_user",
            event=event,
            max_content_chars=max_content_chars,
            briefing=self._get_briefing(),
        )
        return SplitPrompt(system=system, user=user)

    def render_bazin_split(
        self,
        event: Any,
        grimaud_result: dict,
        context: Any,
        max_content_chars: int = 8000,
        max_context_notes: int = 5,
    ) -> SplitPrompt:
        """
        Render Bazin (Pass 2) with cache optimization.

        Returns separate system and user prompts for Anthropic cache.

        Args:
            event: PerceivedEvent to analyze
            grimaud_result: Result from Grimaud pass
            context: StructuredContext with notes, calendar, etc.
            max_content_chars: Maximum content length
            max_context_notes: Maximum notes to include

        Returns:
            SplitPrompt with system and user parts
        """
        system = self.render("pass2_bazin_system")
        user = self.render(
            "pass2_bazin_user",
            event=event,
            previous_result=grimaud_result,
            context=context,
            max_content_chars=max_content_chars,
            max_context_notes=max_context_notes,
            briefing=self._get_briefing(),
        )
        return SplitPrompt(system=system, user=user)

    def render_planchet_split(
        self,
        event: Any,
        grimaud_result: dict,
        bazin_result: dict,
        context: Any,
        max_content_chars: int = 8000,
    ) -> SplitPrompt:
        """
        Render Planchet (Pass 3) with cache optimization.

        Returns separate system and user prompts for Anthropic cache.

        Args:
            event: PerceivedEvent to analyze
            grimaud_result: Result from Grimaud pass
            bazin_result: Result from Bazin pass
            context: StructuredContext with notes, calendar, etc.
            max_content_chars: Maximum content length

        Returns:
            SplitPrompt with system and user parts
        """
        system = self.render("pass3_planchet_system")
        user = self.render(
            "pass3_planchet_user",
            event=event,
            previous_passes=[grimaud_result, bazin_result],
            context=context,
            max_content_chars=max_content_chars,
            briefing=self._get_briefing(),
        )
        return SplitPrompt(system=system, user=user)

    def render_mousqueton_split(
        self,
        event: Any,
        grimaud_result: dict,
        bazin_result: dict,
        planchet_result: dict,
        context: Any,
    ) -> SplitPrompt:
        """
        Render Mousqueton (Pass 4) with cache optimization.

        Returns separate system and user prompts for Anthropic cache.

        Args:
            event: PerceivedEvent to analyze
            grimaud_result: Result from Grimaud pass
            bazin_result: Result from Bazin pass
            planchet_result: Result from Planchet pass
            context: StructuredContext with notes, calendar, etc.

        Returns:
            SplitPrompt with system and user parts
        """
        system = self.render("pass4_mousqueton_system")
        user = self.render(
            "pass4_mousqueton_user",
            event=event,
            previous_passes=[grimaud_result, bazin_result, planchet_result],
            full_context=context,
            briefing=self._get_briefing(),
        )
        return SplitPrompt(system=system, user=user)

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
