"""
Scapin Template Manager

Gestionnaire de templates pour:
- Prompts AI (analyse email, extraction knowledge)
- Templates d'emails
- Messages système

Utilise Jinja2 pour templating flexible.
"""

import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from src.monitoring.logger import get_logger

logger = get_logger("templates")


class TemplateType(str, Enum):
    """Types de templates"""

    # AI Prompts
    EMAIL_ANALYSIS = "email_analysis"
    EMAIL_CONVERSATION = "email_conversation"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    DECISION_REVIEW = "decision_review"

    # Email Templates
    EMAIL_RESPONSE = "email_response"
    EMAIL_SUMMARY = "email_summary"

    # System Messages
    SYSTEM_PROMPT = "system_prompt"
    ERROR_MESSAGE = "error_message"


class TemplateManager:
    """
    Gestionnaire de templates avec Jinja2

    Usage:
        tm = TemplateManager()
        prompt = tm.render("email_analysis", {
            "subject": "Meeting tomorrow",
            "from": "john@example.com",
            "body": "..."
        })
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize template manager

        Args:
            templates_dir: Directory containing templates (default: templates/)
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent.parent / "templates"

        self.templates_dir = templates_dir
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # Templates contain prompts, not HTML
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Custom filters
        self.env.filters["truncate_smart"] = self._truncate_smart

        # In-memory template cache for performance (thread-safe)
        self._template_cache: dict[str, Template] = {}
        self._cache_lock = threading.Lock()

        logger.info(
            "Template manager initialized", extra={"templates_dir": str(self.templates_dir)}
        )

    @staticmethod
    def _truncate_smart(text: str, length: int = 500, suffix: str = "...") -> str:
        """
        Truncate text intelligently (at word boundary)

        Args:
            text: Text to truncate
            length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if len(text) <= length:
            return text

        # Try to truncate at last space before length
        truncated = text[:length].rsplit(" ", 1)[0]
        return truncated + suffix

    def get_template(self, template_name: str) -> Template:
        """
        Get template by name (cached)

        Args:
            template_name: Template name (e.g., "email_analysis.j2")

        Returns:
            Jinja2 Template

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        # Add .j2 extension if not present
        if not template_name.endswith(".j2"):
            template_name = f"{template_name}.j2"

        # Double-check locking for thread-safe cache access
        # First check without lock (fast path)
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        # Acquire lock for cache update
        with self._cache_lock:
            # Check again in case another thread loaded it
            if template_name in self._template_cache:
                return self._template_cache[template_name]

            # Load from filesystem
            try:
                template = self.env.get_template(template_name)
                self._template_cache[template_name] = template
                logger.debug(f"Loaded template: {template_name}")
                return template
            except TemplateNotFound:
                logger.error(f"Template not found: {template_name}")
                raise

    def render(self, template_name: str, **kwargs) -> str:
        """
        Render template with context

        Args:
            template_name: Template name
            **kwargs: Template context variables

        Returns:
            Rendered template string
        """
        try:
            # Ensure 'now' is in context
            kwargs.setdefault("now", datetime.now(timezone.utc))

            template = self.get_template(template_name)
            rendered = template.render(**kwargs)
            logger.debug(
                "Rendered template",
                extra={"template": template_name, "context_keys": list(kwargs.keys())},
            )
            return rendered
        except TemplateNotFound:
            logger.error("Template not found", extra={"template": template_name})
            raise
        except Exception as e:
            logger.error(
                f"Template rendering failed: {e}", extra={"template": template_name}, exc_info=True
            )
            raise

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """
        Render template from string (for dynamic templates)

        Args:
            template_string: Template as string
            context: Template context

        Returns:
            Rendered template
        """
        template = self.env.from_string(template_string)
        return template.render(**context)

    def list_templates(self) -> list[str]:
        """
        List all available templates

        Returns:
            List of template names
        """
        if not self.templates_dir.exists():
            return []

        return [f.name for f in self.templates_dir.glob("**/*.j2")]

    def clear_cache(self) -> None:
        """Clear template cache (thread-safe)"""
        with self._cache_lock:
            self._template_cache.clear()
            logger.debug("Template cache cleared")


# Global template manager instance (thread-safe singleton)
_template_manager: Optional[TemplateManager] = None
_manager_lock = threading.Lock()


def get_template_manager() -> TemplateManager:
    """
    Get global template manager (thread-safe singleton)

    Returns:
        TemplateManager instance
    """
    global _template_manager

    # Double-check locking for thread-safe singleton
    # First check without lock (fast path)
    if _template_manager is not None:
        return _template_manager

    # Acquire lock for initialization
    with _manager_lock:
        # Check again in case another thread initialized it
        if _template_manager is None:
            _template_manager = TemplateManager()
        return _template_manager


# Convenience functions for common templates
def render_email_analysis_prompt(
    subject: str,
    from_address: str,
    body: str,
    preview_mode: bool = False,
    conversation_context: Optional[str] = None,
    entities: Optional[dict[str, list[Any]]] = None,
    context_notes: Optional[list[Any]] = None,
    from_name: Optional[str] = None,
    to_addresses: Optional[str] = None,
    date: Optional[str] = None,
    has_attachments: bool = False,
    existing_folders: Optional[list[str]] = None,
    learned_suggestions: Optional[list[dict[str, Any]]] = None,
) -> str:
    """
    Render email analysis prompt for AI

    Args:
        subject: Email subject
        from_address: Sender address
        body: Email body
        preview_mode: Use preview mode (truncated body)
        conversation_context: Optional conversation context
        entities: Pre-extracted entities by type {"person": [...], "date": [...]}
        context_notes: Notes from knowledge base providing context
        from_name: Sender display name
        to_addresses: Recipients as string
        date: Email date
        has_attachments: Whether email has attachments
        existing_folders: List of existing IMAP folders
        learned_suggestions: Folder suggestions from learning system

    Returns:
        Rendered prompt
    """
    tm = get_template_manager()
    return tm.render(
        "email_analysis",
        subject=subject,
        from_address=from_address,
        from_name=from_name or from_address,
        to_addresses=to_addresses or "",
        date=date or "",
        has_attachments=has_attachments,
        body=body,
        preview_mode=preview_mode,
        conversation_context=conversation_context,
        entities=entities or {},
        context_notes=context_notes or [],
        existing_folders=existing_folders or [],
        learned_suggestions=learned_suggestions or [],
    )


def render_knowledge_extraction_prompt(email_subject: str, email_body: str, category: str) -> str:
    """
    Render knowledge extraction prompt

    Args:
        email_subject: Email subject
        email_body: Email body
        category: Email category

    Returns:
        Rendered prompt
    """
    tm = get_template_manager()
    return tm.render(
        "knowledge_extraction",
        subject=email_subject,
        body=email_body,
        category=category,
    )
