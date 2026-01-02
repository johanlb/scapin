"""
Microsoft Teams Models

Dataclasses for Teams messages, chats, and related entities.
All models are frozen (immutable) for thread safety.
"""

import html
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class TeamsChatType(str, Enum):
    """Type of Teams chat"""

    ONE_ON_ONE = "oneOnOne"
    GROUP = "group"
    MEETING = "meeting"


class TeamsMessageImportance(str, Enum):
    """Importance level of a Teams message"""

    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class TeamsSender:
    """
    Sender of a Teams message

    Represents the user who sent a message.
    """

    user_id: str
    display_name: str
    email: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "email": self.email,
        }

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TeamsSender":
        """Create from Graph API response"""
        user_data = data.get("user", {}) if data else {}
        return cls(
            user_id=user_data.get("id", "unknown"),
            display_name=user_data.get("displayName", "Unknown"),
            email=user_data.get("email"),
        )


@dataclass(frozen=True)
class TeamsChat:
    """
    Teams chat/conversation

    Represents a 1:1 chat, group chat, or meeting chat.
    """

    chat_id: str
    chat_type: TeamsChatType
    created_at: datetime
    topic: Optional[str] = None
    members: tuple[TeamsSender, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chat_id": self.chat_id,
            "chat_type": self.chat_type.value,
            "topic": self.topic,
            "members": [m.to_dict() for m in self.members],
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TeamsChat":
        """Create from Graph API response"""
        # Parse chat type
        chat_type_str = data.get("chatType", "oneOnOne")
        try:
            chat_type = TeamsChatType(chat_type_str)
        except ValueError:
            chat_type = TeamsChatType.ONE_ON_ONE

        # Parse created datetime
        created_str = data.get("createdDateTime", "")
        if created_str:
            created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        else:
            created_at = datetime.now(timezone.utc)

        # Parse members
        members_data = data.get("members", [])
        members = tuple(
            TeamsSender(
                user_id=m.get("userId", m.get("id", "unknown")),
                display_name=m.get("displayName", "Unknown"),
                email=m.get("email"),
            )
            for m in members_data
        )

        return cls(
            chat_id=data.get("id", "unknown"),
            chat_type=chat_type,
            topic=data.get("topic"),
            members=members,
            created_at=created_at,
        )


@dataclass(frozen=True)
class TeamsMessage:
    """
    Teams message

    Represents a message in a Teams chat or channel.
    """

    message_id: str
    chat_id: str
    sender: TeamsSender
    content: str  # HTML content from API
    content_plain: str  # Plain text extracted
    created_at: datetime

    # Metadata
    importance: TeamsMessageImportance = TeamsMessageImportance.NORMAL
    mentions: tuple[str, ...] = ()  # User IDs mentioned
    attachments: tuple[str, ...] = ()  # Attachment names
    is_reply: bool = False
    reply_to_id: Optional[str] = None

    # Context (optional, set after fetch)
    chat: Optional[TeamsChat] = None

    def __post_init__(self) -> None:
        """Validate message"""
        if not self.message_id:
            raise ValueError("message_id is required")
        if not self.chat_id:
            raise ValueError("chat_id is required")

    def with_chat(self, chat: TeamsChat) -> "TeamsMessage":
        """Return new message with chat context attached"""
        return replace(self, chat=chat)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "sender": self.sender.to_dict(),
            "content": self.content,
            "content_plain": self.content_plain,
            "created_at": self.created_at.isoformat(),
            "importance": self.importance.value,
            "mentions": list(self.mentions),
            "attachments": list(self.attachments),
            "is_reply": self.is_reply,
            "reply_to_id": self.reply_to_id,
            "chat": self.chat.to_dict() if self.chat else None,
        }

    @classmethod
    def from_api(cls, data: dict[str, Any], chat_id: str) -> "TeamsMessage":
        """
        Create from Graph API response

        Args:
            data: Graph API message response
            chat_id: ID of the chat this message belongs to

        Returns:
            TeamsMessage instance
        """
        # Parse sender
        from_data = data.get("from", {})
        sender = TeamsSender.from_api(from_data)

        # Parse content
        body_data = data.get("body") or {}
        content_html = body_data.get("content", "")
        content_plain = _extract_plain_text(content_html)

        # Parse created datetime
        created_str = data.get("createdDateTime", "")
        if created_str:
            created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        else:
            created_at = datetime.now(timezone.utc)

        # Parse importance
        importance_str = data.get("importance", "normal")
        try:
            importance = TeamsMessageImportance(importance_str)
        except ValueError:
            importance = TeamsMessageImportance.NORMAL

        # Parse mentions
        mentions_data = data.get("mentions", [])
        mentions = tuple(
            m.get("mentioned", {}).get("user", {}).get("id", "")
            for m in mentions_data
            if m.get("mentioned", {}).get("user", {}).get("id")
        )

        # Parse attachments
        attachments_data = data.get("attachments", [])
        attachments = tuple(
            a.get("name", "")
            for a in attachments_data
            if a.get("name")
        )

        # Check if reply
        reply_to_id = data.get("replyToId")
        is_reply = reply_to_id is not None

        return cls(
            message_id=data.get("id", "unknown"),
            chat_id=chat_id,
            sender=sender,
            content=content_html,
            content_plain=content_plain,
            created_at=created_at,
            importance=importance,
            mentions=mentions,
            attachments=attachments,
            is_reply=is_reply,
            reply_to_id=reply_to_id,
        )


def _extract_plain_text(html_content: str) -> str:
    """
    Extract plain text from HTML content

    Teams messages are in HTML format. This extracts readable text.

    Args:
        html_content: HTML string from Teams API

    Returns:
        Plain text content
    """
    if not html_content:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html_content)

    # Decode HTML entities using standard library (handles all entities)
    text = html.unescape(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text
