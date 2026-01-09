"""
Tests for Teams API Router

Tests Teams chat listing, messages, replies, flagging, and polling endpoints.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.jeeves.api.app import create_app
from src.jeeves.api.routers.teams import _get_teams_service


@pytest.fixture
def mock_teams_service() -> MagicMock:
    """Create mock Teams service"""
    service = MagicMock()

    # Sample chat
    service.sample_chat = {
        "id": "chat-123",
        "topic": "Project Discussion",
        "chat_type": "group",
        "created_at": "2026-01-01T08:00:00+00:00",
        "last_message_at": "2026-01-04T09:30:00+00:00",
        "member_count": 5,
        "unread_count": 3,
    }

    # Sample message
    service.sample_message = {
        "id": "msg-456",
        "chat_id": "chat-123",
        "sender": {
            "id": "user-789",
            "display_name": "John Doe",
            "email": "john@example.com",
        },
        "content": "<p>Hello team!</p>",
        "content_preview": "Hello team!",
        "created_at": "2026-01-04T09:30:00+00:00",
        "is_read": False,
        "importance": "normal",
        "has_mentions": True,
        "attachments_count": 0,
    }

    # Mock async methods
    service.get_chats = AsyncMock(return_value=[service.sample_chat])
    service.get_messages = AsyncMock(return_value=[service.sample_message])
    service.send_reply = AsyncMock(return_value=True)
    service.flag_message = AsyncMock(return_value=True)
    service.poll = AsyncMock(return_value={
        "messages_fetched": 25,
        "messages_new": 8,
        "chats_checked": 10,
        "polled_at": "2026-01-04T10:00:00+00:00",
    })
    service.get_stats = AsyncMock(return_value={
        "total_chats": 15,
        "unread_chats": 4,
        "messages_processed": 250,
        "messages_flagged": 12,
        "last_poll": "2026-01-04T09:55:00+00:00",
    })

    return service


@pytest.fixture
def client(mock_teams_service: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked service"""
    app = create_app()
    app.dependency_overrides[_get_teams_service] = lambda: mock_teams_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListTeamsChats:
    """Tests for GET /api/teams/chats endpoint"""

    def test_list_returns_success(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test listing chats returns success"""
        response = client.get("/api/teams/chats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_list_includes_pagination(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test listing includes pagination info"""
        response = client.get("/api/teams/chats?page=1&page_size=20")

        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "has_more" in data
        assert "total" in data

    def test_list_chat_includes_details(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test chat includes all details"""
        response = client.get("/api/teams/chats")

        data = response.json()["data"][0]
        assert data["id"] == "chat-123"
        assert data["topic"] == "Project Discussion"
        assert data["chat_type"] == "group"
        assert data["member_count"] == 5
        assert data["unread_count"] == 3


class TestListTeamsMessages:
    """Tests for GET /api/teams/chats/{chat_id}/messages endpoint"""

    def test_list_returns_success(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test listing messages returns success"""
        response = client.get("/api/teams/chats/chat-123/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_list_includes_pagination(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test listing includes pagination"""
        response = client.get("/api/teams/chats/chat-123/messages?page=1&page_size=50")

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_list_filters_by_since(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test listing can filter by since parameter"""
        response = client.get(
            "/api/teams/chats/chat-123/messages?since=2026-01-04T09:00:00"
        )

        assert response.status_code == 200
        mock_teams_service.get_messages.assert_called_once()

    def test_list_message_includes_details(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test message includes all details"""
        response = client.get("/api/teams/chats/chat-123/messages")

        data = response.json()["data"][0]
        assert data["id"] == "msg-456"
        assert data["sender"]["display_name"] == "John Doe"
        assert data["content_preview"] == "Hello team!"
        assert data["has_mentions"] is True


class TestReplyToMessage:
    """Tests for POST /api/teams/chats/{chat_id}/messages/{message_id}/reply endpoint"""

    def test_reply_returns_success(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test replying returns success"""
        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/reply",
            json={"content": "Thanks for the update!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["replied"] is True

    def test_reply_requires_content(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test reply requires content field"""
        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/reply",
            json={},
        )

        assert response.status_code == 422

    def test_reply_content_not_empty(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test reply content cannot be empty"""
        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/reply",
            json={"content": ""},
        )

        assert response.status_code == 422

    def test_reply_failure(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test reply failure returns 400"""
        mock_teams_service.send_reply = AsyncMock(return_value=False)

        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/reply",
            json={"content": "Test reply"},
        )

        assert response.status_code == 400


class TestFlagMessage:
    """Tests for POST /api/teams/chats/{chat_id}/messages/{message_id}/flag endpoint"""

    def test_flag_returns_success(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test flagging message returns success"""
        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/flag",
            json={"flag": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["flagged"] is True

    def test_unflag_returns_success(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test unflagging message returns success"""
        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/flag",
            json={"flag": False},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["flagged"] is False

    def test_flag_with_reason(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test flagging with reason"""
        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/flag",
            json={"flag": True, "reason": "Need to follow up"},
        )

        assert response.status_code == 200
        call_kwargs = mock_teams_service.flag_message.call_args[1]
        assert call_kwargs["reason"] == "Need to follow up"

    def test_flag_default_is_true(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test flag defaults to True"""
        response = client.post(
            "/api/teams/chats/chat-123/messages/msg-456/flag",
            json={},
        )

        assert response.status_code == 200
        call_kwargs = mock_teams_service.flag_message.call_args[1]
        assert call_kwargs["flag"] is True


class TestPollTeams:
    """Tests for POST /api/teams/poll endpoint"""

    def test_poll_returns_success(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test polling returns success"""
        response = client.post("/api/teams/poll")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_poll_includes_counts(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test poll includes message counts"""
        response = client.post("/api/teams/poll")

        data = response.json()["data"]
        assert data["messages_fetched"] == 25
        assert data["messages_new"] == 8
        assert data["chats_checked"] == 10
        assert "polled_at" in data


class TestGetTeamsStats:
    """Tests for GET /api/teams/stats endpoint"""

    def test_stats_returns_success(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test stats returns success"""
        response = client.get("/api/teams/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stats_includes_counts(self, client: TestClient, mock_teams_service: MagicMock) -> None:
        """Test stats includes all counts"""
        response = client.get("/api/teams/stats")

        data = response.json()["data"]
        assert data["total_chats"] == 15
        assert data["unread_chats"] == 4
        assert data["messages_processed"] == 250
        assert data["messages_flagged"] == 12
