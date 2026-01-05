"""
API Dependencies

Dependency injection for FastAPI endpoints.
Provides services and configuration access.
"""

from collections.abc import Generator
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config_manager import ScapinConfig, get_config
from src.jeeves.api.auth import JWTHandler, TokenData
from src.jeeves.api.services.briefing_service import BriefingService
from src.jeeves.api.services.notes_review_service import NotesReviewService
from src.jeeves.api.services.notes_service import NotesService

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)

# Cached JWT handler
_jwt_handler: Optional[JWTHandler] = None


@lru_cache
def get_cached_config() -> ScapinConfig:
    """Get cached configuration"""
    return get_config()


def get_jwt_handler() -> JWTHandler:
    """Get cached JWT handler instance"""
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler()
    return _jwt_handler


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
) -> Optional[TokenData]:
    """
    Dependency to verify JWT token and get current user

    If auth is disabled in config, returns None (allows access).
    If auth is enabled and token is invalid/missing, raises 401.

    Usage:
        @router.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user": user.sub if user else "anonymous"}
    """
    config = get_cached_config()

    # If auth is disabled, allow all requests
    if not config.auth.enabled:
        return None

    # Auth is enabled - require valid token
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = jwt_handler.verify_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


def get_briefing_service() -> Generator[BriefingService, None, None]:
    """Get briefing service instance"""
    config = get_cached_config()
    service = BriefingService(config=config)
    yield service


def get_notes_service() -> Generator[NotesService, None, None]:
    """Get notes service instance"""
    config = get_cached_config()
    service = NotesService(config=config)
    yield service


def get_notes_review_service() -> Generator[NotesReviewService, None, None]:
    """Get notes review service instance"""
    config = get_cached_config()
    service = NotesReviewService(config=config)
    yield service
