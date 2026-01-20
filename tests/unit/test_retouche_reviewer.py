"""
Tests for RetoucheReviewer — Memory Cycles v2
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import NoteType
from src.passepartout.retouche_reviewer import (
    AnalysisResult,
    RetoucheAction,
    RetoucheActionResult,
    RetoucheContext,
    RetoucheReviewer,
    RetoucheResult,
)


@pytest.fixture
def mock_note_manager():
    """Create a mock NoteManager"""
    manager = MagicMock()
    manager.notes_dir = "/test/notes"
    return manager


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database"""
    return tmp_path / "test_meta.db"


@pytest.fixture
def metadata_store(temp_db):
    """Create metadata store with temp database"""
    return NoteMetadataStore(temp_db)


@pytest.fixture
def scheduler(metadata_store):
    """Create a scheduler"""
    return NoteScheduler(metadata_store)


@pytest.fixture
def reviewer(mock_note_manager, metadata_store, scheduler):
    """Create a RetoucheReviewer"""
    return RetoucheReviewer(
        note_manager=mock_note_manager,
        metadata_store=metadata_store,
        scheduler=scheduler,
    )


class TestRetoucheActionResult:
    """Tests for RetoucheActionResult dataclass"""

    def test_creation(self):
        """Test creating a RetoucheActionResult"""
        result = RetoucheActionResult(
            action_type=RetoucheAction.ENRICH,
            target="content",
            content="New content",
            confidence=0.9,
            reasoning="Test reasoning",
            applied=True,
            model_used="haiku",
        )

        assert result.action_type == RetoucheAction.ENRICH
        assert result.target == "content"
        assert result.confidence == 0.9
        assert result.applied is True


class TestRetoucheResult:
    """Tests for RetoucheResult dataclass"""

    def test_creation(self):
        """Test creating a RetoucheResult"""
        result = RetoucheResult(
            note_id="test-001",
            success=True,
            quality_before=50,
            quality_after=75,
            actions=[],
            questions_added=2,
            model_used="haiku",
            escalated=False,
            reasoning="Test completed",
        )

        assert result.note_id == "test-001"
        assert result.success is True
        assert result.quality_before == 50
        assert result.quality_after == 75


class TestRetoucheReviewer:
    """Tests for RetoucheReviewer"""

    @pytest.mark.asyncio
    async def test_review_note_not_found(self, reviewer, mock_note_manager):
        """Test review when note not found"""
        mock_note_manager.get_note.return_value = None

        result = await reviewer.review_note("nonexistent")

        assert result.success is False
        assert result.error == "Note not found"

    @pytest.mark.asyncio
    async def test_review_note_creates_metadata(
        self, reviewer, mock_note_manager, metadata_store
    ):
        """Test that review creates metadata if missing"""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "test-new"
        mock_note.title = "Test Note"
        mock_note.content = "Some content here " * 20  # > 100 words
        mock_note.file_path = "/test/notes/personne/test-new.md"
        mock_note.tags = []
        mock_note.metadata = {}

        mock_note_manager.get_note.return_value = mock_note
        mock_note_manager.search_notes.return_value = []

        result = await reviewer.review_note("test-new")

        assert result.success is True
        # Metadata should have been created
        metadata = metadata_store.get("test-new")
        assert metadata is not None

    @pytest.mark.asyncio
    async def test_rule_based_analysis(self, reviewer):
        """Test rule-based analysis without AI"""
        # Create context
        mock_note = MagicMock()
        mock_note.title = "Test Note"
        mock_note.content = "Long content " * 100  # > 500 words, < 2 sections

        context = RetoucheContext(
            note=mock_note,
            metadata=NoteMetadata(note_id="test-001"),
            linked_notes=[],
            word_count=600,  # > 500 words to trigger structure suggestion
            has_summary=False,
            section_count=1,  # < 2 sections
            question_count=0,
        )

        # Test rule-based analysis
        result = reviewer._rule_based_analysis(context)

        assert isinstance(result, AnalysisResult)
        assert result.model_used == "rules"
        # Should suggest structure due to long content with few sections
        structure_actions = [
            a for a in result.actions if a.action_type == RetoucheAction.STRUCTURE
        ]
        assert len(structure_actions) > 0

    def test_has_summary_detection(self, reviewer):
        """Test summary detection"""
        # Content with summary
        content_with_summary = """# Note
## Résumé
Ceci est un résumé.

## Contenu
Plus de détails ici.
"""
        assert reviewer._has_summary(content_with_summary) is True

        # Content without summary
        content_without = """# Note
## Introduction
Pas de résumé.
"""
        assert reviewer._has_summary(content_without) is False

    def test_extract_wikilinks(self, reviewer):
        """Test wikilink extraction"""
        content = """
        Some text with [[Link1]] and [[Link2|Display]] links.
        Also [[Another Link]].
        """
        links = reviewer._extract_wikilinks(content)

        assert "Link1" in links
        assert "Link2" in links
        assert "Another Link" in links

    def test_calculate_quality_score(self, reviewer):
        """Test quality score calculation"""
        mock_note = MagicMock()
        mock_note.title = "Test"
        mock_note.content = "Content"

        context = RetoucheContext(
            note=mock_note,
            metadata=NoteMetadata(note_id="test-001"),
            word_count=200,  # +10 points
            has_summary=True,  # +15 points
            section_count=3,  # +9 points
            linked_notes=[MagicMock(), MagicMock()],  # +4 points
        )

        analysis = AnalysisResult(
            actions=[],  # No actions needed
            confidence=0.9,
            model_used="rules",
            escalated=False,
            reasoning="Good",
        )

        score = reviewer._calculate_quality_score(context, analysis)

        # Base 50 + word_count bonus + summary + sections + links
        assert score >= 70

    def test_quality_to_sm2(self, reviewer):
        """Test quality score to SM-2 conversion"""
        assert reviewer._quality_to_sm2(95) == 5
        assert reviewer._quality_to_sm2(80) == 4
        assert reviewer._quality_to_sm2(65) == 3
        assert reviewer._quality_to_sm2(45) == 2
        assert reviewer._quality_to_sm2(25) == 1
        assert reviewer._quality_to_sm2(10) == 0

    def test_apply_summarize_action(self, reviewer):
        """Test applying summarize action"""
        content = """---
title: Test
---

# Content
Some text here.
"""
        action = RetoucheActionResult(
            action_type=RetoucheAction.SUMMARIZE,
            target="header",
            content="This is a summary",
            confidence=0.9,
            applied=True,
            model_used="rules",
        )

        result = reviewer._apply_action(content, action)

        assert "> **Résumé**: This is a summary" in result

    def test_apply_enrich_action(self, reviewer):
        """Test applying enrich action"""
        content = "Original content"
        action = RetoucheActionResult(
            action_type=RetoucheAction.ENRICH,
            target="content",
            content="Additional information",
            confidence=0.9,
            applied=True,
            model_used="rules",
        )

        result = reviewer._apply_action(content, action)

        assert "Original content" in result
        assert "Additional information" in result
