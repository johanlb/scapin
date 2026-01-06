"""
Authentication Module

JWT-based authentication for Scapin API.
Single-user system with PIN code authentication.
"""

from src.jeeves.api.auth.jwt_handler import JWTHandler, TokenData
from src.jeeves.api.auth.password import get_pin_hash, verify_pin
from src.jeeves.api.auth.rate_limiter import (
    LoginRateLimiter,
    get_login_rate_limiter,
    reset_login_rate_limiter,
)

__all__ = [
    "JWTHandler",
    "TokenData",
    "verify_pin",
    "get_pin_hash",
    "LoginRateLimiter",
    "get_login_rate_limiter",
    "reset_login_rate_limiter",
]
