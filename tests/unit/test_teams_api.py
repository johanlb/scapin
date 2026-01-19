"""
Tests for Teams API endpoints

Tests for POST /api/teams/chats/{chat_id}/read endpoint.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app
from src.frontin.api.routers.teams import _get_teams_service


@pytest.fixture
def mock_teams_service():
    """Create mock teams service"""
    return AsyncMock()


@pytest.fixture
def app(mock_teams_service):
    """Create test app with mocked service"""
    app = create_app()
    app.dependency_overrides[_get_teams_service] = lambda: mock_teams_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestMarkChatAsReadEndpoint:
    """Tests for POST /api/teams/chats/{chat_id}/read"""

    def test_mark_chat_as_read_success(self, client, mock_teams_service):
        """Mark chat as read returns success"""
        mock_teams_service.mark_chat_as_read.return_value = True

        response = client.post("/api/teams/chats/chat123/read")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["chat_id"] == "chat123"
        assert data["data"]["marked_as_read"] is True

        mock_teams_service.mark_chat_as_read.assert_called_once_with("chat123")

    def test_mark_chat_as_read_failure(self, client, mock_teams_service):
        """Mark chat as read returns 400 when service fails"""
        mock_teams_service.mark_chat_as_read.return_value = False

        response = client.post("/api/teams/chats/chat456/read")

        assert response.status_code == 400
        assert "Failed to mark chat" in response.json()["detail"]

    def test_mark_chat_as_read_with_special_chars(self, client, mock_teams_service):
        """Mark chat as read handles chat IDs with special characters"""
        mock_teams_service.mark_chat_as_read.return_value = True

        # URL-encoded chat ID with special characters
        chat_id = "19:meeting_abc123@thread.v2"
        response = client.post(f"/api/teams/chats/{chat_id}/read")

        assert response.status_code == 200
        mock_teams_service.mark_chat_as_read.assert_called_once_with(chat_id)

    def test_mark_chat_as_read_service_exception(self, client, mock_teams_service):
        """Mark chat as read returns 500 when service raises exception"""
        mock_teams_service.mark_chat_as_read.side_effect = Exception("Graph API error")

        response = client.post("/api/teams/chats/chat789/read")

        assert response.status_code == 500
        assert "Graph API error" in response.json()["detail"]


class TestTeamsServiceMarkAsRead:
    """Tests for TeamsService.mark_chat_as_read method"""

    @pytest.mark.asyncio
    async def test_mark_chat_as_read_disabled(self):
        """mark_chat_as_read returns False when Teams disabled"""
        from unittest.mock import patch

        from src.frontin.api.services.teams_service import TeamsService

        with patch("src.frontin.api.services.teams_service.get_config") as mock_config:
            mock_config.return_value.teams.enabled = False
            service = TeamsService()

            result = await service.mark_chat_as_read("chat123")

            assert result is False

    @pytest.mark.asyncio
    async def test_mark_chat_as_read_calls_processor(self):
        """mark_chat_as_read calls processor teams_client"""
        from unittest.mock import MagicMock, patch

        from src.frontin.api.services.teams_service import TeamsService

        with patch("src.frontin.api.services.teams_service.get_config") as mock_config:
            mock_config.return_value.teams.enabled = True

            service = TeamsService()
            mock_processor = MagicMock()
            mock_processor.teams_client.mark_chat_as_read = AsyncMock(return_value=True)
            service._processor = mock_processor

            result = await service.mark_chat_as_read("chat123")

            assert result is True
            mock_processor.teams_client.mark_chat_as_read.assert_called_once_with("chat123")

    @pytest.mark.asyncio
    async def test_mark_chat_as_read_increments_state(self):
        """mark_chat_as_read increments state counter on success"""
        from unittest.mock import MagicMock, patch

        from src.frontin.api.services.teams_service import TeamsService

        with (
            patch("src.frontin.api.services.teams_service.get_config") as mock_config,
            patch("src.frontin.api.services.teams_service.get_state_manager") as mock_state_mgr,
        ):
            mock_config.return_value.teams.enabled = True
            mock_state = MagicMock()
            mock_state_mgr.return_value = mock_state

            service = TeamsService()
            mock_processor = MagicMock()
            mock_processor.teams_client.mark_chat_as_read = AsyncMock(return_value=True)
            service._processor = mock_processor

            await service.mark_chat_as_read("chat123")

            mock_state.increment.assert_called_once_with("teams_chats_marked_read")

    @pytest.mark.asyncio
    async def test_mark_chat_as_read_exception_handling(self):
        """mark_chat_as_read handles exceptions gracefully"""
        from unittest.mock import MagicMock, patch

        from src.frontin.api.services.teams_service import TeamsService

        with patch("src.frontin.api.services.teams_service.get_config") as mock_config:
            mock_config.return_value.teams.enabled = True

            service = TeamsService()
            mock_processor = MagicMock()
            mock_processor.teams_client.mark_chat_as_read = AsyncMock(
                side_effect=Exception("Network error")
            )
            service._processor = mock_processor

            result = await service.mark_chat_as_read("chat123")

            assert result is False
