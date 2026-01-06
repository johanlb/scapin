"""
Tests for Calendar Conflict Detector

Tests conflict detection for overlaps and travel time issues.
"""

from datetime import datetime, timezone

from src.core.events import EventSource, EventType, PerceivedEvent, UrgencyLevel
from src.jeeves.api.models.calendar import ConflictSeverity, ConflictType
from src.jeeves.api.services.conflict_detector import ConflictDetector


def _make_calendar_event(
    event_id: str,
    title: str,
    start: datetime,
    end: datetime,
    location: str = "",
    is_online: bool = False,
    online_url: str | None = None,
) -> PerceivedEvent:
    """Helper to create a calendar PerceivedEvent for testing"""
    now = datetime.now(timezone.utc)
    metadata: dict = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "location": location,
        "is_online": is_online,
    }
    if online_url:
        metadata["online_url"] = online_url

    return PerceivedEvent(
        event_id=event_id,
        source=EventSource.CALENDAR,
        source_id=event_id,
        occurred_at=now,
        received_at=now,
        perceived_at=now,
        title=title,
        content="",
        event_type=EventType.INVITATION,
        urgency=UrgencyLevel.MEDIUM,
        entities=[],
        topics=[],
        keywords=[],
        from_person="organizer@example.com",
        to_people=[],
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        needs_clarification=False,
        clarification_questions=[],
        perception_confidence=0.9,
        metadata=metadata,
    )


class TestConflictDetector:
    """Tests for ConflictDetector"""

    def test_no_conflicts_no_overlap(self) -> None:
        """Events with no overlap return empty conflicts"""
        detector = ConflictDetector()

        event_a = _make_calendar_event(
            "a",
            "Meeting A",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
        )
        event_b = _make_calendar_event(
            "b",
            "Meeting B",
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 12, 0, tzinfo=timezone.utc),
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        assert conflicts == {}

    def test_overlap_full_detected(self) -> None:
        """Full overlap is detected with HIGH severity"""
        detector = ConflictDetector()

        # Meeting A fully contains Meeting B
        event_a = _make_calendar_event(
            "a",
            "Long Meeting",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 12, 0, tzinfo=timezone.utc),
        )
        event_b = _make_calendar_event(
            "b",
            "Short Meeting",
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        # Event A has conflict with B
        assert "a" in conflicts
        assert len(conflicts["a"]) == 1
        assert conflicts["a"][0].conflict_type == ConflictType.OVERLAP_FULL
        assert conflicts["a"][0].severity == ConflictSeverity.HIGH
        assert conflicts["a"][0].conflicting_event_id == "b"

        # Event B also has conflict with A (reverse)
        assert "b" in conflicts
        assert len(conflicts["b"]) == 1
        assert conflicts["b"][0].conflicting_event_id == "a"

    def test_overlap_partial_detected(self) -> None:
        """Partial overlap is detected with MEDIUM severity"""
        detector = ConflictDetector()

        event_a = _make_calendar_event(
            "a",
            "Meeting A",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 30, tzinfo=timezone.utc),
        )
        event_b = _make_calendar_event(
            "b",
            "Meeting B",
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        assert "a" in conflicts
        assert len(conflicts["a"]) == 1
        conflict = conflicts["a"][0]
        assert conflict.conflict_type == ConflictType.OVERLAP_PARTIAL
        assert conflict.severity == ConflictSeverity.MEDIUM
        assert conflict.overlap_minutes == 30

    def test_travel_time_conflict_detected(self) -> None:
        """Different locations with insufficient gap detected"""
        detector = ConflictDetector(min_travel_gap_minutes=30)

        event_a = _make_calendar_event(
            "a",
            "Office Meeting",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            location="Building A, Room 101",
        )
        event_b = _make_calendar_event(
            "b",
            "Client Meeting",
            datetime(2026, 1, 6, 10, 15, tzinfo=timezone.utc),  # Only 15 min gap
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
            location="Downtown Office",
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        assert "a" in conflicts
        assert len(conflicts["a"]) == 1
        conflict = conflicts["a"][0]
        assert conflict.conflict_type == ConflictType.TRAVEL_TIME
        assert conflict.severity == ConflictSeverity.LOW
        assert conflict.gap_minutes == 15

    def test_online_meetings_no_travel_conflict(self) -> None:
        """Online meetings don't trigger travel conflicts"""
        detector = ConflictDetector(min_travel_gap_minutes=30)

        event_a = _make_calendar_event(
            "a",
            "Office Meeting",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            location="Building A",
        )
        event_b = _make_calendar_event(
            "b",
            "Teams Call",
            datetime(2026, 1, 6, 10, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
            location="Teams",  # Contains "teams" keyword
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        # No travel time conflict because event B is online
        assert conflicts == {}

    def test_same_location_no_travel_conflict(self) -> None:
        """Same location doesn't trigger travel conflict"""
        detector = ConflictDetector(min_travel_gap_minutes=30)

        event_a = _make_calendar_event(
            "a",
            "Meeting A",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            location="Conference Room A",
        )
        event_b = _make_calendar_event(
            "b",
            "Meeting B",
            datetime(2026, 1, 6, 10, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
            location="Conference Room A",  # Same location
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        assert conflicts == {}

    def test_multiple_conflicts_for_same_event(self) -> None:
        """One event can have multiple conflicts"""
        detector = ConflictDetector()

        # Event A overlaps with both B and C
        event_a = _make_calendar_event(
            "a",
            "Long Meeting",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 12, 0, tzinfo=timezone.utc),
        )
        event_b = _make_calendar_event(
            "b",
            "Meeting B",
            datetime(2026, 1, 6, 9, 30, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
        )
        event_c = _make_calendar_event(
            "c",
            "Meeting C",
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 11, 30, tzinfo=timezone.utc),
        )

        conflicts = detector.detect_conflicts([event_a, event_b, event_c])

        # Event A should have 2 conflicts
        assert "a" in conflicts
        assert len(conflicts["a"]) == 2

    def test_empty_events_list(self) -> None:
        """Empty events list returns empty conflicts"""
        detector = ConflictDetector()

        conflicts = detector.detect_conflicts([])

        assert conflicts == {}

    def test_single_event_no_conflicts(self) -> None:
        """Single event cannot have conflicts"""
        detector = ConflictDetector()

        event_a = _make_calendar_event(
            "a",
            "Meeting A",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
        )

        conflicts = detector.detect_conflicts([event_a])

        assert conflicts == {}

    def test_non_calendar_events_ignored(self) -> None:
        """Non-calendar events are ignored"""
        detector = ConflictDetector()
        now = datetime.now(timezone.utc)

        calendar_event = _make_calendar_event(
            "a",
            "Meeting A",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
        )
        email_event = PerceivedEvent(
            event_id="email1",
            source=EventSource.EMAIL,
            source_id="email1",
            occurred_at=now,
            received_at=now,
            perceived_at=now,
            title="Important Email",
            content="",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.HIGH,
            entities=[],
            topics=[],
            keywords=[],
            from_person="sender@example.com",
            to_people=[],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            needs_clarification=False,
            clarification_questions=[],
            perception_confidence=0.9,
            metadata={},
        )

        conflicts = detector.detect_conflicts([calendar_event, email_event])

        # No conflicts (email is ignored, only 1 calendar event)
        assert conflicts == {}

    def test_sufficient_travel_gap_no_conflict(self) -> None:
        """Sufficient gap between different locations doesn't trigger conflict"""
        detector = ConflictDetector(min_travel_gap_minutes=30)

        event_a = _make_calendar_event(
            "a",
            "Office Meeting",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            location="Building A",
        )
        event_b = _make_calendar_event(
            "b",
            "Client Meeting",
            datetime(2026, 1, 6, 10, 45, tzinfo=timezone.utc),  # 45 min gap
            datetime(2026, 1, 6, 11, 30, tzinfo=timezone.utc),
            location="Building B",
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        assert conflicts == {}

    def test_online_meeting_url_detection(self) -> None:
        """Events with online_url metadata are detected as online"""
        detector = ConflictDetector(min_travel_gap_minutes=30)

        event_a = _make_calendar_event(
            "a",
            "Office Meeting",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            location="Building A",
        )
        # Event B has a different location but is online (has online_url)
        event_b = _make_calendar_event(
            "b",
            "Video Call",
            datetime(2026, 1, 6, 10, 10, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
            location="External Office",  # Different location
            online_url="https://teams.microsoft.com/meeting/123",  # But has online URL
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        # No travel conflict because B has online_url
        assert conflicts == {}

    def test_conflict_message_in_french(self) -> None:
        """Conflict messages are in French"""
        detector = ConflictDetector()

        event_a = _make_calendar_event(
            "a",
            "Réunion A",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 30, tzinfo=timezone.utc),
        )
        event_b = _make_calendar_event(
            "b",
            "Réunion B",
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
        )

        conflicts = detector.detect_conflicts([event_a, event_b])

        assert "a" in conflicts
        # Message should be in French
        assert "Chevauche" in conflicts["a"][0].message

    def test_events_sorted_by_start_time(self) -> None:
        """Events are processed in chronological order regardless of input order"""
        detector = ConflictDetector()

        # Input events in reverse order
        event_b = _make_calendar_event(
            "b",
            "Later Meeting",
            datetime(2026, 1, 6, 11, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 12, 0, tzinfo=timezone.utc),
        )
        event_a = _make_calendar_event(
            "a",
            "Earlier Meeting",
            datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc),
        )

        # Even with reversed input, conflict detection should work
        conflicts = detector.detect_conflicts([event_b, event_a])

        # No overlap = no conflicts
        assert conflicts == {}


class TestConflictModels:
    """Tests for conflict model types"""

    def test_conflict_type_values(self) -> None:
        """ConflictType enum has correct values"""
        assert ConflictType.OVERLAP_FULL.value == "overlap_full"
        assert ConflictType.OVERLAP_PARTIAL.value == "overlap_partial"
        assert ConflictType.TRAVEL_TIME.value == "travel_time"

    def test_conflict_severity_values(self) -> None:
        """ConflictSeverity enum has correct values"""
        assert ConflictSeverity.HIGH.value == "high"
        assert ConflictSeverity.MEDIUM.value == "medium"
        assert ConflictSeverity.LOW.value == "low"
