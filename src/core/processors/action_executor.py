"""
Action Executor

Executes actions based on AI analysis results.

Responsibilities:
- Execute IMAP operations (archive, delete, move)
- Create OmniFocus tasks
- Handle execution errors gracefully
- Support dry-run mode for testing
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from src.core.schemas import EmailAction, EmailAnalysis, EmailMetadata
from src.monitoring.logger import get_logger

logger = get_logger("action_executor")


@dataclass
class ExecutionResult:
    """
    Result of action execution

    Attributes:
        success: Whether execution succeeded
        actions_taken: List of action descriptions
        errors: List of errors encountered
        metadata: Additional metadata (e.g., email ID)
    """
    success: bool
    actions_taken: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: Optional[Any] = None


class ActionExecutor:
    """
    Executes actions based on AI analysis

    Provides a clean interface for executing email actions with proper
    error handling and dry-run support.

    Usage:
        executor = ActionExecutor(imap_client, omnifocus)
        result = executor.execute(metadata, analysis, dry_run=False)
    """

    def __init__(
        self,
        imap_client: Optional[Any] = None,
        omnifocus: Optional[Any] = None
    ):
        """
        Initialize executor

        Args:
            imap_client: IMAP client for email operations
            omnifocus: OmniFocus integration for task creation
        """
        self.imap_client = imap_client
        self.omnifocus = omnifocus

    def execute(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis,
        dry_run: bool = False
    ) -> ExecutionResult:
        """
        Execute actions based on analysis

        Process:
        1. Archive/delete/move email based on action
        2. Create OmniFocus task if needed
        3. Collect results and errors

        Args:
            metadata: Email metadata
            analysis: AI analysis result
            dry_run: If True, log actions but don't execute

        Returns:
            ExecutionResult with actions taken and any errors
        """
        actions_taken = []
        errors = []

        logger.info(
            f"Executing actions for email {metadata.message_id}",
            extra={
                "action": analysis.action,
                "dry_run": dry_run
            }
        )

        # Execute email action (archive/delete/etc.)
        email_action_result = self._execute_email_action(
            metadata, analysis, dry_run
        )
        if email_action_result:
            actions_taken.append(email_action_result)

        # Create OmniFocus task if needed
        if self._should_create_task(analysis):
            task_result = self._execute_task_creation(
                metadata, analysis, dry_run
            )
            if task_result:
                actions_taken.append(task_result)

        # Determine success
        success = len(errors) == 0

        return ExecutionResult(
            success=success,
            actions_taken=actions_taken,
            errors=errors,
            metadata=metadata.message_id
        )

    def _execute_email_action(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis,
        dry_run: bool
    ) -> Optional[str]:
        """
        Execute email action (archive/delete/move)

        Args:
            metadata: Email metadata
            analysis: AI analysis
            dry_run: Whether to actually execute

        Returns:
            Action description if executed, None otherwise
        """
        if not self.imap_client:
            logger.debug("No IMAP client configured, skipping email action")
            return None

        try:
            if analysis.action == EmailAction.ARCHIVE:
                if not dry_run:
                    # Use destination folder if specified, otherwise "Archive"
                    folder = analysis.destination or "Archive"
                    self.imap_client.move_email(
                        message_id=metadata.message_id,
                        destination_folder=folder
                    )
                return f"archived to {analysis.destination or 'Archive'}"

            elif analysis.action == EmailAction.DELETE:
                if not dry_run:
                    self.imap_client.delete_email(
                        message_id=metadata.message_id
                    )
                return "deleted"

            elif analysis.action == EmailAction.DEFER:
                # Defer = no immediate action
                return "deferred for later review"

            elif analysis.action == EmailAction.QUEUE:
                # Queue = mark for manual review
                return "queued for review"

            else:
                logger.debug(f"No email action needed for {analysis.action}")
                return None

        except Exception as e:
            logger.error(
                f"Failed to execute email action {analysis.action}: {e}",
                exc_info=True
            )
            return None

    def _should_create_task(self, analysis: EmailAnalysis) -> bool:
        """
        Determine if a task should be created

        Args:
            analysis: AI analysis

        Returns:
            True if task should be created
        """
        # Create task only if omnifocus_task is specified in extractions
        # (TASK action removed - tasks are now created via extractions)
        return hasattr(analysis, 'omnifocus_task') and analysis.omnifocus_task is not None

    def _execute_task_creation(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis,
        dry_run: bool
    ) -> Optional[str]:
        """
        Create OmniFocus task

        Args:
            metadata: Email metadata
            analysis: AI analysis
            dry_run: Whether to actually execute

        Returns:
            Action description if executed, None otherwise
        """
        if not self.omnifocus:
            logger.debug("No OmniFocus integration configured, skipping task creation")
            return None

        try:
            if not dry_run:
                # Extract task details from analysis
                if hasattr(analysis, 'omnifocus_task') and analysis.omnifocus_task:
                    task_data = analysis.omnifocus_task
                    self.omnifocus.create_task(
                        title=task_data.get('title') or metadata.subject,
                        note=task_data.get('note'),
                        defer_date=task_data.get('defer_date'),
                        due_date=task_data.get('due_date'),
                        tags=task_data.get('tags', [])
                    )
                else:
                    # Fallback: simple task from subject
                    self.omnifocus.create_task(
                        title=metadata.subject,
                        note=f"From: {metadata.from_address}"
                    )

            return "task created in OmniFocus"

        except Exception as e:
            logger.error(
                f"Failed to create OmniFocus task: {e}",
                exc_info=True
            )
            return None
