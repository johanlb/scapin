"""
Tests for AnalysisEngine base class.

Phase 0 of Retouche implementation.
"""

import pytest

from src.sancho.analysis_engine import (
    AICallResult,
    AnalysisEngine,
    AnalysisMetrics,
    JSONParseError,
    ModelTier,
)


class TestModelTier:
    """Test ModelTier enum."""

    def test_values(self):
        """Test enum values."""
        assert ModelTier.HAIKU.value == "haiku"
        assert ModelTier.SONNET.value == "sonnet"
        assert ModelTier.OPUS.value == "opus"


class TestAICallResult:
    """Test AICallResult dataclass."""

    def test_basic_creation(self):
        """Test creating a basic result."""
        result = AICallResult(
            response='{"test": "data"}',
            model_used=ModelTier.HAIKU,
            model_id="claude-3-haiku-20240307",
            tokens_used=100,
            duration_ms=500.0,
        )
        assert result.response == '{"test": "data"}'
        assert result.model_used == ModelTier.HAIKU
        assert result.tokens_used == 100
        assert not result.cache_hit

    def test_cache_hit_flag(self):
        """Test cache hit detection."""
        result = AICallResult(
            response="{}",
            model_used=ModelTier.HAIKU,
            model_id="claude-3-haiku-20240307",
            tokens_used=50,
            duration_ms=100.0,
            cache_hit=True,
            cache_read_tokens=1000,
        )
        assert result.cache_hit
        assert result.cache_read_tokens == 1000


class TestAnalysisMetrics:
    """Test AnalysisMetrics dataclass."""

    def test_default_values(self):
        """Test default metrics values."""
        metrics = AnalysisMetrics()
        assert metrics.total_calls == 0
        assert metrics.total_tokens == 0
        assert metrics.escalations == 0
        assert metrics.errors == []


class ConcreteAnalysisEngine(AnalysisEngine):
    """Concrete implementation for testing."""

    def _build_prompt(self, context):
        return f"Test prompt: {context}"

    def _process_result(self, result, call_result):
        return {"processed": True, "data": result}


class TestAnalysisEngineJSONParsing:
    """Test JSON parsing functionality."""

    @pytest.fixture
    def engine(self):
        """Create a concrete engine for testing."""
        # Create a mock AI router
        from unittest.mock import MagicMock

        mock_router = MagicMock()
        return ConcreteAnalysisEngine(ai_router=mock_router)

    def test_parse_valid_json(self, engine):
        """Test parsing valid JSON."""
        response = '{"key": "value", "number": 42}'
        result = engine.parse_json_response(response)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_code_block(self, engine):
        """Test parsing JSON wrapped in code block."""
        response = """Here's the result:
```json
{"key": "value"}
```
Done!"""
        result = engine.parse_json_response(response)
        assert result == {"key": "value"}

    def test_parse_json_with_trailing_comma(self, engine):
        """Test parsing JSON with trailing comma (cleaned)."""
        response = '{"key": "value",}'
        result = engine.parse_json_response(response)
        assert result == {"key": "value"}

    def test_parse_json_with_comments(self, engine):
        """Test parsing JSON with comments (cleaned)."""
        response = """{
            // This is a comment
            "key": "value"
        }"""
        result = engine.parse_json_response(response)
        assert result == {"key": "value"}

    def test_parse_empty_response_raises(self, engine):
        """Test that empty response raises JSONParseError."""
        with pytest.raises(JSONParseError, match="Empty response"):
            engine.parse_json_response("")

    def test_parse_no_json_raises(self, engine):
        """Test that response without JSON raises JSONParseError."""
        with pytest.raises(JSONParseError, match="No JSON object found"):
            engine.parse_json_response("Just some text without any JSON")

    def test_parse_incomplete_braces_raises(self, engine):
        """Test that incomplete JSON braces raises JSONParseError."""
        # Only opening brace, no closing - cannot be repaired
        with pytest.raises(JSONParseError, match="No JSON object found"):
            engine.parse_json_response("{key: value without closing")


class TestAnalysisEngineMetrics:
    """Test metrics tracking."""

    @pytest.fixture
    def engine(self):
        """Create a concrete engine."""
        from unittest.mock import MagicMock

        mock_router = MagicMock()
        return ConcreteAnalysisEngine(ai_router=mock_router)

    def test_initial_metrics(self, engine):
        """Test initial metrics are zero."""
        metrics = engine.metrics
        assert metrics.total_calls == 0
        assert metrics.total_tokens == 0

    def test_reset_metrics(self, engine):
        """Test resetting metrics."""
        engine._metrics.total_calls = 10
        engine._metrics.total_tokens = 1000
        engine.reset_metrics()
        assert engine.metrics.total_calls == 0
        assert engine.metrics.total_tokens == 0


class TestAnalysisEngineErrorHandling:
    """Test error handling functionality."""

    @pytest.fixture
    def engine(self):
        """Create a concrete engine."""
        from unittest.mock import MagicMock

        mock_router = MagicMock()
        return ConcreteAnalysisEngine(ai_router=mock_router)

    def test_handle_ai_error(self, engine):
        """Test error handling returns fallback result."""
        error = Exception("Test error")
        result = engine.handle_ai_error(error)
        assert result["error"] == "Test error"
        assert result["fallback"] is True
        assert result["confidence"] == 0.5
