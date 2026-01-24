"""API Routers"""

from src.frontin.api.routers.auth import router as auth_router
from src.frontin.api.routers.briefing import router as briefing_router
from src.frontin.api.routers.calendar import router as calendar_router
from src.frontin.api.routers.canevas import router as canevas_router
from src.frontin.api.routers.discussions import router as discussions_router
from src.frontin.api.routers.drafts import router as drafts_router
from src.frontin.api.routers.email import router as email_router
from src.frontin.api.routers.events import router as events_router
from src.frontin.api.routers.journal import router as journal_router
from src.frontin.api.routers.media import router as media_router
from src.frontin.api.routers.notes import router as notes_router
from src.frontin.api.routers.notifications import router as notifications_router
from src.frontin.api.routers.queue import router as queue_router
from src.frontin.api.routers.search import router as search_router
from src.frontin.api.routers.stats import router as stats_router
from src.frontin.api.routers.system import router as system_router
from src.frontin.api.routers.teams import router as teams_router
from src.frontin.api.routers.valets import router as valets_router
from src.frontin.api.routers.workflow import router as workflow_router

__all__ = [
    "auth_router",
    "briefing_router",
    "calendar_router",
    "canevas_router",
    "discussions_router",
    "drafts_router",
    "email_router",
    "events_router",
    "journal_router",
    "media_router",
    "notes_router",
    "notifications_router",
    "queue_router",
    "search_router",
    "stats_router",
    "system_router",
    "teams_router",
    "valets_router",
    "workflow_router",
]
