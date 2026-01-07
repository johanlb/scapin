"""
Drafts Service

Async service for managing email reply drafts.
"""

from datetime import datetime
from typing import Any

from src.figaro.actions.email import create_email_reply_draft
from src.integrations.storage.draft_storage import (
    DraftReply,
    DraftStatus,
    DraftStorage,
    get_draft_storage,
)
from src.monitoring.logger import get_logger

logger = get_logger("jeeves.api.drafts")


class DraftsService:
    """Service for draft email reply operations"""

    def __init__(self) -> None:
        """Initialize drafts service"""
        self._storage: DraftStorage | None = None

    @property
    def storage(self) -> DraftStorage:
        """Get draft storage instance (lazy initialization)"""
        if self._storage is None:
            self._storage = get_draft_storage()
        return self._storage

    async def list_drafts(
        self,
        *,
        status: str | None = None,
        account_email: str | None = None,
        email_id: int | None = None,
    ) -> list[DraftReply]:
        """
        List drafts with optional filters

        Args:
            status: Filter by status (draft, sent, discarded, failed)
            account_email: Filter by account email
            email_id: Filter by original email ID

        Returns:
            List of matching drafts
        """
        if email_id is not None:
            drafts = self.storage.get_drafts_for_email(email_id)
        else:
            status_filter = DraftStatus(status) if status else None
            drafts = self.storage.get_all_drafts(
                status=status_filter,
                account_email=account_email,
            )

        return drafts

    async def get_draft(self, draft_id: str) -> DraftReply | None:
        """
        Get a single draft by ID

        Args:
            draft_id: Draft ID

        Returns:
            Draft if found, None otherwise
        """
        return self.storage.get_draft(draft_id)

    async def get_pending_drafts(self) -> list[DraftReply]:
        """
        Get all pending (unsent) drafts

        Returns:
            List of pending drafts
        """
        return self.storage.get_pending_drafts()

    async def create_draft(
        self,
        *,
        email_id: int,
        account_email: str,
        subject: str,
        body: str = "",
        to_addresses: list[str] | None = None,
        cc_addresses: list[str] | None = None,
        body_format: str = "plain_text",
        original_subject: str | None = None,
        original_from: str | None = None,
    ) -> DraftReply:
        """
        Create a draft manually

        Args:
            email_id: Original email ID
            account_email: Account email address
            subject: Reply subject
            body: Draft body content
            to_addresses: To recipients
            cc_addresses: CC recipients
            body_format: Body format (plain_text, html, markdown)
            original_subject: Original email subject
            original_from: Original email sender

        Returns:
            Created draft
        """
        from src.integrations.storage.draft_storage import ReplyFormat

        draft = self.storage.create_draft(
            email_id=email_id,
            account_email=account_email,
            subject=subject,
            body=body,
            to_addresses=to_addresses or [],
            cc_addresses=cc_addresses or [],
            body_format=ReplyFormat(body_format),
            original_subject=original_subject or "",
            original_from=original_from or "",
        )

        # Mark as not AI-generated since this is manual creation
        draft.ai_generated = False
        self.storage._save_draft(draft)

        logger.info(f"Created manual draft {draft.draft_id} for email {email_id}")
        return draft

    async def generate_draft(
        self,
        *,
        email_id: int,
        account_email: str,
        original_subject: str,
        original_from: str,
        original_content: str,
        reply_intent: str = "",
        tone: str = "professional",
        language: str = "fr",
        include_original: bool = True,
        original_date: datetime | None = None,
        original_message_id: str | None = None,
    ) -> DraftReply:
        """
        Generate an AI-assisted draft using PrepareEmailReplyAction

        Args:
            email_id: Original email ID
            account_email: Account email address
            original_subject: Original email subject
            original_from: Original email sender
            original_content: Original email content
            reply_intent: Intended reply content
            tone: Tone (professional, casual, formal, friendly)
            language: Language (fr, en)
            include_original: Include quoted original
            original_date: Original email date
            original_message_id: Original message ID

        Returns:
            Generated draft

        Raises:
            ValueError: If generation fails
        """
        action = create_email_reply_draft(
            email_id=email_id,
            account_email=account_email,
            original_subject=original_subject,
            original_from=original_from,
            original_content=original_content,
            reply_intent=reply_intent,
            tone=tone,
            language=language,
            include_original=include_original,
            original_date=original_date,
            original_message_id=original_message_id,
        )

        # Validate the action
        validation = action.validate()
        if not validation.valid:
            raise ValueError(f"Invalid parameters: {', '.join(validation.errors)}")

        # Execute the action
        result = action.execute()

        if not result.success:
            raise ValueError(f"Draft generation failed: {result.error}")

        # Get the created draft
        draft_id = result.output.get("draft_id")
        if not draft_id:
            raise ValueError("Draft generation failed: no draft ID returned")

        draft = self.storage.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found after creation")

        logger.info(f"Generated AI draft {draft_id} for email {email_id}")
        return draft

    async def update_draft(
        self,
        draft_id: str,
        *,
        subject: str | None = None,
        body: str | None = None,
        to_addresses: list[str] | None = None,
        cc_addresses: list[str] | None = None,
        bcc_addresses: list[str] | None = None,
    ) -> DraftReply | None:
        """
        Update a draft

        Args:
            draft_id: Draft ID
            subject: New subject
            body: New body content
            to_addresses: New to recipients
            cc_addresses: New CC recipients
            bcc_addresses: New BCC recipients

        Returns:
            Updated draft if found and updated, None otherwise
        """
        updated = self.storage.update_draft(
            draft_id,
            subject=subject,
            body=body,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            bcc_addresses=bcc_addresses,
        )

        if updated:
            logger.info(f"Updated draft {draft_id}")

        return updated

    async def mark_sent(self, draft_id: str) -> DraftReply | None:
        """
        Mark a draft as sent

        Args:
            draft_id: Draft ID

        Returns:
            Updated draft if found, None otherwise
        """
        draft = self.storage.mark_sent(draft_id)

        if draft:
            logger.info(f"Marked draft {draft_id} as sent")

        return draft

    async def mark_failed(
        self, draft_id: str, error_message: str
    ) -> DraftReply | None:
        """
        Mark a draft as failed

        Args:
            draft_id: Draft ID
            error_message: Error message

        Returns:
            Updated draft if found, None otherwise
        """
        draft = self.storage.mark_failed(draft_id, error_message)

        if draft:
            logger.info(f"Marked draft {draft_id} as failed: {error_message}")

        return draft

    async def discard_draft(
        self, draft_id: str, reason: str | None = None
    ) -> DraftReply | None:
        """
        Discard a draft

        Args:
            draft_id: Draft ID
            reason: Reason for discarding

        Returns:
            Updated draft if found and discarded, None otherwise
        """
        draft = self.storage.discard_draft(draft_id, reason)

        if draft:
            logger.info(f"Discarded draft {draft_id}")

        return draft

    async def delete_draft(self, draft_id: str) -> bool:
        """
        Permanently delete a draft

        Args:
            draft_id: Draft ID

        Returns:
            True if deleted, False if not found
        """
        deleted = self.storage.delete_draft(draft_id)

        if deleted:
            logger.info(f"Deleted draft {draft_id}")

        return deleted

    async def get_stats(self) -> dict[str, Any]:
        """
        Get draft statistics

        Returns:
            Statistics dict with total, by_status, by_account
        """
        return self.storage.get_stats()


def get_drafts_service() -> DraftsService:
    """Get drafts service instance"""
    return DraftsService()
