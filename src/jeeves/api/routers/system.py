"""
System Router

Health, stats, and configuration endpoints.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from src.core.config_manager import ScapinConfig
from src.jeeves.api.deps import get_cached_config
from src.jeeves.api.models.responses import (
    APIResponse,
    ConfigResponse,
    HealthCheckResult,
    HealthResponse,
    StatsResponse,
)

router = APIRouter()

# Track server start time
_start_time = time.time()


@router.get("/health", response_model=APIResponse[HealthResponse])
async def health_check() -> APIResponse[HealthResponse]:
    """
    Health check endpoint

    Returns overall system health status and individual component checks.
    """
    checks: list[HealthCheckResult] = []
    overall_status = "healthy"
    config = None

    # Check configuration
    try:
        config = get_cached_config()
        checks.append(
            HealthCheckResult(
                name="config",
                status="ok",
                message="Configuration loaded",
            )
        )
    except Exception as e:
        checks.append(
            HealthCheckResult(
                name="config",
                status="error",
                message=str(e),
            )
        )
        overall_status = "unhealthy"

    # Check email accounts (only if config loaded)
    if config is not None:
        try:
            enabled_accounts = config.email.get_enabled_accounts()
            if enabled_accounts:
                checks.append(
                    HealthCheckResult(
                        name="email",
                        status="ok",
                        message=f"{len(enabled_accounts)} account(s) configured",
                    )
                )
            else:
                checks.append(
                    HealthCheckResult(
                        name="email",
                        status="warning",
                        message="No email accounts enabled",
                    )
                )
                if overall_status == "healthy":
                    overall_status = "degraded"
        except Exception as e:
            checks.append(
                HealthCheckResult(
                    name="email",
                    status="error",
                    message=str(e),
                )
            )
            overall_status = "unhealthy"

        # Check Teams integration
        if config.teams.enabled:
            checks.append(
                HealthCheckResult(
                    name="teams",
                    status="ok",
                    message="Teams integration enabled",
                )
            )
        else:
            checks.append(
                HealthCheckResult(
                    name="teams",
                    status="warning",
                    message="Teams integration disabled",
                )
            )

        # Check Calendar integration
        if config.calendar.enabled:
            checks.append(
                HealthCheckResult(
                    name="calendar",
                    status="ok",
                    message="Calendar integration enabled",
                )
            )
        else:
            checks.append(
                HealthCheckResult(
                    name="calendar",
                    status="warning",
                    message="Calendar integration disabled",
                )
            )

    uptime = time.time() - _start_time

    return APIResponse(
        success=True,
        data=HealthResponse(
            status=overall_status,
            checks=checks,
            uptime_seconds=uptime,
            version="0.8.0",
        ),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/stats", response_model=APIResponse[StatsResponse])
async def get_stats() -> APIResponse[StatsResponse]:
    """
    Get system statistics

    Returns processing counts and activity information.
    """
    uptime = time.time() - _start_time

    # TODO: Get actual stats from database/state
    # For now, return placeholder values
    return APIResponse(
        success=True,
        data=StatsResponse(
            emails_processed=0,
            teams_messages=0,
            calendar_events=0,
            queue_size=0,
            uptime_seconds=uptime,
            last_activity=None,
        ),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/config", response_model=APIResponse[ConfigResponse])
async def get_config_endpoint(
    config: ScapinConfig = Depends(get_cached_config),
) -> APIResponse[ConfigResponse]:
    """
    Get current configuration

    Returns configuration with sensitive values masked.
    """
    # Get email accounts with masked passwords
    email_accounts = []
    for account in config.email.get_enabled_accounts():
        email_accounts.append(
            {
                "name": account.name,
                "email": account.email_address,
                "enabled": account.enabled,
                # Password is masked
            }
        )

    return APIResponse(
        success=True,
        data=ConfigResponse(
            email_accounts=email_accounts,
            ai_model=config.ai.model,
            teams_enabled=config.teams.enabled,
            calendar_enabled=config.calendar.enabled,
            briefing_enabled=config.briefing.enabled,
        ),
        timestamp=datetime.now(timezone.utc),
    )
