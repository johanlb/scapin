"""
Email Router

API endpoints for email processing.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.frontin.api.deps import get_email_service
from src.frontin.api.models.email import (
    AnalyzeEmailRequest,
    CreateFolderRequest,
    CreateFolderResponse,
    EmailAccountResponse,
    EmailAnalysisResponse,
    EmailMetadataResponse,
    EmailStatsResponse,
    ExecuteActionRequest,
    FolderResponse,
    FolderSuggestionResponse,
    FolderSuggestionsResponse,
    FolderTreeNode,
    ProcessedEmailResponse,
    ProcessInboxRequest,
    ProcessInboxResponse,
    RecordArchiveRequest,
)
from src.frontin.api.models.responses import APIResponse
from src.frontin.api.services.email_service import EmailService
from src.frontin.api.utils import parse_datetime

router = APIRouter()


@router.get("/accounts", response_model=APIResponse[list[EmailAccountResponse]])
async def list_email_accounts(
    service: EmailService = Depends(get_email_service),
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
    service: EmailService = Depends(get_email_service),
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
    service: EmailService = Depends(get_email_service),
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
            unprocessed_only=request.unprocessed_only,
        )

        emails = [
            ProcessedEmailResponse(
                metadata=EmailMetadataResponse(
                    id=str(e["metadata"]["id"]),
                    subject=e["metadata"]["subject"],
                    from_address=e["metadata"]["from_address"],
                    from_name=e["metadata"].get("from_name"),
                    date=parse_datetime(e["metadata"].get("date")),
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
                processed_at=parse_datetime(e["processed_at"]) or datetime.now(timezone.utc),
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
    service: EmailService = Depends(get_email_service),
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
                    date=parse_datetime(result["metadata"].get("date")),
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
    service: EmailService = Depends(get_email_service),
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


@router.get("/attachment/{email_id}/{filename}")
async def get_attachment(
    email_id: str,
    filename: str,
    folder: str = "INBOX",
    service: EmailService = Depends(get_email_service),
) -> Response:
    """
    Download an email attachment

    Args:
        email_id: Email message ID
        filename: Attachment filename
        folder: IMAP folder (default: INBOX)

    Returns:
        Attachment content as binary response
    """
    try:
        result = await service.get_attachment(int(email_id), filename, folder)

        if result is None:
            raise HTTPException(status_code=404, detail="Attachment not found")

        content, content_type = result
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "private, max-age=3600",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid email ID: {e}") from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Folder Endpoints
# ============================================================================


@router.get("/folders", response_model=APIResponse[list[FolderResponse]])
async def list_folders(
    service: EmailService = Depends(get_email_service),
) -> APIResponse[list[FolderResponse]]:
    """
    List all IMAP folders

    Returns flat list of all available folders with metadata.
    """
    try:
        folders = await service.get_folders()

        return APIResponse(
            success=True,
            data=[
                FolderResponse(
                    path=f["path"],
                    name=f["name"],
                    delimiter=f["delimiter"],
                    has_children=f["has_children"],
                    selectable=f["selectable"],
                )
                for f in folders
            ],
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/folders/tree", response_model=APIResponse[list[FolderTreeNode]])
async def get_folder_tree(
    service: EmailService = Depends(get_email_service),
) -> APIResponse[list[FolderTreeNode]]:
    """
    Get hierarchical folder tree

    Returns folders as a nested tree structure for UI display.
    """
    try:
        tree = await service.get_folder_tree()

        def convert_node(node: dict) -> FolderTreeNode:
            return FolderTreeNode(
                name=node["name"],
                path=node["path"],
                children=[convert_node(c) for c in node.get("children", [])],
            )

        return APIResponse(
            success=True,
            data=[convert_node(n) for n in tree],
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/folders/suggested", response_model=APIResponse[FolderSuggestionsResponse])
async def get_folder_suggestions(
    sender_email: str | None = None,
    subject: str | None = None,
    limit: int = 5,
    service: EmailService = Depends(get_email_service),
) -> APIResponse[FolderSuggestionsResponse]:
    """
    Get AI-powered folder suggestions

    Returns learned folder suggestions based on sender and subject,
    plus recently and frequently used folders.

    Args:
        sender_email: Sender's email address for matching
        subject: Email subject for keyword matching
        limit: Maximum suggestions to return (1-20)
    """
    try:
        result = await service.get_folder_suggestions(
            sender_email=sender_email,
            subject=subject,
            limit=min(limit, 20),
        )

        return APIResponse(
            success=True,
            data=FolderSuggestionsResponse(
                suggestions=[
                    FolderSuggestionResponse(
                        folder=s["folder"],
                        confidence=s["confidence"],
                        reason=s["reason"],
                    )
                    for s in result["suggestions"]
                ],
                recent_folders=result["recent_folders"],
                popular_folders=result["popular_folders"],
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/folders", response_model=APIResponse[CreateFolderResponse])
async def create_folder(
    request: CreateFolderRequest,
    service: EmailService = Depends(get_email_service),
) -> APIResponse[CreateFolderResponse]:
    """
    Create a new IMAP folder

    Supports nested folder paths (e.g., 'Archive/Projects/2024').
    Parent folders are created automatically if needed.
    """
    try:
        result = await service.create_folder(request.path)

        return APIResponse(
            success=True,
            data=CreateFolderResponse(
                path=result["path"],
                created=result["created"],
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/folders/record-archive", response_model=APIResponse[dict])
async def record_archive(
    request: RecordArchiveRequest,
    service: EmailService = Depends(get_email_service),
) -> APIResponse[dict]:
    """
    Record an archive action for learning

    Call this after archiving an email to train the folder suggestion system.
    The system learns from sender, domain, and subject keywords.
    """
    try:
        success = await service.record_archive(
            folder=request.folder,
            sender_email=request.sender_email,
            subject=request.subject,
        )

        return APIResponse(
            success=success,
            data={
                "folder": request.folder,
                "recorded": success,
            },
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
