"""
Unit Tests for RecoveryEngine

Tests recovery strategies for different error categories.
"""

import time
from datetime import datetime

import pytest

from src.core.error_manager import ErrorCategory, ErrorSeverity, RecoveryStrategy, SystemError
from src.core.recovery_engine import RecoveryEngine, init_recovery_engine


@pytest.fixture
def recovery_engine():
    """Create RecoveryEngine instance"""
    return RecoveryEngine(default_timeout=5)


@pytest.fixture
def sample_error():
    """Create sample error for testing"""
    return SystemError(
        id="test-error",
        timestamp=datetime.now(),
        category=ErrorCategory.IMAP,
        severity=ErrorSeverity.MEDIUM,
        exception_type="ConnectionError",
        exception_message="Connection failed",
        traceback="Traceback...",
        component="imap_client",
        operation="connect",
        context={"host": "imap.example.com", "port": 993},
        recovery_strategy=RecoveryStrategy.RETRY,
        recovery_attempted=False,
        recovery_successful=None,
        recovery_attempts=0,
        max_recovery_attempts=3,
        resolved=False,
        resolved_at=None,
        notes=""
    )


class TestRecoveryEngineInit:
    """Test RecoveryEngine initialization"""

    def test_init_default_timeout(self):
        """Test initialization with default timeout"""
        engine = RecoveryEngine()
        assert engine.default_timeout == 30

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout"""
        engine = RecoveryEngine(default_timeout=60)
        assert engine.default_timeout == 60

    def test_init_recovery_engine_helper(self, mock_config):
        """Test init_recovery_engine helper function"""
        engine = init_recovery_engine()
        assert isinstance(engine, RecoveryEngine)


class TestIMAPRecovery:
    """Test IMAP error recovery"""

    def test_recover_imap_connection_error(self, recovery_engine, sample_error):
        """Test recovery from connection error"""
        sample_error.exception_type = "ConnectionError"

        result = recovery_engine.recover_imap(sample_error)
        assert result is True

    def test_recover_imap_timeout_error(self, recovery_engine, sample_error):
        """Test recovery from timeout error"""
        sample_error.exception_type = "TimeoutError"

        result = recovery_engine.recover_imap(sample_error)
        assert result is True

    def test_recover_imap_auth_error(self, recovery_engine, sample_error):
        """Test that authentication errors cannot be auto-recovered"""
        sample_error.exception_type = "PermissionError"
        sample_error.exception_message = "Authentication failed"

        result = recovery_engine.recover_imap(sample_error)
        assert result is False

    def test_recover_imap_parse_error_skip(self, recovery_engine, sample_error):
        """Test that parse errors are skipped"""
        sample_error.exception_type = "ValueError"
        sample_error.exception_message = "Could not parse email"

        result = recovery_engine.recover_imap(sample_error)
        assert result is True  # Skip = success

    def test_recover_imap_unicode_error_skip(self, recovery_engine, sample_error):
        """Test that unicode errors are skipped"""
        sample_error.exception_type = "UnicodeDecodeError"

        result = recovery_engine.recover_imap(sample_error)
        assert result is True  # Skip = success


class TestAIRecovery:
    """Test AI error recovery"""

    def test_recover_ai_rate_limit(self, recovery_engine):
        """Test recovery from rate limit error"""
        error = SystemError(
            id="test-ai-rate",
            timestamp=datetime.now(),
            category=ErrorCategory.AI,
            severity=ErrorSeverity.MEDIUM,
            exception_type="APIError",
            exception_message="Rate limit exceeded",
            traceback="",
            component="ai_router",
            operation="analyze",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        start_time = time.time()
        result = recovery_engine.recover_ai(error)
        elapsed = time.time() - start_time

        assert result is True
        # Should have waited (base delay * 2^0 = 5s)
        assert elapsed >= 5

    def test_recover_ai_timeout(self, recovery_engine):
        """Test recovery from timeout error"""
        error = SystemError(
            id="test-ai-timeout",
            timestamp=datetime.now(),
            category=ErrorCategory.AI,
            severity=ErrorSeverity.MEDIUM,
            exception_type="TimeoutError",
            exception_message="Request timed out",
            traceback="",
            component="ai_router",
            operation="analyze",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        result = recovery_engine.recover_ai(error)
        assert result is True

    def test_recover_ai_json_error(self, recovery_engine):
        """Test recovery from JSON decode error"""
        error = SystemError(
            id="test-ai-json",
            timestamp=datetime.now(),
            category=ErrorCategory.AI,
            severity=ErrorSeverity.MEDIUM,
            exception_type="JSONDecodeError",
            exception_message="Invalid JSON response",
            traceback="",
            component="ai_router",
            operation="analyze",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        result = recovery_engine.recover_ai(error)
        assert result is True


class TestNetworkRecovery:
    """Test network error recovery"""

    def test_recover_network(self, recovery_engine):
        """Test network error recovery with retry"""
        error = SystemError(
            id="test-network",
            timestamp=datetime.now(),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            exception_type="ConnectionError",
            exception_message="Network unreachable",
            traceback="",
            component="http_client",
            operation="fetch",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        result = recovery_engine.recover_network(error)
        assert result is True


class TestValidationRecovery:
    """Test validation error recovery"""

    def test_recover_validation_skip(self, recovery_engine):
        """Test validation error recovery by skipping"""
        error = SystemError(
            id="test-validation",
            timestamp=datetime.now(),
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            exception_type="ValueError",
            exception_message="Invalid data format",
            traceback="",
            component="validator",
            operation="validate",
            context={},
            recovery_strategy=RecoveryStrategy.SKIP,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        result = recovery_engine.recover_validation(error)
        assert result is True  # Always succeeds by skipping


class TestBackoffCalculation:
    """Test exponential backoff calculation"""

    def test_calculate_backoff_first_attempt(self, recovery_engine):
        """Test backoff for first attempt"""
        error = SystemError(
            id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.MEDIUM,
            exception_type="ConnectionError",
            exception_message="Test",
            traceback="",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,  # First attempt
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        delay = recovery_engine._calculate_backoff_delay(error)
        # base * 2^0 = 1
        assert delay == 1

    def test_calculate_backoff_second_attempt(self, recovery_engine):
        """Test backoff for second attempt"""
        error = SystemError(
            id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.MEDIUM,
            exception_type="ConnectionError",
            exception_message="Test",
            traceback="",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=True,
            recovery_successful=False,
            recovery_attempts=1,  # Second attempt
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        delay = recovery_engine._calculate_backoff_delay(error)
        # base * 2^1 = 2
        assert delay == 2

    def test_calculate_backoff_max_delay(self, recovery_engine):
        """Test backoff capped at max delay"""
        error = SystemError(
            id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.MEDIUM,
            exception_type="ConnectionError",
            exception_message="Test",
            traceback="",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=True,
            recovery_successful=False,
            recovery_attempts=10,  # Many attempts
            max_recovery_attempts=15,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        delay = recovery_engine._calculate_backoff_delay(error)
        # Should be capped at max_retry_delay
        assert delay == recovery_engine.max_retry_delay

    def test_calculate_backoff_custom_base(self, recovery_engine):
        """Test backoff with custom base delay"""
        error = SystemError(
            id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.MEDIUM,
            exception_type="ConnectionError",
            exception_message="Test",
            traceback="",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=2,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )

        delay = recovery_engine._calculate_backoff_delay(error, base=5)
        # 5 * 2^2 = 20
        assert delay == 20


class TestRecoveryHandlerRegistration:
    """Test recovery handler registration"""

    def test_register_handlers(self, recovery_engine):
        """Test registering handlers with error manager"""
        from src.core.error_manager import ErrorManager

        error_manager = ErrorManager(error_store=None)
        recovery_engine.register_handlers(error_manager)

        # Handlers should be registered (can't directly test, but shouldn't error)
        assert True

    def test_register_handlers_default_manager(self, recovery_engine, mock_config):
        """Test registering with default error manager"""
        # Should use global error manager (mocked)
        recovery_engine.register_handlers(None)
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
