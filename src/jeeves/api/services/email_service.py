"""
Email Service

Async service wrapper for email processing operations.
"""

from typing import Any

from src.core.config_manager import get_config
from src.core.state_manager import get_state_manager
from src.monitoring.logger import get_logger

logger = get_logger("api.email_service")


class EmailService:
    """Async service for email operations"""

    def __init__(self) -> None:
        """Initialize email service"""
        self._config = get_config()
        self._state = get_state_manager()

    async def get_accounts(self) -> list[dict[str, Any]]:
        """
        Get configured email accounts

        Returns:
            List of account info dicts
        """
        accounts = []
        for account in self._config.email.get_enabled_accounts():
            accounts.append({
                "name": account.account_id,
                "email": account.imap_username,
                "enabled": account.enabled,
                "inbox_folder": account.inbox_folder or "INBOX",
            })
        return accounts

    async def get_stats(self) -> dict[str, Any]:
        """
        Get email processing statistics

        Returns:
            Dictionary with processing stats
        """
        return {
            "emails_processed": self._state.get("emails_processed", 0),
            "emails_auto_executed": self._state.get("emails_auto_executed", 0),
            "emails_archived": self._state.get("emails_archived", 0),
            "emails_deleted": self._state.get("emails_deleted", 0),
            "emails_queued": self._state.get("emails_queued", 0),
            "emails_skipped": self._state.get("emails_skipped", 0),
            "tasks_created": self._state.get("tasks_created", 0),
            "average_confidence": self._safe_get_average_confidence(),
            "processing_mode": self._state.get("processing_mode", "unknown"),
        }

    def _safe_get_average_confidence(self) -> float:
        """Get average confidence safely"""
        try:
            if hasattr(self._state, "get_average_confidence"):
                return self._state.get_average_confidence()
            return self._state.stats.confidence_avg if hasattr(self._state, "stats") else 0.0
        except Exception:
            return 0.0

    async def process_inbox(
        self,
        limit: int | None = None,
        auto_execute: bool = False,
        confidence_threshold: int | None = None,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        """
        Process inbox emails

        This runs the full email processing pipeline.

        Args:
            limit: Maximum emails to process
            auto_execute: Whether to auto-execute high confidence actions
            confidence_threshold: Minimum confidence for auto-execution
            unread_only: Only process unread emails

        Returns:
            Processing result dictionary
        """
        # Lazy import to avoid circular imports and heavy initialization
        from src.trivelin.processor import EmailProcessor

        processor = EmailProcessor()

        # Build kwargs, omitting None values to use processor defaults
        kwargs: dict[str, Any] = {
            "auto_execute": auto_execute,
            "unread_only": unread_only,
        }
        if limit is not None:
            kwargs["limit"] = limit
        if confidence_threshold is not None:
            kwargs["confidence_threshold"] = confidence_threshold

        results = processor.process_inbox(**kwargs)

        return {
            "total_processed": len(results),
            "auto_executed": self._state.get("emails_auto_executed", 0),
            "queued": self._state.get("emails_queued", 0),
            "skipped": self._state.get("emails_skipped", 0),
            "emails": [
                {
                    "metadata": {
                        "id": r.metadata.id,
                        "subject": r.metadata.subject,
                        "from_address": r.metadata.from_address,
                        "from_name": r.metadata.from_name,
                        "date": r.metadata.date.isoformat() if r.metadata.date else None,
                        "has_attachments": r.metadata.has_attachments,
                        "folder": r.metadata.folder,
                    },
                    "analysis": {
                        "action": r.analysis.action.value,
                        "confidence": r.analysis.confidence,
                        "category": r.analysis.category.value if r.analysis.category else None,
                        "reasoning": r.analysis.reasoning,
                        "destination": r.analysis.destination,
                    },
                    "processed_at": r.processed_at.isoformat(),
                    "executed": r.analysis.confidence >= (confidence_threshold or 90)
                    and auto_execute,
                }
                for r in results
            ],
        }

    async def analyze_email(
        self,
        email_id: str,
        folder: str = "INBOX",
    ) -> dict[str, Any] | None:
        """
        Analyze a single email

        Args:
            email_id: Email ID to analyze
            folder: Folder containing the email

        Returns:
            Analysis result or None if email not found
        """
        # Lazy import
        from src.integrations.email.imap_client import IMAPClient
        from src.sancho.router import AIModel, get_ai_router

        imap_client = IMAPClient(self._config.email)
        ai_router = get_ai_router(self._config.ai)

        try:
            with imap_client.connect():
                # Fetch the specific email
                emails = imap_client.fetch_emails(
                    folder=folder,
                    limit=1,
                )

                # Find the email by ID
                for metadata, content in emails:
                    if str(metadata.id) == email_id:
                        analysis = ai_router.analyze_email(
                            metadata, content, model=AIModel.CLAUDE_HAIKU
                        )

                        if analysis:
                            return {
                                "metadata": {
                                    "id": metadata.id,
                                    "subject": metadata.subject,
                                    "from_address": metadata.from_address,
                                    "from_name": metadata.from_name,
                                    "date": metadata.date.isoformat() if metadata.date else None,
                                    "has_attachments": metadata.has_attachments,
                                    "folder": metadata.folder,
                                },
                                "analysis": {
                                    "action": analysis.action.value,
                                    "confidence": analysis.confidence,
                                    "category": analysis.category.value
                                    if analysis.category
                                    else None,
                                    "reasoning": analysis.reasoning,
                                    "destination": analysis.destination,
                                },
                            }
                return None
        except Exception as e:
            logger.error(f"Failed to analyze email {email_id}: {e}")
            return None

    async def execute_action(
        self,
        email_id: str,
        action: str,
        destination: str | None = None,
    ) -> bool:
        """
        Execute an action on an email

        Args:
            email_id: Email ID
            action: Action to execute (archive, delete, task)
            destination: Destination folder for archive action

        Returns:
            True if action executed successfully
        """
        # Lazy import
        from src.integrations.email.imap_client import IMAPClient

        imap_client = IMAPClient(self._config.email)

        try:
            with imap_client.connect():
                if action == "archive":
                    dest = destination or self._config.email.archive_folder
                    return imap_client.move_email(
                        msg_id=email_id,
                        from_folder="INBOX",
                        to_folder=dest,
                    )
                elif action == "delete":
                    dest = destination or self._config.email.delete_folder or "Trash"
                    return imap_client.move_email(
                        msg_id=email_id,
                        from_folder="INBOX",
                        to_folder=dest,
                    )
                elif action == "task":
                    # Task creation is not yet implemented
                    logger.info(f"Task creation requested for email {email_id}")
                    return False
                else:
                    logger.warning(f"Unknown action: {action}")
                    return False
        except Exception as e:
            logger.error(f"Failed to execute action {action} on email {email_id}: {e}")
            return False
