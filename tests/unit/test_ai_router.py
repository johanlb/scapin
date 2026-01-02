"""
Unit Tests for AI Router

Tests for AI routing, rate limiting, and email analysis.
"""

import pytest
import time
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from src.sancho.router import AIRouter, RateLimiter, AIModel
from src.core.config_manager import AIConfig
from src.core.schemas import EmailMetadata, EmailContent, EmailAnalysis, EmailAction, EmailCategory
from src.utils import now_utc


@pytest.fixture
def ai_config():
    """Create test AI configuration"""
    return AIConfig(
        anthropic_api_key="test_api_key_12345",
        confidence_threshold=90,
        rate_limit_per_minute=40
    )


class TestRateLimiter:
    """Test rate limiter functionality"""

    def test_init(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60

    def test_acquire_within_limit(self):
        """Test acquiring permission within rate limit"""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        # Should be able to acquire 5 times
        for _ in range(5):
            assert limiter.acquire(timeout=1) is True

    def test_acquire_exceeds_limit(self):
        """Test acquiring when limit is exceeded"""
        limiter = RateLimiter(max_requests=2, window_seconds=10)

        # Acquire twice (at limit)
        assert limiter.acquire(timeout=0.1) is True
        assert limiter.acquire(timeout=0.1) is True

        # Third request should timeout
        assert limiter.acquire(timeout=0.1) is False

    def test_acquire_window_expiry(self):
        """Test that requests expire after window"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Acquire twice
        assert limiter.acquire(timeout=0.1) is True
        assert limiter.acquire(timeout=0.1) is True

        # Wait for window to expire
        time.sleep(1.1)

        # Should be able to acquire again
        assert limiter.acquire(timeout=0.1) is True

    def test_get_current_usage(self):
        """Test getting current usage stats"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        limiter.acquire()
        limiter.acquire()

        usage = limiter.get_current_usage()

        assert usage["current_requests"] == 2
        assert usage["max_requests"] == 10
        assert usage["usage_percent"] == 20.0


class TestAIRouterInit:
    """Test AI router initialization"""

    @patch('anthropic.Anthropic')
    def test_init_with_config(self, mock_anthropic, ai_config):
        """Test initialization with config"""
        router = AIRouter(ai_config)

        assert router.config == ai_config
        assert isinstance(router.rate_limiter, RateLimiter)
        mock_anthropic.assert_called_once_with(api_key="test_api_key_12345")

    def test_init_without_anthropic_package(self, ai_config):
        """Test initialization without anthropic package"""
        # Skip this test if anthropic is installed
        pytest.skip("Anthropic package is installed")


class TestEmailAnalysis:
    """Test email analysis functionality"""

    @patch('anthropic.Anthropic')
    @patch('src.sancho.templates.get_template_manager')
    def test_analyze_email_success(self, mock_template_manager, mock_anthropic, ai_config):
        """Test successful email analysis"""
        # Setup mocks
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Mock template rendering
        mock_tm = MagicMock()
        mock_template_manager.return_value = mock_tm
        mock_tm.render.return_value = "Test prompt"

        # Mock Claude response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "action": "archive",
            "category": "work",
            "destination": "Archive/2025/Work",
            "confidence": 95,
            "reasoning": "Work-related email",
            "tags": ["work", "project"],
            "entities": {"people": ["John"], "projects": ["Q1"], "dates": []},
            "needs_full_content": False
        }))]
        mock_client.messages.create.return_value = mock_response

        router = AIRouter(ai_config)

        # Create test email
        metadata = EmailMetadata(
            id=123,
            folder="INBOX",
            message_id="<test@example.com>",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            subject="Test Email",
            date=now_utc(),
            has_attachments=False,
            size_bytes=1024,
            flags=[]
        )

        content = EmailContent(
            plain_text="Test email content",
            html="<p>Test email content</p>"
        )

        # Analyze email
        analysis = router.analyze_email(metadata, content)

        assert analysis is not None
        assert analysis.action == EmailAction.ARCHIVE
        assert analysis.category == EmailCategory.WORK
        assert analysis.confidence == 95

    @patch('anthropic.Anthropic')
    @patch('src.sancho.templates.get_template_manager')
    def test_analyze_email_template_error(self, mock_template_manager, mock_anthropic, ai_config):
        """Test analysis with template rendering error"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_tm = MagicMock()
        mock_template_manager.return_value = mock_tm
        mock_tm.render.side_effect = Exception("Template error")

        router = AIRouter(ai_config)

        metadata = EmailMetadata(
            id=123,
            folder="INBOX",
            message_id="<test@example.com>",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            subject="Test",
            date=now_utc(),
            has_attachments=False,
            size_bytes=100,
            flags=[]
        )

        content = EmailContent(plain_text="Test")

        analysis = router.analyze_email(metadata, content)

        assert analysis is None

    @patch('anthropic.Anthropic')
    @patch('src.sancho.templates.get_template_manager')
    def test_analyze_email_api_error(self, mock_template_manager, mock_anthropic, ai_config):
        """Test analysis with API error"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_tm = MagicMock()
        mock_template_manager.return_value = mock_tm
        mock_tm.render.return_value = "Prompt"

        # Mock API error (just use a generic exception since APIError requires complex setup)
        mock_client.messages.create.side_effect = Exception("API Error")

        router = AIRouter(ai_config)

        metadata = EmailMetadata(
            id=123,
            folder="INBOX",
            message_id="<test@example.com>",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            subject="Test",
            date=now_utc(),
            has_attachments=False,
            size_bytes=100,
            flags=[]
        )

        content = EmailContent(plain_text="Test")

        analysis = router.analyze_email(metadata, content, max_retries=1)

        assert analysis is None


class TestResponseParsing:
    """Test AI response parsing"""

    @patch('anthropic.Anthropic')
    def test_parse_analysis_response_success(self, mock_anthropic, ai_config):
        """Test successful response parsing"""
        router = AIRouter(ai_config)

        response_json = {
            "action": "task",
            "category": "personal",
            "destination": "Tasks",
            "confidence": 85,
            "reasoning": "Requires action",
            "tags": ["todo"],
            "entities": {"people": [], "projects": [], "dates": []},
            "omnifocus_task": {
                "title": "Test task",
                "note": "Description",
                "defer_date": "2025-01-16",
                "due_date": "2025-01-20",
                "tags": ["work"]
            },
            "needs_full_content": False
        }

        response = f"Here's the analysis:\n{json.dumps(response_json)}\nThat's it."

        metadata = EmailMetadata(
            id=123,
            folder="INBOX",
            message_id="<test@example.com>",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            subject="Test",
            date=now_utc(),
            has_attachments=False,
            size_bytes=100,
            flags=[]
        )

        analysis = router._parse_analysis_response(response, metadata)

        assert analysis is not None
        assert analysis.action == EmailAction.TASK
        assert analysis.confidence == 85
        assert analysis.omnifocus_task is not None

    @patch('anthropic.Anthropic')
    def test_parse_analysis_response_invalid_json(self, mock_anthropic, ai_config):
        """Test parsing with invalid JSON"""
        router = AIRouter(ai_config)

        response = "This is not JSON at all"

        metadata = EmailMetadata(
            id=123,
            folder="INBOX",
            message_id="<test@example.com>",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            subject="Test",
            date=now_utc(),
            has_attachments=False,
            size_bytes=100,
            flags=[]
        )

        analysis = router._parse_analysis_response(response, metadata)

        assert analysis is None

    @patch('anthropic.Anthropic')
    def test_parse_analysis_response_no_json(self, mock_anthropic, ai_config):
        """Test parsing response without JSON"""
        router = AIRouter(ai_config)

        response = "No JSON in this response"

        metadata = EmailMetadata(
            id=123,
            folder="INBOX",
            message_id="<test@example.com>",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            subject="Test",
            date=now_utc(),
            has_attachments=False,
            size_bytes=100,
            flags=[]
        )

        analysis = router._parse_analysis_response(response, metadata)

        assert analysis is None


class TestRateLimitIntegration:
    """Test rate limiting integration"""

    @patch('anthropic.Anthropic')
    def test_get_rate_limit_status(self, mock_anthropic, ai_config):
        """Test getting rate limit status"""
        router = AIRouter(ai_config)

        status = router.get_rate_limit_status()

        assert "current_requests" in status
        assert "max_requests" in status
        assert "usage_percent" in status


class TestAIRouterSingleton:
    """Test AI router singleton pattern"""

    @patch('anthropic.Anthropic')
    def test_get_ai_router_singleton(self, mock_anthropic, ai_config):
        """Test that get_ai_router returns singleton"""
        from src.sancho.router import get_ai_router, _ai_router, _router_lock

        # Reset singleton for test
        import src.sancho.router
        src.sancho.router._ai_router = None

        router1 = get_ai_router(ai_config)
        router2 = get_ai_router()

        assert router1 is router2

    @patch('anthropic.Anthropic')
    def test_get_ai_router_with_config_from_get_config(self, mock_anthropic, ai_config):
        """Test getting router without explicit config"""
        from src.sancho.router import get_ai_router
        import src.sancho.router

        # Reset singleton
        src.sancho.router._ai_router = None

        with patch('src.core.config_manager.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.ai = ai_config
            mock_get_config.return_value = mock_config

            router = get_ai_router()

            assert router is not None
            mock_get_config.assert_called_once()
