"""
Retouche Action Service

Service layer for retouche lifecycle action approval/rejection.
Handles pending actions from the Filage workflow.
"""

import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.core.config_manager import ScapinConfig
from src.frontin.api.models.retouche import (
    ActionResultResponse,
    BatchApproveResponse,
    NoteLifecycleStatusResponse,
    PendingRetoucheActionResponse,
    RetoucheActionType,
    RetoucheQueueResponse,
    RollbackResultResponse,
)
from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager
from src.passepartout.note_metadata import NoteMetadataStore

logger = get_logger("frontin.api.services.retouche_action")


@dataclass
class RetoucheActionService:
    """
    Service for retouche lifecycle action management

    Handles approval/rejection of pending retouche actions from the Filage,
    including FLAG_OBSOLETE, MERGE_INTO, and MOVE_TO_FOLDER actions.
    """

    config: ScapinConfig
    _metadata_store: NoteMetadataStore | None = field(default=None, init=False)
    _note_manager: NoteManager | None = field(default=None, init=False)
    # In-memory rollback history (token -> action data)
    _rollback_history: dict[str, dict] = field(default_factory=dict, init=False)

    def _get_store(self) -> NoteMetadataStore:
        """Get or create NoteMetadataStore instance"""
        if self._metadata_store is None:
            data_dir = self.config.storage.database_path.parent
            db_path = data_dir / "notes_meta.db"
            self._metadata_store = NoteMetadataStore(db_path)
        return self._metadata_store

    def _get_note_manager(self) -> NoteManager:
        """Get or create NoteManager instance"""
        if self._note_manager is None:
            data_dir = self.config.storage.database_path.parent
            db_path = data_dir / "notes_cache.db"
            self._note_manager = NoteManager(db_path)
        return self._note_manager

    async def get_pending_actions(self) -> RetoucheQueueResponse:
        """
        Get all pending retouche actions awaiting approval

        Returns:
            Queue of pending actions with counts by type
        """
        store = self._get_store()
        note_manager = self._get_note_manager()

        notes_with_pending = store.get_notes_with_pending_actions(limit=100)

        actions: list[PendingRetoucheActionResponse] = []
        by_type: dict[str, int] = {}

        for meta in notes_with_pending:
            note = note_manager.get_note(meta.note_id)
            note_title = note.title if note else meta.note_id
            note_path = note.path if note else ""

            for action_data in meta.pending_actions:
                action_type = action_data.get("type", "unknown")
                by_type[action_type] = by_type.get(action_type, 0) + 1

                # Parse created_at if present
                created_at_str = action_data.get("created_at")
                created_at = None
                if created_at_str:
                    with contextlib.suppress(ValueError, TypeError):
                        created_at = datetime.fromisoformat(created_at_str)

                action = PendingRetoucheActionResponse(
                    action_id=action_data.get("id", ""),
                    note_id=meta.note_id,
                    note_title=note_title,
                    note_path=note_path,
                    action_type=RetoucheActionType(action_type),
                    confidence=action_data.get("confidence", 0.0),
                    reasoning=action_data.get("reasoning", ""),
                    target_note_id=action_data.get("target_note_id"),
                    target_note_title=action_data.get("target_note_title"),
                    target_folder=action_data.get("target_folder"),
                    created_at=created_at,
                )
                actions.append(action)

        logger.info(f"Retrieved {len(actions)} pending retouche actions")

        return RetoucheQueueResponse(
            pending_actions=actions,
            total_count=len(actions),
            by_type=by_type,
        )

    async def approve_action(
        self,
        action_id: str,
        note_id: str,
        apply_immediately: bool = True,
        custom_params: dict | None = None,
    ) -> ActionResultResponse:
        """
        Approve a pending retouche action

        Args:
            action_id: ID of the action to approve
            note_id: ID of the note
            apply_immediately: Whether to apply the action now
            custom_params: Optional custom parameters (e.g., different target)

        Returns:
            Result of the approval
        """
        store = self._get_store()
        note_manager = self._get_note_manager()

        metadata = store.get(note_id)
        if metadata is None:
            return ActionResultResponse(
                success=False,
                action_id=action_id,
                note_id=note_id,
                action_type="unknown",
                message="Note non trouvée",
                applied=False,
            )

        # Find the action
        action_data = None
        for a in metadata.pending_actions:
            if a.get("id") == action_id:
                action_data = a
                break

        if action_data is None:
            return ActionResultResponse(
                success=False,
                action_id=action_id,
                note_id=note_id,
                action_type="unknown",
                message="Action non trouvée",
                applied=False,
            )

        action_type = action_data.get("type", "unknown")

        if apply_immediately:
            # Apply the action
            result = await self._apply_action(
                note_id, action_data, note_manager, store, custom_params
            )

            if result["success"]:
                # Remove from pending
                store.clear_pending_action(note_id, action_id)

                # Generate rollback token if applicable
                rollback_token = None
                rollback_available = False
                if action_type in ("flag_obsolete", "merge_into"):
                    rollback_token = str(uuid.uuid4())
                    rollback_available = True
                    self._rollback_history[rollback_token] = {
                        "action_id": action_id,
                        "note_id": note_id,
                        "action_type": action_type,
                        "action_data": action_data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                return ActionResultResponse(
                    success=True,
                    action_id=action_id,
                    note_id=note_id,
                    action_type=action_type,
                    message=result["message"],
                    applied=True,
                    rollback_available=rollback_available,
                    rollback_token=rollback_token,
                )
            else:
                return ActionResultResponse(
                    success=False,
                    action_id=action_id,
                    note_id=note_id,
                    action_type=action_type,
                    message=result["message"],
                    applied=False,
                )
        else:
            # Just mark as approved but don't apply yet
            action_data["approved"] = True
            action_data["approved_at"] = datetime.now(timezone.utc).isoformat()
            store.save(metadata)

            return ActionResultResponse(
                success=True,
                action_id=action_id,
                note_id=note_id,
                action_type=action_type,
                message="Action approuvée, sera appliquée ultérieurement",
                applied=False,
            )

    async def reject_action(
        self,
        action_id: str,
        note_id: str,
        reason: str | None = None,
        suppress_future: bool = False,
    ) -> ActionResultResponse:
        """
        Reject a pending retouche action

        Args:
            action_id: ID of the action to reject
            note_id: ID of the note
            reason: Optional reason for rejection
            suppress_future: Whether to suppress similar suggestions

        Returns:
            Result of the rejection
        """
        store = self._get_store()

        metadata = store.get(note_id)
        if metadata is None:
            return ActionResultResponse(
                success=False,
                action_id=action_id,
                note_id=note_id,
                action_type="unknown",
                message="Note non trouvée",
                applied=False,
            )

        # Find the action
        action_data = None
        for a in metadata.pending_actions:
            if a.get("id") == action_id:
                action_data = a
                break

        if action_data is None:
            return ActionResultResponse(
                success=False,
                action_id=action_id,
                note_id=note_id,
                action_type="unknown",
                message="Action non trouvée",
                applied=False,
            )

        action_type = action_data.get("type", "unknown")

        # Remove from pending
        store.clear_pending_action(note_id, action_id)

        # Log rejection for learning
        logger.info(
            f"Rejected action {action_id} ({action_type}) for note {note_id}",
            extra={
                "reason": reason,
                "suppress_future": suppress_future,
                "action_data": action_data,
            },
        )

        # TODO: If suppress_future, store preference to avoid similar suggestions

        return ActionResultResponse(
            success=True,
            action_id=action_id,
            note_id=note_id,
            action_type=action_type,
            message="Action rejetée",
            applied=False,
        )

    async def rollback_action(
        self,
        rollback_token: str,
        note_id: str,
    ) -> RollbackResultResponse:
        """
        Rollback a previously applied action

        Args:
            rollback_token: Token from the approve response
            note_id: ID of the note

        Returns:
            Result of the rollback
        """
        if rollback_token not in self._rollback_history:
            return RollbackResultResponse(
                success=False,
                note_id=note_id,
                action_type="unknown",
                message="Token de rollback invalide ou expiré",
            )

        rollback_data = self._rollback_history[rollback_token]
        if rollback_data["note_id"] != note_id:
            return RollbackResultResponse(
                success=False,
                note_id=note_id,
                action_type="unknown",
                message="Le token ne correspond pas à cette note",
            )

        action_type = rollback_data["action_type"]
        store = self._get_store()
        metadata = store.get(note_id)

        if metadata is None:
            return RollbackResultResponse(
                success=False,
                note_id=note_id,
                action_type=action_type,
                message="Note non trouvée",
            )

        # Rollback based on action type
        if action_type == "flag_obsolete":
            metadata.obsolete_flag = False
            metadata.obsolete_reason = ""
            store.save(metadata)
            message = "Marqueur obsolète retiré"
        elif action_type == "merge_into":
            # For merge, we can only restore the merge_target_id
            # The actual content merge cannot be undone without backup
            metadata.merge_target_id = None
            store.save(metadata)
            message = "Fusion annulée (contenu non restauré)"
        else:
            return RollbackResultResponse(
                success=False,
                note_id=note_id,
                action_type=action_type,
                message=f"Rollback non supporté pour {action_type}",
            )

        # Remove from history
        del self._rollback_history[rollback_token]

        logger.info(f"Rolled back {action_type} for note {note_id}")

        return RollbackResultResponse(
            success=True,
            note_id=note_id,
            action_type=action_type,
            message=message,
        )

    async def batch_approve(
        self,
        action_ids: list[str],
        note_ids: list[str],
    ) -> BatchApproveResponse:
        """
        Approve multiple pending actions at once

        Args:
            action_ids: List of action IDs to approve
            note_ids: Corresponding note IDs

        Returns:
            Batch result with individual outcomes
        """
        if len(action_ids) != len(note_ids):
            return BatchApproveResponse(
                success=False,
                approved_count=0,
                failed_count=len(action_ids),
                results=[],
            )

        results: list[ActionResultResponse] = []
        approved = 0
        failed = 0

        for action_id, note_id in zip(action_ids, note_ids, strict=False):
            result = await self.approve_action(
                action_id=action_id,
                note_id=note_id,
                apply_immediately=True,
            )
            results.append(result)
            if result.success:
                approved += 1
            else:
                failed += 1

        return BatchApproveResponse(
            success=failed == 0,
            approved_count=approved,
            failed_count=failed,
            results=results,
        )

    async def get_note_lifecycle_status(
        self,
        note_id: str,
    ) -> NoteLifecycleStatusResponse | None:
        """
        Get lifecycle status for a note

        Args:
            note_id: Note identifier

        Returns:
            Lifecycle status or None if note not found
        """
        store = self._get_store()
        note_manager = self._get_note_manager()

        metadata = store.get(note_id)
        if metadata is None:
            return None

        merge_target_title = None
        if metadata.merge_target_id:
            target_note = note_manager.get_note(metadata.merge_target_id)
            if target_note:
                merge_target_title = target_note.title

        return NoteLifecycleStatusResponse(
            note_id=note_id,
            obsolete_flag=metadata.obsolete_flag,
            obsolete_reason=metadata.obsolete_reason,
            merge_target_id=metadata.merge_target_id,
            merge_target_title=merge_target_title,
            pending_actions_count=len(metadata.pending_actions),
            quality_score=metadata.quality_score,
        )

    async def _apply_action(
        self,
        note_id: str,
        action_data: dict,
        note_manager: NoteManager,
        store: NoteMetadataStore,
        custom_params: dict | None = None,
    ) -> dict:
        """
        Apply a retouche action to a note

        Args:
            note_id: Note identifier
            action_data: Action configuration
            note_manager: NoteManager instance
            store: Metadata store
            custom_params: Optional custom parameters

        Returns:
            Result dict with success and message
        """
        action_type = action_data.get("type", "unknown")
        metadata = store.get(note_id)

        if metadata is None:
            return {"success": False, "message": "Note non trouvée"}

        try:
            if action_type == "flag_obsolete":
                metadata.obsolete_flag = True
                metadata.obsolete_reason = action_data.get("reasoning", "Marqué obsolète par IA")
                metadata.updated_at = datetime.now(timezone.utc)
                store.save(metadata)
                return {"success": True, "message": "Note marquée comme obsolète"}

            elif action_type == "merge_into":
                target_id = custom_params.get("target_note_id") if custom_params else None
                if not target_id:
                    target_id = action_data.get("target_note_id")

                if not target_id:
                    return {"success": False, "message": "Note cible non spécifiée"}

                # Verify target exists
                target_note = note_manager.get_note(target_id)
                if target_note is None:
                    return {"success": False, "message": "Note cible non trouvée"}

                # Mark for merge (actual merge is handled by Passepartout)
                metadata.merge_target_id = target_id
                metadata.updated_at = datetime.now(timezone.utc)
                store.save(metadata)
                return {
                    "success": True,
                    "message": f"Fusion programmée vers '{target_note.title}'",
                }

            elif action_type == "move_to_folder":
                target_folder = custom_params.get("target_folder") if custom_params else None
                if not target_folder:
                    target_folder = action_data.get("target_folder")

                if not target_folder:
                    return {"success": False, "message": "Dossier cible non spécifié"}

                # Move the note (via NoteManager)
                note = note_manager.get_note(note_id)
                if note is None:
                    return {"success": False, "message": "Note non trouvée"}

                # Update path
                note_manager.move_note(note_id, target_folder)
                return {
                    "success": True,
                    "message": f"Note déplacée vers '{target_folder}'",
                }

            else:
                return {"success": False, "message": f"Type d'action inconnu: {action_type}"}

        except Exception as e:
            logger.error(f"Failed to apply action {action_type}: {e}")
            return {"success": False, "message": f"Erreur: {e!s}"}
