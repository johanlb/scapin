"""
Tests for Working Memory

Tests WorkingMemory, Hypothesis, ReasoningPass, ContextItem, and MemoryState.
"""

import pytest
from datetime import datetime, timedelta
from src.core.memory import (
    WorkingMemory,
    MemoryState,
    Hypothesis,
    ReasoningPass,
    ContextItem,
)
from src.core.events import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
)
from src.utils import now_utc


@pytest.fixture
def sample_event():
    """Create a sample perceived event for testing"""
    now = now_utc()
    return PerceivedEvent(
        event_id="test_event_123",
        source=EventSource.EMAIL,
        source_id="email_456",
        occurred_at=now,
        received_at=now,
        perceived_at=now,
        title="Test Email",
        content="Test content for working memory",
        event_type=EventType.ACTION_REQUIRED,
        urgency=UrgencyLevel.MEDIUM,
        entities=[],
        topics=["testing"],
        keywords=["test"],
        from_person="sender@example.com",
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
        perception_confidence=0.75,
        needs_clarification=False,
        clarification_questions=[],
        summary=None
    )


class TestHypothesis:
    """Tests for Hypothesis dataclass"""

    def test_hypothesis_creation(self):
        """Test creating a hypothesis"""
        hyp = Hypothesis(
            id="hyp_1",
            description="Email requires immediate response",
            confidence=0.85,
            supporting_evidence=["Urgent keyword in subject"],
            contradicting_evidence=[]
        )

        assert hyp.id == "hyp_1"
        assert hyp.description == "Email requires immediate response"
        assert hyp.confidence == 0.85
        assert len(hyp.supporting_evidence) == 1

    def test_hypothesis_confidence_validation(self):
        """Test hypothesis confidence must be 0.0-1.0"""
        # Valid confidence
        hyp = Hypothesis(
            id="hyp_1",
            description="Test",
            confidence=0.5
        )
        assert hyp.confidence == 0.5

        # Invalid confidence
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            Hypothesis(id="hyp_2", description="Test", confidence=1.5)

        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            Hypothesis(id="hyp_3", description="Test", confidence=-0.1)

    def test_add_supporting_evidence(self):
        """Test adding supporting evidence"""
        hyp = Hypothesis(id="hyp_1", description="Test", confidence=0.5)

        hyp.add_evidence("Evidence 1", supporting=True)
        hyp.add_evidence("Evidence 2", supporting=True)

        assert len(hyp.supporting_evidence) == 2
        assert "Evidence 1" in hyp.supporting_evidence
        assert "Evidence 2" in hyp.supporting_evidence

    def test_add_contradicting_evidence(self):
        """Test adding contradicting evidence"""
        hyp = Hypothesis(id="hyp_1", description="Test", confidence=0.8)

        hyp.add_evidence("Counter evidence", supporting=False)

        assert len(hyp.contradicting_evidence) == 1
        assert "Counter evidence" in hyp.contradicting_evidence

    def test_update_confidence(self):
        """Test updating confidence"""
        hyp = Hypothesis(id="hyp_1", description="Test", confidence=0.5)

        hyp.update_confidence(0.75)
        assert hyp.confidence == 0.75

        # Invalid update
        with pytest.raises(ValueError):
            hyp.update_confidence(1.2)


class TestReasoningPass:
    """Tests for ReasoningPass dataclass"""

    def test_reasoning_pass_creation(self):
        """Test creating a reasoning pass"""
        pass_obj = ReasoningPass(
            pass_number=1,
            pass_type="initial_analysis",
            input_confidence=0.5,
            input_hypotheses_count=0
        )

        assert pass_obj.pass_number == 1
        assert pass_obj.pass_type == "initial_analysis"
        assert pass_obj.input_confidence == 0.5
        assert pass_obj.completed_at is None

    def test_reasoning_pass_complete(self):
        """Test completing a reasoning pass"""
        pass_obj = ReasoningPass(
            pass_number=1,
            pass_type="initial_analysis",
            input_confidence=0.5,
            input_hypotheses_count=0
        )

        pass_obj.output_confidence = 0.7
        pass_obj.output_hypotheses_count = 2
        pass_obj.complete()

        assert pass_obj.completed_at is not None
        assert pass_obj.duration_seconds is not None
        assert pass_obj.confidence_delta == pytest.approx(0.2)  # 0.7 - 0.5

    def test_reasoning_pass_insights(self):
        """Test adding insights to reasoning pass"""
        pass_obj = ReasoningPass(
            pass_number=1,
            pass_type="deep_reasoning"
        )

        pass_obj.insights.append("Found urgent keywords")
        pass_obj.insights.append("Identified action required")
        pass_obj.questions_raised.append("What is the deadline?")

        assert len(pass_obj.insights) == 2
        assert len(pass_obj.questions_raised) == 1


class TestContextItem:
    """Tests for ContextItem dataclass"""

    def test_context_item_creation(self):
        """Test creating a context item"""
        item = ContextItem(
            source="pkm",
            type="note",
            content="Related note about the topic",
            relevance_score=0.85
        )

        assert item.source == "pkm"
        assert item.type == "note"
        assert item.relevance_score == 0.85
        assert item.retrieved_at is not None


class TestWorkingMemoryInitialization:
    """Tests for WorkingMemory initialization"""

    def test_working_memory_creation(self, sample_event):
        """Test creating working memory with event"""
        wm = WorkingMemory(sample_event)

        assert wm.event == sample_event
        assert wm.state == MemoryState.INITIALIZED
        assert wm.overall_confidence == sample_event.perception_confidence
        assert len(wm.hypotheses) == 0
        assert len(wm.reasoning_passes) == 0
        assert wm.is_continuous is False

    def test_working_memory_initial_confidence(self, sample_event):
        """Test initial confidence comes from event"""
        # Events are immutable, use dataclasses.replace to create new event
        from dataclasses import replace
        modified_event = replace(sample_event, perception_confidence=0.85)
        wm = WorkingMemory(modified_event)

        assert wm.overall_confidence == 0.85


class TestWorkingMemoryHypotheses:
    """Tests for hypothesis management in working memory"""

    def test_add_hypothesis(self, sample_event):
        """Test adding hypotheses"""
        wm = WorkingMemory(sample_event)

        hyp1 = Hypothesis(id="hyp_1", description="Requires urgent action", confidence=0.8)
        hyp2 = Hypothesis(id="hyp_2", description="Informational only", confidence=0.3)

        wm.add_hypothesis(hyp1)
        wm.add_hypothesis(hyp2)

        assert len(wm.hypotheses) == 2
        assert wm.hypotheses["hyp_1"] == hyp1
        assert wm.hypotheses["hyp_2"] == hyp2

    def test_current_best_hypothesis(self, sample_event):
        """Test current best hypothesis is tracked"""
        wm = WorkingMemory(sample_event)

        hyp1 = Hypothesis(id="hyp_1", description="Low confidence", confidence=0.3)
        hyp2 = Hypothesis(id="hyp_2", description="High confidence", confidence=0.9)

        wm.add_hypothesis(hyp1)
        assert wm.current_best_hypothesis == hyp1

        wm.add_hypothesis(hyp2)
        assert wm.current_best_hypothesis == hyp2

    def test_get_hypothesis(self, sample_event):
        """Test retrieving hypothesis by ID"""
        wm = WorkingMemory(sample_event)

        hyp = Hypothesis(id="hyp_123", description="Test", confidence=0.7)
        wm.add_hypothesis(hyp)

        retrieved = wm.get_hypothesis("hyp_123")
        assert retrieved == hyp

        not_found = wm.get_hypothesis("nonexistent")
        assert not_found is None

    def test_get_top_hypotheses(self, sample_event):
        """Test getting top N hypotheses"""
        wm = WorkingMemory(sample_event)

        hyps = [
            Hypothesis(id=f"hyp_{i}", description=f"Hypothesis {i}", confidence=i*0.1)
            for i in range(1, 6)
        ]

        for hyp in hyps:
            wm.add_hypothesis(hyp)

        top_3 = wm.get_top_hypotheses(n=3)
        assert len(top_3) == 3
        # Should be sorted by confidence descending
        assert top_3[0].confidence >= top_3[1].confidence >= top_3[2].confidence


class TestWorkingMemoryReasoningPasses:
    """Tests for reasoning pass management"""

    def test_start_reasoning_pass(self, sample_event):
        """Test starting a reasoning pass"""
        wm = WorkingMemory(sample_event)

        pass_obj = wm.start_reasoning_pass(1, "initial_analysis")

        assert wm.current_pass == pass_obj
        assert wm.state == MemoryState.REASONING
        assert pass_obj.input_confidence == wm.overall_confidence

    def test_complete_reasoning_pass(self, sample_event):
        """Test completing a reasoning pass"""
        wm = WorkingMemory(sample_event)

        wm.start_reasoning_pass(1, "initial_analysis")
        wm.update_confidence(0.85)

        wm.complete_reasoning_pass()

        assert wm.current_pass is None
        assert len(wm.reasoning_passes) == 1
        assert wm.reasoning_passes[0].output_confidence == 0.85

    def test_multiple_reasoning_passes(self, sample_event):
        """Test multiple reasoning passes"""
        wm = WorkingMemory(sample_event)

        # Pass 1
        wm.start_reasoning_pass(1, "initial_analysis")
        wm.update_confidence(0.6)
        wm.complete_reasoning_pass()

        # Pass 2
        wm.start_reasoning_pass(2, "context_enrichment")
        wm.update_confidence(0.75)
        wm.complete_reasoning_pass()

        # Pass 3
        wm.start_reasoning_pass(3, "deep_reasoning")
        wm.update_confidence(0.9)
        wm.complete_reasoning_pass()

        assert len(wm.reasoning_passes) == 3
        assert wm.reasoning_passes[0].pass_number == 1
        assert wm.reasoning_passes[1].pass_number == 2
        assert wm.reasoning_passes[2].pass_number == 3


class TestWorkingMemoryContext:
    """Tests for context management"""

    def test_add_context(self, sample_event):
        """Test adding context items"""
        wm = WorkingMemory(sample_event)

        ctx1 = ContextItem(source="pkm", type="note", content="Related note", relevance_score=0.9)
        ctx2 = ContextItem(source="web", type="article", content="Article", relevance_score=0.7)

        wm.add_context(ctx1)
        wm.add_context(ctx2)

        assert len(wm.context_items) == 2

    def test_add_context_simple(self, sample_event):
        """Test simplified context addition interface"""
        wm = WorkingMemory(sample_event)

        wm.add_context_simple(
            source="pkm",
            type="note",
            content="Test note",
            relevance=0.85
        )

        assert len(wm.context_items) == 1
        assert wm.context_items[0].relevance_score == 0.85

    def test_get_context_by_source(self, sample_event):
        """Test filtering context by source"""
        wm = WorkingMemory(sample_event)

        wm.add_context_simple("pkm", "note", "Note 1", 0.9)
        wm.add_context_simple("pkm", "note", "Note 2", 0.8)
        wm.add_context_simple("web", "article", "Article", 0.7)

        pkm_context = wm.get_context_by_source("pkm")
        assert len(pkm_context) == 2

        web_context = wm.get_context_by_source("web")
        assert len(web_context) == 1

    def test_get_top_context(self, sample_event):
        """Test getting top N most relevant context"""
        wm = WorkingMemory(sample_event)

        for i in range(10):
            wm.add_context_simple("pkm", "note", f"Note {i}", relevance=i*0.1)

        top_5 = wm.get_top_context(n=5)
        assert len(top_5) == 5
        # Should be sorted by relevance descending
        assert top_5[0].relevance_score >= top_5[1].relevance_score


class TestWorkingMemoryQuestions:
    """Tests for question and uncertainty management"""

    def test_add_question(self, sample_event):
        """Test adding open questions"""
        wm = WorkingMemory(sample_event)

        wm.add_question("What is the deadline?")
        wm.add_question("Who should be cc'd?")

        assert len(wm.open_questions) == 2
        assert "What is the deadline?" in wm.open_questions

    def test_add_question_deduplication(self, sample_event):
        """Test questions are deduplicated"""
        wm = WorkingMemory(sample_event)

        wm.add_question("Same question")
        wm.add_question("Same question")

        assert len(wm.open_questions) == 1

    def test_add_uncertainty(self, sample_event):
        """Test adding uncertainties"""
        wm = WorkingMemory(sample_event)

        wm.add_uncertainty("Unclear if this is urgent")
        wm.add_uncertainty("Ambiguous recipient list")

        assert len(wm.uncertainties) == 2

    def test_add_uncertainty_deduplication(self, sample_event):
        """Test uncertainties are deduplicated"""
        wm = WorkingMemory(sample_event)

        wm.add_uncertainty("Same uncertainty")
        wm.add_uncertainty("Same uncertainty")

        assert len(wm.uncertainties) == 1


class TestWorkingMemoryConfidence:
    """Tests for confidence management"""

    def test_update_confidence(self, sample_event):
        """Test updating overall confidence"""
        wm = WorkingMemory(sample_event)
        initial_confidence = wm.overall_confidence

        wm.update_confidence(0.85)

        assert wm.overall_confidence == 0.85
        assert wm.overall_confidence != initial_confidence

    def test_update_confidence_validation(self, sample_event):
        """Test confidence validation"""
        wm = WorkingMemory(sample_event)

        # Valid updates
        wm.update_confidence(0.0)
        wm.update_confidence(1.0)
        wm.update_confidence(0.5)

        # Invalid updates
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            wm.update_confidence(1.5)

        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            wm.update_confidence(-0.1)

    def test_is_confident(self, sample_event):
        """Test confidence threshold checking"""
        wm = WorkingMemory(sample_event)

        wm.update_confidence(0.96)
        assert wm.is_confident(threshold=0.95) is True

        wm.update_confidence(0.85)
        assert wm.is_confident(threshold=0.95) is False

    def test_needs_more_reasoning(self, sample_event):
        """Test determining if more reasoning is needed"""
        wm = WorkingMemory(sample_event)

        # Low confidence, no passes - needs more
        wm.update_confidence(0.6)
        assert wm.needs_more_reasoning(threshold=0.95, max_passes=5) is True

        # High confidence - doesn't need more
        wm.update_confidence(0.96)
        assert wm.needs_more_reasoning(threshold=0.95, max_passes=5) is False

        # Max passes reached
        wm.update_confidence(0.7)
        for i in range(5):
            wm.start_reasoning_pass(i+1, "test")
            wm.complete_reasoning_pass()

        assert wm.needs_more_reasoning(threshold=0.95, max_passes=5) is False


class TestWorkingMemoryContinuity:
    """Tests for conversation continuity tracking"""

    def test_set_continuous(self, sample_event):
        """Test marking memory as continuous"""
        wm = WorkingMemory(sample_event)

        previous_events = [sample_event]  # Simplified
        wm.set_continuous("conversation_123", previous_events)

        assert wm.is_continuous is True
        assert wm.conversation_id == "conversation_123"
        assert len(wm.previous_events) == 1


class TestWorkingMemorySummary:
    """Tests for summary and serialization"""

    def test_get_reasoning_summary(self, sample_event):
        """Test getting reasoning summary"""
        wm = WorkingMemory(sample_event)

        # Add some state
        wm.start_reasoning_pass(1, "initial")
        wm.update_confidence(0.8)
        wm.complete_reasoning_pass()

        wm.start_reasoning_pass(2, "deep")
        wm.update_confidence(0.9)
        wm.complete_reasoning_pass()

        wm.add_hypothesis(Hypothesis(id="hyp_1", description="Test", confidence=0.85))
        wm.add_context_simple("pkm", "note", "Context", 0.9)
        wm.add_question("Question?")
        wm.add_uncertainty("Uncertain")

        summary = wm.get_reasoning_summary()

        assert summary["total_passes"] == 2
        assert summary["final_confidence"] == 0.9
        assert summary["hypotheses_considered"] == 1
        assert summary["context_items_retrieved"] == 1
        assert summary["open_questions"] == 1
        assert summary["uncertainties"] == 1

    def test_to_dict(self, sample_event):
        """Test converting working memory to dict"""
        wm = WorkingMemory(sample_event)

        wm.add_hypothesis(Hypothesis(id="hyp_1", description="Test", confidence=0.8))
        wm.start_reasoning_pass(1, "initial")
        wm.complete_reasoning_pass()

        wm_dict = wm.to_dict()

        assert wm_dict["event"]["event_id"] == sample_event.event_id
        assert wm_dict["state"] == "reasoning"  # State changes to reasoning when pass starts
        assert wm_dict["overall_confidence"] == wm.overall_confidence
        assert len(wm_dict["hypotheses"]) == 1
        assert len(wm_dict["reasoning_passes"]) == 1
        assert "reasoning_summary" in wm_dict

    def test_str_representation(self, sample_event):
        """Test string representation"""
        wm = WorkingMemory(sample_event)

        wm.add_hypothesis(Hypothesis(id="hyp_1", description="Test", confidence=0.8))
        wm.start_reasoning_pass(1, "initial")
        wm.complete_reasoning_pass()

        str_repr = str(wm)

        assert "WorkingMemory" in str_repr
        assert "test_eve" in str_repr  # First 8 chars of event ID
        assert "reasoning" in str_repr  # State is reasoning after pass started
        assert "passes=1" in str_repr
        assert "hypotheses=1" in str_repr
