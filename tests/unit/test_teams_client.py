"""
Unit Tests for Teams Client

Tests TeamsClient with mocked GraphClient.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.microsoft.models import TeamsChatType, TeamsMessageImportance
from src.integrations.microsoft.teams_client import TeamsClient


class TestTeamsClient:
    """Tests for TeamsClient"""

    @pytest.fixture
    def mock_graph_client(self):
        """Create mock GraphClient"""
        mock = MagicMock()
        mock.get = AsyncMock()
        mock.post = AsyncMock()
        mock.get_all_pages = AsyncMock()
        return mock

    @pytest.fixture
    def teams_client(self, mock_graph_client):
        """Create TeamsClient with mock"""
        return TeamsClient(graph=mock_graph_client)


class TestGetChats(TestTeamsClient):
    """Tests for get_chats method"""

    @pytest.mark.asyncio
    async def test_get_chats_returns_chat_list(self, teams_client, mock_graph_client):
        """Test getting list of chats"""
        mock_graph_client.get_all_pages.return_value = [
            {
                "id": "chat-001",
                "chatType": "oneOnOne",
                "topic": None,
                "createdDateTime": "2025-01-15T10:00:00Z",
            },
            {
                "id": "chat-002",
                "chatType": "group",
                "topic": "Team Discussion",
                "createdDateTime": "2025-01-14T09:00:00Z",
            },
        ]

        chats = await teams_client.get_chats()

        assert len(chats) == 2
        assert chats[0].chat_id == "chat-001"
        assert chats[0].chat_type == TeamsChatType.ONE_ON_ONE
        assert chats[1].chat_id == "chat-002"
        assert chats[1].chat_type == TeamsChatType.GROUP
        assert chats[1].topic == "Team Discussion"

    @pytest.mark.asyncio
    async def test_get_chats_calls_correct_endpoint(self, teams_client, mock_graph_client):
        """Test that correct API endpoint is called"""
        mock_graph_client.get_all_pages.return_value = []

        await teams_client.get_chats()

        mock_graph_client.get_all_pages.assert_called_once_with("/me/chats")

    @pytest.mark.asyncio
    async def test_get_chats_handles_empty_response(self, teams_client, mock_graph_client):
        """Test handling empty chat list"""
        mock_graph_client.get_all_pages.return_value = []

        chats = await teams_client.get_chats()

        assert chats == []


class TestGetMessages(TestTeamsClient):
    """Tests for get_messages method"""

    @pytest.mark.asyncio
    async def test_get_messages_returns_message_list(self, teams_client, mock_graph_client):
        """Test getting messages from a chat"""
        mock_graph_client.get.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "createdDateTime": "2025-01-15T14:30:00Z",
                    "from": {
                        "user": {
                            "id": "user-123",
                            "displayName": "John Doe",
                            "email": "john@example.com",
                        }
                    },
                    "body": {
                        "content": "<p>Hello World</p>",
                    },
                    "importance": "normal",
                    "mentions": [],
                    "attachments": [],
                },
            ]
        }

        messages = await teams_client.get_messages("chat-001", limit=10)

        assert len(messages) == 1
        assert messages[0].message_id == "msg-001"
        assert messages[0].chat_id == "chat-001"
        assert messages[0].sender.user_id == "user-123"
        assert messages[0].sender.display_name == "John Doe"
        assert "Hello World" in messages[0].content_plain

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, teams_client, mock_graph_client):
        """Test limit parameter is passed correctly"""
        mock_graph_client.get.return_value = {"value": []}

        await teams_client.get_messages("chat-001", limit=25)

        call_args = mock_graph_client.get.call_args
        assert call_args[1]["params"]["$top"] == "25"  # Params are strings

    @pytest.mark.asyncio
    async def test_get_messages_with_since(self, teams_client, mock_graph_client):
        """Test since parameter filters by date"""
        mock_graph_client.get.return_value = {"value": []}
        since = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)

        await teams_client.get_messages("chat-001", since=since)

        call_args = mock_graph_client.get.call_args
        assert "$filter" in call_args[1]["params"]
        assert "createdDateTime gt" in call_args[1]["params"]["$filter"]

    @pytest.mark.asyncio
    async def test_get_messages_parses_importance(self, teams_client, mock_graph_client):
        """Test importance level parsing"""
        mock_graph_client.get.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "createdDateTime": "2025-01-15T14:30:00Z",
                    "from": {"user": {"id": "user-123", "displayName": "User"}},
                    "body": {"content": "Urgent!"},
                    "importance": "urgent",
                    "mentions": [],
                    "attachments": [],
                },
            ]
        }

        messages = await teams_client.get_messages("chat-001")

        assert messages[0].importance == TeamsMessageImportance.URGENT

    @pytest.mark.asyncio
    async def test_get_messages_parses_mentions(self, teams_client, mock_graph_client):
        """Test mentions parsing"""
        mock_graph_client.get.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "createdDateTime": "2025-01-15T14:30:00Z",
                    "from": {"user": {"id": "user-123", "displayName": "User"}},
                    "body": {"content": "@alice @bob check this"},
                    "importance": "normal",
                    "mentions": [
                        {"mentioned": {"user": {"id": "alice-id"}}},
                        {"mentioned": {"user": {"id": "bob-id"}}},
                    ],
                    "attachments": [],
                },
            ]
        }

        messages = await teams_client.get_messages("chat-001")

        assert "alice-id" in messages[0].mentions
        assert "bob-id" in messages[0].mentions

    @pytest.mark.asyncio
    async def test_get_messages_parses_attachments(self, teams_client, mock_graph_client):
        """Test attachments parsing"""
        mock_graph_client.get.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "createdDateTime": "2025-01-15T14:30:00Z",
                    "from": {"user": {"id": "user-123", "displayName": "User"}},
                    "body": {"content": "See attached"},
                    "importance": "normal",
                    "mentions": [],
                    "attachments": [
                        {"name": "report.pdf"},
                        {"name": "data.xlsx"},
                    ],
                },
            ]
        }

        messages = await teams_client.get_messages("chat-001")

        assert "report.pdf" in messages[0].attachments
        assert "data.xlsx" in messages[0].attachments


class TestGetRecentMessages(TestTeamsClient):
    """Tests for get_recent_messages method"""

    @pytest.mark.asyncio
    async def test_get_recent_messages_from_all_chats(self, teams_client, mock_graph_client):
        """Test getting recent messages from all chats"""
        # Mock get_chats
        mock_graph_client.get_all_pages.return_value = [
            {
                "id": "chat-001",
                "chatType": "oneOnOne",
                "createdDateTime": "2025-01-01T00:00:00Z",
            },
            {
                "id": "chat-002",
                "chatType": "group",
                "topic": "Group Chat",
                "createdDateTime": "2025-01-01T00:00:00Z",
            },
        ]

        # Mock get_messages for each chat
        def mock_get(endpoint, params=None):
            if "chat-001" in endpoint:
                return {
                    "value": [
                        {
                            "id": "msg-from-chat-1",
                            "createdDateTime": "2025-01-15T14:30:00Z",
                            "from": {"user": {"id": "user-1", "displayName": "User 1"}},
                            "body": {"content": "From chat 1"},
                            "importance": "normal",
                            "mentions": [],
                            "attachments": [],
                        }
                    ]
                }
            else:
                return {
                    "value": [
                        {
                            "id": "msg-from-chat-2",
                            "createdDateTime": "2025-01-15T15:00:00Z",
                            "from": {"user": {"id": "user-2", "displayName": "User 2"}},
                            "body": {"content": "From chat 2"},
                            "importance": "normal",
                            "mentions": [],
                            "attachments": [],
                        }
                    ]
                }

        mock_graph_client.get.side_effect = mock_get

        messages = await teams_client.get_recent_messages(limit_per_chat=5)

        # Should have messages from both chats
        assert len(messages) == 2
        # Should be sorted by created_at descending
        assert messages[0].message_id == "msg-from-chat-2"  # More recent

    @pytest.mark.asyncio
    async def test_get_recent_messages_includes_chat_context(
        self, teams_client, mock_graph_client
    ):
        """Test that messages include chat context"""
        mock_graph_client.get_all_pages.return_value = [
            {
                "id": "chat-001",
                "chatType": "group",
                "topic": "Project Chat",
                "createdDateTime": "2025-01-01T00:00:00Z",
            }
        ]

        mock_graph_client.get.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "createdDateTime": "2025-01-15T14:30:00Z",
                    "from": {"user": {"id": "user-1", "displayName": "User"}},
                    "body": {"content": "Test"},
                    "importance": "normal",
                    "mentions": [],
                    "attachments": [],
                }
            ]
        }

        messages = await teams_client.get_recent_messages(
            limit_per_chat=5, include_chat_context=True
        )

        assert len(messages) == 1
        assert messages[0].chat is not None
        assert messages[0].chat.topic == "Project Chat"


class TestSendMessage(TestTeamsClient):
    """Tests for send_message method"""

    @pytest.mark.asyncio
    async def test_send_message_success(self, teams_client, mock_graph_client):
        """Test sending a message"""
        mock_graph_client.post.return_value = {
            "id": "sent-msg-001",
            "createdDateTime": "2025-01-15T16:00:00Z",
            "from": {"user": {"id": "me", "displayName": "Me"}},
            "body": {"content": "Hello from test"},
            "importance": "normal",
            "mentions": [],
            "attachments": [],
        }

        message = await teams_client.send_message("chat-001", "Hello from test")

        assert message.message_id == "sent-msg-001"
        mock_graph_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_calls_correct_endpoint(self, teams_client, mock_graph_client):
        """Test correct endpoint is called for sending"""
        mock_graph_client.post.return_value = {
            "id": "msg-001",
            "createdDateTime": "2025-01-15T16:00:00Z",
            "from": {"user": {"id": "me", "displayName": "Me"}},
            "body": {"content": "Test"},
            "importance": "normal",
            "mentions": [],
            "attachments": [],
        }

        await teams_client.send_message("chat-xyz", "Test content")

        call_args = mock_graph_client.post.call_args
        assert "/me/chats/chat-xyz/messages" in call_args[0][0]


class TestReplyToMessage(TestTeamsClient):
    """Tests for reply_to_message method"""

    @pytest.mark.asyncio
    async def test_reply_to_message(self, teams_client, mock_graph_client):
        """Test replying to a message"""
        mock_graph_client.post.return_value = {
            "id": "reply-001",
            "createdDateTime": "2025-01-15T16:30:00Z",
            "from": {"user": {"id": "me", "displayName": "Me"}},
            "body": {"content": "Thanks!"},
            "importance": "normal",
            "mentions": [],
            "attachments": [],
        }

        reply = await teams_client.reply_to_message(
            "chat-001", "original-msg-001", "Thanks!"
        )

        assert reply.message_id == "reply-001"


class TestGetMessage(TestTeamsClient):
    """Tests for get_message method"""

    @pytest.mark.asyncio
    async def test_get_single_message(self, teams_client, mock_graph_client):
        """Test getting a single message by ID"""
        mock_graph_client.get.return_value = {
            "id": "msg-specific",
            "createdDateTime": "2025-01-15T14:30:00Z",
            "from": {"user": {"id": "user-123", "displayName": "John"}},
            "body": {"content": "Specific message content"},
            "importance": "high",
            "mentions": [],
            "attachments": [],
        }

        message = await teams_client.get_message("chat-001", "msg-specific")

        assert message.message_id == "msg-specific"
        assert message.importance == TeamsMessageImportance.HIGH
        mock_graph_client.get.assert_called_once_with(
            "/me/chats/chat-001/messages/msg-specific"
        )


class TestParseHelpers(TestTeamsClient):
    """Tests for parsing helper methods"""

    @pytest.mark.asyncio
    async def test_handles_missing_user_data(self, teams_client, mock_graph_client):
        """Test handling of messages with missing user data"""
        mock_graph_client.get.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "createdDateTime": "2025-01-15T14:30:00Z",
                    "from": {},  # Missing user data
                    "body": {"content": "Test"},
                    "importance": "normal",
                    "mentions": [],
                    "attachments": [],
                },
            ]
        }

        messages = await teams_client.get_messages("chat-001")

        assert len(messages) == 1
        assert messages[0].sender.user_id == "unknown"
        assert messages[0].sender.display_name == "Unknown"

    @pytest.mark.asyncio
    async def test_handles_missing_body(self, teams_client, mock_graph_client):
        """Test handling of messages with missing body"""
        mock_graph_client.get.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "createdDateTime": "2025-01-15T14:30:00Z",
                    "from": {"user": {"id": "user-1", "displayName": "User"}},
                    "body": None,  # Missing body
                    "importance": "normal",
                    "mentions": [],
                    "attachments": [],
                },
            ]
        }

        messages = await teams_client.get_messages("chat-001")

        assert len(messages) == 1
        assert messages[0].content == ""
        assert messages[0].content_plain == ""
