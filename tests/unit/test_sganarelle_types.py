"""
Tests pour Sganarelle Types

Test de tous les dataclasses immutables avec validation.
"""

import pytest
from datetime import datetime, timedelta
from dataclasses import FrozenInstanceError

from src.sganarelle.types import (
    UserFeedback,
    FeedbackAnalysis,
    KnowledgeUpdate,
    Pattern,
    ProviderScore,
    LearningResult,
    UpdateType,
    PatternType
)
from src.core.events.universal_event import (
    PerceivedEvent,
    EventType,
    EventSource,
    UrgencyLevel,
    Entity,
    now_utc
)


def _make_event(
    event_type=EventType.INFORMATION,
    title="Test",
    urgency=UrgencyLevel.MEDIUM,
    entities=None
) -> PerceivedEvent:
    """Helper to create a valid PerceivedEvent with sensible defaults"""
    return PerceivedEvent(
        event_id="test_event",
        source=EventSource.EMAIL,
        source_id="test@example.com_123",
        occurred_at=now_utc(),
        received_at=now_utc(),
        title=title,
        content="Test content",
        event_type=event_type,
        urgency=urgency,
        entities=entities or [],
        topics=["test"],
        keywords=["test"],
        from_person="test@example.com",
        to_people=["recipient@example.com"],
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={},
        perception_confidence=0.9,
        needs_clarification=False,
        clarification_questions=[]
    )
from src.figaro.actions.tasks import CreateTaskAction


class TestUserFeedback:
    """Tests pour UserFeedback dataclass"""

    def test_init_minimal(self):
        """Test création avec paramètres minimaux"""
        feedback = UserFeedback(approval=True)

        assert feedback.approval is True
        assert feedback.rating is None
        assert feedback.comment is None
        assert feedback.correction is None
        assert feedback.action_executed is False
        assert feedback.time_to_action == 0.0
        assert feedback.modification is None
        assert isinstance(feedback.timestamp, datetime)
        assert len(feedback.feedback_id) > 0

    def test_init_complete(self):
        """Test création avec tous paramètres"""
        action = CreateTaskAction(name="Test", project_name="Test")

        feedback = UserFeedback(
            approval=True,
            rating=5,
            comment="Excellent decision",
            correction=None,
            action_executed=True,
            time_to_action=15.5,
            modification=action
        )

        assert feedback.approval is True
        assert feedback.rating == 5
        assert feedback.comment == "Excellent decision"
        assert feedback.action_executed is True
        assert feedback.time_to_action == 15.5
        assert feedback.modification == action

    def test_validation_rating_range(self):
        """Test validation rating 1-5"""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            feedback = UserFeedback(approval=True, rating=rating)
            assert feedback.rating == rating

        # Invalid ratings
        with pytest.raises(ValueError, match="Rating must be 1-5"):
            UserFeedback(approval=True, rating=0)

        with pytest.raises(ValueError, match="Rating must be 1-5"):
            UserFeedback(approval=True, rating=6)

    def test_validation_time_to_action(self):
        """Test validation time_to_action >= 0"""
        # Valid
        feedback = UserFeedback(approval=True, time_to_action=0.0)
        assert feedback.time_to_action == 0.0

        feedback = UserFeedback(approval=True, time_to_action=100.5)
        assert feedback.time_to_action == 100.5

        # Invalid
        with pytest.raises(ValueError, match="time_to_action must be >= 0"):
            UserFeedback(approval=True, time_to_action=-1.0)

    def test_is_positive_property(self):
        """Test is_positive property logic"""
        # Positive: approval + no rating
        feedback = UserFeedback(approval=True)
        assert feedback.is_positive is True

        # Positive: approval + high rating
        feedback = UserFeedback(approval=True, rating=5)
        assert feedback.is_positive is True

        # Negative: no approval
        feedback = UserFeedback(approval=False)
        assert feedback.is_positive is False

        # Negative: approval but low rating
        feedback = UserFeedback(approval=True, rating=2)
        assert feedback.is_positive is False

    def test_implicit_quality_score(self):
        """Test calcul implicit_quality_score"""
        # Perfect: quick execution, no modification
        feedback = UserFeedback(
            approval=True,
            action_executed=True,
            time_to_action=10.0
        )
        score = feedback.implicit_quality_score
        assert 0.9 < score <= 1.0

        # Slow execution
        feedback = UserFeedback(
            approval=True,
            action_executed=True,
            time_to_action=120.0
        )
        score = feedback.implicit_quality_score
        assert 0.6 < score < 0.8

        # With modification
        action = CreateTaskAction(name="Test", project_name="Test")
        feedback = UserFeedback(
            approval=True,
            action_executed=True,
            modification=action
        )
        score = feedback.implicit_quality_score
        assert 0.4 < score < 0.6

        # Not executed
        feedback = UserFeedback(
            approval=True,
            action_executed=False
        )
        score = feedback.implicit_quality_score
        assert 0.2 < score < 0.4

    def test_immutability(self):
        """Test que UserFeedback est immutable"""
        feedback = UserFeedback(approval=True)

        with pytest.raises(FrozenInstanceError):
            feedback.approval = False

        with pytest.raises(FrozenInstanceError):
            feedback.rating = 5


class TestFeedbackAnalysis:
    """Tests pour FeedbackAnalysis dataclass"""

    def test_init_valid(self):
        """Test création avec paramètres valides"""
        feedback = UserFeedback(approval=True, rating=4)

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=0.85,
            suggested_improvements=["Improve X", "Fix Y"],
            confidence_error=0.1,
            action_quality_score=0.9,
            reasoning_quality_score=0.8
        )

        assert analysis.feedback == feedback
        assert analysis.correctness_score == 0.85
        assert len(analysis.suggested_improvements) == 2
        assert analysis.confidence_error == 0.1
        assert analysis.action_quality_score == 0.9
        assert analysis.reasoning_quality_score == 0.8

    def test_validation_scores_range(self):
        """Test validation des scores 0-1"""
        feedback = UserFeedback(approval=True)

        # Invalid correctness_score
        with pytest.raises(ValueError, match="correctness_score must be 0-1"):
            FeedbackAnalysis(
                feedback=feedback,
                correctness_score=1.5,
                suggested_improvements=[],
                confidence_error=0.0,
                action_quality_score=0.5,
                reasoning_quality_score=0.5
            )

        # Invalid action_quality_score
        with pytest.raises(ValueError, match="action_quality_score must be 0-1"):
            FeedbackAnalysis(
                feedback=feedback,
                correctness_score=0.5,
                suggested_improvements=[],
                confidence_error=0.0,
                action_quality_score=-0.1,
                reasoning_quality_score=0.5
            )

        # Invalid reasoning_quality_score
        with pytest.raises(ValueError, match="reasoning_quality_score must be 0-1"):
            FeedbackAnalysis(
                feedback=feedback,
                correctness_score=0.5,
                suggested_improvements=[],
                confidence_error=0.0,
                action_quality_score=0.5,
                reasoning_quality_score=1.1
            )


class TestKnowledgeUpdate:
    """Tests pour KnowledgeUpdate dataclass"""

    def test_init_valid(self):
        """Test création valide"""
        update = KnowledgeUpdate(
            update_type=UpdateType.NOTE_CREATED,
            target_id="note_123",
            changes={"title": "Test Note", "content": "Content"},
            confidence=0.9,
            source="learning_from_execution"
        )

        assert update.update_type == UpdateType.NOTE_CREATED
        assert update.target_id == "note_123"
        assert update.changes["title"] == "Test Note"
        assert update.confidence == 0.9
        assert update.source == "learning_from_execution"
        assert isinstance(update.timestamp, datetime)
        assert len(update.update_id) > 0

    def test_validation_confidence(self):
        """Test validation confidence 0-1"""
        with pytest.raises(ValueError, match="confidence must be 0-1"):
            KnowledgeUpdate(
                update_type=UpdateType.NOTE_CREATED,
                target_id="note_123",
                changes={"test": "value"},
                confidence=1.5,
                source="test"
            )

    def test_validation_target_id(self):
        """Test validation target_id non vide"""
        with pytest.raises(ValueError, match="target_id is required"):
            KnowledgeUpdate(
                update_type=UpdateType.NOTE_CREATED,
                target_id="",
                changes={"test": "value"},
                confidence=0.9,
                source="test"
            )

    def test_validation_changes(self):
        """Test validation changes non vide"""
        with pytest.raises(ValueError, match="changes dict cannot be empty"):
            KnowledgeUpdate(
                update_type=UpdateType.NOTE_CREATED,
                target_id="note_123",
                changes={},
                confidence=0.9,
                source="test"
            )

    def test_to_dict(self):
        """Test sérialisation to_dict"""
        update = KnowledgeUpdate(
            update_type=UpdateType.ENTITY_ADDED,
            target_id="entity_456",
            changes={"name": "Test Entity"},
            confidence=0.8,
            source="test"
        )

        data = update.to_dict()

        assert data["update_id"] == update.update_id
        assert data["update_type"] == "entity_added"
        assert data["target_id"] == "entity_456"
        assert data["changes"] == {"name": "Test Entity"}
        assert data["confidence"] == 0.8
        assert data["source"] == "test"
        assert "timestamp" in data


class TestPattern:
    """Tests pour Pattern dataclass"""

    def test_init_valid(self):
        """Test création valide"""
        pattern = Pattern(
            pattern_id="pattern_123",
            pattern_type=PatternType.CONTEXT_TRIGGER,
            conditions={"event_type": "email_received", "min_urgency": 3},
            suggested_actions=["archive", "create_task"],
            confidence=0.8,
            success_rate=0.75,
            occurrences=10,
            last_seen=now_utc(),
            created_at=now_utc() - timedelta(days=7)
        )

        assert pattern.pattern_id == "pattern_123"
        assert pattern.pattern_type == PatternType.CONTEXT_TRIGGER
        assert len(pattern.conditions) == 2
        assert len(pattern.suggested_actions) == 2
        assert pattern.confidence == 0.8
        assert pattern.success_rate == 0.75
        assert pattern.occurrences == 10

    def test_validation_scores(self):
        """Test validation confidence et success_rate"""
        # Invalid confidence
        with pytest.raises(ValueError, match="confidence must be 0-1"):
            Pattern(
                pattern_id="test",
                pattern_type=PatternType.CONTEXT_TRIGGER,
                conditions={"test": "value"},
                suggested_actions=["action1"],
                confidence=1.5,
                success_rate=0.5,
                occurrences=1,
                last_seen=now_utc(),
                created_at=now_utc()
            )

        # Invalid success_rate
        with pytest.raises(ValueError, match="success_rate must be 0-1"):
            Pattern(
                pattern_id="test",
                pattern_type=PatternType.CONTEXT_TRIGGER,
                conditions={"test": "value"},
                suggested_actions=["action1"],
                confidence=0.5,
                success_rate=-0.1,
                occurrences=1,
                last_seen=now_utc(),
                created_at=now_utc()
            )

    def test_validation_occurrences(self):
        """Test validation occurrences >= 0"""
        with pytest.raises(ValueError, match="occurrences must be >= 0"):
            Pattern(
                pattern_id="test",
                pattern_type=PatternType.CONTEXT_TRIGGER,
                conditions={"test": "value"},
                suggested_actions=["action1"],
                confidence=0.5,
                success_rate=0.5,
                occurrences=-1,
                last_seen=now_utc(),
                created_at=now_utc()
            )

    def test_validation_suggested_actions(self):
        """Test validation suggested_actions non vide"""
        with pytest.raises(ValueError, match="suggested_actions cannot be empty"):
            Pattern(
                pattern_id="test",
                pattern_type=PatternType.CONTEXT_TRIGGER,
                conditions={"test": "value"},
                suggested_actions=[],
                confidence=0.5,
                success_rate=0.5,
                occurrences=1,
                last_seen=now_utc(),
                created_at=now_utc()
            )

    def test_matches_method(self):
        """Test méthode matches()"""
        pattern = Pattern(
            pattern_id="email_urgent_pattern",
            pattern_type=PatternType.CONTEXT_TRIGGER,
            conditions={
                "event_type": "information",
                "required_entities": ["person"]
            },
            suggested_actions=["create_task"],
            confidence=0.8,
            success_rate=0.9,
            occurrences=20,
            last_seen=now_utc(),
            created_at=now_utc()
        )

        # Matching event
        matching_event = _make_event(
            event_type=EventType.INFORMATION,
            title="Test",
            urgency=UrgencyLevel.HIGH,
            entities=[Entity(type="person", value="John", confidence=0.9)]
        )

        assert pattern.matches(matching_event, {}) is True

        # Non-matching: wrong event type
        non_matching = _make_event(
            event_type=EventType.ACTION_REQUIRED,
            title="Test",
            urgency=UrgencyLevel.HIGH,
            entities=[Entity(type="person", value="John", confidence=0.9)]
        )

        assert pattern.matches(non_matching, {}) is False

        # Non-matching: missing entity (urgency comparison removed - requires numeric urgency levels)
        non_matching = _make_event(
            event_type=EventType.INFORMATION,
            title="Test",
            urgency=UrgencyLevel.HIGH,
            entities=[]
        )

        assert pattern.matches(non_matching, {}) is False

    def test_to_dict(self):
        """Test sérialisation"""
        pattern = Pattern(
            pattern_id="test",
            pattern_type=PatternType.ACTION_SEQUENCE,
            conditions={"test": "value"},
            suggested_actions=["action1"],
            confidence=0.8,
            success_rate=0.9,
            occurrences=5,
            last_seen=now_utc(),
            created_at=now_utc()
        )

        data = pattern.to_dict()

        assert data["pattern_id"] == "test"
        assert data["pattern_type"] == "action_sequence"
        assert "last_seen" in data
        assert "created_at" in data


class TestProviderScore:
    """Tests pour ProviderScore dataclass"""

    def test_init_valid(self):
        """Test création valide"""
        score = ProviderScore(
            provider_name="anthropic",
            model_tier="haiku",
            total_calls=100,
            successful_calls=95,
            failed_calls=5,
            avg_confidence=0.85,
            calibration_error=0.05,
            avg_latency_ms=150.0,
            p95_latency_ms=300.0,
            total_cost_usd=0.50
        )

        assert score.provider_name == "anthropic"
        assert score.model_tier == "haiku"
        assert score.total_calls == 100
        assert score.successful_calls == 95
        assert score.failed_calls == 5

    def test_validation_total_calls_equals_sum(self):
        """Test validation total = successful + failed"""
        with pytest.raises(ValueError, match="total_calls must equal"):
            ProviderScore(
                provider_name="test",
                model_tier="haiku",
                total_calls=100,
                successful_calls=95,
                failed_calls=10,  # 95 + 10 != 100
                avg_confidence=0.8,
                calibration_error=0.1,
                avg_latency_ms=100.0,
                p95_latency_ms=200.0,
                total_cost_usd=0.1
            )

    def test_success_rate_property(self):
        """Test calcul success_rate"""
        score = ProviderScore(
            provider_name="test",
            model_tier="haiku",
            total_calls=100,
            successful_calls=80,
            failed_calls=20,
            avg_confidence=0.8,
            calibration_error=0.1,
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            total_cost_usd=0.5
        )

        assert score.success_rate == 0.8

        # Zero calls
        score = ProviderScore(
            provider_name="test",
            model_tier="haiku",
            total_calls=0,
            successful_calls=0,
            failed_calls=0,
            avg_confidence=0.0,
            calibration_error=0.0,
            avg_latency_ms=0.0,
            p95_latency_ms=0.0,
            total_cost_usd=0.0
        )

        assert score.success_rate == 0.0

    def test_cost_per_success_property(self):
        """Test calcul cost_per_success_usd"""
        score = ProviderScore(
            provider_name="test",
            model_tier="haiku",
            total_calls=100,
            successful_calls=80,
            failed_calls=20,
            avg_confidence=0.8,
            calibration_error=0.1,
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            total_cost_usd=0.80
        )

        assert score.cost_per_success_usd == 0.01  # 0.80 / 80

        # Zero successful calls
        score = ProviderScore(
            provider_name="test",
            model_tier="haiku",
            total_calls=10,
            successful_calls=0,
            failed_calls=10,
            avg_confidence=0.0,
            calibration_error=0.0,
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            total_cost_usd=0.10
        )

        assert score.cost_per_success_usd == 0.0

    def test_to_dict(self):
        """Test sérialisation"""
        score = ProviderScore(
            provider_name="anthropic",
            model_tier="sonnet",
            total_calls=50,
            successful_calls=48,
            failed_calls=2,
            avg_confidence=0.9,
            calibration_error=0.03,
            avg_latency_ms=250.0,
            p95_latency_ms=500.0,
            total_cost_usd=1.50
        )

        data = score.to_dict()

        assert data["provider_name"] == "anthropic"
        assert data["model_tier"] == "sonnet"
        assert data["success_rate"] == 0.96
        assert "cost_per_success_usd" in data
        assert "updated_at" in data


class TestLearningResult:
    """Tests pour LearningResult dataclass"""

    def test_init_valid(self):
        """Test création valide"""
        update = KnowledgeUpdate(
            update_type=UpdateType.NOTE_CREATED,
            target_id="note_123",
            changes={"title": "Test"},
            confidence=0.9,
            source="test"
        )

        pattern = Pattern(
            pattern_id="pattern_123",
            pattern_type=PatternType.CONTEXT_TRIGGER,
            conditions={"test": "value"},
            suggested_actions=["action1"],
            confidence=0.8,
            success_rate=0.9,
            occurrences=10,
            last_seen=now_utc(),
            created_at=now_utc()
        )

        score = ProviderScore(
            provider_name="anthropic",
            model_tier="haiku",
            total_calls=10,
            successful_calls=9,
            failed_calls=1,
            avg_confidence=0.85,
            calibration_error=0.05,
            avg_latency_ms=150.0,
            p95_latency_ms=300.0,
            total_cost_usd=0.10
        )

        result = LearningResult(
            knowledge_updates=[update],
            pattern_updates=[pattern],
            provider_scores={"anthropic_haiku": score},
            confidence_adjustments={"overall": 0.05},
            duration=1.5,
            updates_applied=1,
            updates_failed=0
        )

        assert len(result.knowledge_updates) == 1
        assert len(result.pattern_updates) == 1
        assert len(result.provider_scores) == 1
        assert result.duration == 1.5
        assert result.updates_applied == 1
        assert result.updates_failed == 0

    def test_success_property(self):
        """Test propriété success"""
        # Success
        result = LearningResult(
            knowledge_updates=[],
            pattern_updates=[],
            provider_scores={},
            confidence_adjustments={},
            duration=1.0,
            updates_applied=5,
            updates_failed=0
        )

        assert result.success is True

        # Failure
        result = LearningResult(
            knowledge_updates=[],
            pattern_updates=[],
            provider_scores={},
            confidence_adjustments={},
            duration=1.0,
            updates_applied=5,
            updates_failed=2
        )

        assert result.success is False

    def test_total_updates_property(self):
        """Test propriété total_updates"""
        result = LearningResult(
            knowledge_updates=[],
            pattern_updates=[],
            provider_scores={},
            confidence_adjustments={},
            duration=1.0,
            updates_applied=10,
            updates_failed=3
        )

        assert result.total_updates == 13

    def test_to_dict(self):
        """Test sérialisation"""
        result = LearningResult(
            knowledge_updates=[],
            pattern_updates=[],
            provider_scores={},
            confidence_adjustments={"overall": 0.05},
            duration=2.5,
            updates_applied=5,
            updates_failed=1,
            metadata={"test": "value"}
        )

        data = result.to_dict()

        assert data["success"] is False  # Because updates_failed > 0
        assert data["duration"] == 2.5
        assert data["updates_applied"] == 5
        assert data["updates_failed"] == 1
        assert "result_id" in data
        assert "timestamp" in data
        assert data["metadata"] == {"test": "value"}
