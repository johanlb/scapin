"""
Tests for Notes Search Service - Threshold and Title Boost

Tests the search_notes method filtering and ranking logic:
- Minimum score threshold (40%)
- Title boost (+50%)
- Result ordering
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.frontin.api.services.notes_service import NotesService


class MockNote:
    """Simple mock note for testing."""

    def __init__(
        self,
        note_id: str,
        title: str,
        content: str = "",
        tags: list[str] | None = None,
    ):
        self.note_id = note_id
        self.title = title
        self.content = content
        self.tags = tags or []
        self.entities = []
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metadata = {"path": "Test", "pinned": False}


@pytest.fixture
def mock_note_manager() -> MagicMock:
    """Create a mock NoteManager."""
    manager = MagicMock()
    return manager


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock ScapinConfig."""
    config = MagicMock()
    config.notes_dir = "/tmp/notes"
    return config


@pytest.fixture
def notes_service(mock_config: MagicMock, mock_note_manager: MagicMock) -> NotesService:
    """Create a NotesService with mocked dependencies."""
    service = NotesService(config=mock_config)

    # Patch the _get_manager method to return our mock
    with patch.object(service, "_get_manager", return_value=mock_note_manager):
        yield service


class TestSearchThreshold:
    """Tests for minimum score threshold (40%)."""

    @pytest.mark.asyncio
    async def test_filters_results_below_threshold(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Results with score < 40% should be filtered out."""
        # Setup: Notes with different L2 distances
        # L2 distance 1.5 -> score = 1/(1+1.5) = 0.4 (exactly at threshold)
        # L2 distance 2.0 -> score = 1/(1+2.0) = 0.33 (below threshold)
        # L2 distance 0.5 -> score = 1/(1+0.5) = 0.67 (above threshold)

        notes_with_scores = [
            (MockNote("note-1", "Good Match"), 0.5),  # 67% - above
            (MockNote("note-2", "Bad Match"), 2.0),  # 33% - below
            (MockNote("note-3", "Threshold Match"), 1.5),  # 40% - exactly at
        ]

        mock_note_manager.search_notes.return_value = notes_with_scores

        # Execute
        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.search_notes("test query")

        # Verify
        assert len(result.results) == 2  # note-2 should be filtered out
        note_ids = [r.note.id for r in result.results]
        assert "note-1" in note_ids
        assert "note-3" in note_ids
        assert "note-2" not in note_ids  # Below threshold

    @pytest.mark.asyncio
    async def test_threshold_is_40_percent(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Verify the threshold is exactly 40%."""
        # L2 distance 1.49 -> score = 1/(1+1.49) ≈ 0.401 (just above)
        # L2 distance 1.51 -> score = 1/(1+1.51) ≈ 0.398 (just below)

        notes_with_scores = [
            (MockNote("note-above", "Just Above"), 1.49),  # ~40.1%
            (MockNote("note-below", "Just Below"), 1.51),  # ~39.8%
        ]

        mock_note_manager.search_notes.return_value = notes_with_scores

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.search_notes("test")

        # Only the note just above threshold should pass
        assert len(result.results) == 1
        assert result.results[0].note.id == "note-above"


class TestTitleBoost:
    """Tests for title boost (+50%)."""

    @pytest.mark.asyncio
    async def test_title_match_gets_50_percent_boost(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Notes with query in title should get 1.5x score boost."""
        # Both notes have same L2 distance (0.5 -> base score 0.67)
        # But "Ramun Project" contains the query "ramun"

        notes_with_scores = [
            (MockNote("note-without", "Other Project"), 0.5),  # 67%
            (MockNote("note-with", "Ramun Project"), 0.5),  # 67% * 1.5 = 100%
        ]

        mock_note_manager.search_notes.return_value = notes_with_scores

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.search_notes("ramun")

        # Both should be included
        assert len(result.results) == 2

        # The title match should have higher score
        scores = {r.note.id: r.score for r in result.results}
        assert scores["note-with"] > scores["note-without"]

        # The title match should be capped at 1.0
        assert scores["note-with"] == 1.0  # 0.67 * 1.5 > 1.0, capped

    @pytest.mark.asyncio
    async def test_title_boost_case_insensitive(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Title matching should be case-insensitive."""
        notes_with_scores = [
            (MockNote("note-upper", "RAMUN Project"), 0.5),
            (MockNote("note-lower", "ramun project"), 0.5),
            (MockNote("note-mixed", "Ramun Project"), 0.5),
        ]

        mock_note_manager.search_notes.return_value = notes_with_scores

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.search_notes("ramun")

        # All three should get the boost
        for r in result.results:
            assert r.score == 1.0  # All boosted and capped

    @pytest.mark.asyncio
    async def test_title_boost_reorders_results(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Title match should reorder results to top."""
        # Note with title match but worse base score
        # should still rank higher after boost

        notes_with_scores = [
            (MockNote("better-base", "Other Note"), 0.3),  # 77% base
            (MockNote("worse-base", "Ramun Note"), 0.6),  # 62% base -> 93% boosted
        ]

        mock_note_manager.search_notes.return_value = notes_with_scores

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.search_notes("ramun")

        # "Ramun Note" should be first despite worse base score
        assert result.results[0].note.id == "worse-base"
        assert result.results[0].note.title == "Ramun Note"


class TestSearchIntegration:
    """Integration tests for the full search flow."""

    @pytest.mark.asyncio
    async def test_ramun_problem_fixed(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """
        Regression test for the Ramun problem.

        Previously "Ramun" query returned "RABAYE K et hia" with 93.8% score
        even though it didn't contain the word at all.
        """
        # Simulate the problematic scenario
        notes_with_scores = [
            # The irrelevant result with high L2 distance
            (MockNote("irrelevant", "RABAYE K et hia"), 0.065),  # Would be ~93.8%
            # The correct result if it exists
            (MockNote("correct", "Ramun"), 0.1),  # 91% + boost
        ]

        mock_note_manager.search_notes.return_value = notes_with_scores

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.search_notes("Ramun")

        # The correct "Ramun" note should be first due to title boost
        assert result.results[0].note.id == "correct"
        assert "Ramun" in result.results[0].note.title

    @pytest.mark.asyncio
    async def test_empty_results_when_all_below_threshold(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Search should return empty when all results are below threshold."""
        # All notes have very high L2 distance (bad matches)
        notes_with_scores = [
            (MockNote("note-1", "Unrelated A"), 5.0),  # 17%
            (MockNote("note-2", "Unrelated B"), 10.0),  # 9%
        ]

        mock_note_manager.search_notes.return_value = notes_with_scores

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.search_notes("specific term")

        # No results should pass the threshold
        assert len(result.results) == 0
        assert result.total == 0
