"""
Tests for context_searcher.py — Multi-Pass v2.2 context search

Tests cover:
- ContextBlock dataclasses (Note, Calendar, Task, Email, Conflict)
- EntityProfile creation and formatting
- StructuredContext methods
- ContextSearcher initialization and properties
- Search functionality (notes, calendar, tasks, emails)
- Conflict detection
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.sancho.context_searcher import (
    CalendarContextBlock,
    ConflictBlock,
    ContextSearchConfig,
    ContextSearcher,
    EmailContextBlock,
    EntityProfile,
    NoteContextBlock,
    StructuredContext,
    TaskContextBlock,
)


class TestNoteContextBlock:
    """Tests for NoteContextBlock dataclass"""

    def test_creation(self):
        """Create a note context block"""
        block = NoteContextBlock(
            note_id="note-123",
            title="Marc Dupont",
            note_type="personne",
            summary="Tech Lead chez Acme Corp",
            relevance=0.85,
        )
        assert block.note_id == "note-123"
        assert block.title == "Marc Dupont"
        assert block.note_type == "personne"
        assert block.relevance == 0.85

    def test_to_prompt_block(self):
        """Format as prompt block"""
        block = NoteContextBlock(
            note_id="note-123",
            title="Marc Dupont",
            note_type="personne",
            summary="Tech Lead chez Acme Corp",
            relevance=0.85,
        )
        prompt = block.to_prompt_block()
        assert "Marc Dupont" in prompt
        assert "personne" in prompt
        assert "85%" in prompt
        assert "Tech Lead" in prompt


class TestCalendarContextBlock:
    """Tests for CalendarContextBlock dataclass"""

    def test_creation(self):
        """Create a calendar context block"""
        block = CalendarContextBlock(
            event_id="event-456",
            title="Réunion Projet Alpha",
            date="2026-01-15",
            time="14:00",
            participants=["Marc Dupont", "Sophie Martin"],
            location="Salle A",
            relevance=0.9,
        )
        assert block.event_id == "event-456"
        assert block.date == "2026-01-15"
        assert len(block.participants) == 2

    def test_to_prompt_block(self):
        """Format as prompt block"""
        block = CalendarContextBlock(
            event_id="event-456",
            title="Réunion Projet Alpha",
            date="2026-01-15",
            time="14:00",
            participants=["Marc", "Sophie"],
        )
        prompt = block.to_prompt_block()
        assert "📅" in prompt
        assert "2026-01-15" in prompt
        assert "14:00" in prompt
        assert "Réunion Projet Alpha" in prompt
        assert "Marc" in prompt

    def test_to_prompt_block_no_time(self):
        """Format without time"""
        block = CalendarContextBlock(
            event_id="event-456",
            title="Jour férié",
            date="2026-01-01",
            time=None,  # Explicitly no time
        )
        prompt = block.to_prompt_block()
        assert "2026-01-01" in prompt
        assert "Jour férié" in prompt


class TestTaskContextBlock:
    """Tests for TaskContextBlock dataclass"""

    def test_creation(self):
        """Create a task context block"""
        block = TaskContextBlock(
            task_id="task-789",
            title="Préparer présentation",
            project="Projet Alpha",
            due_date="2026-01-20",
            status="active",
            relevance=0.75,
        )
        assert block.task_id == "task-789"
        assert block.project == "Projet Alpha"
        assert block.status == "active"

    def test_to_prompt_block(self):
        """Format as prompt block"""
        block = TaskContextBlock(
            task_id="task-789",
            title="Préparer présentation",
            project="Projet Alpha",
            due_date="2026-01-20",
        )
        prompt = block.to_prompt_block()
        assert "⚡" in prompt
        assert "Préparer présentation" in prompt
        assert "Projet Alpha" in prompt
        assert "2026-01-20" in prompt


class TestEmailContextBlock:
    """Tests for EmailContextBlock dataclass"""

    def test_creation(self):
        """Create an email context block"""
        block = EmailContextBlock(
            message_id="msg-abc",
            subject="Re: Projet Alpha",
            sender="marc@example.com",
            date="2026-01-10",
            snippet="Voici le compte-rendu de la réunion...",
            relevance=0.8,
        )
        assert block.message_id == "msg-abc"
        assert block.sender == "marc@example.com"

    def test_to_prompt_block(self):
        """Format as prompt block"""
        block = EmailContextBlock(
            message_id="msg-abc",
            subject="Re: Projet Alpha",
            sender="marc@example.com",
            date="2026-01-10",
            snippet="Voici le compte-rendu de la réunion...",
        )
        prompt = block.to_prompt_block()
        assert "✉️" in prompt
        assert "Re: Projet Alpha" in prompt
        assert "marc@example.com" in prompt
        assert "2026-01-10" in prompt


class TestConflictBlock:
    """Tests for ConflictBlock dataclass"""

    def test_creation(self):
        """Create a conflict block"""
        block = ConflictBlock(
            conflict_type="calendar_overlap",
            description="Deux réunions le même jour",
            options=["Réunion A", "Réunion B"],
            severity="major",
        )
        assert block.conflict_type == "calendar_overlap"
        assert block.severity == "major"
        assert len(block.options) == 2

    def test_to_prompt_block(self):
        """Format as prompt block"""
        block = ConflictBlock(
            conflict_type="calendar_overlap",
            description="Deux réunions le même jour",
            options=["Réunion A", "Réunion B"],
        )
        prompt = block.to_prompt_block()
        assert "⚠️" in prompt
        assert "calendar_overlap" in prompt
        assert "Réunion A" in prompt


class TestEntityProfile:
    """Tests for EntityProfile dataclass"""

    def test_creation(self):
        """Create an entity profile"""
        profile = EntityProfile(
            name="Marc",
            canonical_name="Marc Dupont",
            entity_type="personne",
            role="Tech Lead",
            relationship="Collègue",
            key_facts=["Expert Python", "Projet Alpha"],
            related_entities=["Sophie Martin"],
        )
        assert profile.name == "Marc"
        assert profile.canonical_name == "Marc Dupont"
        assert profile.role == "Tech Lead"

    def test_to_prompt_block(self):
        """Format as prompt block"""
        profile = EntityProfile(
            name="Marc",
            canonical_name="Marc Dupont",
            entity_type="personne",
            role="Tech Lead",
            relationship="Collègue",
            last_interaction=datetime(2026, 1, 10),
            key_facts=["Expert Python", "Projet Alpha"],
        )
        prompt = profile.to_prompt_block()
        assert "Marc Dupont" in prompt
        assert "personne" in prompt
        assert "Tech Lead" in prompt
        assert "Collègue" in prompt
        assert "2026-01-10" in prompt
        assert "Expert Python" in prompt


class TestStructuredContext:
    """Tests for StructuredContext dataclass"""

    def test_creation_empty(self):
        """Create empty context"""
        context = StructuredContext(
            query_entities=["Marc"],
            search_timestamp=datetime.now(),
            sources_searched=["notes"],
        )
        assert context.is_empty is True
        assert context.total_results == 0

    def test_creation_with_results(self):
        """Create context with results"""
        context = StructuredContext(
            query_entities=["Marc"],
            search_timestamp=datetime.now(),
            sources_searched=["notes", "calendar"],
            notes=[
                NoteContextBlock(
                    note_id="n1",
                    title="Marc",
                    note_type="personne",
                    summary="Test",
                    relevance=0.9,
                )
            ],
            calendar=[
                CalendarContextBlock(
                    event_id="e1",
                    title="Meeting",
                    date="2026-01-15",
                    time="10:00",
                )
            ],
        )
        assert context.is_empty is False
        assert context.total_results == 2

    def test_to_prompt_format(self):
        """Generate prompt format"""
        profile = EntityProfile(
            name="Marc",
            canonical_name="Marc Dupont",
            entity_type="personne",
        )
        context = StructuredContext(
            query_entities=["Marc"],
            search_timestamp=datetime.now(),
            sources_searched=["notes"],
            entity_profiles={"Marc": profile},
            notes=[
                NoteContextBlock(
                    note_id="n1",
                    title="Marc Dupont",
                    note_type="personne",
                    summary="Tech Lead",
                    relevance=0.9,
                )
            ],
        )
        prompt = context.to_prompt_format()
        assert "Profils des Entités" in prompt
        assert "Marc Dupont" in prompt
        assert "Notes PKM Pertinentes" in prompt

    def test_to_prompt_format_empty(self):
        """Empty context returns empty string"""
        context = StructuredContext(
            query_entities=[],
            search_timestamp=datetime.now(),
            sources_searched=[],
        )
        prompt = context.to_prompt_format()
        assert prompt == ""


class TestContextSearchConfig:
    """Tests for ContextSearchConfig dataclass"""

    def test_defaults(self):
        """Check default values"""
        config = ContextSearchConfig()
        assert config.max_notes == 5
        assert config.max_calendar_events == 10
        assert config.max_tasks == 5
        assert config.min_relevance == 0.3
        assert config.include_calendar is True

    def test_custom_values(self):
        """Override default values"""
        config = ContextSearchConfig(
            max_notes=10,
            min_relevance=0.5,
            include_tasks=False,
        )
        assert config.max_notes == 10
        assert config.min_relevance == 0.5
        assert config.include_tasks is False


class TestContextSearcher:
    """Tests for ContextSearcher class"""

    def test_init_no_dependencies(self):
        """Initialize without dependencies"""
        searcher = ContextSearcher()
        assert searcher.has_note_manager is False
        assert searcher.has_cross_source is False

    def test_init_with_note_manager(self):
        """Initialize with note manager"""
        mock_nm = MagicMock()
        searcher = ContextSearcher(note_manager=mock_nm)
        assert searcher.has_note_manager is True
        assert searcher.has_cross_source is False

    def test_init_with_both(self):
        """Initialize with both dependencies"""
        mock_nm = MagicMock()
        mock_cs = MagicMock()
        searcher = ContextSearcher(note_manager=mock_nm, cross_source_engine=mock_cs)
        assert searcher.has_note_manager is True
        assert searcher.has_cross_source is True

    @pytest.mark.asyncio
    async def test_search_empty_no_dependencies(self):
        """Search with no dependencies returns empty context"""
        searcher = ContextSearcher()
        context = await searcher.search_for_entities(["Marc"])
        assert context.is_empty is True
        assert "notes" not in context.sources_searched

    @pytest.mark.asyncio
    async def test_search_with_note_manager(self):
        """Search with note manager"""
        # Mock note manager
        mock_nm = MagicMock()
        mock_note = MagicMock()
        mock_note.id = "note-123"
        mock_note.title = "Marc Dupont"
        mock_note.type = "personne"
        mock_note.summary = "Tech Lead"
        mock_note.content = "Expert Python"
        mock_note.modified_at = datetime.now()
        mock_note.tags = ["important"]
        mock_note.metadata = {}
        mock_nm.search_notes.return_value = [(mock_note, 0.9)]

        searcher = ContextSearcher(note_manager=mock_nm)
        context = await searcher.search_for_entities(["Marc"])

        assert "notes" in context.sources_searched
        assert len(context.notes) == 1
        assert context.notes[0].title == "Marc Dupont"
        assert "Marc" in context.entity_profiles

    @pytest.mark.asyncio
    async def test_search_with_cross_source_calendar(self):
        """Search calendar via cross-source engine"""
        # Mock cross-source engine
        mock_cs = AsyncMock()
        mock_result = MagicMock()
        mock_item = MagicMock()
        mock_item.id = "event-456"
        mock_item.title = "Meeting Marc"
        mock_item.source = "calendar"
        mock_item.metadata = {
            "date": "2026-01-15",
            "time": "14:00",
            "participants": ["Marc"],
        }
        mock_item.final_score = 0.85
        mock_result.items = [mock_item]
        mock_cs.search.return_value = mock_result

        searcher = ContextSearcher(cross_source_engine=mock_cs)
        context = await searcher.search_for_entities(["Marc"])

        assert "calendar" in context.sources_searched
        assert len(context.calendar) == 1
        assert context.calendar[0].title == "Meeting Marc"

    @pytest.mark.asyncio
    async def test_search_filters_low_relevance(self):
        """Filter notes below min_relevance"""
        mock_nm = MagicMock()
        mock_note = MagicMock()
        mock_note.id = "note-low"
        mock_note.title = "Old Note"
        mock_note.type = "note"
        mock_note.summary = "Not relevant"
        mock_note.content = ""
        mock_note.modified_at = None
        mock_note.tags = []
        mock_note.metadata = {}
        mock_nm.search_notes.return_value = [(mock_note, 0.2)]  # Low score

        searcher = ContextSearcher(note_manager=mock_nm)
        config = ContextSearchConfig(min_relevance=0.3)
        context = await searcher.search_for_entities(["Test"], config=config)

        assert len(context.notes) == 0  # Filtered out


class TestConflictDetection:
    """Tests for conflict detection"""

    def test_detect_calendar_overlap(self):
        """Detect overlapping calendar events"""
        searcher = ContextSearcher()
        calendar = [
            CalendarContextBlock(
                event_id="e1", title="Meeting A", date="2026-01-15", time="10:00"
            ),
            CalendarContextBlock(
                event_id="e2", title="Meeting B", date="2026-01-15", time="14:00"
            ),
        ]
        conflicts = searcher._detect_conflicts([], calendar, [])
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "calendar_overlap"

    def test_detect_duplicate_notes(self):
        """Detect similar note titles"""
        searcher = ContextSearcher()
        notes = [
            NoteContextBlock(
                note_id="n1",
                title="Marc Dupont",
                note_type="personne",
                summary="Test",
                relevance=0.9,
            ),
            NoteContextBlock(
                note_id="n2",
                title="Marc dupont",  # Same, different case
                note_type="personne",
                summary="Test 2",
                relevance=0.8,
            ),
        ]
        conflicts = searcher._detect_conflicts(notes, [], [])
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "duplicate_info"

    def test_no_conflict_unique_events(self):
        """No conflicts when events are unique"""
        searcher = ContextSearcher()
        calendar = [
            CalendarContextBlock(
                event_id="e1", title="Meeting A", date="2026-01-15", time="10:00"
            ),
            CalendarContextBlock(
                event_id="e2", title="Meeting B", date="2026-01-16", time="10:00"
            ),
        ]
        conflicts = searcher._detect_conflicts([], calendar, [])
        assert len(conflicts) == 0


class TestSimilarStrings:
    """Tests for string similarity helper"""

    def test_identical_strings(self):
        """Identical strings are similar"""
        searcher = ContextSearcher()
        assert searcher._similar_strings("Marc Dupont", "Marc Dupont") is True

    def test_case_insensitive(self):
        """Case insensitive comparison"""
        searcher = ContextSearcher()
        assert searcher._similar_strings("Marc Dupont", "marc dupont") is True

    def test_different_strings(self):
        """Different strings are not similar"""
        searcher = ContextSearcher()
        assert searcher._similar_strings("Marc Dupont", "Sophie Martin") is False

    def test_partial_overlap(self):
        """Partial word overlap"""
        searcher = ContextSearcher()
        # "Marc Chef Projet" vs "Marc Projet" have 2/3 = 0.67 overlap (< 0.8 threshold)
        assert searcher._similar_strings("Marc Chef Projet", "Marc Projet") is False
        # "Marc Dupont" vs "Marc Dupont Jr" have 2/3 = 0.67 overlap (< 0.8 threshold)
        assert searcher._similar_strings("Marc Dupont", "Marc Dupont Jr") is False
        # High overlap: "Projet Alpha Beta" vs "Projet Alpha" = 2/3 (< 0.8)
        assert searcher._similar_strings("Projet Alpha", "Alpha Projet") is True  # Same words, different order

    def test_empty_strings(self):
        """Empty strings are not similar"""
        searcher = ContextSearcher()
        assert searcher._similar_strings("", "Marc") is False
        assert searcher._similar_strings("Marc", "") is False
