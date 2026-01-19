"""
Drafts Router

API endpoints for managing email reply drafts.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.frontin.api.models.drafts import (
    DraftCreateRequest,
    DraftDiscardRequest,
    DraftResponse,
    DraftStatsResponse,
    DraftUpdateRequest,
    GenerateDraftRequest,
)
from src.frontin.api.models.responses import APIResponse, PaginatedResponse
from src.frontin.api.services.drafts_service import DraftsService, get_drafts_service

router = APIRouter()


def _draft_to_response(draft) -> DraftResponse:
    """Convert DraftReply to DraftResponse"""
    return DraftResponse(
        draft_id=draft.draft_id,
        email_id=draft.email_id,
        account_email=draft.account_email,
        message_id=draft.message_id,
        subject=draft.subject,
        to_addresses=draft.to_addresses,
        cc_addresses=draft.cc_addresses,
        bcc_addresses=draft.bcc_addresses,
        body=draft.body,
        body_format=draft.body_format.value,
        ai_generated=draft.ai_generated,
        ai_confidence=draft.ai_confidence,
        ai_reasoning=draft.ai_reasoning,
        status=draft.status.value,
        original_subject=draft.original_subject,
        original_from=draft.original_from,
        original_date=draft.original_date,
        user_edited=draft.user_edited,
        edit_history=draft.edit_history,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        sent_at=draft.sent_at,
        discarded_at=draft.discarded_at,
    )


@router.get("", response_model=PaginatedResponse[list[DraftResponse]])
async def list_drafts(
    status: str | None = Query(None, description="Filter by status"),
    account_email: str | None = Query(None, description="Filter by account email"),
    email_id: int | None = Query(None, description="Filter by original email ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: DraftsService = Depends(get_drafts_service),
) -> PaginatedResponse[list[DraftResponse]]:
    """
    List drafts with optional filters

    Returns paginated list of drafts.
    """
    try:
        drafts = await service.list_drafts(
            status=status,
            account_email=account_email,
            email_id=email_id,
        )

        # Apply pagination
        total = len(drafts)
        start = (page - 1) * page_size
        end = start + page_size
        page_drafts = drafts[start:end]

        return PaginatedResponse(
            success=True,
            data=[_draft_to_response(d) for d in page_drafts],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
            timestamp=datetime.now(timezone.utc),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/pending", response_model=APIResponse[list[DraftResponse]])
async def list_pending_drafts(
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[list[DraftResponse]]:
    """
    List pending (unsent) drafts

    Returns all drafts with status 'draft'.
    """
    try:
        drafts = await service.get_pending_drafts()

        return APIResponse(
            success=True,
            data=[_draft_to_response(d) for d in drafts],
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats", response_model=APIResponse[DraftStatsResponse])
async def get_draft_stats(
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[DraftStatsResponse]:
    """
    Get draft statistics

    Returns counts by status and by account.
    """
    try:
        stats = await service.get_stats()

        return APIResponse(
            success=True,
            data=DraftStatsResponse(
                total=stats.get("total", 0),
                by_status=stats.get("by_status", {}),
                by_account=stats.get("by_account", {}),
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{draft_id}", response_model=APIResponse[DraftResponse])
async def get_draft(
    draft_id: str,
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[DraftResponse]:
    """
    Get a single draft by ID
    """
    try:
        draft = await service.get_draft(draft_id)

        if not draft:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")

        return APIResponse(
            success=True,
            data=_draft_to_response(draft),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=APIResponse[DraftResponse])
async def create_draft(
    request: DraftCreateRequest,
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[DraftResponse]:
    """
    Create a draft manually

    Creates a new draft without AI generation.
    """
    try:
        draft = await service.create_draft(
            email_id=request.email_id,
            account_email=request.account_email,
            subject=request.subject,
            body=request.body,
            to_addresses=request.to_addresses,
            cc_addresses=request.cc_addresses,
            body_format=request.body_format,
            original_subject=request.original_subject,
            original_from=request.original_from,
        )

        return APIResponse(
            success=True,
            data=_draft_to_response(draft),
            timestamp=datetime.now(timezone.utc),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate", response_model=APIResponse[DraftResponse])
async def generate_draft(
    request: GenerateDraftRequest,
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[DraftResponse]:
    """
    Generate an AI-assisted draft

    Uses PrepareEmailReplyAction to generate a draft with appropriate
    greetings and closings based on tone and language.
    """
    try:
        draft = await service.generate_draft(
            email_id=request.email_id,
            account_email=request.account_email,
            original_subject=request.original_subject,
            original_from=request.original_from,
            original_content=request.original_content,
            reply_intent=request.reply_intent,
            tone=request.tone,
            language=request.language,
            include_original=request.include_original,
            original_date=request.original_date,
            original_message_id=request.original_message_id,
        )

        return APIResponse(
            success=True,
            data=_draft_to_response(draft),
            timestamp=datetime.now(timezone.utc),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{draft_id}", response_model=APIResponse[DraftResponse])
async def update_draft(
    draft_id: str,
    request: DraftUpdateRequest,
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[DraftResponse]:
    """
    Update a draft

    Updates subject, body, and/or recipients.
    Cannot update sent or discarded drafts.
    """
    try:
        draft = await service.update_draft(
            draft_id,
            subject=request.subject,
            body=request.body,
            to_addresses=request.to_addresses,
            cc_addresses=request.cc_addresses,
            bcc_addresses=request.bcc_addresses,
        )

        if not draft:
            raise HTTPException(
                status_code=404,
                detail=f"Draft {draft_id} not found or cannot be updated",
            )

        return APIResponse(
            success=True,
            data=_draft_to_response(draft),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{draft_id}/send", response_model=APIResponse[DraftResponse])
async def mark_draft_sent(
    draft_id: str,
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[DraftResponse]:
    """
    Mark a draft as sent

    Call this after successfully sending the email.
    """
    try:
        draft = await service.mark_sent(draft_id)

        if not draft:
            raise HTTPException(
                status_code=404,
                detail=f"Draft {draft_id} not found",
            )

        return APIResponse(
            success=True,
            data=_draft_to_response(draft),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{draft_id}/discard", response_model=APIResponse[DraftResponse])
async def discard_draft(
    draft_id: str,
    request: DraftDiscardRequest = DraftDiscardRequest(),
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[DraftResponse]:
    """
    Discard a draft

    Marks the draft as discarded. Cannot discard sent drafts.
    """
    try:
        draft = await service.discard_draft(draft_id, reason=request.reason)

        if not draft:
            raise HTTPException(
                status_code=404,
                detail=f"Draft {draft_id} not found or already sent",
            )

        return APIResponse(
            success=True,
            data=_draft_to_response(draft),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{draft_id}", response_model=APIResponse[dict])
async def delete_draft(
    draft_id: str,
    service: DraftsService = Depends(get_drafts_service),
) -> APIResponse[dict]:
    """
    Permanently delete a draft

    Warning: This action cannot be undone.
    """
    try:
        deleted = await service.delete_draft(draft_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Draft {draft_id} not found",
            )

        return APIResponse(
            success=True,
            data={"draft_id": draft_id, "deleted": True},
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
