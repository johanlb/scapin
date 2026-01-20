"""
Error Handler Middleware

Centralized exception handling for the API.
"""

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.frontin.api.models.responses import APIResponse
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.error_handler")


class ServiceError(Exception):
    """
    Base exception for service-level errors.

    Use this for errors that should return a specific HTTP status code
    with a user-friendly message.
    """

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(ServiceError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(ServiceError):
    """Validation failed."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=422)


class ConflictError(ServiceError):
    """Resource conflict."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    This centralizes error handling and ensures consistent error responses.
    The handlers catch exceptions that propagate up from route handlers,
    so individual routes don't need try/except blocks for generic errors.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(ServiceError)
    async def service_error_handler(
        _request: Request,
        exc: ServiceError,
    ) -> JSONResponse:
        """Handle service-level errors with appropriate status codes."""
        logger.warning(f"Service error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=APIResponse(
                success=False,
                error=exc.message,
                timestamp=datetime.now(timezone.utc),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Handle uncaught exceptions.

        Sanitizes error messages for security - internal details are logged
        but not exposed to clients.
        """
        # Log full exception details for debugging
        logger.exception(f"Unhandled exception: {exc}")

        # Return generic error message to client (don't leak internal details)
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                success=False,
                error="Internal server error. Please try again later.",
                timestamp=datetime.now(timezone.utc),
            ).model_dump(mode="json"),
        )
