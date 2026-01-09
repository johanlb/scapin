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
    """Build ValetInfo from current state"""
    state = _valet_states[valet_type]
    display_name, description = VALET_DESCRIPTIONS[valet_type]

    return ValetInfo(
        name=valet_type,
        display_name=display_name,
        description=description,
        status=state["status"],
        current_task=state["current_task"],
        last_activity=state["activities"][-1]["timestamp"] if state["activities"] else None,
        tasks_completed_today=state["tasks_today"],
        error_count_today=state["errors_today"],
        recent_activities=[
            ValetActivity(**a) for a in state["activities"][-10:]
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

    active_workers = sum(1 for v in valets if v.status == ValetStatus.RUNNING)
    total_tasks = sum(v.tasks_completed_today for v in valets)

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
            avg_confidence=0.85,  # Would come from Sganarelle stats
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
    # This would query actual metrics from storage
    # For now, return placeholder data
    metrics = [
        ValetMetrics(
            name=vt,
            tasks_completed=_valet_states[vt]["tasks_today"],
            tasks_failed=_valet_states[vt]["errors_today"],
            avg_duration_ms=150,
            p95_duration_ms=500,
            success_rate=0.95,
            tokens_used=0,
            api_calls=0,
        )
        for vt in ValetType
    ]

    return APIResponse(
        success=True,
        data=ValetsMetricsResponse(
            period=period,
            metrics=metrics,
            total_tasks=sum(m.tasks_completed for m in metrics),
            total_tokens=sum(m.tokens_used for m in metrics),
            total_api_calls=sum(m.api_calls for m in metrics),
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
