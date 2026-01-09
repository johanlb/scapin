"""
Valets Dashboard Router

REST API endpoints for monitoring the valet workers (Trivelin, Sancho, etc.).
Provides status, metrics, and activity timeline.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.jeeves.api.auth import TokenData
from src.jeeves.api.deps import get_current_user
from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.services.valets_stats_service import get_valets_stats_service

router = APIRouter()


class ValetStatus(str, Enum):
    """Status of a valet worker"""

    RUNNING = "running"
    IDLE = "idle"
    PAUSED = "paused"
    ERROR = "error"


class ValetType(str, Enum):
    """Types of valet workers"""

    TRIVELIN = "trivelin"  # Event perception & triage
    SANCHO = "sancho"  # AI reasoning
    PASSEPARTOUT = "passepartout"  # Knowledge base
    PLANCHET = "planchet"  # Planning
    FIGARO = "figaro"  # Execution
    SGANARELLE = "sganarelle"  # Learning
    JEEVES = "jeeves"  # API interface


class ValetActivity(BaseModel):
    """A single activity entry for a valet"""

    timestamp: datetime
    action: str
    details: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool = True


class ValetInfo(BaseModel):
    """Information about a single valet worker"""

    name: ValetType
    display_name: str
    description: str
    status: ValetStatus
    current_task: Optional[str] = None
    last_activity: Optional[datetime] = None
    tasks_completed_today: int = 0
    avg_task_duration_ms: Optional[int] = None
    error_count_today: int = 0
    recent_activities: list[ValetActivity] = Field(default_factory=list)


class ValetsDashboardResponse(BaseModel):
    """Complete dashboard response with all valets"""

    valets: list[ValetInfo]
    system_status: str  # "healthy", "degraded", "error"
    active_workers: int
    total_tasks_today: int
    avg_confidence: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValetMetrics(BaseModel):
    """Detailed metrics for a specific valet"""

    name: ValetType
    tasks_completed: int
    tasks_failed: int
    avg_duration_ms: int
    p95_duration_ms: int
    success_rate: float
    tokens_used: int
    api_calls: int


class ValetsMetricsResponse(BaseModel):
    """Metrics response for all valets"""

    period: str  # "today", "7d", "30d"
    metrics: list[ValetMetrics]
    total_tasks: int
    total_tokens: int
    total_api_calls: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# In-memory state for demo purposes
# In production, this would come from actual worker state
_valet_states: dict[ValetType, dict] = {
    ValetType.TRIVELIN: {
        "status": ValetStatus.IDLE,
        "current_task": None,
        "tasks_today": 0,
        "errors_today": 0,
        "activities": [],
    },
    ValetType.SANCHO: {
        "status": ValetStatus.IDLE,
        "current_task": None,
        "tasks_today": 0,
        "errors_today": 0,
        "activities": [],
    },
    ValetType.PASSEPARTOUT: {
        "status": ValetStatus.IDLE,
        "current_task": None,
        "tasks_today": 0,
        "errors_today": 0,
        "activities": [],
    },
    ValetType.PLANCHET: {
        "status": ValetStatus.IDLE,
        "current_task": None,
        "tasks_today": 0,
        "errors_today": 0,
        "activities": [],
    },
    ValetType.FIGARO: {
        "status": ValetStatus.IDLE,
        "current_task": None,
        "tasks_today": 0,
        "errors_today": 0,
        "activities": [],
    },
    ValetType.SGANARELLE: {
        "status": ValetStatus.IDLE,
        "current_task": None,
        "tasks_today": 0,
        "errors_today": 0,
        "activities": [],
    },
    ValetType.JEEVES: {
        "status": ValetStatus.RUNNING,
        "current_task": "Serving API requests",
        "tasks_today": 0,
        "errors_today": 0,
        "activities": [],
    },
}

VALET_DESCRIPTIONS = {
    ValetType.TRIVELIN: ("Trivelin", "Perception et triage des événements"),
    ValetType.SANCHO: ("Sancho", "Raisonnement IA multi-passes"),
    ValetType.PASSEPARTOUT: ("Passepartout", "Base de connaissances et contexte"),
    ValetType.PLANCHET: ("Planchet", "Planification et évaluation des risques"),
    ValetType.FIGARO: ("Figaro", "Exécution des actions"),
    ValetType.SGANARELLE: ("Sganarelle", "Apprentissage et amélioration continue"),
    ValetType.JEEVES: ("Jeeves", "Interface API et communication"),
}


def _get_valet_info(valet_type: ValetType) -> ValetInfo:
    """Build ValetInfo from current state using real stats"""
    display_name, description = VALET_DESCRIPTIONS[valet_type]

    # Get real stats from the service
    stats_service = get_valets_stats_service()
    valet_name = valet_type.value

    # Get stats for this specific valet
    stats_method = getattr(stats_service, f"get_{valet_name}_stats", None)
    real_stats = stats_method() if stats_method else stats_service._empty_stats()

    # Also get any recorded activities from in-memory state
    state = _valet_states[valet_type]
    activities = state.get("activities", [])

    # Map status string to enum
    status_str = real_stats.get("status", "idle")
    try:
        status = ValetStatus(status_str)
    except ValueError:
        status = ValetStatus.IDLE

    return ValetInfo(
        name=valet_type,
        display_name=display_name,
        description=description,
        status=status,
        current_task=real_stats.get("current_task"),
        last_activity=activities[-1]["timestamp"] if activities else None,
        tasks_completed_today=real_stats.get("tasks_today", 0),
        error_count_today=real_stats.get("errors_today", 0),
        recent_activities=[
            ValetActivity(**a) for a in activities[-10:]
        ],
    )


@router.get("", response_model=APIResponse[ValetsDashboardResponse])
async def get_valets_dashboard(
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ValetsDashboardResponse]:
    """
    Get complete valets dashboard

    Returns status of all valet workers with their current tasks,
    recent activities, and metrics.
    """
    valets = [_get_valet_info(vt) for vt in ValetType]

    # Get aggregated metrics from real stats
    stats_service = get_valets_stats_service()
    aggregate = stats_service.get_aggregate_metrics()

    active_workers = aggregate.get("active_workers", 0)
    total_tasks = aggregate.get("total_tasks_today", 0)
    avg_confidence = aggregate.get("avg_confidence", 0.85)

    # Determine system status
    error_valets = [v for v in valets if v.status == ValetStatus.ERROR]
    if error_valets:
        system_status = "error"
    elif active_workers < len(valets) // 2:
        system_status = "degraded"
    else:
        system_status = "healthy"

    return APIResponse(
        success=True,
        data=ValetsDashboardResponse(
            valets=valets,
            system_status=system_status,
            active_workers=active_workers,
            total_tasks_today=total_tasks,
            avg_confidence=avg_confidence,
        )
    )


@router.get("/metrics", response_model=APIResponse[ValetsMetricsResponse])
async def get_valets_metrics(
    period: str = "today",
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ValetsMetricsResponse]:
    """
    Get detailed metrics for all valets

    Args:
        period: Time period - "today", "7d", or "30d"
    """
    # Get real stats from service
    stats_service = get_valets_stats_service()
    all_stats = stats_service.get_all_stats()

    # Build metrics from real stats
    metrics: list[ValetMetrics] = []
    total_tokens = 0
    total_api_calls = 0

    for vt in ValetType:
        valet_stats = all_stats.get(vt.value, {})
        details = valet_stats.get("details", {})

        tasks_completed = valet_stats.get("tasks_today", 0)
        tasks_failed = valet_stats.get("errors_today", 0)

        # Calculate success rate
        total = tasks_completed + tasks_failed
        success_rate = tasks_completed / total if total > 0 else 1.0

        # Get specific metrics based on valet type
        avg_duration_ms = details.get("avg_duration_ms", 0)
        p95_duration_ms = details.get("p95_duration_ms", 0)
        tokens_used = details.get("total_tokens", 0)
        api_calls = details.get("total_requests", 0)

        total_tokens += tokens_used
        total_api_calls += api_calls

        metrics.append(ValetMetrics(
            name=vt,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            avg_duration_ms=int(avg_duration_ms),
            p95_duration_ms=int(p95_duration_ms),
            success_rate=round(success_rate, 3),
            tokens_used=tokens_used,
            api_calls=api_calls,
        ))

    return APIResponse(
        success=True,
        data=ValetsMetricsResponse(
            period=period,
            metrics=metrics,
            total_tasks=sum(m.tasks_completed for m in metrics),
            total_tokens=total_tokens,
            total_api_calls=total_api_calls,
        )
    )


@router.get("/{valet_name}", response_model=APIResponse[ValetInfo])
async def get_valet_status(
    valet_name: ValetType,
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ValetInfo]:
    """
    Get detailed status for a specific valet

    Args:
        valet_name: Name of the valet worker
    """
    return APIResponse(success=True, data=_get_valet_info(valet_name))


@router.get("/{valet_name}/activities", response_model=APIResponse[list[ValetActivity]])
async def get_valet_activities(
    valet_name: ValetType,
    limit: int = 50,
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[list[ValetActivity]]:
    """
    Get recent activities for a specific valet

    Args:
        valet_name: Name of the valet worker
        limit: Maximum number of activities to return
    """
    state = _valet_states[valet_name]
    activities = state["activities"][-limit:]
    return APIResponse(success=True, data=[ValetActivity(**a) for a in activities])


# Functions to update valet state (called by workers)
def update_valet_status(
    valet: ValetType,
    status: ValetStatus,
    current_task: Optional[str] = None,
) -> None:
    """Update a valet's status"""
    _valet_states[valet]["status"] = status
    _valet_states[valet]["current_task"] = current_task


def record_valet_activity(
    valet: ValetType,
    action: str,
    details: Optional[str] = None,
    duration_ms: Optional[int] = None,
    success: bool = True,
) -> None:
    """Record an activity for a valet"""
    activity = {
        "timestamp": datetime.now(timezone.utc),
        "action": action,
        "details": details,
        "duration_ms": duration_ms,
        "success": success,
    }

    state = _valet_states[valet]
    state["activities"].append(activity)
    state["tasks_today"] += 1 if success else 0
    state["errors_today"] += 0 if success else 1

    # Keep only last 100 activities
    if len(state["activities"]) > 100:
        state["activities"] = state["activities"][-100:]
