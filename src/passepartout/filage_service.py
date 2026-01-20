"""
Filage Service — Memory Cycles (v2)

Morning briefing service that prepares the daily "Filage" (thread).
Selects up to 20 Lectures for Johan based on:
1. Notes related to today's events
2. Notes due for Lecture (SM-2)
3. Recently retouched notes
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import Note, NoteManager
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import CycleType, NoteType

if TYPE_CHECKING:
    from src.core.events import PerceivedEvent
    from src.passepartout.cross_source import CrossSourceEngine

logger = get_logger("passepartout.filage_service")


@dataclass
class FilageLecture:
    """A single Lecture item in the Filage"""

    note_id: str
    note_title: str
    note_type: NoteType
    priority: int  # 1 = highest priority
    reason: str  # Why this note is in the Filage
    quality_score: Optional[int]  # 0-100
    questions_pending: bool
    questions_count: int
    related_event_id: Optional[str] = None  # If related to today's event


@dataclass
class Filage:
    """The complete morning Filage (thread)"""

    date: str  # YYYY-MM-DD
    generated_at: str  # ISO timestamp
    lectures: list[FilageLecture] = field(default_factory=list)
    total_lectures: int = 0
    events_today: int = 0
    notes_with_questions: int = 0


class FilageService:
    """
    Service for generating the morning Filage.

    The Filage is Johan's daily "thread" of notes to review:
    - Max 20 Lectures
    - Prioritized by relevance to today's events
    - Includes notes with pending questions
    - Balances SM-2 due notes with recently improved notes
    """

    DEFAULT_MAX_LECTURES = 20
    FILAGE_HOUR = 6  # Generate at 6 AM

    def __init__(
        self,
        note_manager: NoteManager,
        metadata_store: NoteMetadataStore,
        scheduler: NoteScheduler,
        cross_source_engine: Optional["CrossSourceEngine"] = None,
    ):
        """
        Initialize Filage service

        Args:
            note_manager: Note manager for accessing notes
            metadata_store: Store for metadata
            scheduler: Scheduler for getting due notes
            cross_source_engine: Optional cross-source engine for calendar access
        """
        self.notes = note_manager
        self.store = metadata_store
        self.scheduler = scheduler
        self.cross_source = cross_source_engine

    async def generate_filage(
        self,
        max_lectures: int = DEFAULT_MAX_LECTURES,
        for_date: Optional[datetime] = None,
    ) -> Filage:
        """
        Generate the Filage for a given date.

        Priority order:
        1. Notes with pending questions (urgent)
        2. Notes related to today's events
        3. Notes due for Lecture (SM-2)
        4. Recently retouched notes

        Args:
            max_lectures: Maximum number of lectures (default 20)
            for_date: Date to generate for (default: today)

        Returns:
            Filage with prioritized lectures
        """
        if for_date is None:
            for_date = datetime.now(timezone.utc)

        date_str = for_date.strftime("%Y-%m-%d")
        logger.info(f"Generating Filage for {date_str}")

        lectures: list[FilageLecture] = []
        seen_note_ids: set[str] = set()
        events_today = 0

        # Priority 1: Notes with pending questions
        questions_notes = self.store.get_notes_with_pending_questions(limit=5)
        for meta in questions_notes:
            if len(lectures) >= max_lectures:
                break
            if meta.note_id in seen_note_ids:
                continue

            note = self.notes.get_note(meta.note_id)
            if note:
                lectures.append(
                    FilageLecture(
                        note_id=meta.note_id,
                        note_title=note.title,
                        note_type=meta.note_type,
                        priority=len(lectures) + 1,
                        reason="Questions en attente",
                        quality_score=meta.quality_score,
                        questions_pending=True,
                        questions_count=meta.questions_count,
                    )
                )
                seen_note_ids.add(meta.note_id)

        # Priority 2: Notes related to today's events
        todays_events = await self._get_todays_events(for_date)
        events_today = len(todays_events)

        for event in todays_events:
            if len(lectures) >= max_lectures:
                break

            related_notes = await self._find_related_notes(event)
            for note, meta in related_notes:
                if len(lectures) >= max_lectures:
                    break
                if note.note_id in seen_note_ids:
                    continue

                lectures.append(
                    FilageLecture(
                        note_id=note.note_id,
                        note_title=note.title,
                        note_type=meta.note_type if meta else NoteType.AUTRE,
                        priority=len(lectures) + 1,
                        reason=f"Lié à: {event.title[:50]}",
                        quality_score=meta.quality_score if meta else None,
                        questions_pending=meta.questions_pending if meta else False,
                        questions_count=meta.questions_count if meta else 0,
                        related_event_id=event.event_id if hasattr(event, "event_id") else None,
                    )
                )
                seen_note_ids.add(note.note_id)

        # Priority 3: Notes due for Lecture (SM-2)
        if len(lectures) < max_lectures:
            remaining = max_lectures - len(lectures)
            due_notes = self.scheduler.get_notes_due(
                limit=remaining,
                cycle_type=CycleType.LECTURE,
            )

            for meta in due_notes:
                if meta.note_id in seen_note_ids:
                    continue

                note = self.notes.get_note(meta.note_id)
                if note:
                    lectures.append(
                        FilageLecture(
                            note_id=meta.note_id,
                            note_title=note.title,
                            note_type=meta.note_type,
                            priority=len(lectures) + 1,
                            reason="Lecture due (SM-2)",
                            quality_score=meta.quality_score,
                            questions_pending=meta.questions_pending,
                            questions_count=meta.questions_count,
                        )
                    )
                    seen_note_ids.add(meta.note_id)

        # Priority 4: Recently retouched notes (last 48h)
        if len(lectures) < max_lectures:
            remaining = max_lectures - len(lectures)
            recent = self.store.get_recently_retouched(hours=48, limit=remaining)

            for meta in recent:
                if meta.note_id in seen_note_ids:
                    continue

                note = self.notes.get_note(meta.note_id)
                if note:
                    lectures.append(
                        FilageLecture(
                            note_id=meta.note_id,
                            note_title=note.title,
                            note_type=meta.note_type,
                            priority=len(lectures) + 1,
                            reason="Récemment améliorée",
                            quality_score=meta.quality_score,
                            questions_pending=meta.questions_pending,
                            questions_count=meta.questions_count,
                        )
                    )
                    seen_note_ids.add(meta.note_id)

        # Count notes with questions
        notes_with_questions = sum(1 for lec in lectures if lec.questions_pending)

        logger.info(
            f"Filage generated: {len(lectures)} lectures, "
            f"{events_today} events, {notes_with_questions} with questions"
        )

        return Filage(
            date=date_str,
            generated_at=datetime.now(timezone.utc).isoformat(),
            lectures=lectures,
            total_lectures=len(lectures),
            events_today=events_today,
            notes_with_questions=notes_with_questions,
        )

    async def _get_todays_events(
        self,
        for_date: datetime,
    ) -> list["PerceivedEvent"]:
        """Get calendar events for the specified date"""
        if self.cross_source is None:
            return []

        try:
            # Search for calendar events
            start_of_day = for_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            # Use cross-source to get calendar events
            result = await self.cross_source.search(
                query="",
                sources=["calendar"],
                start_date=start_of_day,
                end_date=end_of_day,
                max_results=20,
            )

            # Convert to PerceivedEvent-like objects
            events = []
            for item in result.items:
                events.append(item)

            logger.debug(f"Found {len(events)} events for {for_date.date()}")
            return events

        except Exception as e:
            logger.warning(f"Failed to get calendar events: {e}")
            return []

    async def _find_related_notes(
        self,
        event: "PerceivedEvent",
    ) -> list[tuple[Note, Optional[NoteMetadata]]]:
        """Find notes related to a calendar event"""
        related = []

        try:
            # Build search query from event
            query_parts = []

            # Event title
            if hasattr(event, "title") and event.title:
                query_parts.append(event.title)

            # Attendee names (if available)
            if hasattr(event, "attendees"):
                for attendee in event.attendees[:3]:  # Limit to 3
                    if hasattr(attendee, "name") and attendee.name:
                        query_parts.append(attendee.name)

            # Search for related notes
            if query_parts:
                query = " ".join(query_parts)
                search_results = self.notes.search_notes(query=query, top_k=5)

                for result in search_results:
                    if isinstance(result, tuple):
                        note = result[0]
                        score = result[1] if len(result) > 1 else 0.0
                    else:
                        note = result
                        score = 1.0

                    # Only include if relevance is high enough
                    if score >= 0.6:
                        meta = self.store.get(note.note_id)
                        related.append((note, meta))

        except Exception as e:
            logger.warning(f"Failed to find related notes for event: {e}")

        return related

    def is_filage_hour(self, now: Optional[datetime] = None) -> bool:
        """Check if it's time to generate the Filage"""
        if now is None:
            now = datetime.now(timezone.utc)

        # Convert to local time (assuming Paris timezone for Johan)
        # For now, use UTC + offset for simplicity
        local_hour = (now.hour + 1) % 24  # UTC+1 for Paris (simplified)

        return local_hour == self.FILAGE_HOUR

    async def get_lecture_for_note(self, note_id: str) -> Optional[FilageLecture]:
        """Get Filage lecture info for a specific note"""
        meta = self.store.get(note_id)
        if meta is None:
            return None

        note = self.notes.get_note(note_id)
        if note is None:
            return None

        # Determine reason
        reason = "Note demandée"
        if meta.questions_pending:
            reason = "Questions en attente"
        elif meta.lecture_next and meta.lecture_next <= datetime.now(timezone.utc):
            reason = "Lecture due (SM-2)"
        elif meta.retouche_last and (
            datetime.now(timezone.utc) - meta.retouche_last
        ) < timedelta(hours=48):
            reason = "Récemment améliorée"

        return FilageLecture(
            note_id=note_id,
            note_title=note.title,
            note_type=meta.note_type,
            priority=1,
            reason=reason,
            quality_score=meta.quality_score,
            questions_pending=meta.questions_pending,
            questions_count=meta.questions_count,
        )
