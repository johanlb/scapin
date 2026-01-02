"""
AI Module

Provides AI routing, model selection, and template management for Scapin's
cognitive architecture (Sancho reasoning engine).
"""

from src.ai.router import AIModel, AIRouter, RateLimiter, get_ai_router

__all__ = [
    "AIModel",
    "AIRouter",
    "RateLimiter",
    "get_ai_router",
]
