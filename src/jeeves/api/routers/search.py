"""
Search Router

Global search API endpoints.
"""

import contextlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.config_manager import get_config
from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.models.search import (
    CrossSourceSearchRequest,
    CrossSourceSearchResponse,
    GlobalSearchResponse,
    RecentSearchesResponse,
    SearchResultType,
)
from src.jeeves.api.services.search_service import SearchService

router = APIRouter()


def _get_search_service() -> SearchService:
    """Dependency to get search service"""
    config = get_config()
    return SearchService(config=config)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_types(types_str: str | None) -> list[SearchResultType] | None:
    """Parse comma-separated types string"""
    if not types_str:
        return None
    type_names = [t.strip().lower() for t in types_str.split(",")]
    types = []
    for name in type_names:
        with contextlib.suppress(ValueError):
            types.append(SearchResultType(name))
    return types if types else None


@router.get("", response_model=APIResponse[GlobalSearchResponse])
async def global_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    types: str | None = Query(
        None,
        description="Filter by types (comma-separated: note,email,calendar,teams)",
    ),
    limit: int = Query(10, ge=1, le=50, description="Max results per type"),
    date_from: str | None = Query(None, description="Filter after this date (ISO format)"),
    date_to: str | None = Query(None, description="Filter before this date (ISO format)"),
    service: SearchService = Depends(_get_search_service),
) -> APIResponse[GlobalSearchResponse]:
    """
    Global search across all content types

    Searches notes, emails, calendar events, and Teams messages.
    Returns results grouped by type with relevance scores.

    Query parameters:
    - q: Search query (required)
    - types: Comma-separated list of types to search (default: all)
    - limit: Maximum results per type (default: 10)
    - date_from: Filter results after this date
    - date_to: Filter results before this date

    Examples:
    - GET /api/search?q=meeting
    - GET /api/search?q=project+update&types=note,email&limit=20
    - GET /api/search?q=john&date_from=2026-01-01
    """
    try:
        parsed_types = _parse_types(types)
        parsed_from = _parse_datetime(date_from)
        parsed_to = _parse_datetime(date_to)

        results = await service.search(
            query=q,
            types=parsed_types,
            limit_per_type=limit,
            date_from=parsed_from,
            date_to=parsed_to,
        )

        return APIResponse(
            success=True,
            data=results,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/recent", response_model=APIResponse[RecentSearchesResponse])
async def get_recent_searches(
    limit: int = Query(20, ge=1, le=100, description="Maximum searches to return"),
    service: SearchService = Depends(_get_search_service),
) -> APIResponse[RecentSearchesResponse]:
    """
    Get recent search queries

    Returns list of recent searches with query, timestamp, and result count.
    Useful for search suggestions and history.
    """
    try:
        results = await service.get_recent_searches(limit=limit)
        return APIResponse(
            success=True,
            data=results,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cross-source", response_model=APIResponse[CrossSourceSearchResponse])
async def cross_source_search(
    request: CrossSourceSearchRequest,
    service: SearchService = Depends(_get_search_service),
) -> APIResponse[CrossSourceSearchResponse]:
    """
    Search across all available sources using CrossSourceEngine

    Unified search across calendar, Teams, emails, and other configured sources.
    Uses intelligent ranking to return the most relevant results.

    Request body:
    - query: Search query (required)
    - sources: List of sources to search (optional, default: all available)
    - max_results: Maximum results to return (default: 20, max: 100)
    - min_relevance: Minimum relevance score threshold (default: 0.3)
    - include_content: Include full content in results (default: true)

    Available sources:
    - email: Archived emails
    - calendar: Microsoft Calendar events
    - icloud_calendar: iCloud Calendar events
    - teams: Teams messages
    - whatsapp: WhatsApp messages (if configured)
    - files: Local files (if configured)
    - web: Web search (if configured)

    Examples:
    - POST /api/search/cross-source {"query": "meeting with John"}
    - POST /api/search/cross-source {"query": "project update", "sources": ["calendar", "teams"]}
    """
    try:
        results = await service.cross_source_search(request)
        return APIResponse(
            success=True,
            data=results,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
