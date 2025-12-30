"""
Events Module

Universal event model for the cognitive architecture.
All inputs (emails, files, questions, etc.) are normalized into PerceivedEvent.
"""

from src.core.events.universal_event import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
    Entity,
)

__all__ = [
    "PerceivedEvent",
    "EventSource",
    "EventType",
    "UrgencyLevel",
    "Entity",
]
