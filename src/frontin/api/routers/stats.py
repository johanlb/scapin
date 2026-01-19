"""
Stats Router

API endpoints for aggregated statistics.
"""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from src.frontin.api.deps import get_current_user
from src.frontin.api.models.responses import APIResponse
from src.frontin.api.models.stats import (
    StatsBySourceResponse,
    StatsOverviewResponse,
    StatsTrendsResponse,
)
from src.frontin.api.services.stats_service import StatsService
from src.monitoring.logger import get_logger

logger = get_logger("api.stats")

router = APIRouter()


def _get_stats_service() -> StatsService:
    """Dependency to get stats service"""
    return StatsService()


@router.get("/overview", response_model=APIResponse[StatsOverviewResponse])
async def get_stats_overview(
    service: StatsService = Depends(_get_stats_service),
    _user: str = Depends(get_current_user),
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
        logger.error(f"Failed to get stats overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics") from e


@router.get("/by-source", response_model=APIResponse[StatsBySourceResponse])
async def get_stats_by_source(
    service: StatsService = Depends(_get_stats_service),
    _user: str = Depends(get_current_user),
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
        logger.error(f"Failed to get stats by source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics") from e


@router.get("/trends", response_model=APIResponse[StatsTrendsResponse])
async def get_stats_trends(
    period: Literal["7d", "30d"] = Query(
        "7d", description="Time period for trends (7d or 30d)"
    ),
    service: StatsService = Depends(_get_stats_service),
    _user: str = Depends(get_current_user),
) -> APIResponse[StatsTrendsResponse]:
    """
    Get historical trends for charts

    Returns daily data points for the specified period.
    Useful for displaying activity trends over time.
    """
    try:
        trends = await service.get_trends(period)

        return APIResponse(
            success=True,
            data=trends,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get stats trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve trends") from e
