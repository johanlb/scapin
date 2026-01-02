"""
Anthropic Provider Implementation

Implements IAIProvider for Anthropic Claude models.
"""

from typing import Optional

import anthropic

from src.ai.providers.base import (
    IAIProvider,
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderModel,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderUsage,
)
from src.monitoring.logger import get_logger

logger = get_logger("anthropic_provider")


# Anthropic model pricing (per million tokens) - Updated 2024
ANTHROPIC_PRICING = {
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
}


class AnthropicProvider(IAIProvider):
    """
    Anthropic Claude provider implementation

    Supports Claude 3.5 Haiku, Sonnet, and Opus 4 models.

    Usage:
        provider = AnthropicProvider(api_key="sk-ant-...")
        response = provider.complete(
            prompt="Analyze this email...",
            model="claude-3-5-haiku-20241022"
        )
    """

    def __init__(self, api_key: str):
        """
        Initialize Anthropic provider

        Args:
            api_key: Anthropic API key

        Raises:
            ImportError: If anthropic package not installed
            ProviderAuthenticationError: If API key invalid
        """
        if not api_key or not api_key.startswith("sk-ant-"):
            raise ProviderAuthenticationError(
                "Invalid Anthropic API key format. "
                "Keys should start with 'sk-ant-'"
            )

        try:
            self._client = anthropic.Anthropic(api_key=api_key)
            self._anthropic = anthropic  # Save for exception handling
            logger.info("Anthropic provider initialized")
        except ImportError as e:
            raise ImportError(
                "anthropic package not installed. "
                "Run: pip install anthropic"
            ) from e

    @property
    def provider_name(self) -> str:
        """Get provider name"""
        return "anthropic"

    @property
    def available_models(self) -> list[str]:
        """Get list of available models"""
        return [
            "claude-3-5-haiku-20241022",
            "claude-3-5-sonnet-20241022",
            "claude-opus-4-20250514",
        ]

    def get_model_for_tier(self, tier: ProviderModel) -> str:
        """
        Get best model for a given tier

        Args:
            tier: Model tier

        Returns:
            Model identifier
        """
        tier_mapping = {
            ProviderModel.FAST: "claude-3-5-haiku-20241022",
            ProviderModel.BALANCED: "claude-3-5-sonnet-20241022",
            ProviderModel.ADVANCED: "claude-opus-4-20250514",
        }
        return tier_mapping.get(tier, "claude-3-5-haiku-20241022")

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
        Generate completion using Claude

        Args:
            prompt: User prompt
            model: Model identifier (defaults to Haiku)
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional Anthropic-specific options

        Returns:
            ProviderResponse with completion

        Raises:
            ProviderAuthenticationError: If API key invalid
            ProviderRateLimitError: If rate limit exceeded
            ProviderAPIError: For other API errors
        """
        # Default to fast model
        if model is None:
            model = self.get_model_for_tier(ProviderModel.FAST)

        # Validate model
        if model not in self.available_models:
            raise ProviderAPIError(
                f"Invalid model: {model}. "
                f"Available models: {', '.join(self.available_models)}"
            )

        # Build message
        messages = [{"role": "user", "content": prompt}]

        # Build request parameters
        request_params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system_prompt:
            request_params["system"] = system_prompt

        # Add any additional kwargs
        request_params.update(kwargs)

        # Make API call
        try:
            logger.debug(
                "Calling Anthropic API",
                extra={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )

            message = self._client.messages.create(**request_params)

            # Extract text from response
            text_content = ""
            for block in message.content:
                if hasattr(block, "text"):
                    text_content += block.text

            # Extract usage
            input_tokens = message.usage.input_tokens if hasattr(message, 'usage') else 0
            output_tokens = message.usage.output_tokens if hasattr(message, 'usage') else 0
            total_tokens = input_tokens + output_tokens

            # Calculate cost
            cost = self.estimate_cost(input_tokens, output_tokens, model)

            usage = ProviderUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
            )

            logger.debug(
                "Anthropic API call successful",
                extra={
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": f"${cost:.4f}",
                }
            )

            return ProviderResponse(
                text=text_content,
                usage=usage,
                model=model,
                provider=self.provider_name,
                raw_response={
                    "id": message.id,
                    "model": message.model,
                    "role": message.role,
                    "stop_reason": message.stop_reason,
                },
            )

        # Map Anthropic exceptions to provider exceptions
        except self._anthropic.AuthenticationError as e:
            raise ProviderAuthenticationError(
                f"Anthropic authentication failed: {e}"
            ) from e

        except self._anthropic.RateLimitError as e:
            raise ProviderRateLimitError(
                f"Anthropic rate limit exceeded: {e}"
            ) from e

        except self._anthropic.APIConnectionError as e:
            raise ProviderConnectionError(
                f"Failed to connect to Anthropic API: {e}"
            ) from e

        except self._anthropic.APIError as e:
            raise ProviderAPIError(
                f"Anthropic API error: {e}"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error calling Anthropic API: {e}", exc_info=True)
            raise ProviderAPIError(
                f"Unexpected error: {e}"
            ) from e

    def validate_api_key(self) -> bool:
        """
        Validate API key by making a small test request

        Returns:
            True if API key is valid

        Raises:
            ProviderAuthenticationError: If API key invalid
        """
        try:
            # Make minimal API call to validate key
            self.complete(
                prompt="Test",
                max_tokens=1,
                temperature=0.0,
            )
            logger.info("Anthropic API key validated successfully")
            return True

        except ProviderAuthenticationError:
            raise

        except Exception as e:
            logger.warning(f"API key validation failed: {e}")
            return False

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
        if model not in ANTHROPIC_PRICING:
            logger.warning(
                f"No pricing info for model: {model}, using Haiku pricing"
            )
            model = "claude-3-5-haiku-20241022"

        pricing = ANTHROPIC_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
