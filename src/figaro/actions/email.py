"""
Email Actions for Figaro

Concrete implementations of email-related actions.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.core.config_manager import EmailAccountConfig
from src.figaro.actions.base import Action, ActionResult, ValidationResult
from src.integrations.email.imap_client import IMAPClient
from src.integrations.storage.draft_storage import (
    DraftStorage,
    ReplyFormat,
    get_draft_storage,
)
from src.monitoring.logger import get_logger

logger = get_logger("figaro.actions.email")


@dataclass
class ArchiveEmailAction(Action):
    """
    Archive an email by moving it to the Archive folder

    This action is reversible - the original folder is tracked
    and the email can be moved back.
    """

    email_id: int
    account_email: str
    imap_config: EmailAccountConfig
    current_folder: str = "INBOX"
    archive_folder: str = "Archive"

    # State for undo
    _executed: bool = False
    _original_folder: Optional[str] = None

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        return f"archive_email_{self.account_email}_{self.email_id}"

    @property
    def action_type(self) -> str:
        """Action type"""
        return "archive_email"

    def validate(self) -> ValidationResult:
        """
        Validate that:
        1. Email ID is valid
        2. IMAP config is valid
        3. Current folder exists
        4. Archive folder exists (will be created if not)
        """
        errors = []
        warnings = []

        if self.email_id <= 0:
            errors.append(f"Invalid email ID: {self.email_id}")

        if not self.account_email:
            errors.append("Account email is required")

        if not self.imap_config:
            errors.append("IMAP config is required")

        # Try to connect and check folders
        try:
            with IMAPClient(self.imap_config) as client:
                folders = client.list_folders()

                if self.current_folder not in folders:
                    errors.append(f"Current folder not found: {self.current_folder}")

                if self.archive_folder not in folders:
                    warnings.append(f"Archive folder will be created: {self.archive_folder}")

        except Exception as e:
            errors.append(f"IMAP connection failed: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def execute(self) -> ActionResult:
        """
        Execute the archive action

        Moves email from current_folder to archive_folder.
        """
        start_time = time.time()

        try:
            with IMAPClient(self.imap_config) as client:
                # Ensure archive folder exists
                folders = client.list_folders()
                if self.archive_folder not in folders:
                    client.create_folder(self.archive_folder)
                    logger.info(f"Created archive folder: {self.archive_folder}")

                # Move email
                client.select_folder(self.current_folder)
                client.move_email(self.email_id, self.archive_folder)

                # Track state for undo
                self._executed = True
                self._original_folder = self.current_folder

                duration = time.time() - start_time

                logger.info(
                    f"Archived email {self.email_id}",
                    extra={
                        "email_id": self.email_id,
                        "from_folder": self.current_folder,
                        "to_folder": self.archive_folder,
                        "duration": duration
                    }
                )

                return ActionResult(
                    success=True,
                    duration=duration,
                    output={
                        "email_id": self.email_id,
                        "archived_to": self.archive_folder
                    },
                    metadata={"action": self}
                )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Failed to archive email {self.email_id}: {e}",
                exc_info=True
            )

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
                metadata={"action": self}
            )

    def can_undo(self) -> bool:
        """Archive actions are reversible"""
        return self._executed and self._original_folder is not None

    def undo(self) -> bool:
        """
        Undo archive by moving email back to original folder
        """
        if not self.can_undo():
            logger.warning("Cannot undo archive: action not executed or original folder unknown")
            return False

        try:
            with IMAPClient(self.imap_config) as client:
                # Move back to original folder
                client.select_folder(self.archive_folder)
                client.move_email(self.email_id, self._original_folder)

                logger.info(
                    f"Undid archive for email {self.email_id}",
                    extra={
                        "email_id": self.email_id,
                        "from_folder": self.archive_folder,
                        "to_folder": self._original_folder
                    }
                )

                self._executed = False
                return True

        except Exception as e:
            logger.error(
                f"Failed to undo archive for email {self.email_id}: {e}",
                exc_info=True
            )
            return False

    def dependencies(self) -> list[str]:
        """Archive actions have no dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated duration in seconds"""
        return 2.0  # IMAP operations are typically 1-3 seconds


@dataclass
class DeleteEmailAction(Action):
    """
    Delete an email (move to Trash folder)

    This action is reversible if executed recently - emails
    can be moved back from Trash.
    """

    email_id: int
    account_email: str
    imap_config: EmailAccountConfig
    current_folder: str = "INBOX"
    trash_folder: str = "Trash"
    permanent: bool = False  # If True, permanently delete (not reversible)

    # State for undo
    _executed: bool = False
    _original_folder: Optional[str] = None

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        return f"delete_email_{self.account_email}_{self.email_id}"

    @property
    def action_type(self) -> str:
        """Action type"""
        return "delete_email"

    def validate(self) -> ValidationResult:
        """Validate delete action"""
        errors = []
        warnings = []

        if self.email_id <= 0:
            errors.append(f"Invalid email ID: {self.email_id}")

        if not self.account_email:
            errors.append("Account email is required")

        if not self.imap_config:
            errors.append("IMAP config is required")

        if self.permanent:
            warnings.append("Permanent deletion is NOT reversible")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def execute(self) -> ActionResult:
        """Execute delete action"""
        start_time = time.time()

        try:
            with IMAPClient(self.imap_config) as client:
                if self.permanent:
                    # Permanently delete (set Deleted flag and expunge)
                    client.select_folder(self.current_folder)
                    client.delete_email(self.email_id, permanent=True)

                    logger.warning(
                        f"Permanently deleted email {self.email_id}",
                        extra={"email_id": self.email_id, "folder": self.current_folder}
                    )
                else:
                    # Move to Trash (reversible)
                    folders = client.list_folders()
                    if self.trash_folder not in folders:
                        client.create_folder(self.trash_folder)

                    client.select_folder(self.current_folder)
                    client.move_email(self.email_id, self.trash_folder)

                    # Track state for undo
                    self._executed = True
                    self._original_folder = self.current_folder

                    logger.info(
                        f"Moved email {self.email_id} to Trash",
                        extra={
                            "email_id": self.email_id,
                            "from_folder": self.current_folder
                        }
                    )

                duration = time.time() - start_time

                return ActionResult(
                    success=True,
                    duration=duration,
                    output={
                        "email_id": self.email_id,
                        "permanent": self.permanent
                    },
                    metadata={"action": self}
                )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to delete email {self.email_id}: {e}", exc_info=True)

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
                metadata={"action": self}
            )

    def can_undo(self) -> bool:
        """Delete actions are reversible only if not permanent"""
        return not self.permanent and self._executed and self._original_folder is not None

    def undo(self) -> bool:
        """Undo delete by moving email back from Trash"""
        if not self.can_undo():
            logger.warning(f"Cannot undo delete: permanent={self.permanent} or not executed")
            return False

        try:
            with IMAPClient(self.imap_config) as client:
                # Move back from Trash
                client.select_folder(self.trash_folder)
                client.move_email(self.email_id, self._original_folder)

                logger.info(
                    f"Undid delete for email {self.email_id}",
                    extra={
                        "email_id": self.email_id,
                        "from_folder": self.trash_folder,
                        "to_folder": self._original_folder
                    }
                )

                self._executed = False
                return True

        except Exception as e:
            logger.error(f"Failed to undo delete for email {self.email_id}: {e}", exc_info=True)
            return False

    def dependencies(self) -> list[str]:
        """Delete actions have no dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated duration in seconds"""
        return 2.0


@dataclass
class MoveEmailAction(Action):
    """
    Move an email to a specific folder

    Generic move action that can be used for any folder transition.
    """

    email_id: int
    account_email: str
    imap_config: EmailAccountConfig
    source_folder: str
    destination_folder: str

    # State for undo
    _executed: bool = False

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        return f"move_email_{self.account_email}_{self.email_id}_{self.destination_folder}"

    @property
    def action_type(self) -> str:
        """Action type"""
        return "move_email"

    def validate(self) -> ValidationResult:
        """Validate move action"""
        errors = []
        warnings = []

        if self.email_id <= 0:
            errors.append(f"Invalid email ID: {self.email_id}")

        if not self.account_email:
            errors.append("Account email is required")

        if not self.imap_config:
            errors.append("IMAP config is required")

        if not self.source_folder:
            errors.append("Source folder is required")

        if not self.destination_folder:
            errors.append("Destination folder is required")

        if self.source_folder == self.destination_folder:
            errors.append("Source and destination folders are the same")

        # Verify folders exist
        try:
            with IMAPClient(self.imap_config) as client:
                folders = client.list_folders()

                if self.source_folder not in folders:
                    errors.append(f"Source folder not found: {self.source_folder}")

                if self.destination_folder not in folders:
                    warnings.append(f"Destination folder will be created: {self.destination_folder}")

        except Exception as e:
            errors.append(f"IMAP connection failed: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def execute(self) -> ActionResult:
        """Execute move action"""
        start_time = time.time()

        try:
            with IMAPClient(self.imap_config) as client:
                # Ensure destination folder exists
                folders = client.list_folders()
                if self.destination_folder not in folders:
                    client.create_folder(self.destination_folder)
                    logger.info(f"Created folder: {self.destination_folder}")

                # Move email
                client.select_folder(self.source_folder)
                client.move_email(self.email_id, self.destination_folder)

                self._executed = True

                duration = time.time() - start_time

                logger.info(
                    f"Moved email {self.email_id}",
                    extra={
                        "email_id": self.email_id,
                        "from_folder": self.source_folder,
                        "to_folder": self.destination_folder,
                        "duration": duration
                    }
                )

                return ActionResult(
                    success=True,
                    duration=duration,
                    output={
                        "email_id": self.email_id,
                        "from_folder": self.source_folder,
                        "to_folder": self.destination_folder
                    },
                    metadata={"action": self}
                )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to move email {self.email_id}: {e}", exc_info=True)

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
                metadata={"action": self}
            )

    def can_undo(self) -> bool:
        """Move actions are reversible"""
        return self._executed

    def undo(self) -> bool:
        """Undo move by moving email back to source folder"""
        if not self.can_undo():
            logger.warning("Cannot undo move: action not executed")
            return False

        try:
            with IMAPClient(self.imap_config) as client:
                # Move back to source
                client.select_folder(self.destination_folder)
                client.move_email(self.email_id, self.source_folder)

                logger.info(
                    f"Undid move for email {self.email_id}",
                    extra={
                        "email_id": self.email_id,
                        "from_folder": self.destination_folder,
                        "to_folder": self.source_folder
                    }
                )

                self._executed = False
                return True

        except Exception as e:
            logger.error(f"Failed to undo move for email {self.email_id}: {e}", exc_info=True)
            return False

    def dependencies(self) -> list[str]:
        """Move actions have no dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated duration in seconds"""
        return 2.0


@dataclass
class PrepareEmailReplyAction(Action):
    """
    Prepare a draft reply to an email

    Uses AI to generate a contextual reply and stores it in DraftStorage
    for user review before sending.

    This action is reversible - drafts can be discarded.
    """

    email_id: int
    account_email: str
    original_subject: str
    original_from: str
    original_content: str
    reply_intent: str = ""  # User's intent for the reply (optional)
    original_date: Optional[datetime] = None
    original_message_id: Optional[str] = None
    thread_context: list[dict[str, Any]] = field(default_factory=list)

    # AI generation parameters
    tone: str = "professional"  # professional, casual, formal, friendly
    language: str = "fr"  # fr, en
    include_original: bool = True  # Include quoted original in reply
    max_length: int = 500  # Maximum reply length in words

    # Generated draft storage
    _action_id: str = field(default_factory=lambda: f"prepare_reply_{uuid.uuid4().hex[:8]}")
    _draft_storage: Optional[DraftStorage] = None
    _created_draft_id: Optional[str] = None
    _executed: bool = False

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        return self._action_id

    @property
    def action_type(self) -> str:
        """Action type"""
        return "prepare_email_reply"

    @property
    def draft_storage(self) -> DraftStorage:
        """Get draft storage (lazy initialization)"""
        if self._draft_storage is None:
            self._draft_storage = get_draft_storage()
        return self._draft_storage

    def validate(self) -> ValidationResult:
        """Validate prepare reply action parameters"""
        errors = []
        warnings = []

        if self.email_id <= 0:
            errors.append(f"Invalid email ID: {self.email_id}")

        if not self.account_email:
            errors.append("Account email is required")

        if not self.original_subject:
            warnings.append("Original subject is empty")

        if not self.original_from:
            errors.append("Original sender (from) is required")

        if not self.original_content:
            warnings.append("Original content is empty - draft may be generic")

        if self.tone not in ("professional", "casual", "formal", "friendly"):
            warnings.append(f"Unknown tone '{self.tone}', defaulting to professional")

        if self.language not in ("fr", "en"):
            warnings.append(f"Unknown language '{self.language}', defaulting to French")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def execute(self) -> ActionResult:
        """
        Execute the prepare reply action

        Generates an AI draft and stores it in DraftStorage.
        """
        start_time = time.time()

        try:
            # Validate first
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # Generate subject line
            subject = self._generate_reply_subject()

            # Generate reply body
            # Note: In production, this would call the AI router
            # For now, we generate a placeholder that can be edited
            body = self._generate_draft_body()

            # Extract recipient from original_from
            to_addresses = [self.original_from]

            # Create and store the draft
            draft = self.draft_storage.create_draft(
                email_id=self.email_id,
                account_email=self.account_email,
                subject=subject,
                body=body,
                to_addresses=to_addresses,
                message_id=self.original_message_id,
                body_format=ReplyFormat.PLAIN_TEXT,
                ai_confidence=0.7,  # Placeholder confidence
                ai_reasoning=f"Generated {self.tone} reply in {self.language}",
                original_subject=self.original_subject,
                original_from=self.original_from,
                original_date=self.original_date,
                original_preview=self.original_content[:200] if self.original_content else "",
                thread_context=self.thread_context,
            )

            self._created_draft_id = draft.draft_id
            self._executed = True

            duration = time.time() - start_time

            logger.info(
                f"PrepareEmailReplyAction executed: draft={draft.draft_id}",
                extra={
                    "email_id": self.email_id,
                    "draft_id": draft.draft_id,
                    "tone": self.tone,
                    "language": self.language,
                },
            )

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "draft_id": draft.draft_id,
                    "subject": subject,
                    "body_length": len(body),
                    "to_addresses": to_addresses,
                },
                metadata={
                    "email_id": self.email_id,
                    "account_email": self.account_email,
                    "tone": self.tone,
                    "language": self.language,
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"PrepareEmailReplyAction failed: {e}", exc_info=True)

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def _generate_reply_subject(self) -> str:
        """Generate reply subject line"""
        subject = self.original_subject.strip()

        # Add Re: prefix if not already present
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        return subject

    def _generate_draft_body(self) -> str:
        """
        Generate draft reply body

        In production, this would call the AI router.
        For now, generates a template that the user can edit.
        """
        # Greeting based on tone and language
        greetings = {
            ("professional", "fr"): "Bonjour,",
            ("professional", "en"): "Hello,",
            ("formal", "fr"): "Madame, Monsieur,",
            ("formal", "en"): "Dear Sir/Madam,",
            ("casual", "fr"): "Salut,",
            ("casual", "en"): "Hi,",
            ("friendly", "fr"): "Bonjour,",
            ("friendly", "en"): "Hi there,",
        }

        closings = {
            ("professional", "fr"): "Cordialement,",
            ("professional", "en"): "Best regards,",
            ("formal", "fr"): "Veuillez agréer mes salutations distinguées.",
            ("formal", "en"): "Yours sincerely,",
            ("casual", "fr"): "À bientôt,",
            ("casual", "en"): "Cheers,",
            ("friendly", "fr"): "À très vite,",
            ("friendly", "en"): "Talk soon,",
        }

        greeting = greetings.get((self.tone, self.language), "Bonjour,")
        closing = closings.get((self.tone, self.language), "Cordialement,")

        # Build reply body
        lines = [greeting, ""]

        # Add user's reply intent if provided
        if self.reply_intent:
            lines.append(self.reply_intent)
        else:
            # Placeholder for AI-generated content
            if self.language == "fr":
                lines.append("[Votre réponse ici]")
            else:
                lines.append("[Your reply here]")

        lines.extend(["", closing])

        # Include quoted original if requested
        if self.include_original and self.original_content:
            original_date_str = (
                self.original_date.strftime("%d/%m/%Y à %H:%M")
                if self.original_date
                else "date inconnue"
            )

            if self.language == "fr":
                header = f"Le {original_date_str}, {self.original_from} a écrit :"
            else:
                original_date_str = (
                    self.original_date.strftime("%Y-%m-%d at %H:%M")
                    if self.original_date
                    else "unknown date"
                )
                header = f"On {original_date_str}, {self.original_from} wrote:"

            lines.extend(["", "---", header, ""])

            # Quote original content (prefix with >)
            for line in self.original_content[:1000].split("\n"):
                lines.append(f"> {line}")

        return "\n".join(lines)

    def supports_undo(self) -> bool:
        """Draft preparation can be undone by discarding"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can undo if draft was created"""
        return result.success and self._created_draft_id is not None

    def undo(self, _result: ActionResult) -> bool:
        """Undo by discarding the draft"""
        if not self._created_draft_id:
            logger.warning("Cannot undo PrepareEmailReplyAction: no draft ID")
            return False

        try:
            draft = self.draft_storage.discard_draft(
                self._created_draft_id,
                reason="Action undone",
            )

            if draft:
                logger.info(
                    f"PrepareEmailReplyAction undone: discarded draft {self._created_draft_id}"
                )
                self._executed = False
                return True
            else:
                logger.warning(f"Draft {self._created_draft_id} not found for undo")
                return False

        except Exception as e:
            logger.error(f"Failed to undo PrepareEmailReplyAction: {e}")
            return False

    def dependencies(self) -> list[str]:
        """No dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated ~2-5 seconds for AI generation"""
        return 3.0


def create_email_reply_draft(
    email_id: int,
    account_email: str,
    original_subject: str,
    original_from: str,
    original_content: str,
    reply_intent: str = "",
    tone: str = "professional",
    language: str = "fr",
    original_date: Optional[datetime] = None,
    original_message_id: Optional[str] = None,
    include_original: bool = True,
) -> PrepareEmailReplyAction:
    """
    Factory function for creating email reply draft action

    Args:
        email_id: IMAP UID of the original email
        account_email: Account to send reply from
        original_subject: Subject of the original email
        original_from: Sender of the original email
        original_content: Content of the original email
        reply_intent: User's intent for the reply (optional)
        tone: Tone of the reply (professional, casual, formal, friendly)
        language: Language for the reply (fr, en)
        original_date: Date of the original email
        original_message_id: Message-ID of the original email
        include_original: Whether to include quoted original in reply

    Returns:
        PrepareEmailReplyAction ready to execute
    """
    return PrepareEmailReplyAction(
        email_id=email_id,
        account_email=account_email,
        original_subject=original_subject,
        original_from=original_from,
        original_content=original_content,
        reply_intent=reply_intent,
        tone=tone,
        language=language,
        original_date=original_date,
        original_message_id=original_message_id,
        include_original=include_original,
    )
