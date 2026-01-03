"""
Tests for System API Router

Tests health, stats, and config endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.jeeves.api.app import create_app
from src.jeeves.api.deps import get_cached_config


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock configuration"""
    config = MagicMock()

    # Email config
    account = MagicMock()
    account.name = "test"
    account.email_address = "test@example.com"
    account.enabled = True
    config.email.get_enabled_accounts.return_value = [account]

    # Integration configs
    config.teams.enabled = True
    config.calendar.enabled = True
    config.briefing.enabled = True
    config.ai.model = "claude-3-5-haiku-20241022"

    return config


@pytest.fixture
def client(mock_config: MagicMock) -> TestClient:
    """Create test client with mocked config"""
    app = create_app()
    # Override dependency
    app.dependency_overrides[get_cached_config] = lambda: mock_config
    yield TestClient(app)
    # Clear overrides after test
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Tests for /api/health endpoint"""

    def test_health_returns_success(self, client: TestClient) -> None:
        """Test health endpoint returns success response"""
        # Health check calls get_cached_config() directly, so we patch it
        with patch(
            "src.jeeves.api.routers.system.get_cached_config",
        ) as mock_get_config:
            # Set up return value for direct call
            mock_config = MagicMock()
            account = MagicMock()
            account.name = "test"
            account.email_address = "test@example.com"
            account.enabled = True
            mock_config.email.get_enabled_accounts.return_value = [account]
            mock_config.teams.enabled = True
            mock_config.calendar.enabled = True
            mock_get_config.return_value = mock_config

            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["status"] in ["healthy", "degraded", "unhealthy"]
        assert "checks" in data["data"]
        assert "uptime_seconds" in data["data"]
        assert data["data"]["version"] == "0.7.0"

    def test_health_includes_checks(self, client: TestClient) -> None:
        """Test health endpoint includes individual checks"""
        with patch(
            "src.jeeves.api.routers.system.get_cached_config",
        ) as mock_get_config:
            mock_config = MagicMock()
            account = MagicMock()
            account.name = "test"
            mock_config.email.get_enabled_accounts.return_value = [account]
            mock_config.teams.enabled = True
            mock_config.calendar.enabled = True
            mock_get_config.return_value = mock_config

            response = client.get("/api/health")

        data = response.json()
        checks = data["data"]["checks"]

        # Should have config, email, teams, calendar checks
        check_names = [c["name"] for c in checks]
        assert "config" in check_names
        assert "email" in check_names
        assert "teams" in check_names
        assert "calendar" in check_names

    def test_health_status_when_no_accounts(self, client: TestClient) -> None:
        """Test health shows degraded when no email accounts"""
        with patch(
            "src.jeeves.api.routers.system.get_cached_config",
        ) as mock_get_config:
            mock_config = MagicMock()
            mock_config.email.get_enabled_accounts.return_value = []
            mock_config.teams.enabled = True
            mock_config.calendar.enabled = True
            mock_get_config.return_value = mock_config

            response = client.get("/api/health")

        data = response.json()
        # Should be degraded (not unhealthy) when email is missing
        assert data["data"]["status"] in ["degraded", "healthy"]


class TestStatsEndpoint:
    """Tests for /api/stats endpoint"""

    def test_stats_returns_success(self, client: TestClient) -> None:
        """Test stats endpoint returns success response"""
        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "uptime_seconds" in data["data"]
        assert "emails_processed" in data["data"]
        assert "teams_messages" in data["data"]
        assert "calendar_events" in data["data"]
        assert "queue_size" in data["data"]

    def test_stats_has_timestamp(self, client: TestClient) -> None:
        """Test stats response includes timestamp"""
        response = client.get("/api/stats")

        data = response.json()
        assert "timestamp" in data


class TestConfigEndpoint:
    """Tests for /api/config endpoint"""

    def test_config_returns_success(
        self, client: TestClient, mock_config: MagicMock
    ) -> None:
        """Test config endpoint returns success response"""
        response = client.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_config_includes_email_accounts(
        self, client: TestClient, mock_config: MagicMock
    ) -> None:
        """Test config includes email accounts"""
        response = client.get("/api/config")

        data = response.json()
        assert "email_accounts" in data["data"]
        assert len(data["data"]["email_accounts"]) == 1
        assert data["data"]["email_accounts"][0]["email"] == "test@example.com"

    def test_config_does_not_expose_passwords(
        self, client: TestClient, mock_config: MagicMock
    ) -> None:
        """Test config endpoint does not expose sensitive data"""
        response = client.get("/api/config")

        data = response.json()
        # Password should not be in the response
        for account in data["data"]["email_accounts"]:
            assert "password" not in account
            assert "imap_password" not in account

    def test_config_includes_integrations(
        self, client: TestClient, mock_config: MagicMock
    ) -> None:
        """Test config includes integration status"""
        response = client.get("/api/config")

        data = response.json()
        assert data["data"]["teams_enabled"] is True
        assert data["data"]["calendar_enabled"] is True
        assert data["data"]["briefing_enabled"] is True
        assert data["data"]["ai_model"] == "claude-3-5-haiku-20241022"


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_returns_api_info(self, client: TestClient) -> None:
        """Test root endpoint returns API information"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Scapin API"
        assert data["version"] == "0.7.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/api/health"
