"""
Notifications Router

REST API endpoints for notification management.
Supports CRUD operations with pagination and filtering.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.jeeves.api.deps import get_current_user
from src.jeeves.api.models.notifications import (
    MarkReadRequest,
    MarkReadResponse,
    NotificationCreate,
    NotificationFilter,
    NotificationListResponse,
    NotificationPriority,
    NotificationResponse,
    NotificationStats,
    NotificationType,
)
from src.jeeves.api.models.responses import APIResponse
from src.jeeves.api.services.notification_service import (
    NotificationService,
    get_notification_service,
)

router = APIRouter()


def get_service() -> NotificationService:
    """Dependency to get notification service"""
    return get_notification_service()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    types: Optional[list[NotificationType]] = Query(
        None, description="Filter by notification types"
    ),
    priorities: Optional[list[NotificationPriority]] = Query(
        None, description="Filter by priorities"
    ),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    since: Optional[datetime] = Query(None, description="Filter by created_at >= since"),
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> NotificationListResponse:
    """
    List notifications for the current user

    Supports filtering by type, priority, read status, and date.
    Results are paginated and sorted by creation date (newest first).
    """
    filters = NotificationFilter(
        types=types,
        priorities=priorities,
        is_read=is_read,
        since=since,
    )

    return await service.list(
        user_id=user,
        page=page,
        page_size=page_size,
        filters=filters if any([types, priorities, is_read is not None, since]) else None,
    )


@router.get("/unread", response_model=NotificationListResponse)
async def list_unread_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> NotificationListResponse:
    """
    List unread notifications only

    Convenience endpoint for fetching only unread notifications.
    """
    filters = NotificationFilter(is_read=False)
    return await service.list(user_id=user, page=page, page_size=page_size, filters=filters)


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> NotificationStats:
    """
    Get notification statistics

    Returns counts by type, priority, and read status.
    """
    return await service.get_stats(user_id=user)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> NotificationResponse:
    """
    Get a specific notification

    Returns 404 if notification not found or not owned by user.
    """
    notification = await service.get(notification_id, user_id=user)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.post("", response_model=NotificationResponse, status_code=201)
async def create_notification(
    notification: NotificationCreate,
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> NotificationResponse:
    """
    Create a new notification

    Notifications are automatically pushed via WebSocket if client is connected.
    Notifications expire after 7 days by default.
    """
    return await service.create(user_id=user, notification=notification)


@router.post("/read", response_model=MarkReadResponse)
async def mark_notifications_read(
    request: MarkReadRequest,
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> MarkReadResponse:
    """
    Mark notifications as read

    Can mark specific notifications by ID or all notifications at once.
    """
    return await service.mark_read(
        user_id=user,
        notification_ids=request.notification_ids,
        mark_all=request.mark_all,
    )


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_single_notification_read(
    notification_id: str,
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> MarkReadResponse:
    """
    Mark a single notification as read

    Convenience endpoint for marking one notification as read.
    """
    return await service.mark_read(user_id=user, notification_ids=[notification_id])


@router.delete("/{notification_id}", response_model=APIResponse)
async def delete_notification(
    notification_id: str,
    user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> APIResponse:
    """
    Delete a notification

    Permanently removes the notification.
    """
    deleted = await service.delete(notification_id, user_id=user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")

    return APIResponse(
        success=True,
        message="Notification deleted",
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/cleanup", response_model=APIResponse)
async def cleanup_expired_notifications(
    _user: str = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
) -> APIResponse:
    """
    Clean up expired notifications

    Removes notifications older than the retention period (7 days).
    This is also done automatically on a schedule.
    """
    deleted_count = await service.cleanup_expired()
    return APIResponse(
        success=True,
        message=f"Cleaned up {deleted_count} expired notifications",
        timestamp=datetime.now(timezone.utc),
    )
