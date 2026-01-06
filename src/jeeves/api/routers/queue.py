"""
Queue Router

API endpoints for review queue management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.entities import AUTO_APPLY_THRESHOLD
from src.jeeves.api.models.queue import (
    ActionOptionResponse,
    ApproveRequest,
    EntityResponse,
    ModifyRequest,
    ProposedNoteResponse,
    ProposedTaskResponse,
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

    # Convert entities to response format
    raw_entities = analysis.get("entities", {})
    entities_by_type: dict[str, list[EntityResponse]] = {}
    for entity_type, entity_list in raw_entities.items():
        entities_by_type[entity_type] = [
            EntityResponse(
                type=e.get("type", entity_type),
                value=e.get("value", ""),
                confidence=e.get("confidence", 0.0),
                source=e.get("source", "extraction"),
                metadata=e.get("metadata", {}),
            )
            for e in entity_list
        ]

    # Convert proposed_notes to response format
    raw_proposed_notes = analysis.get("proposed_notes", [])
    proposed_notes = [
        ProposedNoteResponse(
            action=pn.get("action", "create"),
            note_type=pn.get("note_type", "general"),
            title=pn.get("title", ""),
            content_summary=pn.get("content_summary", ""),
            confidence=pn.get("confidence", 0.0),
            reasoning=pn.get("reasoning", ""),
            target_note_id=pn.get("target_note_id"),
            auto_applied=pn.get("confidence", 0) >= AUTO_APPLY_THRESHOLD,
        )
        for pn in raw_proposed_notes
    ]

    # Convert proposed_tasks to response format
    raw_proposed_tasks = analysis.get("proposed_tasks", [])
    proposed_tasks = [
        ProposedTaskResponse(
            title=pt.get("title", ""),
            note=pt.get("note", ""),
            project=pt.get("project"),
            due_date=pt.get("due_date"),
            confidence=pt.get("confidence", 0.0),
            reasoning=pt.get("reasoning", ""),
            auto_applied=pt.get("confidence", 0) >= AUTO_APPLY_THRESHOLD,
        )
        for pt in raw_proposed_tasks
    ]

    return QueueItemResponse(
        id=item.get("id", ""),
        account_id=item.get("account_id"),
        queued_at=_parse_datetime(item.get("queued_at")) or datetime.now(timezone.utc),
        metadata=QueueItemMetadata(
            id=str(metadata.get("id", "")),  # IMAP returns int, API expects str
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
            summary=analysis.get("summary"),
            options=[
                ActionOptionResponse(
                    action=opt.get("action", ""),
                    destination=opt.get("destination"),
                    confidence=opt.get("confidence", 0),
                    reasoning=opt.get("reasoning", ""),
                    reasoning_detailed=opt.get("reasoning_detailed"),
                    is_recommended=opt.get("is_recommended", False),
                )
                for opt in analysis.get("options", [])
            ],
            entities=entities_by_type,
            proposed_notes=proposed_notes,
            proposed_tasks=proposed_tasks,
            context_used=analysis.get("context_used", []),
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
    Approve a queue item and execute the IMAP action

    Marks the item as approved and executes the action (archive/delete).
    """
    try:
        item = await service.approve_item(
            item_id=item_id,
            modified_action=request.modified_action,
            modified_category=request.modified_category,
            destination=request.destination,
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
    Modify a queue item's action and execute it

    Changes the suggested action to a different one and executes it.
    """
    try:
        item = await service.modify_item(
            item_id=item_id,
            action=request.action,
            category=request.category,
            reasoning=request.reasoning,
            destination=request.destination,
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
