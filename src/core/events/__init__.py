"""
Events Module

Universal event model for the cognitive architecture.
All inputs (emails, files, questions, etc.) are normalized into PerceivedEvent.

Also re-exports processing event classes for backward compatibility.
"""

from src.core.events.universal_event import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
    Entity,
)

from src.core.processing_events import (
    ProcessingEventType,
    ProcessingEvent,
    EventBus,
    get_event_bus,
    reset_event_bus,
)

__all__ = [
    # Universal events (semantic)
    "PerceivedEvent",
    "EventSource",
    "EventType",
    "UrgencyLevel",
    "Entity",
    # Processing events (lifecycle)
    "ProcessingEventType",
    "ProcessingEvent",
    "EventBus",
    "get_event_bus",
    "reset_event_bus",
]
