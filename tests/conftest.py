"""
Pytest Configuration and Fixtures

Global fixtures for all tests.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Dict, Any

from src.core.config_manager import ConfigManager
from src.core.state_manager import StateManager
from src.core.schemas import (
    EmailMetadata,
    EmailContent,
    EmailAnalysis,
    EmailAction,
    EmailCategory,
)
from src.monitoring.logger import PKMLogger, LogLevel, LogFormat


# ============================================================================
# Setup/Teardown Fixtures
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configure logging for tests (session-wide)"""
    PKMLogger.configure(level=LogLevel.WARNING, format=LogFormat.TEXT)


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Reset singletons before each test

    This ensures tests don't interfere with each other.
    """
    # Reset ConfigManager
    ConfigManager._instance = None

    # Reset PKMLogger
    PKMLogger._configured = False
    PKMLogger._loggers.clear()

    yield

    # Cleanup after test
    ConfigManager._instance = None
    PKMLogger._configured = False


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create temporary config directory"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def tmp_templates_dir(tmp_path: Path) -> Path:
    """Create temporary templates directory"""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    return templates_dir


# ============================================================================
# State Manager Fixtures
# ============================================================================


@pytest.fixture
def state_manager() -> StateManager:
    """Create fresh StateManager for testing"""
    return StateManager()


# ============================================================================
# Email Data Fixtures
# ============================================================================


@pytest.fixture
def sample_email_metadata() -> EmailMetadata:
    """Sample email metadata for testing"""
    return EmailMetadata(
        id=12345,
        folder="INBOX",
        message_id="<abc123@example.com>",
        from_address="sender@example.com",
        from_name="Test Sender",
        to_addresses=["recipient@example.com"],
        subject="Test Email Subject",
        date=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        has_attachments=False,
        size_bytes=1024,
        flags=[]
    )


@pytest.fixture
def sample_email_content() -> EmailContent:
    """Sample email content for testing"""
    return EmailContent(
        plain_text="This is a test email body with some content.",
        html="<p>This is a test email body with some content.</p>",
        preview="This is a test email body with some content.",
        attachments=[]
    )


@pytest.fixture
def sample_email_analysis() -> EmailAnalysis:
    """Sample email analysis for testing"""
    return EmailAnalysis(
        action=EmailAction.ARCHIVE,
        category=EmailCategory.WORK,
        destination="Archive/2025",
        confidence=95,
        reasoning="This appears to be a work-related email that should be archived.",
        omnifocus_task=None,
        tags=["work", "project"],
        related_emails=[],
        entities={"people": ["Test Sender"]},
        needs_full_content=False
    )


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def sample_config_yaml(tmp_config_dir: Path) -> Path:
    """Create sample config YAML file"""
    config_file = tmp_config_dir / "defaults.yaml"
    config_content = """
email:
  imap_host: imap.test.com
  imap_port: 993
  imap_username: test@test.com
  imap_password: testpass123
  inbox_folder: INBOX
  archive_folder: Archive
  reference_folder: Reference
  delete_folder: Trash
  max_workers: 10
  batch_size: 100

ai:
  anthropic_api_key: sk-test-key-123
  confidence_threshold: 90
  rate_limit_per_minute: 40

storage:
  database_path: data/test.db
  notes_path: data/notes
  backup_enabled: true
  backup_retention_days: 30

integrations:
  omnifocus_enabled: true
  apple_notes_sync_enabled: false
  sync_interval_minutes: 30
  calendar_enabled: false

monitoring:
  log_level: INFO
  log_format: json
  health_check_enabled: true
  metrics_port: 8000
  error_reporting_enabled: true
"""
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def sample_env_file(tmp_path: Path) -> Path:
    """Create sample .env file"""
    env_file = tmp_path / ".env"
    env_content = """
ANTHROPIC_API_KEY=sk-test-key-123
IMAP_PASSWORD=testpass123
"""
    env_file.write_text(env_content)
    return env_file


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_email_response() -> Dict[str, Any]:
    """Mock IMAP email response"""
    return {
        12345: {
            b'BODY[]': b'From: sender@example.com\r\nTo: recipient@example.com\r\nSubject: Test\r\n\r\nBody',
            b'FLAGS': [b'\\Seen'],
        }
    }


@pytest.fixture
def mock_ai_response() -> Dict[str, Any]:
    """Mock AI analysis response"""
    return {
        "action": "archive",
        "category": "work",
        "destination": "Archive/2025",
        "confidence": 95,
        "reasoning": "Work-related email to archive",
        "omnifocus_task": None,
        "tags": ["work"],
        "related_emails": [],
        "entities": {},
        "needs_full_content": False
    }


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture logs with proper level"""
    caplog.set_level("DEBUG")
    return caplog
