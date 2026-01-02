"""
Email Actions for Figaro

Concrete implementations of email-related actions.
"""

import time
from dataclasses import dataclass
from typing import Optional

from src.core.config_manager import EmailAccountConfig
from src.figaro.actions.base import Action, ActionResult, ValidationResult
from src.integrations.email.imap_client import IMAPClient
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
