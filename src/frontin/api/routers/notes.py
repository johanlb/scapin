"""
Notes Router

CRUD endpoints for notes/carnets management.
All endpoints require authentication when auth is enabled.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.frontin.api.auth import TokenData
from src.frontin.api.deps import get_current_user, get_notes_review_service, get_notes_service
from src.frontin.api.models.notes import (
    EnrichmentHistoryResponse,
    EnrichmentRecordResponse,
    FolderCreateRequest,
    FolderCreateResponse,
    FolderListResponse,
    IndexRebuildResponse,
    NoteCreateRequest,
    NoteDiffResponse,
    NoteLinksResponse,
    NoteMetadataResponse,
    NoteMoveRequest,
    NoteMoveResponse,
    NoteResponse,
    NotesDueResponse,
    NoteSearchResponse,
    NotesTreeResponse,
    NoteSyncStatus,
    NoteUpdateRequest,
    NoteVersionContentResponse,
    NoteVersionsResponse,
    PostponeReviewRequest,
    PostponeReviewResponse,
    RecordReviewRequest,
    RecordReviewResponse,
    ReviewConfigResponse,
    ReviewStatsResponse,
    ReviewWorkloadResponse,
    TriggerReviewResponse,
)
from src.frontin.api.models.responses import APIResponse, PaginatedResponse
from src.frontin.api.services.notes_review_service import NotesReviewService
from src.frontin.api.services.notes_service import NotesService
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.notes")

router = APIRouter()


@router.get("/tree", response_model=APIResponse[NotesTreeResponse])
async def get_notes_tree(
    recent_limit: int = Query(10, ge=1, le=50, description="Recent notes limit"),
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
        logger.error(f"Failed to get notes tree: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve notes tree"
        ) from e


@router.get("", response_model=PaginatedResponse[list[NoteResponse]])
async def list_notes(
    path: str | None = Query(None, description="Filter by folder path"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    pinned: bool = Query(False, description="Only pinned notes"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page"),
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
        logger.error(f"Failed to list notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list notes") from e


@router.get("/search", response_model=APIResponse[NoteSearchResponse])
async def search_notes(
    q: str = Query(..., min_length=1, description="Search query"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
        logger.error(f"Failed to search notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search notes") from e


@router.get("/sync/status", response_model=APIResponse[NoteSyncStatus])
async def get_sync_status(
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
        logger.error(f"Failed to get sync status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get sync status") from e


@router.post("/sync", response_model=APIResponse[NoteSyncStatus])
async def sync_apple_notes(
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
        logger.error(f"Failed to sync Apple Notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to sync Apple Notes") from e


@router.post("/index/rebuild", response_model=APIResponse[IndexRebuildResponse])
async def rebuild_index(
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[IndexRebuildResponse]:
    """
    Rebuild the vector search index

    Clears existing index and re-indexes all notes.
    Useful when the index is corrupted or out of sync with notes.
    """
    try:
        result = await service.rebuild_index()
        return APIResponse(
            success=True,
            data=IndexRebuildResponse(**result),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to rebuild index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rebuild index") from e


@router.get("/deleted", response_model=APIResponse[list[NoteResponse]])
async def get_deleted_notes(
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[list[NoteResponse]]:
    """
    Get notes from Scapin's trash folder (_Supprimées/)

    Returns notes that have been soft-deleted but not yet permanently removed.
    Each note includes a 'deleted_at' timestamp in its metadata.
    """
    try:
        notes = await service.get_deleted_notes()
        return APIResponse(
            success=True,
            data=notes,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get deleted notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get deleted notes") from e


@router.post("/deleted/{note_id}/restore", response_model=APIResponse[dict])
async def restore_deleted_note(
    note_id: str,
    target_folder: str = Query("", description="Target folder path (empty for root)"),
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Restore a note from trash to a folder

    Moves the note from the trash folder back to the specified folder.
    If no target_folder is provided, restores to the root folder.
    """
    try:
        success = await service.restore_note(note_id, target_folder)
        if not success:
            raise HTTPException(status_code=404, detail="Note not found in trash")
        return APIResponse(
            success=True,
            data={"note_id": note_id, "restored_to": target_folder or "/"},
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to restore note") from e


@router.delete("/deleted/{note_id}", response_model=APIResponse[dict])
async def permanently_delete_note(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Permanently delete a note from trash

    This action is irreversible. The note will be permanently removed from disk.
    """
    try:
        success = await service.permanently_delete_note(note_id)
        if not success:
            raise HTTPException(status_code=404, detail="Note not found in trash")
        return APIResponse(
            success=True,
            data={"note_id": note_id, "permanently_deleted": True},
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to permanently delete note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to permanently delete note") from e


@router.delete("/deleted", response_model=APIResponse[dict])
async def empty_trash(
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Empty the trash - permanently delete all notes in trash

    This action is irreversible. All notes in the trash folder will be permanently removed.
    """
    try:
        count = await service.empty_trash()
        return APIResponse(
            success=True,
            data={"deleted_count": count},
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to empty trash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to empty trash") from e


# =============================================================================
# Folder Management Endpoints (MUST be before /{note_id} routes)
# =============================================================================


@router.post("/folders", response_model=APIResponse[FolderCreateResponse])
async def create_folder(
    request: FolderCreateRequest,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[FolderCreateResponse]:
    """
    Create a new folder in the notes directory

    Creates nested folder structure as needed (e.g., 'Clients/ABC' creates both).
    Returns success even if folder already exists.
    """
    try:
        result = await service.create_folder(request.path)
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except ValueError as e:
        # ValueError is user input validation - safe to expose
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create folder") from e


@router.get("/folders", response_model=APIResponse[FolderListResponse])
async def list_folders(
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[FolderListResponse]:
    """
    List all folders in the notes directory

    Returns flat list of all folder paths, sorted alphabetically.
    """
    try:
        result = await service.list_folders()
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to list folders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list folders") from e


# =============================================================================
# Review & Scheduling Endpoints (MUST be before /{note_id} routes)
# =============================================================================


@router.get("/reviews/due", response_model=APIResponse[NotesDueResponse])
async def get_notes_due(
    limit: int = Query(50, ge=1, le=200, description="Maximum notes to return"),
    note_type: str | None = Query(None, description="Filter by note type"),
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NotesDueResponse]:
    """
    Get notes due for review

    Returns notes scheduled for review, ordered by priority.
    Use the SM-2 algorithm for spaced repetition.
    """
    try:
        due = await service.get_notes_due(limit=limit, note_type=note_type)
        return APIResponse(
            success=True,
            data=due,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get notes due for review: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to get notes due for review"
        ) from e


@router.get("/reviews/stats", response_model=APIResponse[ReviewStatsResponse])
async def get_review_stats(
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ReviewStatsResponse]:
    """
    Get review statistics

    Returns scheduling statistics including notes due,
    reviewed today, and distribution by type.
    """
    try:
        stats = await service.get_review_stats()
        return APIResponse(
            success=True,
            data=stats,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get review stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to get review statistics"
        ) from e


@router.get("/reviews/workload", response_model=APIResponse[ReviewWorkloadResponse])
async def get_review_workload(
    days: int = Query(7, ge=1, le=30, description="Days to forecast"),
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ReviewWorkloadResponse]:
    """
    Estimate review workload for upcoming days

    Returns estimated number of notes due per day
    for planning purposes.
    """
    try:
        workload = await service.estimate_workload(days=days)
        return APIResponse(
            success=True,
            data=workload,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to estimate workload: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to estimate review workload"
        ) from e


@router.get("/reviews/configs", response_model=APIResponse[list[ReviewConfigResponse]])
async def get_review_configs(
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[list[ReviewConfigResponse]]:
    """
    Get review configuration for all note types

    Returns SM-2 parameters for each note type.
    """
    try:
        configs = await service.get_review_configs()
        return APIResponse(
            success=True,
            data=configs,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get review configs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to get review configurations"
        ) from e


# =============================================================================
# Note CRUD Endpoints (parameterized paths AFTER static paths)
# =============================================================================


@router.get("/{note_id}", response_model=APIResponse[NoteResponse])
async def get_note(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteResponse]:
    """
    Get a single note by ID
    """
    try:
        note = await service.get_note(note_id)
        if note is None:
            raise HTTPException(status_code=404, detail="Note not found")

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get note {note_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve note") from e


@router.get("/{note_id}/links", response_model=APIResponse[NoteLinksResponse])
async def get_note_links(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteLinksResponse]:
    """
    Get bidirectional links for a note

    Returns incoming and outgoing [[wikilinks]].
    """
    try:
        links = await service.get_note_links(note_id)
        if links is None:
            raise HTTPException(status_code=404, detail="Note not found")

        return APIResponse(
            success=True,
            data=links,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get links for note {note_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve note links") from e


@router.post("", response_model=APIResponse[NoteResponse])
async def create_note(
    request: NoteCreateRequest,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
        # ValueError is user input validation - safe to expose
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create note") from e


@router.patch("/{note_id}", response_model=APIResponse[NoteResponse])
async def update_note(
    note_id: str,
    request: NoteUpdateRequest,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
            raise HTTPException(status_code=404, detail="Note not found")

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update note {note_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update note") from e


@router.post("/{note_id}/pin", response_model=APIResponse[NoteResponse])
async def toggle_pin(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteResponse]:
    """
    Toggle pin status for a note
    """
    try:
        note = await service.toggle_pin(note_id)
        if note is None:
            raise HTTPException(status_code=404, detail="Note not found")

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle pin for note {note_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to toggle pin status") from e


@router.post("/{note_id}/move", response_model=APIResponse[NoteMoveResponse])
async def move_note(
    note_id: str,
    request: NoteMoveRequest,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteMoveResponse]:
    """
    Move a note to a different folder

    Moves the note file to the specified folder path.
    Use empty string '' to move to the root folder.
    Git history is preserved with a move commit.
    """
    try:
        result = await service.move_note(note_id, request.target_folder)
        if result is None:
            raise HTTPException(status_code=404, detail="Note not found")

        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except ValueError as e:
        # ValueError is user input validation - safe to expose
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to move note {note_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to move note") from e


# =============================================================================
# Git Versioning Endpoints
# =============================================================================


@router.get("/{note_id}/versions", response_model=APIResponse[NoteVersionsResponse])
async def list_versions(
    note_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum versions to return"),
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteVersionsResponse]:
    """
    List version history for a note

    Returns list of commits that modified this note, most recent first.
    """
    try:
        versions = await service.list_versions(note_id, limit=limit)
        if versions is None:
            raise HTTPException(status_code=404, detail="Note not found")

        return APIResponse(
            success=True,
            data=versions,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list versions for note {note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to list note versions"
        ) from e


@router.get(
    "/{note_id}/versions/{version_id}",
    response_model=APIResponse[NoteVersionContentResponse],
)
async def get_version(
    note_id: str,
    version_id: str,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
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
            raise HTTPException(status_code=404, detail="Version not found")

        return APIResponse(
            success=True,
            data=version,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get version {version_id} for note {note_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve note version"
        ) from e


@router.get("/{note_id}/diff", response_model=APIResponse[NoteDiffResponse])
async def diff_versions(
    note_id: str,
    v1: str = Query(..., description="Source version (older)"),
    v2: str = Query(..., description="Target version (newer)"),
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteDiffResponse]:
    """
    Get diff between two versions of a note

    Shows what changed between v1 (older) and v2 (newer).
    """
    try:
        diff = await service.diff_versions(note_id, v1, v2)
        if diff is None:
            raise HTTPException(status_code=404, detail="Could not generate diff")

        return APIResponse(
            success=True,
            data=diff,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to diff versions for note {note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to generate version diff"
        ) from e


@router.post(
    "/{note_id}/restore/{version_id}",
    response_model=APIResponse[NoteResponse],
)
async def restore_version(
    note_id: str,
    version_id: str,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteResponse]:
    """
    Restore a note to a previous version

    Creates a new commit with the restored content,
    preserving the full history.
    """
    try:
        note = await service.restore_version(note_id, version_id)
        if note is None:
            raise HTTPException(status_code=404, detail="Could not restore version")

        return APIResponse(
            success=True,
            data=note,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to restore note {note_id} to version {version_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to restore note version"
        ) from e


# =============================================================================
# Delete Endpoint
# =============================================================================


@router.delete("/{note_id}", response_model=APIResponse[None])
async def delete_note(
    note_id: str,
    service: NotesService = Depends(get_notes_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[None]:
    """
    Delete a note
    """
    try:
        deleted = await service.delete_note(note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Note not found")

        return APIResponse(
            success=True,
            data=None,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete note {note_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete note") from e


# =============================================================================
# Note-specific Review Endpoints (parameterized paths)
# =============================================================================


@router.get("/{note_id}/metadata", response_model=APIResponse[NoteMetadataResponse | None])
async def get_note_metadata(
    note_id: str,
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[NoteMetadataResponse | None]:
    """
    Get review metadata for a note

    Returns SM-2 scheduling parameters and review history.
    Returns null data if no metadata exists yet (note not scheduled for review).
    """
    try:
        metadata = await service.get_note_metadata(note_id)
        # Return null if no metadata exists - this is normal for unscheduled notes
        return APIResponse(
            success=True,
            data=metadata,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get metadata for note {note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve note metadata"
        ) from e


@router.get(
    "/{note_id}/enrichment-history", response_model=APIResponse[EnrichmentHistoryResponse]
)
async def get_enrichment_history(
    note_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[EnrichmentHistoryResponse]:
    """
    Get enrichment/retouche history for a note

    Returns the history of AI-powered improvements (Retouche cycles)
    including actions taken, confidence scores, and reasoning.
    """
    try:
        metadata = await service.get_note_metadata(note_id)

        if metadata is None:
            return APIResponse(
                success=True,
                data=EnrichmentHistoryResponse(
                    note_id=note_id,
                    records=[],
                    total_records=0,
                    quality_score=None,
                    retouche_count=0,
                ),
                timestamp=datetime.now(timezone.utc),
            )

        # Convert enrichment history to response format
        records = [
            EnrichmentRecordResponse(
                timestamp=record.timestamp,
                action_type=record.action_type,
                target=record.target,
                content=record.content,
                confidence=record.confidence,
                applied=record.applied,
                reasoning=record.reasoning,
            )
            for record in (metadata.enrichment_history or [])[:limit]
        ]

        # Sort by timestamp descending (newest first)
        records.sort(key=lambda r: r.timestamp, reverse=True)

        return APIResponse(
            success=True,
            data=EnrichmentHistoryResponse(
                note_id=note_id,
                records=records,
                total_records=len(metadata.enrichment_history or []),
                quality_score=metadata.quality_score,
                retouche_count=metadata.retouche_count,
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(
            f"Failed to get enrichment history for note {note_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve enrichment history"
        ) from e


@router.post("/{note_id}/review", response_model=APIResponse[RecordReviewResponse])
async def record_review(
    note_id: str,
    request: RecordReviewRequest,
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[RecordReviewResponse]:
    """
    Record a review for a note

    Updates SM-2 scheduling based on review quality:
    - 5: Perfect - no changes needed
    - 4: Excellent - minor typo fixes only
    - 3: Good - small additions/clarifications
    - 2: Medium - moderate updates required
    - 1: Poor - significant restructuring needed
    - 0: Fail - major overhaul required

    Quality < 3 resets the learning interval.
    """
    try:
        result = await service.record_review(note_id, request.quality)
        if result is None:
            raise HTTPException(status_code=404, detail="Note not found")
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except ValueError as e:
        # ValueError is user input validation - safe to expose
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to record review for note {note_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record review") from e


@router.post("/{note_id}/postpone", response_model=APIResponse[PostponeReviewResponse])
async def postpone_review(
    note_id: str,
    request: PostponeReviewRequest,
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[PostponeReviewResponse]:
    """
    Postpone a note's review

    Delays the next review by the specified number of hours.
    Useful when you need more time before reviewing.
    """
    try:
        result = await service.postpone_review(note_id, request.hours)
        if result is None:
            raise HTTPException(status_code=404, detail="Note not found")
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to postpone review for note {note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to postpone review"
        ) from e


@router.post("/{note_id}/trigger", response_model=APIResponse[TriggerReviewResponse])
async def trigger_immediate_review(
    note_id: str,
    service: NotesReviewService = Depends(get_notes_review_service),
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[TriggerReviewResponse]:
    """
    Trigger immediate review for a note

    Sets the next review time to now, making the note
    immediately appear in the review queue.
    """
    try:
        result = await service.trigger_immediate_review(note_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Note not found")
        return APIResponse(
            success=True,
            data=result,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to trigger review for note {note_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Failed to trigger immediate review"
        ) from e
