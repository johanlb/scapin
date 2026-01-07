"""
Draft Storage System

JSON-based storage for email reply drafts.

Stores AI-generated draft replies for user review and editing
before sending.

Architecture:
    - Each draft is a separate JSON file
    - Filename: {draft_id}.json
    - Directory: data/drafts/
    - Thread-safe file operations

Usage:
    from src.integrations.storage.draft_storage import DraftStorage, DraftReply

    storage = DraftStorage()

    # Create a draft
    draft = storage.create_draft(
        email_id=123,
        account_email="user@example.com",
        subject="Re: Your question",
        body="Thank you for reaching out..."
    )

    # Get draft by ID
    draft = storage.get_draft(draft_id)

    # Update draft
    storage.update_draft(draft_id, body="Updated content...")

    # Mark as sent or discarded
    storage.mark_sent(draft_id)
    storage.discard_draft(draft_id)
"""

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("draft_storage")


class DraftStatus(str, Enum):
    """Status of an email draft"""

    DRAFT = "draft"  # In progress, not yet sent
    SENT = "sent"  # Successfully sent
    DISCARDED = "discarded"  # User chose not to send
    FAILED = "failed"  # Send attempt failed


class ReplyFormat(str, Enum):
    """Format of the reply content"""

    PLAIN_TEXT = "plain_text"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class DraftReply:
    """
    Email reply draft

    Stores all data needed to compose and send an email reply.
    """

    draft_id: str
    email_id: int  # Original email IMAP UID
    account_email: str  # Account used for reply
    message_id: Optional[str] = None  # Original email Message-ID

    # Reply headers
    subject: str = ""
    to_addresses: list[str] = field(default_factory=list)
    cc_addresses: list[str] = field(default_factory=list)
    bcc_addresses: list[str] = field(default_factory=list)

    # Reply content
    body: str = ""
    body_format: ReplyFormat = ReplyFormat.PLAIN_TEXT
    signature: Optional[str] = None

    # AI generation metadata
    ai_generated: bool = True
    ai_confidence: float = 0.0
    ai_reasoning: str = ""
    ai_model: Optional[str] = None
    generation_prompt: Optional[str] = None

    # Context from original email
    original_subject: str = ""
    original_from: str = ""
    original_date: Optional[datetime] = None
    original_preview: str = ""
    thread_context: list[dict[str, Any]] = field(default_factory=list)

    # Status tracking
    status: DraftStatus = DraftStatus.DRAFT
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    sent_at: Optional[datetime] = None
    discarded_at: Optional[datetime] = None

    # User modifications
    user_edited: bool = False
    edit_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage"""
        return {
            "draft_id": self.draft_id,
            "email_id": self.email_id,
            "account_email": self.account_email,
            "message_id": self.message_id,
            "subject": self.subject,
            "to_addresses": self.to_addresses,
            "cc_addresses": self.cc_addresses,
            "bcc_addresses": self.bcc_addresses,
            "body": self.body,
            "body_format": self.body_format.value,
            "signature": self.signature,
            "ai_generated": self.ai_generated,
            "ai_confidence": self.ai_confidence,
            "ai_reasoning": self.ai_reasoning,
            "ai_model": self.ai_model,
            "generation_prompt": self.generation_prompt,
            "original_subject": self.original_subject,
            "original_from": self.original_from,
            "original_date": self.original_date.isoformat() if self.original_date else None,
            "original_preview": self.original_preview,
            "thread_context": self.thread_context,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "discarded_at": self.discarded_at.isoformat() if self.discarded_at else None,
            "user_edited": self.user_edited,
            "edit_history": self.edit_history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DraftReply":
        """Deserialize from dictionary"""
        return cls(
            draft_id=data["draft_id"],
            email_id=data["email_id"],
            account_email=data["account_email"],
            message_id=data.get("message_id"),
            subject=data.get("subject", ""),
            to_addresses=data.get("to_addresses", []),
            cc_addresses=data.get("cc_addresses", []),
            bcc_addresses=data.get("bcc_addresses", []),
            body=data.get("body", ""),
            body_format=ReplyFormat(data.get("body_format", "plain_text")),
            signature=data.get("signature"),
            ai_generated=data.get("ai_generated", True),
            ai_confidence=data.get("ai_confidence", 0.0),
            ai_reasoning=data.get("ai_reasoning", ""),
            ai_model=data.get("ai_model"),
            generation_prompt=data.get("generation_prompt"),
            original_subject=data.get("original_subject", ""),
            original_from=data.get("original_from", ""),
            original_date=(
                datetime.fromisoformat(data["original_date"])
                if data.get("original_date")
                else None
            ),
            original_preview=data.get("original_preview", ""),
            thread_context=data.get("thread_context", []),
            status=DraftStatus(data.get("status", "draft")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            sent_at=(
                datetime.fromisoformat(data["sent_at"]) if data.get("sent_at") else None
            ),
            discarded_at=(
                datetime.fromisoformat(data["discarded_at"])
                if data.get("discarded_at")
                else None
            ),
            user_edited=data.get("user_edited", False),
            edit_history=data.get("edit_history", []),
        )


class DraftStorage:
    """
    JSON-based storage for email drafts

    Stores AI-generated reply drafts for review before sending.
    """

    def __init__(self, drafts_dir: Optional[Path] = None):
        """
        Initialize draft storage

        Args:
            drafts_dir: Directory for draft files (default: data/drafts)
        """
        self.drafts_dir = Path(drafts_dir) if drafts_dir else Path("data/drafts")
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        logger.info("DraftStorage initialized", extra={"drafts_dir": str(self.drafts_dir)})

    def create_draft(
        self,
        email_id: int,
        account_email: str,
        subject: str,
        body: str,
        to_addresses: Optional[list[str]] = None,
        cc_addresses: Optional[list[str]] = None,
        message_id: Optional[str] = None,
        body_format: ReplyFormat = ReplyFormat.PLAIN_TEXT,
        ai_confidence: float = 0.0,
        ai_reasoning: str = "",
        ai_model: Optional[str] = None,
        original_subject: str = "",
        original_from: str = "",
        original_date: Optional[datetime] = None,
        original_preview: str = "",
        thread_context: Optional[list[dict[str, Any]]] = None,
    ) -> DraftReply:
        """
        Create a new draft reply

        Args:
            email_id: IMAP UID of original email
            account_email: Account email address
            subject: Reply subject line
            body: Reply body content
            to_addresses: Recipients (defaults to original sender)
            cc_addresses: CC recipients
            message_id: Original email Message-ID
            body_format: Format of body content
            ai_confidence: AI confidence score
            ai_reasoning: AI explanation
            ai_model: Model used for generation
            original_subject: Original email subject
            original_from: Original sender
            original_date: Original email date
            original_preview: Preview of original content
            thread_context: Previous messages in thread

        Returns:
            DraftReply: Created draft
        """
        draft_id = str(uuid.uuid4())

        draft = DraftReply(
            draft_id=draft_id,
            email_id=email_id,
            account_email=account_email,
            message_id=message_id,
            subject=subject,
            to_addresses=to_addresses or [],
            cc_addresses=cc_addresses or [],
            body=body,
            body_format=body_format,
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            ai_model=ai_model,
            original_subject=original_subject,
            original_from=original_from,
            original_date=original_date,
            original_preview=original_preview,
            thread_context=thread_context or [],
        )

        self._save_draft(draft)

        logger.info(
            "Draft created",
            extra={
                "draft_id": draft_id,
                "email_id": email_id,
                "subject": subject,
            },
        )

        return draft

    def _save_draft(self, draft: DraftReply) -> None:
        """Save draft to file (internal)"""
        file_path = self.drafts_dir / f"{draft.draft_id}.json"

        with self._lock, open(file_path, "w", encoding="utf-8") as f:
            json.dump(draft.to_dict(), f, indent=2, ensure_ascii=False)

    def get_draft(self, draft_id: str) -> Optional[DraftReply]:
        """
        Get a draft by ID

        Args:
            draft_id: Draft identifier

        Returns:
            DraftReply or None if not found
        """
        file_path = self.drafts_dir / f"{draft_id}.json"

        if not file_path.exists():
            return None

        try:
            with self._lock, open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return DraftReply.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load draft {draft_id}: {e}")
            return None

    def get_drafts_for_email(self, email_id: int) -> list[DraftReply]:
        """
        Get all drafts for a specific email

        Args:
            email_id: Original email IMAP UID

        Returns:
            List of drafts for the email
        """
        drafts = []

        with self._lock:
            for file_path in self.drafts_dir.glob("*.json"):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)

                    if data.get("email_id") == email_id:
                        drafts.append(DraftReply.from_dict(data))

                except Exception as e:
                    logger.warning(f"Failed to load draft {file_path.name}: {e}")

        # Sort by created_at, newest first
        drafts.sort(key=lambda d: d.created_at, reverse=True)
        return drafts

    def get_all_drafts(
        self,
        status: Optional[DraftStatus] = None,
        account_email: Optional[str] = None,
    ) -> list[DraftReply]:
        """
        Get all drafts with optional filtering

        Args:
            status: Filter by status
            account_email: Filter by account

        Returns:
            List of drafts
        """
        drafts = []

        with self._lock:
            for file_path in self.drafts_dir.glob("*.json"):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)

                    # Apply filters
                    if status and data.get("status") != status.value:
                        continue

                    if account_email and data.get("account_email") != account_email:
                        continue

                    drafts.append(DraftReply.from_dict(data))

                except Exception as e:
                    logger.warning(f"Failed to load draft {file_path.name}: {e}")

        # Sort by updated_at, newest first
        drafts.sort(key=lambda d: d.updated_at, reverse=True)
        return drafts

    def get_pending_drafts(self) -> list[DraftReply]:
        """
        Get all drafts that are still pending (not sent or discarded)

        Returns:
            List of pending drafts
        """
        return self.get_all_drafts(status=DraftStatus.DRAFT)

    def update_draft(
        self,
        draft_id: str,
        body: Optional[str] = None,
        subject: Optional[str] = None,
        to_addresses: Optional[list[str]] = None,
        cc_addresses: Optional[list[str]] = None,
        bcc_addresses: Optional[list[str]] = None,
    ) -> Optional[DraftReply]:
        """
        Update a draft's content

        Args:
            draft_id: Draft identifier
            body: New body content (optional)
            subject: New subject (optional)
            to_addresses: New recipients (optional)
            cc_addresses: New CC recipients (optional)
            bcc_addresses: New BCC recipients (optional)

        Returns:
            Updated DraftReply or None if not found
        """
        draft = self.get_draft(draft_id)

        if not draft:
            return None

        if draft.status != DraftStatus.DRAFT:
            logger.warning(f"Cannot update draft {draft_id}: status is {draft.status}")
            return None

        # Track edit in history
        edit_record = {
            "timestamp": now_utc().isoformat(),
            "changes": {},
        }

        if body is not None and body != draft.body:
            edit_record["changes"]["body"] = {"old_length": len(draft.body), "new_length": len(body)}
            draft.body = body

        if subject is not None and subject != draft.subject:
            edit_record["changes"]["subject"] = {"old": draft.subject, "new": subject}
            draft.subject = subject

        if to_addresses is not None:
            edit_record["changes"]["to_addresses"] = {"old": draft.to_addresses, "new": to_addresses}
            draft.to_addresses = to_addresses

        if cc_addresses is not None:
            edit_record["changes"]["cc_addresses"] = {"old": draft.cc_addresses, "new": cc_addresses}
            draft.cc_addresses = cc_addresses

        if bcc_addresses is not None:
            edit_record["changes"]["bcc_addresses"] = {"old": draft.bcc_addresses, "new": bcc_addresses}
            draft.bcc_addresses = bcc_addresses

        if edit_record["changes"]:
            draft.user_edited = True
            draft.edit_history.append(edit_record)
            draft.updated_at = now_utc()
            self._save_draft(draft)

            logger.info(
                "Draft updated",
                extra={
                    "draft_id": draft_id,
                    "changes": list(edit_record["changes"].keys()),
                },
            )

        return draft

    def mark_sent(self, draft_id: str) -> Optional[DraftReply]:
        """
        Mark a draft as sent

        Args:
            draft_id: Draft identifier

        Returns:
            Updated DraftReply or None if not found
        """
        draft = self.get_draft(draft_id)

        if not draft:
            return None

        if draft.status != DraftStatus.DRAFT:
            logger.warning(f"Cannot mark draft {draft_id} as sent: status is {draft.status}")
            return None

        draft.status = DraftStatus.SENT
        draft.sent_at = now_utc()
        draft.updated_at = now_utc()
        self._save_draft(draft)

        logger.info("Draft marked as sent", extra={"draft_id": draft_id})
        return draft

    def mark_failed(self, draft_id: str, error_message: str = "") -> Optional[DraftReply]:
        """
        Mark a draft send as failed

        Args:
            draft_id: Draft identifier
            error_message: Error details

        Returns:
            Updated DraftReply or None if not found
        """
        draft = self.get_draft(draft_id)

        if not draft:
            return None

        draft.status = DraftStatus.FAILED
        draft.updated_at = now_utc()
        draft.edit_history.append({
            "timestamp": now_utc().isoformat(),
            "action": "send_failed",
            "error": error_message,
        })
        self._save_draft(draft)

        logger.warning("Draft send failed", extra={"draft_id": draft_id, "error": error_message})
        return draft

    def discard_draft(self, draft_id: str, reason: str = "") -> Optional[DraftReply]:
        """
        Discard a draft (user chose not to send)

        Args:
            draft_id: Draft identifier
            reason: Reason for discarding (optional)

        Returns:
            Updated DraftReply or None if not found
        """
        draft = self.get_draft(draft_id)

        if not draft:
            return None

        if draft.status != DraftStatus.DRAFT:
            logger.warning(f"Cannot discard draft {draft_id}: status is {draft.status}")
            return None

        draft.status = DraftStatus.DISCARDED
        draft.discarded_at = now_utc()
        draft.updated_at = now_utc()

        if reason:
            draft.edit_history.append({
                "timestamp": now_utc().isoformat(),
                "action": "discarded",
                "reason": reason,
            })

        self._save_draft(draft)

        logger.info("Draft discarded", extra={"draft_id": draft_id, "reason": reason})
        return draft

    def delete_draft(self, draft_id: str) -> bool:
        """
        Permanently delete a draft file

        Args:
            draft_id: Draft identifier

        Returns:
            True if deleted successfully
        """
        file_path = self.drafts_dir / f"{draft_id}.json"

        if not file_path.exists():
            return False

        try:
            with self._lock:
                file_path.unlink()

            logger.info("Draft deleted", extra={"draft_id": draft_id})
            return True

        except Exception as e:
            logger.error(f"Failed to delete draft {draft_id}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get draft statistics

        Returns:
            Dictionary with stats
        """
        all_drafts = self.get_all_drafts()

        if not all_drafts:
            return {
                "total": 0,
                "by_status": {},
                "by_account": {},
            }

        by_status: dict[str, int] = {}
        by_account: dict[str, int] = {}
        ai_generated_count = 0
        user_edited_count = 0

        for draft in all_drafts:
            # By status
            status = draft.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # By account
            account = draft.account_email
            by_account[account] = by_account.get(account, 0) + 1

            # AI stats
            if draft.ai_generated:
                ai_generated_count += 1
            if draft.user_edited:
                user_edited_count += 1

        return {
            "total": len(all_drafts),
            "by_status": by_status,
            "by_account": by_account,
            "ai_generated": ai_generated_count,
            "user_edited": user_edited_count,
        }


# Singleton instance
_draft_storage_instance: Optional[DraftStorage] = None
_draft_storage_lock = threading.Lock()


def get_draft_storage(drafts_dir: Optional[Path] = None) -> DraftStorage:
    """
    Get global DraftStorage instance (thread-safe singleton)

    Args:
        drafts_dir: Drafts directory (only used on first call)

    Returns:
        DraftStorage instance
    """
    global _draft_storage_instance

    if _draft_storage_instance is None:
        with _draft_storage_lock:
            # Double-check locking
            if _draft_storage_instance is None:
                _draft_storage_instance = DraftStorage(drafts_dir=drafts_dir)

    return _draft_storage_instance
