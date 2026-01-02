"""
PKM Structured Logger

Logging structuré JSON pour faciliter:
- Parsing automatique
- Recherche et filtering
- Monitoring et alerting
- Debugging

Supporte aussi format texte pour développement.
"""

import json
import logging
import sys
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class LogLevel(str, Enum):
    """Log levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log formats"""

    JSON = "json"
    TEXT = "text"


class StructuredFormatter(logging.Formatter):
    """
    Formatter pour logs structurés JSON

    Output format:
    {
        "timestamp": "2025-12-29T14:30:00.000Z",
        "level": "INFO",
        "logger": "pkm.email",
        "message": "Email processed successfully",
        "extra": {
            "email_id": "abc123",
            "action": "archive",
            "confidence": 95
        }
    }
    """

    # Standard LogRecord attributes (frozenset for immutability and performance)
    STANDARD_ATTRS = frozenset([
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs", "message",
        "pathname", "process", "processName", "relativeCreated",
        "thread", "threadName", "exc_info", "exc_text", "stack_info",
        "taskName",  # Python 3.12+
    ])

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""

        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields (anything not in standard LogRecord attributes)
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in self.STANDARD_ATTRS
        }

        if extra_fields:
            log_entry["extra"] = extra_fields

        # Add source location
        log_entry["source"] = {
            "file": record.pathname,
            "function": record.funcName,
            "line": record.lineno,
        }

        return json.dumps(log_entry)


class TextFormatter(logging.Formatter):
    """
    Formatter pour logs texte (développement)

    Output format:
    2025-12-29 14:30:00 INFO [pkm.email] Email processed successfully
    """

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class PKMLogger:
    """
    Logger PKM structuré (thread-safe)

    Usage:
        logger = PKMLogger.get_logger("pkm.email")
        logger.info("Email processed", email_id="abc123", action="archive")
        logger.error("Failed to process", email_id="def456", exc_info=True)
    """

    _loggers: dict[str, logging.Logger] = {}
    _configured = False
    _display_mode = False  # When True, console logs are hidden
    _config_lock = threading.Lock()
    _saved_console_handlers: list[logging.Handler] = []  # Store handlers when hiding

    @classmethod
    def configure(
        cls,
        level: LogLevel = LogLevel.INFO,
        format: LogFormat = LogFormat.JSON,
        log_file: Optional[Path] = None,
    ) -> None:
        """
        Configure logging system (thread-safe)

        Args:
            level: Minimum log level
            format: Log format (JSON or TEXT)
            log_file: Optional log file path
        """
        # Thread-safe configuration
        with cls._config_lock:
            if cls._configured:
                return

            # Root logger
            root_logger = logging.getLogger("pkm")
            root_logger.setLevel(level.value)
            root_logger.propagate = False

            # Remove existing handlers
            root_logger.handlers.clear()

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level.value)

            if format == LogFormat.JSON:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(TextFormatter())

            root_logger.addHandler(console_handler)

            # File handler (optional)
            if log_file:
                log_file.parent.mkdir(parents=True, exist_ok=True)

                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setLevel(level.value)

                # Always use JSON for file logs
                file_handler.setFormatter(StructuredFormatter())

                root_logger.addHandler(file_handler)

            cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create logger

        Args:
            name: Logger name (e.g. "pkm.email", "pkm.ai.router")

        Returns:
            Logger instance
        """
        if not cls._configured:
            cls.configure()

        if name not in cls._loggers:
            logger = logging.getLogger(f"pkm.{name}")
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def set_display_mode(cls, enabled: bool) -> None:
        """
        Enable or disable display mode

        When display mode is enabled, console log handlers are temporarily
        removed to prevent log output from interfering with the DisplayManager's
        clean UI. File logging (if configured) continues normally.

        This is useful during email processing when using the DisplayManager
        to show a clean, event-driven UI.

        Args:
            enabled: True to hide console logs, False to restore them

        Usage:
            # Hide console logs during processing
            PKMLogger.set_display_mode(True)

            # Process emails (DisplayManager shows events, no log noise)
            processor.process_inbox(...)

            # Restore console logs
            PKMLogger.set_display_mode(False)
        """
        with cls._config_lock:
            # Ensure logging is configured
            if not cls._configured:
                cls.configure()

            root_logger = logging.getLogger("pkm")

            if enabled and not cls._display_mode:
                # Hide console handlers
                cls._saved_console_handlers = []
                for handler in root_logger.handlers[:]:  # Copy list to avoid modification during iteration
                    if isinstance(handler, logging.StreamHandler) and handler.stream in (sys.stdout, sys.stderr):
                        cls._saved_console_handlers.append(handler)
                        root_logger.removeHandler(handler)

                cls._display_mode = True

            elif not enabled and cls._display_mode:
                # Restore console handlers
                for handler in cls._saved_console_handlers:
                    root_logger.addHandler(handler)

                cls._saved_console_handlers = []
                cls._display_mode = False


# Convenience function
def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance

    Usage:
        from monitoring.logger import get_logger

        logger = get_logger("email")
        logger.info("Processing email", email_id="123")
    """
    return PKMLogger.get_logger(name)


# Context manager for temporary log level
class TemporaryLogLevel:
    """
    Context manager pour changer temporairement le log level

    Usage:
        with TemporaryLogLevel("DEBUG"):
            # Code here will log at DEBUG level
            logger.debug("Detailed info")
    """

    def __init__(self, level: str):
        self.level = level
        self.original_level = None

    def __enter__(self):
        root_logger = logging.getLogger("pkm")
        self.original_level = root_logger.level
        root_logger.setLevel(self.level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        root_logger = logging.getLogger("pkm")
        root_logger.setLevel(self.original_level)
