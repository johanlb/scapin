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
from src.frontin.api.auth import JWTHandler, TokenData
from src.frontin.api.services.briefing_service import BriefingService
from src.frontin.api.services.discussion_service import DiscussionService
from src.frontin.api.services.email_service import EmailService
from src.frontin.api.services.notes_review_service import NotesReviewService
from src.frontin.api.services.notes_service import NotesService
from src.frontin.api.services.queue_service import QueueService
from src.passepartout.note_metadata import NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler

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


# Cached NotesService singleton to avoid re-indexing notes on every request
_notes_service_instance: NotesService | None = None


def get_notes_service() -> Generator[NotesService, None, None]:
    """Get notes service instance (cached singleton to avoid re-indexing)"""
    global _notes_service_instance
    if _notes_service_instance is None:
        config = get_cached_config()
        _notes_service_instance = NotesService(config=config)
    yield _notes_service_instance


# Cached NotesReviewService singleton to avoid creating new SQLite connections on every request
_notes_review_service_instance: NotesReviewService | None = None
_queue_service_instance: QueueService | None = None


def get_notes_review_service() -> Generator[NotesReviewService, None, None]:
    """Get notes review service instance (cached singleton to avoid connection pool exhaustion)"""
    global _notes_review_service_instance
    if _notes_review_service_instance is None:
        config = get_cached_config()
        _notes_review_service_instance = NotesReviewService(config=config)
    yield _notes_review_service_instance


def get_queue_service() -> Generator[QueueService, None, None]:
    """Get queue service instance (cached singleton to preserve in_progress state)"""
    global _queue_service_instance
    if _queue_service_instance is None:
        _queue_service_instance = QueueService()
    yield _queue_service_instance


def get_email_service() -> Generator[EmailService, None, None]:
    """Get email service instance"""
    service = EmailService()
    yield service


def get_discussion_service() -> Generator[DiscussionService, None, None]:
    """Get discussion service instance"""
    config = get_cached_config()
    service = DiscussionService(config=config)
    yield service


# Cached NoteMetadataStore singleton to avoid creating new SQLite connections on every request
_metadata_store_instance: NoteMetadataStore | None = None


def get_metadata_store() -> Generator[NoteMetadataStore, None, None]:
    """Get metadata store instance (cached singleton to avoid connection pool exhaustion)"""
    global _metadata_store_instance
    if _metadata_store_instance is None:
        config = get_cached_config()
        # Use database directory for notes metadata
        data_dir = config.storage.database_path.parent
        db_path = data_dir / "notes_meta.db"
        _metadata_store_instance = NoteMetadataStore(db_path)
    yield _metadata_store_instance


# Cached NoteScheduler singleton (depends on metadata store)
_scheduler_instance: NoteScheduler | None = None


def get_scheduler() -> Generator[NoteScheduler, None, None]:
    """Get scheduler instance (cached singleton)"""
    global _scheduler_instance
    if _scheduler_instance is None:
        # Get the metadata store singleton
        store = next(get_metadata_store())
        _scheduler_instance = NoteScheduler(store)
    yield _scheduler_instance
