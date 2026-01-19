"""
Common API Models

Shared models for pagination, errors, and other common structures.
"""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints"""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database query"""
        return (self.page - 1) * self.page_size


class ErrorDetail(BaseModel):
    """Detailed error information"""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: str | None = Field(None, description="Field that caused the error")
    details: dict | None = Field(None, description="Additional error details")
