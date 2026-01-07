"""
Discussions Router

CRUD endpoints for conversation threads with Scapin.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.auth import TokenData
from src.jeeves.api.deps import get_current_user, get_discussion_service
from src.jeeves.api.models.discussions import (
    DiscussionCreateRequest,
    DiscussionDetailResponse,
    DiscussionListResponse,
    DiscussionResponse,
    DiscussionType,
    MessageCreateRequest,
    QuickChatRequest,
    QuickChatResponse,
)
from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.services.discussion_service import DiscussionService

router = APIRouter()


@router.post("", response_model=APIResponse[DiscussionDetailResponse])
async def create_discussion(
    request: DiscussionCreateRequest,
    service: DiscussionService = Depends(get_discussion_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[DiscussionDetailResponse]:
    """
    Create a new discussion

    Optionally include an initial message to start the conversation.
    If provided, an AI response will be generated automatically.
    """
    try:
        discussion = await service.create_discussion(request)
        return APIResponse(
            success=True,
            data=discussion,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la creation") from e


@router.get("", response_model=APIResponse[DiscussionListResponse])
async def list_discussions(
    discussion_type: Optional[DiscussionType] = Query(
        None, description="Filter by discussion type"
    ),
    attached_to_id: Optional[str] = Query(
        None, description="Filter by attached object ID"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: DiscussionService = Depends(get_discussion_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[DiscussionListResponse]:
    """
    List discussions with optional filtering

    Supports pagination and filtering by type or attached object.
    """
    try:
        result = await service.list_discussions(
            discussion_type=discussion_type,
            attached_to_id=attached_to_id,
            page=page,
            page_size=page_size,
        )
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la liste") from e


@router.get("/{discussion_id}", response_model=APIResponse[DiscussionDetailResponse])
async def get_discussion(
    discussion_id: str,
    service: DiscussionService = Depends(get_discussion_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[DiscussionDetailResponse]:
    """
    Get a discussion by ID with all messages

    Returns the full discussion thread with messages and contextual suggestions.
    """
    try:
        discussion = await service.get_discussion(discussion_id)
        if discussion is None:
            raise HTTPException(status_code=404, detail="Discussion non trouvee")
        return APIResponse(
            success=True,
            data=discussion,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la lecture") from e


@router.post(
    "/{discussion_id}/messages",
    response_model=APIResponse[DiscussionDetailResponse],
)
async def add_message(
    discussion_id: str,
    request: MessageCreateRequest,
    service: DiscussionService = Depends(get_discussion_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[DiscussionDetailResponse]:
    """
    Add a message to a discussion

    If the message is from the user, an AI response will be generated.
    Returns the updated discussion with all messages.
    """
    try:
        discussion = await service.add_message(discussion_id, request)
        if discussion is None:
            raise HTTPException(status_code=404, detail="Discussion non trouvee")
        return APIResponse(
            success=True,
            data=discussion,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout") from e


@router.patch("/{discussion_id}", response_model=APIResponse[DiscussionResponse])
async def update_discussion(
    discussion_id: str,
    title: Optional[str] = Query(None, max_length=200, description="New title"),
    service: DiscussionService = Depends(get_discussion_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[DiscussionResponse]:
    """
    Update discussion metadata

    Currently supports updating the title.
    """
    try:
        discussion = await service.update_discussion(discussion_id, title=title)
        if discussion is None:
            raise HTTPException(status_code=404, detail="Discussion non trouvee")
        return APIResponse(
            success=True,
            data=discussion,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise a jour") from e


@router.delete("/{discussion_id}", response_model=APIResponse[dict])
async def delete_discussion(
    discussion_id: str,
    service: DiscussionService = Depends(get_discussion_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Delete a discussion

    This permanently removes the discussion and all its messages.
    """
    try:
        deleted = await service.delete_discussion(discussion_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Discussion non trouvee")
        return APIResponse(
            success=True,
            data={"deleted": True, "discussion_id": discussion_id},
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression") from e


@router.post("/quick", response_model=APIResponse[QuickChatResponse])
async def quick_chat(
    request: QuickChatRequest,
    service: DiscussionService = Depends(get_discussion_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[QuickChatResponse]:
    """
    Quick one-off chat without creating a persistent discussion

    Useful for simple questions or quick actions.
    Optionally provide context to get more relevant responses.
    """
    try:
        response = await service.quick_chat(request)
        return APIResponse(
            success=True,
            data=response,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors du chat") from e
