"""
Briefing Router

Morning and pre-meeting briefing endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.events import PerceivedEvent
from src.jeeves.api.deps import get_briefing_service
from src.jeeves.api.models.calendar import CalendarConflict
from src.jeeves.api.models.responses import (
    APIResponse,
    AttendeeResponse,
    BriefingItemResponse,
    BriefingResponse,
    CalendarConflictResponse,
    PreMeetingBriefingResponse,
)
from src.jeeves.api.services.briefing_service import BriefingService
from src.jeeves.api.services.conflict_detector import ConflictDetector

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
