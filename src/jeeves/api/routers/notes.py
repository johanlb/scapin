"""
Notes Router

CRUD endpoints for notes/carnets management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.deps import get_notes_service
from src.jeeves.api.models.notes import (
    NoteCreateRequest,
    NoteDiffResponse,
    NoteLinksResponse,
    NoteResponse,
    NoteSearchResponse,
    NotesTreeResponse,
    NoteSyncStatus,
    NoteUpdateRequest,
    NoteVersionContentResponse,
    NoteVersionsResponse,
)
from src.jeeves.api.models.responses import APIResponse, PaginatedResponse
from src.jeeves.api.services.notes_service import NotesService

router = APIRouter()


@router.get("/tree", response_model=APIResponse[NotesTreeResponse])
async def get_notes_tree(
    recent_limit: int = Query(10, ge=1, le=50, description="Recent notes limit"),
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NotesTreeResponse]:
    """
    Get notes organized in folder tree

    Returns folder hierarchy, pinned notes, and recent notes.
    """
    try:
        tree = await service.get_notes_tree(recent_limit=recent_limit)
        return APIResponse(
            success=True,
            data=tree,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=PaginatedResponse[list[NoteResponse]])
async def list_notes(
    path: str | None = Query(None, description="Filter by folder path"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    pinned: bool = Query(False, description="Only pinned notes"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: NotesService = Depends(get_notes_service),
) -> PaginatedResponse[list[NoteResponse]]:
    """
    List notes with optional filtering

    Supports filtering by path, tags, and pinned status.
    """
    try:
        # Parse tags
        tag_list = tags.split(",") if tags else None

        offset = (page - 1) * page_size
        notes, total = await service.list_notes(
            path=path,
            tags=tag_list,
            pinned_only=pinned,
            limit=page_size,
            offset=offset,
        )

        return PaginatedResponse(
            success=True,
            data=notes,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(notes)) < total,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/search", response_model=APIResponse[NoteSearchResponse])
async def search_notes(
    q: str = Query(..., min_length=1, description="Search query"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteSearchResponse]:
    """
    Semantic search for notes

    Uses vector embeddings for relevance ranking.
    """
    try:
        # Parse tags
        tag_list = tags.split(",") if tags else None

        results = await service.search_notes(query=q, tags=tag_list, limit=limit)
        return APIResponse(
            success=True,
            data=results,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sync/status", response_model=APIResponse[NoteSyncStatus])
async def get_sync_status(
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteSyncStatus]:
    """
    Get Apple Notes sync status
    """
    try:
        status = await service.get_sync_status()
        return APIResponse(
            success=True,
            data=status,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sync", response_model=APIResponse[NoteSyncStatus])
async def sync_apple_notes(
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteSyncStatus]:
    """
    Trigger Apple Notes sync
    """
    try:
        status = await service.sync_apple_notes()
        return APIResponse(
            success=True,
            data=status,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{note_id}", response_model=APIResponse[NoteResponse])
async def get_note(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteResponse]:
    """
    Get a single note by ID
    """
    try:
        note = await service.get_note(note_id)
        if note is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{note_id}/links", response_model=APIResponse[NoteLinksResponse])
async def get_note_links(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteLinksResponse]:
    """
    Get bidirectional links for a note

    Returns incoming and outgoing [[wikilinks]].
    """
    try:
        links = await service.get_note_links(note_id)
        if links is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=links,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=APIResponse[NoteResponse])
async def create_note(
    request: NoteCreateRequest,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteResponse]:
    """
    Create a new note
    """
    try:
        note = await service.create_note(
            title=request.title,
            content=request.content,
            path=request.path,
            tags=request.tags,
            pinned=request.pinned,
        )
        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{note_id}", response_model=APIResponse[NoteResponse])
async def update_note(
    note_id: str,
    request: NoteUpdateRequest,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteResponse]:
    """
    Update an existing note
    """
    try:
        note = await service.update_note(
            note_id=note_id,
            title=request.title,
            content=request.content,
            path=request.path,
            tags=request.tags,
            pinned=request.pinned,
        )
        if note is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{note_id}/pin", response_model=APIResponse[NoteResponse])
async def toggle_pin(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteResponse]:
    """
    Toggle pin status for a note
    """
    try:
        note = await service.toggle_pin(note_id)
        if note is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# Git Versioning Endpoints
# =============================================================================


@router.get("/{note_id}/versions", response_model=APIResponse[NoteVersionsResponse])
async def list_versions(
    note_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum versions to return"),
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteVersionsResponse]:
    """
    List version history for a note

    Returns list of commits that modified this note, most recent first.
    """
    try:
        versions = await service.list_versions(note_id, limit=limit)
        if versions is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=versions,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{note_id}/versions/{version_id}",
    response_model=APIResponse[NoteVersionContentResponse],
)
async def get_version(
    note_id: str,
    version_id: str,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteVersionContentResponse]:
    """
    Get note content at a specific version

    Args:
        note_id: Note identifier
        version_id: Git commit hash (short or full)
    """
    try:
        version = await service.get_version(note_id, version_id)
        if version is None:
            raise HTTPException(
                status_code=404,
                detail=f"Version not found: {version_id} for note {note_id}",
            )

        return APIResponse(
            success=True,
            data=version,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{note_id}/diff", response_model=APIResponse[NoteDiffResponse])
async def diff_versions(
    note_id: str,
    v1: str = Query(..., description="Source version (older)"),
    v2: str = Query(..., description="Target version (newer)"),
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteDiffResponse]:
    """
    Get diff between two versions of a note

    Shows what changed between v1 (older) and v2 (newer).
    """
    try:
        diff = await service.diff_versions(note_id, v1, v2)
        if diff is None:
            raise HTTPException(
                status_code=404,
                detail=f"Could not generate diff for note {note_id}: {v1} -> {v2}",
            )

        return APIResponse(
            success=True,
            data=diff,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/{note_id}/restore/{version_id}",
    response_model=APIResponse[NoteResponse],
)
async def restore_version(
    note_id: str,
    version_id: str,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteResponse]:
    """
    Restore a note to a previous version

    Creates a new commit with the restored content,
    preserving the full history.
    """
    try:
        note = await service.restore_version(note_id, version_id)
        if note is None:
            raise HTTPException(
                status_code=404,
                detail=f"Could not restore note {note_id} to version {version_id}",
            )

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# Delete Endpoint
# =============================================================================


@router.delete("/{note_id}", response_model=APIResponse[None])
async def delete_note(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[None]:
    """
    Delete a note
    """
    try:
        deleted = await service.delete_note(note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

        return APIResponse(
            success=True,
            data=None,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
