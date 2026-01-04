"""
Email Router

API endpoints for email processing.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.jeeves.api.models.email import (
    AnalyzeEmailRequest,
    EmailAccountResponse,
    EmailAnalysisResponse,
    EmailMetadataResponse,
    EmailStatsResponse,
    ExecuteActionRequest,
    ProcessedEmailResponse,
    ProcessInboxRequest,
    ProcessInboxResponse,
)
from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.services.email_service import EmailService

router = APIRouter()


def _get_email_service() -> EmailService:
    """Dependency to get email service"""
    return EmailService()


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@router.get("/accounts", response_model=APIResponse[list[EmailAccountResponse]])
async def list_email_accounts(
    service: EmailService = Depends(_get_email_service),
) -> APIResponse[list[EmailAccountResponse]]:
    """
    List configured email accounts

    Returns enabled email accounts with their configuration.
    """
    try:
        accounts = await service.get_accounts()

        return APIResponse(
            success=True,
            data=[
                EmailAccountResponse(
                    name=a["name"],
                    email=a["email"],
                    enabled=a["enabled"],
                    inbox_folder=a["inbox_folder"],
                )
                for a in accounts
            ],
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats", response_model=APIResponse[EmailStatsResponse])
async def get_email_stats(
    service: EmailService = Depends(_get_email_service),
) -> APIResponse[EmailStatsResponse]:
    """
    Get email processing statistics

    Returns counts and metrics from email processing.
    """
    try:
        stats = await service.get_stats()

        return APIResponse(
            success=True,
            data=EmailStatsResponse(
                emails_processed=stats.get("emails_processed", 0),
                emails_auto_executed=stats.get("emails_auto_executed", 0),
                emails_archived=stats.get("emails_archived", 0),
                emails_deleted=stats.get("emails_deleted", 0),
                emails_queued=stats.get("emails_queued", 0),
                emails_skipped=stats.get("emails_skipped", 0),
                tasks_created=stats.get("tasks_created", 0),
                average_confidence=stats.get("average_confidence", 0.0),
                processing_mode=stats.get("processing_mode", "unknown"),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/process", response_model=APIResponse[ProcessInboxResponse])
async def process_inbox(
    request: ProcessInboxRequest = ProcessInboxRequest(),
    service: EmailService = Depends(_get_email_service),
) -> APIResponse[ProcessInboxResponse]:
    """
    Process inbox emails

    Fetches and processes emails from the inbox using AI analysis.
    High-confidence actions can be auto-executed if enabled.
    """
    try:
        result = await service.process_inbox(
            limit=request.limit,
            auto_execute=request.auto_execute,
            confidence_threshold=request.confidence_threshold,
            unread_only=request.unread_only,
        )

        emails = [
            ProcessedEmailResponse(
                metadata=EmailMetadataResponse(
                    id=e["metadata"]["id"],
                    subject=e["metadata"]["subject"],
                    from_address=e["metadata"]["from_address"],
                    from_name=e["metadata"].get("from_name"),
                    date=_parse_datetime(e["metadata"].get("date")),
                    has_attachments=e["metadata"].get("has_attachments", False),
                    folder=e["metadata"].get("folder"),
                ),
                analysis=EmailAnalysisResponse(
                    action=e["analysis"]["action"],
                    confidence=e["analysis"]["confidence"],
                    category=e["analysis"].get("category"),
                    reasoning=e["analysis"].get("reasoning"),
                    destination=e["analysis"].get("destination"),
                ),
                processed_at=_parse_datetime(e["processed_at"]) or datetime.now(timezone.utc),
                executed=e.get("executed", False),
            )
            for e in result.get("emails", [])
        ]

        return APIResponse(
            success=True,
            data=ProcessInboxResponse(
                total_processed=result.get("total_processed", 0),
                auto_executed=result.get("auto_executed", 0),
                queued=result.get("queued", 0),
                skipped=result.get("skipped", 0),
                emails=emails,
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/analyze", response_model=APIResponse[ProcessedEmailResponse])
async def analyze_email(
    request: AnalyzeEmailRequest,
    service: EmailService = Depends(_get_email_service),
) -> APIResponse[ProcessedEmailResponse]:
    """
    Analyze a single email

    Fetches and analyzes one email without executing any action.
    """
    try:
        result = await service.analyze_email(
            email_id=request.email_id,
            folder=request.folder,
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Email not found: {request.email_id}",
            )

        return APIResponse(
            success=True,
            data=ProcessedEmailResponse(
                metadata=EmailMetadataResponse(
                    id=result["metadata"]["id"],
                    subject=result["metadata"]["subject"],
                    from_address=result["metadata"]["from_address"],
                    from_name=result["metadata"].get("from_name"),
                    date=_parse_datetime(result["metadata"].get("date")),
                    has_attachments=result["metadata"].get("has_attachments", False),
                    folder=result["metadata"].get("folder"),
                ),
                analysis=EmailAnalysisResponse(
                    action=result["analysis"]["action"],
                    confidence=result["analysis"]["confidence"],
                    category=result["analysis"].get("category"),
                    reasoning=result["analysis"].get("reasoning"),
                    destination=result["analysis"].get("destination"),
                ),
                processed_at=datetime.now(timezone.utc),
                executed=False,
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/execute", response_model=APIResponse[dict])
async def execute_action(
    request: ExecuteActionRequest,
    service: EmailService = Depends(_get_email_service),
) -> APIResponse[dict]:
    """
    Execute an action on an email

    Performs the specified action (archive, delete, task) on an email.
    """
    try:
        success = await service.execute_action(
            email_id=request.email_id,
            action=request.action,
            destination=request.destination,
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to execute action {request.action} on email {request.email_id}",
            )

        return APIResponse(
            success=True,
            data={
                "email_id": request.email_id,
                "action": request.action,
                "executed": True,
            },
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
