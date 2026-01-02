"""
Tests for ContextEngine

Coverage:
- Initialization and weight validation
- Entity-based retrieval
- Semantic retrieval
- Thread-based retrieval
- Full context retrieval with multiple strategies
- Ranking and deduplication
- Error handling
- Performance and relevance scoring
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from src.passepartout.context_engine import (
    ContextEngine,
    ContextRetrievalResult,
    CONTEXT_SOURCE_KB,
    CONTEXT_SOURCE_HISTORY,
    CONTEXT_TYPE_ENTITY,
    CONTEXT_TYPE_SEMANTIC,
    CONTEXT_TYPE_THREAD
)
from src.passepartout.note_manager import Note
from src.core.events import PerceivedEvent, Entity, EventType, EventSource, UrgencyLevel
from src.core.memory.working_memory import ContextItem


def create_test_event(**overrides):
    """Helper to create test PerceivedEvent with minimal required fields"""
    now = datetime.now(timezone.utc)
    defaults = {
        "event_id": "test_evt_1",
        "source": EventSource.EMAIL,
        "source_id": "msg_123",
        "occurred_at": now,
        "received_at": now,
        "title": "Test Event",
        "content": "Test content",
        "event_type": EventType.INFORMATION,
        "urgency": UrgencyLevel.MEDIUM,
        "entities": [],
        "topics": [],
        "keywords": [],
        "from_person": "test@example.com",
        "to_people": ["recipient@example.com"],
        "cc_people": [],
        "thread_id": None,
        "references": [],
        "in_reply_to": None,
        "has_attachments": False,
        "attachment_count": 0,
        "attachment_types": [],
        "urls": [],
        "metadata": {},
        "perception_confidence": 0.9,
        "needs_clarification": False,
        "clarification_questions": []
    }
    defaults.update(overrides)
    return PerceivedEvent(**defaults)


class TestContextEngineInit:
    """Test ContextEngine initialization"""

    def test_init_with_defaults(self):
        """Test default initialization"""
        note_manager = Mock()

        engine = ContextEngine(note_manager)

        assert engine.note_manager is note_manager
        assert engine.entity_weight == 0.4
        assert engine.semantic_weight == 0.4
        assert engine.thread_weight == 0.2
        assert abs((engine.entity_weight + engine.semantic_weight + engine.thread_weight) - 1.0) < 0.01

    def test_init_with_custom_weights(self):
        """Test initialization with custom weights"""
        note_manager = Mock()

        engine = ContextEngine(
            note_manager,
            entity_weight=0.5,
            semantic_weight=0.3,
            thread_weight=0.2
        )

        assert engine.entity_weight == 0.5
        assert engine.semantic_weight == 0.3
        assert engine.thread_weight == 0.2

    def test_init_invalid_weights_raises(self):
        """Test error when weights don't sum to 1.0"""
        note_manager = Mock()

        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ContextEngine(
                note_manager,
                entity_weight=0.5,
                semantic_weight=0.5,
                thread_weight=0.5  # Total = 1.5
            )


class TestEntityRetrieval:
    """Test entity-based context retrieval"""

    @pytest.fixture
    def engine(self):
        note_manager = Mock()
        return ContextEngine(note_manager)

    def test_retrieve_by_entities(self, engine):
        """Test retrieving context by entities"""
        # Mock notes
        note1 = Note(
            note_id="note1",
            title="Meeting with Alice",
            content="Discussed project timeline",
            created_at=datetime(2025, 1, 15),
            updated_at=datetime(2025, 1, 15),
            tags=["work"],
            entities=[]
        )

        entity = Entity(type="person", value="Alice", confidence=0.9)
        # Mock returns tuples (note, distance) when return_scores=True
        # Use small distance (0.1) to get high relevance with L2 metric
        engine.note_manager.get_notes_by_entity.return_value = [(note1, 0.1)]

        # Retrieve
        context_items = engine._retrieve_by_entities([entity], top_k=10)

        assert len(context_items) == 1
        assert context_items[0].source == CONTEXT_SOURCE_KB
        assert context_items[0].type == CONTEXT_TYPE_ENTITY
        assert "Meeting with Alice" in context_items[0].content
        # Relevance = entity.confidence * distance_to_relevance(0.1)
        # With L2: exp(-(0.1^2)/2.0) = exp(-0.005) ≈ 0.995, so 0.9 * 0.995 ≈ 0.895
        assert context_items[0].relevance_score > 0.85  # High relevance
        assert context_items[0].metadata["entity_value"] == "Alice"

    def test_retrieve_by_entities_multiple(self, engine):
        """Test retrieval with multiple entities"""
        note1 = Note(
            note_id="note1", title="Alice Note", content="Content",
            created_at=datetime.now(), updated_at=datetime.now(),
            tags=[], entities=[]
        )
        note2 = Note(
            note_id="note2", title="Bob Note", content="Content",
            created_at=datetime.now(), updated_at=datetime.now(),
            tags=[], entities=[]
        )

        entity1 = Entity(type="person", value="Alice", confidence=0.9)
        entity2 = Entity(type="person", value="Bob", confidence=0.8)

        def mock_get_by_entity(entity, top_k, return_scores=False):
            # Return tuples (note, distance) when return_scores=True
            if entity.value == "Alice":
                return [(note1, 1.0)]
            elif entity.value == "Bob":
                return [(note2, 0.9)]
            return []

        engine.note_manager.get_notes_by_entity.side_effect = mock_get_by_entity

        context_items = engine._retrieve_by_entities([entity1, entity2], top_k=10)

        assert len(context_items) == 2
        assert any("Alice Note" in item.content for item in context_items)
        assert any("Bob Note" in item.content for item in context_items)

    def test_retrieve_by_entities_no_results(self, engine):
        """Test entity retrieval with no results"""
        entity = Entity(type="person", value="Unknown", confidence=0.9)
        engine.note_manager.get_notes_by_entity.return_value = []

        context_items = engine._retrieve_by_entities([entity], top_k=10)

        assert len(context_items) == 0

    def test_retrieve_by_entities_error_handling(self, engine):
        """Test error handling in entity retrieval"""
        entity = Entity(type="person", value="Alice", confidence=0.9)
        engine.note_manager.get_notes_by_entity.side_effect = Exception("DB error")

        # Should not raise, just log warning and continue
        context_items = engine._retrieve_by_entities([entity], top_k=10)

        assert len(context_items) == 0


class TestSemanticRetrieval:
    """Test semantic-based context retrieval"""

    @pytest.fixture
    def engine(self):
        note_manager = Mock()
        return ContextEngine(note_manager)

    def test_retrieve_by_semantic(self, engine):
        """Test semantic search"""
        note1 = Note(
            note_id="note1",
            title="Python Tutorial",
            content="Learn Python programming",
            created_at=datetime(2025, 1, 15),
            updated_at=datetime(2025, 1, 15),
            tags=["programming"],
            entities=[]
        )

        # Mock returns tuples (note, distance) when return_scores=True
        engine.note_manager.search_notes.return_value = [(note1, 0.2)]

        event = create_test_event(
            title="Python question",
            content="How do I learn Python?",
            event_type=EventType.REQUEST
        )

        context_items = engine._retrieve_by_semantic(event, top_k=10)

        assert len(context_items) == 1
        assert context_items[0].source == CONTEXT_SOURCE_KB
        assert context_items[0].type == CONTEXT_TYPE_SEMANTIC
        assert "Python Tutorial" in context_items[0].content
        # Distance 0.2 with L2 metric should give high relevance
        assert context_items[0].relevance_score >= 0.5

    def test_retrieve_by_semantic_relevance_decay(self, engine):
        """Test relevance scores decay with position"""
        notes = [
            Note(
                note_id=f"note{i}",
                title=f"Note {i}",
                content=f"Content {i}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=[],
                entities=[]
            )
            for i in range(5)
        ]

        # Mock returns tuples with increasing distances (decreasing relevance)
        notes_with_scores = [(note, i * 0.2) for i, note in enumerate(notes)]
        engine.note_manager.search_notes.return_value = notes_with_scores

        event = create_test_event(
            title="Test",
            content="Test content"
        )

        context_items = engine._retrieve_by_semantic(event, top_k=10)

        # Scores should decay (as distances increase)
        assert len(context_items) == 5
        for i in range(len(context_items) - 1):
            assert context_items[i].relevance_score >= context_items[i + 1].relevance_score

    def test_retrieve_by_semantic_error_handling(self, engine):
        """Test error handling in semantic retrieval"""
        engine.note_manager.search_notes.side_effect = Exception("Search error")

        event = create_test_event(
            title="Test",
            content="Test"
        )

        # Should not raise, return empty list
        context_items = engine._retrieve_by_semantic(event, top_k=10)

        assert len(context_items) == 0


class TestThreadRetrieval:
    """Test thread-based context retrieval"""

    @pytest.fixture
    def engine(self):
        note_manager = Mock()
        return ContextEngine(note_manager)

    def test_retrieve_by_thread(self, engine):
        """Test thread-based retrieval"""
        note1 = Note(
            note_id="note1",
            title="Thread Message",
            content="Previous message in thread",
            created_at=datetime(2025, 1, 15),
            updated_at=datetime(2025, 1, 15),
            tags=[],
            entities=[],
            metadata={"thread_id": "thread123"}
        )

        engine.note_manager.search_notes.return_value = [note1]

        context_items = engine._retrieve_by_thread("thread123", top_k=5)

        assert len(context_items) == 1
        assert context_items[0].source == CONTEXT_SOURCE_HISTORY
        assert context_items[0].type == CONTEXT_TYPE_THREAD
        assert "Thread Message" in context_items[0].content
        assert context_items[0].relevance_score == 0.9
        assert context_items[0].metadata["thread_id"] == "thread123"

    def test_retrieve_by_thread_filters_by_thread_id(self, engine):
        """Test that only notes with matching thread_id are returned"""
        note1 = Note(
            note_id="note1",
            title="Correct Thread",
            content="Content",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=[],
            entities=[],
            metadata={"thread_id": "thread123"}
        )
        note2 = Note(
            note_id="note2",
            title="Wrong Thread",
            content="Content",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=[],
            entities=[],
            metadata={"thread_id": "thread456"}
        )

        engine.note_manager.search_notes.return_value = [note1, note2]

        context_items = engine._retrieve_by_thread("thread123", top_k=5)

        # Only note1 should be returned
        assert len(context_items) == 1
        assert context_items[0].metadata["note_id"] == "note1"

    def test_retrieve_by_thread_error_handling(self, engine):
        """Test error handling in thread retrieval"""
        engine.note_manager.search_notes.side_effect = Exception("Search error")

        # Should not raise, return empty list
        context_items = engine._retrieve_by_thread("thread123", top_k=5)

        assert len(context_items) == 0


class TestRetrieveContext:
    """Test full context retrieval with all strategies"""

    @pytest.fixture
    def engine(self):
        note_manager = Mock()

        # Setup default returns
        note_manager.get_notes_by_entity.return_value = []
        note_manager.search_notes.return_value = []

        return ContextEngine(note_manager)

    def test_retrieve_context_all_sources(self, engine):
        """Test context retrieval using all sources"""
        # Setup mocks
        entity_note = Note(
            note_id="note1",
            title="Entity Note",
            content="Content",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=[],
            entities=[]
        )
        semantic_note = Note(
            note_id="note2",
            title="Semantic Note",
            content="Content",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=[],
            entities=[]
        )
        thread_note = Note(
            note_id="note3",
            title="Thread Note",
            content="Content",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=[],
            entities=[],
            metadata={"thread_id": "thread123"}
        )

        # Entity retrieval uses return_scores=True
        engine.note_manager.get_notes_by_entity.return_value = [(entity_note, 0.1)]

        # Search notes: thread search doesn't use return_scores, semantic does
        def mock_search_notes(q, top_k, return_scores=False):
            if "thread:" in q:
                return [thread_note]  # Thread search doesn't use scores
            else:
                return [(semantic_note, 0.2)] if return_scores else [semantic_note]

        engine.note_manager.search_notes.side_effect = mock_search_notes

        event = create_test_event(
            title="Test Event",
            content="Test content",
            entities=[Entity(type="person", value="Alice", confidence=0.9)],
            thread_id="thread123"
        )

        result = engine.retrieve_context(event, top_k=10, min_relevance=0.1)

        assert isinstance(result, ContextRetrievalResult)
        assert len(result.context_items) > 0
        assert result.total_retrieved >= len(result.context_items)
        assert len(result.sources_used) > 0
        assert result.retrieval_duration_seconds >= 0

    def test_retrieve_context_top_k_limiting(self, engine):
        """Test that top_k limits results"""
        notes = [
            Note(
                note_id=f"note{i}",
                title=f"Note {i}",
                content=f"Content {i}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=[],
                entities=[]
            )
            for i in range(20)
        ]

        # Semantic search uses return_scores=True
        notes_with_scores = [(note, i * 0.1) for i, note in enumerate(notes)]
        engine.note_manager.search_notes.return_value = notes_with_scores

        event = create_test_event(
            title="Test",
            content="Test"
        )

        result = engine.retrieve_context(event, top_k=5)

        # Should only return 5 items
        assert len(result.context_items) <= 5

    def test_retrieve_context_min_relevance_filtering(self, engine):
        """Test minimum relevance threshold filtering"""
        notes = [
            Note(
                note_id=f"note{i}",
                title=f"Note {i}",
                content=f"Content {i}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=[],
                entities=[]
            )
            for i in range(10)
        ]

        # Semantic search uses return_scores=True
        # Use small distances for first few notes to get high relevance scores
        notes_with_scores = [(note, i * 0.05) for i, note in enumerate(notes)]
        engine.note_manager.search_notes.return_value = notes_with_scores

        event = create_test_event(
            title="Test",
            content="Test"
        )

        # High threshold should filter out more items
        result = engine.retrieve_context(event, top_k=10, min_relevance=0.9)

        # All returned items should meet threshold
        for item in result.context_items:
            assert item.relevance_score >= 0.9

    def test_retrieve_context_no_entities(self, engine):
        """Test context retrieval without entities"""
        semantic_note = Note(
            note_id="note1",
            title="Note",
            content="Content",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=[],
            entities=[]
        )

        # Mock returns tuples (note, distance) when return_scores=True
        engine.note_manager.search_notes.return_value = [(semantic_note, 0.2)]

        event = create_test_event(
            title="Test",
            content="Test",
            entities=[]  # No entities
        )

        result = engine.retrieve_context(event, top_k=10, min_relevance=0.1)

        # Should still use semantic search
        assert "entity" not in result.sources_used
        assert len(result.context_items) > 0

    def test_retrieve_context_no_thread_id(self, engine):
        """Test context retrieval without thread_id"""
        semantic_note = Note(
            note_id="note1",
            title="Note",
            content="Content",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=[],
            entities=[]
        )

        # Semantic search uses return_scores=True
        engine.note_manager.search_notes.return_value = [(semantic_note, 0.2)]

        event = create_test_event(
            title="Test",
            content="Test",
            thread_id=None  # No thread
        )

        result = engine.retrieve_context(event, top_k=10)

        # Should not use thread search
        assert "thread" not in result.sources_used


class TestRankingAndDeduplication:
    """Test ranking and deduplication logic"""

    @pytest.fixture
    def engine(self):
        note_manager = Mock()
        return ContextEngine(note_manager)

    def test_rank_and_deduplicate(self, engine):
        """Test ranking by score"""
        ctx1 = ContextItem(
            source=CONTEXT_SOURCE_KB,
            type=CONTEXT_TYPE_SEMANTIC,
            content="Content 1",
            relevance_score=0.9,
            metadata={"note_id": "note1"}
        )
        ctx2 = ContextItem(
            source=CONTEXT_SOURCE_KB,
            type=CONTEXT_TYPE_SEMANTIC,
            content="Content 2",
            relevance_score=0.7,
            metadata={"note_id": "note2"}
        )

        candidates = [(ctx1, 0.5), (ctx2, 0.5)]

        ranked = engine._rank_and_deduplicate(candidates, top_k=10, min_relevance=0.0)

        # Should be sorted by final score (relevance * weight)
        assert len(ranked) == 2
        assert ranked[0].metadata["note_id"] == "note1"  # Higher score
        assert ranked[1].metadata["note_id"] == "note2"

    def test_rank_and_deduplicate_removes_duplicates(self, engine):
        """Test deduplication by note_id"""
        ctx1 = ContextItem(
            source=CONTEXT_SOURCE_KB,
            type=CONTEXT_TYPE_ENTITY,
            content="Content 1",
            relevance_score=0.9,
            metadata={"note_id": "note1"}
        )
        ctx2 = ContextItem(
            source=CONTEXT_SOURCE_KB,
            type=CONTEXT_TYPE_SEMANTIC,
            content="Content 1 duplicate",
            relevance_score=0.8,
            metadata={"note_id": "note1"}  # Same note_id
        )

        candidates = [(ctx1, 0.5), (ctx2, 0.5)]

        ranked = engine._rank_and_deduplicate(candidates, top_k=10, min_relevance=0.0)

        # Should only have one item
        assert len(ranked) == 1
        assert ranked[0].metadata["note_id"] == "note1"

    def test_rank_and_deduplicate_filters_by_min_relevance(self, engine):
        """Test filtering by minimum relevance"""
        ctx1 = ContextItem(
            source=CONTEXT_SOURCE_KB,
            type=CONTEXT_TYPE_SEMANTIC,
            content="High relevance",
            relevance_score=0.9,
            metadata={"note_id": "note1"}
        )
        ctx2 = ContextItem(
            source=CONTEXT_SOURCE_KB,
            type=CONTEXT_TYPE_SEMANTIC,
            content="Low relevance",
            relevance_score=0.3,
            metadata={"note_id": "note2"}
        )

        candidates = [(ctx1, 0.5), (ctx2, 0.5)]

        ranked = engine._rank_and_deduplicate(candidates, top_k=10, min_relevance=0.4)

        # Should filter out ctx2 (0.3 * 0.5 = 0.15 < 0.4)
        assert len(ranked) == 1
        assert ranked[0].metadata["note_id"] == "note1"

    def test_rank_and_deduplicate_empty_list(self, engine):
        """Test with empty candidate list"""
        ranked = engine._rank_and_deduplicate([], top_k=10, min_relevance=0.0)

        assert ranked == []


class TestStatsAndRepr:
    """Test statistics and string representation"""

    def test_get_stats(self):
        """Test get_stats method"""
        note_manager = Mock()
        note_manager.__repr__ = Mock(return_value="NoteManager(...)")

        engine = ContextEngine(
            note_manager,
            entity_weight=0.5,
            semantic_weight=0.3,
            thread_weight=0.2
        )

        stats = engine.get_stats()

        assert stats["weights"]["entity"] == 0.5
        assert stats["weights"]["semantic"] == 0.3
        assert stats["weights"]["thread"] == 0.2
        assert "note_manager" in stats

    def test_repr(self):
        """Test string representation"""
        note_manager = Mock()

        engine = ContextEngine(
            note_manager,
            entity_weight=0.5,
            semantic_weight=0.3,
            thread_weight=0.2
        )

        repr_str = repr(engine)

        assert "ContextEngine" in repr_str
        assert "0.5" in repr_str
        assert "0.3" in repr_str
        assert "0.2" in repr_str
