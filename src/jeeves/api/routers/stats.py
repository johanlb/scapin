"""
Stats Router

API endpoints for aggregated statistics.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.models.stats import StatsBySourceResponse, StatsOverviewResponse
from src.jeeves.api.services.stats_service import StatsService

router = APIRouter()


def _get_stats_service() -> StatsService:
    """Dependency to get stats service"""
    return StatsService()


@router.get("/overview", response_model=APIResponse[StatsOverviewResponse])
async def get_stats_overview(
    service: StatsService = Depends(_get_stats_service),
) -> APIResponse[StatsOverviewResponse]:
    """
    Get aggregated statistics overview

    Returns high-level stats from all sources (email, teams, calendar, queue, notes).
    Useful for dashboard summary views.
    """
    try:
        overview = await service.get_overview()

        return APIResponse(
            success=True,
            data=overview,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/by-source", response_model=APIResponse[StatsBySourceResponse])
async def get_stats_by_source(
    service: StatsService = Depends(_get_stats_service),
) -> APIResponse[StatsBySourceResponse]:
    """
    Get detailed statistics per source

    Returns complete stats for each source (email, teams, calendar, queue, notes).
    Sources that are disabled return null.
    """
    try:
        by_source = await service.get_by_source()

        return APIResponse(
            success=True,
            data=by_source,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
