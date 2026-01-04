"""
JWT Token Handler

Creates and verifies JWT tokens for API authentication.
Uses python-jose for token operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config_manager import get_config


class TokenData(BaseModel):
    """Token payload data"""

    sub: str  # Subject (username)
    exp: datetime  # Expiration
    iat: datetime  # Issued at


class JWTHandler:
    """
    Handles JWT token creation and verification

    Usage:
        handler = JWTHandler()
        token = handler.create_access_token("johan")
        data = handler.verify_token(token)

        # Or with custom values for testing:
        handler = JWTHandler(secret_key="...", expire_minutes=60)
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: Optional[str] = None,
        expire_minutes: Optional[int] = None,
    ) -> None:
        config = get_config()
        self.secret_key = secret_key or config.auth.jwt_secret_key
        self.algorithm = algorithm or config.auth.jwt_algorithm
        self.expire_minutes = expire_minutes or config.auth.jwt_expire_minutes

    def create_access_token(self, subject: str = "johan") -> str:
        """
        Create a new JWT access token

        Args:
            subject: Token subject (default: "johan" for single-user system)

        Returns:
            Encoded JWT token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.expire_minutes)

        payload = {
            "sub": subject,
            "exp": expire,
            "iat": now,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT token

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None if invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenData(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            )
        except JWTError:
            return None
