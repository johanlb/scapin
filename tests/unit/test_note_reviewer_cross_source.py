"""Tests for RetoucheReviewer CrossSourceEngine integration"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.passepartout.cross_source.models import CrossSourceResult, SourceItem
from src.passepartout.note_manager import Note, NoteManager
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import NoteType
from src.passepartout.retouche_reviewer import RetoucheReviewer


class TestRetoucheReviewerCrossSourceInit:
    """Tests for RetoucheReviewer initialization with CrossSourceEngine"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def mock_note_manager(self):
        """Create mock NoteManager"""
        return MagicMock(spec=NoteManager)

    @pytest.fixture
    def store(self, temp_db):
        """Create a store with temporary database"""
        return NoteMetadataStore(temp_db)

    @pytest.fixture
    def scheduler(self, store):
        """Create a scheduler"""
        return NoteScheduler(store)

    def test_init_without_cross_source(self, mock_note_manager, store, scheduler):
        """Should initialize without CrossSourceEngine"""
        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
        )
        assert reviewer.cross_source_engine is None

    def test_init_with_cross_source(self, mock_note_manager, store, scheduler):
        """Should accept CrossSourceEngine parameter"""
        mock_engine = MagicMock()

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )
        assert reviewer.cross_source_engine is mock_engine


class TestQueryCrossSource:
    """Tests for the _query_cross_source method"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def mock_note_manager(self):
        """Create mock NoteManager"""
        manager = MagicMock(spec=NoteManager)
        manager.search_notes.return_value = []
        return manager

    @pytest.fixture
    def store(self, temp_db):
        """Create a store with temporary database"""
        return NoteMetadataStore(temp_db)

    @pytest.fixture
    def scheduler(self, store):
        """Create a scheduler"""
        return NoteScheduler(store)

    @pytest.fixture
    def sample_note(self):
        """Create a sample note"""
        return Note(
            note_id="test-note-001",
            title="Project Budget Analysis",
            content="# Project Budget Analysis\n\nThis note covers the Q1 budget.",
            tags=["finance", "project", "Q1"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_cross_source_result(self):
        """Create a sample CrossSourceResult"""
        return CrossSourceResult(
            query="Project Budget Analysis finance project Q1",
            items=[
                SourceItem(
                    source="email",
                    type="message",
                    title="Q1 Budget Report",
                    content="Here is the Q1 budget report you requested...",
                    timestamp=datetime.now(timezone.utc),
                    relevance_score=0.85,
                    url=None,
                    metadata={"from": "john@example.com"},
                ),
                SourceItem(
                    source="calendar",
                    type="event",
                    title="Budget Review Meeting",
                    content="Discuss Q1 budget with finance team",
                    timestamp=datetime.now(timezone.utc),
                    relevance_score=0.72,
                    url="https://calendar.example.com/event/123",
                    metadata={"attendees": ["alice@example.com"]},
                ),
            ],
            sources_searched=["email", "calendar"],
        )

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_engine(
        self, mock_note_manager, store, scheduler, sample_note
    ):
        """Should return empty list when no cross_source_engine is set"""
        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=None,
        )

        result = await reviewer._query_cross_source(sample_note)

        assert result == []

    @pytest.mark.asyncio
    async def test_queries_with_note_title_and_tags(
        self, mock_note_manager, store, scheduler, sample_note, sample_cross_source_result
    ):
        """Should build query from note title and tags"""
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=sample_cross_source_result)

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        await reviewer._query_cross_source(sample_note)

        # Verify search was called
        mock_engine.search.assert_called_once()
        call_args = mock_engine.search.call_args
        query = call_args.kwargs.get("query") or call_args.args[0]

        # Query should include title and tags
        assert "Project Budget Analysis" in query
        assert "finance" in query
        assert "project" in query

    @pytest.mark.asyncio
    async def test_converts_items_to_dicts(
        self, mock_note_manager, store, scheduler, sample_note, sample_cross_source_result
    ):
        """Should convert SourceItems to dictionaries"""
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=sample_cross_source_result)

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        result = await reviewer._query_cross_source(sample_note)

        assert len(result) == 2

        # Check first item
        assert result[0]["source"] == "email"
        assert result[0]["type"] == "message"
        assert result[0]["title"] == "Q1 Budget Report"
        assert "Q1 budget report" in result[0]["content"]
        assert result[0]["relevance_score"] == 0.85

        # Check second item
        assert result[1]["source"] == "calendar"
        assert result[1]["type"] == "event"

    @pytest.mark.asyncio
    async def test_limits_max_results(
        self, mock_note_manager, store, scheduler, sample_note, sample_cross_source_result
    ):
        """Should limit results to max_results=5"""
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=sample_cross_source_result)

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        await reviewer._query_cross_source(sample_note)

        call_args = mock_engine.search.call_args
        assert call_args.kwargs.get("max_results") == 5

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(
        self, mock_note_manager, store, scheduler, sample_note
    ):
        """Should return empty list on exception"""
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(side_effect=Exception("Search failed"))

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        result = await reviewer._query_cross_source(sample_note)

        assert result == []

    @pytest.mark.asyncio
    async def test_includes_content_context(
        self, mock_note_manager, store, scheduler, sample_cross_source_result
    ):
        """Should include content context in query"""
        note = Note(
            note_id="test-note-002",
            title="Simple Title",
            content="# Simple Title\n\nImportant context line here.\n\nMore content below.",
            tags=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=sample_cross_source_result)

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        await reviewer._query_cross_source(note)

        call_args = mock_engine.search.call_args
        query = call_args.kwargs.get("query") or call_args.args[0]

        # Query should include content context
        assert "Important context line here" in query

    @pytest.mark.asyncio
    async def test_truncates_long_content(
        self, mock_note_manager, store, scheduler, sample_cross_source_result
    ):
        """Should truncate content to 300 chars"""
        long_content = "x" * 500
        result_with_long_content = CrossSourceResult(
            query="test",
            items=[
                SourceItem(
                    source="email",
                    type="message",
                    title="Test",
                    content=long_content,
                    timestamp=datetime.now(timezone.utc),
                    relevance_score=0.5,
                )
            ],
            sources_searched=["email"],
        )

        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=result_with_long_content)

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        note = Note(
            note_id="test-note",
            title="Test Note",
            content="# Test Note\n\nContent",
            tags=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        result = await reviewer._query_cross_source(note)

        # Content should be truncated to 300 chars
        assert len(result[0]["content"]) <= 300


class TestLoadContextCrossSource:
    """Tests for _load_context method with CrossSourceEngine"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def mock_note_manager(self):
        """Create mock NoteManager"""
        manager = MagicMock(spec=NoteManager)
        manager.search_notes.return_value = []
        return manager

    @pytest.fixture
    def store(self, temp_db):
        """Create a store with temporary database"""
        return NoteMetadataStore(temp_db)

    @pytest.fixture
    def scheduler(self, store):
        """Create a scheduler"""
        return NoteScheduler(store)

    @pytest.fixture
    def sample_note(self):
        """Create a sample note"""
        return Note(
            note_id="test-note-001",
            title="Test Note",
            content="# Test Note\n\nSome content here.",
            tags=["test"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_metadata(self):
        """Create sample note metadata"""
        return NoteMetadata(
            note_id="test-note-001",
            note_type=NoteType.ENTITE,
        )

    @pytest.mark.asyncio
    async def test_includes_cross_source_in_context(
        self, mock_note_manager, store, scheduler, sample_note, sample_metadata
    ):
        """Should include cross-source results in context.related_entities"""
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(
            return_value=CrossSourceResult(
                query="test",
                items=[
                    SourceItem(
                        source="email",
                        type="message",
                        title="Related Email",
                        content="Content",
                        timestamp=datetime.now(timezone.utc),
                        relevance_score=0.9,
                    )
                ],
                sources_searched=["email"],
            )
        )

        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        context = await reviewer._load_context(sample_note, sample_metadata)

        assert len(context.related_entities) == 1
        assert context.related_entities[0]["source"] == "email"
        assert context.related_entities[0]["title"] == "Related Email"

    @pytest.mark.asyncio
    async def test_empty_related_entities_without_engine(
        self, mock_note_manager, store, scheduler, sample_note, sample_metadata
    ):
        """Should have empty related_entities without CrossSourceEngine"""
        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=None,
        )

        context = await reviewer._load_context(sample_note, sample_metadata)

        assert context.related_entities == []


class TestReviewWithCrossSource:
    """Integration tests for full review with CrossSourceEngine"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary notes directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def store(self, temp_db):
        """Create a store with temporary database"""
        return NoteMetadataStore(temp_db)

    @pytest.fixture
    def scheduler(self, store):
        """Create a scheduler"""
        return NoteScheduler(store)

    @pytest.mark.asyncio
    async def test_review_note_with_cross_source_context(
        self, temp_notes_dir, store, scheduler
    ):
        """Full review should include cross-source context"""
        # Create actual note manager with temp directory
        note_manager = NoteManager(temp_notes_dir, auto_index=False)

        # Create a note (create_note returns note_id string, then we get the Note)
        note_id = note_manager.create_note(
            title="Meeting Notes",
            content="# Meeting Notes\n\nDiscussed project budget.",
        )
        note = note_manager.get_note(note_id)

        # Create metadata
        store.create_for_note(
            note_id=note_id,
            note_type=NoteType.REUNION,
            content=note.content,
        )

        # Mock cross-source engine
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(
            return_value=CrossSourceResult(
                query="Meeting Notes",
                items=[
                    SourceItem(
                        source="calendar",
                        type="event",
                        title="Budget Meeting",
                        content="Calendar event for budget discussion",
                        timestamp=datetime.now(timezone.utc),
                        relevance_score=0.85,
                    )
                ],
                sources_searched=["calendar"],
            )
        )

        reviewer = RetoucheReviewer(
            note_manager=note_manager,
            metadata_store=store,
            scheduler=scheduler,
            cross_source_engine=mock_engine,
        )

        result = await reviewer.review_note(note_id)

        # Review should complete
        assert result.error is None
        # Cross-source engine should have been called
        mock_engine.search.assert_called_once()
