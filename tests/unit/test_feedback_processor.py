"""
Tests pour Sganarelle Feedback Processor

Test du traitement et analyse du feedback utilisateur.
"""


import pytest

from src.core.events.universal_event import (
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
)
from src.core.memory.working_memory import Hypothesis, WorkingMemory
from src.figaro.actions.tasks import CreateTaskAction
from src.sganarelle.feedback_processor import FeedbackProcessor
from src.sganarelle.types import FeedbackAnalysis, UserFeedback
from src.utils import now_utc


def _make_event(
    event_type=EventType.INFORMATION,
    urgency=UrgencyLevel.MEDIUM,
    entities=None
) -> PerceivedEvent:
    """Helper to create a valid PerceivedEvent for testing"""
    return PerceivedEvent(
        event_id="test_event",
        source=EventSource.EMAIL,
        source_id="test@example.com_123",
        occurred_at=now_utc(),
        received_at=now_utc(),
        title="Test",
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


class TestFeedbackProcessorInit:
    """Tests d'initialisation"""

    def test_init_default(self):
        """Test initialisation avec paramètres par défaut"""
        processor = FeedbackProcessor()

        assert processor.implicit_weight == 0.3
        assert processor.explicit_weight == 0.7

    def test_init_custom_weights(self):
        """Test avec poids personnalisés"""
        processor = FeedbackProcessor(
            implicit_weight=0.4,
            explicit_weight=0.6
        )

        assert processor.implicit_weight == 0.4
        assert processor.explicit_weight == 0.6

    def test_init_validation_weight_range(self):
        """Test validation poids 0-1"""
        with pytest.raises(ValueError, match="implicit_weight doit être 0-1"):
            FeedbackProcessor(implicit_weight=1.5, explicit_weight=0.5)

        with pytest.raises(ValueError, match="explicit_weight doit être 0-1"):
            FeedbackProcessor(implicit_weight=0.5, explicit_weight=-0.1)

    def test_init_validation_weight_sum(self):
        """Test validation somme poids = 1"""
        with pytest.raises(ValueError, match="Poids doivent sommer à 1.0"):
            FeedbackProcessor(implicit_weight=0.5, explicit_weight=0.6)


class TestAnalyzeFeedback:
    """Tests de la méthode analyze_feedback"""

    @pytest.fixture
    def processor(self):
        """Processeur avec poids par défaut"""
        return FeedbackProcessor()

    @pytest.fixture
    def working_memory(self):
        """Working memory basique pour tests"""
        event = PerceivedEvent(
            event_id="test_event_001",
            source=EventSource.EMAIL,
            source_id="test@example.com_12345",
            occurred_at=now_utc(),
            received_at=now_utc(),
            title="Test Email",
            content="This is a test email content",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.MEDIUM,
            entities=[],
            topics=["testing"],
            keywords=["test"],
            from_person="sender@example.com",
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

        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "initial")

        # Add hypothesis
        hypothesis = Hypothesis(
            id="hyp_1",
            description="Archive this email",
            confidence=0.85,
            supporting_evidence=["Low priority"],
            contradicting_evidence=[]
        )
        wm.add_hypothesis(hypothesis)
        wm.current_best_hypothesis = "hyp_1"
        wm.update_confidence(0.85)

        wm.complete_reasoning_pass()

        return wm

    @pytest.fixture
    def actions(self):
        """Actions basiques pour tests"""
        return [CreateTaskAction(name="Test Task")]

    def test_analyze_positive_feedback(self, processor, working_memory, actions):
        """Test analyse feedback positif"""
        feedback = UserFeedback(
            approval=True,
            rating=5,
            action_executed=True,
            time_to_action=10.0
        )

        analysis = processor.analyze_feedback(feedback, working_memory, actions)

        assert isinstance(analysis, FeedbackAnalysis)
        assert analysis.feedback == feedback
        assert analysis.correctness_score > 0.7
        assert analysis.action_quality_score > 0.7
        assert analysis.reasoning_quality_score > 0.7
        # Positive feedback may not have suggestions (nothing to improve)
        assert isinstance(analysis.suggested_improvements, list)

    def test_analyze_negative_feedback(self, processor, working_memory, actions):
        """Test analyse feedback négatif"""
        feedback = UserFeedback(
            approval=False,
            rating=1,
            comment="Wrong action",
            action_executed=False
        )

        analysis = processor.analyze_feedback(feedback, working_memory, actions)

        assert analysis.correctness_score < 0.5
        assert analysis.action_quality_score < 0.5
        # Suggestions d'amélioration should be present
        assert len(analysis.suggested_improvements) > 0

    def test_analyze_with_correction(self, processor, working_memory, actions):
        """Test feedback avec correction"""
        feedback = UserFeedback(
            approval=False,
            correction="Should have created a task instead",
            action_executed=False
        )

        analysis = processor.analyze_feedback(feedback, working_memory, actions)

        # Correctness score should be low with correction
        assert analysis.correctness_score < 0.5

        # Suggestions should include correction
        suggestions_text = " ".join(analysis.suggested_improvements)
        assert "correction" in suggestions_text.lower()

    def test_analyze_with_modification(self, processor, working_memory, actions):
        """Test feedback avec modification d'action"""
        modified_action = CreateTaskAction(name="Modified Task", project_name="Test")

        feedback = UserFeedback(
            approval=True,
            modification=modified_action,
            action_executed=True,
            time_to_action=30.0
        )

        analysis = processor.analyze_feedback(feedback, working_memory, actions)

        # Modification should lower scores
        assert analysis.correctness_score < 0.9
        assert analysis.action_quality_score < 0.9

    def test_confidence_error_overconfident(self, processor, actions):
        """Test calcul erreur confiance (overconfident)"""
        # High confidence mais rejected
        event = _make_event()

        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "initial")
        wm.update_confidence(0.95)  # Very high confidence
        wm.complete_reasoning_pass()

        feedback = UserFeedback(
            approval=False,  # But rejected
            rating=1
        )

        analysis = processor.analyze_feedback(feedback, wm, actions)

        # Should detect overconfidence
        assert analysis.confidence_error > 0  # Positive = overconfident

    def test_confidence_error_underconfident(self, processor, actions):
        """Test calcul erreur confiance (underconfident)"""
        # Low confidence mais approved
        event = _make_event()

        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "initial")
        wm.update_confidence(0.60)  # Low confidence
        wm.complete_reasoning_pass()

        feedback = UserFeedback(
            approval=True,  # But approved
            rating=5,
            action_executed=True,
            time_to_action=15.0
        )

        analysis = processor.analyze_feedback(feedback, wm, actions)

        # Should detect underconfidence
        assert analysis.confidence_error < 0  # Negative = underconfident

    def test_suggestions_for_slow_response(self, processor, working_memory, actions):
        """Test suggestions pour temps de réponse lent"""
        feedback = UserFeedback(
            approval=True,
            action_executed=True,
            time_to_action=150.0  # Very slow
        )

        analysis = processor.analyze_feedback(feedback, working_memory, actions)

        suggestions_text = " ".join(analysis.suggested_improvements)
        assert "temps" in suggestions_text.lower() or "performance" in suggestions_text.lower()

    def test_metadata_populated(self, processor, working_memory, actions):
        """Test que metadata est bien rempli"""
        feedback = UserFeedback(
            approval=True,
            rating=4,
            action_executed=True,
            time_to_action=25.0
        )

        analysis = processor.analyze_feedback(feedback, working_memory, actions)

        assert "passes_executed" in analysis.metadata
        assert "actions_count" in analysis.metadata
        assert "time_to_action" in analysis.metadata
        assert "implicit_score" in analysis.metadata
        assert "weights" in analysis.metadata

        assert analysis.metadata["passes_executed"] == len(working_memory.reasoning_passes)
        assert analysis.metadata["actions_count"] == len(actions)


class TestExtractCorrectionActions:
    """Tests de extract_correction_actions"""

    def test_extract_archive_correction(self):
        """Test extraction correction 'archive'"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(
            approval=False,
            correction="Should have archived this email"
        )

        corrections = processor.extract_correction_actions(feedback)

        assert len(corrections) > 0
        assert any(c["action"] == "archive" for c in corrections if c["type"] == "action_correction")

    def test_extract_delete_correction(self):
        """Test extraction correction 'delete'"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(
            approval=False,
            correction="Please delete this email"
        )

        corrections = processor.extract_correction_actions(feedback)

        assert len(corrections) > 0
        assert any(c["action"] == "delete" for c in corrections if c["type"] == "action_correction")

    def test_extract_task_correction(self):
        """Test extraction correction 'task'"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(
            approval=False,
            correction="Create a task for this"
        )

        corrections = processor.extract_correction_actions(feedback)

        assert len(corrections) > 0
        assert any(c["action"] == "create_task" for c in corrections if c["type"] == "action_correction")

    def test_extract_modification(self):
        """Test extraction modification"""
        processor = FeedbackProcessor()

        modified_action = CreateTaskAction(name="Modified", project_name="Test")

        feedback = UserFeedback(
            approval=True,
            modification=modified_action
        )

        corrections = processor.extract_correction_actions(feedback)

        assert len(corrections) > 0
        assert any(c["type"] == "action_modification" for c in corrections)

    def test_extract_generic_correction(self):
        """Test correction générique non matchée"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(
            approval=False,
            correction="This is some generic feedback that doesn't match patterns"
        )

        corrections = processor.extract_correction_actions(feedback)

        assert len(corrections) > 0
        assert any(c["type"] == "generic_correction" for c in corrections)

    def test_no_correction(self):
        """Test sans correction"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(approval=True)

        corrections = processor.extract_correction_actions(feedback)

        assert len(corrections) == 0


class TestShouldTriggerLearning:
    """Tests de should_trigger_learning"""

    def test_trigger_on_correction(self):
        """Test trigger sur correction explicite"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(
            approval=False,
            correction="Fix this"
        )

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=0.5,
            suggested_improvements=[],
            confidence_error=0.0,
            action_quality_score=0.5,
            reasoning_quality_score=0.5
        )

        assert processor.should_trigger_learning(feedback, analysis) is True

    def test_trigger_on_modification(self):
        """Test trigger sur modification"""
        processor = FeedbackProcessor()

        modified_action = CreateTaskAction(name="Modified", project_name="Test")

        feedback = UserFeedback(
            approval=True,
            modification=modified_action
        )

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=0.8,
            suggested_improvements=[],
            confidence_error=0.0,
            action_quality_score=0.7,
            reasoning_quality_score=0.8
        )

        assert processor.should_trigger_learning(feedback, analysis) is True

    def test_trigger_on_low_correctness(self):
        """Test trigger sur faible correctness"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(approval=False)

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=0.4,  # Low
            suggested_improvements=[],
            confidence_error=0.0,
            action_quality_score=0.5,
            reasoning_quality_score=0.5
        )

        assert processor.should_trigger_learning(feedback, analysis) is True

    def test_trigger_on_high_confidence_error(self):
        """Test trigger sur erreur confiance élevée"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(approval=True, rating=5)

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=0.9,
            suggested_improvements=[],
            confidence_error=0.3,  # High error
            action_quality_score=0.9,
            reasoning_quality_score=0.9
        )

        assert processor.should_trigger_learning(feedback, analysis) is True

    def test_trigger_on_rating(self):
        """Test trigger sur rating explicite"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(approval=True, rating=4)

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=0.9,
            suggested_improvements=[],
            confidence_error=0.05,
            action_quality_score=0.9,
            reasoning_quality_score=0.9
        )

        # Should trigger car rating est explicit signal
        assert processor.should_trigger_learning(feedback, analysis) is True

    def test_no_trigger_on_perfect_confirmation(self):
        """Test pas de trigger sur confirmation parfaite"""
        processor = FeedbackProcessor()

        feedback = UserFeedback(
            approval=True,
            action_executed=True,
            time_to_action=30.0  # Fast
        )

        analysis = FeedbackAnalysis(
            feedback=feedback,
            correctness_score=0.95,  # Very high
            suggested_improvements=[],
            confidence_error=0.02,  # Very low
            action_quality_score=0.95,
            reasoning_quality_score=0.95
        )

        # Should not trigger (no new info)
        assert processor.should_trigger_learning(feedback, analysis) is False
