"""
Queue Router

API endpoints for review queue management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.models.queue import (
    ApproveRequest,
    ModifyRequest,
    QueueItemAnalysis,
    QueueItemContent,
    QueueItemMetadata,
    QueueItemResponse,
    QueueStatsResponse,
    RejectRequest,
)
from src.jeeves.api.models.responses import APIResponse, PaginatedResponse
from src.jeeves.api.services.queue_service import QueueService

router = APIRouter()


def _get_queue_service() -> QueueService:
    """Dependency to get queue service"""
    return QueueService()


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _convert_item_to_response(item: dict) -> QueueItemResponse:
    """Convert raw queue item to response model"""
    metadata = item.get("metadata", {})
    analysis = item.get("analysis", {})
    content = item.get("content", {})

    return QueueItemResponse(
        id=item.get("id", ""),
        account_id=item.get("account_id"),
        queued_at=_parse_datetime(item.get("queued_at")) or datetime.now(timezone.utc),
        metadata=QueueItemMetadata(
            id=metadata.get("id", ""),
            subject=metadata.get("subject", ""),
            from_address=metadata.get("from_address", ""),
            from_name=metadata.get("from_name", ""),
            date=_parse_datetime(metadata.get("date")),
            has_attachments=metadata.get("has_attachments", False),
            folder=metadata.get("folder"),
        ),
        analysis=QueueItemAnalysis(
            action=analysis.get("action", ""),
            confidence=analysis.get("confidence", 0),
            category=analysis.get("category"),
            reasoning=analysis.get("reasoning", ""),
        ),
        content=QueueItemContent(
            preview=content.get("preview", ""),
        ),
        status=item.get("status", "pending"),
        reviewed_at=_parse_datetime(item.get("reviewed_at")),
        review_decision=item.get("review_decision"),
    )


@router.get("", response_model=PaginatedResponse[list[QueueItemResponse]])
async def list_queue_items(
    account_id: str | None = Query(None, description="Filter by account"),
    status: str = Query("pending", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: QueueService = Depends(_get_queue_service),
) -> PaginatedResponse[list[QueueItemResponse]]:
    """
    List queue items with pagination

    Returns pending items awaiting review by default.
    """
    try:
        items, total = await service.list_items(
            account_id=account_id,
            status=status,
            page=page,
            page_size=page_size,
        )

        return PaginatedResponse(
            success=True,
            data=[_convert_item_to_response(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats", response_model=APIResponse[QueueStatsResponse])
async def get_queue_stats(
    service: QueueService = Depends(_get_queue_service),
) -> APIResponse[QueueStatsResponse]:
    """
    Get queue statistics

    Returns counts by status and account.
    """
    try:
        stats = await service.get_stats()

        return APIResponse(
            success=True,
            data=QueueStatsResponse(
                total=stats.get("total", 0),
                by_status=stats.get("by_status", {}),
                by_account=stats.get("by_account", {}),
                oldest_item=_parse_datetime(stats.get("oldest_item")),
                newest_item=_parse_datetime(stats.get("newest_item")),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{item_id}", response_model=APIResponse[QueueItemResponse])
async def get_queue_item(
    item_id: str,
    service: QueueService = Depends(_get_queue_service),
) -> APIResponse[QueueItemResponse]:
    """
    Get single queue item by ID

    Returns full item details including content preview.
    """
    try:
        item = await service.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: {item_id}")

        return APIResponse(
            success=True,
            data=_convert_item_to_response(item),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/approve", response_model=APIResponse[QueueItemResponse])
async def approve_queue_item(
    item_id: str,
    request: ApproveRequest = ApproveRequest(),
    service: QueueService = Depends(_get_queue_service),
) -> APIResponse[QueueItemResponse]:
    """
    Approve a queue item

    Marks the item as approved, optionally with modified action/category.
    """
    try:
        item = await service.approve_item(
            item_id=item_id,
            modified_action=request.modified_action,
            modified_category=request.modified_category,
        )
        if not item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: {item_id}")

        return APIResponse(
            success=True,
            data=_convert_item_to_response(item),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/modify", response_model=APIResponse[QueueItemResponse])
async def modify_queue_item(
    item_id: str,
    request: ModifyRequest,
    service: QueueService = Depends(_get_queue_service),
) -> APIResponse[QueueItemResponse]:
    """
    Modify a queue item's action

    Changes the suggested action to a different one.
    """
    try:
        item = await service.modify_item(
            item_id=item_id,
            action=request.action,
            category=request.category,
            reasoning=request.reasoning,
        )
        if not item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: {item_id}")

        return APIResponse(
            success=True,
            data=_convert_item_to_response(item),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/reject", response_model=APIResponse[QueueItemResponse])
async def reject_queue_item(
    item_id: str,
    request: RejectRequest = RejectRequest(),
    service: QueueService = Depends(_get_queue_service),
) -> APIResponse[QueueItemResponse]:
    """
    Reject a queue item

    Marks the item as rejected (no action will be taken).
    """
    try:
        item = await service.reject_item(
            item_id=item_id,
            reason=request.reason,
        )
        if not item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: {item_id}")

        return APIResponse(
            success=True,
            data=_convert_item_to_response(item),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{item_id}", response_model=APIResponse[dict])
async def delete_queue_item(
    item_id: str,
    service: QueueService = Depends(_get_queue_service),
) -> APIResponse[dict]:
    """
    Delete a queue item

    Permanently removes the item from the queue.
    """
    try:
        success = await service.delete_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Queue item not found: {item_id}")

        return APIResponse(
            success=True,
            data={"deleted": item_id},
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
