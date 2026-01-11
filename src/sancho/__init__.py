"""
Sancho - AI Routing Module

The AI routing and model selection component of Scapin's architecture.

Named after Sancho Panza from Don Quixote - the wise, pragmatic companion
who provides grounded reasoning and sound judgment.

Includes:
- AI routing with rate limiting
- Model selection (Haiku → Sonnet escalation)
- Template management for prompts
- Provider abstractions (Anthropic, etc.)

Note: For multi-pass reasoning with context enrichment, use V2EmailProcessor
which integrates Sancho routing with CrossSourceEngine and PatternStore.
"""

from src.sancho.model_selector import ModelSelector, ModelTier
from src.sancho.router import AIModel, AIRouter, RateLimiter, get_ai_router
from src.sancho.templates import TemplateManager, get_template_manager

__all__ = [
    # Router
    "AIModel",
    "AIRouter",
    "RateLimiter",
    "get_ai_router",
    # Model Selection
    "ModelSelector",
    "ModelTier",
    # Templates
    "TemplateManager",
    "get_template_manager",
]
