"""
Microsoft Teams Client

High-level client for Teams operations using Microsoft Graph API.

Provides methods for:
- Listing chats and messages
- Sending messages
- Marking messages as read
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.integrations.microsoft.graph_client import GraphClient
from src.integrations.microsoft.models import TeamsChat, TeamsMessage
from src.monitoring.logger import get_logger

logger = get_logger("integrations.microsoft.teams_client")


@dataclass
class TeamsClient:
    """
    Microsoft Teams Client

    Provides high-level operations for Teams messaging.

    Usage:
        auth = MicrosoftAuthenticator(config, cache_dir)
        graph = GraphClient(auth)
        client = TeamsClient(graph)

        chats = await client.get_chats()
        messages = await client.get_messages(chats[0].chat_id)
    """

    graph: GraphClient

    async def get_chats(self) -> list[TeamsChat]:
        """
        Get all chats for the current user

        Returns:
            List of TeamsChat objects
        """
        logger.debug("Fetching chats")

        data = await self.graph.get_all_pages("/me/chats")
        chats = [TeamsChat.from_api(chat_data) for chat_data in data]

        logger.info(f"Found {len(chats)} chats")
        return chats

    async def get_chat(self, chat_id: str) -> TeamsChat:
        """
        Get a specific chat by ID

        Args:
            chat_id: Chat identifier

        Returns:
            TeamsChat object
        """
        logger.debug(f"Fetching chat {chat_id}")

        data = await self.graph.get(f"/me/chats/{chat_id}")
        return TeamsChat.from_api(data)

    async def get_messages(
        self,
        chat_id: str,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> list[TeamsMessage]:
        """
        Get messages from a specific chat

        Args:
            chat_id: Chat identifier
            limit: Maximum number of messages to fetch
            since: Only fetch messages after this datetime

        Returns:
            List of TeamsMessage objects (newest first)
        """
        logger.debug(f"Fetching messages from chat {chat_id}")

        params: dict[str, str] = {
            "$top": str(limit),
            "$orderby": "createdDateTime desc",
        }

        if since:
            # Use OData filter for datetime
            since_str = since.isoformat()
            params["$filter"] = f"createdDateTime gt {since_str}"

        data = await self.graph.get(f"/me/chats/{chat_id}/messages", params=params)

        messages = [
            TeamsMessage.from_api(msg_data, chat_id)
            for msg_data in data.get("value", [])
        ]

        logger.debug(f"Found {len(messages)} messages in chat {chat_id}")
        return messages

    async def get_recent_messages(
        self,
        limit_per_chat: int = 10,
        since: Optional[datetime] = None,
        include_chat_context: bool = True,
    ) -> list[TeamsMessage]:
        """
        Get recent messages from all chats

        Args:
            limit_per_chat: Maximum messages per chat
            since: Only fetch messages after this datetime
            include_chat_context: Attach chat context to each message

        Returns:
            List of TeamsMessage objects sorted by date (newest first)
        """
        logger.info("Fetching recent messages from all chats")

        all_messages: list[TeamsMessage] = []
        chats = await self.get_chats()

        for chat in chats:
            try:
                messages = await self.get_messages(
                    chat.chat_id,
                    limit=limit_per_chat,
                    since=since,
                )

                # Attach chat context if requested
                if include_chat_context:
                    messages = [msg.with_chat(chat) for msg in messages]

                all_messages.extend(messages)

            except Exception as e:
                logger.warning(f"Failed to fetch messages from chat {chat.chat_id}: {e}")
                continue

        # Sort all messages by date (newest first)
        all_messages.sort(key=lambda m: m.created_at, reverse=True)

        logger.info(f"Found {len(all_messages)} messages across {len(chats)} chats")
        return all_messages

    async def send_message(
        self,
        chat_id: str,
        content: str,
    ) -> TeamsMessage:
        """
        Send a message to a chat

        Args:
            chat_id: Chat identifier
            content: Message content (HTML supported)

        Returns:
            The sent TeamsMessage
        """
        logger.info(f"Sending message to chat {chat_id}")

        data = await self.graph.post(
            f"/me/chats/{chat_id}/messages",
            json_data={
                "body": {
                    "content": content,
                    "contentType": "html",
                }
            },
        )

        message = TeamsMessage.from_api(data, chat_id)
        logger.debug(f"Sent message {message.message_id}")
        return message

    async def reply_to_message(
        self,
        chat_id: str,
        message_id: str,
        content: str,
    ) -> TeamsMessage:
        """
        Reply to a specific message

        Note: Teams doesn't have true threading in chats. This sends
        a new message that references the original.

        Args:
            chat_id: Chat identifier
            message_id: Message to reply to
            content: Reply content

        Returns:
            The sent TeamsMessage
        """
        logger.info(f"Replying to message {message_id} in chat {chat_id}")

        # For Teams chats, we send a regular message
        # The client can show it as a reply based on context
        # For channels, we would use replyToId
        return await self.send_message(chat_id, content)

    async def get_message(
        self,
        chat_id: str,
        message_id: str,
    ) -> TeamsMessage:
        """
        Get a specific message by ID

        Args:
            chat_id: Chat identifier
            message_id: Message identifier

        Returns:
            TeamsMessage object
        """
        logger.debug(f"Fetching message {message_id} from chat {chat_id}")

        data = await self.graph.get(f"/me/chats/{chat_id}/messages/{message_id}")
        return TeamsMessage.from_api(data, chat_id)

    async def get_user_profile(self) -> dict:
        """
        Get the current user's profile

        Returns:
            User profile data
        """
        return await self.graph.get("/me")

    async def get_presence(self, user_id: Optional[str] = None) -> dict:
        """
        Get user presence (availability)

        Args:
            user_id: User ID (default: current user)

        Returns:
            Presence data (availability, activity)
        """
        if user_id:
            return await self.graph.get(f"/users/{user_id}/presence")
        return await self.graph.get("/me/presence")
