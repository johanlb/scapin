"""API Routers"""

from src.jeeves.api.routers.auth import router as auth_router
from src.jeeves.api.routers.briefing import router as briefing_router
from src.jeeves.api.routers.journal import router as journal_router
from src.jeeves.api.routers.system import router as system_router

__all__ = [
    "auth_router",
    "briefing_router",
    "journal_router",
    "system_router",
]
