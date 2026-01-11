"""
PKM Enricher — Knowledge Application

Applique les extractions de l'analyse au PKM (Personal Knowledge Management).

Ce module implémente la phase d'application du Workflow v2.1 :
1. Pour chaque extraction, trouve ou crée la note cible
2. Ajoute l'information à la note appropriée
3. Crée les tâches OmniFocus si nécessaire
4. Retourne un rapport d'enrichissement

Usage:
    enricher = PKMEnricher(note_manager, omnifocus_client)
    result = await enricher.apply(analysis_result, source_event_id)
"""

from typing import Optional

from src.core.models.v2_models import (
    AnalysisResult,
    EnrichmentResult,
    Extraction,
    NoteAction,
    NoteResult,
)
from src.integrations.apple.omnifocus import OmniFocusClient, OmniFocusError
from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager

logger = get_logger("enricher")


class EnricherError(Exception):
    """Base exception for enricher errors"""

    pass


class PKMEnricher:
    """
    Applique les extractions au PKM.

    Prend un AnalysisResult et applique chaque extraction à la note
    cible correspondante. Gère également la création de tâches OmniFocus.

    Attributes:
        note_manager: Gestionnaire de notes pour les opérations CRUD
        omnifocus_client: Client OmniFocus (optionnel)
        omnifocus_enabled: Si True, crée les tâches OmniFocus

    Example:
        >>> enricher = PKMEnricher(note_manager, omnifocus_client)
        >>> result = await enricher.apply(analysis_result, "email_123")
        >>> if result.success:
        ...     print(f"Updated {result.total_notes_affected} notes")
    """

    def __init__(
        self,
        note_manager: NoteManager,
        omnifocus_client: Optional[OmniFocusClient] = None,
        omnifocus_enabled: bool = True,
    ):
        """
        Initialize the enricher.

        Args:
            note_manager: NoteManager instance for note operations
            omnifocus_client: Optional OmniFocusClient for task creation
            omnifocus_enabled: Enable OmniFocus integration (default True)
        """
        self.note_manager = note_manager
        self.omnifocus_client = omnifocus_client
        self.omnifocus_enabled = omnifocus_enabled and omnifocus_client is not None

    async def apply(
        self,
        analysis: AnalysisResult,
        source_event_id: str,
    ) -> EnrichmentResult:
        """
        Apply all extractions from an analysis to the PKM.

        Args:
            analysis: AnalysisResult containing extractions to apply
            source_event_id: ID of the source event (for traceability)

        Returns:
            EnrichmentResult with lists of affected notes and tasks
        """
        result = EnrichmentResult()

        if not analysis.has_extractions:
            logger.debug(f"No extractions to apply for event {source_event_id}")
            return result

        logger.info(
            f"Applying {analysis.extraction_count} extractions "
            f"for event {source_event_id}"
        )

        for extraction in analysis.extractions:
            try:
                note_result = await self._apply_extraction(extraction, source_event_id)

                if note_result.success:
                    if note_result.created:
                        result.notes_created.append(note_result.note_id)
                    else:
                        result.notes_updated.append(note_result.note_id)

                    # Create OmniFocus task if needed
                    if extraction.omnifocus and self.omnifocus_enabled:
                        task_result = await self._create_omnifocus_task(
                            extraction,
                            note_result.note_id,
                            source_event_id,
                        )
                        if task_result:
                            result.tasks_created.append(task_result)
                else:
                    result.errors.append(note_result.error or "Unknown error")

            except Exception as e:
                error_msg = f"Failed to apply extraction '{extraction.info}': {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        logger.info(
            f"Enrichment complete: {len(result.notes_updated)} updated, "
            f"{len(result.notes_created)} created, "
            f"{len(result.tasks_created)} tasks, "
            f"{len(result.errors)} errors"
        )

        return result

    async def _apply_extraction(
        self,
        extraction: Extraction,
        source_event_id: str,
    ) -> NoteResult:
        """
        Apply a single extraction to the PKM.

        Args:
            extraction: Extraction to apply
            source_event_id: Source event ID for linking

        Returns:
            NoteResult with operation status
        """
        if extraction.note_action == NoteAction.CREER:
            return self._create_new_note(extraction, source_event_id)
        else:
            return self._enrich_existing_note(extraction, source_event_id)

    def _create_new_note(
        self,
        extraction: Extraction,
        source_event_id: str,
    ) -> NoteResult:
        """
        Create a new note for an extraction.

        Args:
            extraction: Extraction to apply
            source_event_id: Source event ID

        Returns:
            NoteResult with created note ID
        """
        try:
            # Build initial content
            content = self._build_note_content(extraction)

            # Create the note
            note_id = self.note_manager.create_note(
                title=extraction.note_cible,
                content=content,
                tags=[extraction.type.value, extraction.importance.value],
                metadata={
                    "source_event": source_event_id,
                    "auto_created": True,
                    "extraction_type": extraction.type.value,
                },
            )

            logger.debug(f"Created new note: {extraction.note_cible} ({note_id})")

            return NoteResult(
                note_id=note_id,
                created=True,
                title=extraction.note_cible,
            )

        except Exception as e:
            error_msg = f"Failed to create note '{extraction.note_cible}': {e}"
            logger.error(error_msg)
            return NoteResult(
                note_id="",
                created=True,
                title=extraction.note_cible,
                error=error_msg,
            )

    def _enrich_existing_note(
        self,
        extraction: Extraction,
        source_event_id: str,
    ) -> NoteResult:
        """
        Enrich an existing note with extraction info.

        If the note doesn't exist, creates it.

        Args:
            extraction: Extraction to apply
            source_event_id: Source event ID

        Returns:
            NoteResult with note ID
        """
        try:
            # Try to find existing note by title
            existing_note = self.note_manager.get_note_by_title(extraction.note_cible)

            if existing_note is None:
                # Note doesn't exist, create it
                logger.info(
                    f"Note '{extraction.note_cible}' not found, creating new note"
                )
                return self._create_new_note(extraction, source_event_id)

            # Add info to existing note
            success = self.note_manager.add_info(
                note_id=existing_note.note_id,
                info=extraction.info,
                info_type=extraction.type.value,
                importance=extraction.importance.value,
                source_id=source_event_id,
            )

            if not success:
                return NoteResult(
                    note_id=existing_note.note_id,
                    created=False,
                    title=extraction.note_cible,
                    error=f"Failed to add info to note {existing_note.note_id}",
                )

            logger.debug(
                f"Enriched note '{extraction.note_cible}' ({existing_note.note_id})"
            )

            return NoteResult(
                note_id=existing_note.note_id,
                created=False,
                title=extraction.note_cible,
            )

        except Exception as e:
            error_msg = f"Failed to enrich note '{extraction.note_cible}': {e}"
            logger.error(error_msg)
            return NoteResult(
                note_id="",
                created=False,
                title=extraction.note_cible,
                error=error_msg,
            )

    def _build_note_content(self, extraction: Extraction) -> str:
        """
        Build initial content for a new note.

        Args:
            extraction: Extraction data

        Returns:
            Markdown content string
        """
        # Map type to section name
        section_names = {
            "decision": "Décisions",
            "engagement": "Engagements",
            "fait": "Faits",
            "deadline": "Jalons",
            "relation": "Relations",
            # Nouveaux types v2.1.1
            "coordonnees": "Coordonnées",
            "montant": "Montants",
            "reference": "Références",
            "demande": "Demandes",
            "evenement": "Événements",
        }

        section = section_names.get(extraction.type.value, "Notes")
        importance_icon = "🔴" if extraction.importance.value == "haute" else "🟡"

        content = f"""# {extraction.note_cible}

## {section}

- {importance_icon} {extraction.info}

---
*Note auto-generee par Scapin*
"""
        return content

    async def _create_omnifocus_task(
        self,
        extraction: Extraction,
        note_id: str,
        source_event_id: str,
    ) -> Optional[str]:
        """
        Create an OmniFocus task for an extraction.

        Args:
            extraction: Extraction data
            note_id: Related note ID
            source_event_id: Source event ID

        Returns:
            Task ID if created, None otherwise
        """
        if not self.omnifocus_client:
            return None

        try:
            # Build task note with links
            task_note = f"""Source: {source_event_id}
Note: {note_id}

{extraction.info}"""

            # Extract due date if deadline type
            due_date = None
            if extraction.type.value == "deadline":
                due_date = self._extract_date_from_info(extraction.info)

            task = await self.omnifocus_client.create_task(
                title=extraction.info[:100],  # Truncate for task title
                project=extraction.note_cible,  # Use note title as project
                due_date=due_date,
                note=task_note,
                tags=["scapin", extraction.type.value],
            )

            logger.debug(f"Created OmniFocus task: {task.task_id}")
            return task.task_id

        except OmniFocusError as e:
            logger.warning(f"Failed to create OmniFocus task: {e}")
            return None

    def _extract_date_from_info(self, info: str) -> Optional[str]:
        """
        Try to extract a date from extraction info.

        Looks for patterns like "15 mars", "2026-01-15", etc.

        Args:
            info: Information string

        Returns:
            Date in YYYY-MM-DD format if found, None otherwise
        """
        import re
        from datetime import datetime

        # Try ISO format first (YYYY-MM-DD)
        iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", info)
        if iso_match:
            return iso_match.group(1)

        # French month names
        months_fr = {
            "janvier": 1,
            "fevrier": 2,
            "février": 2,
            "mars": 3,
            "avril": 4,
            "mai": 5,
            "juin": 6,
            "juillet": 7,
            "aout": 8,
            "août": 8,
            "septembre": 9,
            "octobre": 10,
            "novembre": 11,
            "decembre": 12,
            "décembre": 12,
        }

        # Try French date format (e.g., "15 mars", "1er avril")
        fr_match = re.search(
            r"(\d{1,2})(?:er)?\s+(" + "|".join(months_fr.keys()) + r")",
            info.lower(),
        )
        if fr_match:
            day = int(fr_match.group(1))
            month = months_fr.get(fr_match.group(2), 1)
            year = datetime.now().year
            # If month is in the past, assume next year
            if month < datetime.now().month:
                year += 1
            return f"{year}-{month:02d}-{day:02d}"

        return None


def create_enricher(
    note_manager: Optional[NoteManager] = None,
    omnifocus_client: Optional[OmniFocusClient] = None,
    omnifocus_enabled: bool = True,
) -> PKMEnricher:
    """
    Factory function to create a PKMEnricher.

    Args:
        note_manager: NoteManager instance (creates default if None)
        omnifocus_client: OmniFocusClient instance (creates default if None and enabled)
        omnifocus_enabled: Enable OmniFocus integration

    Returns:
        Configured PKMEnricher instance
    """
    if note_manager is None:
        from src.core.config_manager import get_config

        config = get_config()
        note_manager = NoteManager(notes_dir=config.storage.notes_path)

    if omnifocus_client is None and omnifocus_enabled:
        from src.integrations.apple.omnifocus import create_omnifocus_client

        omnifocus_client = create_omnifocus_client()

    return PKMEnricher(
        note_manager=note_manager,
        omnifocus_client=omnifocus_client,
        omnifocus_enabled=omnifocus_enabled,
    )
