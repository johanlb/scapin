"""
Tests for Auth Router

Tests login endpoint and authentication flow.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app


class TestLoginEndpoint:
    """Tests for POST /api/auth/login"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_app()
        return TestClient(app)

    def test_login_success_with_real_config(self, client):
        """Valid PIN should return JWT token (using .env config)"""
        # This test uses the real .env configuration
        response = client.post(
            "/api/auth/login",
            json={"pin": "1234"},  # PIN from .env
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["expires_in"] > 0

    def test_login_wrong_pin(self, client):
        """Wrong PIN should return 401"""
        response = client.post(
            "/api/auth/login",
            json={"pin": "0000"},
        )

        assert response.status_code == 401
        data = response.json()
        # HTTPException returns {"detail": "..."}
        assert "detail" in data
        assert "incorrect" in data["detail"].lower() or "invalide" in data["detail"].lower()

    def test_login_invalid_pin_format_too_short(self, client):
        """PIN shorter than 4 digits should fail validation"""
        response = client.post(
            "/api/auth/login",
            json={"pin": "123"},
        )

        assert response.status_code == 422  # Validation error

    def test_login_invalid_pin_format_too_long(self, client):
        """PIN longer than 6 digits should fail validation"""
        response = client.post(
            "/api/auth/login",
            json={"pin": "1234567"},
        )

        assert response.status_code == 422  # Validation error


class TestCheckEndpoint:
    """Tests for GET /api/auth/check"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_app()
        return TestClient(app)

    def test_check_with_valid_token(self, client):
        """Valid token should return user info"""
        # First login to get token
        login_response = client.post(
            "/api/auth/login",
            json={"pin": "1234"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]

        # Then check with token
        response = client.get(
            "/api/auth/check",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["authenticated"] is True
        assert data["data"]["user"] == "johan"

    def test_check_without_token(self, client):
        """Missing token should return 401 when auth is enabled"""
        response = client.get("/api/auth/check")

        # Should be 401 since auth is enabled in .env
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_check_with_invalid_token(self, client):
        """Invalid token should return 401"""
        response = client.get(
            "/api/auth/check",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


class TestAuthDisabled:
    """Tests when auth is disabled"""

    @pytest.fixture
    def client_auth_disabled(self):
        """Create test client with auth disabled"""
        # Create a mock config with auth disabled
        mock_config = MagicMock()
        mock_config.auth.enabled = False
        mock_config.auth.jwt_secret_key = "test-secret-key-minimum-32-characters"
        mock_config.auth.jwt_algorithm = "HS256"
        mock_config.auth.jwt_expire_minutes = 60
        mock_config.auth.pin_hash = ""

        with patch("src.frontin.api.routers.auth.get_config", return_value=mock_config), patch(
            "src.frontin.api.deps.get_cached_config", return_value=mock_config
        ), patch("src.core.config_manager.get_config", return_value=mock_config), patch(
            "src.frontin.api.auth.jwt_handler.get_config", return_value=mock_config
        ):
            app = create_app()
            yield TestClient(app)

    def test_login_auth_disabled(self, client_auth_disabled):
        """When auth is disabled, any PIN should work"""
        response = client_auth_disabled.post(
            "/api/auth/login",
            json={"pin": "0000"},  # Any PIN
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    def test_check_auth_disabled_no_token(self, client_auth_disabled):
        """When auth is disabled, check endpoint should work without token"""
        response = client_auth_disabled.get("/api/auth/check")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["authenticated"] is True
        assert data["data"]["auth_required"] is False
