"""
Pytest fixtures for Sganarelle unit tests
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from src.core.events.universal_event import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
    Entity,
    now_utc
)
from src.core.memory.working_memory import WorkingMemory


@pytest.fixture
def simple_event():
    """Create a minimal PerceivedEvent for testing"""
    return PerceivedEvent(
        # Identity
        event_id="test_event_001",
        source=EventSource.EMAIL,
        source_id="test@example.com_12345",

        # Timing
        occurred_at=now_utc(),
        received_at=now_utc(),

        # Core Content
        title="Test Event",
        content="This is a test event for unit testing.",

        # Classification
        event_type=EventType.INFORMATION,
        urgency=UrgencyLevel.MEDIUM,

        # Extracted Information
        entities=[],
        topics=["testing"],
        keywords=["test", "unit"],

        # Participants
        from_person="tester@example.com",
        to_people=["recipient@example.com"],
        cc_people=[],

        # Context Links
        thread_id=None,
        references=[],
        in_reply_to=None,

        # Attachments
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],

        # Source-Specific Data
        metadata={},

        # Quality Metrics
        perception_confidence=0.9,
        needs_clarification=False,
        clarification_questions=[]
    )


@pytest.fixture
def simple_working_memory(simple_event):
    """Create a WorkingMemory with a simple event"""
    return WorkingMemory(simple_event)


@pytest.fixture
def tmp_storage_dir():
    """Create a temporary storage directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
