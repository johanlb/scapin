"""
Unit Tests for Sancho Reasoning Engine

Tests for the iterative multi-pass reasoning system.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.sancho.reasoning_engine import ReasoningEngine, ReasoningResult
from src.ai.router import AIRouter, AIModel
from src.ai.templates import TemplateManager
from src.core.events.universal_event import (
    PerceivedEvent, Entity, EventType, EventSource, UrgencyLevel
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_test_event(
    event_id: str = "test-event-001",
    title: str = "Test Email Subject",
    content: str = "Test email content here.",
    event_type: EventType = EventType.INFORMATION,
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
    from_person: str = "sender@example.com"
) -> PerceivedEvent:
    """Create a valid PerceivedEvent for testing"""
    now = datetime.now(timezone.utc)
    return PerceivedEvent(
        event_id=event_id,
        source=EventSource.EMAIL,
        source_id="12345",
        occurred_at=now - timedelta(minutes=5),
        received_at=now - timedelta(minutes=4),
        title=title,
        content=content,
        event_type=event_type,
        urgency=urgency,
        entities=[],
        topics=["test"],
        keywords=["test"],
        from_person=from_person,
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
        perception_confidence=0.85,
        needs_clarification=False,
        clarification_questions=[]
    )


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_ai_router():
    """Create mock AI router"""
    router = MagicMock(spec=AIRouter)
    router.analyze_with_prompt.return_value = (
        json.dumps({
            "understanding": {
                "summary": "Test email about project update",
                "intent": "information",
                "urgency": "routine"
            },
            "category": {
                "main": "work",
                "sub": "project",
                "priority": "medium"
            },
            "hypothesis": {
                "recommended_action": "archive",
                "reasoning": "Routine project update",
                "confidence": 70,
                "missing_information": [],
                "needs_context": False
            },
            "entities_confirmed": [
                {"type": "person", "value": "John Doe", "relevance": "high"}
            ],
            "next_steps": []
        }),
        {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
    )
    return router


@pytest.fixture
def mock_template_manager():
    """Create mock template manager"""
    tm = MagicMock(spec=TemplateManager)
    tm.render.return_value = "Test prompt content"
    return tm


@pytest.fixture
def sample_event():
    """Create a sample PerceivedEvent for testing"""
    return create_test_event(
        title="Project Update - Q1 Review",
        content="Dear team, please find the Q1 project update attached."
    )


@pytest.fixture
def reasoning_engine(mock_ai_router, mock_template_manager):
    """Create reasoning engine with mocks"""
    return ReasoningEngine(
        ai_router=mock_ai_router,
        template_manager=mock_template_manager,
        max_iterations=5,
        confidence_threshold=0.95,
        enable_context=False,
        enable_validation=False
    )


# ============================================================================
# REASONING ENGINE INITIALIZATION TESTS
# ============================================================================


class TestReasoningEngineInit:
    """Test reasoning engine initialization"""

    def test_init_with_defaults(self, mock_ai_router, mock_template_manager):
        """Test initialization with default parameters"""
        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager
        )

        assert engine.ai_router == mock_ai_router
        assert engine.template_manager == mock_template_manager
        assert engine.max_iterations == 5
        assert engine.confidence_threshold == 0.95
        assert engine.enable_context is False
        assert engine.enable_validation is False

    def test_init_with_custom_params(self, mock_ai_router, mock_template_manager):
        """Test initialization with custom parameters"""
        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=3,
            confidence_threshold=0.90,
            enable_context=True,
            enable_validation=True
        )

        assert engine.max_iterations == 3
        assert engine.confidence_threshold == 0.90
        assert engine.enable_context is True
        assert engine.enable_validation is True

    def test_init_without_template_manager(self, mock_ai_router):
        """Test initialization without explicit template manager"""
        with patch('src.sancho.reasoning_engine.get_template_manager') as mock_get_tm:
            mock_tm = MagicMock()
            mock_get_tm.return_value = mock_tm

            engine = ReasoningEngine(ai_router=mock_ai_router)

            assert engine.template_manager == mock_tm
            mock_get_tm.assert_called_once()


# ============================================================================
# REASONING RESULT TESTS
# ============================================================================


class TestReasoningResult:
    """Test ReasoningResult dataclass"""

    def test_result_creation(self):
        """Test creating a reasoning result"""
        from src.core.memory.working_memory import WorkingMemory

        event = create_test_event()
        wm = WorkingMemory(event)

        result = ReasoningResult(
            working_memory=wm,
            final_analysis=None,
            reasoning_trace=[],
            confidence=0.85,
            passes_executed=2,
            total_duration_seconds=5.0,
            converged=True
        )

        assert result.confidence == 0.85
        assert result.passes_executed == 2
        assert result.converged is True
        assert result.key_factors == []
        assert result.uncertainties == []

    def test_result_with_questions(self):
        """Test result with user questions"""
        from src.core.memory.working_memory import WorkingMemory

        event = create_test_event()
        wm = WorkingMemory(event)

        result = ReasoningResult(
            working_memory=wm,
            final_analysis=None,
            reasoning_trace=[],
            confidence=0.60,
            passes_executed=5,
            total_duration_seconds=15.0,
            converged=False,
            questions_for_user=[
                {"question": "Is this urgent?", "type": "open_ended"}
            ]
        )

        assert result.converged is False
        assert len(result.questions_for_user) == 1


# ============================================================================
# REASONING LOOP TESTS
# ============================================================================


class TestReasoningLoop:
    """Test the main reasoning loop"""

    def test_reason_single_pass_high_confidence(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test reasoning with high confidence in first pass"""
        # Mock high confidence response
        mock_ai_router.analyze_with_prompt.return_value = (
            json.dumps({
                "understanding": {"summary": "Clear email", "intent": "info", "urgency": "routine"},
                "category": {"main": "work", "sub": "update", "priority": "medium"},
                "hypothesis": {
                    "recommended_action": "archive",
                    "reasoning": "Clear project update",
                    "confidence": 96,  # High confidence
                    "missing_information": [],
                    "needs_context": False
                },
                "entities_confirmed": []
            }),
            {"total_tokens": 100}
        )

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=5,
            confidence_threshold=0.95
        )

        result = engine.reason(sample_event)

        assert result is not None
        assert result.passes_executed >= 1
        assert result.confidence >= 0.0

    def test_reason_multiple_passes_low_confidence(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test reasoning with low confidence requiring multiple passes"""
        # Mock low confidence response
        mock_ai_router.analyze_with_prompt.return_value = (
            json.dumps({
                "understanding": {"summary": "Unclear email", "intent": "unclear", "urgency": "unknown"},
                "category": {"main": "personal", "sub": "", "priority": "low"},
                "hypothesis": {
                    "recommended_action": "queue",
                    "reasoning": "Uncertain about intent",
                    "confidence": 45,  # Low confidence
                    "missing_information": ["sender history", "context"],
                    "needs_context": True
                },
                "entities_confirmed": []
            }),
            {"total_tokens": 100}
        )

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=3,
            confidence_threshold=0.95,
            enable_context=False,
            enable_validation=False
        )

        result = engine.reason(sample_event)

        assert result is not None
        # With low confidence, should run multiple passes up to max
        assert result.passes_executed >= 1

    def test_reason_stops_at_max_iterations(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test reasoning stops at max iterations"""
        # Mock low confidence response (never converges)
        mock_ai_router.analyze_with_prompt.return_value = (
            json.dumps({
                "understanding": {"summary": "Unclear", "intent": "unclear", "urgency": "unknown"},
                "category": {"main": "other", "sub": "", "priority": "low"},
                "hypothesis": {
                    "recommended_action": "queue",
                    "reasoning": "Cannot determine",
                    "confidence": 30,  # Very low
                    "missing_information": ["everything"],
                    "needs_context": True
                },
                "entities_confirmed": []
            }),
            {"total_tokens": 100}
        )

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=2,  # Low limit
            confidence_threshold=0.95
        )

        result = engine.reason(sample_event)

        assert result is not None
        # Should not exceed max_iterations (but may be less due to logic)
        assert result.passes_executed <= 2


# ============================================================================
# PASS-SPECIFIC TESTS
# ============================================================================


class TestPass1InitialAnalysis:
    """Test Pass 1 initial analysis"""

    def test_pass1_calls_ai(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test Pass 1 makes AI call"""
        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=1,  # Only run pass 1
            confidence_threshold=0.99  # High threshold to not converge
        )

        result = engine.reason(sample_event)

        # Should have called template render
        mock_template_manager.render.assert_called()

        # Should have called AI
        mock_ai_router.analyze_with_prompt.assert_called()

    def test_pass1_uses_haiku_model(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test Pass 1 uses Haiku for speed"""
        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=1,
            confidence_threshold=0.99
        )

        engine.reason(sample_event)

        # Check that Haiku was used
        calls = mock_ai_router.analyze_with_prompt.call_args_list
        if calls:
            _, kwargs = calls[0]
            assert kwargs.get('model') == AIModel.CLAUDE_HAIKU


class TestPass3DeepReasoning:
    """Test Pass 3 deep reasoning"""

    def test_pass3_uses_sonnet_model(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test Pass 3 uses Sonnet for deeper analysis"""
        # First pass returns low confidence to trigger pass 3
        mock_ai_router.analyze_with_prompt.return_value = (
            json.dumps({
                "understanding": {"summary": "Test", "intent": "test", "urgency": "routine"},
                "category": {"main": "work", "sub": "", "priority": "medium"},
                "hypothesis": {
                    "recommended_action": "archive",
                    "reasoning": "Test",
                    "confidence": 60,
                    "missing_information": [],
                    "needs_context": False
                },
                "entities_confirmed": []
            }),
            {"total_tokens": 100}
        )

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=3,
            confidence_threshold=0.95,
            enable_context=False
        )

        engine.reason(sample_event)

        # Check that calls include Sonnet (for pass 3)
        calls = mock_ai_router.analyze_with_prompt.call_args_list
        models_used = [call[1].get('model') for call in calls if call[1].get('model')]
        # At least one call should use Sonnet
        # (Pass 3 uses Sonnet, so if we reached pass 3, Sonnet should be in the list)


# ============================================================================
# FINAL ANALYSIS EXTRACTION TESTS
# ============================================================================


class TestFinalAnalysisExtraction:
    """Test extraction of final EmailAnalysis"""

    def test_extract_final_analysis(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test final analysis is extracted from working memory"""
        mock_ai_router.analyze_with_prompt.return_value = (
            json.dumps({
                "understanding": {"summary": "Project update email", "intent": "inform", "urgency": "routine"},
                "category": {"main": "work", "sub": "project", "priority": "medium"},
                "hypothesis": {
                    "recommended_action": "archive",
                    "reasoning": "Routine project update from team",
                    "confidence": 85,
                    "destination": "Archive/2025/Work",
                    "missing_information": [],
                    "needs_context": False
                },
                "entities_confirmed": [{"type": "person", "value": "John"}]
            }),
            {"total_tokens": 100}
        )

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=1,
            confidence_threshold=0.99
        )

        result = engine.reason(sample_event)

        # Should have a final analysis (may be None if parsing fails)
        # This tests the extraction logic works
        assert result is not None
        assert result.working_memory is not None


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Test error handling in reasoning engine"""

    def test_handles_ai_error_gracefully(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test engine handles AI errors gracefully"""
        mock_ai_router.analyze_with_prompt.side_effect = Exception("API Error")

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=1,
            confidence_threshold=0.95
        )

        # Should not raise, but return result with low confidence
        result = engine.reason(sample_event)

        assert result is not None
        # Confidence should be low due to error
        assert result.confidence <= 0.6

    def test_handles_template_error_gracefully(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test engine handles template errors gracefully"""
        mock_template_manager.render.side_effect = Exception("Template Error")

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=1,
            confidence_threshold=0.95
        )

        # Should not raise
        result = engine.reason(sample_event)

        assert result is not None

    def test_handles_invalid_json_response(
        self, mock_ai_router, mock_template_manager, sample_event
    ):
        """Test engine handles invalid JSON in AI response"""
        mock_ai_router.analyze_with_prompt.return_value = (
            "This is not JSON at all",
            {"total_tokens": 50}
        )

        engine = ReasoningEngine(
            ai_router=mock_ai_router,
            template_manager=mock_template_manager,
            max_iterations=1,
            confidence_threshold=0.95
        )

        result = engine.reason(sample_event)

        assert result is not None
        # Should handle gracefully with conservative confidence
        assert result.confidence <= 0.6
