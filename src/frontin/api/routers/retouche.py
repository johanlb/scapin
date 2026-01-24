"""
Retouche Actions Router

Endpoints for retouche lifecycle action management (Filage workflow).
Handles approval/rejection of pending actions like FLAG_OBSOLETE, MERGE_INTO, etc.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.core.config_manager import get_config
from src.frontin.api.auth import TokenData
from src.frontin.api.deps import get_current_user
from src.frontin.api.models.responses import APIResponse
from src.frontin.api.models.retouche import (
    ActionResultResponse,
    ApproveActionRequest,
    BatchApproveRequest,
    BatchApproveResponse,
    NoteLifecycleStatusResponse,
    RejectActionRequest,
    RetoucheQueueResponse,
    RollbackActionRequest,
    RollbackResultResponse,
)
from src.frontin.api.services.retouche_action_service import RetoucheActionService
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.retouche")

router = APIRouter()


def get_retouche_action_service() -> RetoucheActionService:
    """Get RetoucheActionService instance"""
    config = get_config()
    return RetoucheActionService(config=config)


@router.get("/pending", response_model=APIResponse[RetoucheQueueResponse])
async def get_pending_actions(
    service: RetoucheActionService = Depends(get_retouche_action_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[RetoucheQueueResponse]:
    """
    Get all pending retouche actions awaiting approval

    Returns the queue of actions from the Filage that need human decision.
    """
    try:
        result = await service.get_pending_actions()
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get pending actions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des actions: {e!s}",
        ) from e


@router.post("/approve", response_model=APIResponse[ActionResultResponse])
async def approve_action(
    request: ApproveActionRequest,
    service: RetoucheActionService = Depends(get_retouche_action_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ActionResultResponse]:
    """
    Approve a pending retouche action

    Approves and optionally applies the action immediately.
    Returns a rollback token for reversible actions.
    """
    try:
        result = await service.approve_action(
            action_id=request.action_id,
            note_id=request.note_id,
            apply_immediately=request.apply_immediately,
            custom_params=request.custom_params,
        )
        return APIResponse(
            success=result.success,
            data=result,
            timestamp=datetime.now(timezone.utc),
            message=result.message if not result.success else None,
        )
    except Exception as e:
        logger.error(f"Failed to approve action: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'approbation: {e!s}",
        ) from e


@router.post("/reject", response_model=APIResponse[ActionResultResponse])
async def reject_action(
    request: RejectActionRequest,
    service: RetoucheActionService = Depends(get_retouche_action_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ActionResultResponse]:
    """
    Reject a pending retouche action

    Removes the action from the pending queue without applying it.
    Optionally records rejection reason for learning.
    """
    try:
        result = await service.reject_action(
            action_id=request.action_id,
            note_id=request.note_id,
            reason=request.reason,
            suppress_future=request.suppress_future,
        )
        return APIResponse(
            success=result.success,
            data=result,
            timestamp=datetime.now(timezone.utc),
            message=result.message if not result.success else None,
        )
    except Exception as e:
        logger.error(f"Failed to reject action: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du rejet: {e!s}",
        ) from e


@router.post("/rollback", response_model=APIResponse[RollbackResultResponse])
async def rollback_action(
    request: RollbackActionRequest,
    service: RetoucheActionService = Depends(get_retouche_action_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[RollbackResultResponse]:
    """
    Rollback a previously applied retouche action

    Uses the rollback token from the approve response.
    Only available for reversible actions (FLAG_OBSOLETE, MERGE_INTO).
    """
    try:
        result = await service.rollback_action(
            rollback_token=request.rollback_token,
            note_id=request.note_id,
        )
        return APIResponse(
            success=result.success,
            data=result,
            timestamp=datetime.now(timezone.utc),
            message=result.message if not result.success else None,
        )
    except Exception as e:
        logger.error(f"Failed to rollback action: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du rollback: {e!s}",
        ) from e


@router.post("/batch-approve", response_model=APIResponse[BatchApproveResponse])
async def batch_approve_actions(
    request: BatchApproveRequest,
    service: RetoucheActionService = Depends(get_retouche_action_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[BatchApproveResponse]:
    """
    Approve multiple pending actions at once

    Useful for the "Tout valider" button in the Filage UI.
    """
    try:
        result = await service.batch_approve(
            action_ids=request.action_ids,
            note_ids=request.note_ids,
        )
        return APIResponse(
            success=result.success,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to batch approve: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'approbation par lot: {e!s}",
        ) from e


@router.get(
    "/note/{note_id}/lifecycle",
    response_model=APIResponse[NoteLifecycleStatusResponse],
)
async def get_note_lifecycle_status(
    note_id: str,
    service: RetoucheActionService = Depends(get_retouche_action_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteLifecycleStatusResponse]:
    """
    Get lifecycle status for a specific note

    Returns obsolete flag, merge target, pending actions count, etc.
    """
    try:
        result = await service.get_note_lifecycle_status(note_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Note non trouvée: {note_id}",
            )
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lifecycle status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération du statut: {e!s}",
        ) from e
