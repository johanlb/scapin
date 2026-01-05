"""API Routers"""

from src.jeeves.api.routers.auth import router as auth_router
from src.jeeves.api.routers.briefing import router as briefing_router
from src.jeeves.api.routers.calendar import router as calendar_router
from src.jeeves.api.routers.email import router as email_router
from src.jeeves.api.routers.journal import router as journal_router
from src.jeeves.api.routers.notes import router as notes_router
from src.jeeves.api.routers.queue import router as queue_router
from src.jeeves.api.routers.search import router as search_router
from src.jeeves.api.routers.stats import router as stats_router
from src.jeeves.api.routers.system import router as system_router
from src.jeeves.api.routers.teams import router as teams_router

__all__ = [
    "auth_router",
    "briefing_router",
    "calendar_router",
    "email_router",
    "journal_router",
    "notes_router",
    "queue_router",
    "search_router",
    "stats_router",
    "system_router",
    "teams_router",
]
