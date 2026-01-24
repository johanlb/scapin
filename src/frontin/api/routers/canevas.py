"""
Canevas Router

API endpoints for Canevas (permanent user context) management.
"""

from fastapi import APIRouter

from src.frontin.api.models.queue import CanevasFileStatusResponse, CanevasStatusResponse
from src.sancho.template_renderer import get_template_renderer

router = APIRouter()


@router.get("/status", response_model=CanevasStatusResponse | None)
async def get_canevas_status() -> CanevasStatusResponse | None:
    """
    Get the current Canevas completion status.

    Returns:
        CanevasStatusResponse with completeness info, or None if not loaded.
    """
    renderer = get_template_renderer()
    status = renderer.get_canevas_status()

    if status is None:
        return None

    return CanevasStatusResponse(
        completeness=status.completeness.value,
        files=[
            CanevasFileStatusResponse(
                name=f.name,
                status=f.status.value,
                char_count=f.char_count,
                line_count=f.line_count,
                required=f.required,
                loaded_from=f.loaded_from,
            )
            for f in status.files
        ],
        total_chars=status.total_chars,
        files_present=status.files_present,
        files_missing=status.files_missing,
        files_partial=status.files_partial,
        loaded_at=status.loaded_at.isoformat() if status.loaded_at else None,
    )
