"""
Email Service

Async service wrapper for email processing operations.
"""

import asyncio
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
        unprocessed_only: bool = True,
    ) -> dict[str, Any]:
        """
        Process inbox emails

        This runs the full email processing pipeline.

        Args:
            limit: Maximum emails to process
            auto_execute: Whether to auto-execute high confidence actions
            confidence_threshold: Minimum confidence for auto-execution
            unread_only: Only process unread emails
            unprocessed_only: Only fetch emails not yet processed by Scapin

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
            "unprocessed_only": unprocessed_only,
        }
        if limit is not None:
            kwargs["limit"] = limit
        if confidence_threshold is not None:
            kwargs["confidence_threshold"] = confidence_threshold

        # Run blocking IMAP/processor operations in a thread to not block event loop
        results = await asyncio.to_thread(processor.process_inbox, **kwargs)

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
        # Run blocking IMAP/AI operations in a thread to not block event loop
        return await asyncio.to_thread(
            self._analyze_email_sync, email_id, folder
        )

    def _analyze_email_sync(
        self,
        email_id: str,
        folder: str,
    ) -> dict[str, Any] | None:
        """Synchronous email analysis (runs in thread pool)"""
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
        # Run blocking IMAP operations in a thread to not block event loop
        return await asyncio.to_thread(
            self._execute_action_sync, email_id, action, destination
        )

    def _execute_action_sync(
        self,
        email_id: str,
        action: str,
        destination: str | None,
    ) -> bool:
        """Synchronous action execution (runs in thread pool)"""
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

    async def get_attachment(
        self,
        email_id: int,
        filename: str,
        folder: str = "INBOX",
    ) -> tuple[bytes, str] | None:
        """
        Get an attachment from an email

        Args:
            email_id: Email message ID
            filename: Attachment filename
            folder: IMAP folder

        Returns:
            Tuple of (content bytes, content_type) or None if not found
        """
        return await asyncio.to_thread(
            self._get_attachment_sync, email_id, filename, folder
        )

    def _get_attachment_sync(
        self,
        email_id: int,
        filename: str,
        folder: str,
    ) -> tuple[bytes, str] | None:
        """Synchronous attachment fetch (runs in thread pool)"""
        from src.integrations.email.imap_client import IMAPClient

        imap_client = IMAPClient(self._config.email)

        try:
            with imap_client.connect():
                return imap_client.get_attachment(email_id, filename, folder)
        except Exception as e:
            logger.error(f"Failed to get attachment {filename} from email {email_id}: {e}")
            return None

    # ========================================================================
    # Folder Operations
    # ========================================================================

    async def get_folders(self) -> list[dict[str, Any]]:
        """
        Get list of all IMAP folders

        Returns:
            List of folder info dicts with path, name, delimiter
        """
        return await asyncio.to_thread(self._get_folders_sync)

    def _get_folders_sync(self) -> list[dict[str, Any]]:
        """Synchronous folder list (runs in thread pool)"""
        from src.integrations.email.imap_client import IMAPClient

        imap_client = IMAPClient(self._config.email)

        try:
            with imap_client.connect():
                folders = imap_client.list_folders()
                return [
                    {
                        "path": f.get("path", f.get("name", "")),
                        "name": f.get("name", "").split("/")[-1],
                        "delimiter": f.get("delimiter", "/"),
                        "has_children": f.get("has_children", False),
                        "selectable": f.get("selectable", True),
                    }
                    for f in folders
                ]
        except Exception as e:
            logger.error(f"Failed to list folders: {e}")
            return []

    async def get_folder_tree(self) -> list[dict[str, Any]]:
        """
        Get hierarchical folder tree

        Returns:
            List of folder tree nodes with children
        """
        return await asyncio.to_thread(self._get_folder_tree_sync)

    def _get_folder_tree_sync(self) -> list[dict[str, Any]]:
        """Synchronous folder tree (runs in thread pool)"""
        from src.integrations.email.imap_client import IMAPClient

        imap_client = IMAPClient(self._config.email)

        try:
            with imap_client.connect():
                return imap_client.get_folder_tree()
        except Exception as e:
            logger.error(f"Failed to get folder tree: {e}")
            return []

    async def get_folder_suggestions(
        self,
        sender_email: str | None = None,
        subject: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Get AI-powered folder suggestions

        Based on learned preferences from past archive actions.

        Args:
            sender_email: Sender's email address
            subject: Email subject for keyword matching
            limit: Maximum number of suggestions

        Returns:
            Dict with suggestions, recent_folders, popular_folders
        """
        return await asyncio.to_thread(
            self._get_folder_suggestions_sync, sender_email, subject, limit
        )

    def _get_folder_suggestions_sync(
        self,
        sender_email: str | None,
        subject: str | None,
        limit: int,
    ) -> dict[str, Any]:
        """Synchronous folder suggestions (runs in thread pool)"""
        from src.integrations.email.folder_preferences import get_folder_preferences

        store = get_folder_preferences()

        suggestions = store.get_suggestions(
            sender_email=sender_email,
            subject=subject,
            limit=limit,
        )

        return {
            "suggestions": [
                {
                    "folder": s.folder,
                    "confidence": s.confidence,
                    "reason": s.reason,
                }
                for s in suggestions
            ],
            "recent_folders": store.get_recent_folders(limit=10),
            "popular_folders": store.get_popular_folders(limit=10),
        }

    async def create_folder(self, path: str) -> dict[str, Any]:
        """
        Create a new IMAP folder

        Args:
            path: Folder path to create (supports nested paths)

        Returns:
            Dict with path and created status
        """
        return await asyncio.to_thread(self._create_folder_sync, path)

    def _create_folder_sync(self, path: str) -> dict[str, Any]:
        """Synchronous folder creation (runs in thread pool)"""
        from src.integrations.email.imap_client import IMAPClient

        imap_client = IMAPClient(self._config.email)

        try:
            with imap_client.connect():
                created = imap_client.create_folder(path)
                return {
                    "path": path,
                    "created": created,
                }
        except Exception as e:
            logger.error(f"Failed to create folder {path}: {e}")
            raise

    async def record_archive(
        self,
        folder: str,
        sender_email: str | None = None,
        subject: str | None = None,
    ) -> bool:
        """
        Record an archive action for learning

        This feeds the folder suggestion algorithm.

        Args:
            folder: Destination folder used
            sender_email: Sender's email address
            subject: Email subject

        Returns:
            True if recorded successfully
        """
        return await asyncio.to_thread(
            self._record_archive_sync, folder, sender_email, subject
        )

    def _record_archive_sync(
        self,
        folder: str,
        sender_email: str | None,
        subject: str | None,
    ) -> bool:
        """Synchronous archive recording (runs in thread pool)"""
        from src.integrations.email.folder_preferences import get_folder_preferences

        try:
            store = get_folder_preferences()
            store.record_archive(
                folder=folder,
                sender_email=sender_email,
                subject=subject,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to record archive: {e}")
            return False
