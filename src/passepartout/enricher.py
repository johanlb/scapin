"""
PKM Enricher — Knowledge Application

Applique les extractions de l'analyse au PKM (Personal Knowledge Management).

Ce module implémente la phase d'application du Workflow v2.1.1 :
1. Pour chaque extraction, trouve ou crée la note cible
2. Ajoute l'information à la note appropriée
3. Crée les tâches OmniFocus si nécessaire
4. Crée les événements calendrier si nécessaire (type=evenement)
5. Retourne un rapport d'enrichissement

Usage:
    enricher = PKMEnricher(note_manager, omnifocus_client, calendar_client)
    result = await enricher.apply(analysis_result, source_event_id)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from src.core.models.v2_models import (
    AnalysisResult,
    EnrichmentResult,
    Extraction,
    NoteAction,
    NoteResult,
)
from src.integrations.apple.omnifocus import OmniFocusClient, OmniFocusError
from src.integrations.microsoft.calendar_client import CalendarClient
from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager
from src.utils.date_utils import get_local_timezone

logger = get_logger("enricher")

# Timezone indicators mapping
# HF = Heure France, HM = Heure Madagascar
TIMEZONE_INDICATORS: dict[str, ZoneInfo] = {
    "paris": ZoneInfo("Europe/Paris"),
    "hf": ZoneInfo("Europe/Paris"),  # Heure France
    "france": ZoneInfo("Europe/Paris"),
    "hm": ZoneInfo("Indian/Antananarivo"),  # Heure Madagascar
    "madagascar": ZoneInfo("Indian/Antananarivo"),
    "maurice": ZoneInfo("Indian/Mauritius"),  # Port Louis, UTC+4
    "mauritius": ZoneInfo("Indian/Mauritius"),
    "utc": ZoneInfo("UTC"),
    "gmt": ZoneInfo("UTC"),
}


class EnricherError(Exception):
    """Base exception for enricher errors"""

    pass


class CalendarError(Exception):
    """Error creating calendar events"""

    pass


class PKMEnricher:
    """
    Applique les extractions au PKM.

    Prend un AnalysisResult et applique chaque extraction à la note
    cible correspondante. Gère également la création de tâches OmniFocus
    et d'événements calendrier.

    Attributes:
        note_manager: Gestionnaire de notes pour les opérations CRUD
        omnifocus_client: Client OmniFocus (optionnel)
        omnifocus_enabled: Si True, crée les tâches OmniFocus
        calendar_client: Client calendrier Microsoft (optionnel)
        calendar_enabled: Si True, crée les événements calendrier

    Example:
        >>> enricher = PKMEnricher(note_manager, omnifocus_client, calendar_client)
        >>> result = await enricher.apply(analysis_result, "email_123")
        >>> if result.success:
        ...     print(f"Updated {result.total_notes_affected} notes")
    """

    def __init__(
        self,
        note_manager: NoteManager,
        omnifocus_client: Optional[OmniFocusClient] = None,
        omnifocus_enabled: bool = True,
        calendar_client: Optional[CalendarClient] = None,
        calendar_enabled: bool = True,
    ):
        """
        Initialize the enricher.

        Args:
            note_manager: NoteManager instance for note operations
            omnifocus_client: Optional OmniFocusClient for task creation
            omnifocus_enabled: Enable OmniFocus integration (default True)
            calendar_client: Optional CalendarClient for event creation
            calendar_enabled: Enable calendar integration (default True)
        """
        self.note_manager = note_manager
        self.omnifocus_client = omnifocus_client
        self.omnifocus_enabled = omnifocus_enabled and omnifocus_client is not None
        self.calendar_client = calendar_client
        self.calendar_enabled = calendar_enabled and calendar_client is not None

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

                    # Create calendar event if needed
                    if extraction.calendar and self.calendar_enabled:
                        event_result = await self._create_calendar_event(
                            extraction,
                            note_result.note_id,
                            source_event_id,
                        )
                        if event_result:
                            result.events_created.append(event_result)
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
            f"{len(result.events_created)} events, "
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
            "citation": "Citations",
            "objectif": "Objectifs",
            "competence": "Compétences",
            "preference": "Préférences",
        }

        section = section_names.get(extraction.type.value, "Notes")
        importance_icons = {"haute": "🔴", "moyenne": "🟡", "basse": "⚪"}
        importance_icon = importance_icons.get(extraction.importance.value, "🟡")

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

            # Extract due date - prefer explicit date, fallback to parsing from info
            due_date = extraction.date  # Use explicit date if provided
            if not due_date and extraction.type.value == "deadline":
                due_date = self._extract_date_from_info(extraction.info)

            # Use explicit project if set, otherwise fall back to note_cible
            project_name = extraction.project if extraction.project else extraction.note_cible

            # Build tags list
            tags = ["scapin", extraction.type.value]
            # TODO: Add priority support when OmniFocus client supports it
            # Currently extraction.priority is parsed but not used

            task = await self.omnifocus_client.create_task(
                title=extraction.info[:100],  # Truncate for task title
                project=project_name,
                due_date=due_date,
                note=task_note,
                tags=tags,
            )

            logger.debug(f"Created OmniFocus task: {task.task_id}")
            return task.task_id

        except OmniFocusError as e:
            logger.warning(f"Failed to create OmniFocus task: {e}")
            return None

    async def _create_calendar_event(
        self,
        extraction: Extraction,
        note_id: str,
        source_event_id: str,
    ) -> Optional[str]:
        """
        Create a calendar event for an extraction.

        Extracts date/time from the extraction info and creates
        a calendar event via Microsoft Graph API.

        Args:
            extraction: Extraction data (type should be 'evenement')
            note_id: Related note ID
            source_event_id: Source event ID

        Returns:
            Event ID if created, None otherwise
        """
        if not self.calendar_client:
            return None

        try:
            # First try to use explicit date/time fields from extraction
            event_datetime = None
            if extraction.date:
                event_datetime = self._parse_explicit_datetime(
                    extraction.date,
                    extraction.time,
                    extraction.timezone,
                    extraction.duration,
                )

            # Fallback: try to extract from info text
            if event_datetime is None:
                event_datetime = self._extract_datetime_from_info(extraction.info)

            if event_datetime is None:
                logger.warning(
                    f"Could not extract date/time from event info: {extraction.info}"
                )
                return None

            start_dt, end_dt = event_datetime

            # Build event body with source info
            body = f"""<p>Source: {source_event_id}</p>
<p>Note: {note_id}</p>
<hr/>
<p>{extraction.info}</p>
<p><em>Événement créé automatiquement par Scapin</em></p>"""

            # Create the event
            event = await self.calendar_client.create_event(
                subject=extraction.info[:100],  # Truncate for subject
                start=start_dt,
                end=end_dt,
                body=body,
                importance="normal",
                reminder_minutes=15,
            )

            logger.debug(f"Created calendar event: {event.event_id}")
            return event.event_id

        except Exception as e:
            logger.warning(f"Failed to create calendar event: {e}")
            return None

    def _parse_explicit_datetime(
        self,
        date_str: str,
        time_str: Optional[str] = None,
        timezone_str: Optional[str] = None,
        duration_minutes: Optional[int] = None,
    ) -> Optional[tuple[datetime, datetime]]:
        """
        Parse explicit date/time fields from extraction.

        Dates are interpreted in the specified timezone (or local by default)
        and converted to UTC.

        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Optional time in HH:MM format
            timezone_str: Optional timezone indicator (HF, HM, Maurice, UTC, Paris)
            duration_minutes: Optional duration in minutes (default 60)

        Returns:
            Tuple of (start_datetime, end_datetime) in UTC, or None if invalid
        """
        try:
            # Parse date
            parts = date_str.split("-")
            if len(parts) != 3:
                return None

            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])

            # Parse time (default to 9:00 if not provided)
            hour = 9
            minute = 0
            if time_str:
                time_parts = time_str.split(":")
                if len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])

            # Determine timezone (explicit > default local)
            source_tz: ZoneInfo
            if timezone_str:
                tz_key = timezone_str.lower()
                source_tz = TIMEZONE_INDICATORS.get(tz_key, get_local_timezone())
            else:
                source_tz = get_local_timezone()

            # Create datetime in source timezone, then convert to UTC
            start_local = datetime(year, month, day, hour, minute, tzinfo=source_tz)
            start_dt = start_local.astimezone(timezone.utc)

            # Calculate end time based on duration (default 60 minutes)
            duration = duration_minutes if duration_minutes else 60
            end_dt = start_dt + timedelta(minutes=duration)

            return (start_dt, end_dt)

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse explicit date/time: {date_str} {time_str}: {e}")
            return None

    def _extract_datetime_from_info(
        self, info: str
    ) -> Optional[tuple[datetime, datetime]]:
        """
        Extract start and end datetime from extraction info.

        Parses patterns like:
        - "Réunion le 25 janvier à 14h" → (25/01 14:00 Paris, 25/01 15:00)
        - "Événement 2026-01-25 10:30" → (25/01 10:30, 25/01 11:30)
        - "Anniversaire le 15 mars" → (15/03 00:00, 15/03 23:59)
        - "Call à 9h Paris" → 9:00 Europe/Paris → UTC
        - "Réunion à 14h HF" → 14:00 Europe/Paris (HF = Heure France)
        - "Appel à 10h HM" → 10:00 Indian/Antananarivo (HM = Heure Madagascar)

        Timezone indicators supported:
        - Paris, HF, France → Europe/Paris
        - HM, Madagascar → Indian/Antananarivo
        - UTC, GMT → UTC

        Args:
            info: Information string

        Returns:
            Tuple of (start_datetime, end_datetime) in UTC, or None if not found
        """
        import re

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

        year = datetime.now(timezone.utc).year
        month = None
        day = None
        hour = 9  # Default to 9h if no time specified
        minute = 0
        explicit_tz: Optional[ZoneInfo] = None  # Detected timezone indicator

        # Try ISO format with time (YYYY-MM-DD HH:MM)
        iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})", info)
        if iso_match:
            year = int(iso_match.group(1))
            month = int(iso_match.group(2))
            day = int(iso_match.group(3))
            hour = int(iso_match.group(4))
            minute = int(iso_match.group(5))
        else:
            # Try ISO date only (YYYY-MM-DD)
            iso_date = re.search(r"(\d{4})-(\d{2})-(\d{2})", info)
            if iso_date:
                year = int(iso_date.group(1))
                month = int(iso_date.group(2))
                day = int(iso_date.group(3))

        # Try French date format (e.g., "15 mars", "1er avril")
        if month is None:
            fr_match = re.search(
                r"(\d{1,2})(?:er)?\s+(" + "|".join(months_fr.keys()) + r")",
                info.lower(),
            )
            if fr_match:
                day = int(fr_match.group(1))
                month = months_fr.get(fr_match.group(2), 1)
                # If month is in the past, assume next year
                if month < datetime.now(timezone.utc).month:
                    year += 1

        # Extract time (e.g., "à 14h", "14:30", "14h30")
        time_match = re.search(r"(?:à\s+)?(\d{1,2})[h:](\d{2})?", info.lower())
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0

        # Extract timezone indicator (e.g., "9h Paris", "14h HF", "10h HM")
        # Pattern: time followed by optional space and timezone indicator
        tz_pattern = (
            r"(?:\d{1,2}[h:]\d{0,2})\s*"
            r"(paris|hf|france|hm|madagascar|maurice|mauritius|utc|gmt)"
        )
        tz_match = re.search(tz_pattern, info.lower())
        if tz_match:
            tz_key = tz_match.group(1).lower()
            explicit_tz = TIMEZONE_INDICATORS.get(tz_key)
            if explicit_tz:
                logger.debug(f"Detected timezone indicator '{tz_key}' → {explicit_tz}")

        if month is None or day is None:
            return None

        try:
            # Use explicit timezone if detected, otherwise default to local (Paris)
            source_tz = explicit_tz if explicit_tz else get_local_timezone()
            start_local = datetime(year, month, day, hour, minute, tzinfo=source_tz)
            # Convert to UTC
            start_dt = start_local.astimezone(timezone.utc)
            # Default duration: 1 hour
            end_dt = start_dt + timedelta(hours=1)
            return (start_dt, end_dt)
        except ValueError:
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
    calendar_client: Optional[CalendarClient] = None,
    calendar_enabled: bool = True,
) -> PKMEnricher:
    """
    Factory function to create a PKMEnricher.

    Args:
        note_manager: NoteManager instance (creates default if None)
        omnifocus_client: OmniFocusClient instance (creates default if None and enabled)
        omnifocus_enabled: Enable OmniFocus integration
        calendar_client: CalendarClient instance (creates default if None and enabled)
        calendar_enabled: Enable calendar integration

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

    if calendar_client is None and calendar_enabled:
        from src.core.config_manager import get_config
        from src.integrations.microsoft.auth import MicrosoftAuthenticator
        from src.integrations.microsoft.graph_client import GraphClient

        try:
            config = get_config()
            auth = MicrosoftAuthenticator(config.teams, config.storage.cache_path)
            graph = GraphClient(auth)
            calendar_client = CalendarClient(graph=graph)
        except Exception as e:
            logger.warning(f"Could not initialize calendar client: {e}")
            calendar_client = None

    return PKMEnricher(
        note_manager=note_manager,
        omnifocus_client=omnifocus_client,
        omnifocus_enabled=omnifocus_enabled,
        calendar_client=calendar_client,
        calendar_enabled=calendar_enabled,
    )
