"""
Base AI Provider Interface

Defines the contract that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ProviderModel(str, Enum):
    """Provider-agnostic model tiers"""
    FAST = "fast"  # Haiku, GPT-4o-mini, Mistral Small
    BALANCED = "balanced"  # Sonnet, GPT-4o, Mistral Medium
    ADVANCED = "advanced"  # Opus, O1, Mistral Large


@dataclass(frozen=True)
class ProviderUsage:
    """
    Token usage information from provider

    All providers should return usage in this format for consistency.
    """
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float = 0.0  # Estimated cost


@dataclass(frozen=True)
class ProviderResponse:
    """
    Standardized response from any AI provider

    This abstraction allows switching providers without changing
    calling code.
    """
    text: str  # Response text
    usage: ProviderUsage  # Token usage
    model: str  # Actual model used
    provider: str  # Provider name (anthropic, openai, etc.)
    raw_response: Optional[dict[str, Any]] = None  # Raw provider response


class IAIProvider(ABC):
    """
    Abstract interface for AI providers

    All AI providers (Anthropic, OpenAI, Mistral, Ollama, etc.) must
    implement this interface to ensure consistency.

    Benefits:
    - Easy to swap providers
    - Testable with MockProvider
    - Unified error handling
    - Consistent metrics tracking
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get provider name

        Returns:
            Provider name (e.g., "anthropic", "openai")
        """
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """
        Get list of available models

        Returns:
            List of model identifiers
        """
        pass

    @abstractmethod
    def get_model_for_tier(self, tier: ProviderModel) -> str:
        """
        Get best model for a given tier

        Args:
            tier: Model tier (FAST, BALANCED, ADVANCED)

        Returns:
            Model identifier for this tier
        """
        pass

    @abstractmethod
    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> ProviderResponse:
        """
        Generate completion for prompt

        Args:
            prompt: User prompt
            model: Model identifier (if None, uses default)
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)
            **kwargs: Provider-specific options

        Returns:
            ProviderResponse with text and usage

        Raises:
            ProviderAuthenticationError: If API key invalid
            ProviderRateLimitError: If rate limit exceeded
            ProviderAPIError: For other API errors
        """
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """
        Validate API key is configured and working

        Returns:
            True if API key is valid

        Raises:
            ProviderAuthenticationError: If API key invalid
        """
        pass

    @abstractmethod
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> float:
        """
        Estimate cost for token usage

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        pass


# Provider-specific exceptions (inherit from standard errors for compatibility)


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class ProviderAuthenticationError(ProviderError):
    """API key authentication failed"""
    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded"""
    pass


class ProviderAPIError(ProviderError):
    """General API error"""
    pass


class ProviderConnectionError(ProviderError):
    """Connection to provider failed"""
    pass
