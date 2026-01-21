"""
Tests for Workflow V2.2 features.

Tests the new V2.2 additions:
- V2WorkingMemory and state management
- CrossSourceContext
- PatternMatch
- ClarificationQuestion
- New V2ProcessingResult properties
- New V2EmailProcessor methods
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.events.universal_event import (
    Entity,
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
    now_utc,
)
from src.core.models.v2_models import (
    AnalysisResult,
    ClarificationQuestion,
    ContextNote,
    CrossSourceContext,
    EmailAction,
    ExtractionType,
    ImportanceLevel,
    NoteAction,
    Extraction,
    PatternMatch,
    V2MemoryState,
    V2WorkingMemory,
)
from src.trivelin.v2_processor import V2EmailProcessor, V2ProcessingResult


def make_test_event(
    event_id: str = "test_123",
    title: str = "Test Event",
    content: str = "Test content",
    sender_name: str | None = None,
    sender_email: str | None = None,
) -> PerceivedEvent:
    """Helper to create test PerceivedEvent with all required fields."""
    now = now_utc()

    # Create sender entity if provided
    entities = []
    if sender_name or sender_email:
        entities.append(
            Entity(
                type="person",
                value=sender_name or sender_email or "unknown",
                confidence=0.9,
                metadata={"email": sender_email} if sender_email else {},
            )
        )

    from_person = sender_email or sender_name or "test@example.com"

    return PerceivedEvent(
        # Identity
        event_id=event_id,
        source=EventSource.EMAIL,
        source_id=f"email_{event_id}",
        # Timing
        occurred_at=now,
        received_at=now,
        # Core Content
        title=title,
        content=content,
        # Classification
        event_type=EventType.INFORMATION,
        urgency=UrgencyLevel.MEDIUM,
        # Extracted Information
        entities=entities,
        topics=["test"],
        keywords=["test"],
        # Participants
        from_person=from_person,
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
        clarification_questions=[],
    )


class TestV2WorkingMemory:
    """Tests for V2WorkingMemory dataclass."""

    def test_working_memory_initialization(self) -> None:
        """Test basic initialization."""
        memory = V2WorkingMemory(event_id="test_123")

        assert memory.event_id == "test_123"
        assert memory.state == V2MemoryState.INITIALIZED
        assert memory.context_notes == []
        assert memory.cross_source_context == []
        assert memory.pattern_matches == []
        assert memory.analysis is None
        assert memory.clarification_questions == []
        assert memory.errors == []
        assert memory.trace == []
        assert not memory.is_complete
        assert not memory.has_errors

    def test_working_memory_state_transition(self) -> None:
        """Test state transitions."""
        memory = V2WorkingMemory(event_id="test_123")

        memory.transition_to(V2MemoryState.CONTEXT_RETRIEVED)
        assert memory.state == V2MemoryState.CONTEXT_RETRIEVED
        assert len(memory.trace) == 1
        assert "initialized → context_retrieved" in memory.trace[0]["message"]

        memory.transition_to(V2MemoryState.ANALYZING)
        assert memory.state == V2MemoryState.ANALYZING

    def test_working_memory_complete_state(self) -> None:
        """Test that complete state sets completed_at."""
        memory = V2WorkingMemory(event_id="test_123")

        assert memory.completed_at is None
        memory.transition_to(V2MemoryState.COMPLETE)
        assert memory.completed_at is not None
        assert memory.is_complete

    def test_working_memory_failed_state(self) -> None:
        """Test that failed state sets completed_at."""
        memory = V2WorkingMemory(event_id="test_123")

        memory.transition_to(V2MemoryState.FAILED)
        assert memory.completed_at is not None
        assert memory.is_complete

    def test_working_memory_add_trace(self) -> None:
        """Test adding trace entries."""
        memory = V2WorkingMemory(event_id="test_123")

        memory.add_trace("Processing started", {"auto_apply": True})
        assert len(memory.trace) == 1
        assert memory.trace[0]["message"] == "Processing started"
        assert memory.trace[0]["metadata"] == {"auto_apply": True}
        assert "timestamp" in memory.trace[0]

    def test_working_memory_add_error(self) -> None:
        """Test adding errors."""
        memory = V2WorkingMemory(event_id="test_123")

        memory.add_error("Something went wrong")
        assert len(memory.errors) == 1
        assert memory.errors[0] == "Something went wrong"
        assert memory.has_errors
        # Error should also be in trace
        assert len(memory.trace) == 1
        assert "Error:" in memory.trace[0]["message"]

    def test_working_memory_duration_ms(self) -> None:
        """Test duration calculation."""
        memory = V2WorkingMemory(event_id="test_123")
        memory.started_at = datetime.now() - timedelta(milliseconds=100)
        memory.completed_at = datetime.now()

        # Duration should be approximately 100ms (allow some tolerance)
        assert 50 <= memory.duration_ms <= 200

    def test_working_memory_total_context_items(self) -> None:
        """Test total context items count."""
        memory = V2WorkingMemory(event_id="test_123")
        memory.context_notes = [
            ContextNote(title="Note 1", type="projet", content_summary="...", relevance=0.9)
        ]
        memory.cross_source_context = [
            CrossSourceContext(
                source="email", title="Email 1", content_summary="...", relevance=0.8
            ),
            CrossSourceContext(
                source="calendar", title="Event 1", content_summary="...", relevance=0.7
            ),
        ]

        assert memory.total_context_items == 3

    def test_working_memory_to_dict(self) -> None:
        """Test serialization to dict."""
        memory = V2WorkingMemory(event_id="test_123")
        memory.add_trace("Test trace")
        memory.transition_to(V2MemoryState.COMPLETE)

        result = memory.to_dict()

        assert result["event_id"] == "test_123"
        assert result["state"] == "complete"
        assert result["started_at"] is not None
        assert result["completed_at"] is not None
        assert isinstance(result["duration_ms"], float)
        assert result["context_notes_count"] == 0
        assert result["cross_source_count"] == 0
        assert result["has_analysis"] is False


class TestV2MemoryState:
    """Tests for V2MemoryState enum."""

    def test_all_states_exist(self) -> None:
        """Test that all expected states exist."""
        assert V2MemoryState.INITIALIZED.value == "initialized"
        assert V2MemoryState.CONTEXT_RETRIEVED.value == "context_retrieved"
        assert V2MemoryState.ANALYZING.value == "analyzing"
        assert V2MemoryState.PATTERN_VALIDATING.value == "pattern_validating"
        assert V2MemoryState.NEEDS_CLARIFICATION.value == "needs_clarification"
        assert V2MemoryState.APPLYING.value == "applying"
        assert V2MemoryState.COMPLETE.value == "complete"
        assert V2MemoryState.FAILED.value == "failed"


class TestCrossSourceContext:
    """Tests for CrossSourceContext dataclass."""

    def test_cross_source_context_creation(self) -> None:
        """Test basic creation."""
        ctx = CrossSourceContext(
            source="email",
            title="Re: Budget meeting",
            content_summary="Meeting scheduled for tomorrow...",
            relevance=0.85,
        )

        assert ctx.source == "email"
        assert ctx.title == "Re: Budget meeting"
        assert ctx.relevance == 0.85
        assert ctx.timestamp is None
        assert ctx.metadata == {}

    def test_cross_source_context_with_metadata(self) -> None:
        """Test creation with metadata."""
        ctx = CrossSourceContext(
            source="calendar",
            title="Budget Review",
            content_summary="Quarterly review...",
            relevance=0.9,
            timestamp=datetime.now(),
            metadata={"attendees": ["Alice", "Bob"]},
        )

        assert ctx.source == "calendar"
        assert ctx.timestamp is not None
        assert ctx.metadata["attendees"] == ["Alice", "Bob"]


class TestPatternMatch:
    """Tests for PatternMatch dataclass."""

    def test_pattern_match_creation(self) -> None:
        """Test basic creation."""
        match = PatternMatch(
            pattern_id="pattern_email_newsletter",
            description="Newsletter pattern: auto-archive",
            confidence=0.92,
            suggested_action="archive",
            occurrences=150,
        )

        assert match.pattern_id == "pattern_email_newsletter"
        assert match.confidence == 0.92
        assert match.suggested_action == "archive"
        assert match.occurrences == 150


class TestClarificationQuestion:
    """Tests for ClarificationQuestion dataclass."""

    def test_clarification_question_creation(self) -> None:
        """Test basic creation."""
        question = ClarificationQuestion(
            question="Quelle action dois-je effectuer ?",
            reason="Confiance basse",
            options=["Archiver", "Marquer", "Ignorer"],
            priority="haute",
        )

        assert "action" in question.question
        assert question.reason == "Confiance basse"
        assert len(question.options) == 3
        assert question.priority == "haute"

    def test_clarification_question_default_priority(self) -> None:
        """Test default priority."""
        question = ClarificationQuestion(
            question="Test?",
            reason="Test",
        )

        assert question.priority == "moyenne"
        assert question.options == []


class TestAnalysisResultV22:
    """Tests for V2.2 additions to AnalysisResult."""

    def test_analysis_result_effective_confidence(self) -> None:
        """Test effective_confidence property."""
        result = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.75,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        # No boost
        assert result.effective_confidence == 0.75

        # With boost
        result.pattern_confidence_boost = 0.1
        assert result.effective_confidence == 0.85

    def test_analysis_result_effective_confidence_capped(self) -> None:
        """Test that effective_confidence is capped at 1.0."""
        result = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.95,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
            pattern_confidence_boost=0.15,
        )

        assert result.effective_confidence == 1.0

    def test_analysis_result_pattern_fields(self) -> None:
        """Test pattern validation fields."""
        result = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.8,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        # Defaults
        assert result.pattern_matches == []
        assert result.pattern_validated is False
        assert result.pattern_confidence_boost == 0.0

    def test_analysis_result_clarification_fields(self) -> None:
        """Test clarification fields."""
        result = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.5,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        # Defaults
        assert result.clarification_questions == []
        assert result.needs_clarification is False


class TestV2ProcessingResultV22:
    """Tests for V2.2 additions to V2ProcessingResult."""

    def test_result_with_v22_fields(self) -> None:
        """Test result with V2.2 additions."""
        memory = V2WorkingMemory(event_id="test_123")
        cross_source = [
            CrossSourceContext(source="email", title="Test", content_summary="...", relevance=0.8)
        ]
        patterns = [
            PatternMatch(
                pattern_id="p1",
                description="Test",
                confidence=0.9,
                suggested_action="archive",
                occurrences=10,
            )
        ]
        questions = [ClarificationQuestion(question="Test?", reason="Low confidence")]

        result = V2ProcessingResult(
            success=True,
            event_id="test_123",
            working_memory=memory,
            cross_source_context=cross_source,
            pattern_matches=patterns,
            clarification_questions=questions,
            needs_clarification=True,
        )

        assert result.working_memory is not None
        assert len(result.cross_source_context) == 1
        assert len(result.pattern_matches) == 1
        assert len(result.clarification_questions) == 1
        assert result.needs_clarification is True

    def test_result_effective_confidence_with_analysis(self) -> None:
        """Test effective_confidence property."""
        analysis = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.8,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
            pattern_confidence_boost=0.1,
        )

        result = V2ProcessingResult(
            success=True,
            event_id="test_123",
            analysis=analysis,
        )

        assert result.effective_confidence == 0.9

    def test_result_effective_confidence_without_analysis(self) -> None:
        """Test effective_confidence without analysis."""
        result = V2ProcessingResult(
            success=False,
            event_id="test_123",
        )

        assert result.effective_confidence == 0.0

    def test_result_pattern_validated(self) -> None:
        """Test pattern_validated property."""
        result = V2ProcessingResult(
            success=True,
            event_id="test_123",
            pattern_matches=[
                PatternMatch(
                    pattern_id="p1",
                    description="Test",
                    confidence=0.9,
                    suggested_action="archive",
                    occurrences=10,
                )
            ],
        )

        assert result.pattern_validated is True

    def test_result_pattern_not_validated(self) -> None:
        """Test pattern_validated with no patterns."""
        result = V2ProcessingResult(
            success=True,
            event_id="test_123",
        )

        assert result.pattern_validated is False


class TestV2EmailProcessorV22Methods:
    """Tests for V2.2 methods in V2EmailProcessor."""

    @pytest.fixture
    def mock_processor(self) -> V2EmailProcessor:
        """Create a processor with mocked dependencies."""
        with (
            patch("src.trivelin.v2_processor.get_config") as mock_config,
            patch("src.trivelin.v2_processor.get_ai_router") as mock_router,
            patch("src.trivelin.v2_processor.NoteManager") as mock_nm,
            patch("src.trivelin.v2_processor.ContextEngine") as mock_ce,
            patch("src.trivelin.v2_processor.CrossSourceEngine") as mock_cse,
            patch("src.trivelin.v2_processor.PatternStore") as mock_ps,
            patch("src.trivelin.v2_processor.MultiPassAnalyzer") as mock_mpa,
            patch("src.trivelin.v2_processor.PKMEnricher") as mock_en,
        ):
            # Configure mocks
            mock_config.return_value = MagicMock()
            mock_config.return_value.ai = MagicMock()
            mock_config.return_value.storage = MagicMock()
            mock_config.return_value.storage.notes_path = "/tmp/notes"
            mock_config.return_value.storage.database_path = "/tmp/db.sqlite"

            processor = V2EmailProcessor()

            # Setup async mocks
            processor.cross_source_engine = MagicMock()
            processor.cross_source_engine.search = AsyncMock()
            processor.pattern_store = MagicMock()

            return processor

    def test_build_cross_source_query(self, mock_processor: V2EmailProcessor) -> None:
        """Test building search query from event."""
        event = make_test_event(
            title="Meeting tomorrow",
            content="Let's discuss the budget...",
            sender_name="Alice",
            sender_email="alice@example.com",
        )

        query = mock_processor._build_cross_source_query(event)

        assert "Meeting tomorrow" in query
        # from_person will be the email, not name
        assert "alice@example.com" in query

    def test_build_cross_source_query_minimal(self, mock_processor: V2EmailProcessor) -> None:
        """Test query building with minimal event (no content)."""
        event = make_test_event(title="Just a title", content="")

        query = mock_processor._build_cross_source_query(event)
        assert "Just a title" in query

    def test_generate_clarification_questions_low_confidence(
        self, mock_processor: V2EmailProcessor
    ) -> None:
        """Test question generation for low confidence."""
        event = make_test_event(
            sender_name="Bob",
            sender_email="bob@example.com",
        )

        analysis = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.5,  # Low confidence
            raisonnement="Uncertain",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        questions = mock_processor._generate_clarification_questions(event, analysis)

        assert len(questions) >= 1
        assert any("action" in q.question.lower() for q in questions)

    def test_generate_clarification_questions_with_extractions(
        self, mock_processor: V2EmailProcessor
    ) -> None:
        """Test question generation with extractions."""
        event = make_test_event()

        analysis = AnalysisResult(
            extractions=[
                Extraction(
                    info="Meeting at 3pm",
                    type=ExtractionType.DEADLINE,
                    importance=ImportanceLevel.HAUTE,
                    note_cible="Project Alpha",
                    note_action=NoteAction.ENRICHIR,
                )
            ],
            action=EmailAction.ARCHIVE,
            confidence=0.6,  # Low confidence with extractions
            raisonnement="Uncertain",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        questions = mock_processor._generate_clarification_questions(event, analysis)

        # Should have question about extractions
        assert any(
            "extraites" in q.question.lower() or "correctes" in q.question.lower()
            for q in questions
        )

    def test_generate_clarification_questions_high_confidence(
        self, mock_processor: V2EmailProcessor
    ) -> None:
        """Test no questions for high confidence."""
        event = make_test_event()

        analysis = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.95,  # High confidence
            raisonnement="Clear newsletter",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        questions = mock_processor._generate_clarification_questions(event, analysis)

        assert len(questions) == 0

    @pytest.mark.asyncio
    async def test_get_cross_source_context(self, mock_processor: V2EmailProcessor) -> None:
        """Test cross-source context retrieval."""
        from src.passepartout.cross_source.models import CrossSourceResult, SourceItem

        event = make_test_event(title="Budget meeting")

        # Mock search result
        mock_result = CrossSourceResult(
            query="Budget meeting",
            items=[
                SourceItem(
                    source="email",
                    title="Previous budget email",
                    content="Budget details here...",
                    timestamp=datetime.now(),
                    relevance_score=0.9,
                    type="email",  # Required field
                )
            ],
            sources_searched=["email"],
            sources_failed=[],
        )
        mock_result.items[0].final_score = 0.9

        mock_processor.cross_source_engine.search = AsyncMock(return_value=mock_result)

        result = await mock_processor._get_cross_source_context(event)

        assert len(result) == 1
        assert result[0].source == "email"
        assert result[0].title == "Previous budget email"

    @pytest.mark.asyncio
    async def test_get_cross_source_context_error(self, mock_processor: V2EmailProcessor) -> None:
        """Test cross-source context handles errors gracefully."""
        event = make_test_event(title="Test")

        # Mock search failure
        mock_processor.cross_source_engine.search = AsyncMock(
            side_effect=Exception("Search failed")
        )

        result = await mock_processor._get_cross_source_context(event)

        # Should return empty list on error
        assert result == []

    def test_validate_with_patterns(self, mock_processor: V2EmailProcessor) -> None:
        """Test pattern validation."""
        from src.sganarelle.types import Pattern, PatternType

        event = make_test_event()

        analysis = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.8,
            raisonnement="Newsletter",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        # Mock pattern store
        mock_pattern = Pattern(
            pattern_id="newsletter_pattern",
            pattern_type=PatternType.CONTEXT_TRIGGER,  # Use valid PatternType
            conditions={"sender": "newsletter@"},
            suggested_actions=["archive"],
            confidence=0.9,
            success_rate=0.95,
            occurrences=100,
            last_seen=now_utc(),
            created_at=now_utc(),
        )
        mock_processor.pattern_store.find_matching_patterns = MagicMock(return_value=[mock_pattern])

        result = mock_processor._validate_with_patterns(event, analysis)

        assert len(result) == 1
        assert result[0].pattern_id == "newsletter_pattern"
        assert result[0].confidence == 0.9

    def test_validate_with_patterns_error(self, mock_processor: V2EmailProcessor) -> None:
        """Test pattern validation handles errors gracefully."""
        event = make_test_event()

        analysis = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.8,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=100,
            duration_ms=50,
        )

        # Mock pattern store error
        mock_processor.pattern_store.find_matching_patterns = MagicMock(
            side_effect=Exception("Pattern store error")
        )

        result = mock_processor._validate_with_patterns(event, analysis)

        # Should return empty list on error
        assert result == []
