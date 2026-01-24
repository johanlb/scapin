"""
Tests for Notes Hygiene Endpoint

Tests the run_hygiene method and endpoint:
- Temporal references detection
- Completed tasks detection
- Missing links detection
- Formatting issues detection
- Health score calculation
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.frontin.api.services.notes_service import NotesService


class MockNote:
    """Simple mock note for testing."""

    def __init__(
        self,
        note_id: str = "test-note-1",
        title: str = "Test Note",
        content: str = "# Test Note\n\nSome content.",
    ):
        self.note_id = note_id
        self.title = title
        self.content = content
        self.tags = []
        self.entities = []
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metadata = {"path": "Test", "pinned": False}


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock ScapinConfig."""
    config = MagicMock()
    config.notes_dir = "/tmp/notes"
    config.data_path = MagicMock()
    config.data_path.__truediv__ = MagicMock(return_value="/tmp/notes/metadata.db")
    return config


@pytest.fixture
def mock_note_manager() -> MagicMock:
    """Create a mock NoteManager."""
    manager = MagicMock()
    manager.notes_dir = "/tmp/notes"
    return manager


@pytest.fixture
def notes_service(mock_config: MagicMock) -> NotesService:
    """Create a NotesService with mocked dependencies."""
    service = NotesService(config=mock_config)
    return service


class TestRunHygiene:
    """Tests for run_hygiene method."""

    @pytest.mark.asyncio
    async def test_hygiene_returns_result_for_valid_note(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Hygiene returns HygieneResultResponse for valid note."""
        note = MockNote()
        mock_note_manager.get_note.return_value = note
        mock_note_manager.get_linked_notes.return_value = []

        mock_reviewer = MagicMock()
        mock_reviewer._check_temporal_references.return_value = []
        mock_reviewer._check_completed_tasks.return_value = []
        mock_reviewer._check_missing_links.return_value = []
        mock_reviewer._check_formatting.return_value = []

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.retouche_reviewer.RetoucheReviewer",
                return_value=mock_reviewer,
            ),
        ):
            result = await notes_service.run_hygiene(note_id="test-note-1")

        assert result is not None
        assert result.note_id == "test-note-1"
        assert result.model_used == "rule-based"
        assert result.issues == []
        assert result.summary.total_issues == 0
        assert result.summary.health_score == 1.0

    @pytest.mark.asyncio
    async def test_hygiene_returns_none_for_missing_note(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Hygiene returns None if note not found."""
        mock_note_manager.get_note.return_value = None

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.run_hygiene(note_id="nonexistent-note")

        assert result is None

    @pytest.mark.asyncio
    async def test_hygiene_detects_temporal_issues(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Hygiene detects temporal reference issues."""
        note = MockNote(content="# Test\n\nDemain je ferai ceci.")
        mock_note_manager.get_note.return_value = note
        mock_note_manager.get_linked_notes.return_value = []

        mock_reviewer = MagicMock()
        mock_reviewer._check_temporal_references.return_value = [
            {
                "text": "Demain",
                "confidence": 0.85,
                "reason": "Référence temporelle obsolète: 'Demain'",
            }
        ]
        mock_reviewer._check_completed_tasks.return_value = []
        mock_reviewer._check_missing_links.return_value = []
        mock_reviewer._check_formatting.return_value = []

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.retouche_reviewer.RetoucheReviewer",
                return_value=mock_reviewer,
            ),
        ):
            result = await notes_service.run_hygiene(note_id="test-note-1")

        assert result is not None
        assert len(result.issues) == 1
        assert result.issues[0].type == "temporal"
        assert result.issues[0].severity == "warning"
        assert result.summary.total_issues == 1

    @pytest.mark.asyncio
    async def test_hygiene_detects_completed_tasks(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Hygiene detects completed tasks."""
        note = MockNote(content="# Tasks\n\n[x] Task done")
        mock_note_manager.get_note.return_value = note
        mock_note_manager.get_linked_notes.return_value = []

        mock_reviewer = MagicMock()
        mock_reviewer._check_temporal_references.return_value = []
        mock_reviewer._check_completed_tasks.return_value = [
            {
                "text": "[x] Task done",
                "confidence": 0.75,
                "reason": "Tâche terminée",
            }
        ]
        mock_reviewer._check_missing_links.return_value = []
        mock_reviewer._check_formatting.return_value = []

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.retouche_reviewer.RetoucheReviewer",
                return_value=mock_reviewer,
            ),
        ):
            result = await notes_service.run_hygiene(note_id="test-note-1")

        assert result is not None
        assert len(result.issues) == 1
        assert result.issues[0].type == "task"
        assert result.issues[0].severity == "info"

    @pytest.mark.asyncio
    async def test_hygiene_health_score_decreases_with_issues(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Health score decreases based on issue severity."""
        note = MockNote()
        mock_note_manager.get_note.return_value = note
        mock_note_manager.get_linked_notes.return_value = []

        mock_reviewer = MagicMock()
        # 2 warnings = -0.2, 3 info = -0.06 => health = 0.74
        mock_reviewer._check_temporal_references.return_value = [
            {"confidence": 0.8, "reason": "Issue 1"},
            {"confidence": 0.8, "reason": "Issue 2"},
        ]
        mock_reviewer._check_completed_tasks.return_value = [
            {"confidence": 0.75, "reason": "Task 1"},
            {"confidence": 0.75, "reason": "Task 2"},
            {"confidence": 0.75, "reason": "Task 3"},
        ]
        mock_reviewer._check_missing_links.return_value = []
        mock_reviewer._check_formatting.return_value = []

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.retouche_reviewer.RetoucheReviewer",
                return_value=mock_reviewer,
            ),
        ):
            result = await notes_service.run_hygiene(note_id="test-note-1")

        assert result is not None
        assert result.summary.total_issues == 5
        # 2 warnings (-0.2) + 3 info (-0.06) = 0.74
        assert result.summary.health_score == pytest.approx(0.74, abs=0.01)

    @pytest.mark.asyncio
    async def test_hygiene_includes_duration_ms(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Hygiene result includes duration in milliseconds."""
        note = MockNote()
        mock_note_manager.get_note.return_value = note
        mock_note_manager.get_linked_notes.return_value = []

        mock_reviewer = MagicMock()
        mock_reviewer._check_temporal_references.return_value = []
        mock_reviewer._check_completed_tasks.return_value = []
        mock_reviewer._check_missing_links.return_value = []
        mock_reviewer._check_formatting.return_value = []

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.retouche_reviewer.RetoucheReviewer",
                return_value=mock_reviewer,
            ),
        ):
            result = await notes_service.run_hygiene(note_id="test-note-1")

        assert result is not None
        assert result.duration_ms >= 0
        assert isinstance(result.duration_ms, int)
