"""
Queue Service

Async service wrapper for QueueStorage operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from src.core.schemas import EmailAnalysis, EmailMetadata
from src.frontin.api.websocket.queue_events import QueueEventEmitter, get_queue_event_emitter
from src.integrations.email.processed_tracker import get_processed_tracker
from src.integrations.storage.action_history import (
    ActionHistoryStorage,
    ActionType,
    get_action_history,
)
from src.integrations.storage.queue_storage import QueueStorage, get_queue_storage
from src.integrations.storage.snooze_storage import (
    SnoozeReason,
    SnoozeRecord,
    SnoozeStorage,
    get_snooze_storage,
)
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("api.queue_service")


class EnrichmentFailedError(Exception):
    """Raised when required enrichments fail and operation is aborted."""

    def __init__(self, item_id: str, failed_enrichments: list[str], action: str):
        self.item_id = item_id
        self.failed_enrichments = failed_enrichments
        self.action = action
        super().__init__(
            f"Required enrichments failed for item {item_id}: {', '.join(failed_enrichments)}. "
            f"Action '{action}' aborted to prevent data loss."
        )


class QueueService:
    """Async service for queue operations"""

    def __init__(
        self,
        queue_storage: QueueStorage | None = None,
        snooze_storage: SnoozeStorage | None = None,
        action_history: ActionHistoryStorage | None = None,
        event_emitter: QueueEventEmitter | None = None,
    ):
        """
        Initialize queue service

        Args:
            queue_storage: Optional QueueStorage instance (uses singleton if None)
            snooze_storage: Optional SnoozeStorage instance (uses singleton if None)
            action_history: Optional ActionHistoryStorage instance (uses singleton if None)
            event_emitter: Optional QueueEventEmitter instance (uses singleton if None)
        """
        self._storage = queue_storage or get_queue_storage()
        self._snooze_storage = snooze_storage or get_snooze_storage()
        self._action_history = action_history or get_action_history()
        self._event_emitter = event_emitter or get_queue_event_emitter()

    async def list_items(
        self,
        account_id: str | None = None,
        status: str = "pending",
        state: str | None = None,
        tab: str | None = None,
        include_snoozed: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List queue items with pagination

        Args:
            account_id: Filter by account
            status: Filter by legacy status (pending, approved, rejected, skipped)
            state: v2.4 - Filter by state (queued, analyzing, awaiting_review, processed, error)
            tab: v2.4 - Filter by UI tab (to_process, in_progress, snoozed, history, errors)
            include_snoozed: v2.4 - Include snoozed items in results (default True)
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (items, total_count)
        """
        # v2.4: Use new filtering if state or tab is provided
        if state or tab:
            all_items = self._storage.load_queue_by_state(
                state=state,
                tab=tab,
                account_id=account_id,
                include_snoozed=include_snoozed,
            )
        else:
            # Legacy filtering by status
            all_items = self._storage.load_queue(account_id=account_id, status=status)

        total = len(all_items)

        # Bug #56 fix: Sort by appropriate field based on status/state/tab
        # - pending/awaiting_review/to_process: oldest first (by queued_at) - process oldest first
        # - approved/rejected/processed/history: newest first (by reviewed_at) - show most recent
        # - errors: newest first (by error timestamp)
        if status in ("approved", "rejected") or state == "processed" or tab == "history":
            # Sort by reviewed_at, newest first (reverse chronological)
            all_items.sort(
                key=lambda x: (
                    x.get("resolution", {}).get("resolved_at")
                    if x.get("resolution")
                    else x.get("reviewed_at")
                ) or x.get("queued_at", ""),
                reverse=True,
            )
        elif state == "error" or tab == "errors":
            # Sort errors by error timestamp, newest first
            all_items.sort(
                key=lambda x: (
                    x.get("error", {}).get("occurred_at")
                    if x.get("error")
                    else x.get("queued_at", "")
                ),
                reverse=True,
            )
        elif tab == "snoozed":
            # Sort snoozed by wake_at, soonest first
            all_items.sort(
                key=lambda x: (
                    x.get("snooze", {}).get("wake_at")
                    if x.get("snooze")
                    else ""
                ),
            )
        # else: pending/awaiting_review items keep the default sort (oldest first by queued_at)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        items = all_items[start:end]

        return items, total

    async def get_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Get single queue item

        Args:
            item_id: Queue item ID

        Returns:
            Queue item or None if not found
        """
        return self._storage.get_item(item_id)

    async def get_stats(self) -> dict[str, Any]:
        """
        Get queue statistics

        Returns:
            Dictionary with queue stats
        """
        return self._storage.get_stats()

    async def approve_item(
        self,
        item_id: str,
        modified_action: str | None = None,
        modified_category: str | None = None,
        destination: str | None = None,
        execute_enrichments: bool = True,
    ) -> dict[str, Any] | None:
        """
        Approve a queue item and execute enrichments + IMAP action atomically.

        Atomic Transaction Logic:
        1. Execute all required enrichments first
        2. If any required enrichment fails, abort (don't execute email action)
        3. Execute email action only after enrichments succeed
        4. Execute optional enrichments (best-effort, don't block)

        Args:
            item_id: Queue item ID
            modified_action: Override action (optional)
            modified_category: Override category (optional)
            destination: Destination folder (optional, uses option's destination if not provided)
            execute_enrichments: Whether to execute note enrichments (default True)

        Returns:
            Updated item or None if not found/failed
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Determine the action to execute
        action = modified_action or item.get("analysis", {}).get("action", "archive")

        # Use provided destination, or fall back to analysis destination
        dest = destination or item.get("analysis", {}).get("destination")

        # Get metadata for rollback
        metadata = item.get("metadata", {})
        original_folder = metadata.get("folder", "INBOX")
        email_id = metadata.get("id")

        # ATOMIC TRANSACTION: Execute required enrichments FIRST
        # For any action with proposed enrichments, we should capture the information.
        # Required enrichments MUST succeed before proceeding with archive/delete.
        enrichments_executed = []
        enrichments_failed = []

        if execute_enrichments:
            (
                enrichment_success,
                enrichments_executed,
                enrichments_failed,
            ) = await self._execute_enrichments(item, only_required=True)

            # Only abort for archive/delete if required enrichments fail
            # For other actions (flag, task, etc.), log warning but continue
            if not enrichment_success and action in ("archive", "delete", "ARCHIVE", "DELETE"):
                logger.error(
                    f"Required enrichments failed for item {item_id}, aborting",
                    extra={
                        "item_id": item_id,
                        "action": action,
                        "failed_enrichments": enrichments_failed,
                    },
                )
                # Update item with enrichment failure info
                self._storage.update_item(
                    item_id,
                    {
                        "enrichment_status": "failed",
                        "enrichment_error": f"Failed enrichments: {', '.join(enrichments_failed)}",
                    },
                )
                # Raise exception to signal failure - router will return 409 Conflict
                raise EnrichmentFailedError(
                    item_id=item_id,
                    failed_enrichments=enrichments_failed,
                    action=action,
                )
            elif not enrichment_success:
                # Non-blocking warning for other actions
                logger.warning(
                    f"Some enrichments failed for item {item_id}, continuing with action",
                    extra={"action": action, "failed": enrichments_failed},
                )

        # Execute the IMAP action (only after enrichments succeed)
        imap_success = await self._execute_email_action(item, action, dest)

        # Bug #52 fix: Only mark as approved if IMAP action succeeded
        # If IMAP fails, keep item in pending so user can retry
        if not imap_success:
            logger.error(
                f"IMAP action failed for item {item_id}, keeping in pending",
                extra={"item_id": item_id, "action": action, "email_id": email_id},
            )
            # Return None to signal failure - frontend will show error
            return None

        # Execute optional enrichments (best-effort, don't block on failures)
        if execute_enrichments:
            optional_success, opt_executed, opt_failed = await self._execute_enrichments(
                item,
                only_required=False,  # Execute ALL remaining enrichments
            )
            enrichments_executed.extend([e for e in opt_executed if e not in enrichments_executed])
            enrichments_failed.extend(opt_failed)

            if opt_failed:
                logger.warning(
                    f"Some optional enrichments failed for item {item_id}",
                    extra={"failed": opt_failed},
                )

        if email_id:
            # Record action in history for undo capability
            self._action_history.create_action(
                action_type=ActionType.QUEUE_APPROVE,
                item_id=item_id,
                item_type="email",
                action_data={
                    "action": action,
                    "destination": dest,
                    "subject": metadata.get("subject"),
                },
                rollback_data={
                    "original_folder": original_folder,
                    "email_id": email_id,
                    "destination": dest,
                    "action": action,
                },
                account_id=item.get("account_id"),
            )

        updates: dict[str, Any] = {
            "status": "approved",
            "reviewed_at": now_utc().isoformat(),
            "review_decision": "approve",
        }

        if modified_action:
            updates["modified_action"] = modified_action
        if modified_category:
            updates["modified_category"] = modified_category

        # Track enrichment results
        if enrichments_executed or enrichments_failed:
            updates["enrichment_status"] = "complete" if not enrichments_failed else "partial"
            updates["enrichments_executed"] = enrichments_executed
            updates["enrichments_failed"] = enrichments_failed

        success = self._storage.update_item(item_id, updates)
        if not success:
            return None

        # Bug #51: Log feedback for debugging and learning
        original_action = item.get("analysis", {}).get("action")
        original_confidence = item.get("analysis", {}).get("confidence")
        logger.info(
            "Feedback received: APPROVE",
            extra={
                "item_id": item_id,
                "feedback_type": "approve",
                "original_action": original_action,
                "executed_action": action,
                "action_modified": modified_action is not None,
                "original_confidence": original_confidence,
                "destination": dest,
                "subject": metadata.get("subject", "")[:50],
                "enrichments_executed": enrichments_executed,
                "enrichments_failed": enrichments_failed,
            },
        )

        # Bug #60 fix: Mark message_id as processed to prevent re-queueing
        message_id = metadata.get("message_id")
        if message_id:
            self._storage.mark_message_processed(message_id)

        # v2.4: Emit WebSocket events for real-time updates
        updated_item = self._storage.get_item(item_id)
        if updated_item:
            await self._emit_item_event(updated_item, changes=["status", "resolution"])

        return updated_item

    async def _execute_email_action(
        self,
        item: dict[str, Any],
        action: str,
        destination: str | None = None,
    ) -> bool:
        """
        Execute IMAP action for a queue item

        Args:
            item: Queue item data
            action: Action to execute (archive, delete, task, etc.)
            destination: Destination folder (optional)

        Returns:
            True if action executed successfully
        """
        # Run blocking IMAP operations in a thread to not block event loop
        return await asyncio.to_thread(self._execute_email_action_sync, item, action, destination)

    def _execute_email_action_sync(
        self,
        item: dict[str, Any],
        action: str,
        destination: str | None,
    ) -> bool:
        """Synchronous IMAP action execution (runs in thread pool)"""
        from src.core.config_manager import get_config
        from src.integrations.email.imap_client import IMAPClient

        metadata = item.get("metadata", {})
        email_id = metadata.get("id")
        folder = metadata.get("folder", "INBOX")
        message_id = metadata.get("message_id")
        subject = metadata.get("subject")
        from_address = metadata.get("from_address")

        if not email_id:
            logger.warning(f"No email ID in queue item {item.get('id')}")
            return False

        config = get_config()
        imap_client = IMAPClient(config.email)

        try:
            with imap_client.connect():
                # Bug #60 fix: Add gray flag FIRST to mark as processed
                # This prevents re-fetching even if the subsequent action fails
                # Also marks in local SQLite tracker for iCloud compatibility
                imap_client.add_flag(
                    msg_id=int(email_id),
                    folder=folder,
                    message_id=message_id,
                    subject=subject,
                    from_address=from_address,
                )

                if action in ("archive", "ARCHIVE"):
                    dest = destination or config.email.archive_folder or "Archive"
                    success = imap_client.move_email(
                        msg_id=int(email_id),
                        from_folder=folder,
                        to_folder=dest,
                    )
                    if success:
                        logger.info(f"Archived email {email_id} to {dest}")
                    return success

                elif action in ("delete", "DELETE"):
                    dest = destination or config.email.delete_folder or "Trash"
                    success = imap_client.move_email(
                        msg_id=int(email_id),
                        from_folder=folder,
                        to_folder=dest,
                    )
                    if success:
                        logger.info(f"Deleted email {email_id} to {dest}")
                    return success

                elif action in ("task", "TASK"):
                    # Task creation - move to archive after creating task
                    # TODO: Integrate with OmniFocus
                    dest = destination or config.email.archive_folder or "Archive"
                    success = imap_client.move_email(
                        msg_id=int(email_id),
                        from_folder=folder,
                        to_folder=dest,
                    )
                    if success:
                        logger.info(f"Archived email {email_id} after task action")
                    return success

                elif action in ("keep", "KEEP", "defer", "DEFER"):
                    # Bug #60 fix: Keep in inbox with gray flag so it won't be re-fetched
                    logger.info(f"Keep/defer action for email {email_id} - marked as processed")
                    return True

                elif action in ("flag", "FLAG"):
                    # Flag action - mark email as important/flagged but keep in inbox
                    # The gray flag was already added above, now add the flagged flag
                    try:
                        imap_client.add_flag(
                            msg_id=int(email_id),
                            flag="\\Flagged",
                            folder=folder,
                        )
                        logger.info(f"Flagged email {email_id} in {folder}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to add Flagged flag to email {email_id}: {e}")
                        # Still return True since the gray flag was added - email won't be re-fetched
                        return True

                elif action in ("rien", "RIEN", "none", "NONE"):
                    # No action needed - just mark as processed (gray flag already added)
                    logger.info(f"No action for email {email_id} - marked as processed")
                    return True

                else:
                    logger.warning(f"Unknown action: {action} for email {email_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to execute action {action} on email {email_id}: {e}")
            return False

    async def _execute_enrichments(
        self,
        item: dict[str, Any],
        only_required: bool = True,
    ) -> tuple[bool, list[str], list[str]]:
        """
        Execute note enrichments for a queue item.

        This executes all proposed_notes enrichments atomically. If any required
        enrichment fails, the entire operation is considered failed.

        Args:
            item: Queue item with analysis containing proposed_notes
            only_required: If True, only execute required enrichments

        Returns:
            Tuple of (success, executed_enrichments, failed_enrichments)
        """
        analysis = item.get("analysis", {})
        proposed_notes = analysis.get("proposed_notes", [])
        source_id = item.get("id", "unknown")

        if not proposed_notes:
            logger.debug(f"No proposed notes to execute for item {source_id}")
            return True, [], []

        # Filter to only required if specified
        if only_required:
            notes_to_execute = [n for n in proposed_notes if n.get("required", False)]
        else:
            notes_to_execute = proposed_notes

        if not notes_to_execute:
            logger.debug(
                f"No {'required ' if only_required else ''}notes to execute for item {source_id}"
            )
            return True, [], []

        # Execute enrichments
        executed = []
        failed = []

        for note_proposal in notes_to_execute:
            # Support both multi-pass format (title/content_summary) and old format (note_title/content)
            note_title = note_proposal.get("title") or note_proposal.get("note_title")
            content = note_proposal.get("content_summary") or note_proposal.get("content")
            note_type = note_proposal.get("note_type") or note_proposal.get("type", "fait")
            importance = note_proposal.get("importance", "moyenne")

            if not note_title or not content:
                logger.warning(
                    f"Skipping enrichment with missing title or content: {note_proposal}"
                )
                continue

            try:
                success = await self._execute_single_enrichment(
                    note_title=note_title,
                    content=content,
                    note_type=note_type,
                    importance=importance,
                    source_id=source_id,
                )

                if success:
                    executed.append(note_title)
                    logger.info(
                        f"Executed enrichment for note '{note_title}'",
                        extra={"note_type": note_type, "importance": importance},
                    )
                else:
                    failed.append(note_title)
                    logger.warning(f"Failed to enrich note '{note_title}'")

            except Exception as e:
                failed.append(note_title)
                logger.error(f"Error enriching note '{note_title}': {e}")

        # Check if any required enrichments failed
        has_required_failures = False
        for note_proposal in notes_to_execute:
            if note_proposal.get("required", False) and note_proposal.get("title") in failed:
                has_required_failures = True
                break

        overall_success = not has_required_failures

        logger.info(
            f"Enrichments complete: {len(executed)} executed, {len(failed)} failed, success={overall_success}",
            extra={"item_id": source_id, "executed": executed, "failed": failed},
        )

        return overall_success, executed, failed

    async def _execute_single_enrichment(
        self,
        note_title: str,
        content: str,
        note_type: str,
        importance: str,
        source_id: str,
    ) -> bool:
        """
        Execute a single note enrichment.

        Args:
            note_title: Title of the target note
            content: Information to add
            note_type: Type of information (fait, decision, engagement, etc.)
            importance: Importance level (haute, moyenne, basse)
            source_id: Source event ID for traceability

        Returns:
            True if successful
        """
        return await asyncio.to_thread(
            self._execute_single_enrichment_sync,
            note_title,
            content,
            note_type,
            importance,
            source_id,
        )

    def _execute_single_enrichment_sync(
        self,
        note_title: str,
        content: str,
        note_type: str,
        importance: str,
        source_id: str,
    ) -> bool:
        """Synchronous enrichment execution (runs in thread pool)"""
        from src.passepartout.note_manager import get_note_manager

        try:
            # Use singleton note manager (uses config path automatically)
            note_manager = get_note_manager()

            # CONSOLIDATION: Always search for existing note first (regardless of action)
            # This ensures we don't create duplicates like "Free Mobile Tarifs Maroc"
            # when a "Free Mobile" note already exists
            matching_note = None
            note_title_lower = note_title.lower().strip()

            # Strategy 1: Exact match using get_note_by_title (uses cache)
            matching_note = note_manager.get_note_by_title(note_title)

            # Strategy 2: If no exact match, find existing notes whose title is a prefix
            # e.g., "Free Mobile Tarifs Maroc" should match "Free Mobile"
            # OPTIMIZATION: Use lightweight summaries for searching, then load full note
            if not matching_note:
                candidate_summaries = []
                for summary in note_manager.get_notes_summary():
                    existing_title_lower = summary.get("title", "").lower().strip()
                    # Check if requested title starts with existing note title
                    # Minimum 3 chars to avoid matching too broadly (e.g., "A" or "Le")
                    if len(existing_title_lower) >= 3 and note_title_lower.startswith(
                        existing_title_lower
                    ):
                        candidate_summaries.append(summary)

                if candidate_summaries:
                    # Pick the note with the longest matching title (most specific match)
                    best_match = max(candidate_summaries, key=lambda s: len(s.get("title", "")))
                    matching_note = note_manager.get_note(best_match["note_id"])
                    if matching_note:
                        logger.info(
                            f"Fuzzy matched '{note_title}' to existing note '{matching_note.title}'",
                            extra={
                                "strategy": "prefix_match",
                                "matched_title": matching_note.title,
                            },
                        )

            if matching_note:
                # Note exists - add info to existing note
                logger.info(
                    f"Found existing note '{matching_note.title}', adding info",
                    extra={"note_id": matching_note.note_id, "note_type": note_type},
                )
                return note_manager.add_info(
                    note_id=matching_note.note_id,
                    info=content,
                    info_type=note_type,
                    importance=importance,
                    source_id=source_id,
                )
            else:
                # Note not found - create new note in appropriate PKM subfolder
                logger.info(
                    f"Note '{note_title}' not found, creating new note",
                    extra={"note_title": note_title, "note_type": note_type},
                )
                formatted_content = f"## {note_type.capitalize()}\n\n{content}"
                if importance:
                    formatted_content += f"\n\n**Importance**: {importance}"

                # Determine PKM subfolder based on note_type
                # People-related types go to Personnes
                # Events go to Réunions
                # Goals/objectives go to Projets
                # Everything else goes to Entités
                pkm_subfolder_map = {
                    "relation": "Personnes",
                    "coordonnees": "Personnes",
                    "competence": "Personnes",
                    "preference": "Personnes",
                    "evenement": "Réunions",
                    "objectif": "Projets",
                }
                subfolder_name = pkm_subfolder_map.get(note_type, "Entités")
                subfolder = f"Personal Knowledge Management/{subfolder_name}"

                note_id = note_manager.create_note(
                    title=note_title,
                    content=formatted_content,
                    tags=[note_type],
                    metadata={
                        "note_type": note_type,
                        "importance": importance,
                        "source_id": source_id,
                        "created_from": "email_enrichment",
                    },
                    subfolder=subfolder,
                )
                return bool(note_id)

        except Exception as e:
            logger.error(f"Failed to execute enrichment for '{note_title}': {e}", exc_info=True)
            return False

    async def modify_item(
        self,
        item_id: str,
        action: str,
        category: str | None = None,
        reasoning: str | None = None,
        destination: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Modify a queue item's action and execute it

        Args:
            item_id: Queue item ID
            action: New action to execute
            category: New category (optional)
            reasoning: Reason for modification
            destination: Destination folder (optional)

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Execute the modified action
        await self._execute_email_action(item, action, destination)

        updates: dict[str, Any] = {
            "status": "approved",  # Modified items are approved with new action
            "reviewed_at": now_utc().isoformat(),
            "review_decision": "modify",
            "modified_action": action,
        }

        if category:
            updates["modified_category"] = category
        if reasoning:
            updates["modification_reason"] = reasoning

        success = self._storage.update_item(item_id, updates)
        if not success:
            return None

        # Bug #51: Log feedback for debugging and learning
        original_action = item.get("analysis", {}).get("action")
        original_confidence = item.get("analysis", {}).get("confidence")
        metadata = item.get("metadata", {})
        logger.info(
            "Feedback received: MODIFY",
            extra={
                "item_id": item_id,
                "feedback_type": "modify",
                "original_action": original_action,
                "modified_action": action,
                "original_confidence": original_confidence,
                "modification_reason": reasoning,
                "destination": destination,
                "subject": metadata.get("subject", "")[:50],
            },
        )

        # Bug #60 fix: Mark message_id as processed to prevent re-queueing
        message_id = metadata.get("message_id")
        if message_id:
            self._storage.mark_message_processed(message_id)

        # v2.4: Emit WebSocket events for real-time updates
        updated_item = self._storage.get_item(item_id)
        if updated_item:
            await self._emit_item_event(updated_item, changes=["status", "modified_action"])

        return updated_item

    async def reject_item(
        self,
        item_id: str,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Reject a queue item (no action on email, unflag for potential reprocessing)

        Args:
            item_id: Queue item ID
            reason: Reason for rejection

        Returns:
            Updated item or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Optionally unflag the email so it can be reprocessed later
        # This is useful if the user wants to reconsider the email
        await self._unflag_email(item)

        updates: dict[str, Any] = {
            "status": "rejected",
            "reviewed_at": now_utc().isoformat(),
            "review_decision": "reject",
        }

        if reason:
            updates["rejection_reason"] = reason

        success = self._storage.update_item(item_id, updates)
        if not success:
            return None

        # Bug #51: Log feedback for debugging and learning
        original_action = item.get("analysis", {}).get("action")
        original_confidence = item.get("analysis", {}).get("confidence")
        metadata = item.get("metadata", {})
        logger.info(
            "Feedback received: REJECT",
            extra={
                "item_id": item_id,
                "feedback_type": "reject",
                "original_action": original_action,
                "original_confidence": original_confidence,
                "rejection_reason": reason,
                "subject": metadata.get("subject", "")[:50],
            },
        )

        # v2.4: Emit WebSocket events for real-time updates
        updated_item = self._storage.get_item(item_id)
        if updated_item:
            await self._emit_item_event(updated_item, changes=["status"])

        return updated_item

    async def _unflag_email(self, item: dict[str, Any]) -> bool:
        """
        Remove the flag from an email to allow reprocessing

        Args:
            item: Queue item data

        Returns:
            True if successful
        """
        # Run blocking IMAP operations in a thread to not block event loop
        return await asyncio.to_thread(self._unflag_email_sync, item)

    def _unflag_email_sync(self, item: dict[str, Any]) -> bool:
        """Synchronous unflag operation (runs in thread pool)"""
        from src.core.config_manager import get_config
        from src.integrations.email.imap_client import IMAPClient

        metadata = item.get("metadata", {})
        email_id = metadata.get("id")
        folder = metadata.get("folder", "INBOX")

        if not email_id:
            return False

        config = get_config()
        imap_client = IMAPClient(config.email)

        try:
            with imap_client.connect():
                return imap_client.remove_flag(
                    msg_id=int(email_id),
                    folder=folder,
                )
        except Exception as e:
            logger.warning(f"Failed to unflag email {email_id}: {e}")
            return False

    async def delete_item(self, item_id: str) -> bool:
        """
        Delete a queue item

        Args:
            item_id: Queue item ID

        Returns:
            True if deleted, False if not found
        """
        result = self._storage.remove_item(item_id)

        # v2.4: Emit WebSocket events for real-time updates
        if result:
            await self._event_emitter.emit_item_removed(item_id, reason="deleted")
            # Also emit stats update
            try:
                stats = self._storage.get_stats()
                await self._event_emitter.emit_stats_updated(stats)
            except Exception as e:
                logger.warning(f"Failed to emit stats update after delete: {e}")

        return result

    async def snooze_item(
        self,
        item_id: str,
        snooze_option: str,
        custom_hours: int | None = None,
        reason: str | None = None,
    ) -> SnoozeRecord | None:
        """
        Snooze a queue item

        Args:
            item_id: Queue item ID
            snooze_option: One of later_today, tomorrow, this_weekend, next_week, custom
            custom_hours: Hours to snooze (only for custom option)
            reason: Optional reason for snoozing

        Returns:
            SnoozeRecord or None if item not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        # Calculate snooze_until based on option
        now = now_utc()

        if snooze_option == "in_30_min":
            snooze_until = now + timedelta(minutes=30)
            snooze_reason = SnoozeReason.CUSTOM
        elif snooze_option == "in_2_hours" or snooze_option == "later_today":
            # 2 hours from now (Sprint 3 decision)
            snooze_until = now + timedelta(hours=2)
            snooze_reason = SnoozeReason.LATER_TODAY
        elif snooze_option == "tomorrow":
            # Tomorrow at 9 AM
            tomorrow = now + timedelta(days=1)
            snooze_until = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            snooze_reason = SnoozeReason.TOMORROW
        elif snooze_option == "this_weekend":
            # Saturday at 10 AM
            days_until_saturday = (5 - now.weekday()) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7  # If today is Saturday, go to next Saturday
            weekend = now + timedelta(days=days_until_saturday)
            snooze_until = weekend.replace(hour=10, minute=0, second=0, microsecond=0)
            snooze_reason = SnoozeReason.THIS_WEEKEND
        elif snooze_option == "next_week":
            # Next Monday at 9 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # If today is Monday, go to next Monday
            next_monday = now + timedelta(days=days_until_monday)
            snooze_until = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
            snooze_reason = SnoozeReason.NEXT_WEEK
        elif snooze_option == "custom" and custom_hours:
            snooze_until = now + timedelta(hours=custom_hours)
            snooze_reason = SnoozeReason.CUSTOM
        else:
            # Default to 3 hours
            snooze_until = now + timedelta(hours=3)
            snooze_reason = SnoozeReason.CUSTOM

        # Create snooze record
        record = self._snooze_storage.snooze_item(
            item_id=item_id,
            item_type="queue_item",
            snooze_until=snooze_until,
            reason=snooze_reason,
            reason_text=reason,
            original_data=item,
            account_id=item.get("account_id"),
        )

        # Update queue item status to snoozed
        self._storage.update_item(
            item_id,
            {
                "status": "snoozed",
                "snoozed_at": now.isoformat(),
                "snooze_until": snooze_until.isoformat(),
                "snooze_id": record.snooze_id,
            },
        )

        logger.info(
            f"Queue item snoozed: {item_id} until {snooze_until.isoformat()}",
            extra={"snooze_id": record.snooze_id, "snooze_option": snooze_option},
        )

        # v2.4: Emit WebSocket events for real-time updates
        updated_item = self._storage.get_item(item_id)
        if updated_item:
            await self._emit_item_event(updated_item, changes=["status", "snooze"])

        return record

    async def unsnooze_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Manually unsnooze a queue item

        Args:
            item_id: Queue item ID

        Returns:
            Updated queue item or None if not found
        """
        record = self._snooze_storage.unsnooze_item(item_id)
        if not record:
            return None

        # Update queue item status back to pending
        self._storage.update_item(
            item_id,
            {
                "status": "pending",
                "snoozed_at": None,
                "snooze_until": None,
                "snooze_id": None,
            },
        )

        # v2.4: Emit WebSocket events for real-time updates
        updated_item = self._storage.get_item(item_id)
        if updated_item:
            await self._emit_item_event(updated_item, changes=["status", "snooze"])

        return updated_item

    async def undo_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Undo an approved queue item action

        Moves the email back to its original folder and marks the queue item as pending.

        Args:
            item_id: Queue item ID

        Returns:
            Updated queue item or None if not found or cannot undo
        """
        # Find the last action for this item
        action_record = self._action_history.get_last_action_for_item(item_id)
        if not action_record:
            logger.warning(f"No action found to undo for item {item_id}")
            return None

        if not self._action_history.can_undo(action_record.action_id):
            logger.warning(f"Action {action_record.action_id} cannot be undone")
            return None

        rollback_data = action_record.rollback_data
        original_folder = rollback_data.get("original_folder", "INBOX")
        email_id = rollback_data.get("email_id")
        destination = rollback_data.get("destination")

        if not email_id or not destination:
            logger.warning(f"Missing rollback data for action {action_record.action_id}")
            return None

        # Execute the undo IMAP action (move back to original folder)
        success = await self._undo_email_action(email_id, destination, original_folder)

        if success:
            # Mark the action as undone
            self._action_history.mark_undone(
                action_record.action_id,
                undo_result={"moved_to": original_folder},
            )

            # Update queue item status back to pending
            self._storage.update_item(
                item_id,
                {
                    "status": "pending",
                    "reviewed_at": None,
                    "review_decision": None,
                    "undone_at": now_utc().isoformat(),
                },
            )

            logger.info(
                f"Undid action for queue item {item_id}",
                extra={"action_id": action_record.action_id, "moved_to": original_folder},
            )

            # v2.4: Emit WebSocket events for real-time updates
            updated_item = self._storage.get_item(item_id)
            if updated_item:
                await self._emit_item_event(updated_item, changes=["status", "undone"])

            return updated_item

        return None

    async def _undo_email_action(
        self,
        email_id: str,
        from_folder: str,
        to_folder: str,
    ) -> bool:
        """
        Move an email back to its original folder

        Args:
            email_id: Email UID
            from_folder: Current folder where email is
            to_folder: Target folder to move email back to

        Returns:
            True if successful
        """
        return await asyncio.to_thread(
            self._undo_email_action_sync, email_id, from_folder, to_folder
        )

    def _undo_email_action_sync(
        self,
        email_id: str,
        from_folder: str,
        to_folder: str,
    ) -> bool:
        """Synchronous undo IMAP operation (runs in thread pool)"""
        from src.core.config_manager import get_config
        from src.integrations.email.imap_client import IMAPClient

        config = get_config()
        imap_client = IMAPClient(config.email)

        try:
            with imap_client.connect():
                success = imap_client.move_email(
                    msg_id=int(email_id),
                    from_folder=from_folder,
                    to_folder=to_folder,
                )
                if success:
                    logger.info(f"Undid email {email_id}: moved from {from_folder} to {to_folder}")
                return success

        except Exception as e:
            logger.error(f"Failed to undo email action for {email_id}: {e}")
            return False

    async def can_undo_item(self, item_id: str) -> bool:
        """
        Check if a queue item's action can be undone

        Args:
            item_id: Queue item ID

        Returns:
            True if the item has a completed action that can be undone
        """
        action_record = self._action_history.get_last_action_for_item(item_id)
        if not action_record:
            return False
        return self._action_history.can_undo(action_record.action_id)

    async def reanalyze_item(
        self,
        item_id: str,
        user_instruction: str = "",
        mode: str = "immediate",
        force_model: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Reanalyze a queue item with user instruction

        Takes the user's custom instruction into account for the analysis.

        Args:
            item_id: Queue item ID
            user_instruction: User's instruction for reanalysis (optional)
            mode: 'immediate' (wait for result) or 'background' (queue for later)
            force_model: Force a specific model ('opus', 'sonnet', 'haiku') or None for auto

        Returns:
            Dict with status and new analysis, or None if not found
        """
        item = self._storage.get_item(item_id)
        if not item:
            return None

        metadata = item.get("metadata", {})
        content = item.get("content", {})

        # For immediate mode, run the reanalysis now
        if mode == "immediate":
            # Mark as in_progress during reanalysis
            original_status = item.get("status", "pending")
            self._storage.update_item(item_id, {"status": "in_progress"})

            new_analysis = await self._reanalyze_sync(
                metadata=metadata,
                content=content,
                user_instruction=user_instruction,
                force_model=force_model,
            )

            if new_analysis:
                # Save original analysis if first reanalysis
                if "original_analysis" not in item:
                    item["original_analysis"] = item.get("analysis", {})

                # Update item with new analysis
                item["analysis"] = new_analysis
                item["user_instruction"] = user_instruction
                item["reanalysis_count"] = item.get("reanalysis_count", 0) + 1

                # Update timestamps for re-analysis
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                if "timestamps" not in item:
                    item["timestamps"] = {}
                item["timestamps"]["analysis_completed_at"] = now.isoformat()
                item["timestamps"]["analysis_started_at"] = now.isoformat()

                # Restore to pending status after reanalysis
                item["status"] = "pending"

                self._storage.update_item(item_id, item)

                logger.info(
                    f"Reanalyzed queue item {item_id} with instruction",
                    extra={
                        "user_instruction": user_instruction[:50],
                        "new_action": new_analysis.get("action"),
                        "new_confidence": new_analysis.get("confidence"),
                    },
                )

                return {
                    "status": "complete",
                    "new_analysis": new_analysis,
                }

            # Reanalysis failed - restore original status
            self._storage.update_item(item_id, {"status": original_status})
            return {
                "status": "failed",
                "new_analysis": None,
            }

        # Background mode: just save the instruction and mark for reanalysis
        self._storage.update_item(
            item_id,
            {
                "pending_reanalysis": True,
                "user_instruction": user_instruction,
            },
        )

        return {
            "status": "queued",
            "analysis_id": f"reanalysis-{item_id}",
        }

    async def _reanalyze_sync(
        self,
        metadata: dict[str, Any],
        content: dict[str, Any],
        user_instruction: str,
        force_model: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Run reanalysis with user instruction using Multi-Pass v2.2.

        Args:
            metadata: Email metadata
            content: Email content
            user_instruction: User's instruction
            force_model: Force a specific model ('opus', 'sonnet', 'haiku') or None

        Returns:
            New analysis dict or None on failure
        """
        return await self._reanalyze_email_multi_pass(
            metadata,
            content,
            user_instruction,
            force_model,
        )

    async def _reanalyze_email_multi_pass(
        self,
        metadata: dict[str, Any],
        content: dict[str, Any],
        user_instruction: str,
        force_model: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Reanalysis using Multi-Pass v2.2 Analyzer.

        Uses the new MultiPassAnalyzer for intelligent multi-pass analysis
        with model escalation (Haiku -> Sonnet -> Opus).

        Args:
            metadata: Email metadata
            content: Email content
            user_instruction: User's instruction
            force_model: Force a specific model ('opus', 'sonnet', 'haiku') or None
        """
        from src.core.config_manager import get_config
        from src.passepartout.note_manager import get_note_manager
        from src.sancho.context_searcher import ContextSearcher
        from src.sancho.convergence import MultiPassConfig
        from src.sancho.model_selector import ModelTier
        from src.sancho.multi_pass_analyzer import MultiPassAnalyzer
        from src.sancho.router import get_ai_router

        try:
            config = get_config()
            ai_router = get_ai_router(config.ai)

            # Create adapter event for templates
            event = _create_email_event_adapter(metadata, content, user_instruction)

            # Build multi-pass config with optional forced model
            mp_config = MultiPassConfig()
            if force_model:
                model_map = {
                    "opus": ModelTier.OPUS,
                    "sonnet": ModelTier.SONNET,
                    "haiku": ModelTier.HAIKU,
                }
                mp_config.force_model = model_map.get(force_model.lower())
                logger.info(f"Reanalysis with forced model: {force_model}")

            # Use singleton NoteManager for PKM context
            note_manager = get_note_manager()

            # Create ContextSearcher for PKM context retrieval (v2.5 fix)
            context_searcher = ContextSearcher(
                note_manager=note_manager,
                cross_source_engine=None,  # No cross-source for reanalysis
            )

            # Create MultiPassAnalyzer with context search enabled
            analyzer = MultiPassAnalyzer(
                ai_router=ai_router,
                note_manager=note_manager,
                context_searcher=context_searcher,
                config=mp_config,
                enable_coherence_pass=True,
            )

            # Run multi-pass analysis
            result = await analyzer.analyze(event)

            # Convert MultiPassResult to expected dict format
            return self._multi_pass_result_to_dict(result)

        except Exception as e:
            logger.error(f"Failed to reanalyze email with multi-pass: {e}", exc_info=True)
            return None

    def _multi_pass_result_to_dict(self, result: Any) -> dict[str, Any]:
        """Convert MultiPassResult to queue analysis dict format."""
        # Debug: Log the result type and pass_history
        logger.info(
            f"Converting MultiPassResult: passes_count={result.passes_count}, "
            f"pass_history_len={len(result.pass_history) if result.pass_history else 0}, "
            f"final_model={result.final_model}"
        )

        # Build proposed_notes from extractions with note_cible
        proposed_notes = []
        proposed_tasks = []

        for ext in result.extractions:
            if ext.note_cible:
                # Map extraction to proposed_note format expected by router
                # Router expects: action, note_type, title, content_summary, confidence, reasoning
                proposed_notes.append(
                    {
                        "action": ext.note_action,  # "enrichir" or "creer"
                        "note_type": ext.type,  # fait, decision, engagement, deadline, etc.
                        "title": ext.note_cible,  # Target note title
                        "content_summary": ext.info,  # The extracted information
                        "confidence": ext.confidence.to_dict(),  # 4-dimension confidence dict
                        "reasoning": f"Extraction de type '{ext.type}' (importance: {ext.importance})",
                        "target_note_id": None,  # Would need lookup to find existing note
                        "required": ext.required,  # Required for safe archiving
                        "importance": ext.importance,  # haute, moyenne, basse
                    }
                )
            if ext.omnifocus:
                proposed_tasks.append(
                    {
                        "title": ext.info,
                        "due_date": ext.date,
                        "project": ext.note_cible,
                    }
                )

        # Build entities dict from entities_discovered
        # Format: {"type": [{"type": "...", "value": "...", "confidence": ...}, ...]}
        # The router expects entities grouped by type as lists
        entities: dict[str, list[dict[str, Any]]] = {}
        if result.entities_discovered:
            entities["discovered"] = [
                {"type": "discovered", "value": entity, "confidence": 1.0}
                for entity in result.entities_discovered
            ]

        # Get reasoning from last pass
        reasoning = ""
        if result.pass_history:
            last_pass = result.pass_history[-1]
            reasoning = getattr(last_pass, "reasoning", "") or ""

        # Build multi_pass metadata first for logging
        multi_pass_data = self._build_multi_pass_metadata(result)

        analysis_dict = {
            "action": result.action,
            "confidence": int(result.confidence.overall * 100),  # Convert to 0-100
            "category": None,  # Multi-pass doesn't use categories
            "reasoning": reasoning,
            "destination": None,  # Not used in multi-pass
            "summary": f"Multi-Pass analysis ({result.passes_count} passes, {result.final_model})",
            "entities": entities,
            "proposed_notes": proposed_notes,
            "proposed_tasks": proposed_tasks,
            "options": [],  # Multi-pass doesn't generate options
            # Coherence pass metadata
            "coherence_validated": result.coherence_validated,
            "coherence_corrections": result.coherence_corrections,
            "coherence_duplicates_detected": result.coherence_duplicates_detected,
            "coherence_confidence": result.coherence_confidence,
            "coherence_warnings": result.coherence_warnings,
            # Additional multi-pass metadata (v2.3: Analysis Transparency)
            "multi_pass": multi_pass_data,
            # v2.2.2: Context transparency
            "retrieved_context": result.retrieved_context,
            "context_influence": result.context_influence,
        }

        # Debug: Log the multi_pass result
        logger.info(
            f"Built analysis dict: multi_pass={'present' if multi_pass_data else 'None'}, "
            f"passes_count={multi_pass_data.get('passes_count') if multi_pass_data else 'N/A'}"
        )

        return analysis_dict

    def _build_multi_pass_metadata(self, result: Any) -> dict[str, Any] | None:
        """
        Build multi-pass metadata dict for API response (v2.3 Analysis Transparency).

        Includes:
        - passes_count, final_model, models_used
        - escalated, stop_reason, high_stakes
        - total_tokens, total_duration_ms
        - pass_history with per-pass details
        """
        # Check if result has pass_history
        if not hasattr(result, "pass_history") or not result.pass_history:
            logger.warning(
                "No pass_history in result, cannot build multi_pass metadata",
                extra={"result_type": type(result).__name__},
            )
            return None

        logger.info(
            f"Building multi_pass metadata with {len(result.pass_history)} passes",
            extra={
                "passes_count": result.passes_count,
                "final_model": result.final_model,
            },
        )

        # Build models_used list from pass_history
        models_used: list[str] = []
        pass_history: list[dict[str, Any]] = []

        prev_confidence = 0.0
        for i, pass_result in enumerate(result.pass_history):
            model = getattr(pass_result, "model_used", "unknown")
            models_used.append(model)

            # Determine if context was searched (refine passes search context)
            pass_type = getattr(pass_result, "pass_type", None)
            pass_type_value = pass_type.value if hasattr(pass_type, "value") else str(pass_type)
            context_searched = pass_type_value in ["refine", "deep"]

            # Count notes found from retrieved_context if available
            notes_found = 0
            if context_searched and result.retrieved_context:
                notes_found = len(result.retrieved_context.get("notes", []))

            # Get confidence after this pass
            confidence_after = getattr(pass_result, "confidence", None)
            if confidence_after and hasattr(confidence_after, "overall"):
                confidence_after = confidence_after.overall
            elif isinstance(confidence_after, (int, float)):
                pass  # Already a number
            else:
                confidence_after = 0.0

            # Determine if escalation was triggered by this pass
            # Escalation happens when moving from haiku to sonnet or sonnet to opus
            escalation_triggered = False
            if i > 0 and len(models_used) > 1:
                prev_model = models_used[i - 1]
                escalation_triggered = (
                    (prev_model == "haiku" and model in ["sonnet", "opus"])
                    or (prev_model == "sonnet" and model == "opus")
                )

            pass_history.append({
                "pass_number": getattr(pass_result, "pass_number", i + 1),
                "pass_type": pass_type_value,
                "model": model,
                "duration_ms": getattr(pass_result, "duration_ms", 0.0),
                "tokens": getattr(pass_result, "tokens_used", 0),
                "confidence_before": prev_confidence,
                "confidence_after": float(confidence_after) if confidence_after else 0.0,
                "context_searched": context_searched,
                "notes_found": notes_found,
                "escalation_triggered": escalation_triggered,
                # v2.3.1: Thinking Bubbles - Questions/doubts for next pass
                "questions": getattr(pass_result, "next_pass_questions", []),
            })

            prev_confidence = float(confidence_after) if confidence_after else prev_confidence

        return {
            "passes_count": result.passes_count,
            "final_model": result.final_model,
            "models_used": models_used,
            "escalated": result.escalated,
            "stop_reason": result.stop_reason,
            "high_stakes": result.high_stakes,
            "total_tokens": result.total_tokens,
            "total_duration_ms": result.total_duration_ms,
            "pass_history": pass_history,
        }

    async def reanalyze_all_pending(self) -> dict[str, Any]:
        """
        Reanalyze all pending queue items.

        Triggers a fresh AI analysis for all items in 'pending' status.
        Marks all items as in_progress immediately and returns,
        then runs analyses in the background.

        Returns:
            Dict with total count and status
        """
        import asyncio

        pending_items = self._storage.load_queue(status="pending")
        total = len(pending_items)

        if total == 0:
            return {"total": 0, "started": 0, "failed": 0, "status": "complete"}

        logger.info(f"Starting bulk reanalysis of {total} pending items")

        # Mark ALL items as in_progress upfront so UI shows correct count
        for item in pending_items:
            item_id = item.get("id")
            if item_id:
                self._storage.update_item(item_id, {"status": "in_progress"})

        # Launch background task for actual analysis
        asyncio.create_task(self._reanalyze_items_background(pending_items))

        # Return immediately with count
        return {
            "total": total,
            "started": total,  # All started (in background)
            "failed": 0,
            "status": "processing",
        }

    async def _reanalyze_items_background(self, items: list[dict[str, Any]]) -> None:
        """Background task to reanalyze items one by one."""
        total = len(items)
        started = 0
        failed = 0

        for item in items:
            item_id = item.get("id")
            if not item_id:
                failed += 1
                continue

            try:
                metadata = item.get("metadata", {})
                content = item.get("content", {})

                # Run reanalysis without user instruction
                new_analysis = await self._reanalyze_sync(
                    metadata=metadata,
                    content=content,
                    user_instruction="",  # No specific instruction
                )

                if new_analysis:
                    # Save original analysis if first reanalysis
                    if "original_analysis" not in item:
                        item["original_analysis"] = item.get("analysis", {})

                    # Update item with new analysis
                    item["analysis"] = new_analysis
                    item["reanalysis_count"] = item.get("reanalysis_count", 0) + 1

                    # Update timestamps for re-analysis
                    from datetime import datetime, timezone

                    now = datetime.now(timezone.utc)
                    if "timestamps" not in item:
                        item["timestamps"] = {}
                    item["timestamps"]["analysis_completed_at"] = now.isoformat()
                    item["timestamps"]["analysis_started_at"] = now.isoformat()

                    # Restore to pending status after reanalysis
                    item["status"] = "pending"

                    self._storage.update_item(item_id, item)
                    started += 1
                    logger.debug(f"Reanalyzed item {item_id}")
                else:
                    # Restore to pending status on failure
                    self._storage.update_item(item_id, {"status": "pending"})
                    failed += 1
                    logger.warning(f"Failed to reanalyze item {item_id}")

            except Exception as e:
                # Restore to pending status on error
                self._storage.update_item(item_id, {"status": "pending"})
                failed += 1
                logger.error(f"Error reanalyzing item {item_id}: {e}")

        logger.info(f"Bulk reanalysis complete: {started}/{total} succeeded, {failed} failed")

    async def enqueue_email(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis,
        content_preview: str,
        account_id: str = "default",
        html_body: str | None = None,
        full_text: str | None = None,
        multi_pass_data: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Enqueue an analyzed email for review.

        Also marks the email as processed in the local tracker to prevent
        re-fetching by the IMAP client.

        Args:
            metadata: Email metadata
            analysis: AI analysis results
            content_preview: Text preview
            account_id: Account ID
            html_body: HTML body (optional)
            full_text: Full text (optional)
            multi_pass_data: Multi-pass analysis transparency data (v2.3)

        Returns:
            Item ID if queued, None if duplicate or failed
        """
        # Save to queue storage (unblocking I/O)
        item_id = await asyncio.to_thread(
            self._storage.save_item,
            metadata=metadata,
            analysis=analysis,
            content_preview=content_preview,
            account_id=account_id,
            html_body=html_body,
            full_text=full_text,
            multi_pass_data=multi_pass_data,
        )

        if item_id:
            # Successfully queued - mark as processed in both trackers
            # 1. QueueStorage tracker (already done implicitly by save_item check,
            #    but we should mark it explicitly if not done)
            #    Actually save_item doesn't mark as processed, it only checks.
            #    We should mark it processed only after approval usually,
            #    BUT for preventing re-fetching we need to mark it now in the
            #    fetch tracker.

            # 2. IMAP fetch tracker (SQLite) - prevents re-fetching
            if metadata.message_id:
                try:
                    tracker = get_processed_tracker()
                    tracker.mark_processed(
                        message_id=metadata.message_id,
                        account_id=account_id,
                        subject=metadata.subject,
                        from_address=metadata.from_address,
                    )
                except Exception as e:
                    logger.warning(f"Failed to mark email as processed in tracker: {e}")

            logger.info(
                f"Enqueued email {item_id}",
                extra={
                    "subject": metadata.subject,
                    "confidence": analysis.confidence,
                    "action": analysis.action.value,
                },
            )

            # v2.4: Emit WebSocket events for real-time updates
            new_item = self._storage.get_item(item_id)
            if new_item:
                await self._event_emitter.emit_item_added(new_item)

        return item_id

    async def _emit_item_event(
        self,
        item: dict[str, Any],
        changes: list[str] | None = None,
        previous_state: str | None = None,
    ) -> None:
        """
        Helper to emit item update event and stats update.

        Args:
            item: The updated queue item
            changes: List of fields that changed
            previous_state: Previous state value
        """
        await self._event_emitter.emit_item_updated(item, changes, previous_state)

        # Also emit stats update since item changes affect stats
        try:
            stats = self._storage.get_stats()
            await self._event_emitter.emit_stats_updated(stats)
        except Exception as e:
            logger.warning(f"Failed to emit stats update: {e}")


class _EmailSender:
    """Adapter class for email sender info expected by templates."""

    def __init__(self, name: str, email: str):
        self.name = name
        self.display_name = name
        self.email = email


class _EmailEventAdapter:
    """
    Adapter to wrap email metadata/content for MultiPassAnalyzer templates.

    The Jinja2 templates expect specific attributes:
    - event.source_type (str)
    - event.timestamp (str)
    - event.sender.name, event.sender.email
    - event.title (str)
    - event.content (str)
    - event.entities (list)
    """

    def __init__(
        self,
        metadata: dict[str, Any],
        content: dict[str, Any],
        user_instruction: str = "",
    ):
        # Basic identification
        self.event_id = str(metadata.get("id", metadata.get("message_id", "unknown")))
        self.source_type = "email"

        # Timing - parse the date for age calculations
        date_str = metadata.get("date", now_utc().isoformat())
        self.timestamp = date_str

        # Parse date for age-aware analysis (MultiPassAnalyzer expects datetime)
        try:
            if isinstance(date_str, str):
                # Handle ISO format with timezone
                self.received_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                self.received_at = date_str
        except (ValueError, TypeError):
            self.received_at = now_utc()

        # occurred_at alias for event-style access
        self.occurred_at = self.received_at

        # Content - try full_text first, then preview, then html_body (strip HTML if needed)
        self.title = metadata.get("subject", "(No subject)")
        content_text = content.get("full_text") or content.get("preview") or ""

        # If still empty, try to extract text from html_body
        if not content_text and content.get("html_body"):
            # Simple HTML stripping (remove tags, decode entities)
            import html
            import re

            html_content = content.get("html_body", "")
            # Remove script/style tags and their content
            html_content = re.sub(
                r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE
            )
            # Remove HTML tags
            text = re.sub(r"<[^>]+>", " ", html_content)
            # Decode HTML entities
            text = html.unescape(text)
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text).strip()
            content_text = text[:10000]  # Limit to 10k chars

        if user_instruction:
            self.content = f"[User instruction: {user_instruction}]\n\n{content_text}"
        else:
            self.content = content_text

        # Sender
        sender_name = metadata.get("from_name", "") or metadata.get("from_address", "Unknown")
        sender_email = metadata.get("from_address", "")
        self.sender = _EmailSender(sender_name, sender_email)
        # Also expose from_person for compatibility with PerceivedEvent-style access
        self.from_person = sender_name

        # Entities (empty for reanalysis, will be discovered by pass 1)
        self.entities: list = []

        # Attachments
        self.has_attachments = metadata.get("has_attachments", False)
        self.attachments = metadata.get("attachments", [])

        # Thread info
        self.thread_id = metadata.get("thread_id")


def _create_email_event_adapter(
    metadata: dict[str, Any],
    content: dict[str, Any],
    user_instruction: str = "",
) -> _EmailEventAdapter:
    """
    Create an adapter that wraps email metadata/content for MultiPassAnalyzer.

    Args:
        metadata: Email metadata dict from queue item
        content: Email content dict from queue item
        user_instruction: Optional user instruction to include

    Returns:
        _EmailEventAdapter instance compatible with Jinja2 templates
    """
    return _EmailEventAdapter(metadata, content, user_instruction)


# Singleton instance
_service: QueueService | None = None


def get_queue_service() -> QueueService:
    """Get singleton QueueService instance"""
    global _service
    if _service is None:
        _service = QueueService()
    return _service
