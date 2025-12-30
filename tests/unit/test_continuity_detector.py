"""
Tests for Continuity Detector

Tests ContinuityDetector that determines if events are part of
a continuous conversation or independent events.
"""

import pytest
from datetime import datetime, timedelta
from src.core.memory import ContinuityDetector, ContinuityScore
from src.core.events import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
    Entity,
)
from src.utils import now_utc


@pytest.fixture
def detector():
    """Create continuity detector instance"""
    return ContinuityDetector()


@pytest.fixture
def base_event():
    """Create a base event for testing"""
    now = now_utc()
    # Set base event to 3 days in past so tests that add time don't create future events
    base_time = now - timedelta(days=3)
    return PerceivedEvent(
        event_id="event_1",
        source=EventSource.EMAIL,
        source_id="email_1",
        occurred_at=base_time,
        received_at=base_time,
        perceived_at=base_time,
        title="Initial Email",
        content="This is the first email",
        event_type=EventType.INFORMATION,
        urgency=UrgencyLevel.LOW,
        entities=[
            Entity(type="person", value="alice@example.com", confidence=1.0)
        ],
        topics=["Project Alpha"],
        keywords=["project", "alpha"],
        from_person="alice@example.com",
        to_people=["me@example.com"],
        cc_people=[],
        thread_id="thread_123",
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={},
        perception_confidence=0.8,
        needs_clarification=False,
        clarification_questions=[],
        summary=None
    )


@pytest.fixture
def reply_event(base_event):
    """Create a reply event"""
    now = now_utc()
    return PerceivedEvent(
        event_id="event_2",
        source=EventSource.EMAIL,
        source_id="email_2",
        occurred_at=now,
        received_at=now,
        perceived_at=now,
        title="Re: Initial Email",
        content="This is a reply to the first email",
        event_type=EventType.REPLY,
        urgency=UrgencyLevel.LOW,
        entities=[
            Entity(type="person", value="alice@example.com", confidence=1.0)
        ],
        topics=["Project Alpha"],
        keywords=["project", "alpha"],
        from_person="me@example.com",
        to_people=["alice@example.com"],
        cc_people=[],
        thread_id="thread_123",
        references=["<msg1@example.com>"],
        in_reply_to="email_1",  # Links to base_event.source_id
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={},
        perception_confidence=0.8,
        needs_clarification=False,
        clarification_questions=[],
        summary=None
    )


class TestContinuityScoreBasic:
    """Basic tests for ContinuityScore"""

    def test_continuity_score_creation(self):
        """Test creating a continuity score"""
        score = ContinuityScore(
            overall_score=0.85,
            is_continuous=True,
            explicit_thread_match=True,
            is_reply=False,
            time_proximity_score=0.9,
            participant_overlap_score=0.8,
            topic_similarity_score=0.7,
            entity_overlap_score=0.6
        )

        assert score.overall_score == 0.85
        assert score.is_continuous is True
        assert score.explicit_thread_match is True

    def test_continuity_score_str(self):
        """Test string representation"""
        score = ContinuityScore(
            overall_score=0.75,
            is_continuous=True,
            explicit_thread_match=False,
            is_reply=True
        )

        str_repr = str(score)
        assert "0.75" in str_repr
        assert "continuous=True" in str_repr
        assert "thread=False" in str_repr
        assert "reply=True" in str_repr


class TestExplicitThreadDetection:
    """Tests for explicit thread matching"""

    def test_explicit_thread_match(self, detector, base_event, reply_event):
        """Test detecting explicit thread match"""
        # Both have thread_id="thread_123"
        score = detector.detect_continuity(reply_event, [base_event])

        assert score.explicit_thread_match is True
        assert score.is_continuous is True
        assert score.overall_score == 1.0  # Explicit signals return 1.0

    def test_no_thread_id(self, detector, base_event):
        """Test when events have no thread_id"""
        event_no_thread = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Unrelated Email",
            content="Different content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(event_no_thread, [base_event])

        assert score.explicit_thread_match is False

    def test_different_thread_ids(self, detector, base_event):
        """Test events with different thread IDs"""
        event_different_thread = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Different Thread",
            content="Different thread content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id="different_thread_456",
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(event_different_thread, [base_event])

        assert score.explicit_thread_match is False


class TestReplyDetection:
    """Tests for reply detection"""

    def test_is_reply(self, detector, base_event, reply_event):
        """Test detecting direct reply"""
        score = detector.detect_continuity(reply_event, [base_event])

        assert score.is_reply is True
        assert score.is_continuous is True
        assert score.overall_score == 1.0  # Explicit signal

    def test_not_reply(self, detector, base_event):
        """Test when event is not a reply"""
        non_reply = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="New Topic",
            content="Completely new email",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(non_reply, [base_event])

        assert score.is_reply is False


class TestTimeProximity:
    """Tests for time proximity scoring"""

    def test_quick_reply(self, detector, base_event):
        """Test quick reply within QUICK_REPLY_HOURS"""
        # Event within 1 hour (< QUICK_REPLY_HOURS=2)
        quick_event = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=base_event.occurred_at + timedelta(minutes=30),
            received_at=base_event.occurred_at + timedelta(minutes=30),
            perceived_at=now_utc(),
            title="Quick Reply",
            content="Fast response",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(quick_event, [base_event])

        assert score.time_proximity_score == 1.0

    def test_medium_gap(self, detector, base_event):
        """Test medium time gap"""
        # Event 12 hours later (between QUICK_REPLY_HOURS and MAX_TIME_GAP_HOURS)
        medium_event = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=base_event.occurred_at + timedelta(hours=12),
            received_at=base_event.occurred_at + timedelta(hours=12),
            perceived_at=now_utc(),
            title="Medium Gap",
            content="Response after 12 hours",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(medium_event, [base_event])

        # Should be between 0 and 1
        assert 0.0 < score.time_proximity_score < 1.0

    def test_too_far_apart(self, detector, base_event):
        """Test events too far apart in time"""
        # Event more than MAX_TIME_GAP_HOURS (24 hours) later
        old_event = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=base_event.occurred_at + timedelta(hours=48),
            received_at=base_event.occurred_at + timedelta(hours=48),
            perceived_at=now_utc(),
            title="Old Event",
            content="Very delayed response",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(old_event, [base_event])

        assert score.time_proximity_score == 0.0


class TestParticipantOverlap:
    """Tests for participant overlap scoring"""

    def test_same_participants(self, detector, base_event):
        """Test events with same participants"""
        same_participants = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Follow-up",
            content="Following up",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="alice@example.com",  # Same as base_event
            to_people=["me@example.com"],  # Same as base_event
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(same_participants, [base_event])

        # Should have high participant overlap
        assert score.participant_overlap_score > 0.5

    def test_no_participant_overlap(self, detector, base_event):
        """Test events with no participant overlap"""
        different_participants = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Unrelated",
            content="Unrelated email",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="bob@example.com",  # Different
            to_people=["charlie@example.com"],  # Different
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(different_participants, [base_event])

        assert score.participant_overlap_score == 0.0


class TestTopicSimilarity:
    """Tests for topic similarity scoring"""

    def test_same_topics(self, detector, base_event):
        """Test events with same topics"""
        same_topic = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Re: Project Alpha Update",
            content="More about project alpha",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=["Project Alpha"],  # Same as base_event
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(same_topic, [base_event])

        # Should have high topic similarity
        assert score.topic_similarity_score > 0.5

    def test_different_topics(self, detector, base_event):
        """Test events with different topics"""
        different_topic = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Completely Different Subject",
            content="About something else entirely",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=["Unrelated Topic"],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(different_topic, [base_event])

        # Should have low topic similarity
        assert score.topic_similarity_score < 0.5


class TestEntityOverlap:
    """Tests for entity overlap scoring"""

    def test_same_entities(self, detector, base_event):
        """Test events with same entities"""
        same_entities = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Follow-up",
            content="Following up",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[
                Entity(type="person", value="alice@example.com", confidence=1.0)
            ],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(same_entities, [base_event])

        # Should have high entity overlap
        assert score.entity_overlap_score > 0.5

    def test_no_entity_overlap(self, detector, base_event):
        """Test events with no entity overlap"""
        different_entities = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="Different",
            content="Different content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[
                Entity(type="organization", value="Acme Corp", confidence=1.0)
            ],
            topics=[],
            keywords=[],
            from_person="other@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(different_entities, [base_event])

        assert score.entity_overlap_score == 0.0


class TestOverallContinuity:
    """Tests for overall continuity determination"""

    def test_no_previous_events(self, detector):
        """Test with no previous events"""
        current = PerceivedEvent(
            event_id="event_1",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now_utc(),
            received_at=now_utc(),
            perceived_at=now_utc(),
            title="First Event",
            content="Content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=[],
            keywords=[],
            from_person="test@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(current, [])

        assert score.overall_score == 0.0
        assert score.is_continuous is False

    def test_continuity_threshold(self, detector, base_event):
        """Test continuity threshold"""
        # Create event that should be borderline
        borderline = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=base_event.occurred_at + timedelta(hours=1),
            received_at=base_event.occurred_at + timedelta(hours=1),
            perceived_at=now_utc(),
            title="Project Alpha Update",
            content="Update on project alpha",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=["Project Alpha"],
            keywords=[],
            from_person="alice@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        score = detector.detect_continuity(borderline, [base_event])

        # is_continuous should match threshold check
        expected_continuous = score.overall_score >= detector.CONTINUITY_THRESHOLD
        assert score.is_continuous == expected_continuous


class TestConversationChain:
    """Tests for finding conversation chains"""

    def test_find_simple_chain(self, detector):
        """Test finding a simple conversation chain"""
        now = now_utc()

        event1 = PerceivedEvent(
            event_id="event_1",
            source=EventSource.EMAIL,
            source_id="email_1",
            occurred_at=now - timedelta(hours=3),
            received_at=now - timedelta(hours=3),
            perceived_at=now - timedelta(hours=3),
            title="Start",
            content="Starting conversation",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=["Project"],
            keywords=[],
            from_person="alice@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id="thread_1",
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        event2 = PerceivedEvent(
            event_id="event_2",
            source=EventSource.EMAIL,
            source_id="email_2",
            occurred_at=now - timedelta(hours=2),
            received_at=now - timedelta(hours=2),
            perceived_at=now - timedelta(hours=2),
            title="Re: Start",
            content="Reply",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=["Project"],
            keywords=[],
            from_person="me@example.com",
            to_people=["alice@example.com"],
            cc_people=[],
            thread_id="thread_1",
            references=[],
            in_reply_to="email_1",
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        event3 = PerceivedEvent(
            event_id="event_3",
            source=EventSource.EMAIL,
            source_id="email_3",
            occurred_at=now - timedelta(hours=1),
            received_at=now - timedelta(hours=1),
            perceived_at=now - timedelta(hours=1),
            title="Re: Re: Start",
            content="Another reply",
            event_type=EventType.REPLY,
            urgency=UrgencyLevel.LOW,
            entities=[],
            topics=["Project"],
            keywords=[],
            from_person="alice@example.com",
            to_people=["me@example.com"],
            cc_people=[],
            thread_id="thread_1",
            references=[],
            in_reply_to="email_2",
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.7,
            needs_clarification=False,
            clarification_questions=[],
            summary=None
        )

        all_events = [event1, event2, event3]
        chain = detector.find_conversation_chain(event3, all_events, max_depth=10)

        # Should find event1 and event2 in the chain
        assert len(chain) >= 1
        # Chain should be chronologically ordered (oldest first)
        for i in range(len(chain) - 1):
            assert chain[i].occurred_at <= chain[i + 1].occurred_at

    def test_max_depth_limit(self, detector):
        """Test max_depth limits chain length"""
        now = now_utc()

        # Create long chain of events
        events = []
        for i in range(20):
            event = PerceivedEvent(
                event_id=f"event_{i}",
                source=EventSource.EMAIL,
                source_id=f"email_{i}",
                occurred_at=now - timedelta(hours=20-i),
                received_at=now - timedelta(hours=20-i),
                perceived_at=now - timedelta(hours=20-i),
                title=f"Message {i}",
                content="Content",
                event_type=EventType.REPLY,
                urgency=UrgencyLevel.LOW,
                entities=[],
                topics=["Thread"],
                keywords=[],
                from_person="alice@example.com",
                to_people=["me@example.com"],
                cc_people=[],
                thread_id="long_thread",
                references=[],
                in_reply_to=f"email_{i-1}" if i > 0 else None,
                has_attachments=False,
                attachment_count=0,
                attachment_types=[],
                urls=[],
                metadata={},
                perception_confidence=0.7,
                needs_clarification=False,
                clarification_questions=[],
                summary=None
            )
            events.append(event)

        latest_event = events[-1]
        chain = detector.find_conversation_chain(latest_event, events, max_depth=5)

        # Chain should be limited by max_depth
        assert len(chain) <= 5
