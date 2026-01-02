"""
Unit tests for Health Check System
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.schemas import HealthCheck, ServiceStatus, SystemHealth
from src.monitoring.health import (
    HealthCheckService,
    check_ai_api_health,
    check_config_health,
    check_disk_space_health,
    check_filesystem_health,
    check_git_health,
    check_imap_health,
    check_python_dependencies,
    check_queue_health,
    get_health_service,
)


class TestHealthCheckService:
    """Test HealthCheckService"""

    def setup_method(self):
        """Create fresh service for each test"""
        self.service = HealthCheckService()

    def test_register_checker(self):
        """Test registering a health checker"""

        def dummy_checker() -> HealthCheck:
            return HealthCheck(
                service="test", status=ServiceStatus.HEALTHY, message="OK"
            )

        self.service.register_checker("test", dummy_checker)

        # Should be able to check this service now
        result = self.service.check_service("test")
        assert result is not None
        assert result.service == "test"

    def test_check_nonexistent_service(self):
        """Test checking a service that doesn't exist"""
        result = self.service.check_service("nonexistent")
        assert result is None

    def test_check_service_caching(self):
        """Test that health checks are cached"""
        call_count = 0

        def counting_checker() -> HealthCheck:
            nonlocal call_count
            call_count += 1
            return HealthCheck(
                service="cached", status=ServiceStatus.HEALTHY, message="OK"
            )

        self.service.register_checker("cached", counting_checker)

        # First call - should execute
        self.service.check_service("cached", use_cache=True)
        assert call_count == 1

        # Second call - should use cache
        self.service.check_service("cached", use_cache=True)
        assert call_count == 1  # Not incremented

        # Third call without cache - should execute
        self.service.check_service("cached", use_cache=False)
        assert call_count == 2

    def test_check_service_error_handling(self):
        """Test health check error handling"""

        def failing_checker() -> HealthCheck:
            raise Exception("Simulated failure")

        self.service.register_checker("failing", failing_checker)

        result = self.service.check_service("failing")
        assert result is not None
        assert result.status == ServiceStatus.UNHEALTHY
        assert "Simulated failure" in result.message

    def test_check_all_services(self):
        """Test checking all registered services"""

        def checker1() -> HealthCheck:
            return HealthCheck(
                service="service1", status=ServiceStatus.HEALTHY, message="OK"
            )

        def checker2() -> HealthCheck:
            return HealthCheck(
                service="service2", status=ServiceStatus.HEALTHY, message="OK"
            )

        self.service.register_checker("service1", checker1)
        self.service.register_checker("service2", checker2)

        health = self.service.check_all()

        assert isinstance(health, SystemHealth)
        assert len(health.checks) == 2
        assert health.overall_status == ServiceStatus.HEALTHY

    def test_check_all_with_unhealthy_service(self):
        """Test overall status when a service is unhealthy"""

        def healthy_checker() -> HealthCheck:
            return HealthCheck(
                service="healthy", status=ServiceStatus.HEALTHY, message="OK"
            )

        def unhealthy_checker() -> HealthCheck:
            return HealthCheck(
                service="unhealthy", status=ServiceStatus.UNHEALTHY, message="Failed"
            )

        self.service.register_checker("healthy", healthy_checker)
        self.service.register_checker("unhealthy", unhealthy_checker)

        health = self.service.check_all()

        assert health.overall_status == ServiceStatus.UNHEALTHY
        assert "unhealthy" in health.unhealthy_services

    def test_clear_cache(self):
        """Test clearing cache"""
        call_count = 0

        def counting_checker() -> HealthCheck:
            nonlocal call_count
            call_count += 1
            return HealthCheck(
                service="test", status=ServiceStatus.HEALTHY, message="OK"
            )

        self.service.register_checker("test", counting_checker)

        # Cache a result
        self.service.check_service("test")
        assert call_count == 1

        # Clear cache
        self.service.clear_cache()

        # Should execute again
        self.service.check_service("test")
        assert call_count == 2


class TestFilesystemHealthCheck:
    """Test filesystem health checker"""

    def test_healthy_filesystem(self):
        """Test health check with healthy filesystem"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_filesystem_health(Path(tmpdir))

            assert result.service == "filesystem"
            assert result.status == ServiceStatus.HEALTHY
            assert "readable and writable" in result.message.lower()

    def test_nonexistent_path(self):
        """Test health check with nonexistent path"""
        result = check_filesystem_health(Path("/nonexistent/path/12345"))

        assert result.status == ServiceStatus.UNHEALTHY
        assert "does not exist" in result.message.lower()

    def test_readonly_filesystem(self):
        """Test health check with readonly filesystem"""
        # This test is platform-specific and might not work on all systems
        # Skipping for now as it requires special permissions
        pass


class TestGitHealthCheck:
    """Test git health checker"""

    def test_git_healthy(self):
        """Test health check with initialized git repo"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Initialize git repo
            import subprocess

            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            result = check_git_health(tmppath)

            assert result.service == "git"
            assert result.status == ServiceStatus.HEALTHY
            assert result.details.get("initialized") is True

    def test_git_not_initialized(self):
        """Test health check with no git repo"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_git_health(Path(tmpdir))

            assert result.status == ServiceStatus.DEGRADED
            assert "not initialized" in result.message.lower()


class TestConfigHealthCheck:
    """Test config health checker"""

    def test_config_missing_directory(self):
        """Test health check with missing config directory"""
        result = check_config_health(Path("/nonexistent/config"))

        assert result.status == ServiceStatus.UNHEALTHY
        assert "not found" in result.message.lower()

    def test_config_missing_files(self):
        """Test health check with missing config files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Create only one required file
            (config_dir / "defaults.yaml").write_text("test: value")

            result = check_config_health(config_dir)

            # Should be degraded due to missing logging.yaml
            assert result.status == ServiceStatus.DEGRADED
            assert "logging.yaml" in result.message.lower()


class TestPythonDependenciesCheck:
    """Test Python dependencies checker"""

    def test_dependencies_check(self):
        """Test that required packages are installed"""
        result = check_python_dependencies()

        assert result.service == "dependencies"

        # Should have pydantic installed at minimum
        assert result.details.get("installed") is not None

        # Status should be healthy or degraded (not unhealthy)
        assert result.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]


class TestIMAPHealthCheck:
    """Test IMAP health checker (Phase 3)"""

    @patch("src.core.config_manager.get_config")
    @patch("src.integrations.email.imap_client.IMAPClient")
    def test_imap_health_successful_connection(self, mock_imap_client, mock_get_config):
        """Test IMAP health check with successful connection"""
        # Mock config
        mock_account = Mock()
        mock_account.account_id = "test"
        mock_account.account_name = "Test Account"
        mock_account.imap_host = "imap.test.com"
        mock_account.imap_port = 993

        mock_config = Mock()
        mock_config.email.get_enabled_accounts.return_value = [mock_account]
        mock_get_config.return_value = mock_config

        # Mock IMAP client
        mock_client = Mock()
        mock_client.connect.return_value = None
        mock_client.disconnect.return_value = None
        mock_imap_client.return_value = mock_client

        result = check_imap_health()

        assert result.service == "imap"
        assert result.status == ServiceStatus.HEALTHY
        assert "successful" in result.message.lower()
        assert result.details["account_id"] == "test"

    @patch("src.core.config_manager.get_config")
    def test_imap_health_no_accounts(self, mock_get_config):
        """Test IMAP health check with no accounts configured"""
        mock_config = Mock()
        mock_config.email.get_enabled_accounts.return_value = []
        mock_get_config.return_value = mock_config

        result = check_imap_health()

        assert result.status == ServiceStatus.DEGRADED
        assert "no imap accounts" in result.message.lower()

    @patch("src.core.config_manager.get_config")
    @patch("src.integrations.email.imap_client.IMAPClient")
    def test_imap_health_connection_failure(self, mock_imap_client, mock_get_config):
        """Test IMAP health check with connection failure"""
        # Mock config
        mock_account = Mock()
        mock_account.account_id = "test"
        mock_account.account_name = "Test Account"
        mock_account.imap_host = "imap.test.com"
        mock_account.imap_port = 993

        mock_config = Mock()
        mock_config.email.get_enabled_accounts.return_value = [mock_account]
        mock_get_config.return_value = mock_config

        # Mock IMAP client failure
        mock_imap_client.side_effect = Exception("Connection refused")

        result = check_imap_health()

        assert result.status == ServiceStatus.UNHEALTHY
        assert "connection refused" in result.message.lower()


class TestAIAPIHealthCheck:
    """Test AI API health checker (Phase 3)"""

    @patch("src.core.config_manager.get_config")
    @patch("anthropic.Anthropic")
    def test_ai_api_health_successful(self, mock_anthropic, mock_get_config):
        """Test AI API health check with successful connection"""
        # Mock config
        mock_config = Mock()
        mock_config.ai.anthropic_api_key = "sk-test-key"
        mock_config.ai.rate_limit_per_minute = 40
        mock_get_config.return_value = mock_config

        # Mock Anthropic client
        mock_client = Mock()
        mock_client.messages.count_tokens.return_value = Mock(input_tokens=1)
        mock_anthropic.return_value = mock_client

        result = check_ai_api_health()

        assert result.service == "ai_api"
        assert result.status == ServiceStatus.HEALTHY
        assert "successful" in result.message.lower()

    @patch("src.core.config_manager.get_config")
    @patch("anthropic.Anthropic")
    def test_ai_api_health_authentication_error(self, mock_anthropic, mock_get_config):
        """Test AI API health check with authentication error"""
        from anthropic import AuthenticationError

        # Mock config
        mock_config = Mock()
        mock_config.ai.anthropic_api_key = "invalid-key"
        mock_get_config.return_value = mock_config

        # Mock Anthropic client failure
        mock_client = Mock()
        mock_client.messages.count_tokens.side_effect = AuthenticationError("Invalid API key", response=Mock(), body=None)
        mock_anthropic.return_value = mock_client

        result = check_ai_api_health()

        assert result.status == ServiceStatus.UNHEALTHY
        assert "authentication failed" in result.message.lower()

    @patch("src.core.config_manager.get_config")
    @patch("anthropic.Anthropic")
    def test_ai_api_health_rate_limit(self, mock_anthropic, mock_get_config):
        """Test AI API health check with rate limit error"""
        from anthropic import RateLimitError

        # Mock config
        mock_config = Mock()
        mock_config.ai.anthropic_api_key = "sk-test-key"
        mock_get_config.return_value = mock_config

        # Mock Anthropic client rate limit
        mock_client = Mock()
        mock_client.messages.count_tokens.side_effect = RateLimitError("Rate limit exceeded", response=Mock(), body=None)
        mock_anthropic.return_value = mock_client

        result = check_ai_api_health()

        assert result.status == ServiceStatus.DEGRADED
        assert "rate limit" in result.message.lower()


class TestDiskSpaceHealthCheck:
    """Test disk space health checker (Phase 3)"""

    @patch("shutil.disk_usage")
    def test_disk_space_healthy(self, mock_disk_usage):
        """Test disk space health check with healthy disk"""
        # Mock disk usage: 50% used
        mock_usage = Mock()
        mock_usage.total = 1000 * (1024**3)  # 1000 GB
        mock_usage.used = 500 * (1024**3)   # 500 GB
        mock_usage.free = 500 * (1024**3)   # 500 GB
        mock_disk_usage.return_value = mock_usage

        result = check_disk_space_health()

        assert result.service == "disk_space"
        assert result.status == ServiceStatus.HEALTHY
        assert "healthy" in result.message.lower()

    @patch("shutil.disk_usage")
    def test_disk_space_low(self, mock_disk_usage):
        """Test disk space health check with low disk space"""
        # Mock disk usage: 90% used
        mock_usage = Mock()
        mock_usage.total = 1000 * (1024**3)
        mock_usage.used = 900 * (1024**3)
        mock_usage.free = 100 * (1024**3)
        mock_disk_usage.return_value = mock_usage

        result = check_disk_space_health()

        assert result.status == ServiceStatus.DEGRADED
        assert "low" in result.message.lower()

    @patch("shutil.disk_usage")
    def test_disk_space_critical(self, mock_disk_usage):
        """Test disk space health check with critical disk space"""
        # Mock disk usage: 96% used
        mock_usage = Mock()
        mock_usage.total = 1000 * (1024**3)
        mock_usage.used = 960 * (1024**3)
        mock_usage.free = 40 * (1024**3)
        mock_disk_usage.return_value = mock_usage

        result = check_disk_space_health()

        assert result.status == ServiceStatus.UNHEALTHY
        assert "critical" in result.message.lower()


class TestQueueHealthCheck:
    """Test queue health checker (Phase 3)"""

    @patch("src.integrations.storage.queue_storage.get_queue_storage")
    def test_queue_health_empty(self, mock_get_queue_storage):
        """Test queue health check with empty queue"""
        mock_storage = Mock()
        mock_storage.get_stats.return_value = {
            "total": 0,
            "by_status": {"pending": 0},
        }
        mock_get_queue_storage.return_value = mock_storage

        result = check_queue_health()

        assert result.service == "queue"
        assert result.status == ServiceStatus.HEALTHY
        assert result.details["total"] == 0

    @patch("src.integrations.storage.queue_storage.get_queue_storage")
    def test_queue_health_small(self, mock_get_queue_storage):
        """Test queue health check with small queue"""
        mock_storage = Mock()
        mock_storage.get_stats.return_value = {
            "total": 50,
            "by_status": {"pending": 30},
        }
        mock_get_queue_storage.return_value = mock_storage

        result = check_queue_health()

        assert result.status == ServiceStatus.HEALTHY
        assert result.details["total"] == 50

    @patch("src.integrations.storage.queue_storage.get_queue_storage")
    def test_queue_health_growing(self, mock_get_queue_storage):
        """Test queue health check with growing queue"""
        mock_storage = Mock()
        mock_storage.get_stats.return_value = {
            "total": 150,
            "by_status": {"pending": 100},
        }
        mock_get_queue_storage.return_value = mock_storage

        result = check_queue_health()

        assert result.status == ServiceStatus.DEGRADED
        assert "growing" in result.message.lower()

    @patch("src.integrations.storage.queue_storage.get_queue_storage")
    def test_queue_health_large(self, mock_get_queue_storage):
        """Test queue health check with large queue"""
        mock_storage = Mock()
        mock_storage.get_stats.return_value = {
            "total": 1500,
            "by_status": {"pending": 1200},
        }
        mock_get_queue_storage.return_value = mock_storage

        result = check_queue_health()

        assert result.status == ServiceStatus.DEGRADED
        assert "large" in result.message.lower()


class TestGetHealthService:
    """Test global health service singleton"""

    def test_get_health_service_singleton(self):
        """Test that get_health_service returns same instance"""
        service1 = get_health_service()
        service2 = get_health_service()

        assert service1 is service2

    def test_health_service_has_default_checkers(self):
        """Test that default checkers are registered"""
        service = get_health_service()

        # Should have built-in checkers registered
        result = service.check_service("filesystem")
        assert result is not None

        result = service.check_service("git")
        assert result is not None

        result = service.check_service("config")
        assert result is not None

        result = service.check_service("dependencies")
        assert result is not None

    def test_health_service_has_phase3_checkers(self):
        """Test that Phase 3 checkers are registered"""
        service = get_health_service()

        # Phase 3 checkers
        result = service.check_service("imap")
        assert result is not None

        result = service.check_service("ai_api")
        assert result is not None

        result = service.check_service("disk_space")
        assert result is not None

        result = service.check_service("queue")
        assert result is not None
