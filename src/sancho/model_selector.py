"""
AI Model Selector

Intelligent model selection based on use case.
Dynamically fetches available models from Anthropic API and selects
the most appropriate model (Opus, Sonnet, or Haiku) based on task requirements.
"""

from enum import Enum
from typing import Optional

import anthropic

from src.monitoring.logger import get_logger

logger = get_logger("model_selector")


class ModelTier(str, Enum):
    """
    Model tiers for different use cases.

    Multi-Pass v2.2 Architecture:
    - HAIKU: Pass 1-3 (blind extraction, contextual refinement)
    - SONNET: Pass 4 (deep reasoning when confidence < 80%)
    - OPUS: Pass 5 (expert analysis when confidence < 75% OR high-stakes)

    Cost/Speed Tradeoffs:
    - HAIKU: ~$0.25/1M tokens, 1-2s — Fast, economical
    - SONNET: ~$3/1M tokens, 2-4s — Balanced
    - OPUS: ~$15/1M tokens, 4-8s — Powerful, thorough
    """
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"

    @classmethod
    def for_pass(cls, pass_number: int) -> "ModelTier":
        """
        Get the default model tier for a given pass number.

        This is the baseline; actual selection may escalate based on confidence.

        Args:
            pass_number: Pass number (1-5)

        Returns:
            Default ModelTier for that pass
        """
        if pass_number <= 3:
            return cls.HAIKU
        if pass_number == 4:
            return cls.SONNET
        return cls.OPUS


class ModelSelector:
    """
    Intelligent model selector that chooses the best model based on use case

    Usage:
        selector = ModelSelector(api_key)
        model = selector.get_best_model(ModelTier.HAIKU)  # For health checks
        model = selector.get_best_model(ModelTier.SONNET)  # For email processing
        model = selector.get_best_model(ModelTier.OPUS)    # For complex analysis
    """

    # Static fallback models (ordered newest to oldest per tier)
    FALLBACK_MODELS = {
        ModelTier.HAIKU: [
            "claude-haiku-4-5-20251001",
            "claude-3-5-haiku-20241022",
            "claude-3-haiku-20240307",
        ],
        ModelTier.SONNET: [
            "claude-sonnet-4-5-20250929",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
        ],
        ModelTier.OPUS: [
            "claude-opus-4-5-20251101",
            "claude-opus-4-1-20250805",
            "claude-opus-4-20250514",
        ],
    }

    def __init__(self, api_key: str):
        """
        Initialize model selector

        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self._available_models = None

    def _fetch_available_models(self) -> list:
        """
        Fetch available models from Anthropic API

        Returns:
            List of ModelInfo objects
        """
        if self._available_models is None:
            try:
                self._available_models = list(self.client.models.list())
                logger.debug(f"Fetched {len(self._available_models)} available models from API")
            except Exception as e:
                logger.warning(f"Failed to fetch models from API: {e}")
                self._available_models = []

        return self._available_models

    def get_latest_by_tier(self, tier: ModelTier) -> Optional[str]:
        """
        Get the latest version of a specific model tier

        Args:
            tier: Model tier (HAIKU, SONNET, or OPUS)

        Returns:
            Model ID of the latest version, or None if not found
        """
        available_models = self._fetch_available_models()

        # If API fetch failed, use fallback
        if not available_models:
            fallback = self.FALLBACK_MODELS.get(tier, [])
            return fallback[0] if fallback else None

        # Filter models by tier
        filtered = [m for m in available_models if tier.value.lower() in m.id.lower()]

        if not filtered:
            logger.warning(f"No {tier.value} models found in API response")
            fallback = self.FALLBACK_MODELS.get(tier, [])
            return fallback[0] if fallback else None

        # Sort by creation date (newest first) and return the first one
        latest = sorted(filtered, key=lambda m: m.created_at, reverse=True)[0]
        logger.debug(f"Selected {tier.value} model: {latest.id}")
        return latest.id

    def get_best_model(self, tier: ModelTier, fallback_tiers: Optional[list[ModelTier]] = None) -> str:
        """
        Get the best available model for a given tier with fallback options

        Args:
            tier: Preferred model tier
            fallback_tiers: Optional list of fallback tiers if preferred tier fails

        Returns:
            Model ID (guaranteed to return something)

        Example:
            # Try Haiku first, fallback to Sonnet if not available
            model = selector.get_best_model(ModelTier.HAIKU, [ModelTier.SONNET])
        """
        # Try preferred tier
        model = self.get_latest_by_tier(tier)
        if model:
            return model

        # Try fallback tiers
        if fallback_tiers:
            for fallback_tier in fallback_tiers:
                model = self.get_latest_by_tier(fallback_tier)
                if model:
                    logger.info(f"Using fallback tier {fallback_tier.value} instead of {tier.value}")
                    return model

        # Last resort: return first available model from static fallback
        for tier_fallback in [tier] + (fallback_tiers or []):
            fallback_list = self.FALLBACK_MODELS.get(tier_fallback, [])
            if fallback_list:
                logger.warning(f"Using static fallback model: {fallback_list[0]}")
                return fallback_list[0]

        # Absolute fallback (should never happen)
        logger.error("No models available - using hardcoded fallback")
        return "claude-3-haiku-20240307"


# Use cases documentation
"""
MODEL SELECTION GUIDE (v2.2)
============================

MULTI-PASS ARCHITECTURE
-----------------------
The v2.2 multi-pass analysis uses automatic model escalation:

Pass 1-3 (HAIKU):
- Blind extraction (no context)
- Contextual refinement (with PKM context)
- Target: 95% confidence with 2-3 passes
- Cost: ~$0.001-0.003 per email

Pass 4 (SONNET):
- Deep reasoning for complex cases
- Triggered when: confidence < 80% after Pass 3
- Resolves ambiguities Haiku couldn't handle
- Cost: ~$0.015 per escalated email

Pass 5 (OPUS):
- Expert analysis for critical decisions
- Triggered when: confidence < 75% OR high-stakes
- High-stakes = VIP sender, >10k€, deadline <48h
- Cost: ~$0.08 per critical email

HAIKU (Fast & Economical)
-------------------------
Best for:
- Pass 1-3 in multi-pass analysis
- Health checks (count_tokens, connectivity tests)
- Simple categorization
- Quick responses
- High-volume, low-complexity tasks
- Draft generation

Cost: ~$0.25 / 1M input tokens
Speed: Fastest (~1-2s for typical tasks)

SONNET (Balanced)
-----------------
Best for:
- Pass 4 deep reasoning
- Email analysis and classification
- Medium complexity reasoning
- Content summarization
- General-purpose processing
- Most production workloads

Cost: ~$3 / 1M input tokens
Speed: Medium (~2-4s for typical tasks)

OPUS (Powerful & Thorough)
---------------------------
Best for:
- Pass 5 expert analysis
- High-stakes decisions (money, VIPs, legal)
- Complex decision making
- Critical email routing
- Detailed analysis requiring nuance
- Tasks where accuracy is paramount

Cost: ~$15 / 1M input tokens
Speed: Slower (~4-8s for typical tasks)

RECOMMENDATION
--------------
Use MultiPassAnalyzer for email processing (automatic escalation).
For direct API calls:
- HAIKU for simple tasks
- SONNET for medium complexity
- OPUS for critical decisions
"""
