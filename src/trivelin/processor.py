"""
Email Processor

Core email processing logic that orchestrates IMAP, AI analysis, and actions.
"""

import signal
import sys
from typing import Any, Optional

from src.core.config_manager import get_config
from src.core.entities import AUTO_APPLY_THRESHOLD
from src.core.error_manager import get_error_manager
from src.core.events import ProcessingEvent, ProcessingEventType, get_event_bus
from src.core.schemas import (
    EmailAction,
    EmailAnalysis,
    EmailContent,
    EmailMetadata,
    EmailValidationResult,
    ProcessedEmail,
)
from src.core.state_manager import get_state_manager
from src.integrations.email.imap_client import IMAPClient
from src.integrations.storage.queue_storage import get_queue_storage
from src.monitoring.logger import get_logger
from src.sancho.router import AIModel, get_ai_router
from src.utils import now_utc

logger = get_logger("email_processor")

# Default limit for processing - prevents overwhelming the system
# This applies to all channels (email, teams, calendar)
# Items are always processed oldest-first to handle backlog chronologically
DEFAULT_PROCESSING_LIMIT = 20


class EmailProcessor:
    """
    Email processor that orchestrates the email processing pipeline

    Pipeline:
    1. Fetch emails from IMAP
    2. Analyze with AI
    3. Execute actions
    4. Update state
    5. Log results

    Usage:
        processor = EmailProcessor()
        results = processor.process_inbox(limit=50, auto_execute=True)
    """

    def __init__(self):
        """Initialize email processor"""
        self.config = get_config()
        self.state = get_state_manager()
        self.imap_client = IMAPClient(self.config.email)
        self.ai_router = get_ai_router(self.config.ai)
        self.event_bus = get_event_bus()
        self.error_manager = get_error_manager()
        self.queue_storage = get_queue_storage()
        self._shutdown_requested = False

        # Setup graceful shutdown handlers
        self._setup_signal_handlers()

        # Initialize recovery engine
        from src.core.recovery_engine import init_recovery_engine
        self.recovery_engine = init_recovery_engine()

        # Initialize NoteManager for auto-apply of proposed_notes
        self.note_manager = None
        try:
            from src.passepartout.note_manager import NoteManager
            self.note_manager = NoteManager(notes_dir=self.config.storage.notes_dir)
        except Exception as e:
            logger.warning(f"NoteManager not available for auto-apply: {e}")

        # Initialize cognitive pipeline if enabled
        self.cognitive_pipeline = None
        if self.config.processing.enable_cognitive_reasoning:
            self._init_cognitive_pipeline()

        logger.info(
            "Email processor initialized",
            extra={
                "cognitive_enabled": self.cognitive_pipeline is not None,
                "auto_apply_enabled": self.note_manager is not None,
            }
        )

    def _init_cognitive_pipeline(self) -> None:
        """Initialize the cognitive pipeline components"""
        from src.trivelin.cognitive_pipeline import CognitivePipeline

        self.cognitive_pipeline = CognitivePipeline(
            ai_router=self.ai_router,
            config=self.config.processing,
        )
        logger.info(
            "Cognitive pipeline initialized",
            extra={
                "confidence_threshold": self.config.processing.cognitive_confidence_threshold,
                "timeout_seconds": self.config.processing.cognitive_timeout_seconds,
                "max_passes": self.config.processing.cognitive_max_passes,
            }
        )

    def _setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown

        Handles SIGINT (Ctrl+C) and SIGTERM for clean process termination

        Note: Signal handlers must be minimal to avoid deadlocks.
        Logging is done via stderr instead of logger.
        """
        def shutdown_handler(signum: int, _frame: object) -> None:
            """
            Handle shutdown signals gracefully

            IMPORTANT: This runs in signal context - must be minimal!
            No logging framework calls to avoid deadlocks.
            """
            # Set shutdown flag (atomic operation)
            self._shutdown_requested = True

            # Write directly to stderr (thread-safe in signal handlers)
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            sys.stderr.write(f"\n[SHUTDOWN] Received {signal_name}, stopping gracefully...\n")
            sys.stderr.flush()

        # Register handlers for SIGINT and SIGTERM
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        logger.debug("Signal handlers registered for graceful shutdown")

    def _analyze_email(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        _auto_execute: bool = False,
        existing_folders: list[str] | None = None
    ) -> Optional[EmailAnalysis]:
        """
        Analyze email using cognitive pipeline or legacy single-pass

        When cognitive reasoning is enabled:
        - Uses CognitivePipeline for multi-pass reasoning
        - Falls back to legacy mode on failure if configured

        When cognitive reasoning is disabled:
        - Uses direct AI router call (legacy mode)

        Args:
            metadata: Email metadata
            content: Email content
            auto_execute: Whether to auto-execute actions (passed to pipeline)
            existing_folders: List of existing IMAP folders for destination suggestions

        Returns:
            EmailAnalysis or None if analysis fails
        """
        # Try cognitive pipeline if enabled
        if self.cognitive_pipeline:
            try:
                pipeline_result = self.cognitive_pipeline.process(
                    metadata, content, auto_execute=False  # Don't auto-execute in pipeline
                )

                if pipeline_result.success and pipeline_result.analysis:
                    logger.debug(
                        "Cognitive pipeline analysis complete",
                        extra={
                            "email_id": metadata.id,
                            "confidence": pipeline_result.analysis.confidence,
                            "passes": pipeline_result.reasoning_result.passes_executed
                            if pipeline_result.reasoning_result else 0,
                            "duration": pipeline_result.total_duration_seconds,
                        }
                    )
                    return pipeline_result.analysis

                # Pipeline failed - check if we should fallback
                if self.config.processing.fallback_on_failure:
                    logger.warning(
                        "Cognitive pipeline failed, falling back to legacy mode",
                        extra={
                            "email_id": metadata.id,
                            "error": pipeline_result.error,
                            "error_stage": pipeline_result.error_stage,
                            "timed_out": pipeline_result.timed_out,
                        }
                    )
                    # Fall through to legacy mode below
                else:
                    logger.error(
                        "Cognitive pipeline failed, no fallback configured",
                        extra={
                            "email_id": metadata.id,
                            "error": pipeline_result.error,
                        }
                    )
                    return None

            except Exception as e:
                logger.error(
                    f"Cognitive pipeline exception: {e}",
                    extra={"email_id": metadata.id},
                    exc_info=True
                )
                if not self.config.processing.fallback_on_failure:
                    return None
                # Fall through to legacy mode

        # Legacy mode: direct AI router call
        analysis = self.ai_router.analyze_email(
            metadata,
            content,
            model=AIModel.CLAUDE_HAIKU,
            existing_folders=existing_folders
        )
        return analysis

    def process_inbox(
        self,
        limit: int = DEFAULT_PROCESSING_LIMIT,
        auto_execute: bool = False,
        confidence_threshold: Optional[int] = None,
        unread_only: bool = False,
        unflagged_only: bool = True
    ) -> list[ProcessedEmail]:
        """
        Process emails from inbox

        Args:
            limit: Maximum number of emails to process (default: 20)
            auto_execute: Automatically execute high-confidence decisions
            confidence_threshold: Minimum confidence for auto-execution
            unread_only: Only process unread emails (UNSEEN flag)
            unflagged_only: Only process unflagged emails (no \\Flagged flag)
                          Default: True (process unflagged = not already marked)

        Returns:
            List of processed emails, sorted oldest first
        """
        if confidence_threshold is None:
            confidence_threshold = self.config.ai.confidence_threshold

        logger.info(
            "Starting inbox processing",
            extra={
                "limit": limit,
                "auto_execute": auto_execute,
                "confidence_threshold": confidence_threshold,
                "unread_only": unread_only,
                "unflagged_only": unflagged_only
            }
        )

        # Start processing session
        self.state.set("processing_started_at", now_utc().isoformat())
        self.state.set("processing_mode", "auto" if auto_execute else "manual")

        # Emit processing started event
        self.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.PROCESSING_STARTED,
            metadata={
                "limit": limit,
                "auto_execute": auto_execute,
                "confidence_threshold": confidence_threshold,
                "unread_only": unread_only,
                "unflagged_only": unflagged_only
            }
        ))

        processed_emails = []

        try:
            # CRITICAL FIX: Keep IMAP connection open for entire session
            # This prevents connection exhaustion (one connection for all operations)
            with self.imap_client.connect():
                # Get existing folders for AI destination suggestions
                existing_folders = self.imap_client.list_folders()
                logger.debug(f"Found {len(existing_folders)} existing IMAP folders")

                emails = self.imap_client.fetch_emails(
                    folder=self.config.email.inbox_folder,
                    limit=limit,
                    unread_only=unread_only,
                    unflagged_only=unflagged_only
                )

                logger.info(f"Fetched {len(emails)} emails from inbox")

                # Process each email (reusing the same connection)
                # Events are emitted for display instead of progress bar
                for idx, (metadata, content) in enumerate(emails, start=1):
                    # Check for shutdown request
                    if self._shutdown_requested:
                        logger.info(
                            "Shutdown requested, stopping email processing",
                            extra={
                                "processed": len(processed_emails),
                                "remaining": len(emails) - len(processed_emails)
                            }
                        )
                        break

                    try:
                        # Emit email started event
                        self.event_bus.emit(ProcessingEvent(
                            event_type=ProcessingEventType.EMAIL_STARTED,
                            email_id=metadata.id,
                            subject=metadata.subject,
                            from_address=metadata.from_address,
                            current=idx,
                            total=len(emails)
                        ))

                        # Process email
                        processed = self._process_single_email(
                            metadata,
                            content,
                            auto_execute=auto_execute,
                            confidence_threshold=confidence_threshold,
                            current=idx,
                            total=len(emails),
                            existing_folders=existing_folders
                        )

                        if processed:
                            processed_emails.append(processed)

                    except Exception as e:
                        # Emit error event
                        self.event_bus.emit(ProcessingEvent(
                            event_type=ProcessingEventType.EMAIL_ERROR,
                            email_id=metadata.id,
                            subject=metadata.subject,
                            from_address=metadata.from_address,
                            error=str(e),
                            error_type=type(e).__name__,
                            current=idx,
                            total=len(emails)
                        ))

                        logger.error(
                            f"Failed to process email {metadata.id}: {e}",
                            exc_info=True,
                            extra={"email_id": metadata.id, "subject": metadata.subject}
                        )

            # Update final statistics
            self.state.set("processing_completed_at", now_utc().isoformat())
            if self._shutdown_requested:
                self.state.set("shutdown_graceful", True)

            completion_status = "interrupted by shutdown" if self._shutdown_requested else "completed"

            # Emit processing completed event
            self.event_bus.emit(ProcessingEvent(
                event_type=ProcessingEventType.PROCESSING_COMPLETED,
                metadata={
                    "total_processed": len(processed_emails),
                    "auto_executed": self.state.get("emails_auto_executed", 0),
                    "queued": self.state.get("emails_queued", 0),
                    "shutdown_requested": self._shutdown_requested
                }
            ))

            logger.info(
                f"Inbox processing {completion_status}",
                extra={
                    "total_processed": len(processed_emails),
                    "auto_executed": self.state.get("emails_auto_executed", 0),  # Use actual counter
                    "shutdown_requested": self._shutdown_requested
                }
            )

            return processed_emails

        except Exception as e:
            logger.error(f"Inbox processing failed: {e}", exc_info=True)
            return processed_emails

    def _process_single_email(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        auto_execute: bool = False,
        confidence_threshold: int = 90,
        current: Optional[int] = None,
        total: Optional[int] = None,
        existing_folders: list[str] | None = None
    ) -> Optional[ProcessedEmail]:
        """
        Process a single email

        Args:
            metadata: Email metadata
            content: Email content
            auto_execute: Auto-execute high-confidence decisions
            confidence_threshold: Minimum confidence for auto-execution
            existing_folders: List of existing IMAP folders for destination suggestions

        Returns:
            ProcessedEmail or None if processing fails
        """
        # Check if already processed
        if self.state.is_processed(str(metadata.id)):
            logger.debug(f"Email {metadata.id} already processed, skipping")
            return None

        logger.info(
            "Processing email",
            extra={
                "email_id": metadata.id,
                "subject": metadata.subject,
                "from": metadata.from_address
            }
        )

        # Validate email before processing
        validation_result = self._validate_email_for_processing(metadata, content)

        if not validation_result.is_valid:
            logger.info(
                f"Skipping email {metadata.id}: {validation_result.reason}",
                extra={
                    "email_id": metadata.id,
                    "skip_reason": validation_result.reason,
                    "validation_details": validation_result.details
                }
            )
            self.state.increment("emails_skipped")
            return None

        # Apply content truncation if needed
        if validation_result.should_truncate:
            content = self._truncate_content(content, max_chars=10000)
            logger.info(
                f"Truncated email {metadata.id} content",
                extra={"email_id": metadata.id, "max_chars": 10000}
            )

        # Analyze email with AI (cognitive pipeline or legacy)
        analysis = self._analyze_email(metadata, content, auto_execute, existing_folders)

        if not analysis:
            logger.warning(f"Failed to analyze email {metadata.id}")
            return None

        # Auto-apply high-confidence proposals (notes, tasks)
        # This happens BEFORE execution decision to capture all proposals
        auto_apply_result = self._auto_apply_proposals(analysis, str(metadata.id))
        if any(v > 0 for v in auto_apply_result.values()):
            logger.info(
                "Auto-apply results",
                extra={
                    "email_id": metadata.id,
                    **auto_apply_result,
                }
            )

        # Create processed email record
        processed = ProcessedEmail(
            metadata=metadata,
            content=content,
            analysis=analysis,
            processed_at=now_utc()
        )

        # Update state
        self.state.increment("emails_processed")
        self.state.add_confidence_score(analysis.confidence)
        self.state.mark_processed(str(metadata.id))

        # Cache email data
        self.state.cache_entity(
            f"email-{metadata.id}",
            {
                "subject": metadata.subject,
                "from": metadata.from_address,
                "action": analysis.action.value,
                "confidence": analysis.confidence,
                "processed_at": processed.processed_at.isoformat()
            }
        )

        # Execute action if confidence is high enough
        if auto_execute and analysis.confidence >= confidence_threshold:
            self._execute_action(metadata, analysis)
            self.state.increment("emails_auto_executed")  # Track actual auto-executions

            # Emit email completed event (executed)
            self.event_bus.emit(ProcessingEvent(
                event_type=ProcessingEventType.EMAIL_COMPLETED,
                email_id=metadata.id,
                subject=metadata.subject,
                from_address=metadata.from_address,
                email_date=metadata.date,
                preview=content.plain_text[:80] if content.plain_text else None,
                action=analysis.action.value,
                confidence=analysis.confidence,
                category=analysis.category.value if analysis.category else None,
                reasoning=analysis.reasoning,
                current=current,
                total=total,
                metadata={"executed": True}
            ))
        else:
            # Save to queue storage for manual review
            content_preview = content.plain_text[:200] if content.plain_text else ""
            queue_item_id = self.queue_storage.save_item(
                metadata=metadata,
                analysis=analysis,
                content_preview=content_preview,
                account_id=self.config.email.get_enabled_accounts()[0].account_id
                if self.config.email.get_enabled_accounts()
                else None,
            )

            # Flag the email to prevent reimport on next run
            # Uses \\Flagged which is filtered out by unflagged_only=True
            try:
                self.imap_client.add_flag(
                    msg_id=metadata.id,
                    folder=metadata.folder or self.config.email.inbox_folder
                )
            except Exception as e:
                logger.warning(f"Failed to flag email {metadata.id}: {e}")

            logger.info(
                "Queuing email for manual review",
                extra={
                    "email_id": metadata.id,
                    "queue_item_id": queue_item_id,
                    "confidence": analysis.confidence,
                    "threshold": confidence_threshold
                }
            )
            self.state.increment("emails_queued")

            # Emit email queued event
            self.event_bus.emit(ProcessingEvent(
                event_type=ProcessingEventType.EMAIL_QUEUED,
                email_id=metadata.id,
                subject=metadata.subject,
                from_address=metadata.from_address,
                email_date=metadata.date,
                preview=content.plain_text[:80] if content.plain_text else None,
                action=analysis.action.value,
                confidence=analysis.confidence,
                category=analysis.category.value if analysis.category else None,
                reasoning=analysis.reasoning,
                current=current,
                total=total,
                metadata={"executed": False}
            ))

        return processed

    def _execute_action(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis
    ) -> bool:
        """
        Execute action based on analysis

        Args:
            metadata: Email metadata
            analysis: Email analysis

        Returns:
            True if action executed successfully
        """
        logger.info(
            "Executing action",
            extra={
                "email_id": metadata.id,
                "action": analysis.action.value,
                "confidence": analysis.confidence
            }
        )

        try:
            if analysis.action == EmailAction.ARCHIVE:
                return self._archive_email(metadata, analysis)

            elif analysis.action == EmailAction.DELETE:
                return self._delete_email(metadata)

            elif analysis.action == EmailAction.TASK:
                return self._create_task(metadata, analysis)

            elif analysis.action == EmailAction.REPLY:
                logger.info(f"REPLY action not yet implemented for email {metadata.id}")
                return False

            elif analysis.action == EmailAction.DEFER:
                logger.info(f"DEFER action not yet implemented for email {metadata.id}")
                return False

            elif analysis.action == EmailAction.QUEUE:
                # Already handled by queueing logic
                return True

            else:
                logger.warning(f"Unknown action: {analysis.action}")
                return False

        except Exception as e:
            logger.error(
                f"Failed to execute action: {e}",
                exc_info=True,
                extra={"email_id": metadata.id, "action": analysis.action.value}
            )
            return False

    def _archive_email(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis
    ) -> bool:
        """
        Archive email to specified destination

        Args:
            metadata: Email metadata
            analysis: Email analysis

        Returns:
            True if successful

        Note:
            Assumes IMAP connection is already established.
            This method is called within the process_inbox() connection context.
        """
        try:
            # CRITICAL FIX: Reuse existing connection instead of creating new one
            # Connection is maintained by process_inbox() context manager
            if self.imap_client._connection is None:
                raise RuntimeError("IMAP connection not established")

            success = self.imap_client.move_email(
                msg_id=metadata.id,
                from_folder=metadata.folder,
                to_folder=analysis.destination or self.config.email.archive_folder
            )

            if success:
                logger.info(
                    "Email archived",
                    extra={
                        "email_id": metadata.id,
                        "destination": analysis.destination
                    }
                )
                self.state.increment("emails_archived")
                return True
            else:
                logger.warning(f"Failed to archive email {metadata.id}")
                return False

        except Exception as e:
            logger.error(f"Error archiving email: {e}", exc_info=True)
            return False

    def _delete_email(self, metadata: EmailMetadata) -> bool:
        """
        Delete email

        Args:
            metadata: Email metadata

        Returns:
            True if successful

        Note:
            Assumes IMAP connection is already established.
            This method is called within the process_inbox() connection context.
        """
        try:
            # CRITICAL FIX: Reuse existing connection instead of creating new one
            if self.imap_client._connection is None:
                raise RuntimeError("IMAP connection not established")

            # Mark as deleted (moved to trash)
            success = self.imap_client.move_email(
                msg_id=metadata.id,
                from_folder=metadata.folder,
                to_folder=self.config.email.delete_folder
            )

            if success:
                logger.info("Email deleted", extra={"email_id": metadata.id})
                self.state.increment("emails_deleted")
                return True
            else:
                logger.warning(f"Failed to delete email {metadata.id}")
                return False

        except Exception as e:
            logger.error(f"Error deleting email: {e}", exc_info=True)
            return False

    def _create_task(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis
    ) -> bool:
        """
        Create OmniFocus task

        Args:
            metadata: Email metadata
            analysis: Email analysis

        Returns:
            True if successful
        """
        if not analysis.omnifocus_task:
            logger.warning(f"No task data in analysis for email {metadata.id}")
            return False

        logger.info(
            "Creating OmniFocus task",
            extra={
                "email_id": metadata.id,
                "task_title": analysis.omnifocus_task.get("title", "")
            }
        )

        # TODO: Integrate with OmniFocus MCP in Phase 5
        # For now, just log the task creation
        logger.info(
            "Task creation not yet implemented - would create task",
            extra={"task_data": analysis.omnifocus_task}
        )

        self.state.increment("tasks_created")
        return True

    def _auto_apply_proposals(
        self,
        analysis: EmailAnalysis,
        email_id: str,
    ) -> dict[str, Any]:
        """
        Auto-apply high-confidence proposed_notes and proposed_tasks

        Applies proposals that meet AUTO_APPLY_THRESHOLD (0.90).
        Lower confidence proposals remain in the analysis for UI display
        and manual review.

        Args:
            analysis: Email analysis containing proposed_notes/tasks
            email_id: Source email ID for tracking

        Returns:
            Dict with counts of applied and queued proposals
        """
        result = {
            "notes_created": 0,
            "notes_enriched": 0,
            "tasks_created": 0,
            "queued_for_review": 0,
        }

        # Auto-apply proposed notes
        if analysis.proposed_notes and self.note_manager:
            for proposal in analysis.proposed_notes:
                confidence = proposal.get("confidence", 0)
                action = proposal.get("action", "")
                title = proposal.get("title", "")

                if confidence >= AUTO_APPLY_THRESHOLD:
                    applied = self._apply_proposed_note(proposal, email_id)
                    if applied:
                        if action == "create":
                            result["notes_created"] += 1
                        elif action == "enrich":
                            result["notes_enriched"] += 1
                        logger.info(
                            "Auto-applied proposed note",
                            extra={
                                "action": action,
                                "title": title,
                                "confidence": confidence,
                                "email_id": email_id,
                            }
                        )
                    else:
                        result["queued_for_review"] += 1
                else:
                    result["queued_for_review"] += 1
                    logger.debug(
                        f"Proposed note below threshold: {title} (conf={confidence:.2f})"
                    )

        # Auto-apply proposed tasks
        if analysis.proposed_tasks:
            for proposal in analysis.proposed_tasks:
                confidence = proposal.get("confidence", 0)
                title = proposal.get("title", "")

                if confidence >= AUTO_APPLY_THRESHOLD:
                    applied = self._apply_proposed_task(proposal, email_id)
                    if applied:
                        result["tasks_created"] += 1
                        logger.info(
                            "Auto-applied proposed task",
                            extra={
                                "title": title,
                                "confidence": confidence,
                                "email_id": email_id,
                            }
                        )
                    else:
                        result["queued_for_review"] += 1
                else:
                    result["queued_for_review"] += 1
                    logger.debug(
                        f"Proposed task below threshold: {title} (conf={confidence:.2f})"
                    )

        return result

    def _apply_proposed_note(
        self,
        proposal: dict[str, Any],
        email_id: str,
    ) -> bool:
        """
        Apply a single proposed note

        Args:
            proposal: ProposedNote as dict with action, title, content_summary, etc.
            email_id: Source email ID

        Returns:
            True if successfully applied
        """
        if not self.note_manager:
            return False

        try:
            action = proposal.get("action", "create")
            title = proposal.get("title", "")
            content_summary = proposal.get("content_summary", "")
            note_type = proposal.get("note_type", "general")
            suggested_tags = proposal.get("suggested_tags", [])
            target_note_id = proposal.get("target_note_id")

            if action == "create":
                # Create new note
                content = self._format_note_content(
                    title=title,
                    summary=content_summary,
                    email_id=email_id,
                    note_type=note_type,
                )

                note_id = self.note_manager.create_note(
                    title=title,
                    content=content,
                    tags=suggested_tags,
                    metadata={
                        "source": "email_extraction",
                        "source_email_id": email_id,
                        "note_type": note_type,
                        "auto_applied": True,
                    }
                )

                self.state.increment("notes_created")
                logger.info(f"Created note from email: {note_id}")
                return True

            elif action == "enrich" and target_note_id:
                # Enrich existing note (append to it)
                existing_note = self.note_manager.get_note(target_note_id)
                if existing_note:
                    enrichment_section = (
                        f"\n\n---\n"
                        f"## Enrichissement (Email: {email_id[:8]}...)\n\n"
                        f"{content_summary}\n"
                    )
                    updated_content = existing_note.content + enrichment_section

                    self.note_manager.update_note(
                        note_id=target_note_id,
                        content=updated_content,
                    )

                    self.state.increment("notes_enriched")
                    logger.info(f"Enriched note {target_note_id} from email")
                    return True
                else:
                    logger.warning(f"Target note not found: {target_note_id}")
                    return False

            return False

        except Exception as e:
            logger.error(f"Failed to apply proposed note: {e}", exc_info=True)
            return False

    def _apply_proposed_task(
        self,
        proposal: dict[str, Any],
        email_id: str,
    ) -> bool:
        """
        Apply a single proposed task (create OmniFocus task)

        Args:
            proposal: ProposedTask as dict with title, note, due_date, etc.
            email_id: Source email ID

        Returns:
            True if successfully applied
        """
        try:
            title = proposal.get("title", "")
            note = proposal.get("note", "")
            project = proposal.get("project")
            tags = proposal.get("tags", [])
            due_date = proposal.get("due_date")

            # For now, log the task creation (OmniFocus integration not yet complete)
            # TODO: Use OmniFocus MCP when available
            logger.info(
                "Would create OmniFocus task (not yet implemented)",
                extra={
                    "title": title,
                    "note": note[:100] if note else None,
                    "project": project,
                    "tags": tags,
                    "due_date": due_date,
                    "source_email_id": email_id,
                }
            )

            self.state.increment("tasks_proposed")
            return True

        except Exception as e:
            logger.error(f"Failed to apply proposed task: {e}", exc_info=True)
            return False

    def _format_note_content(
        self,
        title: str,
        summary: str,
        email_id: str,
        note_type: str,
    ) -> str:
        """
        Format note content with standard structure

        Args:
            title: Note title
            summary: Content summary from AI
            email_id: Source email ID
            note_type: Type of note (personne, projet, etc.)

        Returns:
            Formatted markdown content
        """
        now = now_utc().strftime("%Y-%m-%d %H:%M")

        content = f"""# {title}

## Résumé

{summary}

## Métadonnées

- **Type**: {note_type}
- **Source**: Email ({email_id})
- **Créé**: {now}
- **Auto-appliqué**: Oui (confiance >= {AUTO_APPLY_THRESHOLD * 100:.0f}%)

## Notes

_Ajouter vos notes ici..._
"""
        return content

    def _validate_email_for_processing(
        self,
        metadata: EmailMetadata,
        content: EmailContent
    ) -> EmailValidationResult:
        """
        Validate email is suitable for AI processing

        Args:
            metadata: Email metadata
            content: Email content

        Returns:
            EmailValidationResult with validation status
        """
        # Check for minimum content
        if not content.plain_text and not content.html:
            return EmailValidationResult(
                is_valid=False,
                reason="no_text_content",
                details="Email has no text content (binary only)"
            )

        # Check content length
        total_length = len(content.plain_text or "") + len(content.html or "")

        if total_length < 10:
            return EmailValidationResult(
                is_valid=False,
                reason="content_too_short",
                details=f"Email has only {total_length} characters"
            )

        # Check for oversized content (>200KB = ~50k tokens)
        MAX_CONTENT_SIZE = 200_000  # 200KB
        if total_length > MAX_CONTENT_SIZE:
            return EmailValidationResult(
                is_valid=True,
                should_truncate=True,
                reason="content_oversized",
                details=f"Email size {total_length} bytes exceeds {MAX_CONTENT_SIZE}"
            )

        # Check for spam indicators (log warning but don't skip)
        subject_lower = metadata.subject.lower()
        spam_keywords = [
            "viagra", "cialis", "casino", "lottery", "winner",
            "click here now", "act now", "limited time", "buy now",
            "free money", "weight loss", "enlarge"
        ]

        if any(keyword in subject_lower for keyword in spam_keywords):
            logger.warning(
                f"Email {metadata.id} matches spam pattern",
                extra={"subject": metadata.subject, "from": metadata.from_address}
            )
            # Don't skip - just flag for review

        # Check sender blacklist (if configured)
        sender_domain = metadata.from_address.split('@')[-1] if '@' in metadata.from_address else ""
        blocked_domains = getattr(self.config.email, 'blocked_domains', [])

        if sender_domain and sender_domain in blocked_domains:
            return EmailValidationResult(
                is_valid=False,
                reason="sender_blocked",
                details=f"Sender domain {sender_domain} is blocked"
            )

        # All checks passed
        return EmailValidationResult(
            is_valid=True,
            should_truncate=False
        )

    def _truncate_content(
        self,
        content: EmailContent,
        max_chars: int = 10000
    ) -> EmailContent:
        """
        Truncate email content to fit token limits

        Args:
            content: Original email content
            max_chars: Maximum characters to keep

        Returns:
            Truncated EmailContent
        """
        truncated_text = content.plain_text[:max_chars] if content.plain_text else None
        truncated_html = content.html[:max_chars] if content.html else None

        # Update metadata to track truncation
        content_metadata = content.metadata or {}
        content_metadata["truncated"] = True
        content_metadata["original_plain_text_size"] = len(content.plain_text or "")
        content_metadata["original_html_size"] = len(content.html or "")

        return EmailContent(
            plain_text=truncated_text,
            html=truncated_html,
            attachments=content.attachments,
            preview=content.preview,
            metadata=content_metadata
        )

    def get_processing_stats(self) -> dict:
        """
        Get processing statistics

        Returns:
            Dict with processing stats
        """
        return {
            "emails_processed": self.state.get("emails_processed", 0),
            "emails_auto_executed": self.state.get("emails_auto_executed", 0),
            "emails_archived": self.state.get("emails_archived", 0),
            "emails_deleted": self.state.get("emails_deleted", 0),
            "emails_queued": self.state.get("emails_queued", 0),
            "emails_skipped": self.state.get("emails_skipped", 0),
            "tasks_created": self.state.get("tasks_created", 0),
            "average_confidence": self._safe_get_average_confidence(),
            "processing_mode": self.state.get("processing_mode", "unknown"),
            "rate_limit_status": self._safe_get_rate_limit_status()
        }

    def _safe_get_average_confidence(self) -> float:
        """
        Safely get average confidence with fallback

        Returns:
            Average confidence or 0.0 on error
        """
        try:
            if hasattr(self.state, 'get_average_confidence'):
                return self.state.get_average_confidence()
            else:
                # Fallback: calculate manually
                return self.state.stats.confidence_avg if hasattr(self.state, 'stats') else 0.0
        except Exception as e:
            logger.warning(f"Failed to get average confidence: {e}")
            return 0.0

    def _safe_get_rate_limit_status(self) -> dict:
        """
        Safely get rate limit status with fallback

        Returns:
            Rate limit status dict or empty dict on error
        """
        try:
            if hasattr(self.ai_router, 'get_rate_limit_status'):
                return self.ai_router.get_rate_limit_status()
            else:
                return {"available": 0, "total": 0}
        except Exception as e:
            logger.warning(f"Failed to get rate limit status: {e}")
            return {"available": 0, "total": 0}
