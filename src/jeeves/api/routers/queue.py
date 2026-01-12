"""
Queue Router

API endpoints for review queue management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.entities import should_auto_apply
from src.jeeves.api.deps import get_queue_service
from src.jeeves.api.models.queue import (
    ActionOptionResponse,
    ApproveRequest,
    AttachmentResponse,
    BulkReanalyzeResponse,
    EntityResponse,
    ExtractionConfidenceResponse,
    ModifyRequest,
    ProposedNoteResponse,
    ProposedTaskResponse,
    QueueItemAnalysis,
    QueueItemContent,
    QueueItemMetadata,
    QueueItemResponse,
    QueueStatsResponse,
    ReanalyzeRequest,
    ReanalyzeResponse,
    RejectRequest,
    SnoozeRequest,
    SnoozeResponse,
)
from src.jeeves.api.models.responses import APIResponse, PaginatedResponse
from src.jeeves.api.services.queue_service import EnrichmentFailedError, QueueService

router = APIRouter()


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_extraction_confidence(
    conf_data: dict | float | None,
) -> tuple[float, ExtractionConfidenceResponse | None, str | None]:
    """
    Parse extraction confidence data.

    Returns:
        tuple: (overall_score, confidence_details, weakness_label)
    """
    if conf_data is None:
        return 0.8, None, None

    if isinstance(conf_data, (int, float)):
        # Legacy single score format
        return float(conf_data), None, None

    if isinstance(conf_data, dict):
        # New 4-dimension format
        quality = float(conf_data.get("quality", 0.8))
        target_match = float(conf_data.get("target_match", 0.8))
        relevance = float(conf_data.get("relevance", 0.8))
        completeness = float(conf_data.get("completeness", 0.8))

        # Calculate geometric mean
        overall = (quality * target_match * relevance * completeness) ** 0.25

        # Use pre-computed overall if available (from backend)
        overall = float(conf_data.get("overall", overall))

        # Get weakness label if provided
        weakness_label = conf_data.get("weakness_label")

        details = ExtractionConfidenceResponse(
            quality=quality,
            target_match=target_match,
            relevance=relevance,
            completeness=completeness,
            overall=overall,
        )
        return overall, details, weakness_label

    return 0.8, None, None


def _convert_item_to_response(item: dict) -> QueueItemResponse:
    """Convert raw queue item to response model"""
    metadata = item.get("metadata", {})
    analysis = item.get("analysis", {})
    content = item.get("content", {})

    # Convert entities to response format
    # Handle two formats:
    # - New format: {"type": [{"type": "...", "value": "...", ...}, ...]}
    # - Old format: {"entity_name": {"type": "..."}} (from broken multi-pass)
    raw_entities = analysis.get("entities", {})
    entities_by_type: dict[str, list[EntityResponse]] = {}
    for entity_type, entity_data in raw_entities.items():
        # Check if entity_data is a list (new format) or dict (old format)
        if isinstance(entity_data, list):
            # New format: list of entity dicts
            entities_by_type[entity_type] = [
                EntityResponse(
                    type=e.get("type", entity_type) if isinstance(e, dict) else entity_type,
                    value=e.get("value", "") if isinstance(e, dict) else str(e),
                    confidence=e.get("confidence", 0.0) if isinstance(e, dict) else 0.0,
                    source=e.get("source", "extraction") if isinstance(e, dict) else "extraction",
                    metadata=e.get("metadata", {}) if isinstance(e, dict) else {},
                )
                for e in entity_data
            ]
        elif isinstance(entity_data, dict):
            # Old format: entity_type is actually the entity name, entity_data is info
            # Convert to "discovered" type
            if "discovered" not in entities_by_type:
                entities_by_type["discovered"] = []
            entities_by_type["discovered"].append(
                EntityResponse(
                    type=entity_data.get("type", "discovered"),
                    value=entity_type,  # The key is the entity name
                    confidence=entity_data.get("confidence", 1.0),
                    source=entity_data.get("source", "extraction"),
                    metadata={},
                )
            )

    # Convert proposed_notes to response format
    raw_proposed_notes = analysis.get("proposed_notes", [])
    proposed_notes = []
    for pn in raw_proposed_notes:
        # Parse 4-dimension confidence
        conf_score, conf_details, weakness_label = _parse_extraction_confidence(
            pn.get("confidence")
        )
        # Also check for pre-computed confidence_score from backend
        if "confidence_score" in pn:
            conf_score = float(pn["confidence_score"])
        # Get weakness_label from backend if available
        if "weakness_label" in pn:
            weakness_label = pn["weakness_label"]

        required = pn.get("required", False)
        manually_approved = pn.get("manually_approved")

        proposed_notes.append(
            ProposedNoteResponse(
                action=pn.get("action", "create"),
                note_type=pn.get("note_type", "general"),
                title=pn.get("title", ""),
                content_summary=pn.get("content_summary", ""),
                confidence=conf_score,
                confidence_details=conf_details,
                weakness_label=weakness_label,
                reasoning=pn.get("reasoning", ""),
                target_note_id=pn.get("target_note_id"),
                auto_applied=should_auto_apply(conf_score, required, manually_approved),
                required=required,
                importance=pn.get("importance", "moyenne"),
                manually_approved=manually_approved,
            )
        )

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
            auto_applied=should_auto_apply(pt.get("confidence", 0), False),  # Tasks are not required
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
            attachments=[
                AttachmentResponse(
                    filename=att.get("filename", ""),
                    size_bytes=att.get("size_bytes", 0),
                    content_type=att.get("content_type", "application/octet-stream"),
                )
                for att in metadata.get("attachments", [])
            ],
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
            draft_reply=analysis.get("draft_reply"),
        ),
        content=QueueItemContent(
            preview=content.get("preview", ""),
            html_body=content.get("html_body"),
            full_text=content.get("full_text"),
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
    service: QueueService = Depends(get_queue_service),
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
    service: QueueService = Depends(get_queue_service),
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
    service: QueueService = Depends(get_queue_service),
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
    service: QueueService = Depends(get_queue_service),
) -> APIResponse[QueueItemResponse]:
    """
    Approve a queue item and execute the IMAP action

    Marks the item as approved and executes the action (archive/delete).

    Returns 409 Conflict if required enrichments fail (to prevent data loss).
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
    except EnrichmentFailedError as e:
        # Required enrichments failed - return 409 Conflict to prevent data loss
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(e),
                "item_id": e.item_id,
                "failed_enrichments": e.failed_enrichments,
                "action_aborted": e.action,
            },
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/modify", response_model=APIResponse[QueueItemResponse])
async def modify_queue_item(
    item_id: str,
    request: ModifyRequest,
    service: QueueService = Depends(get_queue_service),
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
    service: QueueService = Depends(get_queue_service),
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
    service: QueueService = Depends(get_queue_service),
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


@router.post("/{item_id}/snooze", response_model=APIResponse[SnoozeResponse])
async def snooze_queue_item(
    item_id: str,
    request: SnoozeRequest,
    service: QueueService = Depends(get_queue_service),
) -> APIResponse[SnoozeResponse]:
    """
    Snooze a queue item

    Temporarily hides the item from the queue. It will reappear when the snooze expires.

    Options:
    - later_today: 3 hours from now
    - tomorrow: Tomorrow at 9 AM
    - this_weekend: Saturday at 10 AM
    - next_week: Next Monday at 9 AM
    - custom: Use custom_hours parameter (1-168 hours)
    """
    try:
        record = await service.snooze_item(
            item_id=item_id,
            snooze_option=request.snooze_option,
            custom_hours=request.custom_hours,
            reason=request.reason,
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"Queue item not found: {item_id}")

        return APIResponse(
            success=True,
            data=SnoozeResponse(
                snooze_id=record.snooze_id,
                item_id=record.item_id,
                snoozed_at=record.snoozed_at.isoformat(),
                snooze_until=record.snooze_until.isoformat(),
                snooze_option=request.snooze_option,
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/unsnooze", response_model=APIResponse[QueueItemResponse])
async def unsnooze_queue_item(
    item_id: str,
    service: QueueService = Depends(get_queue_service),
) -> APIResponse[QueueItemResponse]:
    """
    Unsnooze a queue item

    Manually returns a snoozed item to the pending queue.
    """
    try:
        item = await service.unsnooze_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Snoozed item not found: {item_id}")

        return APIResponse(
            success=True,
            data=_convert_item_to_response(item),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/undo", response_model=APIResponse[QueueItemResponse])
async def undo_queue_item(
    item_id: str,
    service: QueueService = Depends(get_queue_service),
) -> APIResponse[QueueItemResponse]:
    """
    Undo an approved queue item action

    Reverses the IMAP action (moves email back to original folder) and returns the item to pending status.
    Only works for recently approved items that haven't been processed further.
    """
    try:
        item = await service.undo_item(item_id)
        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Cannot undo item {item_id}: not found or action cannot be undone",
            )

        return APIResponse(
            success=True,
            data=_convert_item_to_response(item),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{item_id}/can-undo", response_model=APIResponse[dict])
async def can_undo_queue_item(
    item_id: str,
    service: QueueService = Depends(get_queue_service),
) -> APIResponse[dict]:
    """
    Check if a queue item's action can be undone

    Returns whether the undo operation is available for this item.
    """
    try:
        can_undo = await service.can_undo_item(item_id)

        return APIResponse(
            success=True,
            data={"item_id": item_id, "can_undo": can_undo},
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{item_id}/reanalyze", response_model=APIResponse[ReanalyzeResponse])
async def reanalyze_queue_item(
    item_id: str,
    request: ReanalyzeRequest,
    service: QueueService = Depends(get_queue_service),
) -> APIResponse[ReanalyzeResponse]:
    """
    Reanalyze a queue item with user instruction

    Takes the user's custom instruction into account and generates a new analysis.
    The new analysis will replace the original one.

    Modes:
    - immediate: Wait for the new analysis (synchronous)
    - background: Queue for later and return immediately
    """
    try:
        result = await service.reanalyze_item(
            item_id=item_id,
            user_instruction=request.user_instruction,
            mode=request.mode,
            force_model=request.force_model,
        )
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Queue item not found: {item_id}",
            )

        return APIResponse(
            success=True,
            data=ReanalyzeResponse(
                item_id=item_id,
                status=result.get("status", "complete"),
                analysis_id=result.get("analysis_id"),
                new_analysis=_convert_analysis_to_response(result.get("new_analysis"))
                if result.get("new_analysis")
                else None,
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/reanalyze-all", response_model=APIResponse[BulkReanalyzeResponse])
async def reanalyze_all_pending(
    service: QueueService = Depends(get_queue_service),
) -> APIResponse[BulkReanalyzeResponse]:
    """
    Reanalyze all pending queue items.

    This triggers a fresh AI analysis for all items currently in 'pending' status.
    Useful when the analysis template or model has been updated.
    """
    try:
        result = await service.reanalyze_all_pending()
        return APIResponse(
            success=True,
            data=BulkReanalyzeResponse(
                total_items=result.get("total", 0),
                started=result.get("started", 0),
                failed=result.get("failed", 0),
                status=result.get("status", "processing"),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _convert_analysis_to_response(analysis: dict | None) -> QueueItemAnalysis | None:
    """Convert raw analysis dict to response model"""
    if not analysis:
        return None

    # Convert entities to response format
    # Handle two formats:
    # - New format: {"type": [{"type": "...", "value": "...", ...}, ...]}
    # - Old format: {"entity_name": {"type": "..."}} (from broken multi-pass)
    raw_entities = analysis.get("entities", {})
    entities_by_type: dict[str, list[EntityResponse]] = {}
    for entity_type, entity_data in raw_entities.items():
        # Check if entity_data is a list (new format) or dict (old format)
        if isinstance(entity_data, list):
            # New format: list of entity dicts
            entities_by_type[entity_type] = [
                EntityResponse(
                    type=e.get("type", entity_type) if isinstance(e, dict) else entity_type,
                    value=e.get("value", "") if isinstance(e, dict) else str(e),
                    confidence=e.get("confidence", 0.0) if isinstance(e, dict) else 0.0,
                    source=e.get("source", "extraction") if isinstance(e, dict) else "extraction",
                    metadata=e.get("metadata", {}) if isinstance(e, dict) else {},
                )
                for e in entity_data
            ]
        elif isinstance(entity_data, dict):
            # Old format: entity_type is actually the entity name, entity_data is info
            # Convert to "discovered" type
            if "discovered" not in entities_by_type:
                entities_by_type["discovered"] = []
            entities_by_type["discovered"].append(
                EntityResponse(
                    type=entity_data.get("type", "discovered"),
                    value=entity_type,  # The key is the entity name
                    confidence=entity_data.get("confidence", 1.0),
                    source=entity_data.get("source", "extraction"),
                    metadata={},
                )
            )

    # Convert proposed_notes to response format
    raw_proposed_notes = analysis.get("proposed_notes", [])
    proposed_notes = []
    for pn in raw_proposed_notes:
        # Parse 4-dimension confidence
        conf_score, conf_details, weakness_label = _parse_extraction_confidence(
            pn.get("confidence")
        )
        # Also check for pre-computed confidence_score from backend
        if "confidence_score" in pn:
            conf_score = float(pn["confidence_score"])
        # Get weakness_label from backend if available
        if "weakness_label" in pn:
            weakness_label = pn["weakness_label"]

        required = pn.get("required", False)
        manually_approved = pn.get("manually_approved")

        proposed_notes.append(
            ProposedNoteResponse(
                action=pn.get("action", "create"),
                note_type=pn.get("note_type", "general"),
                title=pn.get("title", ""),
                content_summary=pn.get("content_summary", ""),
                confidence=conf_score,
                confidence_details=conf_details,
                weakness_label=weakness_label,
                reasoning=pn.get("reasoning", ""),
                target_note_id=pn.get("target_note_id"),
                auto_applied=should_auto_apply(conf_score, required, manually_approved),
                required=required,
                importance=pn.get("importance", "moyenne"),
                manually_approved=manually_approved,
            )
        )

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
            auto_applied=should_auto_apply(pt.get("confidence", 0), False),  # Tasks are not required
        )
        for pt in raw_proposed_tasks
    ]

    return QueueItemAnalysis(
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
        draft_reply=analysis.get("draft_reply"),
    )
