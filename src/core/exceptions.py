"""
Custom Exceptions for PKM System

Provides a hierarchy of specific exceptions to replace broad catch-all handlers.
All exceptions inherit from PKMError base class for easy catching of PKM-specific errors.

Usage:
    from src.core.exceptions import ValidationError, EmailProcessingError

    if size > limit:
        raise ValidationError(f"Size {size} exceeds limit {limit}")
"""

from typing import Any, Optional


class PKMError(Exception):
    """
    Base exception for all PKM system errors

    All custom PKM exceptions inherit from this to allow catching
    any PKM-specific error with a single except clause.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """
        Initialize PKM error

        Args:
            message: Human-readable error message
            details: Optional dictionary with error details for debugging
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class EmailProcessingError(PKMError):
    """
    Email processing failed

    Raised when email processing encounters an unrecoverable error.
    """

    pass


class AIAnalysisError(PKMError):
    """
    AI analysis failed

    Raised when AI provider returns an error or invalid response.
    """

    pass


class ValidationError(PKMError):
    """
    Validation failed

    Raised when input validation fails (email size, folder name, etc.).
    """

    pass


class RateLimitError(PKMError):
    """
    Rate limit exceeded

    Raised when API rate limit is exceeded and retry is not possible.
    """

    pass


class AuthenticationError(PKMError):
    """
    Authentication failed

    Raised when credentials are invalid or authentication fails.
    """

    pass


class ConfigurationError(PKMError):
    """
    Configuration is invalid

    Raised when required configuration is missing or invalid.
    """

    pass


class DatabaseError(PKMError):
    """
    Database operation failed

    Raised when database operations fail (SQLite, connection, etc.).
    """

    pass


class IMAPError(PKMError):
    """
    IMAP operation failed

    Raised when IMAP operations fail (connection, folder access, etc.).
    """

    pass


class NetworkError(PKMError):
    """
    Network operation failed

    Raised when network operations fail (timeout, connection refused, etc.).
    """

    pass


class SerializationError(PKMError):
    """
    Serialization/deserialization failed

    Raised when JSON/pickle serialization fails.
    """

    pass
