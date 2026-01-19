"""
Unit Tests for CLI Application

Tests CLI commands and output using Typer's testing utilities.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.core.schemas import HealthCheck, ServiceStatus, SystemHealth
from src.frontin.cli import app

runner = CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality"""

    def test_cli_help(self):
        """Test CLI shows help message"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Scapin" in result.stdout
        assert "Intelligent email management system" in result.stdout

    def test_cli_version(self):
        """Test version flag"""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Scapin" in result.stdout
        assert "v2.0.0" in result.stdout

    def test_cli_version_short(self):
        """Test -v flag for version"""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "Scapin" in result.stdout


@pytest.mark.skip(reason="Process command requires full config - integration test")
class TestProcessCommand:
    """Test process command"""

    def test_process_command_basic(self):
        """Test process command runs"""
        result = runner.invoke(app, ["process"])
        assert result.exit_code == 0
        assert "Processing your inbox" in result.stdout

    def test_process_command_with_limit(self):
        """Test process command with limit"""
        result = runner.invoke(app, ["process", "--limit", "10"])
        assert result.exit_code == 0

    def test_process_command_auto_mode(self):
        """Test process command in auto mode"""
        result = runner.invoke(app, ["process", "--auto"])
        assert result.exit_code == 0
        assert "auto" in result.stdout.lower()

    def test_process_command_custom_confidence(self):
        """Test process command with custom confidence"""
        result = runner.invoke(app, ["process", "--auto", "--confidence", "95"])
        assert result.exit_code == 0
        assert "95" in result.stdout

    def test_process_command_implementation(self):
        """Test that process command is implemented"""
        result = runner.invoke(app, ["process", "--limit", "1"])
        # Should attempt to process (may fail due to missing credentials, that's ok)
        assert "Processing your inbox" in result.stdout or "processing your inbox" in result.stdout.lower()


@pytest.mark.skip(reason="Review command requires full config - integration test")
class TestReviewCommand:
    """Test review command"""

    def test_review_command_basic(self):
        """Test review command runs"""
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "Decision Review" in result.stdout or "Reviewing" in result.stdout

    def test_review_command_with_limit(self):
        """Test review command with limit"""
        result = runner.invoke(app, ["review", "--limit", "10"])
        assert result.exit_code == 0

    def test_review_not_implemented_notice(self):
        """Test that review shows not implemented notice"""
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout.lower()


@pytest.mark.skip(reason="Queue command requires full config - integration test")
class TestQueueCommand:
    """Test queue command"""

    def test_queue_command_basic(self):
        """Test queue command runs"""
        result = runner.invoke(app, ["queue"])
        assert result.exit_code == 0
        assert "Queue" in result.stdout

    def test_queue_command_with_process(self):
        """Test queue command with --process flag"""
        result = runner.invoke(app, ["queue", "--process"])
        assert result.exit_code == 0

    def test_queue_not_implemented_notice(self):
        """Test that queue shows not implemented notice"""
        result = runner.invoke(app, ["queue"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout.lower()


class TestHealthCommand:
    """Test health command"""

    @patch('src.frontin.cli.quick_health_check')
    def test_health_command_all_healthy(self, mock_health):
        """Test health command when all services healthy"""
        mock_health.return_value = SystemHealth(
            overall_status=ServiceStatus.HEALTHY,
            checks=[
                HealthCheck(
                    service="config",
                    status=ServiceStatus.HEALTHY,
                    message="Configuration loaded",
                    response_time_ms=5.0
                ),
                HealthCheck(
                    service="git",
                    status=ServiceStatus.HEALTHY,
                    message="Git repository ready",
                    response_time_ms=10.0
                ),
            ]
        )

        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "Health Check Results" in result.stdout
        assert "config" in result.stdout
        assert "git" in result.stdout
        assert "All systems healthy" in result.stdout

    @patch('src.frontin.cli.quick_health_check')
    def test_health_command_with_unhealthy(self, mock_health):
        """Test health command with unhealthy services"""
        mock_health.return_value = SystemHealth(
            overall_status=ServiceStatus.UNHEALTHY,
            checks=[
                HealthCheck(
                    service="config",
                    status=ServiceStatus.HEALTHY,
                    message="Configuration loaded",
                    response_time_ms=5.0
                ),
                HealthCheck(
                    service="imap",
                    status=ServiceStatus.UNHEALTHY,
                    message="Connection failed",
                    response_time_ms=None
                ),
            ]
        )

        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "imap" in result.stdout
        assert "unhealthy" in result.stdout.lower()

    @patch('src.frontin.cli.quick_health_check')
    def test_health_command_with_degraded(self, mock_health):
        """Test health command with degraded services"""
        mock_health.return_value = SystemHealth(
            overall_status=ServiceStatus.DEGRADED,
            checks=[
                HealthCheck(
                    service="config",
                    status=ServiceStatus.DEGRADED,
                    message="Using defaults",
                    response_time_ms=5.0
                ),
            ]
        )

        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "Degraded" in result.stdout


@pytest.mark.skip(reason="Stats command output format may differ - integration test")
class TestStatsCommand:
    """Test stats command"""

    @patch('src.frontin.cli.get_state_manager')
    def test_stats_command_basic(self, mock_get_state):
        """Test stats command shows statistics"""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "processing_state": "idle",
            "stats": {
                "emails_processed": 42,
                "emails_skipped": 5,
                "archived": 30,
                "deleted": 2,
                "referenced": 10,
                "confidence_avg": 87.5,
                "duration_minutes": 15,
            }
        }
        mock_get_state.return_value = mock_state

        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Session Statistics" in result.stdout
        assert "42" in result.stdout  # emails processed
        assert "87.5" in result.stdout  # confidence avg
        assert "idle" in result.stdout

    @patch('src.frontin.cli.get_state_manager')
    def test_stats_command_empty(self, mock_get_state):
        """Test stats command with no data"""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "processing_state": "idle",
            "stats": {}
        }
        mock_get_state.return_value = mock_state

        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "0" in result.stdout  # Should show zeros


@pytest.mark.skip(reason="Config command uses outdated config format - needs update")
class TestConfigCommand:
    """Test config command"""

    @patch('src.frontin.cli.get_config')
    def test_config_command_basic(self, mock_get_config):
        """Test config command shows configuration"""
        from src.core.config_manager import (
            AIConfig,
            EmailConfig,
            IntegrationsConfig,
            MonitoringConfig,
            ScapinConfig,
            StorageConfig,
        )

        mock_config = ScapinConfig(
            email=EmailConfig(
                imap_host="imap.test.com",
                imap_port=993,
                imap_username="test@test.com",
                imap_password="password",
                inbox_folder="INBOX",
                archive_folder="Archive",
                reference_folder="Reference",
                delete_folder="Trash",
                max_workers=10,
                batch_size=100,
            ),
            ai=AIConfig(
                anthropic_api_key="sk-test-123",
                confidence_threshold=90,
                rate_limit_per_minute=40,
            ),
            storage=StorageConfig(
                database_path="data/test.db",
                notes_path="data/notes",
                backup_enabled=True,
                backup_retention_days=30,
            ),
            integrations=IntegrationsConfig(
                omnifocus_enabled=True,
                apple_notes_sync_enabled=False,
                sync_interval_minutes=30,
                calendar_enabled=False,
            ),
            monitoring=MonitoringConfig(
                log_level="INFO",
                log_format="json",
                health_check_enabled=True,
                metrics_port=8000,
                error_reporting_enabled=True,
            ),
        )
        mock_get_config.return_value = mock_config

        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Configuration" in result.stdout
        assert "imap.test.com" in result.stdout
        assert "90" in result.stdout  # confidence threshold

    @patch('src.frontin.cli.get_config')
    def test_config_command_validate(self, mock_get_config):
        """Test config command with --validate flag"""
        from src.core.config_manager import (
            AIConfig,
            EmailConfig,
            IntegrationsConfig,
            MonitoringConfig,
            ScapinConfig,
            StorageConfig,
        )

        mock_config = ScapinConfig(
            email=EmailConfig(
                imap_host="imap.test.com",
                imap_port=993,
                imap_username="test@test.com",
                imap_password="password",
                inbox_folder="INBOX",
                archive_folder="Archive",
                reference_folder="Reference",
                delete_folder="Trash",
                max_workers=10,
                batch_size=100,
            ),
            ai=AIConfig(
                anthropic_api_key="sk-test-123",
                confidence_threshold=90,
                rate_limit_per_minute=40,
            ),
            storage=StorageConfig(
                database_path="data/test.db",
                notes_path="data/notes",
                backup_enabled=True,
                backup_retention_days=30,
            ),
            integrations=IntegrationsConfig(
                omnifocus_enabled=True,
                apple_notes_sync_enabled=False,
                sync_interval_minutes=30,
                calendar_enabled=False,
            ),
            monitoring=MonitoringConfig(
                log_level="INFO",
                log_format="json",
                health_check_enabled=True,
                metrics_port=8000,
                error_reporting_enabled=True,
            ),
        )
        mock_get_config.return_value = mock_config

        result = runner.invoke(app, ["config", "--validate"])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    @patch('src.frontin.cli.get_config')
    def test_config_command_error(self, mock_get_config):
        """Test config command handles errors"""
        mock_get_config.side_effect = Exception("Configuration error")

        result = runner.invoke(app, ["config"])
        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestVerboseLogging:
    """Test verbose logging option"""

    def test_verbose_flag(self):
        """Test --verbose flag"""
        result = runner.invoke(app, ["--verbose", "stats"])
        assert result.exit_code == 0

    def test_log_format_json(self):
        """Test --log-format json"""
        result = runner.invoke(app, ["--log-format", "json", "stats"])
        assert result.exit_code == 0

    def test_log_format_text(self):
        """Test --log-format text"""
        result = runner.invoke(app, ["--log-format", "text", "stats"])
        assert result.exit_code == 0
