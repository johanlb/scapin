"""
Queue WebSocket Events (v2.4)

Utility module for emitting queue events to WebSocket subscribers.
Bridges queue operations to the QUEUE channel.

Events:
    - item_added: New item added to queue
    - item_updated: Item state/resolution changed
    - item_removed: Item removed from queue
    - stats_updated: Queue statistics changed

AutoFetch Events (SC-20):
    - fetch_started: Background fetch started for a source
    - fetch_completed: Background fetch completed with item count

Memory Cycles v2 Events:
    - retouche_done: AI improvement cycle completed
    - filage_ready: Morning briefing prepared
    - lecture_completed: Human review completed
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from src.frontin.api.websocket.channels import ChannelManager, ChannelType, get_channel_manager
from src.monitoring.logger import get_logger

logger = get_logger("api.websocket.queue_events")


class QueueEventEmitter:
    """
    Emits queue events to WebSocket subscribers.

    Usage:
        emitter = get_queue_event_emitter()
        await emitter.emit_item_added(item)
        await emitter.emit_item_updated(item, changes=["status", "resolution"])
        await emitter.emit_item_removed(item_id)
        await emitter.emit_stats_updated(stats)
    """

    def __init__(self, channel_manager: Optional[ChannelManager] = None):
        """
        Initialize the queue event emitter.

        Args:
            channel_manager: Optional ChannelManager instance (uses singleton if None)
        """
        self._manager = channel_manager

    @property
    def manager(self) -> ChannelManager:
        """Get the channel manager (lazy initialization)."""
        if self._manager is None:
            self._manager = get_channel_manager()
        return self._manager

    async def emit_item_added(self, item: dict[str, Any]) -> int:
        """
        Emit event when a new item is added to the queue.

        Args:
            item: The queue item that was added

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "item_added",
            "item": _sanitize_item(item),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted item_added event to {sent_count} clients",
            extra={"item_id": item.get("id")},
        )

        return sent_count

    async def emit_item_updated(
        self,
        item: dict[str, Any],
        changes: Optional[list[str]] = None,
        previous_state: Optional[str] = None,
    ) -> int:
        """
        Emit event when a queue item is updated.

        Args:
            item: The updated queue item
            changes: List of fields that changed (e.g., ["status", "resolution"])
            previous_state: Previous state value for transition tracking

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "item_updated",
            "item": _sanitize_item(item),
            "changes": changes or [],
            "previous_state": previous_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted item_updated event to {sent_count} clients",
            extra={"item_id": item.get("id"), "changes": changes},
        )

        return sent_count

    async def emit_item_removed(self, item_id: str, reason: Optional[str] = None) -> int:
        """
        Emit event when a queue item is removed.

        Args:
            item_id: ID of the removed item
            reason: Optional reason for removal

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "item_removed",
            "item_id": item_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted item_removed event to {sent_count} clients",
            extra={"item_id": item_id},
        )

        return sent_count

    async def emit_stats_updated(self, stats: dict[str, Any]) -> int:
        """
        Emit event when queue statistics change.

        Args:
            stats: The updated queue statistics

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "stats_updated",
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted stats_updated event to {sent_count} clients",
            extra={"total": stats.get("total")},
        )

        return sent_count

    # === AutoFetch Events (SC-20) ===

    async def emit_fetch_started(self, source: str) -> int:
        """
        Emit event when background fetch starts for a source.

        Args:
            source: Source being fetched (email, teams, calendar)

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "fetch_started",
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted fetch_started event to {sent_count} clients",
            extra={"source": source},
        )

        return sent_count

    async def emit_fetch_completed(self, source: str, count: int) -> int:
        """
        Emit event when background fetch completes for a source.

        Args:
            source: Source that was fetched (email, teams, calendar)
            count: Number of items fetched

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "fetch_completed",
            "source": source,
            "count": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted fetch_completed event to {sent_count} clients",
            extra={"source": source, "count": count},
        )

        return sent_count

    # === Memory Cycles v2 Events ===

    async def emit_retouche_done(
        self,
        note_id: str,
        note_title: str,
        quality_before: Optional[int],
        quality_after: int,
        actions: list[str],
        questions_added: int = 0,
    ) -> int:
        """
        Emit event when a Retouche (AI improvement) completes.

        Args:
            note_id: ID of the note that was retouched
            note_title: Title of the note
            quality_before: Quality score before Retouche (0-100)
            quality_after: Quality score after Retouche (0-100)
            actions: List of action types performed
            questions_added: Number of questions added for Johan

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "retouche_done",
            "note_id": note_id,
            "note_title": note_title,
            "quality_before": quality_before,
            "quality_after": quality_after,
            "actions": actions,
            "questions_added": questions_added,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted retouche_done event to {sent_count} clients",
            extra={"note_id": note_id, "quality_delta": quality_after - (quality_before or 0)},
        )

        return sent_count

    async def emit_filage_ready(
        self,
        date: str,
        total_lectures: int,
        events_today: int,
        notes_with_questions: int,
    ) -> int:
        """
        Emit event when the daily Filage (morning briefing) is ready.

        Args:
            date: Date of the Filage (YYYY-MM-DD)
            total_lectures: Number of lectures in the Filage
            events_today: Number of calendar events today
            notes_with_questions: Number of notes with pending questions

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "filage_ready",
            "date": date,
            "total_lectures": total_lectures,
            "events_today": events_today,
            "notes_with_questions": notes_with_questions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted filage_ready event to {sent_count} clients",
            extra={"date": date, "total_lectures": total_lectures},
        )

        return sent_count

    async def emit_lecture_completed(
        self,
        note_id: str,
        note_title: str,
        quality: int,
        next_lecture: str,
        answers_recorded: int = 0,
    ) -> int:
        """
        Emit event when a Lecture (human review) completes.

        Args:
            note_id: ID of the note that was reviewed
            note_title: Title of the note
            quality: Quality rating given (0-5)
            next_lecture: ISO timestamp of next scheduled lecture
            answers_recorded: Number of questions answered

        Returns:
            Number of clients that received the event
        """
        message = {
            "type": "lecture_completed",
            "note_id": note_id,
            "note_title": note_title,
            "quality": quality,
            "next_lecture": next_lecture,
            "answers_recorded": answers_recorded,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = await self.manager.broadcast_to_channel(ChannelType.QUEUE, message)

        logger.debug(
            f"Emitted lecture_completed event to {sent_count} clients",
            extra={"note_id": note_id, "quality": quality},
        )

        return sent_count

    def emit_item_added_sync(self, item: dict[str, Any]) -> None:
        """
        Synchronous wrapper for emit_item_added.

        Schedules the async emit in the event loop.
        Use when called from sync code.
        """
        _schedule_async(self.emit_item_added(item))

    def emit_item_updated_sync(
        self,
        item: dict[str, Any],
        changes: Optional[list[str]] = None,
        previous_state: Optional[str] = None,
    ) -> None:
        """
        Synchronous wrapper for emit_item_updated.

        Schedules the async emit in the event loop.
        Use when called from sync code.
        """
        _schedule_async(self.emit_item_updated(item, changes, previous_state))

    def emit_item_removed_sync(self, item_id: str, reason: Optional[str] = None) -> None:
        """
        Synchronous wrapper for emit_item_removed.

        Schedules the async emit in the event loop.
        Use when called from sync code.
        """
        _schedule_async(self.emit_item_removed(item_id, reason))

    def emit_stats_updated_sync(self, stats: dict[str, Any]) -> None:
        """
        Synchronous wrapper for emit_stats_updated.

        Schedules the async emit in the event loop.
        Use when called from sync code.
        """
        _schedule_async(self.emit_stats_updated(stats))

    def emit_retouche_done_sync(
        self,
        note_id: str,
        note_title: str,
        quality_before: Optional[int],
        quality_after: int,
        actions: list[str],
        questions_added: int = 0,
    ) -> None:
        """Synchronous wrapper for emit_retouche_done."""
        _schedule_async(
            self.emit_retouche_done(
                note_id, note_title, quality_before, quality_after, actions, questions_added
            )
        )

    def emit_filage_ready_sync(
        self,
        date: str,
        total_lectures: int,
        events_today: int,
        notes_with_questions: int,
    ) -> None:
        """Synchronous wrapper for emit_filage_ready."""
        _schedule_async(
            self.emit_filage_ready(date, total_lectures, events_today, notes_with_questions)
        )

    def emit_lecture_completed_sync(
        self,
        note_id: str,
        note_title: str,
        quality: int,
        next_lecture: str,
        answers_recorded: int = 0,
    ) -> None:
        """Synchronous wrapper for emit_lecture_completed."""
        _schedule_async(
            self.emit_lecture_completed(note_id, note_title, quality, next_lecture, answers_recorded)
        )

    def emit_fetch_started_sync(self, source: str) -> None:
        """Synchronous wrapper for emit_fetch_started."""
        _schedule_async(self.emit_fetch_started(source))

    def emit_fetch_completed_sync(self, source: str, count: int) -> None:
        """Synchronous wrapper for emit_fetch_completed."""
        _schedule_async(self.emit_fetch_completed(source, count))


def _sanitize_item(item: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize a queue item for WebSocket transmission.

    Removes potentially large fields that aren't needed for UI updates.

    Args:
        item: Raw queue item

    Returns:
        Sanitized item suitable for WebSocket
    """
    # Create a shallow copy to avoid modifying the original
    sanitized = {
        "id": item.get("id"),
        "account_id": item.get("account_id"),
        "state": item.get("state"),
        "status": item.get("status"),  # Legacy
        "resolution": item.get("resolution"),
        "snooze": item.get("snooze"),
        "error": item.get("error"),
        "timestamps": item.get("timestamps"),
        "queued_at": item.get("queued_at"),
        "reviewed_at": item.get("reviewed_at"),
        # Include minimal metadata for UI display
        "metadata": {
            "subject": item.get("metadata", {}).get("subject"),
            "from_address": item.get("metadata", {}).get("from_address"),
            "from_name": item.get("metadata", {}).get("from_name"),
            "date": item.get("metadata", {}).get("date"),
            "has_attachments": item.get("metadata", {}).get("has_attachments"),
        },
        # Include minimal analysis for UI display (may be None for "analyzing" state)
        "analysis": {
            "action": (item.get("analysis") or {}).get("action"),
            "confidence": (item.get("analysis") or {}).get("confidence"),
            "summary": (item.get("analysis") or {}).get("summary"),
        },
    }

    return sanitized


def _schedule_async(coro: Any) -> None:
    """
    Schedule an async coroutine to run in the event loop.

    Used by sync wrappers to emit events from sync code.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running event loop - log and skip
        logger.debug("No event loop available for queue event emission")


# Singleton instance
_emitter: Optional[QueueEventEmitter] = None


def get_queue_event_emitter() -> QueueEventEmitter:
    """Get the singleton QueueEventEmitter instance."""
    global _emitter
    if _emitter is None:
        _emitter = QueueEventEmitter()
    return _emitter


def reset_queue_event_emitter() -> None:
    """Reset the singleton emitter (for testing)."""
    global _emitter
    _emitter = None
