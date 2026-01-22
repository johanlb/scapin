"""
Workflow v2.1 Router

API endpoints for knowledge extraction workflow.
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    from src.frontin.api.services.queue_service import QueueService
    from src.integrations.email.models import EmailContent, EmailMetadata

from src.core.config_manager import get_config
from src.core.schemas import EmailAnalysis, EmailCategory
from src.frontin.api.auth import TokenData
from src.frontin.api.deps import get_current_user
from src.frontin.api.models.responses import APIResponse
from src.frontin.api.models.workflow import (
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
from src.frontin.api.services.queue_service import get_queue_service
from src.monitoring.logger import get_logger

logger = get_logger("workflow_router")


def _build_multi_pass_data(multi_pass_result: Any) -> dict[str, Any] | None:
    """
    Convert MultiPassResult to dict format for storage (v2.3 Analysis Transparency).

    Args:
        multi_pass_result: MultiPassResult from V2EmailProcessor

    Returns:
        Dict with multi_pass metadata or None if not available
    """
    if not multi_pass_result or not hasattr(multi_pass_result, "pass_history"):
        return None

    if not multi_pass_result.pass_history:
        return None

    # Build pass_history list
    pass_history = []
    models_used = []
    prev_confidence = 0.0

    for i, pass_result in enumerate(multi_pass_result.pass_history):
        model = getattr(pass_result, "model_used", "unknown")
        models_used.append(model)

        # Get pass type
        pass_type = getattr(pass_result, "pass_type", None)
        pass_type_value = pass_type.value if hasattr(pass_type, "value") else str(pass_type)

        # Get confidence
        confidence_after = getattr(pass_result, "confidence", None)
        if confidence_after and hasattr(confidence_after, "overall"):
            confidence_after = confidence_after.overall
        elif not isinstance(confidence_after, (int, float)):
            confidence_after = 0.0

        # Check for escalation
        escalation_triggered = False
        if i > 0:
            prev_model = models_used[i - 1]
            escalation_triggered = (prev_model == "haiku" and model in ["sonnet", "opus"]) or (
                prev_model == "sonnet" and model == "opus"
            )

        pass_history.append(
            {
                "pass_number": i + 1,
                "model_used": model,
                "pass_type": pass_type_value,
                "duration_ms": getattr(pass_result, "duration_ms", 0),
                "tokens_used": getattr(pass_result, "tokens_used", 0),
                "confidence_before": prev_confidence,
                "confidence_after": confidence_after,
                "escalation_triggered": escalation_triggered,
                "reasoning": getattr(pass_result, "reasoning", ""),
                "thinking_bubbles": getattr(pass_result, "thinking_bubbles", []),
            }
        )
        prev_confidence = confidence_after

    return {
        "passes_count": multi_pass_result.passes_count,
        "final_model": multi_pass_result.final_model,
        "models_used": models_used,
        "escalated": multi_pass_result.escalated,
        "stop_reason": multi_pass_result.stop_reason,
        "high_stakes": multi_pass_result.high_stakes,
        "total_tokens": multi_pass_result.total_tokens,
        "total_duration_ms": multi_pass_result.total_duration_ms,
        "pass_history": pass_history,
    }


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
    2. Analyzes with MultiPassAnalyzer (Four Valets v3.0)
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

    New flow (v2.5):
    1. Fetch emails from IMAP
    2. Create queue items in ANALYZING state immediately (shown in "En cours")
    3. Return response quickly with count of items being analyzed
    4. Run analysis in background, updating each item when complete

    Args:
        request: Processing options (limit, auto_execute, etc.)

    Returns:
        Processing results with count of items queued for analysis
    """
    try:
        from src.integrations.email.imap_client import IMAPClient

        config = get_config()
        queue_service = get_queue_service()

        # Initialize IMAP client
        imap_client = IMAPClient(config.email)

        # Phase 1: Fetch emails and create ANALYZING items immediately
        items_to_analyze: list[tuple[str, EmailMetadata, EmailContent]] = []

        with imap_client.connect():
            emails = imap_client.fetch_emails(
                folder=config.email.get_default_account().inbox_folder,
                limit=request.limit or 50,
                unread_only=request.unread_only,
                unprocessed_only=True,
            )

            for metadata, content in emails:
                # Create item in ANALYZING state immediately
                item_id = await queue_service.create_analyzing_item(
                    metadata=metadata,
                    content_preview=content.preview or "",
                    account_id="default",
                    html_body=content.html,
                    full_text=content.plain_text,
                )

                if item_id:
                    items_to_analyze.append((item_id, metadata, content))
                    logger.debug(f"Created analyzing item {item_id} for {metadata.subject}")

        if not items_to_analyze:
            return {
                "total_processed": 0,
                "in_progress": 0,
                "queued": 0,
                "skipped": 0,
                "emails": [],
                "status": "no_new_emails",
            }

        # Phase 2: Start background analysis task
        asyncio.create_task(
            _analyze_items_background(
                items_to_analyze,
                queue_service,
                auto_execute=request.auto_execute,
            )
        )

        logger.info(
            f"Started background analysis for {len(items_to_analyze)} emails",
            extra={"count": len(items_to_analyze)},
        )

        # Return immediately with items in progress
        return {
            "total_processed": len(items_to_analyze),
            "in_progress": len(items_to_analyze),
            "queued": 0,  # Will be updated as analysis completes
            "skipped": 0,
            "emails": [
                {
                    "metadata": {
                        "id": item_id,
                        "subject": metadata.subject,
                        "confidence": 0,  # Not yet analyzed
                    },
                    "analysis": {
                        "action": "analyzing",
                        "confidence": 0,
                        "extractions": 0,
                        "notes_affected": 0,
                        "context_notes_used": 0,
                    },
                    "enrichment": {
                        "auto_applied": False,
                        "needs_clarification": True,
                        "pattern_matches": 0,
                    },
                    "executed": False,
                }
                for item_id, metadata, content in items_to_analyze
            ],
            "status": "analyzing",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V2 inbox processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _analyze_items_background(
    items: list[tuple[str, "EmailMetadata", "EmailContent"]],
    queue_service: "QueueService",
    auto_execute: bool = False,
) -> None:
    """
    Background task to analyze items and update their state.

    Args:
        items: List of (item_id, metadata, content) tuples
        queue_service: Queue service instance
        auto_execute: Whether to auto-apply high-confidence enrichments
    """
    from src.core.events.universal_event import (
        EventSource,
        EventType,
        PerceivedEvent,
        UrgencyLevel,
    )

    processor = _get_v2_processor()

    # Use semaphore to limit concurrent analysis
    semaphore = asyncio.Semaphore(3)

    async def analyze_single(item_id: str, metadata: "EmailMetadata", content: "EmailContent") -> bool:
        """Analyze a single item with semaphore control."""
        async with semaphore:
            try:
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

                # Process with V2 pipeline
                result = await processor.process_event(
                    event=event,
                    context_notes=None,
                    auto_apply=auto_execute,
                )

                if result.success and result.analysis:
                    # Build EmailAnalysis from result
                    email_analysis = EmailAnalysis(
                        action=result.analysis.action,
                        category=EmailCategory.OTHER,
                        confidence=int(result.analysis.effective_confidence * 100),
                        reasoning=result.analysis.raisonnement or "Analyzed by V2 Pipeline",
                        summary=f"Analyzed by {result.analysis.model_used}",
                        options=[],
                    )

                    # Build multi_pass data
                    multi_pass_data = _build_multi_pass_data(result.multi_pass_result)

                    # Update item with analysis results
                    await queue_service.complete_analysis(
                        item_id=item_id,
                        analysis=email_analysis,
                        multi_pass_data=multi_pass_data,
                    )

                    logger.debug(
                        f"Analysis completed for item {item_id}",
                        extra={"confidence": email_analysis.confidence},
                    )
                    return True
                else:
                    # Mark as error
                    error_msg = "Analysis failed or returned no results"
                    await queue_service.mark_analysis_error(item_id, error_msg)
                    logger.warning(f"Analysis failed for item {item_id}: {error_msg}")
                    return False

            except Exception as e:
                error_msg = str(e)
                await queue_service.mark_analysis_error(item_id, error_msg)
                logger.error(f"Error analyzing item {item_id}: {e}", exc_info=True)
                return False

    # Run all analyses in parallel with semaphore control
    results = await asyncio.gather(
        *[analyze_single(item_id, metadata, content) for item_id, metadata, content in items],
        return_exceptions=True,
    )

    succeeded = sum(1 for r in results if r is True)
    failed = len(items) - succeeded

    logger.info(
        f"Background analysis complete: {succeeded}/{len(items)} succeeded, {failed} failed"
    )


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
            action=EmailAction.KEEP,  # Manual application keeps email
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
