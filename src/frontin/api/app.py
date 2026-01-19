"""
FastAPI Application

Main FastAPI application configuration and setup.
"""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from src.core.config_manager import get_config
from src.frontin.api.models.responses import APIResponse
from src.frontin.api.routers import (
    auth_router,
    briefing_router,
    calendar_router,
    discussions_router,
    drafts_router,
    email_router,
    events_router,
    journal_router,
    media_router,
    notes_router,
    notifications_router,
    queue_router,
    search_router,
    stats_router,
    system_router,
    teams_router,
    valets_router,
    workflow_router,
)
from src.frontin.api.services.notification_service import get_notification_service
from src.frontin.api.websocket import ws_router
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api")

# Flag to track if notes service is initialized
_notes_service_ready = False

# Cleanup interval in seconds (1 hour)
NOTIFICATION_CLEANUP_INTERVAL = 3600


async def init_notes_service_background() -> None:
    """
    Initialize NotesService in background at startup.

    This pre-loads the embedding model, vector store, and metadata index
    so that the first request to /api/notes doesn't have to wait.
    """
    global _notes_service_ready
    import time

    start = time.time()
    logger.info("Starting background initialization of NotesService...")

    try:
        # Run in executor to not block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _init_notes_service_sync)

        elapsed = time.time() - start
        _notes_service_ready = True
        logger.info(f"NotesService initialized in {elapsed:.1f}s")
    except Exception as e:
        logger.warning(f"Background NotesService init failed: {e}")


def _init_notes_service_sync() -> None:
    """Synchronous helper to initialize NotesService"""
    from src.frontin.api.deps import get_notes_service

    # This triggers the singleton creation
    gen = get_notes_service()
    service = next(gen)
    # Force initialization of the NoteManager
    _ = service._get_manager()


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

    # Start background initialization of NotesService (non-blocking)
    # This preloads embedding model, vector store, and metadata index
    notes_init_task = asyncio.create_task(init_notes_service_background())

    yield

    # Cancel notes init task if still running
    if not notes_init_task.done():
        notes_init_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await notes_init_task

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
    app.include_router(media_router, tags=["Media"])  # Already has /api/media prefix
    app.include_router(search_router, prefix="/api/search", tags=["Search"])
    app.include_router(stats_router, prefix="/api/stats", tags=["Stats"])
    app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])
    app.include_router(valets_router, prefix="/api/valets", tags=["Valets"])
    app.include_router(workflow_router, prefix="/api/workflow", tags=["Workflow v2.1"])
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

    # Static assets (Favicon, Apple Touch Icon)
    # web/static/icons is relative to project root
    project_root = Path(__file__).resolve().parents[3]
    static_icons_dir = project_root / "web/static/icons"

    if static_icons_dir.exists():

        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            return FileResponse(static_icons_dir / "favicon.ico")

        @app.get("/apple-touch-icon.png", include_in_schema=False)
        async def apple_touch_icon():
            return FileResponse(static_icons_dir / "apple-touch-icon.png")

        @app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
        async def apple_touch_icon_precomposed():
            return FileResponse(static_icons_dir / "apple-touch-icon.png")

    return app


# Application instance for uvicorn
app = create_app()
