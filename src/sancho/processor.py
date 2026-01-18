"""
Sancho Note Processor

Orchestrates the cognitive analysis and execution of proposals for notes.
Bridge between BackgroundWorker (Perception) and NoteManager (Execution).
"""

from typing import Any, Optional

from src.core.config_manager import get_config
from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager
from src.sancho.router import AIRouter, NoteAnalysis, NoteMetadata

logger = get_logger("sancho.processor")


class NoteProcessor:
    """
    Processor for AI-driven note analysis and enrichment.
    """

    def __init__(
        self,
        note_manager: NoteManager,
        ai_router: Optional[AIRouter] = None,
    ):
        """
        Initialize Note Processor.

        Args:
            note_manager: NoteManager instance for data access
            ai_router: AIRouter instance (creates default if None)
        """
        self.note_manager = note_manager

        if ai_router:
            self.ai_router = ai_router
        else:
            config = get_config()
            self.ai_router = AIRouter(config.ai)

    async def process_note(self, note_id: str) -> bool:
        """
        Process a single note: Analyze and apply proposals.

        Args:
            note_id: ID of the note to process

        Returns:
            True if processing resulted in changes, False otherwise
        """
        logger.info(f"Processing note for cognitive analysis: {note_id}")

        # 1. Retrieve Note
        note = self.note_manager.get_note(note_id)
        if not note:
            logger.warning(f"Note not found: {note_id}")
            return False

        # 2. Analyze Note
        try:
            analysis = await self.ai_router.analyze_note_async(
                note, NoteMetadata(note_id=note.note_id)
            )
            if not analysis:
                logger.warning(f"Analysis returned None for note {note_id}")
                return False

            logger.info(
                f"Analysis completed for {note_id}",
                extra={
                    "confidence": analysis.confidence,
                    "category": analysis.category,
                    "proposals_count": len(analysis.proposed_notes)
                    if analysis.proposed_notes
                    else 0,
                },
            )

        except Exception as e:
            logger.error(f"Failed to analyze note {note_id}: {e}", exc_info=True)
            return False

        # 3. Apply Results
        changes_made = await self._apply_analysis_results(analysis, note_id)

        return changes_made

    async def _apply_analysis_results(self, analysis: NoteAnalysis, source_note_id: str) -> bool:
        """
        Apply proposals from analysis if they meet confidence thresholds.

        Args:
            analysis: Analysis result
            source_note_id: ID of the source note

        Returns:
            True if any changes were applied
        """
        changes_applied = False

        # Apply Proposed Notes (Creation or Enrichment)
        if analysis.proposed_notes:
            for proposal in analysis.proposed_notes:
                try:
                    applied = self._apply_single_proposal(proposal, source_note_id)
                    if applied:
                        changes_applied = True
                except Exception as e:
                    logger.error(
                        f"Failed to apply proposal for {source_note_id}: {e}",
                        exc_info=True,
                        extra={"proposal": proposal},
                    )

        # Apply Proposed Tasks (Log only for now, similar to EmailProcessor)
        if analysis.proposed_tasks:
            for task in analysis.proposed_tasks:
                logger.info(
                    "Proposed task (not yet implemented)",
                    extra={"task": task, "source_note_id": source_note_id},
                )

        return changes_applied

    def _apply_single_proposal(self, proposal: dict[str, Any], source_note_id: str) -> bool:
        """
        Apply a single note proposal.

        Args:
            proposal: Dictionary containing proposal details
            source_note_id: ID of the source note

        Returns:
            True if applied
        """
        action = proposal.get("action", "").lower()
        confidence = float(proposal.get("confidence", 0.0))
        target_note_id = proposal.get("target_note_id")  # May be None for creation
        title = proposal.get("title", "")

        # Threshold for auto-application
        # TODO: Make configurable
        AUTO_APPLY_THRESHOLD = 0.85

        if confidence < AUTO_APPLY_THRESHOLD:
            logger.info(
                f"Skipping proposal due to low confidence ({confidence} < {AUTO_APPLY_THRESHOLD})",
                extra={"proposal": proposal},
            )
            return False

        if action == "create":
            return self._handle_create_proposal(proposal, source_note_id)
        elif action == "enrich":
            return self._handle_enrich_proposal(proposal, source_note_id)
        else:
            logger.warning(f"Unknown action in proposal: {action}")
            return False

    def _handle_create_proposal(self, proposal: dict[str, Any], source_note_id: str) -> bool:
        """Handle creating a new note from proposal."""
        title = proposal.get("title")
        content = proposal.get("content")

        if not title or not content:
            logger.warning("Cannot create note: missing title or content")
            return False

        # Check if note already exists by title to prevent duplicates
        existing = self.note_manager.get_note_by_title(title)
        if existing:
            logger.info(f"Note '{title}' already exists, switching to enrich")
            # Fallback to enrichment if supported by logic, or just skip
            # For now, let's treat it as a skip to avoid overwriting or confused state
            return False

        try:
            new_note_id = self.note_manager.create_note(
                title=title,
                content=content,
                tags=proposal.get("tags", []),
                metadata={"source_event": source_note_id},
            )
            logger.info(f"Auto-created note: {new_note_id} from {source_note_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create note '{title}': {e}")
            return False

    def _handle_enrich_proposal(self, proposal: dict[str, Any], source_note_id: str) -> bool:
        """Handle enriching an existing note."""
        target_id = proposal.get("target_note_id")
        # If target_id not provided, try to find by title?
        # The prompt asks for target_note_id if known.

        if not target_id:
            # Try finding by title if available
            title = proposal.get("title")
            if title:
                existing = self.note_manager.get_note_by_title(title)
                if existing:
                    target_id = existing.note_id

            if not target_id:
                logger.warning("Cannot enrich: missing target_note_id and title not found")
                return False

        info = proposal.get("content")  # Use content as the info to add
        # Or maybe the prompt returns 'reasoning' or specific field?
        # Looking at prompt: "action": "enrich", "target_note_id": "...", "content": "The new info to add"

        if not info:
            logger.warning("Cannot enrich: missing content/info")
            return False

        # Use add_info
        # We need info_type and importance. Proposal might not have them?
        # The analysis template asks for: action, title, content, target_note_id, confidence.
        # It doesn't explicitly ask for info_type/importance for enrichment.
        # I'll default them for now or infer if possible.

        info_type = proposal.get("type", "fait")  # Default to 'fait'
        importance = proposal.get("importance", "moyenne")

        try:
            success = self.note_manager.add_info(
                note_id=target_id,
                info=info,
                info_type=info_type,
                importance=importance,
                source_id=source_note_id,
            )
            if success:
                logger.info(f"Auto-enriched note {target_id} from {source_note_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to enrich note {target_id}: {e}")
            return False
