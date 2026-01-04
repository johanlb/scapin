"""
Journal Router

Journal API endpoints for daily entries, reviews, and calibration.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.models.journal import (
    AnswerRequest,
    CalendarSummaryResponse,
    CalibrationResponse,
    CorrectionRequest,
    CorrectionResponse,
    EmailSummaryResponse,
    ExportRequest,
    JournalEntryResponse,
    JournalListItemResponse,
    MonthlyReviewResponse,
    OmniFocusSummaryResponse,
    PatternResponse,
    QuestionResponse,
    SourceCalibrationResponse,
    TaskSummaryResponse,
    TeamsSummaryResponse,
    WeeklyReviewResponse,
)
from src.jeeves.api.models.responses import APIResponse, PaginatedResponse
from src.jeeves.api.services.journal_service import JournalService
from src.jeeves.journal import JournalEntry

router = APIRouter()


def _get_journal_service() -> JournalService:
    """Dependency to get journal service"""
    return JournalService()


def _convert_entry_to_response(entry: JournalEntry) -> JournalEntryResponse:
    """Convert JournalEntry to response model"""
    return JournalEntryResponse(
        entry_id=entry.entry_id,
        journal_date=entry.journal_date,
        created_at=entry.created_at,
        status=entry.status.value,
        emails_count=len(entry.emails_processed),
        tasks_count=len(entry.tasks_created),
        teams_count=len(entry.teams_messages),
        calendar_count=len(entry.calendar_events),
        omnifocus_count=len(entry.omnifocus_items),
        questions_count=len(entry.questions),
        corrections_count=len(entry.corrections),
        emails_processed=[
            EmailSummaryResponse(
                email_id=e.email_id,
                from_address=e.from_address,
                from_name=e.from_name,
                subject=e.subject,
                action=e.action,
                category=e.category,
                confidence=e.confidence,
                reasoning=e.reasoning,
                processed_at=e.processed_at,
            )
            for e in entry.emails_processed
        ],
        tasks_created=[
            TaskSummaryResponse(
                task_id=t.task_id,
                title=t.title,
                source_email_id=t.source_email_id,
                project=t.project,
                due_date=t.due_date,
                created_at=t.created_at,
            )
            for t in entry.tasks_created
        ],
        teams_messages=[
            TeamsSummaryResponse(
                message_id=m.message_id,
                chat_name=m.chat_name,
                sender=m.sender,
                preview=m.preview,
                action=m.action,
                confidence=m.confidence,
                processed_at=m.processed_at,
            )
            for m in entry.teams_messages
        ],
        calendar_events=[
            CalendarSummaryResponse(
                event_id=c.event_id,
                title=c.title,
                start_time=c.start_time,
                end_time=c.end_time,
                action=c.action,
                attendees=c.attendees,
                location=c.location,
                is_online=c.is_online,
                notes=c.notes,
            )
            for c in entry.calendar_events
        ],
        omnifocus_items=[
            OmniFocusSummaryResponse(
                task_id=o.task_id,
                title=o.title,
                project=o.project,
                status=o.status,
                tags=o.tags,
                completed_at=o.completed_at,
                due_date=o.due_date,
                flagged=o.flagged,
                estimated_minutes=o.estimated_minutes,
            )
            for o in entry.omnifocus_items
        ],
        questions=[
            QuestionResponse(
                question_id=q.question_id,
                category=q.category.value,
                question_text=q.question_text,
                context=q.context,
                options=list(q.options),
                priority=q.priority,
                related_email_id=q.related_email_id,
                related_entity=q.related_entity,
                answer=q.answer,
            )
            for q in entry.questions
        ],
        corrections=[
            CorrectionResponse(
                email_id=c.email_id,
                original_action=c.original_action,
                corrected_action=c.corrected_action,
                original_category=c.original_category,
                corrected_category=c.corrected_category,
                reason=c.reason,
            )
            for c in entry.corrections
        ],
        average_confidence=entry.average_confidence,
        unanswered_questions=len(entry.unanswered_questions),
    )


@router.get("/{target_date}", response_model=APIResponse[JournalEntryResponse])
async def get_journal(
    target_date: date,
    generate: bool = Query(False, description="Generate if not exists"),
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[JournalEntryResponse]:
    """
    Get journal entry for a specific date

    Returns existing journal or optionally generates a new one.
    """
    try:
        if generate:
            entry = await service.get_or_generate_journal(target_date)
        else:
            entry = await service.get_journal(target_date)
            if not entry:
                raise HTTPException(
                    status_code=404,
                    detail=f"No journal found for {target_date}",
                )

        return APIResponse(
            success=True,
            data=_convert_entry_to_response(entry),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list", response_model=PaginatedResponse[list[JournalListItemResponse]])
async def list_journals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    start_date: date | None = Query(None, description="Filter start date"),
    end_date: date | None = Query(None, description="Filter end date"),
    service: JournalService = Depends(_get_journal_service),
) -> PaginatedResponse[list[JournalListItemResponse]]:
    """
    List journal entries with pagination

    Returns a paginated list of journal entries.
    """
    try:
        entries, total = await service.list_journals(
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
        )

        items = [
            JournalListItemResponse(
                entry_id=e.entry_id,
                journal_date=e.journal_date,
                status=e.status.value,
                emails_count=len(e.emails_processed),
                questions_count=len(e.questions),
                corrections_count=len(e.corrections),
                average_confidence=e.average_confidence,
                completed_at=e.completed_at,
            )
            for e in entries
        ]

        return PaginatedResponse(
            success=True,
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{target_date}/answer", response_model=APIResponse[JournalEntryResponse])
async def answer_question(
    target_date: date,
    request: AnswerRequest,
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[JournalEntryResponse]:
    """
    Answer a journal question

    Records the user's answer to a journal question.
    """
    try:
        entry = await service.answer_question(
            target_date=target_date,
            question_id=request.question_id,
            answer=request.answer,
        )
        return APIResponse(
            success=True,
            data=_convert_entry_to_response(entry),
            timestamp=datetime.now(timezone.utc),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{target_date}/correction", response_model=APIResponse[JournalEntryResponse])
async def submit_correction(
    target_date: date,
    request: CorrectionRequest,
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[JournalEntryResponse]:
    """
    Submit a correction for an email decision

    Records a user correction for an automated decision.
    """
    try:
        entry = await service.submit_correction(
            target_date=target_date,
            email_id=request.email_id,
            corrected_action=request.corrected_action,
            corrected_category=request.corrected_category,
            reason=request.reason,
            confidence_override=request.confidence_override,
        )
        return APIResponse(
            success=True,
            data=_convert_entry_to_response(entry),
            timestamp=datetime.now(timezone.utc),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{target_date}/complete", response_model=APIResponse[JournalEntryResponse])
async def complete_journal(
    target_date: date,
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[JournalEntryResponse]:
    """
    Mark journal as completed

    Processes all feedback and marks the journal as done.
    """
    try:
        entry = await service.complete_journal(target_date)
        return APIResponse(
            success=True,
            data=_convert_entry_to_response(entry),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/weekly/{week_start}", response_model=APIResponse[WeeklyReviewResponse])
async def get_weekly_review(
    week_start: date,
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[WeeklyReviewResponse]:
    """
    Get weekly review

    Generates a summary of the week's activity with patterns and suggestions.
    """
    try:
        review_dict = await service.get_weekly_review(week_start)

        # Convert patterns
        patterns = [
            PatternResponse(
                pattern_type=p.get("pattern_type", ""),
                description=p.get("description", ""),
                frequency=p.get("frequency", 0),
                confidence=p.get("confidence", 0.0),
                examples=p.get("examples", []),
            )
            for p in review_dict.get("patterns_detected", [])
        ]

        return APIResponse(
            success=True,
            data=WeeklyReviewResponse(
                week_start=date.fromisoformat(review_dict.get("week_start", str(week_start))),
                week_end=date.fromisoformat(review_dict.get("week_end", str(week_start))),
                daily_entry_count=review_dict.get("daily_entry_count", 0),
                patterns_detected=patterns,
                productivity_score=review_dict.get("productivity_score", 0.0),
                top_categories=review_dict.get("top_categories", []),
                suggestions=review_dict.get("suggestions", []),
                emails_total=review_dict.get("emails_total", 0),
                tasks_total=review_dict.get("tasks_total", 0),
                corrections_total=review_dict.get("corrections_total", 0),
                accuracy_rate=review_dict.get("accuracy_rate", 0.0),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/monthly/{month}", response_model=APIResponse[MonthlyReviewResponse])
async def get_monthly_review(
    month: date,
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[MonthlyReviewResponse]:
    """
    Get monthly review

    Generates a summary of the month's activity with trends and calibration.
    """
    try:
        review_dict = await service.get_monthly_review(month)

        return APIResponse(
            success=True,
            data=MonthlyReviewResponse(
                month=date.fromisoformat(review_dict.get("month", str(month))),
                weekly_review_count=review_dict.get("weekly_review_count", 0),
                trends=review_dict.get("trends", []),
                goals_progress=review_dict.get("goals_progress", {}),
                calibration_summary=review_dict.get("calibration_summary", {}),
                productivity_average=review_dict.get("productivity_average", 0.0),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/calibration", response_model=APIResponse[CalibrationResponse])
async def get_calibration(
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[CalibrationResponse]:
    """
    Get calibration analysis

    Returns accuracy data and threshold recommendations.
    """
    try:
        analysis = await service.get_calibration()

        sources = {
            source: SourceCalibrationResponse(
                source=cal.source,
                total_items=cal.total_items,
                correct_decisions=cal.correct_decisions,
                incorrect_decisions=cal.incorrect_decisions,
                accuracy=cal.accuracy,
                correction_rate=cal.correction_rate,
                average_confidence=cal.average_confidence,
                last_updated=cal.last_updated,
            )
            for source, cal in analysis.source_calibrations.items()
        }

        return APIResponse(
            success=True,
            data=CalibrationResponse(
                sources=sources,
                overall_accuracy=analysis.overall_accuracy,
                recommended_threshold_adjustment=analysis.recommended_threshold_adjustment,
                patterns_learned=analysis.patterns_learned,
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{target_date}/export", response_model=APIResponse[str])
async def export_journal(
    target_date: date,
    request: ExportRequest = ExportRequest(),
    service: JournalService = Depends(_get_journal_service),
) -> APIResponse[str]:
    """
    Export journal in specified format

    Returns the journal content as markdown, JSON, or HTML.
    """
    try:
        content = await service.export_journal(
            target_date=target_date,
            format=request.format,
            include_questions=request.include_questions,
            include_corrections=request.include_corrections,
        )
        return APIResponse(
            success=True,
            data=content,
            timestamp=datetime.now(timezone.utc),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
