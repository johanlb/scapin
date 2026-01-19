"""API Models"""

from src.frontin.api.models.common import ErrorDetail, PaginationParams
from src.frontin.api.models.notes import (
    FolderNode,
    NoteCreateRequest,
    NoteLinksResponse,
    NoteResponse,
    NoteSearchResponse,
    NoteSearchResult,
    NotesTreeResponse,
    NoteSyncStatus,
    NoteUpdateRequest,
    WikilinkResponse,
)
from src.frontin.api.models.responses import (
    APIResponse,
    BriefingResponse,
    HealthCheckResult,
    HealthResponse,
    PaginatedResponse,
    PreMeetingBriefingResponse,
    StatsResponse,
)

__all__ = [
    "APIResponse",
    "BriefingResponse",
    "ErrorDetail",
    "FolderNode",
    "HealthCheckResult",
    "HealthResponse",
    "NoteCreateRequest",
    "NoteLinksResponse",
    "NoteResponse",
    "NoteSearchResponse",
    "NoteSearchResult",
    "NotesTreeResponse",
    "NoteSyncStatus",
    "NoteUpdateRequest",
    "PaginatedResponse",
    "PaginationParams",
    "PreMeetingBriefingResponse",
    "StatsResponse",
    "WikilinkResponse",
]
