"""
FastAPI Application

Main FastAPI application configuration and setup.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.routers import briefing_router, system_router
from src.monitoring.logger import get_logger

logger = get_logger("jeeves.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler"""
    logger.info("Starting Scapin API server")
    yield
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
        version="0.7.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    # TODO: Get origins from config when APIConfig is added
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle uncaught exceptions"""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                success=False,
                error=str(exc),
                timestamp=datetime.now(timezone.utc),
            ).model_dump(mode="json"),
        )

    # Include routers
    app.include_router(system_router, prefix="/api", tags=["System"])
    app.include_router(briefing_router, prefix="/api/briefing", tags=["Briefing"])

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        """Root endpoint with API info"""
        return {
            "name": "Scapin API",
            "version": "0.7.0",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


# Application instance for uvicorn
app = create_app()
