"""
Action Factory - Converts Email Analysis to Figaro Actions

Bridges the gap between AI analysis results and executable actions.
Used by the CognitivePipeline to generate actions from EmailAnalysis.
"""

from typing import TYPE_CHECKING

from src.core.schemas import EmailAction, EmailAnalysis, EmailMetadata
from src.figaro.actions.base import Action
from src.figaro.actions.email import ArchiveEmailAction, DeleteEmailAction
from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.core.config_manager import EmailAccountConfig

logger = get_logger("trivelin.action_factory")


class ActionFactory:
    """
    Factory for creating Figaro actions from EmailAnalysis

    Converts high-level AI decisions (ARCHIVE, DELETE, TASK, etc.)
    into concrete executable actions for the Figaro orchestrator.

    Example:
        >>> factory = ActionFactory(imap_config)
        >>> actions = factory.create_actions(analysis, metadata)
        >>> for action in actions:
        ...     result = action.execute()
    """

    def __init__(self, imap_config: "EmailAccountConfig"):
        """
        Initialize action factory

        Args:
            imap_config: IMAP configuration for email actions
        """
        self.imap_config = imap_config

    def create_actions(
        self,
        analysis: EmailAnalysis,
        metadata: EmailMetadata
    ) -> list[Action]:
        """
        Create actions from email analysis

        Maps EmailAction enum to concrete Action implementations:
        - ARCHIVE → ArchiveEmailAction
        - DELETE → DeleteEmailAction
        - TASK → CreateTaskAction + ArchiveEmailAction (future)
        - REFERENCE → MoveEmailAction (to Reference folder)
        - REVIEW → No action (needs manual handling)
        - SNOOZE → No action (not yet implemented)

        Args:
            analysis: EmailAnalysis from AI reasoning
            metadata: Email metadata for action context

        Returns:
            List of Action objects ready for execution
        """
        actions: list[Action] = []
        email_id = metadata.id
        account_email = str(metadata.to[0]) if metadata.to else ""

        logger.debug(
            "Creating actions from analysis",
            extra={
                "email_id": email_id,
                "action": analysis.action.value,
                "confidence": analysis.confidence,
            }
        )

        # Map action type to concrete actions
        if analysis.action == EmailAction.ARCHIVE:
            actions.append(
                ArchiveEmailAction(
                    email_id=email_id,
                    account_email=account_email,
                    imap_config=self.imap_config,
                    current_folder="INBOX",
                    archive_folder=self.imap_config.archive_folder,
                )
            )

        elif analysis.action == EmailAction.DELETE:
            actions.append(
                DeleteEmailAction(
                    email_id=email_id,
                    account_email=account_email,
                    imap_config=self.imap_config,
                    current_folder="INBOX",
                    delete_folder=self.imap_config.delete_folder,
                )
            )

        elif analysis.action in (EmailAction.KEEP, EmailAction.QUEUE):
            # KEEP/QUEUE = no auto-action, needs manual handling
            logger.debug(
                f"{analysis.action.value} action - no actions created",
                extra={"email_id": email_id}
            )

        elif analysis.action == EmailAction.FLAG:
            # FLAG = mark for follow-up, archive for now
            # TODO: Implement IMAP flag setting
            actions.append(
                ArchiveEmailAction(
                    email_id=email_id,
                    account_email=account_email,
                    imap_config=self.imap_config,
                    current_folder="INBOX",
                    archive_folder=self.imap_config.archive_folder,
                )
            )

        elif analysis.action == EmailAction.DEFER:
            # DEFER = snooze, not yet implemented
            logger.debug(
                "DEFER action - snooze not implemented, keeping in inbox",
                extra={"email_id": email_id}
            )

        elif analysis.action == EmailAction.REPLY:
            # REPLY = response needed, keep in inbox for now
            logger.debug(
                "REPLY action - keeping in inbox for response",
                extra={"email_id": email_id}
            )

        else:
            logger.warning(
                f"Unknown action type: {analysis.action}",
                extra={"email_id": email_id, "action": analysis.action}
            )

        logger.debug(
            f"Created {len(actions)} actions",
            extra={
                "email_id": email_id,
                "action_types": [a.action_type for a in actions],
            }
        )

        return actions
