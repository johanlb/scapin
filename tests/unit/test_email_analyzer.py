"""
Tests for EmailAnalyzer

Covers AI analysis integration, error handling, and preview mode.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.core.processors.email_analyzer import EmailAnalyzer
from src.core.schemas import EmailMetadata, EmailContent, EmailAnalysis, EmailAction, EmailCategory
from src.core.exceptions import AIAnalysisError, RateLimitError
from src.utils import now_utc


@pytest.fixture
def mock_ai_router():
    """Create mock AI router"""
    router = Mock()
    router.analyze_email = Mock()
    return router


@pytest.fixture
def analyzer(mock_ai_router):
    """Create EmailAnalyzer with mock router"""
    return EmailAnalyzer(mock_ai_router)


@pytest.fixture
def sample_metadata():
    """Create sample email metadata"""
    return EmailMetadata(
        id=1,
        message_id="test@example.com",
        subject="Test Email",
        from_address="sender@example.com",
        from_name="Test Sender",
        to_addresses=["recipient@example.com"],
        date=now_utc(),
        has_attachments=False,
        flags=[]
    )


@pytest.fixture
def sample_content():
    """Create sample email content"""
    return EmailContent(
        plain_text="This is a test email body.",
        html="<p>This is a test email body.</p>"
    )


class TestAnalyze:
    """Test email analysis"""

    def test_analyze_success(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test successful email analysis"""
        # Mock successful AI response
        expected_analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=95,
            reasoning="Test email newsletter, safe to archive",
            destination="Archive"
        )
        mock_ai_router.analyze_email.return_value = expected_analysis

        result = analyzer.analyze(sample_metadata, sample_content)

        # Verify AI router was called correctly
        mock_ai_router.analyze_email.assert_called_once_with(
            metadata=sample_metadata,
            content=sample_content,
            preview_mode=False
        )

        # Verify result
        assert result == expected_analysis
        assert result.action == EmailAction.ARCHIVE
        assert result.confidence == 95

    def test_analyze_preview_mode(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test analysis in preview mode"""
        expected_analysis = EmailAnalysis(
            action=EmailAction.DEFER,
            category=EmailCategory.OTHER,
            confidence=80,
            reasoning="Quick preview analysis result"
        )
        mock_ai_router.analyze_email.return_value = expected_analysis

        result = analyzer.analyze(sample_metadata, sample_content, preview_mode=True)

        # Verify preview_mode was passed
        mock_ai_router.analyze_email.assert_called_once_with(
            metadata=sample_metadata,
            content=sample_content,
            preview_mode=True
        )

        assert result.confidence == 80

    def test_analyze_returns_none(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test handling of None response from AI"""
        mock_ai_router.analyze_email.return_value = None

        result = analyzer.analyze(sample_metadata, sample_content)

        assert result is None

    def test_analyze_rate_limit_error(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test RateLimitError is propagated"""
        mock_ai_router.analyze_email.side_effect = RateLimitError("Rate limit exceeded")

        with pytest.raises(RateLimitError) as exc_info:
            analyzer.analyze(sample_metadata, sample_content)

        assert "Rate limit exceeded" in str(exc_info.value)

    def test_analyze_generic_error_wrapped(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test generic errors are wrapped in AIAnalysisError"""
        mock_ai_router.analyze_email.side_effect = ValueError("Invalid input")

        with pytest.raises(AIAnalysisError) as exc_info:
            analyzer.analyze(sample_metadata, sample_content)

        assert "Failed to analyze email" in str(exc_info.value)
        # Original error should be preserved as cause
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_analyze_includes_email_id_in_error(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test error details include email ID"""
        mock_ai_router.analyze_email.side_effect = Exception("AI service down")

        with pytest.raises(AIAnalysisError) as exc_info:
            analyzer.analyze(sample_metadata, sample_content)

        # Check that error details include the email_id
        error = exc_info.value
        assert hasattr(error, 'details')
        assert error.details.get('email_id') == "test@example.com"


class TestErrorHandling:
    """Test error handling edge cases"""

    def test_network_error_wrapped(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test network errors are wrapped properly"""
        mock_ai_router.analyze_email.side_effect = ConnectionError("Network unreachable")

        with pytest.raises(AIAnalysisError) as exc_info:
            analyzer.analyze(sample_metadata, sample_content)

        assert "Failed to analyze email" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_timeout_error_wrapped(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test timeout errors are wrapped properly"""
        mock_ai_router.analyze_email.side_effect = TimeoutError("Request timed out")

        with pytest.raises(AIAnalysisError) as exc_info:
            analyzer.analyze(sample_metadata, sample_content)

        assert isinstance(exc_info.value.__cause__, TimeoutError)

    def test_preserves_rate_limit_error(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test RateLimitError is NOT wrapped"""
        rate_limit = RateLimitError("Rate limit exceeded")
        mock_ai_router.analyze_email.side_effect = rate_limit

        # Should raise RateLimitError directly, not wrapped
        with pytest.raises(RateLimitError) as exc_info:
            analyzer.analyze(sample_metadata, sample_content)

        # Should be the exact same exception
        assert exc_info.value is rate_limit


class TestIntegration:
    """Test integration scenarios"""

    def test_multiple_analyses(self, analyzer, mock_ai_router, sample_metadata, sample_content):
        """Test multiple sequential analyses"""
        # First analysis
        analysis1 = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=90,
            reasoning="First analysis result"
        )
        mock_ai_router.analyze_email.return_value = analysis1

        result1 = analyzer.analyze(sample_metadata, sample_content)
        assert result1.action == EmailAction.ARCHIVE

        # Second analysis (different result)
        analysis2 = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=85,
            reasoning="Second analysis result"
        )
        mock_ai_router.analyze_email.return_value = analysis2

        result2 = analyzer.analyze(sample_metadata, sample_content)
        assert result2.action == EmailAction.TASK

        # Verify both calls were made
        assert mock_ai_router.analyze_email.call_count == 2

    def test_analyzer_with_real_router_interface(self, sample_metadata, sample_content):
        """Test analyzer expects correct AIRouter interface"""
        # Create a minimal mock that matches AIRouter interface
        router = Mock()
        router.analyze_email = Mock(return_value=EmailAnalysis(
            action=EmailAction.DEFER,
            category=EmailCategory.OTHER,
            confidence=50,
            reasoning="Test analysis result"
        ))

        analyzer = EmailAnalyzer(router)
        result = analyzer.analyze(sample_metadata, sample_content)

        assert result is not None
        assert hasattr(result, 'action')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reasoning')
