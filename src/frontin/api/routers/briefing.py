"""
Briefing Router

Morning and pre-meeting briefing endpoints.
Includes Memory Cycles v2: Filage (morning briefing) and Lecture (human review).
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.events import PerceivedEvent
from src.frontin.api.deps import get_briefing_service
from src.frontin.api.models.calendar import CalendarConflict
from src.frontin.api.models.responses import (
    APIResponse,
    AttendeeResponse,
    BriefingItemResponse,
    BriefingResponse,
    CalendarConflictResponse,
    PreMeetingBriefingResponse,
)
from src.frontin.api.services.briefing_service import BriefingService
from src.frontin.api.services.conflict_detector import ConflictDetector

router = APIRouter()

# Shared conflict detector instance
_conflict_detector = ConflictDetector()


def _convert_conflict(conflict: CalendarConflict) -> CalendarConflictResponse:
    """Convert CalendarConflict to response model"""
    return CalendarConflictResponse(
        conflict_type=conflict.conflict_type.value,
        severity=conflict.severity.value,
        conflicting_event_id=conflict.conflicting_event_id,
        conflicting_title=conflict.conflicting_title,
        conflicting_start=conflict.conflicting_start.isoformat(),
        conflicting_end=conflict.conflicting_end.isoformat(),
        overlap_minutes=conflict.overlap_minutes,
        gap_minutes=conflict.gap_minutes,
        message=conflict.message,
    )


def _convert_briefing_item(
    item_dict: dict,
    conflicts: list[CalendarConflict] | None = None,
) -> BriefingItemResponse:
    """Convert briefing item dict to response model with optional conflicts"""
    conflict_responses = [_convert_conflict(c) for c in (conflicts or [])]
    return BriefingItemResponse(
        event_id=item_dict.get("event_id", ""),
        title=item_dict.get("title", ""),
        source=item_dict.get("source", ""),
        priority_rank=item_dict.get("priority_rank", 0),
        time_context=item_dict.get("time_context", ""),
        action_summary=item_dict.get("action_summary"),
        confidence=item_dict.get("confidence", 0.0),
        urgency=item_dict.get("urgency", ""),
        from_person=item_dict.get("from_person"),
        has_conflicts=len(conflict_responses) > 0,
        conflicts=conflict_responses,
    )


@router.get("/morning", response_model=APIResponse[BriefingResponse])
async def get_morning_briefing(
    hours_ahead: int = Query(24, ge=1, le=48, description="Hours ahead for calendar"),
    service: BriefingService = Depends(get_briefing_service),
) -> APIResponse[BriefingResponse]:
    """
    Get morning briefing

    Aggregates urgent items, calendar events, pending emails,
    and unread Teams messages into a unified briefing.
    Includes calendar conflict detection for 7 days ahead.
    """
    try:
        briefing = await service.generate_morning_briefing(hours_ahead=hours_ahead)
        briefing_dict = briefing.to_dict()

        # Extract PerceivedEvents from calendar items for conflict detection
        # Also extract from urgent_items that are calendar events
        all_calendar_events: list[PerceivedEvent] = []
        for item in briefing.calendar_today:
            all_calendar_events.append(item.event)
        for item in briefing.urgent_items:
            # Avoid duplicates - only add calendar events not already in list
            if item.event.source.value == "calendar" and item.event not in all_calendar_events:
                all_calendar_events.append(item.event)

        # Detect conflicts across all calendar events (7 days)
        conflicts_by_id = _conflict_detector.detect_conflicts(
            all_calendar_events,
            days_ahead=7,
        )

        # Count total conflicts
        conflicts_count = sum(len(c) for c in conflicts_by_id.values())

        # Convert items to response models with conflict data
        urgent_items = [
            _convert_briefing_item(
                item,
                conflicts_by_id.get(item.get("event_id", ""), []),
            )
            for item in briefing_dict.get("urgent_items", [])
        ]
        calendar_today = [
            _convert_briefing_item(
                item,
                conflicts_by_id.get(item.get("event_id", ""), []),
            )
            for item in briefing_dict.get("calendar_today", [])
        ]
        emails_pending = [
            _convert_briefing_item(item)
            for item in briefing_dict.get("emails_pending", [])
        ]
        teams_unread = [
            _convert_briefing_item(item)
            for item in briefing_dict.get("teams_unread", [])
        ]

        return APIResponse(
            success=True,
            data=BriefingResponse(
                date=briefing_dict.get("date", ""),
                generated_at=briefing_dict.get("generated_at", ""),
                urgent_count=briefing_dict.get("urgent_count", 0),
                meetings_today=briefing_dict.get("meetings_today", 0),
                total_items=briefing_dict.get("total_items", 0),
                conflicts_count=conflicts_count,
                urgent_items=urgent_items,
                calendar_today=calendar_today,
                emails_pending=emails_pending,
                teams_unread=teams_unread,
                ai_summary=briefing_dict.get("ai_summary"),
                key_decisions=briefing_dict.get("key_decisions", []),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/meeting/{event_id}", response_model=APIResponse[PreMeetingBriefingResponse])
async def get_pre_meeting_briefing(
    event_id: str,
    service: BriefingService = Depends(get_briefing_service),
) -> APIResponse[PreMeetingBriefingResponse]:
    """
    Get pre-meeting briefing for a calendar event

    Provides attendee context, recent communications,
    and suggested talking points.
    """
    try:
        briefing = await service.generate_pre_meeting_briefing(event_id)
        briefing_dict = briefing.to_dict()

        # Convert attendees to response models
        attendees = [
            AttendeeResponse(
                name=att.get("name", ""),
                email=att.get("email", ""),
                is_organizer=att.get("is_organizer", False),
                interaction_count=att.get("interaction_count", 0),
                relationship_hint=att.get("relationship_hint"),
            )
            for att in briefing_dict.get("attendees", [])
        ]

        return APIResponse(
            success=True,
            data=PreMeetingBriefingResponse(
                event_id=briefing_dict.get("event_id", ""),
                event_title=briefing_dict.get("event_title", ""),
                generated_at=briefing_dict.get("generated_at", ""),
                minutes_until_start=briefing_dict.get("minutes_until_start", 0),
                attendees=attendees,
                recent_emails_count=briefing_dict.get("recent_emails_count", 0),
                recent_teams_count=briefing_dict.get("recent_teams_count", 0),
                meeting_url=briefing_dict.get("meeting_url"),
                location=briefing_dict.get("location"),
                talking_points=briefing_dict.get("talking_points", []),
                open_items=briefing_dict.get("open_items", []),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# === Memory Cycles v2: Filage & Lecture ===


class FilageLectureResponse(BaseModel):
    """Response model for a single Filage lecture"""

    note_id: str
    note_title: str
    note_type: str
    priority: int
    reason: str
    quality_score: Optional[int] = None
    questions_pending: bool = False
    questions_count: int = 0
    related_event_id: Optional[str] = None


class FilageResponse(BaseModel):
    """Response model for Filage"""

    date: str
    generated_at: str
    lectures: list[FilageLectureResponse]
    total_lectures: int
    events_today: int
    notes_with_questions: int


class LectureSessionResponse(BaseModel):
    """Response model for Lecture session"""

    session_id: str
    note_id: str
    note_title: str
    note_content: str
    started_at: str
    quality_score: Optional[int] = None
    questions: list[str] = Field(default_factory=list)
    metadata: Optional[dict] = None


class LectureCompleteRequest(BaseModel):
    """Request model for completing a Lecture"""

    quality: int = Field(..., ge=0, le=5, description="Review quality (0-5)")
    answers: Optional[dict[str, str]] = Field(
        default=None, description="Answers to questions (key=question_index)"
    )


class LectureResultResponse(BaseModel):
    """Response model for Lecture completion result"""

    note_id: str
    quality_rating: int
    next_lecture: str
    interval_hours: float
    answers_recorded: int
    questions_remaining: int
    success: bool
    error: Optional[str] = None


class LectureStatsResponse(BaseModel):
    """Response model for Lecture statistics"""

    note_id: str
    lecture_count: int
    lecture_ef: float
    lecture_interval_hours: float
    lecture_next: Optional[str] = None
    lecture_last: Optional[str] = None
    quality_score: Optional[int] = None
    questions_pending: bool = False
    questions_count: int = 0


@router.get("/filage", response_model=APIResponse[FilageResponse])
async def get_filage(
    max_lectures: int = Query(20, ge=1, le=50, description="Maximum lectures to include"),
) -> APIResponse[FilageResponse]:
    """
    Get the Filage (morning briefing with notes to review).

    The Filage includes:
    - Notes with pending questions (priority 1)
    - Notes related to today's events (priority 2)
    - Notes due for Lecture via SM-2 (priority 3)
    - Recently retouched notes (priority 4)
    """
    try:
        # Import here to avoid circular imports
        from src.passepartout.filage_service import FilageService
        from src.passepartout.note_manager import get_note_manager
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.note_scheduler import NoteScheduler

        # Get singleton instances
        note_manager = get_note_manager()
        metadata_store = NoteMetadataStore()
        scheduler = NoteScheduler(metadata_store)

        filage_service = FilageService(
            note_manager=note_manager,
            metadata_store=metadata_store,
            scheduler=scheduler,
        )

        filage = await filage_service.generate_filage(max_lectures=max_lectures)

        # Convert to response model
        lectures = [
            FilageLectureResponse(
                note_id=lecture.note_id,
                note_title=lecture.note_title,
                note_type=lecture.note_type.value,
                priority=lecture.priority,
                reason=lecture.reason,
                quality_score=lecture.quality_score,
                questions_pending=lecture.questions_pending,
                questions_count=lecture.questions_count,
                related_event_id=lecture.related_event_id,
            )
            for lecture in filage.lectures
        ]

        return APIResponse(
            success=True,
            data=FilageResponse(
                date=filage.date,
                generated_at=filage.generated_at,
                lectures=lectures,
                total_lectures=filage.total_lectures,
                events_today=filage.events_today,
                notes_with_questions=filage.notes_with_questions,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/lecture/{note_id}/start", response_model=APIResponse[LectureSessionResponse])
async def start_lecture(
    note_id: str,
) -> APIResponse[LectureSessionResponse]:
    """
    Start a Lecture session for a note.

    Returns the note content, pending questions, and session ID.
    """
    try:
        # Import here to avoid circular imports
        from src.passepartout.lecture_service import LectureService
        from src.passepartout.note_manager import get_note_manager
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.note_scheduler import NoteScheduler

        # Get singleton instances
        note_manager = get_note_manager()
        metadata_store = NoteMetadataStore()
        scheduler = NoteScheduler(metadata_store)

        lecture_service = LectureService(
            note_manager=note_manager,
            metadata_store=metadata_store,
            scheduler=scheduler,
        )

        session = lecture_service.start_lecture(note_id)

        if session is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=LectureSessionResponse(
                session_id=session.session_id,
                note_id=session.note_id,
                note_title=session.note_title,
                note_content=session.note_content,
                started_at=session.started_at,
                quality_score=session.quality_score,
                questions=session.questions,
                metadata=session.metadata,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/lecture/{note_id}/complete", response_model=APIResponse[LectureResultResponse])
async def complete_lecture(
    note_id: str,
    request: LectureCompleteRequest,
) -> APIResponse[LectureResultResponse]:
    """
    Complete a Lecture session and update SM-2 scheduling.

    Args:
        note_id: Note that was reviewed
        request: Quality rating (0-5) and optional answers
    """
    try:
        # Import here to avoid circular imports
        from src.passepartout.lecture_service import LectureService
        from src.passepartout.note_manager import get_note_manager
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.note_scheduler import NoteScheduler

        # Get singleton instances
        note_manager = get_note_manager()
        metadata_store = NoteMetadataStore()
        scheduler = NoteScheduler(metadata_store)

        lecture_service = LectureService(
            note_manager=note_manager,
            metadata_store=metadata_store,
            scheduler=scheduler,
        )

        result = lecture_service.complete_lecture(
            note_id=note_id,
            quality=request.quality,
            answers=request.answers,
        )

        return APIResponse(
            success=result.success,
            data=LectureResultResponse(
                note_id=result.note_id,
                quality_rating=result.quality_rating,
                next_lecture=result.next_lecture,
                interval_hours=result.interval_hours,
                answers_recorded=result.answers_recorded,
                questions_remaining=result.questions_remaining,
                success=result.success,
                error=result.error,
            ),
            timestamp=datetime.now(timezone.utc),
            error=result.error,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/lecture/{note_id}/stats", response_model=APIResponse[LectureStatsResponse])
async def get_lecture_stats(
    note_id: str,
) -> APIResponse[LectureStatsResponse]:
    """Get Lecture statistics for a note."""
    try:
        # Import here to avoid circular imports
        from src.passepartout.lecture_service import LectureService
        from src.passepartout.note_manager import get_note_manager
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.note_scheduler import NoteScheduler

        # Get singleton instances
        note_manager = get_note_manager()
        metadata_store = NoteMetadataStore()
        scheduler = NoteScheduler(metadata_store)

        lecture_service = LectureService(
            note_manager=note_manager,
            metadata_store=metadata_store,
            scheduler=scheduler,
        )

        stats = lecture_service.get_lecture_stats(note_id)

        if stats is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=LectureStatsResponse(**stats),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class AddToFilageResponse(BaseModel):
    """Response model for adding a note to Filage"""

    note_id: str
    success: bool
    message: str


class RetoucheResponse(BaseModel):
    """Response model for Retouche request"""

    note_id: str
    success: bool
    quality_before: Optional[int] = None
    quality_after: Optional[int] = None
    improvements_count: int = 0
    message: str


@router.post("/filage/add/{note_id}", response_model=APIResponse[AddToFilageResponse])
async def add_to_filage(
    note_id: str,
) -> APIResponse[AddToFilageResponse]:
    """
    Add a note to today's Filage (force immediate review).

    This sets the note's next_review to now, ensuring it appears in the Filage.
    """
    try:
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.note_scheduler import NoteScheduler

        metadata_store = NoteMetadataStore()
        scheduler = NoteScheduler(metadata_store)

        success = scheduler.trigger_immediate_review(note_id)

        if not success:
            return APIResponse(
                success=False,
                data=AddToFilageResponse(
                    note_id=note_id,
                    success=False,
                    message=f"Note not found: {note_id}",
                ),
                timestamp=datetime.now(timezone.utc),
                error=f"Note not found: {note_id}",
            )

        return APIResponse(
            success=True,
            data=AddToFilageResponse(
                note_id=note_id,
                success=True,
                message="Note ajoutée au filage du jour",
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/retouche/{note_id}", response_model=APIResponse[RetoucheResponse])
async def trigger_retouche(
    note_id: str,
) -> APIResponse[RetoucheResponse]:
    """
    Trigger an AI Retouche (review) for a note.

    The Retouche process:
    1. Analyzes the note content for potential improvements
    2. Suggests and applies corrections (links, formatting, etc.)
    3. Updates quality score

    Uses escalation Haiku -> Sonnet -> Opus based on confidence.
    """
    try:
        from src.passepartout.note_manager import get_note_manager
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.retouche_reviewer import RetoucheReviewer

        note_manager = get_note_manager()
        metadata_store = NoteMetadataStore()

        # Get quality before
        metadata = metadata_store.get(note_id)
        quality_before = metadata.quality_score if metadata else None

        # Create reviewer and execute retouche
        reviewer = RetoucheReviewer(
            note_manager=note_manager,
            metadata_store=metadata_store,
        )

        result = await reviewer.review_note(note_id)

        # Get quality after
        metadata_after = metadata_store.get(note_id)
        quality_after = metadata_after.quality_score if metadata_after else None

        return APIResponse(
            success=result.success,
            data=RetoucheResponse(
                note_id=note_id,
                success=result.success,
                quality_before=quality_before,
                quality_after=quality_after,
                improvements_count=len(result.improvements) if result.improvements else 0,
                message=result.error if result.error else "Retouche terminée avec succès",
            ),
            timestamp=datetime.now(timezone.utc),
            error=result.error,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
