"""
Workflow v2.1 API Models

Pydantic models for the knowledge extraction workflow API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExtractionResponse(BaseModel):
    """Single extraction from analysis"""

    info: str = Field(description="Extracted information")
    type: str = Field(description="Type: decision, engagement, fait, deadline, relation")
    importance: str = Field(description="Importance: haute or moyenne")
    note_cible: str = Field(description="Target note title")
    note_action: str = Field(description="Action: enrichir or creer")
    omnifocus: bool = Field(default=False, description="Create OmniFocus task")


class AnalysisResultResponse(BaseModel):
    """Analysis result from MultiPassAnalyzer (Four Valets)"""

    extractions: list[ExtractionResponse] = Field(default_factory=list)
    action: str = Field(description="Recommended email action")
    confidence: float = Field(ge=0.0, le=1.0)
    raisonnement: str = Field(description="Analysis reasoning")
    model_used: str
    tokens_used: int
    duration_ms: float
    escalated: bool = False


class EnrichmentResultResponse(BaseModel):
    """Result of PKM enrichment"""

    notes_updated: list[str] = Field(default_factory=list)
    notes_created: list[str] = Field(default_factory=list)
    tasks_created: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    success: bool


class V2ProcessingResponse(BaseModel):
    """Complete v2.1 processing result"""

    success: bool
    event_id: str
    analysis: Optional[AnalysisResultResponse] = None
    enrichment: Optional[EnrichmentResultResponse] = None
    email_action: str = "rien"
    error: Optional[str] = None
    duration_ms: float = 0.0
    auto_applied: bool = False
    timestamp: datetime


class AnalyzeEventRequest(BaseModel):
    """Request to analyze a single event"""

    event_id: str = Field(description="ID of the event to analyze")
    auto_apply: bool = Field(default=True, description="Auto-apply high-confidence extractions")


class AnalyzeEmailRequest(BaseModel):
    """Request to analyze an email by ID"""

    email_id: str = Field(description="Email message ID")
    auto_apply: bool = Field(default=True, description="Auto-apply high-confidence extractions")


class ApplyExtractionsRequest(BaseModel):
    """Request to manually apply extractions"""

    event_id: str = Field(description="Event ID")
    extractions: list[ExtractionResponse] = Field(description="Extractions to apply")


class WorkflowConfigResponse(BaseModel):
    """Current workflow v2.1 configuration"""

    enabled: bool
    default_model: str
    escalation_model: str
    escalation_threshold: float
    auto_apply_threshold: float
    context_notes_count: int
    omnifocus_enabled: bool
    omnifocus_default_project: str


class WorkflowStatsResponse(BaseModel):
    """Workflow v2.1 statistics"""

    events_processed: int = 0
    extractions_total: int = 0
    extractions_auto_applied: int = 0
    notes_created: int = 0
    notes_updated: int = 0
    tasks_created: int = 0
    escalations: int = 0
    average_confidence: float = 0.0
    average_duration_ms: float = 0.0


class ProcessInboxRequest(BaseModel):
    """Request to process inbox emails with V2 workflow"""

    limit: int | None = Field(default=None, description="Maximum emails to process")
    auto_execute: bool = Field(default=False, description="Auto-execute high confidence actions")
    confidence_threshold: int | None = Field(
        default=None, description="Minimum confidence for auto-execution (deprecated)"
    )
    unread_only: bool = Field(default=False, description="Only process unread emails")
