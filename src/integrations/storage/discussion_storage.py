"""
Discussion Storage System

JSON-based storage for conversation threads with Scapin.

Architecture:
    - Each discussion is a separate JSON file
    - Filename: {discussion_id}.json
    - Directory: data/discussions/
    - Messages stored within discussion file
    - Thread-safe file operations

Usage:
    from src.integrations.storage.discussion_storage import DiscussionStorage

    storage = DiscussionStorage()

    # Create a discussion
    discussion_id = storage.create_discussion(title="About project X", ...)

    # Add a message
    message_id = storage.add_message(discussion_id, "user", "Hello!")

    # Load discussions
    discussions = storage.list_discussions()
"""

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("discussion_storage")


@dataclass
class StoredMessage:
    """A message stored in a discussion"""

    id: str
    discussion_id: str
    role: str  # user, assistant, system
    content: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "discussion_id": self.discussion_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoredMessage":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            discussion_id=data["discussion_id"],
            role=data["role"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class StoredDiscussion:
    """A discussion stored on disk"""

    id: str
    title: Optional[str]
    discussion_type: str  # free, note, email, task, event
    attached_to_id: Optional[str]
    attached_to_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: list[StoredMessage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "discussion_type": self.discussion_type,
            "attached_to_id": self.attached_to_id,
            "attached_to_type": self.attached_to_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoredDiscussion":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            title=data.get("title"),
            discussion_type=data.get("discussion_type", "free"),
            attached_to_id=data.get("attached_to_id"),
            attached_to_type=data.get("attached_to_type"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[StoredMessage.from_dict(m) for m in data.get("messages", [])],
            metadata=data.get("metadata", {}),
        )

    @property
    def message_count(self) -> int:
        """Number of messages in the discussion"""
        return len(self.messages)

    @property
    def last_message_preview(self) -> Optional[str]:
        """Preview of the last message"""
        if not self.messages:
            return None
        last = self.messages[-1]
        return last.content[:100] + "..." if len(last.content) > 100 else last.content


class DiscussionStorage:
    """
    JSON-based storage for discussions

    Stores conversation threads with messages and metadata.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize discussion storage

        Args:
            storage_dir: Directory for discussion files (default: data/discussions)
        """
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/discussions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        logger.info(
            "DiscussionStorage initialized", extra={"storage_dir": str(self.storage_dir)}
        )

    def _get_path(self, discussion_id: str) -> Path:
        """Get file path for a discussion"""
        return self.storage_dir / f"{discussion_id}.json"

    def create_discussion(
        self,
        title: Optional[str] = None,
        discussion_type: str = "free",
        attached_to_id: Optional[str] = None,
        attached_to_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredDiscussion:
        """
        Create a new discussion

        Args:
            title: Discussion title
            discussion_type: Type of discussion (free, note, email, task, event)
            attached_to_id: ID of attached object
            attached_to_type: Type of attached object
            metadata: Additional metadata

        Returns:
            Created discussion
        """
        discussion_id = str(uuid.uuid4())
        now = now_utc()

        discussion = StoredDiscussion(
            id=discussion_id,
            title=title,
            discussion_type=discussion_type,
            attached_to_id=attached_to_id,
            attached_to_type=attached_to_type,
            created_at=now,
            updated_at=now,
            messages=[],
            metadata=metadata or {},
        )

        self._save_discussion(discussion)

        logger.info(
            "Discussion created",
            extra={
                "discussion_id": discussion_id,
                "title": title,
                "type": discussion_type,
            },
        )

        return discussion

    def get_discussion(self, discussion_id: str) -> Optional[StoredDiscussion]:
        """
        Get a discussion by ID

        Args:
            discussion_id: Discussion ID

        Returns:
            Discussion or None if not found
        """
        path = self._get_path(discussion_id)

        with self._lock:
            if not path.exists():
                return None

            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                return StoredDiscussion.from_dict(data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to load discussion {discussion_id}: {e}")
                return None

    def list_discussions(
        self,
        discussion_type: Optional[str] = None,
        attached_to_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[StoredDiscussion], int]:
        """
        List discussions with optional filtering

        Args:
            discussion_type: Filter by type
            attached_to_id: Filter by attached object
            limit: Max items to return
            offset: Skip first N items

        Returns:
            Tuple of (discussions, total_count)
        """
        discussions = []

        with self._lock:
            for path in self.storage_dir.glob("*.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    discussion = StoredDiscussion.from_dict(data)

                    # Apply filters
                    if discussion_type and discussion.discussion_type != discussion_type:
                        continue
                    if attached_to_id and discussion.attached_to_id != attached_to_id:
                        continue

                    discussions.append(discussion)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to load discussion from {path}: {e}")
                    continue

        # Sort by updated_at descending (most recent first)
        discussions.sort(key=lambda d: d.updated_at, reverse=True)

        total = len(discussions)
        discussions = discussions[offset : offset + limit]

        return discussions, total

    def add_message(
        self,
        discussion_id: str,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[StoredMessage]:
        """
        Add a message to a discussion

        Args:
            discussion_id: Discussion ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata

        Returns:
            Created message or None if discussion not found
        """
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            logger.warning(f"Discussion not found: {discussion_id}")
            return None

        message_id = str(uuid.uuid4())
        now = now_utc()

        message = StoredMessage(
            id=message_id,
            discussion_id=discussion_id,
            role=role,
            content=content,
            created_at=now,
            metadata=metadata or {},
        )

        discussion.messages.append(message)
        discussion.updated_at = now

        self._save_discussion(discussion)

        logger.debug(
            "Message added",
            extra={
                "discussion_id": discussion_id,
                "message_id": message_id,
                "role": role,
            },
        )

        return message

    def update_discussion(
        self,
        discussion_id: str,
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[StoredDiscussion]:
        """
        Update discussion metadata

        Args:
            discussion_id: Discussion ID
            title: New title (if provided)
            metadata: Metadata to merge (if provided)

        Returns:
            Updated discussion or None if not found
        """
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            return None

        if title is not None:
            discussion.title = title
        if metadata is not None:
            discussion.metadata.update(metadata)

        discussion.updated_at = now_utc()
        self._save_discussion(discussion)

        return discussion

    def delete_discussion(self, discussion_id: str) -> bool:
        """
        Delete a discussion

        Args:
            discussion_id: Discussion ID

        Returns:
            True if deleted, False if not found
        """
        path = self._get_path(discussion_id)

        with self._lock:
            if not path.exists():
                return False

            try:
                path.unlink()
                logger.info("Discussion deleted", extra={"discussion_id": discussion_id})
                return True
            except OSError as e:
                logger.error(f"Failed to delete discussion {discussion_id}: {e}")
                return False

    def _save_discussion(self, discussion: StoredDiscussion) -> None:
        """Save discussion to disk"""
        path = self._get_path(discussion.id)

        with self._lock, open(path, "w", encoding="utf-8") as f:
            json.dump(discussion.to_dict(), f, indent=2, ensure_ascii=False)


# Singleton instance
_storage: Optional[DiscussionStorage] = None
_storage_lock = threading.Lock()


def get_discussion_storage(storage_dir: Optional[Path] = None) -> DiscussionStorage:
    """
    Get singleton instance of DiscussionStorage

    Args:
        storage_dir: Optional custom storage directory

    Returns:
        DiscussionStorage instance
    """
    global _storage

    with _storage_lock:
        if _storage is None:
            _storage = DiscussionStorage(storage_dir)
        return _storage
