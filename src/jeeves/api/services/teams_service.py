"""
Teams Service

Async service wrapper for Teams operations.
"""

from datetime import datetime
from typing import Any

from src.core.config_manager import get_config
from src.core.state_manager import get_state_manager
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("api.teams_service")


class TeamsService:
    """Async service for Teams operations"""

    def __init__(self) -> None:
        """Initialize Teams service"""
        self._config = get_config()
        self._state = get_state_manager()
        self._processor = None

    def _get_processor(self) -> Any:
        """Lazy load Teams processor"""
        if self._processor is None:
            from src.trivelin.teams_processor import TeamsProcessor

            self._processor = TeamsProcessor()
        return self._processor

    async def get_chats(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get Teams chats

        Args:
            limit: Maximum chats to return

        Returns:
            List of chat dictionaries
        """
        if not self._config.teams.enabled:
            return []

        processor = self._get_processor()

        try:
            chats = await processor.teams_client.get_chats(limit=limit)
            return [self._chat_to_dict(c) for c in chats]
        except Exception as e:
            logger.error(f"Failed to get Teams chats: {e}")
            return []

    async def get_messages(
        self,
        chat_id: str,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get messages from a chat

        Args:
            chat_id: Chat ID
            limit: Maximum messages to return
            since: Only get messages since this time

        Returns:
            List of message dictionaries
        """
        if not self._config.teams.enabled:
            return []

        processor = self._get_processor()

        try:
            messages = await processor.teams_client.get_messages(
                chat_id=chat_id,
                limit=limit,
                since=since,
            )
            return [self._message_to_dict(m, chat_id) for m in messages]
        except Exception as e:
            logger.error(f"Failed to get messages for chat {chat_id}: {e}")
            return []

    async def send_reply(
        self,
        chat_id: str,
        message_id: str,
        content: str,
    ) -> bool:
        """
        Send a reply to a message

        Args:
            chat_id: Chat ID
            message_id: Message ID to reply to
            content: Reply content

        Returns:
            True if reply was sent successfully
        """
        if not self._config.teams.enabled:
            return False

        processor = self._get_processor()

        try:
            success = await processor.teams_client.send_message(
                chat_id=chat_id,
                content=content,
            )
            return success
        except Exception as e:
            logger.error(f"Failed to send reply to message {message_id}: {e}")
            return False

    async def flag_message(
        self,
        chat_id: str,
        message_id: str,
        flag: bool = True,
        reason: str | None = None,
    ) -> bool:
        """
        Flag/unflag a message

        Args:
            chat_id: Chat ID
            message_id: Message ID
            flag: Flag state
            reason: Optional reason for flagging

        Returns:
            True if operation succeeded
        """
        # Note: Teams Graph API doesn't have native flagging
        # This is tracked in local state
        try:
            flag_key = f"teams_flag_{chat_id}_{message_id}"
            if flag:
                self._state.set(flag_key, {
                    "flagged_at": now_utc().isoformat(),
                    "reason": reason,
                })
                self._state.increment("teams_messages_flagged")
            else:
                self._state.delete(flag_key)

            return True
        except Exception as e:
            logger.error(f"Failed to flag message {message_id}: {e}")
            return False

    async def poll(self) -> dict[str, Any]:
        """
        Poll Teams for new messages

        Returns:
            Poll result summary
        """
        if not self._config.teams.enabled:
            return {
                "messages_fetched": 0,
                "messages_new": 0,
                "chats_checked": 0,
                "polled_at": now_utc().isoformat(),
            }

        processor = self._get_processor()

        try:
            summary = await processor.poll_and_process()
            return {
                "messages_fetched": summary.total,
                "messages_new": summary.successful,
                "chats_checked": len({r.message_id.split("/")[0] for r in summary.results if "/" in r.message_id}),
                "polled_at": now_utc().isoformat(),
            }
        except Exception as e:
            logger.error(f"Teams poll failed: {e}")
            return {
                "messages_fetched": 0,
                "messages_new": 0,
                "chats_checked": 0,
                "polled_at": now_utc().isoformat(),
                "error": str(e),
            }

    async def get_stats(self) -> dict[str, Any]:
        """
        Get Teams statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_chats": self._state.get("teams_total_chats", 0),
            "unread_chats": self._state.get("teams_unread_chats", 0),
            "messages_processed": self._state.get("teams_messages_processed", 0),
            "messages_flagged": self._state.get("teams_messages_flagged", 0),
            "last_poll": self._state.get("teams_last_poll"),
        }

    def _chat_to_dict(self, chat: Any) -> dict[str, Any]:
        """Convert TeamsChat to dictionary"""
        return {
            "id": chat.id,
            "topic": chat.topic,
            "chat_type": chat.chat_type.value if hasattr(chat.chat_type, "value") else str(chat.chat_type),
            "created_at": chat.created_datetime.isoformat() if chat.created_datetime else None,
            "last_message_at": chat.last_updated_datetime.isoformat() if chat.last_updated_datetime else None,
            "member_count": len(chat.members) if chat.members else 0,
            "unread_count": 0,  # Would need additional API call
        }

    def _message_to_dict(self, message: Any, chat_id: str) -> dict[str, Any]:
        """Convert TeamsMessage to dictionary"""
        return {
            "id": message.id,
            "chat_id": chat_id,
            "sender": {
                "id": message.sender.id if message.sender else "",
                "display_name": message.sender.display_name if message.sender else "Unknown",
                "email": message.sender.email if message.sender else None,
            },
            "content": message.body or "",
            "content_preview": message.body_preview or "",
            "created_at": message.created_datetime.isoformat() if message.created_datetime else now_utc().isoformat(),
            "is_read": True,  # Would need read receipts API
            "importance": message.importance.value if hasattr(message, "importance") and hasattr(message.importance, "value") else "normal",
            "has_mentions": bool(message.mentions) if hasattr(message, "mentions") else False,
            "attachments_count": len(message.attachments) if hasattr(message, "attachments") and message.attachments else 0,
        }
