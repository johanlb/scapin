"""
Workflow v2.1 Router

API endpoints for knowledge extraction workflow.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.core.config_manager import get_config
from src.core.schemas import EmailAnalysis, EmailCategory
from src.jeeves.api.auth import TokenData
from src.jeeves.api.deps import get_current_user
from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.models.workflow import (
    AnalysisResultResponse,
    AnalyzeEmailRequest,
    ApplyExtractionsRequest,
    EnrichmentResultResponse,
    ExtractionResponse,
    ProcessInboxRequest,
    V2ProcessingResponse,
    WorkflowConfigResponse,
    WorkflowStatsResponse,
)
from src.jeeves.api.services.queue_service import get_queue_service
from src.monitoring.logger import get_logger

logger = get_logger("workflow_router")

router = APIRouter()

# Global stats tracking (in-memory for now)
_workflow_stats = {
    "events_processed": 0,
    "extractions_total": 0,
    "extractions_auto_applied": 0,
    "notes_created": 0,
    "notes_updated": 0,
    "tasks_created": 0,
    "escalations": 0,
    "total_confidence": 0.0,
    "total_duration_ms": 0.0,
}


def _get_v2_processor():
    """Get or create V2EmailProcessor instance"""
    config = get_config()

    if not config.workflow_v2.enabled:
        raise HTTPException(
            status_code=400,
            detail="Workflow v2.1 is not enabled in configuration",
        )

    from src.trivelin.v2_processor import V2EmailProcessor

    return V2EmailProcessor(config=config.workflow_v2)


@router.get("/config", response_model=APIResponse[WorkflowConfigResponse])
async def get_workflow_config(
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[WorkflowConfigResponse]:
    """
    Get current workflow v2.1 configuration

    Returns the configuration settings for the knowledge extraction workflow.
    """
    config = get_config()
    wf_config = config.workflow_v2

    return APIResponse(
        success=True,
        data=WorkflowConfigResponse(
            enabled=wf_config.enabled,
            default_model=wf_config.default_model,
            escalation_model=wf_config.escalation_model,
            escalation_threshold=wf_config.escalation_threshold,
            auto_apply_threshold=wf_config.auto_apply_threshold,
            context_notes_count=wf_config.context_notes_count,
            omnifocus_enabled=wf_config.omnifocus_enabled,
            omnifocus_default_project=wf_config.omnifocus_default_project,
        ),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/stats", response_model=APIResponse[WorkflowStatsResponse])
async def get_workflow_stats(
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[WorkflowStatsResponse]:
    """
    Get workflow v2.1 processing statistics

    Returns counts and metrics from knowledge extraction processing.
    """
    avg_confidence = 0.0
    avg_duration = 0.0

    if _workflow_stats["events_processed"] > 0:
        avg_confidence = _workflow_stats["total_confidence"] / _workflow_stats["events_processed"]
        avg_duration = _workflow_stats["total_duration_ms"] / _workflow_stats["events_processed"]

    return APIResponse(
        success=True,
        data=WorkflowStatsResponse(
            events_processed=_workflow_stats["events_processed"],
            extractions_total=_workflow_stats["extractions_total"],
            extractions_auto_applied=_workflow_stats["extractions_auto_applied"],
            notes_created=_workflow_stats["notes_created"],
            notes_updated=_workflow_stats["notes_updated"],
            tasks_created=_workflow_stats["tasks_created"],
            escalations=_workflow_stats["escalations"],
            average_confidence=avg_confidence,
            average_duration_ms=avg_duration,
        ),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/analyze/email", response_model=APIResponse[V2ProcessingResponse])
async def analyze_email_v2(
    request: AnalyzeEmailRequest,
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[V2ProcessingResponse]:
    """
    Analyze an email using workflow v2.1

    Processes the email through the knowledge extraction pipeline:
    1. Retrieves context notes
    2. Analyzes with EventAnalyzer (Haiku → Sonnet if needed)
    3. Auto-applies extractions if high confidence

    Args:
        request: Email ID and options

    Returns:
        V2ProcessingResponse with analysis and enrichment results
    """
    try:
        processor = _get_v2_processor()

        # Get email and convert to PerceivedEvent
        from src.core.events.universal_event import (
            EventSource,
            EventType,
            PerceivedEvent,
            UrgencyLevel,
        )

        now = datetime.now(timezone.utc)

        # For now, create a basic event from email ID
        # In production, this would fetch from IMAP
        event = PerceivedEvent(
            event_id=request.email_id,
            source=EventSource.EMAIL,
            source_id=request.email_id,
            occurred_at=now,
            received_at=now,
            title=f"Email {request.email_id}",
            content="",  # Would be populated from IMAP
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.NONE,
            entities=[],
            topics=[],
            keywords=[],
            from_person="unknown",
            to_people=[],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={"email_id": request.email_id},
            perception_confidence=0.5,
            needs_clarification=False,
            clarification_questions=[],
        )

        result = await processor.process_event(event, auto_apply=request.auto_apply)

        # Update stats
        _workflow_stats["events_processed"] += 1
        if result.analysis:
            _workflow_stats["extractions_total"] += result.analysis.extraction_count
            _workflow_stats["total_confidence"] += result.analysis.confidence
            if result.analysis.escalated:
                _workflow_stats["escalations"] += 1
        _workflow_stats["total_duration_ms"] += result.duration_ms

        if result.enrichment:
            _workflow_stats["notes_created"] += len(result.enrichment.notes_created)
            _workflow_stats["notes_updated"] += len(result.enrichment.notes_updated)
            _workflow_stats["tasks_created"] += len(result.enrichment.tasks_created)
            if result.auto_applied:
                _workflow_stats["extractions_auto_applied"] += result.extraction_count

        # Convert to response
        analysis_response = None
        if result.analysis:
            analysis_response = AnalysisResultResponse(
                extractions=[
                    ExtractionResponse(
                        info=e.info,
                        type=e.type.value,
                        importance=e.importance.value,
                        note_cible=e.note_cible,
                        note_action=e.note_action.value,
                        omnifocus=e.omnifocus,
                    )
                    for e in result.analysis.extractions
                ],
                action=result.analysis.action.value,
                confidence=result.analysis.confidence,
                raisonnement=result.analysis.raisonnement,
                model_used=result.analysis.model_used,
                tokens_used=result.analysis.tokens_used,
                duration_ms=result.analysis.duration_ms,
                escalated=result.analysis.escalated,
            )

        enrichment_response = None
        if result.enrichment:
            enrichment_response = EnrichmentResultResponse(
                notes_updated=result.enrichment.notes_updated,
                notes_created=result.enrichment.notes_created,
                tasks_created=result.enrichment.tasks_created,
                errors=result.enrichment.errors,
                success=result.enrichment.success,
            )

        return APIResponse(
            success=True,
            data=V2ProcessingResponse(
                success=result.success,
                event_id=result.event_id,
                analysis=analysis_response,
                enrichment=enrichment_response,
                email_action=result.email_action.value,
                error=result.error,
                duration_ms=result.duration_ms,
                auto_applied=result.auto_applied,
                timestamp=result.timestamp,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V2 analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/process-inbox")
async def process_inbox_v2(
    request: "ProcessInboxRequest",
    _user: Optional[TokenData] = Depends(get_current_user),
):
    """
    Process inbox emails using V2 workflow (context-aware)

    Fetches emails from IMAP and processes each through V2EmailProcessor:
    1. Retrieves context notes from knowledge base
    2. Analyzes with multi-pass AI (Haiku → Sonnet if needed)
    3. Auto-applies high-confidence enrichments
    4. Returns results compatible with legacy format

    Args:
        request: Processing options (limit, auto_execute, etc.)

    Returns:
        Processing results with emails, analysis, and enrichments
    """
    try:
        from src.core.events.universal_event import (
            EventSource,
            EventType,
            PerceivedEvent,
            UrgencyLevel,
        )
        from src.integrations.email.imap_client import IMAPClient

        processor = _get_v2_processor()
        config = get_config()

        # Initialize IMAP client
        imap_client = IMAPClient(config.email)

        # Fetch emails from IMAP
        with imap_client.connect():
            emails = imap_client.fetch_emails(
                folder=config.email.get_default_account().inbox_folder,
                limit=request.limit or 50,
                unread_only=request.unread_only,
                unprocessed_only=True,
            )

            results = []

            # Process each email through V2 pipeline
            for metadata, content in emails:
                # Convert to PerceivedEvent
                # Convert to PerceivedEvent
                event = PerceivedEvent(
                    event_id=str(metadata.id),
                    source=EventSource.EMAIL,
                    source_id=str(metadata.id),
                    occurred_at=metadata.date,
                    received_at=metadata.date,
                    perceived_at=datetime.now(timezone.utc),
                    title=metadata.subject or "No Subject",
                    content=content.plain_text or content.preview or "",
                    event_type=EventType.INFORMATION,
                    urgency=UrgencyLevel.LOW,
                    entities=[],
                    topics=[],
                    keywords=[],
                    from_person=metadata.from_name or metadata.from_address or "Unknown",
                    to_people=metadata.to_addresses or [],
                    cc_people=[],
                    thread_id=None,
                    references=[],
                    in_reply_to=None,
                    has_attachments=metadata.has_attachments,
                    attachment_count=1 if metadata.has_attachments else 0,
                    attachment_types=["unknown"] if metadata.has_attachments else [],
                    urls=[],
                    metadata={
                        "from_address": metadata.from_address,
                        "from_name": metadata.from_name,
                        "to_addresses": metadata.to_addresses,
                        "has_attachments": metadata.has_attachments,
                        "folder": metadata.folder,
                    },
                    perception_confidence=1.0,
                    needs_clarification=False,
                    clarification_questions=[],
                )

                # Process with V2 pipeline (context-aware)
                result = await processor.process_event(
                    event=event,
                    context_notes=None,  # Will be fetched automatically
                    auto_apply=request.auto_execute,
                )

                # Persist to queue logic
                if result.success:
                    try:
                        queue_service = get_queue_service()

                        # Default values
                        email_category = EmailCategory.OTHER
                        email_reasoning = "Analyzed by V2 Pipeline"

                        if result.analysis:
                            # Convert confidence to 0-100 int
                            confidence_int = int(result.analysis.effective_confidence * 100)
                            email_reasoning = result.analysis.raisonnement or email_reasoning

                            email_analysis = EmailAnalysis(
                                action=result.analysis.action,
                                category=email_category,  # V2 doesn't use categories yet
                                confidence=confidence_int,
                                reasoning=email_reasoning,
                                summary=f"Analyzed by {result.analysis.model_used}",
                                options=[],
                            )

                            await queue_service.enqueue_email(
                                metadata=metadata,
                                analysis=email_analysis,
                                content_preview=content.preview or "",
                                html_body=content.html,
                                full_text=content.plain_text,
                            )
                            logger.debug(f"Enqueued email {event.event_id}")

                    except Exception as e:
                        logger.error(
                            f"Failed to enqueue email {event.event_id}: {e}", exc_info=True
                        )

                results.append(result)

        # Convert to legacy format for frontend compatibility
        return {
            "total_processed": len(results),
            "auto_executed": sum(1 for r in results if r.auto_applied),
            "queued": sum(1 for r in results if r.needs_clarification),
            "skipped": 0,
            "emails": [
                {
                    "metadata": {
                        "id": r.event_id,
                        "subject": r.analysis.summary
                        if r.analysis and hasattr(r.analysis, "summary")
                        else "N/A",
                        "confidence": r.analysis.confidence if r.analysis else 0,
                    },
                    "analysis": {
                        "action": r.email_action.value,
                        "confidence": r.analysis.confidence if r.analysis else 0,
                        "extractions": r.extraction_count,
                        "notes_affected": r.notes_affected,
                        "context_notes_used": len(r.working_memory.context_notes)
                        if r.working_memory
                        else 0,
                    },
                    "enrichment": {
                        "auto_applied": r.auto_applied,
                        "needs_clarification": r.needs_clarification,
                        "pattern_matches": len(r.pattern_matches),
                    },
                    "executed": r.auto_applied,
                }
                for r in results
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V2 inbox processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/apply", response_model=APIResponse[EnrichmentResultResponse])
async def apply_extractions(
    request: ApplyExtractionsRequest,
    _user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[EnrichmentResultResponse]:
    """
    Manually apply extractions to PKM

    Used for applying extractions that weren't auto-applied
    or for re-applying with modifications.

    Args:
        request: Event ID and extractions to apply

    Returns:
        EnrichmentResultResponse with affected notes and tasks
    """
    try:
        from src.core.models.v2_models import (
            AnalysisResult,
            EmailAction,
            Extraction,
            ExtractionType,
            ImportanceLevel,
            NoteAction,
        )
        from src.passepartout.enricher import create_enricher

        config = get_config()

        # Convert request extractions to model objects
        extractions = [
            Extraction(
                info=e.info,
                type=ExtractionType(e.type),
                importance=ImportanceLevel(e.importance),
                note_cible=e.note_cible,
                note_action=NoteAction(e.note_action),
                omnifocus=e.omnifocus,
            )
            for e in request.extractions
        ]

        # Create enricher
        enricher = create_enricher(
            omnifocus_enabled=config.workflow_v2.omnifocus_enabled,
        )

        # Create a minimal analysis result for enrichment
        analysis = AnalysisResult(
            extractions=extractions,
            action=EmailAction.RIEN,
            confidence=1.0,  # Manual application
            raisonnement="Manual application via API",
            model_used="manual",
            tokens_used=0,
            duration_ms=0.0,
        )

        # Apply extractions
        result = await enricher.apply(analysis, request.event_id)

        # Update stats
        _workflow_stats["extractions_total"] += len(extractions)
        _workflow_stats["notes_created"] += len(result.notes_created)
        _workflow_stats["notes_updated"] += len(result.notes_updated)
        _workflow_stats["tasks_created"] += len(result.tasks_created)

        return APIResponse(
            success=True,
            data=EnrichmentResultResponse(
                notes_updated=result.notes_updated,
                notes_created=result.notes_created,
                tasks_created=result.tasks_created,
                errors=result.errors,
                success=result.success,
            ),
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Apply extractions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
