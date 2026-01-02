"""
Tests for AI Provider abstraction (C1-3)

Covers:
- IAIProvider interface contract
- AnthropicProvider implementation
- Provider exception handling
- Cost estimation
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.sancho.providers.anthropic_provider import AnthropicProvider
from src.sancho.providers.base import (
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderModel,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderUsage,
)


class TestProviderDataclasses:
    """Test provider data structures"""

    def test_provider_usage_immutable(self):
        """Test ProviderUsage is frozen/immutable"""
        usage = ProviderUsage(
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
            cost_usd=0.05,
        )

        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.total_tokens == 300
        assert usage.cost_usd == 0.05

        # Should be frozen
        with pytest.raises(AttributeError):
            usage.input_tokens = 999

    def test_provider_response_immutable(self):
        """Test ProviderResponse is frozen/immutable"""
        usage = ProviderUsage(
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
        )

        response = ProviderResponse(
            text="Test response",
            usage=usage,
            model="claude-3-5-haiku-20241022",
            provider="anthropic",
        )

        assert response.text == "Test response"
        assert response.provider == "anthropic"

        # Should be frozen
        with pytest.raises(AttributeError):
            response.text = "Modified"


class TestAnthropicProvider:
    """Test Anthropic provider implementation"""

    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

            assert provider.provider_name == "anthropic"
            assert len(provider.available_models) >= 3

    def test_init_with_invalid_api_key_format(self):
        """Test initialization fails with invalid API key format"""
        with pytest.raises(ProviderAuthenticationError):
            AnthropicProvider(api_key="invalid-key")

        with pytest.raises(ProviderAuthenticationError):
            AnthropicProvider(api_key="")

    def test_get_model_for_tier(self):
        """Test model selection by tier"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

            assert provider.get_model_for_tier(ProviderModel.FAST) == "claude-3-5-haiku-20241022"
            assert provider.get_model_for_tier(ProviderModel.BALANCED) == "claude-3-5-sonnet-20241022"
            assert provider.get_model_for_tier(ProviderModel.ADVANCED) == "claude-opus-4-20250514"

    def test_complete_success(self):
        """Test successful completion"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_message = Mock()
        mock_message.content = [Mock(text="This is a test response")]
        mock_message.usage = Mock(input_tokens=100, output_tokens=50)
        mock_message.id = "msg-123"
        mock_message.model = "claude-3-5-haiku-20241022"
        mock_message.role = "assistant"
        mock_message.stop_reason = "end_turn"

        mock_client.messages.create.return_value = mock_message

        with patch('anthropic.Anthropic', return_value=mock_client):
            provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

            response = provider.complete(
                prompt="Test prompt",
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
            )

            assert isinstance(response, ProviderResponse)
            assert response.text == "This is a test response"
            assert response.usage.input_tokens == 100
            assert response.usage.output_tokens == 50
            assert response.usage.total_tokens == 150
            assert response.model == "claude-3-5-haiku-20241022"
            assert response.provider == "anthropic"

    def test_complete_with_system_prompt(self):
        """Test completion with system prompt"""
        mock_client = MagicMock()
        mock_message = Mock()
        mock_message.content = [Mock(text="Response")]
        mock_message.usage = Mock(input_tokens=100, output_tokens=50)
        mock_message.id = "msg-123"
        mock_message.model = "claude-3-5-haiku-20241022"
        mock_message.role = "assistant"
        mock_message.stop_reason = "end_turn"

        mock_client.messages.create.return_value = mock_message

        with patch('anthropic.Anthropic', return_value=mock_client):
            provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

            response = provider.complete(
                prompt="Test",
                system_prompt="You are a helpful assistant",
            )

            # Verify system prompt was passed
            call_args = mock_client.messages.create.call_args
            assert call_args[1]["system"] == "You are a helpful assistant"

    def test_complete_invalid_model(self):
        """Test completion with invalid model raises error"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

            with pytest.raises(ProviderAPIError, match="Invalid model"):
                provider.complete(
                    prompt="Test",
                    model="invalid-model",
                )

    def test_complete_authentication_error(self):
        """Test completion handles authentication errors"""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("AuthenticationError")

        with patch('anthropic.Anthropic', return_value=mock_client):
            with patch('anthropic.AuthenticationError', Exception):
                provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

                # Inject anthropic module with exceptions
                provider._anthropic.AuthenticationError = type('AuthenticationError', (Exception,), {})
                mock_client.messages.create.side_effect = provider._anthropic.AuthenticationError("Invalid API key")

                with pytest.raises(ProviderAuthenticationError):
                    provider.complete(prompt="Test")

    def test_estimate_cost(self):
        """Test cost estimation"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

            # Test Haiku pricing (cheapest)
            cost = provider.estimate_cost(
                input_tokens=1_000_000,  # 1M tokens
                output_tokens=1_000_000,  # 1M tokens
                model="claude-3-5-haiku-20241022",
            )

            # Expected: 1M * $0.80 + 1M * $4.00 = $4.80
            assert cost == pytest.approx(4.80, rel=0.01)

            # Test Sonnet pricing
            cost = provider.estimate_cost(
                input_tokens=1_000_000,
                output_tokens=1_000_000,
                model="claude-3-5-sonnet-20241022",
            )

            # Expected: 1M * $3.00 + 1M * $15.00 = $18.00
            assert cost == pytest.approx(18.00, rel=0.01)

    def test_estimate_cost_unknown_model_fallback(self):
        """Test cost estimation falls back to Haiku for unknown models"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(api_key="sk-ant-test-key-12345")

            cost = provider.estimate_cost(
                input_tokens=1_000_000,
                output_tokens=1_000_000,
                model="unknown-model",
            )

            # Should use Haiku pricing as fallback
            expected = 1_000_000 / 1_000_000 * 0.80 + 1_000_000 / 1_000_000 * 4.00
            assert cost == pytest.approx(expected, rel=0.01)


class TestProviderExceptions:
    """Test provider exception hierarchy"""

    def test_provider_exceptions_inherit_correctly(self):
        """Test exception hierarchy"""
        from src.sancho.providers.base import ProviderError

        # All exceptions should inherit from ProviderError
        assert issubclass(ProviderAuthenticationError, ProviderError)
        assert issubclass(ProviderRateLimitError, ProviderError)
        assert issubclass(ProviderAPIError, ProviderError)
        assert issubclass(ProviderConnectionError, ProviderError)

    def test_exceptions_can_be_raised_and_caught(self):
        """Test exceptions can be raised and caught"""
        with pytest.raises(ProviderAuthenticationError):
            raise ProviderAuthenticationError("Test auth error")

        with pytest.raises(ProviderRateLimitError):
            raise ProviderRateLimitError("Test rate limit error")

        with pytest.raises(ProviderAPIError):
            raise ProviderAPIError("Test API error")

        with pytest.raises(ProviderConnectionError):
            raise ProviderConnectionError("Test connection error")
