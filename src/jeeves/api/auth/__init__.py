"""
Authentication Module

JWT-based authentication for Scapin API.
Single-user system with PIN code authentication.
"""

from src.jeeves.api.auth.jwt_handler import JWTHandler, TokenData
from src.jeeves.api.auth.password import get_pin_hash, verify_pin

__all__ = ["JWTHandler", "TokenData", "verify_pin", "get_pin_hash"]
