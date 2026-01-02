"""
Unit tests for StructuredLogger
"""

import json
import logging

from src.monitoring.logger import (
    LogFormat,
    LogLevel,
    PKMLogger,
    StructuredFormatter,
    get_logger,
)


class TestStructuredFormatter:
    """Test StructuredFormatter"""

    def test_format_basic_message(self):
        """Test formatting basic log message"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="pkm.test",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_func",
        )

        result = formatter.format(record)
        log_entry = json.loads(result)

        assert log_entry["level"] == "INFO"
        assert log_entry["logger"] == "pkm.test"
        assert log_entry["message"] == "Test message"
        assert "timestamp" in log_entry
        assert log_entry["source"]["file"] == "/test/file.py"
        assert log_entry["source"]["line"] == 42

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="pkm.email",
            level=logging.INFO,
            pathname="/test/email.py",
            lineno=10,
            msg="Email processed",
            args=(),
            exc_info=None,
            func="process_email",
        )

        # Add extra fields
        record.email_id = "abc123"
        record.action = "archive"
        record.confidence = 95

        result = formatter.format(record)
        log_entry = json.loads(result)

        assert log_entry["message"] == "Email processed"
        assert log_entry["extra"]["email_id"] == "abc123"
        assert log_entry["extra"]["action"] == "archive"
        assert log_entry["extra"]["confidence"] == 95


class TestPKMLogger:
    """Test PKMLogger"""

    def setup_method(self):
        """Reset logger configuration"""
        PKMLogger._configured = False
        PKMLogger._loggers.clear()

    def test_configure_json_format(self):
        """Test configuring logger with JSON format"""
        PKMLogger.configure(level=LogLevel.INFO, format=LogFormat.JSON)

        logger = PKMLogger.get_logger("test")
        assert logger is not None
        # Logger inherits from parent, check effective level
        assert logger.getEffectiveLevel() == logging.INFO

    def test_configure_text_format(self):
        """Test configuring logger with text format"""
        PKMLogger.configure(level=LogLevel.DEBUG, format=LogFormat.TEXT)

        logger = PKMLogger.get_logger("test")
        assert logger is not None
        assert logger.getEffectiveLevel() == logging.DEBUG

    def test_get_logger_returns_logger(self):
        """Test get_logger returns valid logger"""
        logger = PKMLogger.get_logger("email")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "pkm.email"

    def test_get_logger_caches_instances(self):
        """Test logger instances are cached"""
        logger1 = PKMLogger.get_logger("test")
        logger2 = PKMLogger.get_logger("test")

        assert logger1 is logger2

    def test_get_logger_convenience_function(self):
        """Test convenience function"""
        logger = get_logger("test")

        assert isinstance(logger, logging.Logger)
        assert "pkm.test" in logger.name


class TestTemporaryLogLevelContext:
    """Test TemporaryLogLevel context manager"""

    def test_temporary_log_level_context_changes_level(self):
        """Test context manager changes log level temporarily"""
        from src.monitoring.logger import TemporaryLogLevel

        PKMLogger.configure(level=LogLevel.INFO)
        root_logger = logging.getLogger("pkm")

        original_level = root_logger.level

        with TemporaryLogLevel("DEBUG"):
            assert root_logger.level == logging.DEBUG

        assert root_logger.level == original_level
