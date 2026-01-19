"""
Valets Dashboard Router

REST API endpoints for monitoring the valet workers (Trivelin, Sancho, etc.).
Provides status, metrics, activity timeline, pipeline status, costs, and alerts.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.frontin.api.auth import TokenData
from src.frontin.api.deps import get_current_user
from src.frontin.api.models.responses import APIResponse
from src.frontin.api.models.valets import (
    Alert,
    AlertsResponse,
    CostMetricsResponse,
    DailyMetrics,
    ModelCosts,
    ModelUsageStats,
    PipelineStage,
    PipelineStatusResponse,
    ValetDetailsResponse,
)
from src.frontin.api.services.alerts_service import get_alerts_service
from src.frontin.api.services.valets_stats_service import get_valets_stats_service

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
    FRONTIN = "frontin"  # API interface


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
    ValetType.FRONTIN: {
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
    ValetType.FRONTIN: ("Frontin", "Interface API et communication"),
}

VALET_ICONS = {
    ValetType.TRIVELIN: "👁️",
    ValetType.SANCHO: "🧠",
    ValetType.PASSEPARTOUT: "📚",
    ValetType.PLANCHET: "📋",
    ValetType.FIGARO: "⚡",
    ValetType.SGANARELLE: "🎓",
    ValetType.FRONTIN: "🎭",
}

# Model pricing (January 2026) - USD per 1M tokens
MODEL_PRICING = {
    "haiku": {"input": 0.80, "output": 4.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus": {"input": 15.00, "output": 75.00},
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


@router.get("/{valet_name}/details", response_model=APIResponse[ValetDetailsResponse])
async def get_valet_details(
    valet_name: ValetType,
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[ValetDetailsResponse]:
    """
    Get detailed information about a specific valet including
    performance history and model usage breakdown.

    Args:
        valet_name: Name of the valet worker
    """
    display_name, description = VALET_DESCRIPTIONS[valet_name]
    stats_service = get_valets_stats_service()

    # Get stats for this valet
    stats_method = getattr(stats_service, f"get_{valet_name.value}_stats", None)
    stats = stats_method() if stats_method else stats_service._empty_stats()

    # Get activities from state
    state = _valet_states[valet_name]
    activities = state.get("activities", [])[-100:]

    # Generate mock 7-day performance data (in production, would come from actual history)
    performance_7d = []
    today = datetime.now(timezone.utc).date()
    for i in range(7):
        day = today - timedelta(days=6 - i)
        # Use actual stats for today, mock for history
        if i == 6:  # Today
            performance_7d.append(
                DailyMetrics(
                    date=day.isoformat(),
                    tasks_completed=stats.get("tasks_today", 0),
                    tasks_failed=stats.get("errors_today", 0),
                    avg_duration_ms=stats.get("details", {}).get("avg_duration_ms", 0),
                    tokens_used=stats.get("details", {}).get("total_tokens", 0),
                )
            )
        else:
            # Mock historical data based on today's stats with some variation
            base_tasks = max(1, stats.get("tasks_today", 10))
            performance_7d.append(
                DailyMetrics(
                    date=day.isoformat(),
                    tasks_completed=int(base_tasks * (0.8 + 0.4 * ((i + 1) / 7))),
                    tasks_failed=int(stats.get("errors_today", 0) * 0.5),
                    avg_duration_ms=stats.get("details", {}).get("avg_duration_ms", 150),
                    tokens_used=int(stats.get("details", {}).get("total_tokens", 0) * 0.9),
                )
            )

    # Model usage (Sancho only)
    model_usage = None
    if valet_name == ValetType.SANCHO:
        details = stats.get("details", {})
        total_tokens = details.get("total_tokens", 0)
        total_cost = details.get("total_cost_usd", 0)
        # Estimate distribution (in production, would track actual model usage)
        model_usage = ModelUsageStats(
            haiku_requests=int(details.get("total_requests", 0) * 0.45),
            haiku_tokens=int(total_tokens * 0.30),
            haiku_cost_usd=round(total_cost * 0.15, 4),
            sonnet_requests=int(details.get("total_requests", 0) * 0.40),
            sonnet_tokens=int(total_tokens * 0.50),
            sonnet_cost_usd=round(total_cost * 0.55, 4),
            opus_requests=int(details.get("total_requests", 0) * 0.15),
            opus_tokens=int(total_tokens * 0.20),
            opus_cost_usd=round(total_cost * 0.30, 4),
            total_requests=details.get("total_requests", 0),
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 4),
        )

    # Map status
    status_str = stats.get("status", "idle")
    try:
        status = ValetStatus(status_str)
    except ValueError:
        status = ValetStatus.IDLE

    return APIResponse(
        success=True,
        data=ValetDetailsResponse(
            name=valet_name.value,
            display_name=display_name,
            description=description,
            status=status.value,
            current_task=stats.get("current_task"),
            last_activity=activities[-1]["timestamp"] if activities else None,
            tasks_completed_today=stats.get("tasks_today", 0),
            error_count_today=stats.get("errors_today", 0),
            avg_duration_ms_today=stats.get("details", {}).get("avg_duration_ms", 0),
            tokens_used_today=stats.get("details", {}).get("total_tokens", 0),
            activities=[
                {
                    "timestamp": a["timestamp"].isoformat() if isinstance(a["timestamp"], datetime) else a["timestamp"],
                    "action": a["action"],
                    "details": a.get("details"),
                    "duration_ms": a.get("duration_ms"),
                    "success": a.get("success", True),
                }
                for a in activities
            ],
            performance_7d=performance_7d,
            model_usage=model_usage,
            details=stats.get("details", {}),
        ),
    )


@router.get("/pipeline", response_model=APIResponse[PipelineStatusResponse])
async def get_pipeline_status(
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[PipelineStatusResponse]:
    """
    Get the current pipeline status for workflow visualization.
    Shows items in progress at each stage.
    """
    stats_service = get_valets_stats_service()
    all_stats = stats_service.get_all_stats()

    # Pipeline order (email processing flow)
    pipeline_order = [
        ValetType.TRIVELIN,
        ValetType.SANCHO,
        ValetType.PASSEPARTOUT,
        ValetType.PLANCHET,
        ValetType.FIGARO,
        ValetType.SGANARELLE,
    ]

    stages: list[PipelineStage] = []
    total_in_pipeline = 0
    max_queue = 0
    bottleneck_valet = None

    for valet_type in pipeline_order:
        valet_stats = all_stats.get(valet_type.value, {})
        display_name, _ = VALET_DESCRIPTIONS[valet_type]
        icon = VALET_ICONS[valet_type]

        # Get queue sizes (mock data - in production from actual queues)
        # For now, use tasks_today as a proxy
        tasks = valet_stats.get("tasks_today", 0)
        items_processing = 1 if valet_stats.get("status") == "running" else 0
        items_queued = max(0, tasks % 10)  # Mock queue

        # Detect bottleneck (highest queue)
        if items_queued > max_queue:
            max_queue = items_queued
            bottleneck_valet = valet_type.value

        total_in_pipeline += items_processing + items_queued

        stages.append(
            PipelineStage(
                valet=valet_type.value,
                display_name=display_name,
                icon=icon,
                status=valet_stats.get("status", "idle"),
                items_processing=items_processing,
                items_queued=items_queued,
                avg_processing_time_ms=valet_stats.get("details", {}).get("avg_duration_ms", 0),
                is_bottleneck=False,  # Set below
            )
        )

    # Mark bottleneck (if queue > 5)
    if max_queue > 5 and bottleneck_valet:
        for stage in stages:
            if stage.valet == bottleneck_valet:
                stage.is_bottleneck = True

    # Estimate completion time
    avg_time_per_item_ms = 500  # Default estimate
    if stages:
        times = [s.avg_processing_time_ms for s in stages if s.avg_processing_time_ms > 0]
        if times:
            avg_time_per_item_ms = sum(times) / len(times)
    estimated_minutes = (total_in_pipeline * avg_time_per_item_ms) / 60000

    return APIResponse(
        success=True,
        data=PipelineStatusResponse(
            stages=stages,
            total_in_pipeline=total_in_pipeline,
            estimated_completion_minutes=round(estimated_minutes, 1),
            bottleneck_valet=bottleneck_valet if max_queue > 5 else None,
        ),
    )


@router.get("/costs", response_model=APIResponse[CostMetricsResponse])
async def get_cost_metrics(
    period: str = "today",
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[CostMetricsResponse]:
    """
    Get cost metrics by model and valet.

    Args:
        period: Time period - "today", "7d", or "30d"
    """
    stats_service = get_valets_stats_service()
    all_stats = stats_service.get_all_stats()

    # Get Sancho stats (main cost driver)
    sancho_details = all_stats.get("sancho", {}).get("details", {})
    total_tokens = sancho_details.get("total_tokens", 0)
    total_cost = sancho_details.get("total_cost_usd", 0)
    total_requests = sancho_details.get("total_requests", 0)

    # Estimate model distribution (in production, track actual usage)
    haiku_pct, sonnet_pct, opus_pct = 0.45, 0.40, 0.15

    # Build costs by valet (mainly Sancho uses AI)
    costs_by_valet: dict[str, ModelCosts] = {}
    for valet_type in ValetType:
        if valet_type == ValetType.SANCHO:
            costs_by_valet[valet_type.value] = ModelCosts(
                haiku_tokens=int(total_tokens * 0.30),
                haiku_cost_usd=round(total_cost * 0.15, 4),
                sonnet_tokens=int(total_tokens * 0.50),
                sonnet_cost_usd=round(total_cost * 0.55, 4),
                opus_tokens=int(total_tokens * 0.20),
                opus_cost_usd=round(total_cost * 0.30, 4),
                total_tokens=total_tokens,
                total_cost_usd=round(total_cost, 4),
            )
        else:
            costs_by_valet[valet_type.value] = ModelCosts()

    # Calculate projections
    trivelin_details = all_stats.get("trivelin", {}).get("details", {})
    emails_processed = trivelin_details.get("emails_processed", 0)
    cost_per_email = total_cost / emails_processed if emails_processed > 0 else 0

    # Project monthly based on period
    multiplier = {"today": 30, "7d": 4.3, "30d": 1}.get(period, 30)
    projected_monthly = total_cost * multiplier

    # Efficiency: confidence points per dollar
    confidence_avg = trivelin_details.get("confidence_avg", 85)
    confidence_per_dollar = confidence_avg / total_cost if total_cost > 0 else 0

    # Daily costs (mock for 7d)
    daily_costs: list[DailyMetrics] = []
    today = datetime.now(timezone.utc).date()
    for i in range(7):
        day = today - timedelta(days=6 - i)
        day_cost = total_cost / 7 * (0.8 + 0.4 * (i / 6))  # Slight variation
        daily_costs.append(
            DailyMetrics(
                date=day.isoformat(),
                tasks_completed=int(emails_processed / 7),
                cost_usd=round(day_cost, 4),
            )
        )

    return APIResponse(
        success=True,
        data=CostMetricsResponse(
            period=period,
            costs_by_valet=costs_by_valet,
            total_cost_usd=round(total_cost, 4),
            projected_monthly_usd=round(projected_monthly, 2),
            cost_per_email_avg_usd=round(cost_per_email, 4),
            confidence_per_dollar=round(confidence_per_dollar, 2),
            daily_costs=daily_costs,
        ),
    )


@router.get("/alerts", response_model=APIResponse[AlertsResponse])
async def get_alerts(
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[AlertsResponse]:
    """
    Get current health alerts for all valets.
    """
    stats_service = get_valets_stats_service()
    alerts_service = get_alerts_service()

    all_stats = stats_service.get_all_stats()
    response = alerts_service.check_alerts(all_stats)

    return APIResponse(success=True, data=response)


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
