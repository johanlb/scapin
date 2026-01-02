"""
Continuity Detector

Determines if events are part of a continuous conversation/thread.

When events are continuous, Working Memory should preserve context
from previous events in the thread. When they're independent, Working
Memory should start fresh.

Design Philosophy:
- Auto-detect continuity (hybrid approach)
- Use explicit signals (thread_id, in_reply_to) when available
- Fall back to heuristics (time proximity, participant overlap, topic similarity)
- Conservative: When in doubt, treat as independent
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from src.core.events import PerceivedEvent


@dataclass
class ContinuityScore:
    """
    Score indicating how likely two events are part of same conversation

    Multiple signals are combined to produce overall continuity score.
    """
    overall_score: float  # 0.0-1.0
    is_continuous: bool  # True if score >= threshold

    # Individual signals
    explicit_thread_match: bool = False  # Same thread_id
    is_reply: bool = False  # in_reply_to points to previous event
    time_proximity_score: float = 0.0  # How close in time (0.0-1.0)
    participant_overlap_score: float = 0.0  # Shared participants (0.0-1.0)
    topic_similarity_score: float = 0.0  # Similar topics (0.0-1.0)
    entity_overlap_score: float = 0.0  # Shared entities (0.0-1.0)

    def __str__(self) -> str:
        return (
            f"ContinuityScore(overall={self.overall_score:.2f}, "
            f"continuous={self.is_continuous}, "
            f"thread={self.explicit_thread_match}, "
            f"reply={self.is_reply})"
        )


class ContinuityDetector:
    """
    Detects if events are part of continuous conversation

    Uses multiple signals:
    1. Explicit: thread_id, in_reply_to (strongest signals)
    2. Temporal: Time between events
    3. Participants: Shared people
    4. Content: Topic/entity overlap
    """

    # Default Thresholds
    DEFAULT_CONTINUITY_THRESHOLD = 0.6  # Overall score needed for continuity
    DEFAULT_MAX_TIME_GAP_HOURS = 24  # Max time between continuous events
    DEFAULT_QUICK_REPLY_HOURS = 2  # Quick replies get higher score

    # Default Weights for implicit signals
    DEFAULT_WEIGHTS = {
        'time_proximity': 0.4,
        'participant_overlap': 0.3,
        'topic_similarity': 0.2,
        'entity_overlap': 0.1,
    }

    def __init__(
        self,
        continuity_threshold: float = DEFAULT_CONTINUITY_THRESHOLD,
        max_time_gap_hours: float = DEFAULT_MAX_TIME_GAP_HOURS,
        quick_reply_hours: float = DEFAULT_QUICK_REPLY_HOURS,
        weights: Optional[dict[str, float]] = None
    ):
        """
        Initialize continuity detector

        Args:
            continuity_threshold: Overall score threshold for continuity (0.0-1.0)
            max_time_gap_hours: Maximum time gap for continuous events
            quick_reply_hours: Time threshold for quick replies (higher score)
            weights: Custom weights for implicit signals (must sum to 1.0)
        """
        self.CONTINUITY_THRESHOLD = continuity_threshold
        self.MAX_TIME_GAP_HOURS = max_time_gap_hours
        self.QUICK_REPLY_HOURS = quick_reply_hours

        # Validate and set weights
        if weights is None:
            self.weights = self.DEFAULT_WEIGHTS.copy()
        else:
            # Validate weights sum to 1.0
            weight_sum = sum(weights.values())
            if not (0.99 <= weight_sum <= 1.01):  # Allow small floating point error
                raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")
            self.weights = weights

    def detect_continuity(
        self,
        current_event: PerceivedEvent,
        previous_events: list[PerceivedEvent]
    ) -> ContinuityScore:
        """
        Detect if current event continues from previous events

        Args:
            current_event: Event being processed
            previous_events: Recent events (chronologically ordered, most recent first)

        Returns:
            ContinuityScore with signals and overall decision
        """
        if not previous_events:
            return ContinuityScore(overall_score=0.0, is_continuous=False)

        # Check most recent event for continuity
        most_recent = previous_events[0]

        # Calculate individual signals
        explicit_thread = self._check_explicit_thread(current_event, most_recent)
        is_reply = self._check_is_reply(current_event, most_recent)
        time_proximity = self._calculate_time_proximity(current_event, most_recent)
        participant_overlap = self._calculate_participant_overlap(current_event, most_recent)
        topic_similarity = self._calculate_topic_similarity(current_event, most_recent)
        entity_overlap = self._calculate_entity_overlap(current_event, most_recent)

        # Calculate overall score (weighted combination)
        overall_score = self._calculate_overall_score(
            explicit_thread=explicit_thread,
            is_reply=is_reply,
            time_proximity=time_proximity,
            participant_overlap=participant_overlap,
            topic_similarity=topic_similarity,
            entity_overlap=entity_overlap
        )

        # Determine if continuous
        is_continuous = overall_score >= self.CONTINUITY_THRESHOLD

        return ContinuityScore(
            overall_score=overall_score,
            is_continuous=is_continuous,
            explicit_thread_match=explicit_thread,
            is_reply=is_reply,
            time_proximity_score=time_proximity,
            participant_overlap_score=participant_overlap,
            topic_similarity_score=topic_similarity,
            entity_overlap_score=entity_overlap
        )

    def _check_explicit_thread(
        self,
        current: PerceivedEvent,
        previous: PerceivedEvent
    ) -> bool:
        """Check if events explicitly share a thread"""
        if not current.thread_id or not previous.thread_id:
            return False
        return current.thread_id == previous.thread_id

    def _check_is_reply(
        self,
        current: PerceivedEvent,
        previous: PerceivedEvent
    ) -> bool:
        """Check if current event is direct reply to previous"""
        if not current.in_reply_to:
            return False
        return current.in_reply_to == previous.source_id

    def _calculate_time_proximity(
        self,
        current: PerceivedEvent,
        previous: PerceivedEvent
    ) -> float:
        """
        Calculate time proximity score

        Returns 1.0 for very recent, decaying to 0.0 over MAX_TIME_GAP_HOURS

        Normalizes both datetimes to UTC before comparison to handle timezone
        differences correctly (e.g., EST vs UTC).

        Raises:
            ValueError: If datetimes are naive or if current event precedes previous
        """
        from datetime import timezone

        # Ensure both datetimes are timezone-aware for valid comparison
        if current.occurred_at.tzinfo is None or previous.occurred_at.tzinfo is None:
            raise ValueError("Cannot calculate time proximity for naive datetimes")

        # Normalize both datetimes to UTC to handle timezone differences
        # This prevents incorrect time gaps when events are in different timezones
        current_utc = current.occurred_at.astimezone(timezone.utc)
        previous_utc = previous.occurred_at.astimezone(timezone.utc)

        time_gap = current_utc - previous_utc

        # Negative time gap indicates events out of order (data corruption)
        if time_gap.total_seconds() < 0:
            raise ValueError(
                f"Current event occurred before previous event: "
                f"current={current_utc.isoformat()}, previous={previous_utc.isoformat()}"
            )

        gap_hours = time_gap.total_seconds() / 3600

        # Too far apart
        if gap_hours > self.MAX_TIME_GAP_HOURS:
            return 0.0

        # Quick replies get high score
        if gap_hours <= self.QUICK_REPLY_HOURS:
            return 1.0

        # Linear decay from QUICK_REPLY_HOURS to MAX_TIME_GAP_HOURS
        score = 1.0 - ((gap_hours - self.QUICK_REPLY_HOURS) /
                       (self.MAX_TIME_GAP_HOURS - self.QUICK_REPLY_HOURS))

        return max(0.0, min(1.0, score))

    def _calculate_participant_overlap(
        self,
        current: PerceivedEvent,
        previous: PerceivedEvent
    ) -> float:
        """
        Calculate participant overlap score

        High score if same people involved in both events.
        """
        # Get all participants from both events
        current_participants = self._get_participants(current)
        previous_participants = self._get_participants(previous)

        if not current_participants or not previous_participants:
            return 0.0

        # Calculate Jaccard similarity
        intersection = current_participants & previous_participants
        union = current_participants | previous_participants

        return len(intersection) / len(union)

    def _get_participants(self, event: PerceivedEvent) -> set[str]:
        """Get all participants (from, to, cc) from event"""
        participants = set()

        if event.from_person:
            participants.add(event.from_person.lower())

        for person in event.to_people:
            participants.add(person.lower())

        for person in event.cc_people:
            participants.add(person.lower())

        return participants

    def _calculate_topic_similarity(
        self,
        current: PerceivedEvent,
        previous: PerceivedEvent
    ) -> float:
        """
        Calculate topic similarity score

        Uses simple text similarity for now. Can be enhanced with embeddings.
        """
        if not current.topics or not previous.topics:
            # Fall back to title similarity
            return self._text_similarity(current.title, previous.title)

        # Calculate average similarity between topic pairs
        similarities = []
        for curr_topic in current.topics:
            for prev_topic in previous.topics:
                sim = self._text_similarity(curr_topic, prev_topic)
                similarities.append(sim)

        if not similarities:
            return 0.0

        return max(similarities)  # Use best match

    def _calculate_entity_overlap(
        self,
        current: PerceivedEvent,
        previous: PerceivedEvent
    ) -> float:
        """
        Calculate entity overlap score

        High score if events mention same entities (people, orgs, topics)
        """
        if not current.entities or not previous.entities:
            return 0.0

        # Extract entity values
        current_entities = {
            (e.type, e.value.lower())
            for e in current.entities
        }
        previous_entities = {
            (e.type, e.value.lower())
            for e in previous.entities
        }

        # Calculate Jaccard similarity
        intersection = current_entities & previous_entities
        union = current_entities | previous_entities

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using sequence matching

        Returns 0.0-1.0 similarity score
        """
        if not text1 or not text2:
            return 0.0

        # Normalize
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, text1, text2).ratio()

    def _calculate_overall_score(
        self,
        explicit_thread: bool,
        is_reply: bool,
        time_proximity: float,
        participant_overlap: float,
        topic_similarity: float,
        entity_overlap: float
    ) -> float:
        """
        Calculate weighted overall continuity score

        Explicit signals (thread, reply) are strongest.
        Implicit signals are combined using configurable weights when explicit signals absent.
        """
        # Explicit signals override everything
        if explicit_thread or is_reply:
            return 1.0  # Definitely continuous

        # Combine implicit signals with configurable weights
        score = (
            time_proximity * self.weights['time_proximity'] +
            participant_overlap * self.weights['participant_overlap'] +
            topic_similarity * self.weights['topic_similarity'] +
            entity_overlap * self.weights['entity_overlap']
        )

        return min(1.0, score)

    def find_conversation_chain(
        self,
        current_event: PerceivedEvent,
        all_events: list[PerceivedEvent],
        max_depth: int = 10
    ) -> list[PerceivedEvent]:
        """
        Find all events that are part of same conversation

        Walks backwards through events to build conversation chain.

        Args:
            current_event: Starting event
            all_events: All available events (sorted chronologically)
            max_depth: Maximum conversation length to track

        Returns:
            List of events in conversation (chronologically ordered, oldest first)
        """
        conversation = []
        current = current_event

        # Walk backwards up to max_depth
        for _ in range(max_depth):
            # Find previous continuous event
            previous_continuous = None

            for event in all_events:
                # Skip if same event or after current
                if event.event_id == current.event_id:
                    continue
                if event.occurred_at >= current.occurred_at:
                    continue

                # Check continuity
                score = self.detect_continuity(current, [event])
                # Take most recent continuous event
                if score.is_continuous and (previous_continuous is None or event.occurred_at > previous_continuous.occurred_at):
                    previous_continuous = event

            if previous_continuous is None:
                # No more continuous events
                break

            conversation.insert(0, previous_continuous)
            current = previous_continuous

        return conversation
