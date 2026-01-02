"""
Event System for PKM Email Processor

Provides a pub/sub event bus for decoupling backend processing from frontend display.
Enables sequential display of parallel processing events.
"""

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from src.monitoring.logger import PKMLogger

logger = PKMLogger.get_logger(__name__)


class ProcessingEventType(str, Enum):
    """Types of processing lifecycle events (distinct from semantic EventType)"""
    # Processing-level events
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"

    # Account-level events
    ACCOUNT_STARTED = "account_started"
    ACCOUNT_COMPLETED = "account_completed"
    ACCOUNT_ERROR = "account_error"

    # Email-level events
    EMAIL_STARTED = "email_started"
    EMAIL_ANALYZING = "email_analyzing"
    EMAIL_COMPLETED = "email_completed"
    EMAIL_QUEUED = "email_queued"
    EMAIL_EXECUTED = "email_executed"
    EMAIL_ERROR = "email_error"

    # Batch events
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    BATCH_PROGRESS = "batch_progress"

    # System events
    SYSTEM_READY = "system_ready"
    SYSTEM_ERROR = "system_error"


@dataclass
class ProcessingEvent:
    """
    Event emitted during email processing

    This is the core data structure for communicating between the backend
    (EmailProcessor) and frontend (DisplayManager).
    """
    event_type: ProcessingEventType
    timestamp: datetime = field(default_factory=datetime.now)

    # Account context
    account_id: Optional[str] = None
    account_name: Optional[str] = None

    # Email context
    email_id: Optional[int] = None
    subject: Optional[str] = None
    from_address: Optional[str] = None
    email_date: Optional[datetime] = None  # Email sent date
    preview: Optional[str] = None  # 80 chars max

    # Analysis results
    action: Optional[str] = None
    confidence: Optional[int] = None
    category: Optional[str] = None
    reasoning: Optional[str] = None

    # Progress tracking
    current: Optional[int] = None
    total: Optional[int] = None

    # Error context
    error: Optional[str] = None
    error_type: Optional[str] = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation for logging"""
        parts = [f"[{self.event_type.value}]"]

        if self.account_id:
            parts.append(f"account={self.account_id}")

        if self.email_id:
            parts.append(f"email={self.email_id}")

        if self.current and self.total:
            parts.append(f"{self.current}/{self.total}")

        if self.action:
            parts.append(f"action={self.action}")

        if self.error:
            parts.append(f"error={self.error}")

        return " ".join(parts)


class EventBus:
    """
    Thread-safe publish/subscribe event bus

    Allows backend components (EmailProcessor) to emit events and frontend
    components (DisplayManager) to subscribe to them.

    Thread-Safety:
        - Uses threading.Lock for subscriber management
        - Safe for concurrent event emission and subscription

    Example:
        # Subscribe to events
        bus = EventBus()
        bus.subscribe(EventType.EMAIL_COMPLETED, my_handler)

        # Emit events
        bus.emit(ProcessingEvent(
            event_type=EventType.EMAIL_COMPLETED,
            email_id=123,
            subject="Test"
        ))
    """

    def __init__(self):
        """Initialize event bus"""
        self._subscribers: dict[ProcessingEventType, list[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._event_count = 0
        self._max_events = 10000  # Prevent memory leaks

        logger.debug("EventBus initialized")

    def subscribe(self, event_type: ProcessingEventType, callback: Callable[[ProcessingEvent], None]) -> None:
        """
        Subscribe to events of a specific type

        Args:
            event_type: Type of events to subscribe to
            callback: Function to call when event is emitted
                     Signature: callback(event: ProcessingEvent) -> None

        Thread-Safe: Yes
        """
        with self._lock:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type.value}: {callback.__name__}")

    def unsubscribe(self, event_type: ProcessingEventType, callback: Callable[[ProcessingEvent], None]) -> None:
        """
        Unsubscribe from events

        Args:
            event_type: Type of events to unsubscribe from
            callback: Callback to remove

        Thread-Safe: Yes
        """
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.value}: {callback.__name__}")

    def emit(self, event: ProcessingEvent) -> None:
        """
        Emit an event to all subscribers

        Args:
            event: Event to emit

        Thread-Safe: Yes

        Note:
            - Callbacks are executed in the emitting thread
            - Callbacks should be fast to avoid blocking
            - Exceptions in callbacks are caught and logged
        """
        # Get subscribers (thread-safe copy)
        with self._lock:
            subscribers = self._subscribers[event.event_type].copy()
            self._event_count += 1

            # Warn if too many events
            if self._event_count >= self._max_events:
                logger.warning(
                    f"EventBus has emitted {self._event_count} events. "
                    "Consider clearing or restarting."
                )

        # Execute callbacks (outside lock to avoid blocking)
        logger.debug(f"Emitting event: {event}")

        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"Error in event callback {callback.__name__}: {e}",
                    exc_info=True
                )

    def clear(self) -> None:
        """
        Clear all subscribers and reset event count

        Useful for testing and cleanup.

        Thread-Safe: Yes
        """
        with self._lock:
            self._subscribers.clear()
            self._event_count = 0
            logger.debug("EventBus cleared")

    def get_subscriber_count(self, event_type: Optional[ProcessingEventType] = None) -> int:
        """
        Get number of subscribers

        Args:
            event_type: Specific event type, or None for total

        Returns:
            Number of subscribers

        Thread-Safe: Yes
        """
        with self._lock:
            if event_type:
                return len(self._subscribers[event_type])
            else:
                return sum(len(subs) for subs in self._subscribers.values())

    def get_event_count(self) -> int:
        """
        Get total number of events emitted

        Returns:
            Event count

        Thread-Safe: Yes
        """
        with self._lock:
            return self._event_count


# Global event bus singleton
_event_bus: Optional[EventBus] = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """
    Get global event bus singleton

    Thread-Safe: Yes (double-check locking)

    Returns:
        Global EventBus instance
    """
    global _event_bus

    if _event_bus is None:
        with _event_bus_lock:
            if _event_bus is None:
                _event_bus = EventBus()
                logger.debug("Global EventBus created")

    return _event_bus


def reset_event_bus() -> None:
    """
    Reset global event bus (for testing)

    Thread-Safe: Yes
    """
    global _event_bus

    with _event_bus_lock:
        if _event_bus is not None:
            _event_bus.clear()
        _event_bus = None
        logger.debug("Global EventBus reset")
