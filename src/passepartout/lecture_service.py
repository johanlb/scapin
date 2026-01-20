"""
Lecture Service — Memory Cycles (v2)

Human review service for Johan's spaced repetition learning.
Manages Lecture sessions: starting, completing, and recording feedback.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager
from src.passepartout.note_metadata import NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import CycleType

logger = get_logger("passepartout.lecture_service")


@dataclass
class LectureSession:
    """Active Lecture session"""

    session_id: str
    note_id: str
    note_title: str
    note_content: str
    started_at: str  # ISO timestamp
    quality_score: Optional[int]  # 0-100
    questions: list[str] = field(default_factory=list)  # Pending questions
    metadata: Optional[dict] = None  # Additional metadata


@dataclass
class LectureResult:
    """Result of completing a Lecture"""

    note_id: str
    quality_rating: int  # 0-5 (SM-2)
    next_lecture: str  # ISO timestamp
    interval_hours: float
    answers_recorded: int
    questions_remaining: int
    success: bool
    error: Optional[str] = None


class LectureService:
    """
    Service for managing human Lecture sessions.

    A Lecture is a human review session where Johan:
    1. Reviews a note
    2. Answers any pending questions
    3. Rates the quality (0-5)
    4. Gets scheduled for next review via SM-2
    """

    def __init__(
        self,
        note_manager: NoteManager,
        metadata_store: NoteMetadataStore,
        scheduler: NoteScheduler,
    ):
        """
        Initialize Lecture service

        Args:
            note_manager: Note manager for accessing notes
            metadata_store: Store for metadata
            scheduler: Scheduler for updating review times
        """
        self.notes = note_manager
        self.store = metadata_store
        self.scheduler = scheduler

        # Track active sessions (in-memory, for simplicity)
        self._active_sessions: dict[str, LectureSession] = {}

    def start_lecture(self, note_id: str) -> Optional[LectureSession]:
        """
        Start a Lecture session for a note.

        Args:
            note_id: Note to review

        Returns:
            LectureSession or None if note not found
        """
        logger.info(f"Starting Lecture session for note {note_id}")

        note = self.notes.get_note(note_id)
        if note is None:
            logger.warning(f"Note not found: {note_id}")
            return None

        metadata = self.store.get(note_id)
        if metadata is None:
            # Create metadata if missing
            from src.passepartout.note_types import detect_note_type_from_path

            note_type = detect_note_type_from_path(str(note.file_path) if note.file_path else "")
            metadata = self.store.create_for_note(
                note_id=note_id,
                note_type=note_type,
                content=note.content,
            )

        # Extract questions from note content
        questions = self._extract_questions(note.content)

        # Create session
        session_id = f"lecture-{note_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        session = LectureSession(
            session_id=session_id,
            note_id=note_id,
            note_title=note.title,
            note_content=note.content,
            started_at=datetime.now(timezone.utc).isoformat(),
            quality_score=metadata.quality_score,
            questions=questions,
            metadata={
                "note_type": metadata.note_type.value,
                "lecture_count": metadata.lecture_count,
                "last_lecture": metadata.lecture_last.isoformat() if metadata.lecture_last else None,
            },
        )

        # Store active session
        self._active_sessions[session_id] = session

        logger.info(
            f"Lecture session started: {session_id}, {len(questions)} questions pending"
        )

        return session

    def complete_lecture(
        self,
        note_id: str,
        quality: int,
        answers: Optional[dict[str, str]] = None,
        session_id: Optional[str] = None,
    ) -> LectureResult:
        """
        Complete a Lecture session and update SM-2 scheduling.

        Args:
            note_id: Note that was reviewed
            quality: Review quality rating (0-5)
            answers: Optional dict mapping question_index to answer
            session_id: Optional session ID to close

        Returns:
            LectureResult with scheduling info
        """
        logger.info(f"Completing Lecture for note {note_id} with quality {quality}")

        # Validate quality
        if not 0 <= quality <= 5:
            return LectureResult(
                note_id=note_id,
                quality_rating=quality,
                next_lecture="",
                interval_hours=0,
                answers_recorded=0,
                questions_remaining=0,
                success=False,
                error=f"Invalid quality rating: {quality}. Must be 0-5.",
            )

        # Get metadata
        metadata = self.store.get(note_id)
        if metadata is None:
            return LectureResult(
                note_id=note_id,
                quality_rating=quality,
                next_lecture="",
                interval_hours=0,
                answers_recorded=0,
                questions_remaining=0,
                success=False,
                error="Note metadata not found",
            )

        # Process answers if provided
        answers_recorded = 0
        questions_remaining = metadata.questions_count

        if answers:
            answers_recorded = len(answers)
            # Update note content with answers
            self._record_answers(note_id, answers)

            # Update questions count
            questions_remaining = max(0, metadata.questions_count - answers_recorded)
            metadata.questions_count = questions_remaining
            metadata.questions_pending = questions_remaining > 0

        # Record the Lecture review
        updated_metadata = self.scheduler.record_review(
            note_id=note_id,
            quality=quality,
            metadata=metadata,
            cycle_type=CycleType.LECTURE,
        )

        if updated_metadata is None:
            return LectureResult(
                note_id=note_id,
                quality_rating=quality,
                next_lecture="",
                interval_hours=0,
                answers_recorded=answers_recorded,
                questions_remaining=questions_remaining,
                success=False,
                error="Failed to update review scheduling",
            )

        # Clean up session if provided
        if session_id and session_id in self._active_sessions:
            del self._active_sessions[session_id]

        # Calculate next lecture datetime
        next_lecture = updated_metadata.lecture_next
        interval_hours = updated_metadata.lecture_interval

        logger.info(
            f"Lecture complete for {note_id}: Q={quality}, "
            f"next in {interval_hours:.1f}h, answers={answers_recorded}"
        )

        return LectureResult(
            note_id=note_id,
            quality_rating=quality,
            next_lecture=next_lecture.isoformat() if next_lecture else "",
            interval_hours=interval_hours,
            answers_recorded=answers_recorded,
            questions_remaining=questions_remaining,
            success=True,
        )

    def get_active_session(self, session_id: str) -> Optional[LectureSession]:
        """Get an active Lecture session by ID"""
        return self._active_sessions.get(session_id)

    def get_sessions_for_note(self, note_id: str) -> list[LectureSession]:
        """Get all active sessions for a note"""
        return [
            session
            for session in self._active_sessions.values()
            if session.note_id == note_id
        ]

    def cancel_session(self, session_id: str) -> bool:
        """Cancel an active Lecture session"""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            logger.info(f"Lecture session cancelled: {session_id}")
            return True
        return False

    def _extract_questions(self, content: str) -> list[str]:
        """Extract pending questions from note content"""
        questions = []

        # Look for questions section
        import re

        # Pattern 1: Questions section
        questions_section = re.search(
            r"##\s*Questions?\s*(?:pour Johan)?\s*\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if questions_section:
            section_content = questions_section.group(1)
            # Extract bullet points or numbered items
            items = re.findall(r"[-*]\s*(.+\?)", section_content)
            questions.extend(items)

        # Pattern 2: Inline questions marked with [?]
        inline_questions = re.findall(r"\[?\?\]?\s*(.+\?)", content)
        for q in inline_questions:
            if q not in questions:
                questions.append(q)

        return questions

    def _record_answers(self, note_id: str, answers: dict[str, str]) -> bool:
        """Record answers in the note content"""
        note = self.notes.get_note(note_id)
        if note is None:
            return False

        content = note.content

        # Add answers section if not present
        answers_header = "\n\n## Réponses de Johan\n\n"
        if "## Réponses de Johan" not in content:
            content += answers_header

        # Add each answer
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for question_key, answer in answers.items():
            answer_entry = f"- **Q{question_key}** ({timestamp}): {answer}\n"
            content += answer_entry

        # Update note
        try:
            self.notes.update_note(note_id=note_id, content=content)
            logger.info(f"Recorded {len(answers)} answers for note {note_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to record answers: {e}")
            return False

    def get_lecture_stats(self, note_id: str) -> Optional[dict]:
        """Get Lecture statistics for a note"""
        metadata = self.store.get(note_id)
        if metadata is None:
            return None

        return {
            "note_id": note_id,
            "lecture_count": metadata.lecture_count,
            "lecture_ef": metadata.lecture_ef,
            "lecture_interval_hours": metadata.lecture_interval,
            "lecture_next": metadata.lecture_next.isoformat() if metadata.lecture_next else None,
            "lecture_last": metadata.lecture_last.isoformat() if metadata.lecture_last else None,
            "quality_score": metadata.quality_score,
            "questions_pending": metadata.questions_pending,
            "questions_count": metadata.questions_count,
        }
