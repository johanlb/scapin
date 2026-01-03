"""
Pytest Configuration and Fixtures

Global fixtures for all tests.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

from src.core.config_manager import ConfigManager
from src.core.schemas import (
    EmailAction,
    EmailAnalysis,
    EmailCategory,
    EmailContent,
    EmailMetadata,
)
from src.core.state_manager import StateManager
from src.monitoring.logger import LogFormat, LogLevel, ScapinLogger

# ============================================================================
# Setup/Teardown Fixtures
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configure logging for tests (session-wide)"""
    ScapinLogger.configure(level=LogLevel.WARNING, format=LogFormat.TEXT)


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Reset singletons before each test

    This ensures tests don't interfere with each other.
    """
    # Reset ConfigManager
    ConfigManager._instance = None

    # Reset ScapinLogger
    ScapinLogger._configured = False
    ScapinLogger._loggers.clear()

    # Reset error store and manager
    try:
        from src.core.error_store import reset_error_store
        reset_error_store()
    except Exception:
        pass

    try:
        from src.core.error_manager import reset_error_manager
        reset_error_manager()
    except Exception:
        pass

    yield

    # Cleanup after test
    ConfigManager._instance = None
    ScapinLogger._configured = False

    try:
        from src.core.error_store import reset_error_store
        reset_error_store()
    except Exception:
        pass

    try:
        from src.core.error_manager import reset_error_manager
        reset_error_manager()
    except Exception:
        pass


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


# ============================================================================
# Mock Config Fixtures
# ============================================================================


@pytest.fixture
def mock_config(tmp_path):
    """
    Provide a mock ScapinConfig for tests that need config

    This fixture patches get_config() to return a mock config,
    allowing tests to run without a real .env file.

    Usage:
        def test_something(mock_config):
            # config is automatically mocked
            from src.core.config_manager import get_config
            config = get_config()  # Returns mock_config
    """
    from unittest.mock import MagicMock, patch

    # Create mock storage config
    mock_storage = MagicMock()
    mock_storage.database_path = tmp_path / "test_pkm.db"
    mock_storage.notes_path = tmp_path / "test_notes"

    # Create mock email account config
    mock_account = MagicMock()
    mock_account.account_id = "default"
    mock_account.account_name = "Default Account"
    mock_account.enabled = True
    mock_account.imap_host = "imap.example.com"
    mock_account.imap_port = 993
    mock_account.imap_username = "test@example.com"
    mock_account.imap_password = "test_password"
    mock_account.imap_timeout = 30
    mock_account.imap_read_timeout = 60
    mock_account.inbox_folder = "INBOX"
    mock_account.archive_folder = "Archive"
    mock_account.reference_folder = "Reference"
    mock_account.delete_folder = "Trash"
    mock_account.max_workers = 10
    mock_account.batch_size = 100

    # Create mock email config
    mock_email = MagicMock()
    mock_email.accounts = [mock_account]
    mock_email.default_account_id = "default"
    mock_email.imap_host = "imap.example.com"
    mock_email.imap_port = 993
    mock_email.imap_username = "test@example.com"
    mock_email.imap_password = "test_password"
    mock_email.get_default_account.return_value = mock_account
    mock_email.get_account.return_value = mock_account

    # Create mock AI config
    mock_ai = MagicMock()
    mock_ai.anthropic_api_key = "test-api-key"
    mock_ai.confidence_threshold = 90
    mock_ai.rate_limit_per_minute = 40

    # Create mock integrations config
    mock_integrations = MagicMock()
    mock_integrations.omnifocus_enabled = True

    # Create mock monitoring config
    mock_monitoring = MagicMock()
    mock_monitoring.log_level = "INFO"
    mock_monitoring.error_reporting_enabled = True

    # Create main mock config
    mock_cfg = MagicMock()
    mock_cfg.storage = mock_storage
    mock_cfg.email = mock_email
    mock_cfg.ai = mock_ai
    mock_cfg.integrations = mock_integrations
    mock_cfg.monitoring = mock_monitoring
    mock_cfg.environment = "test"

    with patch('src.core.config_manager.get_config', return_value=mock_cfg):
        with patch('src.core.config_manager.ConfigManager.get', return_value=mock_cfg):
            # Also patch where it's imported in other modules
            with patch('src.core.error_store.get_config', return_value=mock_cfg):
                yield mock_cfg


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for tests"""
    db_path = tmp_path / "test.db"
    yield db_path
    # Cleanup
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
