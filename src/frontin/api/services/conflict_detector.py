"""
Calendar Conflict Detector

Detects conflicts between calendar events:
- Full overlap (one event contains another)
- Partial overlap (events overlap partially)
- Travel time conflicts (different locations with insufficient gap)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.core.events import EventSource, PerceivedEvent
from src.frontin.api.models.calendar import (
    CalendarConflict,
    ConflictSeverity,
    ConflictType,
)
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.services.conflict_detector")

# Keywords indicating online meetings (case-insensitive)
ONLINE_KEYWORDS = frozenset([
    "teams", "zoom", "meet", "webex", "skype", "online", "virtual",
    "remote", "video", "call", "conference call", "teams meeting",
    "google meet", "zoom meeting",
])


@dataclass
class ConflictDetector:
    """
    Detects calendar conflicts between events

    Supports three types of conflicts:
    - OVERLAP_FULL: One event fully contains another
    - OVERLAP_PARTIAL: Events partially overlap
    - TRAVEL_TIME: Insufficient time between events at different locations
    """

    min_travel_gap_minutes: int = field(default=30)

    def detect_conflicts(
        self,
        events: list[PerceivedEvent],
        days_ahead: int = 7,
    ) -> dict[str, list[CalendarConflict]]:
        """
        Detect all conflicts between calendar events

        Args:
            events: List of PerceivedEvents (filters to calendar only)
            days_ahead: Number of days ahead to check (default: 7)

        Returns:
            Dict mapping event_id to list of conflicts for that event
        """
        # Filter to calendar events only
        calendar_events = [
            e for e in events
            if e.source == EventSource.CALENDAR
        ]

        if len(calendar_events) < 2:
            return {}

        # Parse and sort events by start time
        parsed = self._parse_events(calendar_events)
        parsed.sort(key=lambda x: x[1])  # Sort by start datetime

        conflicts: dict[str, list[CalendarConflict]] = {}

        # Compare each pair of events
        for i, (event_a, start_a, end_a, loc_a, is_online_a) in enumerate(parsed):
            event_conflicts: list[CalendarConflict] = []

            for event_b, start_b, end_b, loc_b, is_online_b in parsed[i + 1:]:
                # Skip if event_b starts too far in the future
                # (events are sorted, so we can break)
                if (start_b - start_a).days > days_ahead:
                    break

                # Check for overlap
                overlap_conflict = self._check_overlap(
                    event_a, start_a, end_a,
                    event_b, start_b, end_b,
                )
                if overlap_conflict:
                    event_conflicts.append(overlap_conflict)
                    # Also add reverse conflict to event_b
                    reverse = self._make_reverse_conflict(
                        overlap_conflict, event_a, start_a, end_a
                    )
                    if event_b.event_id not in conflicts:
                        conflicts[event_b.event_id] = []
                    conflicts[event_b.event_id].append(reverse)

                # Check for travel time conflicts (only if no overlap)
                if not overlap_conflict:
                    travel_conflict = self._check_travel_time(
                        event_a, start_a, end_a, loc_a, is_online_a,
                        event_b, start_b, end_b, loc_b, is_online_b,
                    )
                    if travel_conflict:
                        event_conflicts.append(travel_conflict)

            if event_conflicts:
                if event_a.event_id not in conflicts:
                    conflicts[event_a.event_id] = []
                conflicts[event_a.event_id].extend(event_conflicts)

        logger.info(
            f"Conflict detection: {len(calendar_events)} events, "
            f"{sum(len(c) for c in conflicts.values())} conflicts found"
        )

        return conflicts

    def _parse_events(
        self,
        events: list[PerceivedEvent],
    ) -> list[tuple[PerceivedEvent, datetime, datetime, str, bool]]:
        """
        Parse events into tuples with start/end times and location info

        Returns list of (event, start_dt, end_dt, location, is_online)
        """
        parsed: list[tuple[PerceivedEvent, datetime, datetime, str, bool]] = []

        for event in events:
            start_str = event.metadata.get("start")
            end_str = event.metadata.get("end")

            if not start_str or not end_str:
                continue

            try:
                start_dt = datetime.fromisoformat(start_str)
                end_dt = datetime.fromisoformat(end_str)

                # Ensure timezone aware
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)

                # Get location
                location = event.metadata.get("location", "") or ""

                # Determine if online
                is_online = self._is_online_meeting(event, location)

                parsed.append((event, start_dt, end_dt, location, is_online))
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse event {event.event_id}: {e}")

        return parsed

    def _is_online_meeting(self, event: PerceivedEvent, location: str) -> bool:
        """Check if an event is an online meeting"""
        # Check explicit flag
        if event.metadata.get("is_online"):
            return True

        # Check for online meeting URL
        if event.metadata.get("online_url"):
            return True

        # Check location for online keywords
        location_lower = location.lower()
        return any(keyword in location_lower for keyword in ONLINE_KEYWORDS)

    def _check_overlap(
        self,
        _event_a: PerceivedEvent,
        start_a: datetime,
        end_a: datetime,
        event_b: PerceivedEvent,
        start_b: datetime,
        end_b: datetime,
    ) -> CalendarConflict | None:
        """
        Check if two events overlap

        Returns CalendarConflict if overlap detected, None otherwise
        """
        # No overlap if one ends before the other starts
        if end_a <= start_b or end_b <= start_a:
            return None

        # Calculate overlap
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)
        overlap_minutes = int((overlap_end - overlap_start).total_seconds() / 60)

        if overlap_minutes <= 0:
            return None

        # Determine conflict type
        if start_a <= start_b and end_a >= end_b:
            # A fully contains B
            conflict_type = ConflictType.OVERLAP_FULL
            severity = ConflictSeverity.HIGH
            message = f"Chevauche entièrement '{event_b.title}'"
        elif start_b <= start_a and end_b >= end_a:
            # B fully contains A
            conflict_type = ConflictType.OVERLAP_FULL
            severity = ConflictSeverity.HIGH
            message = f"Chevauche entièrement '{event_b.title}'"
        else:
            # Partial overlap
            conflict_type = ConflictType.OVERLAP_PARTIAL
            severity = ConflictSeverity.MEDIUM
            message = f"Chevauche '{event_b.title}' de {overlap_minutes} min"

        return CalendarConflict(
            conflict_type=conflict_type,
            severity=severity,
            conflicting_event_id=event_b.event_id,
            conflicting_title=event_b.title,
            conflicting_start=start_b,
            conflicting_end=end_b,
            overlap_minutes=overlap_minutes,
            gap_minutes=0,
            message=message,
        )

    def _check_travel_time(
        self,
        event_a: PerceivedEvent,
        _start_a: datetime,
        end_a: datetime,
        loc_a: str,
        is_online_a: bool,
        event_b: PerceivedEvent,
        start_b: datetime,
        end_b: datetime,
        loc_b: str,
        is_online_b: bool,
    ) -> CalendarConflict | None:
        """
        Check if there's insufficient travel time between two events

        Returns CalendarConflict if travel time is insufficient, None otherwise
        """
        # No travel time issue if either event is online
        if is_online_a or is_online_b:
            return None

        # No issue if same location or either location is empty
        if not loc_a or not loc_b:
            return None

        # Normalize locations for comparison
        loc_a_norm = loc_a.strip().lower()
        loc_b_norm = loc_b.strip().lower()

        if loc_a_norm == loc_b_norm:
            return None

        # Calculate gap between events
        # event_b starts after event_a (events are sorted)
        gap_minutes = int((start_b - end_a).total_seconds() / 60)

        # If gap is negative, there's an overlap (handled separately)
        if gap_minutes < 0:
            return None

        # Check if gap is sufficient
        if gap_minutes >= self.min_travel_gap_minutes:
            return None

        return CalendarConflict(
            conflict_type=ConflictType.TRAVEL_TIME,
            severity=ConflictSeverity.LOW,
            conflicting_event_id=event_b.event_id,
            conflicting_title=event_b.title,
            conflicting_start=start_b,
            conflicting_end=end_b,
            overlap_minutes=0,
            gap_minutes=gap_minutes,
            message=f"Seulement {gap_minutes} min entre '{event_a.title}' et '{event_b.title}' (lieux différents)",
        )

    def _make_reverse_conflict(
        self,
        conflict: CalendarConflict,
        event_a: PerceivedEvent,
        start_a: datetime,
        end_a: datetime,
    ) -> CalendarConflict:
        """Create a reverse conflict (from B's perspective about A)"""
        if conflict.conflict_type == ConflictType.OVERLAP_FULL:
            message = f"Chevauche entièrement '{event_a.title}'"
        else:
            message = f"Chevauche '{event_a.title}' de {conflict.overlap_minutes} min"

        return CalendarConflict(
            conflict_type=conflict.conflict_type,
            severity=conflict.severity,
            conflicting_event_id=event_a.event_id,
            conflicting_title=event_a.title,
            conflicting_start=start_a,
            conflicting_end=end_a,
            overlap_minutes=conflict.overlap_minutes,
            gap_minutes=0,
            message=message,
        )
