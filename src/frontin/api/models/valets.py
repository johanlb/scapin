"""
Valets API Models

Extended models for the enhanced valets dashboard:
- Detailed valet info with performance history
- Pipeline status for workflow visualization
- Cost metrics by model
- Health alerts
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Severity level for health alerts"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DailyMetrics(BaseModel):
    """Metrics for a single day"""

    date: str  # ISO date string (YYYY-MM-DD)
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_duration_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0


class ModelUsageStats(BaseModel):
    """Model usage breakdown (for Sancho)"""

    haiku_requests: int = 0
    haiku_tokens: int = 0
    haiku_cost_usd: float = 0.0
    sonnet_requests: int = 0
    sonnet_tokens: int = 0
    sonnet_cost_usd: float = 0.0
    opus_requests: int = 0
    opus_tokens: int = 0
    opus_cost_usd: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class ValetDetailsResponse(BaseModel):
    """Detailed information about a specific valet"""

    name: str
    display_name: str
    description: str
    status: str
    current_task: Optional[str] = None
    last_activity: Optional[datetime] = None

    # Today's stats
    tasks_completed_today: int = 0
    error_count_today: int = 0
    avg_duration_ms_today: int = 0
    tokens_used_today: int = 0

    # Extended activities (last 100)
    activities: list[dict] = Field(default_factory=list)

    # Performance over 7 days
    performance_7d: list[DailyMetrics] = Field(default_factory=list)

    # Model usage (Sancho only)
    model_usage: Optional[ModelUsageStats] = None

    # Additional valet-specific details
    details: dict = Field(default_factory=dict)


class PipelineStage(BaseModel):
    """Status of a single pipeline stage"""

    valet: str
    display_name: str
    icon: str
    status: str  # running, idle, paused, error
    items_processing: int = 0
    items_queued: int = 0
    avg_processing_time_ms: int = 0
    is_bottleneck: bool = False


class PipelineStatusResponse(BaseModel):
    """Complete pipeline status for workflow visualization"""

    stages: list[PipelineStage]
    total_in_pipeline: int = 0
    estimated_completion_minutes: float = 0.0
    bottleneck_valet: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelCosts(BaseModel):
    """Cost breakdown by model"""

    haiku_tokens: int = 0
    haiku_cost_usd: float = 0.0
    sonnet_tokens: int = 0
    sonnet_cost_usd: float = 0.0
    opus_tokens: int = 0
    opus_cost_usd: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class CostMetricsResponse(BaseModel):
    """Cost metrics for the dashboard"""

    period: str  # today, 7d, 30d
    costs_by_valet: dict[str, ModelCosts] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    projected_monthly_usd: float = 0.0
    cost_per_email_avg_usd: float = 0.0
    confidence_per_dollar: float = 0.0  # Efficiency metric
    daily_costs: list[DailyMetrics] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Alert(BaseModel):
    """A single health alert"""

    id: str
    severity: AlertSeverity
    valet: Optional[str] = None
    message: str
    details: Optional[str] = None
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


class AlertsResponse(BaseModel):
    """Health alerts response"""

    alerts: list[Alert] = Field(default_factory=list)
    total_critical: int = 0
    total_warning: int = 0
    total_info: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
