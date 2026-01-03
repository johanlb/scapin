"""
API Dependencies

Dependency injection for FastAPI endpoints.
Provides services and configuration access.
"""

from collections.abc import Generator
from functools import lru_cache

from src.core.config_manager import ScapinConfig, get_config
from src.jeeves.api.services.briefing_service import BriefingService


@lru_cache
def get_cached_config() -> ScapinConfig:
    """Get cached configuration"""
    return get_config()


def get_briefing_service() -> Generator[BriefingService, None, None]:
    """Get briefing service instance"""
    config = get_cached_config()
    service = BriefingService(config=config)
    yield service
