"""
Email Processor

Core email processing logic that orchestrates IMAP, AI analysis, and actions.
"""

import signal
import sys
from typing import Optional

from src.ai.router import AIModel, get_ai_router
from src.core.config_manager import get_config
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
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("email_processor")


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
        self._shutdown_requested = False

        # Setup graceful shutdown handlers
        self._setup_signal_handlers()

        # Initialize recovery engine
        from src.core.recovery_engine import init_recovery_engine
        self.recovery_engine = init_recovery_engine()

        logger.info("Email processor initialized with error management")

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

    def process_inbox(
        self,
        limit: Optional[int] = None,
        auto_execute: bool = False,
        confidence_threshold: Optional[int] = None,
        unread_only: bool = False,
        unflagged_only: bool = True
    ) -> list[ProcessedEmail]:
        """
        Process emails from inbox

        Args:
            limit: Maximum number of emails to process
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
                            total=len(emails)
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
        total: Optional[int] = None
    ) -> Optional[ProcessedEmail]:
        """
        Process a single email

        Args:
            metadata: Email metadata
            content: Email content
            auto_execute: Auto-execute high-confidence decisions
            confidence_threshold: Minimum confidence for auto-execution

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

        # Analyze email with AI
        analysis = self.ai_router.analyze_email(
            metadata,
            content,
            model=AIModel.CLAUDE_HAIKU
        )

        if not analysis:
            logger.warning(f"Failed to analyze email {metadata.id}")
            return None

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
            logger.info(
                "Queuing email for manual review",
                extra={
                    "email_id": metadata.id,
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
