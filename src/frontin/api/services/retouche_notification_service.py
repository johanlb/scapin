"""
Retouche Notification Service

Manages notifications for retouche actions.
Handles rate limiting to prevent spam.

Features:
    - Creates notifications for important retouche actions
    - Aggregates auto-applied notifications
    - Respects daily limits per notification type
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.frontin.api.models.notifications import (
    NotificationCreate,
    NotificationPriority,
    NotificationType,
)
from src.frontin.api.services.notification_service import (
    NotificationService,
    get_notification_service,
)
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.services.retouche_notifications")

# Daily limits per notification type
NOTIFICATION_LIMITS = {
    NotificationType.RETOUCHE_AUTO: 0,  # Never send toast (panel only)
    NotificationType.RETOUCHE_PENDING: 3,  # Max 3 toasts/day
    NotificationType.RETOUCHE_IMPORTANT: 5,  # Max 5 toasts/day
    NotificationType.RETOUCHE_ERROR: 2,  # Max 2 toasts/day
}

# Default user for single-user mode
DEFAULT_USER_ID = "johan"


@dataclass
class RetoucheNotificationService:
    """
    Service for managing retouche-specific notifications

    Provides specialized methods for creating retouche notifications
    with rate limiting and aggregation.
    """

    notification_service: NotificationService = field(
        default_factory=get_notification_service
    )
    user_id: str = DEFAULT_USER_ID

    # Daily counters (reset at midnight)
    _daily_counts: dict[str, int] = field(default_factory=dict)
    _count_date: date | None = field(default=None, init=False)

    def _reset_counters_if_needed(self) -> None:
        """Reset daily counters at midnight"""
        today = date.today()
        if self._count_date != today:
            self._daily_counts = {}
            self._count_date = today

    def _can_send(self, notification_type: NotificationType) -> bool:
        """Check if we can send this notification type today"""
        self._reset_counters_if_needed()
        limit = NOTIFICATION_LIMITS.get(notification_type, 10)
        if limit == 0:
            return False
        current = self._daily_counts.get(notification_type.value, 0)
        return current < limit

    def _increment_counter(self, notification_type: NotificationType) -> None:
        """Increment daily counter for notification type"""
        self._reset_counters_if_needed()
        key = notification_type.value
        self._daily_counts[key] = self._daily_counts.get(key, 0) + 1

    async def notify_important_action(
        self,
        note_id: str,
        note_title: str,
        action_type: str,
        message: str,
        confidence: float,
    ) -> bool:
        """
        Create notification for important retouche action

        Args:
            note_id: Note identifier
            note_title: Note title
            action_type: Type of retouche action
            message: User-friendly message
            confidence: Action confidence score

        Returns:
            True if notification was created
        """
        if not self._can_send(NotificationType.RETOUCHE_IMPORTANT):
            logger.debug("Rate limit reached for RETOUCHE_IMPORTANT")
            return False

        notification = NotificationCreate(
            type=NotificationType.RETOUCHE_IMPORTANT,
            title=f"Retouche: {note_title}",
            message=message,
            priority=NotificationPriority.HIGH,
            link=f"/memoires?note={note_id}",
            metadata={
                "note_id": note_id,
                "action_type": action_type,
                "confidence": confidence,
            },
        )

        await self.notification_service.create(
            user_id=self.user_id,
            notification=notification,
            push_realtime=True,
        )

        self._increment_counter(NotificationType.RETOUCHE_IMPORTANT)
        logger.info(f"Created RETOUCHE_IMPORTANT notification for {note_title}")
        return True

    async def notify_pending_actions(
        self,
        note_id: str,
        note_title: str,
        action_count: int,
        avg_confidence: float,
    ) -> bool:
        """
        Create notification for pending retouche actions

        Args:
            note_id: Note identifier
            note_title: Note title
            action_count: Number of pending actions
            avg_confidence: Average confidence of actions

        Returns:
            True if notification was created
        """
        if not self._can_send(NotificationType.RETOUCHE_PENDING):
            logger.debug("Rate limit reached for RETOUCHE_PENDING")
            return False

        message = (
            f"{action_count} amélioration{'s' if action_count > 1 else ''} "
            f"proposée{'s' if action_count > 1 else ''} "
            f"(confiance: {avg_confidence:.0%})"
        )

        notification = NotificationCreate(
            type=NotificationType.RETOUCHE_PENDING,
            title=f"Retouche en attente: {note_title}",
            message=message,
            priority=NotificationPriority.NORMAL,
            link=f"/memoires?note={note_id}&action=retouche",
            metadata={
                "note_id": note_id,
                "action_count": action_count,
                "avg_confidence": avg_confidence,
            },
        )

        await self.notification_service.create(
            user_id=self.user_id,
            notification=notification,
            push_realtime=True,
        )

        self._increment_counter(NotificationType.RETOUCHE_PENDING)
        logger.info(f"Created RETOUCHE_PENDING notification for {note_title}")
        return True

    async def notify_auto_applied(
        self,
        notes: list[dict],
    ) -> bool:
        """
        Create aggregated notification for auto-applied retouches

        Auto-applied retouches are grouped into a single notification
        to avoid spam. Only shown in panel (no toast).

        Args:
            notes: List of dicts with note_id, note_title, action_count

        Returns:
            True if notification was created
        """
        if not notes:
            return False

        # Auto notifications go to panel only (no realtime push)
        count = len(notes)
        total_actions = sum(n.get("action_count", 1) for n in notes)

        if count == 1:
            message = f"[[{notes[0]['note_title']}]]: {total_actions} amélioration{'s' if total_actions > 1 else ''}"
        else:
            titles = [f"[[{n['note_title']}]]" for n in notes[:3]]
            if count > 3:
                titles.append(f"+{count - 3} autres")
            message = f"{total_actions} améliorations appliquées: {', '.join(titles)}"

        notification = NotificationCreate(
            type=NotificationType.RETOUCHE_AUTO,
            title=f"{count} note{'s' if count > 1 else ''} améliorée{'s' if count > 1 else ''}",
            message=message,
            priority=NotificationPriority.LOW,
            link="/memoires/retouche-queue",
            metadata={
                "note_ids": [n["note_id"] for n in notes],
                "total_actions": total_actions,
            },
        )

        await self.notification_service.create(
            user_id=self.user_id,
            notification=notification,
            push_realtime=False,  # Panel only, no toast
        )

        logger.info(f"Created RETOUCHE_AUTO notification for {count} notes")
        return True

    async def notify_error(
        self,
        note_id: str,
        note_title: str,
        error_type: str,
        error_message: str,
    ) -> bool:
        """
        Create notification for retouche error

        Args:
            note_id: Note identifier
            note_title: Note title
            error_type: Type of error
            error_message: Error description

        Returns:
            True if notification was created
        """
        if not self._can_send(NotificationType.RETOUCHE_ERROR):
            logger.debug("Rate limit reached for RETOUCHE_ERROR")
            return False

        notification = NotificationCreate(
            type=NotificationType.RETOUCHE_ERROR,
            title=f"Erreur retouche: {note_title}",
            message=error_message,
            priority=NotificationPriority.HIGH,
            link=f"/memoires?note={note_id}",
            metadata={
                "note_id": note_id,
                "error_type": error_type,
            },
        )

        await self.notification_service.create(
            user_id=self.user_id,
            notification=notification,
            push_realtime=True,
        )

        self._increment_counter(NotificationType.RETOUCHE_ERROR)
        logger.info(f"Created RETOUCHE_ERROR notification for {note_title}")
        return True

    async def notify_contact_suggestion(
        self,
        note_id: str,
        contact_name: str,
        days_since_contact: int,
    ) -> bool:
        """
        Create notification to suggest resuming contact

        Args:
            note_id: Note identifier
            contact_name: Contact name
            days_since_contact: Days since last contact

        Returns:
            True if notification was created
        """
        message = f"Dernier échange avec [[{contact_name}]] il y a {days_since_contact} jours"

        return await self.notify_important_action(
            note_id=note_id,
            note_title=contact_name,
            action_type="suggest_contact",
            message=message,
            confidence=0.85,
        )

    async def notify_stale_project(
        self,
        note_id: str,
        project_name: str,
        days_stale: int,
    ) -> bool:
        """
        Create notification for stale project

        Args:
            note_id: Note identifier
            project_name: Project name
            days_stale: Days since last activity

        Returns:
            True if notification was created
        """
        message = f"[[{project_name}]] sans activité depuis {days_stale} jours"

        return await self.notify_important_action(
            note_id=note_id,
            note_title=project_name,
            action_type="flag_stale",
            message=message,
            confidence=0.80,
        )

    async def notify_omnifocus_suggestion(
        self,
        note_id: str,
        note_title: str,
        task_description: str,
        confidence: float,
    ) -> bool:
        """
        Create notification for OmniFocus task suggestion

        Args:
            note_id: Note identifier
            note_title: Note title
            task_description: Suggested task
            confidence: Confidence score

        Returns:
            True if notification was created
        """
        message = f"Créer tâche : {task_description}"

        return await self.notify_important_action(
            note_id=note_id,
            note_title=note_title,
            action_type="create_omnifocus",
            message=message,
            confidence=confidence,
        )


# Global singleton
_retouche_notification_service: RetoucheNotificationService | None = None


def get_retouche_notification_service() -> RetoucheNotificationService:
    """Get global RetoucheNotificationService singleton"""
    global _retouche_notification_service
    if _retouche_notification_service is None:
        _retouche_notification_service = RetoucheNotificationService()
    return _retouche_notification_service


def reset_retouche_notification_service() -> None:
    """Reset global service (for testing)"""
    global _retouche_notification_service
    _retouche_notification_service = None
