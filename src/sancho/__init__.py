"""
Sancho - AI Reasoning Module

The AI reasoning and model selection component of Scapin's architecture.

Named after Sancho Panza from Don Quixote - the wise, pragmatic companion
who provides grounded reasoning and sound judgment.

Includes:
- AI routing with rate limiting
- Model selection (Haiku → Sonnet → Opus escalation)
- Multi-pass analysis with convergence logic
- Template management for prompts
- Provider abstractions (Anthropic, etc.)

Multi-Pass Architecture (v2.2):
- Pass 1: Blind extraction (Haiku)
- Pass 2-3: Contextual refinement (Haiku)
- Pass 4: Deep reasoning (Sonnet)
- Pass 5: Expert analysis (Opus)
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
    # Convergence (Multi-Pass v2.2)
    "AnalysisContext",
    "DecomposedConfidence",
    "Extraction",
    "MultiPassConfig",
    "PassResult",
    "PassType",
    "get_pass_type",
    "get_pass_ui_name",
    "get_status_message",
    "is_high_stakes",
    "select_model",
    "should_stop",
    "targeted_escalation",
]
