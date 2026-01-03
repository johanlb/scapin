"""
Briefing Router

Morning and pre-meeting briefing endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.deps import get_briefing_service
from src.jeeves.api.models.responses import (
    APIResponse,
    AttendeeResponse,
    BriefingItemResponse,
    BriefingResponse,
    PreMeetingBriefingResponse,
)
from src.jeeves.api.services.briefing_service import BriefingService

router = APIRouter()


def _convert_briefing_item(item_dict: dict) -> BriefingItemResponse:
    """Convert briefing item dict to response model"""
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
    """
    try:
        briefing = await service.generate_morning_briefing(hours_ahead=hours_ahead)
        briefing_dict = briefing.to_dict()

        # Convert items to response models
        urgent_items = [
            _convert_briefing_item(item) for item in briefing_dict.get("urgent_items", [])
        ]
        calendar_today = [
            _convert_briefing_item(item)
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
