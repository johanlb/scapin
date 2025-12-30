"""
Tests for AI Model Selector

Tests the intelligent model selection system that dynamically chooses
the best Claude model based on use case and tier (Haiku/Sonnet/Opus).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.ai.model_selector import ModelSelector, ModelTier


class TestModelTier:
    """Test ModelTier enum"""

    def test_model_tier_values(self):
        """Test that ModelTier has correct values"""
        assert ModelTier.HAIKU.value == "haiku"
        assert ModelTier.SONNET.value == "sonnet"
        assert ModelTier.OPUS.value == "opus"

    def test_model_tier_string_conversion(self):
        """Test ModelTier can be used as strings"""
        assert ModelTier.HAIKU.value == "haiku"
        assert ModelTier.SONNET.value == "sonnet"
        assert ModelTier.OPUS.value == "opus"


class TestModelSelectorInit:
    """Test ModelSelector initialization"""

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        selector = ModelSelector(api_key="test-key")
        assert selector.client is not None
        assert selector._available_models is None

    def test_init_creates_anthropic_client(self):
        """Test that initialization creates Anthropic client"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            selector = ModelSelector(api_key="test-key")
            mock_anthropic.assert_called_once_with(api_key="test-key")


class TestFetchAvailableModels:
    """Test fetching available models from API"""

    def test_fetch_models_from_api(self):
        """Test fetching models from Anthropic API"""
        mock_model1 = Mock()
        mock_model1.id = "claude-haiku-4-5-20251001"
        mock_model1.created_at = datetime(2025, 10, 1)

        mock_model2 = Mock()
        mock_model2.id = "claude-sonnet-4-5-20250929"
        mock_model2.created_at = datetime(2025, 9, 29)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = [mock_model1, mock_model2]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            models = selector._fetch_available_models()

            assert len(models) == 2
            assert models[0].id == "claude-haiku-4-5-20251001"
            assert models[1].id == "claude-sonnet-4-5-20250929"

    def test_fetch_models_caches_result(self):
        """Test that fetching models caches the result"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = []
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")

            # First call
            selector._fetch_available_models()
            # Second call
            selector._fetch_available_models()

            # Should only call API once due to caching
            assert mock_client.models.list.call_count == 1

    def test_fetch_models_handles_api_error(self):
        """Test handling of API errors during model fetch"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            models = selector._fetch_available_models()

            # Should return empty list on error
            assert models == []


class TestGetLatestByTier:
    """Test getting latest model by tier"""

    def test_get_latest_haiku(self):
        """Test getting latest Haiku model"""
        mock_haiku_old = Mock()
        mock_haiku_old.id = "claude-3-haiku-20240307"
        mock_haiku_old.created_at = datetime(2024, 3, 7)

        mock_haiku_new = Mock()
        mock_haiku_new.id = "claude-haiku-4-5-20251001"
        mock_haiku_new.created_at = datetime(2025, 10, 1)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = [mock_haiku_old, mock_haiku_new]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            latest = selector.get_latest_by_tier(ModelTier.HAIKU)

            # Should return the newest Haiku
            assert latest == "claude-haiku-4-5-20251001"

    def test_get_latest_sonnet(self):
        """Test getting latest Sonnet model"""
        mock_sonnet = Mock()
        mock_sonnet.id = "claude-sonnet-4-5-20250929"
        mock_sonnet.created_at = datetime(2025, 9, 29)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = [mock_sonnet]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            latest = selector.get_latest_by_tier(ModelTier.SONNET)

            assert latest == "claude-sonnet-4-5-20250929"

    def test_get_latest_opus(self):
        """Test getting latest Opus model"""
        mock_opus = Mock()
        mock_opus.id = "claude-opus-4-5-20251101"
        mock_opus.created_at = datetime(2025, 11, 1)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = [mock_opus]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            latest = selector.get_latest_by_tier(ModelTier.OPUS)

            assert latest == "claude-opus-4-5-20251101"

    def test_get_latest_filters_by_tier(self):
        """Test that get_latest_by_tier filters models correctly"""
        mock_haiku = Mock()
        mock_haiku.id = "claude-haiku-4-5-20251001"
        mock_haiku.created_at = datetime(2025, 10, 1)

        mock_sonnet = Mock()
        mock_sonnet.id = "claude-sonnet-4-5-20250929"
        mock_sonnet.created_at = datetime(2025, 9, 29)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = [mock_haiku, mock_sonnet]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")

            # Should only return Haiku, not Sonnet
            haiku = selector.get_latest_by_tier(ModelTier.HAIKU)
            assert "haiku" in haiku.lower()
            assert "sonnet" not in haiku.lower()

    def test_get_latest_returns_fallback_when_api_fails(self):
        """Test fallback to static models when API fails"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            latest = selector.get_latest_by_tier(ModelTier.HAIKU)

            # Should return first fallback model
            assert latest in selector.FALLBACK_MODELS[ModelTier.HAIKU]

    def test_get_latest_returns_fallback_when_no_models(self):
        """Test fallback when no models of requested tier"""
        mock_opus = Mock()
        mock_opus.id = "claude-opus-4-5-20251101"
        mock_opus.created_at = datetime(2025, 11, 1)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            # Only Opus model available
            mock_client.models.list.return_value = [mock_opus]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            # Request Haiku when only Opus available
            latest = selector.get_latest_by_tier(ModelTier.HAIKU)

            # Should fallback to static model
            assert latest in selector.FALLBACK_MODELS[ModelTier.HAIKU]


class TestGetBestModel:
    """Test getting best model with fallback tiers"""

    def test_get_best_model_returns_preferred_tier(self):
        """Test that preferred tier is returned when available"""
        mock_haiku = Mock()
        mock_haiku.id = "claude-haiku-4-5-20251001"
        mock_haiku.created_at = datetime(2025, 10, 1)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = [mock_haiku]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")
            model = selector.get_best_model(ModelTier.HAIKU)

            assert model == "claude-haiku-4-5-20251001"

    def test_get_best_model_uses_fallback_tier(self):
        """Test fallback to alternative tier when preferred unavailable"""
        mock_sonnet = Mock()
        mock_sonnet.id = "claude-sonnet-4-5-20250929"
        mock_sonnet.created_at = datetime(2025, 9, 29)

        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            # Only Sonnet available, no Haiku
            mock_client.models.list.return_value = [mock_sonnet]
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")

            # Mock get_latest_by_tier to return None for Haiku, Sonnet for Sonnet
            original_get_latest = selector.get_latest_by_tier

            def mock_get_latest(tier):
                if tier == ModelTier.HAIKU:
                    return None  # Haiku not available
                return original_get_latest(tier)

            selector.get_latest_by_tier = mock_get_latest

            # Request Haiku with Sonnet fallback
            model = selector.get_best_model(
                tier=ModelTier.HAIKU,
                fallback_tiers=[ModelTier.SONNET]
            )

            # Should get Sonnet as fallback
            assert "sonnet" in model.lower()

    def test_get_best_model_tries_multiple_fallbacks(self):
        """Test trying multiple fallback tiers in order"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.return_value = []
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")

            # All API calls fail, should use static fallback
            model = selector.get_best_model(
                tier=ModelTier.HAIKU,
                fallback_tiers=[ModelTier.SONNET, ModelTier.OPUS]
            )

            # Should return a valid model (from static fallback)
            assert model is not None
            assert isinstance(model, str)
            assert len(model) > 0

    def test_get_best_model_always_returns_something(self):
        """Test that get_best_model always returns a model (never None)"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.models.list.side_effect = Exception("Total API failure")
            mock_anthropic.return_value = mock_client

            selector = ModelSelector(api_key="test-key")

            # Even with total failure, should return hardcoded fallback
            model = selector.get_best_model(ModelTier.HAIKU)

            assert model is not None
            assert isinstance(model, str)
            assert "claude" in model.lower()


class TestFallbackModels:
    """Test static fallback model lists"""

    def test_fallback_models_defined(self):
        """Test that fallback models are defined for all tiers"""
        assert ModelTier.HAIKU in ModelSelector.FALLBACK_MODELS
        assert ModelTier.SONNET in ModelSelector.FALLBACK_MODELS
        assert ModelTier.OPUS in ModelSelector.FALLBACK_MODELS

    def test_fallback_models_non_empty(self):
        """Test that each tier has at least one fallback model"""
        for tier in [ModelTier.HAIKU, ModelTier.SONNET, ModelTier.OPUS]:
            fallbacks = ModelSelector.FALLBACK_MODELS[tier]
            assert len(fallbacks) > 0

    def test_fallback_models_ordered_newest_first(self):
        """Test that fallback models are ordered newest to oldest"""
        # Haiku fallbacks should start with 4.5, then 3.5, then 3
        haiku_fallbacks = ModelSelector.FALLBACK_MODELS[ModelTier.HAIKU]
        assert "4-5" in haiku_fallbacks[0] or "4.5" in haiku_fallbacks[0]

        # Sonnet fallbacks should start with 4.5 or 4
        sonnet_fallbacks = ModelSelector.FALLBACK_MODELS[ModelTier.SONNET]
        assert "4" in sonnet_fallbacks[0]

        # Opus fallbacks should start with 4.5 or 4
        opus_fallbacks = ModelSelector.FALLBACK_MODELS[ModelTier.OPUS]
        assert "4" in opus_fallbacks[0]

    def test_fallback_models_contain_tier_name(self):
        """Test that fallback models contain their tier name"""
        for tier, models in ModelSelector.FALLBACK_MODELS.items():
            for model in models:
                # Each model should contain its tier name (haiku/sonnet/opus)
                assert tier.value.lower() in model.lower()
