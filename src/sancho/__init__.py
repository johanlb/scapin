"""
Sancho - Reasoning Module

The wisdom and reasoning component of Scapin's cognitive architecture.

Named after Sancho Panza from Don Quixote - the wise, pragmatic companion
who provides grounded reasoning and sound judgment.

Sancho performs iterative multi-pass reasoning to achieve high-confidence
decisions through:
- Initial quick analysis
- Context enrichment from knowledge base
- Deep multi-step reasoning
- Cross-provider validation
- User clarification when needed

Includes:
- AI routing and model selection
- Template management for prompts
- Provider abstractions (Anthropic, etc.)
"""

from src.sancho.model_selector import ModelSelector, ModelTier
from src.sancho.reasoning_engine import ReasoningEngine, ReasoningResult
from src.sancho.router import AIModel, AIRouter, RateLimiter, get_ai_router
from src.sancho.templates import TemplateManager, get_template_manager

__all__ = [
    # Reasoning
    "ReasoningEngine",
    "ReasoningResult",
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
