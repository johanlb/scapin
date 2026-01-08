"""
FastAPI Application

Main FastAPI application configuration and setup.
"""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config_manager import get_config
from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.routers import (
    auth_router,
    briefing_router,
    calendar_router,
    discussions_router,
    drafts_router,
    email_router,
    events_router,
    journal_router,
    notes_router,
    notifications_router,
    queue_router,
    search_router,
    stats_router,
    system_router,
    teams_router,
    valets_router,
)
from src.jeeves.api.services.notification_service import get_notification_service
from src.jeeves.api.websocket import ws_router
from src.monitoring.logger import get_logger

logger = get_logger("jeeves.api")

# Cleanup interval in seconds (1 hour)
NOTIFICATION_CLEANUP_INTERVAL = 3600


async def notification_cleanup_task() -> None:
    """
    Background task to periodically clean up expired notifications.

    Runs every NOTIFICATION_CLEANUP_INTERVAL seconds.
    """
    while True:
        try:
            await asyncio.sleep(NOTIFICATION_CLEANUP_INTERVAL)
            service = get_notification_service()
            deleted = await service.cleanup_expired()
            if deleted > 0:
                logger.info(f"Notification cleanup: removed {deleted} expired notifications")
        except asyncio.CancelledError:
            logger.debug("Notification cleanup task cancelled")
            break
        except Exception as e:
            logger.warning(f"Notification cleanup error: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler"""
    logger.info("Starting Scapin API server")

    # Security check: warn if auth is disabled in production
    config = get_config()
    if (
        config.environment == "production"
        and not config.auth.enabled
        and config.auth.warn_disabled_in_production
    ):
        logger.warning(
            "SECURITY WARNING: Authentication is DISABLED in production environment! "
            "Set AUTH__ENABLED=true or ENVIRONMENT=development"
        )

    # Start background cleanup task for notifications
    cleanup_task = asyncio.create_task(notification_cleanup_task())

    yield

    # Cancel cleanup task on shutdown
    cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await cleanup_task

    logger.info("Shutting down Scapin API server")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Scapin API",
        description=(
            "Personal cognitive guardian API.\n\n"
            "Exposes email processing, briefings, calendar, Teams, "
            "and journal functionality via REST endpoints."
        ),
        version="0.8.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware - configured via API__CORS_* environment variables
    config = get_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=config.api.cors_methods,
        allow_headers=config.api.cors_headers,
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle uncaught exceptions - sanitize error messages for security"""
        # Log full exception details for debugging
        logger.exception(f"Unhandled exception: {exc}")

        # Return generic error message to client (don't leak internal details)
        # In development, you can check logs for full details
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                success=False,
                error="Internal server error. Please try again later.",
                timestamp=datetime.now(timezone.utc),
            ).model_dump(mode="json"),
        )

    # Include routers
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(system_router, prefix="/api", tags=["System"])
    app.include_router(briefing_router, prefix="/api/briefing", tags=["Briefing"])
    app.include_router(discussions_router, prefix="/api/discussions", tags=["Discussions"])
    app.include_router(drafts_router, prefix="/api/drafts", tags=["Drafts"])
    app.include_router(events_router, prefix="/api/events", tags=["Events"])
    app.include_router(journal_router, prefix="/api/journal", tags=["Journal"])
    app.include_router(queue_router, prefix="/api/queue", tags=["Queue"])
    app.include_router(email_router, prefix="/api/email", tags=["Email"])
    app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])
    app.include_router(teams_router, prefix="/api/teams", tags=["Teams"])
    app.include_router(notes_router, prefix="/api/notes", tags=["Notes"])
    app.include_router(search_router, prefix="/api/search", tags=["Search"])
    app.include_router(stats_router, prefix="/api/stats", tags=["Stats"])
    app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])
    app.include_router(valets_router, prefix="/api/valets", tags=["Valets"])
    app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        """Root endpoint with API info"""
        return {
            "name": "Scapin API",
            "version": "0.8.0",
            "docs": "/docs",
            "health": "/api/health",
            "auth": "/api/auth/login",
        }

    return app


# Application instance for uvicorn
app = create_app()
