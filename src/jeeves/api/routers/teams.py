"""
Teams Router

API endpoints for Teams chat management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.models.responses import APIResponse, PaginatedResponse
from src.jeeves.api.models.teams import (
    FlagMessageRequest,
    SendReplyRequest,
    TeamsChatResponse,
    TeamsMessageResponse,
    TeamsPollResponse,
    TeamsSenderResponse,
    TeamsStatsResponse,
)
from src.jeeves.api.services.teams_service import TeamsService

router = APIRouter()


def _get_teams_service() -> TeamsService:
    """Dependency to get Teams service"""
    return TeamsService()


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _convert_chat_to_response(chat: dict) -> TeamsChatResponse:
    """Convert chat dict to response model"""
    return TeamsChatResponse(
        id=chat.get("id", ""),
        topic=chat.get("topic"),
        chat_type=chat.get("chat_type", "oneOnOne"),
        created_at=_parse_datetime(chat.get("created_at")),
        last_message_at=_parse_datetime(chat.get("last_message_at")),
        member_count=chat.get("member_count", 0),
        unread_count=chat.get("unread_count", 0),
    )


def _convert_message_to_response(msg: dict) -> TeamsMessageResponse:
    """Convert message dict to response model"""
    sender = msg.get("sender", {})
    return TeamsMessageResponse(
        id=msg.get("id", ""),
        chat_id=msg.get("chat_id", ""),
        sender=TeamsSenderResponse(
            id=sender.get("id", ""),
            display_name=sender.get("display_name", "Unknown"),
            email=sender.get("email"),
        ),
        content=msg.get("content", ""),
        content_preview=msg.get("content_preview", ""),
        created_at=_parse_datetime(msg.get("created_at")) or datetime.now(timezone.utc),
        is_read=msg.get("is_read", True),
        importance=msg.get("importance", "normal"),
        has_mentions=msg.get("has_mentions", False),
        attachments_count=msg.get("attachments_count", 0),
    )


@router.get("/messages", response_model=PaginatedResponse[list[TeamsMessageResponse]])
async def list_recent_messages(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    since: datetime | None = Query(None, description="Only messages since this time"),
    mentions_only: bool = Query(False, description="Only messages where you are @mentioned"),
    service: TeamsService = Depends(_get_teams_service),
) -> PaginatedResponse[list[TeamsMessageResponse]]:
    """
    List recent messages from all chats

    Returns messages from all chats, optionally filtered by @mentions.
    """
    try:
        messages = await service.get_recent_messages(
            limit_per_chat=page * page_size,
            since=since,
            mentions_only=mentions_only,
        )

        # Apply pagination
        total = len(messages)
        start = (page - 1) * page_size
        end = start + page_size
        page_messages = messages[start:end]

        return PaginatedResponse(
            success=True,
            data=[_convert_message_to_response(m) for m in page_messages],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/chats", response_model=PaginatedResponse[list[TeamsChatResponse]])
async def list_chats(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: TeamsService = Depends(_get_teams_service),
) -> PaginatedResponse[list[TeamsChatResponse]]:
    """
    List Teams chats

    Returns chats the user is a member of.
    """
    try:
        chats = await service.get_chats(limit=page * page_size)

        # Apply pagination
        total = len(chats)
        start = (page - 1) * page_size
        end = start + page_size
        page_chats = chats[start:end]

        return PaginatedResponse(
            success=True,
            data=[_convert_chat_to_response(c) for c in page_chats],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/chats/{chat_id}/messages", response_model=PaginatedResponse[list[TeamsMessageResponse]])
async def list_messages(
    chat_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    since: datetime | None = Query(None, description="Only messages since this time"),
    service: TeamsService = Depends(_get_teams_service),
) -> PaginatedResponse[list[TeamsMessageResponse]]:
    """
    List messages in a chat

    Returns messages from the specified chat.
    """
    try:
        messages = await service.get_messages(
            chat_id=chat_id,
            limit=page * page_size,
            since=since,
        )

        # Apply pagination
        total = len(messages)
        start = (page - 1) * page_size
        end = start + page_size
        page_messages = messages[start:end]

        return PaginatedResponse(
            success=True,
            data=[_convert_message_to_response(m) for m in page_messages],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/chats/{chat_id}/messages/{message_id}/reply", response_model=APIResponse[dict])
async def reply_to_message(
    chat_id: str,
    message_id: str,
    request: SendReplyRequest,
    service: TeamsService = Depends(_get_teams_service),
) -> APIResponse[dict]:
    """
    Reply to a message

    Sends a reply in the chat thread.
    """
    try:
        success = await service.send_reply(
            chat_id=chat_id,
            message_id=message_id,
            content=request.content,
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to send reply to message {message_id}",
            )

        return APIResponse(
            success=True,
            data={
                "chat_id": chat_id,
                "message_id": message_id,
                "replied": True,
            },
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/chats/{chat_id}/messages/{message_id}/flag", response_model=APIResponse[dict])
async def flag_message(
    chat_id: str,
    message_id: str,
    request: FlagMessageRequest = FlagMessageRequest(),
    service: TeamsService = Depends(_get_teams_service),
) -> APIResponse[dict]:
    """
    Flag/unflag a message

    Marks a message for follow-up or removes the flag.
    """
    try:
        success = await service.flag_message(
            chat_id=chat_id,
            message_id=message_id,
            flag=request.flag,
            reason=request.reason,
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to flag message {message_id}",
            )

        return APIResponse(
            success=True,
            data={
                "chat_id": chat_id,
                "message_id": message_id,
                "flagged": request.flag,
            },
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/chats/{chat_id}/read", response_model=APIResponse[dict])
async def mark_chat_as_read(
    chat_id: str,
    service: TeamsService = Depends(_get_teams_service),
) -> APIResponse[dict]:
    """
    Mark all messages in a chat as read

    Marks all messages in the specified chat as read for the current user.
    """
    try:
        success = await service.mark_chat_as_read(chat_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to mark chat {chat_id} as read",
            )

        return APIResponse(
            success=True,
            data={
                "chat_id": chat_id,
                "marked_as_read": True,
            },
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/poll", response_model=APIResponse[TeamsPollResponse])
async def poll_teams(
    service: TeamsService = Depends(_get_teams_service),
) -> APIResponse[TeamsPollResponse]:
    """
    Poll Teams for new messages

    Checks all chats for new messages and processes them.
    """
    try:
        result = await service.poll()

        return APIResponse(
            success=True,
            data=TeamsPollResponse(
                messages_fetched=result.get("messages_fetched", 0),
                messages_new=result.get("messages_new", 0),
                chats_checked=result.get("chats_checked", 0),
                polled_at=_parse_datetime(result.get("polled_at")) or datetime.now(timezone.utc),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats", response_model=APIResponse[TeamsStatsResponse])
async def get_teams_stats(
    service: TeamsService = Depends(_get_teams_service),
) -> APIResponse[TeamsStatsResponse]:
    """
    Get Teams statistics

    Returns message and chat statistics.
    """
    try:
        stats = await service.get_stats()

        return APIResponse(
            success=True,
            data=TeamsStatsResponse(
                total_chats=stats.get("total_chats", 0),
                unread_chats=stats.get("unread_chats", 0),
                messages_processed=stats.get("messages_processed", 0),
                messages_flagged=stats.get("messages_flagged", 0),
                last_poll=_parse_datetime(stats.get("last_poll")),
            ),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
