"""
Calendar Router

API endpoints for calendar management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.frontin.api.models.calendar import (
    CalendarAttendeeResponse,
    CalendarEventResponse,
    CalendarPollResponse,
    CreateEventRequest,
    EventCreatedResponse,
    EventDeletedResponse,
    RespondToEventRequest,
    TodayEventsResponse,
    UpdateEventRequest,
)
from src.frontin.api.models.responses import APIResponse, PaginatedResponse
from src.frontin.api.services.calendar_service import CalendarService

router = APIRouter()


def _get_calendar_service() -> CalendarService:
    """Dependency to get calendar service"""
    return CalendarService()


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _convert_event_to_response(event: dict) -> CalendarEventResponse:
    """Convert event dict to response model"""
    return CalendarEventResponse(
        id=event.get("id", ""),
        title=event.get("title", ""),
        start=_parse_datetime(event.get("start")) or datetime.now(timezone.utc),
        end=_parse_datetime(event.get("end")) or datetime.now(timezone.utc),
        location=event.get("location"),
        is_online=event.get("is_online", False),
        meeting_url=event.get("meeting_url"),
        organizer=event.get("organizer"),
        attendees=[
            CalendarAttendeeResponse(
                email=a.get("email", ""),
                name=a.get("name"),
                response_status=a.get("response_status", "none"),
                is_organizer=a.get("is_organizer", False),
            )
            for a in event.get("attendees", [])
        ],
        is_all_day=event.get("is_all_day", False),
        is_recurring=event.get("is_recurring", False),
        description=event.get("description"),
        status=event.get("status", "confirmed"),
    )


@router.get("/events", response_model=PaginatedResponse[list[CalendarEventResponse]])
async def list_calendar_events(
    start_date: datetime | None = Query(None, description="Start of date range"),
    end_date: datetime | None = Query(None, description="End of date range"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: CalendarService = Depends(_get_calendar_service),
) -> PaginatedResponse[list[CalendarEventResponse]]:
    """
    List calendar events

    Returns events within the specified date range.
    """
    try:
        # Fetch all matching events (pagination is applied client-side for simplicity)
        events = await service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=page * page_size,
        )

        # Apply pagination
        total = len(events)
        start = (page - 1) * page_size
        end = start + page_size
        page_events = events[start:end]

        return PaginatedResponse(
            success=True,
            data=[_convert_event_to_response(e) for e in page_events],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/events/{event_id}", response_model=APIResponse[CalendarEventResponse])
async def get_calendar_event(
    event_id: str,
    service: CalendarService = Depends(_get_calendar_service),
) -> APIResponse[CalendarEventResponse]:
    """
    Get single calendar event

    Returns full event details including attendees.
    """
    try:
        event = await service.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")

        return APIResponse(
            success=True,
            data=_convert_event_to_response(event),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/today", response_model=APIResponse[TodayEventsResponse])
async def get_today_events(
    service: CalendarService = Depends(_get_calendar_service),
) -> APIResponse[TodayEventsResponse]:
    """
    Get today's calendar events

    Returns all events scheduled for today.
    """
    try:
        result = await service.get_today_events()

        return APIResponse(
            success=True,
            data=TodayEventsResponse(
                date=result.get("date", ""),
                total_events=result.get("total_events", 0),
                meetings=result.get("meetings", 0),
                all_day_events=result.get("all_day_events", 0),
                events=[_convert_event_to_response(e) for e in result.get("events", [])],
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/events/{event_id}/respond", response_model=APIResponse[dict])
async def respond_to_event(
    event_id: str,
    request: RespondToEventRequest,
    service: CalendarService = Depends(_get_calendar_service),
) -> APIResponse[dict]:
    """
    Respond to an event invitation

    Send accept, decline, or tentative response to an event.
    """
    valid_responses = ["accept", "decline", "tentative"]
    if request.response.lower() not in valid_responses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response. Must be one of: {valid_responses}",
        )

    try:
        success = await service.respond_to_event(
            event_id=event_id,
            response=request.response.lower(),
            message=request.message,
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to respond to event {event_id}",
            )

        return APIResponse(
            success=True,
            data={
                "event_id": event_id,
                "response": request.response,
                "sent": True,
            },
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/poll", response_model=APIResponse[CalendarPollResponse])
async def poll_calendar(
    service: CalendarService = Depends(_get_calendar_service),
) -> APIResponse[CalendarPollResponse]:
    """
    Poll calendar for updates

    Syncs calendar events and processes any new/updated events.
    """
    try:
        result = await service.poll()

        return APIResponse(
            success=True,
            data=CalendarPollResponse(
                events_fetched=result.get("events_fetched", 0),
                events_new=result.get("events_new", 0),
                events_updated=result.get("events_updated", 0),
                polled_at=_parse_datetime(result.get("polled_at")) or datetime.now(timezone.utc),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/events", response_model=APIResponse[EventCreatedResponse])
async def create_calendar_event(
    request: CreateEventRequest,
    service: CalendarService = Depends(_get_calendar_service),
) -> APIResponse[EventCreatedResponse]:
    """
    Create a new calendar event

    Creates an event in the user's calendar. Supports creating
    Teams meetings when is_online=true.
    """
    # Validate start < end
    if request.start >= request.end:
        raise HTTPException(
            status_code=400,
            detail="Start time must be before end time",
        )

    try:
        result = await service.create_event(
            title=request.title,
            start=request.start,
            end=request.end,
            location=request.location,
            description=request.description,
            attendees=request.attendees,
            is_online=request.is_online,
            reminder_minutes=request.reminder_minutes,
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create calendar event",
            )

        return APIResponse(
            success=True,
            data=EventCreatedResponse(
                id=result["id"],
                title=result["title"],
                start=_parse_datetime(result["start"]) or request.start,
                end=_parse_datetime(result["end"]) or request.end,
                web_link=result.get("web_link"),
                meeting_url=result.get("meeting_url"),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/events/{event_id}", response_model=APIResponse[CalendarEventResponse])
async def update_calendar_event(
    event_id: str,
    request: UpdateEventRequest,
    service: CalendarService = Depends(_get_calendar_service),
) -> APIResponse[CalendarEventResponse]:
    """
    Update an existing calendar event

    Updates specified fields of an event. Only provided fields are updated.
    """
    # Validate start < end if both provided
    if request.start and request.end and request.start >= request.end:
        raise HTTPException(
            status_code=400,
            detail="Start time must be before end time",
        )

    try:
        result = await service.update_event(
            event_id=event_id,
            title=request.title,
            start=request.start,
            end=request.end,
            location=request.location,
            description=request.description,
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Event not found or failed to update: {event_id}",
            )

        return APIResponse(
            success=True,
            data=_convert_event_to_response(result),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/events/{event_id}", response_model=APIResponse[EventDeletedResponse])
async def delete_calendar_event(
    event_id: str,
    service: CalendarService = Depends(_get_calendar_service),
) -> APIResponse[EventDeletedResponse]:
    """
    Delete a calendar event

    Permanently deletes the event from the calendar.
    """
    try:
        success = await service.delete_event(event_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Event not found or failed to delete: {event_id}",
            )

        return APIResponse(
            success=True,
            data=EventDeletedResponse(
                event_id=event_id,
                deleted=True,
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
