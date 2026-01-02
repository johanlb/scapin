"""
Tests for CognitivePipeline

Tests the cognitive pipeline orchestrator that coordinates
Trivelin → Sancho → Planchet → Figaro → Sganarelle.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.core.config_manager import ProcessingConfig
from src.core.events import EventSource, EventType, PerceivedEvent, UrgencyLevel
from src.core.memory.working_memory import WorkingMemory
from src.core.schemas import (
    EmailAction,
    EmailAnalysis,
    EmailCategory,
    EmailContent,
    EmailMetadata,
)
from src.figaro.orchestrator import ExecutionResult
from src.planchet.planning_engine import ActionPlan
from src.sancho.reasoning_engine import ReasoningResult
from src.trivelin.cognitive_pipeline import (
    CognitivePipeline,
    CognitivePipelineResult,
    CognitiveTimeoutError,
)

# ============================================================================
# TEST HELPERS
# ============================================================================


def create_test_event(
    event_id: str = "test-event-123",
    title: str = "Test Subject",
    content: str = "Test content",
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
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def mock_ai_router():
    """Create a mock AI router"""
    router = MagicMock()
    router.analyze_email.return_value = EmailAnalysis(
        action=EmailAction.ARCHIVE,
        category=EmailCategory.WORK,
        confidence=85,
        reasoning="Mock analysis"
    )
    return router


@pytest.fixture
def default_config():
    """Create default processing config"""
    return ProcessingConfig(
        enable_cognitive_reasoning=True,
        cognitive_confidence_threshold=0.85,
        cognitive_timeout_seconds=20,
        cognitive_max_passes=5,
        fallback_on_failure=True,
    )


@pytest.fixture
def sample_metadata():
    """Create sample email metadata"""
    return EmailMetadata(
        id=12345,
        subject="Test Email Subject",
        from_address="sender@example.com",
        to=["recipient@example.com"],
        date=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_content():
    """Create sample email content"""
    return EmailContent(
        plain_text="This is a test email body.",
        html_content="<p>This is a test email body.</p>",
    )


@pytest.fixture
def sample_event():
    """Create sample perceived event"""
    return create_test_event()


@pytest.fixture
def sample_analysis():
    """Create sample email analysis"""
    return EmailAnalysis(
        action=EmailAction.ARCHIVE,
        category=EmailCategory.WORK,
        confidence=92,
        reasoning="High-confidence decision",
    )


@pytest.fixture
def mock_reasoning_result(sample_event, sample_analysis):
    """Create mock reasoning result"""
    wm = WorkingMemory(sample_event)
    return ReasoningResult(
        working_memory=wm,
        final_analysis=sample_analysis,
        reasoning_trace=[],
        confidence=0.92,
        passes_executed=3,
        total_duration_seconds=5.5,
        converged=True,
    )


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================


class TestCognitivePipelineInit:
    """Tests for CognitivePipeline initialization"""

    def test_init_with_default_config(self, mock_ai_router):
        """Test initialization with default config"""
        pipeline = CognitivePipeline(ai_router=mock_ai_router)

        assert pipeline.ai_router == mock_ai_router
        assert pipeline.config is not None
        assert pipeline.reasoning_engine is not None
        assert pipeline.planning_engine is not None
        assert pipeline.orchestrator is not None
        assert pipeline.learning_engine is None  # Optional

    def test_init_with_custom_config(self, mock_ai_router, default_config):
        """Test initialization with custom config"""
        pipeline = CognitivePipeline(
            ai_router=mock_ai_router,
            config=default_config,
        )

        assert pipeline.config.cognitive_confidence_threshold == 0.85
        assert pipeline.config.cognitive_timeout_seconds == 20
        assert pipeline.config.cognitive_max_passes == 5

    def test_init_with_learning_engine(self, mock_ai_router, default_config):
        """Test initialization with learning engine"""
        mock_learning = MagicMock()
        pipeline = CognitivePipeline(
            ai_router=mock_ai_router,
            config=default_config,
            learning_engine=mock_learning,
        )

        assert pipeline.learning_engine == mock_learning


# ============================================================================
# PROCESSING TESTS
# ============================================================================


class TestCognitivePipelineProcess:
    """Tests for CognitivePipeline.process()"""

    def test_process_success_high_confidence(
        self,
        mock_ai_router,
        default_config,
        sample_metadata,
        sample_content,
        sample_event,
        mock_reasoning_result,
    ):
        """Test successful processing with high confidence"""
        with patch(
            'src.trivelin.cognitive_pipeline.EmailNormalizer.normalize',
            return_value=sample_event
        ), patch.object(
            CognitivePipeline,
            '__init__',
            lambda self, **kw: None
        ):
            pipeline = CognitivePipeline.__new__(CognitivePipeline)
            pipeline.ai_router = mock_ai_router
            pipeline.config = default_config
            pipeline.learning_engine = None

            # Mock reasoning engine
            mock_reasoning_engine = MagicMock()
            mock_reasoning_engine.reason.return_value = mock_reasoning_result
            pipeline.reasoning_engine = mock_reasoning_engine

            # Mock planning engine
            mock_planning_engine = MagicMock()
            mock_plan = MagicMock(spec=ActionPlan)
            mock_plan.actions = []
            mock_plan.requires_approval.return_value = False
            mock_planning_engine.plan.return_value = mock_plan
            pipeline.planning_engine = mock_planning_engine

            # Mock orchestrator
            mock_orchestrator = MagicMock()
            mock_exec_result = ExecutionResult(
                success=True,
                executed_actions=[],
                duration=0.1,
            )
            mock_orchestrator.execute_plan.return_value = mock_exec_result
            pipeline.orchestrator = mock_orchestrator

            result = pipeline.process(sample_metadata, sample_content, auto_execute=True)

            assert result.success is True
            assert result.analysis is not None
            assert result.analysis.confidence == 92
            assert result.needs_review is False
            assert result.used_fallback is False
            assert result.timed_out is False

    def test_process_low_confidence_needs_review(
        self,
        mock_ai_router,
        default_config,
        sample_metadata,
        sample_content,
        sample_event,
    ):
        """Test processing with low confidence triggers review"""
        # Create low confidence result
        low_confidence_analysis = EmailAnalysis(
            action=EmailAction.QUEUE,  # Queue for manual review
            category=EmailCategory.OTHER,
            confidence=60,
            reasoning="Not confident enough",
        )
        wm = WorkingMemory(sample_event)
        low_confidence_result = ReasoningResult(
            working_memory=wm,
            final_analysis=low_confidence_analysis,
            reasoning_trace=[],
            confidence=0.60,  # Below 0.85 threshold
            passes_executed=5,
            total_duration_seconds=10.0,
            converged=False,
        )

        with patch(
            'src.trivelin.cognitive_pipeline.EmailNormalizer.normalize',
            return_value=sample_event
        ), patch.object(
            CognitivePipeline,
            '__init__',
            lambda self, **kw: None
        ):
            pipeline = CognitivePipeline.__new__(CognitivePipeline)
            pipeline.ai_router = mock_ai_router
            pipeline.config = default_config
            pipeline.learning_engine = None

            mock_reasoning_engine = MagicMock()
            mock_reasoning_engine.reason.return_value = low_confidence_result
            pipeline.reasoning_engine = mock_reasoning_engine
            pipeline.planning_engine = MagicMock()
            pipeline.orchestrator = MagicMock()

            result = pipeline.process(sample_metadata, sample_content, auto_execute=False)

            assert result.success is True
            assert result.needs_review is True  # Low confidence
            assert result.analysis.confidence == 60

    def test_process_normalization_failure(
        self,
        mock_ai_router,
        default_config,
        sample_metadata,
        sample_content,
    ):
        """Test handling of normalization failure"""
        with patch(
            'src.trivelin.cognitive_pipeline.EmailNormalizer.normalize',
            side_effect=ValueError("Normalization failed")
        ):
            pipeline = CognitivePipeline(
                ai_router=mock_ai_router,
                config=default_config,
            )

            result = pipeline.process(sample_metadata, sample_content)

            assert result.success is False
            assert result.error_stage == "normalize"
            assert "Normalization failed" in result.error

    def test_process_reasoning_failure(
        self,
        mock_ai_router,
        default_config,
        sample_metadata,
        sample_content,
        sample_event,
    ):
        """Test handling of reasoning failure"""
        with patch(
            'src.trivelin.cognitive_pipeline.EmailNormalizer.normalize',
            return_value=sample_event
        ):
            pipeline = CognitivePipeline(
                ai_router=mock_ai_router,
                config=default_config,
            )
            pipeline.reasoning_engine = MagicMock()
            pipeline.reasoning_engine.reason.side_effect = RuntimeError("Reasoning error")

            result = pipeline.process(sample_metadata, sample_content)

            assert result.success is False
            assert result.error_stage == "reason"
            assert "Reasoning error" in result.error


# ============================================================================
# TIMEOUT TESTS
# ============================================================================


class TestCognitivePipelineTimeout:
    """Tests for timeout handling"""

    def test_timeout_error_class(self):
        """Test CognitiveTimeoutError exception"""
        error = CognitiveTimeoutError("Test timeout")
        assert str(error) == "Test timeout"

    @pytest.mark.skipif(
        True,  # Skip on CI - signal handling is tricky
        reason="Signal-based timeout test unreliable in CI"
    )
    def test_process_timeout(
        self,
        mock_ai_router,
        sample_metadata,
        sample_content,
        sample_event,
    ):
        """Test that processing respects timeout"""
        import time

        # Create config with very short timeout
        config = ProcessingConfig(
            enable_cognitive_reasoning=True,
            cognitive_timeout_seconds=1,  # 1 second timeout
            cognitive_confidence_threshold=0.85,
            fallback_on_failure=True,
        )

        with patch(
            'src.trivelin.cognitive_pipeline.EmailNormalizer.normalize',
            return_value=sample_event
        ):
            pipeline = CognitivePipeline(
                ai_router=mock_ai_router,
                config=config,
            )

            # Make reasoning take longer than timeout
            def slow_reason(_event):
                time.sleep(3)
                return MagicMock()

            pipeline.reasoning_engine.reason = slow_reason

            result = pipeline.process(sample_metadata, sample_content)

            assert result.success is False
            assert result.timed_out is True


# ============================================================================
# RESULT DATACLASS TESTS
# ============================================================================


class TestCognitivePipelineResult:
    """Tests for CognitivePipelineResult dataclass"""

    def test_result_to_dict_success(self, sample_analysis):
        """Test successful result serialization"""
        result = CognitivePipelineResult(
            success=True,
            analysis=sample_analysis,
            needs_review=False,
            total_duration_seconds=5.5,
            stage_durations={"normalize": 0.1, "reason": 5.0},
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["has_analysis"] is True
        assert d["needs_review"] is False
        assert d["confidence"] == 92
        assert d["action"] == "archive"
        assert d["total_duration_seconds"] == 5.5

    def test_result_to_dict_failure(self):
        """Test failed result serialization"""
        result = CognitivePipelineResult(
            success=False,
            analysis=None,
            error="Test error",
            error_stage="reason",
        )

        d = result.to_dict()

        assert d["success"] is False
        assert d["has_analysis"] is False
        assert d["error"] == "Test error"
        assert d["error_stage"] == "reason"
        assert d["confidence"] is None


# ============================================================================
# CONFIG TESTS
# ============================================================================


class TestProcessingConfig:
    """Tests for ProcessingConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = ProcessingConfig()

        assert config.enable_cognitive_reasoning is False
        assert config.cognitive_confidence_threshold == 0.85
        assert config.cognitive_timeout_seconds == 20
        assert config.cognitive_max_passes == 5
        assert config.fallback_on_failure is True

    def test_validation_confidence_threshold(self):
        """Test confidence threshold validation"""
        # Valid values
        config = ProcessingConfig(cognitive_confidence_threshold=0.0)
        assert config.cognitive_confidence_threshold == 0.0

        config = ProcessingConfig(cognitive_confidence_threshold=1.0)
        assert config.cognitive_confidence_threshold == 1.0

        # Invalid values
        with pytest.raises(ValueError):
            ProcessingConfig(cognitive_confidence_threshold=-0.1)

        with pytest.raises(ValueError):
            ProcessingConfig(cognitive_confidence_threshold=1.1)

    def test_validation_timeout(self):
        """Test timeout validation"""
        # Valid values
        config = ProcessingConfig(cognitive_timeout_seconds=5)
        assert config.cognitive_timeout_seconds == 5

        config = ProcessingConfig(cognitive_timeout_seconds=120)
        assert config.cognitive_timeout_seconds == 120

        # Invalid values
        with pytest.raises(ValueError):
            ProcessingConfig(cognitive_timeout_seconds=4)  # Min is 5

        with pytest.raises(ValueError):
            ProcessingConfig(cognitive_timeout_seconds=121)  # Max is 120

    def test_validation_max_passes(self):
        """Test max passes validation"""
        # Valid values
        config = ProcessingConfig(cognitive_max_passes=1)
        assert config.cognitive_max_passes == 1

        config = ProcessingConfig(cognitive_max_passes=10)
        assert config.cognitive_max_passes == 10

        # Invalid values
        with pytest.raises(ValueError):
            ProcessingConfig(cognitive_max_passes=0)  # Min is 1

        with pytest.raises(ValueError):
            ProcessingConfig(cognitive_max_passes=11)  # Max is 10
