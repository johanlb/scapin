"""
Events Router

API endpoints for event management (snooze, undo, action history).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.models.events import (
    ActionHistoryResponse,
    EventsStatsResponse,
    SnoozedItemResponse,
    SnoozeRequest,
    SnoozeResponse,
    UndoRequest,
    UndoResponse,
)
from src.jeeves.api.models.responses import APIResponse, PaginatedResponse
from src.jeeves.api.services.events_service import EventsService

router = APIRouter()


def _get_events_service() -> EventsService:
    """Dependency to get events service"""
    return EventsService()


@router.get("/snoozed", response_model=PaginatedResponse[list[SnoozedItemResponse]])
async def list_snoozed_items(
    item_type: str | None = Query(None, description="Filter by item type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: EventsService = Depends(_get_events_service),
) -> PaginatedResponse[list[SnoozedItemResponse]]:
    """
    List snoozed items

    Returns items that are currently snoozed, ordered by expiration time.
    """
    try:
        items = await service.get_snoozed_items(item_type=item_type)

        # Apply pagination
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        return PaginatedResponse(
            success=True,
            data=[
                SnoozedItemResponse(
                    snooze_id=item["snooze_id"],
                    item_id=item["item_id"],
                    item_type=item["item_type"],
                    snoozed_at=item["snoozed_at"],
                    snooze_until=item["snooze_until"],
                    reason=item.get("reason"),
                    time_remaining_minutes=item["time_remaining_minutes"],
                    is_expired=item["is_expired"],
                    item_preview=item.get("item_preview", {}),
                )
                for item in page_items
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/snooze", response_model=APIResponse[SnoozeResponse])
async def snooze_item(
    item_id: str,
    request: SnoozeRequest,
    service: EventsService = Depends(_get_events_service),
) -> APIResponse[SnoozeResponse]:
    """
    Snooze a queue item

    The item will be hidden until the snooze expires.
    Provide one of: hours, days, or until (datetime).
    """
    try:
        record = await service.snooze_item(
            item_id=item_id,
            hours=request.hours,
            days=request.days,
            until=request.until,
            reason=request.reason,
        )

        return APIResponse(
            success=True,
            data=SnoozeResponse(
                snooze_id=record.snooze_id,
                item_id=record.item_id,
                item_type=record.item_type,
                snoozed_at=record.snoozed_at,
                snooze_until=record.snooze_until,
                reason=record.reason_text,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{item_id}/snooze", response_model=APIResponse[SnoozeResponse])
async def unsnooze_item(
    item_id: str,
    service: EventsService = Depends(_get_events_service),
) -> APIResponse[SnoozeResponse]:
    """
    Unsnooze an item (cancel snooze)

    The item will be restored to its previous status.
    """
    try:
        record = await service.unsnooze_item(item_id)

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"No active snooze found for item {item_id}",
            )

        return APIResponse(
            success=True,
            data=SnoozeResponse(
                snooze_id=record.snooze_id,
                item_id=record.item_id,
                item_type=record.item_type,
                snoozed_at=record.snoozed_at,
                snooze_until=record.snooze_until,
                reason=record.reason_text,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/history", response_model=PaginatedResponse[list[ActionHistoryResponse]])
async def get_action_history(
    item_id: str | None = Query(None, description="Filter by item ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: EventsService = Depends(_get_events_service),
) -> PaginatedResponse[list[ActionHistoryResponse]]:
    """
    Get action history

    Returns recent actions that can potentially be undone.
    """
    try:
        actions = await service.get_action_history(
            item_id=item_id,
            limit=page * page_size,
        )

        # Apply pagination
        total = len(actions)
        start = (page - 1) * page_size
        end = start + page_size
        page_actions = actions[start:end]

        return PaginatedResponse(
            success=True,
            data=[
                ActionHistoryResponse(
                    action_id=action.action_id,
                    action_type=action.action_type.value,
                    item_id=action.item_id,
                    item_type=action.item_type,
                    executed_at=action.executed_at,
                    status=action.status.value,
                    can_undo=action.status.value == "completed",
                    action_data=action.action_data,
                )
                for action in page_actions
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/undo", response_model=APIResponse[UndoResponse])
async def undo_action(
    item_id: str,
    request: UndoRequest = UndoRequest(),
    service: EventsService = Depends(_get_events_service),
) -> APIResponse[UndoResponse]:
    """
    Undo the last action on an item

    Finds the most recent completed action for the item and undoes it.
    """
    try:
        # Get the last action for this item
        actions = await service.get_action_history(item_id=item_id, limit=1)

        if not actions:
            raise HTTPException(
                status_code=404,
                detail=f"No actions found for item {item_id}",
            )

        action = actions[0]

        if action.status.value != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Last action cannot be undone (status: {action.status.value})",
            )

        # Perform undo
        result = await service.undo_action(
            action_id=action.action_id,
            reason=request.reason,
        )

        return APIResponse(
            success=True,
            data=UndoResponse(
                action_id=action.action_id,
                item_id=item_id,
                success=result.get("success", False),
                message=result.get("message", ""),
                undo_result=result,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/wake-expired", response_model=APIResponse[dict])
async def wake_expired_snoozes(
    service: EventsService = Depends(_get_events_service),
) -> APIResponse[dict]:
    """
    Wake up all expired snoozes

    This endpoint should be called periodically (e.g., by a background task)
    to process expired snoozes and restore items to the queue.
    """
    try:
        woken = await service.wake_expired_snoozes()

        return APIResponse(
            success=True,
            data={
                "woken_count": len(woken),
                "woken_items": [
                    {
                        "snooze_id": r.snooze_id,
                        "item_id": r.item_id,
                    }
                    for r in woken
                ],
            },
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats", response_model=APIResponse[EventsStatsResponse])
async def get_events_stats(
    service: EventsService = Depends(_get_events_service),
) -> APIResponse[EventsStatsResponse]:
    """
    Get events statistics

    Returns statistics about snoozes and action history.
    """
    try:
        stats = await service.get_stats()

        return APIResponse(
            success=True,
            data=EventsStatsResponse(
                snoozed_count=stats.get("snoozed_count", 0),
                expired_pending=stats.get("expired_pending", 0),
                total_actions=stats.get("total_actions", 0),
                undoable_actions=stats.get("undoable_actions", 0),
                actions_by_type=stats.get("actions_by_type", {}),
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
