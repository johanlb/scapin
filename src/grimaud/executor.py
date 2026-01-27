"""
Executor for Grimaud actions.

Applique les actions Grimaud au PKM avec creation de snapshots pour rollback.
"""

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.grimaud.history import GrimaudHistoryManager
from src.grimaud.models import GrimaudAction, GrimaudActionType, GrimaudSnapshot
from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.passepartout.note_manager import NoteManager

logger = get_logger("grimaud.executor")


class GrimaudExecutor:
    """
    Executeur d'actions Grimaud.

    Applique les actions au PKM en creant des snapshots avant modification
    pour permettre le rollback.
    """

    def __init__(
        self,
        note_manager: "NoteManager",
        history_manager: GrimaudHistoryManager,
    ):
        """
        Initialise l'executeur.

        Args:
            note_manager: Gestionnaire de notes pour les operations PKM
            history_manager: Gestionnaire d'historique pour les snapshots
        """
        self.note_manager = note_manager
        self.history_manager = history_manager

    def execute(self, action: GrimaudAction, dry_run: bool = False) -> bool:
        """
        Execute une action Grimaud.

        Args:
            action: Action a executer
            dry_run: Si True, simule l'execution sans modifier

        Returns:
            True si succes, False si erreur
        """
        if dry_run:
            logger.debug(
                "Dry run - action not executed",
                extra={"action_id": action.action_id, "type": action.action_type.value},
            )
            return True

        # Get the note
        note = self.note_manager.get_note(action.note_id)
        if not note:
            logger.warning(
                "Note not found for action",
                extra={"note_id": action.note_id, "action_id": action.action_id},
            )
            return False

        # Create snapshot before modification
        snapshot = GrimaudSnapshot(
            note_id=note.note_id,
            note_title=note.title,
            action_type=action.action_type,
            action_detail=action.reasoning,
            confidence=action.confidence,
            content_before=note.content,
            frontmatter_before=note.metadata.copy() if note.metadata else {},
            triggered_by="grimaud_executor",
        )
        self.history_manager.save_snapshot(snapshot)
        logger.debug(
            "Snapshot created",
            extra={"snapshot_id": snapshot.snapshot_id, "note_id": note.note_id},
        )

        # Apply action based on type
        success = False
        try:
            if action.action_type in (
                GrimaudActionType.ENRICHISSEMENT,
                GrimaudActionType.RESTRUCTURATION,
                GrimaudActionType.ENRICHISSEMENT_WEB,
            ):
                success = self._apply_content_update(action)

            elif action.action_type == GrimaudActionType.FUSION:
                success = self._apply_fusion(action)

            elif action.action_type == GrimaudActionType.LIAISON:
                success = self._apply_liaison(action, note.content)

            elif action.action_type in (
                GrimaudActionType.METADONNEES,
                GrimaudActionType.ARCHIVAGE,
            ):
                # Placeholder for future implementation
                logger.info(
                    "Placeholder action type - no modification",
                    extra={"action_type": action.action_type.value},
                )
                success = True

            else:
                logger.warning(
                    "Unknown action type",
                    extra={"action_type": action.action_type.value},
                )
                success = False

        except Exception as e:
            logger.exception(
                "Error executing action",
                extra={"action_id": action.action_id, "error": str(e)},
            )
            success = False

        # Mark action as applied if successful
        if success:
            action.applied = True
            action.applied_at = datetime.now(timezone.utc)
            logger.info(
                "Action executed successfully",
                extra={
                    "action_id": action.action_id,
                    "type": action.action_type.value,
                    "note_id": action.note_id,
                },
            )

        return success

    def _apply_content_update(self, action: GrimaudAction) -> bool:
        """
        Applique une mise a jour de contenu (enrichissement, restructuration).

        Args:
            action: Action avec new_content

        Returns:
            True si succes
        """
        if not action.new_content:
            logger.warning(
                "No new_content in action",
                extra={"action_id": action.action_id},
            )
            return False

        result = self.note_manager.update_note(
            action.note_id,
            content=action.new_content,
        )

        if result is False:
            logger.warning(
                "Failed to update note",
                extra={"note_id": action.note_id},
            )
            return False

        return True

    def _apply_fusion(self, action: GrimaudAction) -> bool:
        """
        Applique une fusion de notes.

        Met a jour la note cible avec le contenu fusionne,
        puis deplace la note source vers la corbeille.

        Args:
            action: Action de fusion avec target_note_id et new_content

        Returns:
            True si succes
        """
        if not action.target_note_id:
            logger.warning(
                "No target_note_id for fusion",
                extra={"action_id": action.action_id},
            )
            return False

        if not action.new_content:
            logger.warning(
                "No new_content for fusion",
                extra={"action_id": action.action_id},
            )
            return False

        # Update target note with merged content
        result = self.note_manager.update_note(
            action.target_note_id,
            content=action.new_content,
        )

        if result is False:
            logger.warning(
                "Failed to update target note for fusion",
                extra={"target_note_id": action.target_note_id},
            )
            return False

        # Move source note to trash
        delete_result = self.note_manager.delete_note(action.note_id)
        if not delete_result:
            logger.warning(
                "Failed to delete source note after fusion",
                extra={"note_id": action.note_id},
            )
            # Still consider success if target was updated
            # The source note remains but target has merged content

        logger.info(
            "Fusion completed",
            extra={
                "source_note": action.note_id,
                "target_note": action.target_note_id,
            },
        )
        return True

    def _apply_liaison(self, action: GrimaudAction, current_content: str) -> bool:
        """
        Applique une liaison entre notes (ajoute wikilink).

        Ajoute un lien vers la note cible dans la section "Voir aussi".
        Cree la section si elle n'existe pas.

        Args:
            action: Action de liaison avec target_note_title
            current_content: Contenu actuel de la note

        Returns:
            True si succes
        """
        if not action.target_note_title:
            logger.warning(
                "No target_note_title for liaison",
                extra={"action_id": action.action_id},
            )
            return False

        wikilink = f"[[{action.target_note_title}]]"

        # Check if link already exists
        if wikilink in current_content:
            logger.info(
                "Link already exists in note",
                extra={"note_id": action.note_id, "link": wikilink},
            )
            return True

        # Add link to "Voir aussi" section
        new_content = self._add_to_voir_aussi(current_content, wikilink)

        result = self.note_manager.update_note(
            action.note_id,
            content=new_content,
        )

        if result is False:
            logger.warning(
                "Failed to add link to note",
                extra={"note_id": action.note_id},
            )
            return False

        return True

    def _add_to_voir_aussi(self, content: str, wikilink: str) -> str:
        """
        Ajoute un wikilink a la section "Voir aussi".

        Cree la section si elle n'existe pas.

        Args:
            content: Contenu actuel
            wikilink: Lien a ajouter (ex: "[[Note Title]]")

        Returns:
            Contenu mis a jour
        """
        # Pattern to find "Voir aussi" section (case insensitive)
        voir_aussi_pattern = re.compile(
            r"(##\s*Voir\s+aussi\s*\n)(.*?)(?=\n##|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        match = voir_aussi_pattern.search(content)

        if match:
            # Section exists - append link
            section_header = match.group(1)
            section_content = match.group(2)
            new_section = f"{section_header}{section_content.rstrip()}\n- {wikilink}\n"
            return content[: match.start()] + new_section + content[match.end() :]
        else:
            # Section doesn't exist - create it at the end
            return f"{content.rstrip()}\n\n## Voir aussi\n\n- {wikilink}\n"

    def rollback(self, snapshot_id: str) -> bool:
        """
        Annule une action en restaurant le contenu depuis un snapshot.

        Args:
            snapshot_id: ID du snapshot a restaurer

        Returns:
            True si succes, False si snapshot non trouve
        """
        snapshot = self.history_manager.get_snapshot(snapshot_id)
        if not snapshot:
            logger.warning(
                "Snapshot not found for rollback",
                extra={"snapshot_id": snapshot_id},
            )
            return False

        # Restore note content
        result = self.note_manager.update_note(
            snapshot.note_id,
            content=snapshot.content_before,
        )

        if result is False:
            logger.warning(
                "Failed to restore note content",
                extra={"note_id": snapshot.note_id, "snapshot_id": snapshot_id},
            )
            return False

        # Delete the snapshot
        self.history_manager.delete_snapshot(snapshot_id)

        logger.info(
            "Rollback completed",
            extra={
                "snapshot_id": snapshot_id,
                "note_id": snapshot.note_id,
            },
        )
        return True
