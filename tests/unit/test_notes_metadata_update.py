"""
Tests for Notes Metadata Update - PATCH endpoint

Tests the update_note_metadata method and endpoint:
- Individual field updates
- skip_revision behavior
- Partial updates (only specified fields change)
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.frontin.api.services.notes_service import NotesService


class MockMetadata:
    """Simple mock metadata for testing."""

    def __init__(
        self,
        note_id: str = "test-note-1",
        note_type: str = "autre",
        importance: str = "normal",
        auto_enrich: bool = True,
        web_search_enabled: bool = False,
        next_review: datetime | None = None,
    ):
        self.note_id = note_id
        self._note_type = note_type
        self._importance = importance
        self.auto_enrich = auto_enrich
        self.web_search_enabled = web_search_enabled
        self.next_review = next_review
        self.easiness_factor = 2.5
        self.repetition_number = 0
        self.interval_hours = 24.0
        self.last_quality = None
        self.review_count = 0

    @property
    def note_type(self):
        """Return note_type as an object with value attribute."""
        return MagicMock(value=self._note_type)

    @note_type.setter
    def note_type(self, value):
        """Allow setting note_type."""
        if hasattr(value, "value"):
            self._note_type = value.value
        else:
            self._note_type = str(value)

    @property
    def importance(self):
        """Return importance as an object with value attribute."""
        return MagicMock(value=self._importance)

    @importance.setter
    def importance(self, value):
        """Allow setting importance."""
        if hasattr(value, "value"):
            self._importance = value.value
        else:
            self._importance = str(value)


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock ScapinConfig."""
    config = MagicMock()
    config.notes_dir = "/tmp/notes"
    config.notes_metadata_path = "/tmp/notes/metadata.db"
    return config


@pytest.fixture
def notes_service(mock_config: MagicMock) -> NotesService:
    """Create a NotesService with mocked dependencies."""
    service = NotesService(config=mock_config)
    return service


class TestUpdateMetadata:
    """Tests for update_note_metadata method."""

    @pytest.mark.asyncio
    async def test_update_note_type(
        self, notes_service: NotesService
    ) -> None:
        """Updating note_type should change only that field."""
        metadata = MockMetadata(note_type="autre")
        mock_store = MagicMock()
        mock_store.get.return_value = metadata
        mock_store.save.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="test-note-1",
                note_type="personne",
            )

        assert result is not None
        assert metadata._note_type == "personne"
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_importance(
        self, notes_service: NotesService
    ) -> None:
        """Updating importance should change only that field."""
        metadata = MockMetadata(importance="normal")
        mock_store = MagicMock()
        mock_store.get.return_value = metadata
        mock_store.save.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="test-note-1",
                importance="high",
            )

        assert result is not None
        assert metadata._importance == "high"
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_auto_enrich(
        self, notes_service: NotesService
    ) -> None:
        """Updating auto_enrich boolean."""
        metadata = MockMetadata(auto_enrich=True)
        mock_store = MagicMock()
        mock_store.get.return_value = metadata
        mock_store.save.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="test-note-1",
                auto_enrich=False,
            )

        assert result is not None
        assert metadata.auto_enrich is False
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_web_search_enabled(
        self, notes_service: NotesService
    ) -> None:
        """Updating web_search_enabled boolean."""
        metadata = MockMetadata(web_search_enabled=False)
        mock_store = MagicMock()
        mock_store.get.return_value = metadata
        mock_store.save.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="test-note-1",
                web_search_enabled=True,
            )

        assert result is not None
        assert metadata.web_search_enabled is True
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_revision_true_sets_next_review_to_none(
        self, notes_service: NotesService
    ) -> None:
        """skip_revision=True should set next_review to None."""
        metadata = MockMetadata(next_review=datetime.now(timezone.utc))
        mock_store = MagicMock()
        mock_store.get.return_value = metadata
        mock_store.save.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="test-note-1",
                skip_revision=True,
            )

        assert result is not None
        assert metadata.next_review is None
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_revision_false_does_not_change_next_review(
        self, notes_service: NotesService
    ) -> None:
        """skip_revision=False should NOT change next_review."""
        original_next_review = datetime.now(timezone.utc)
        metadata = MockMetadata(next_review=original_next_review)
        mock_store = MagicMock()
        mock_store.get.return_value = metadata
        mock_store.save.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="test-note-1",
                skip_revision=False,
            )

        assert result is not None
        assert metadata.next_review == original_next_review  # Unchanged
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_note(
        self, notes_service: NotesService
    ) -> None:
        """Should return None if note doesn't exist."""
        mock_store = MagicMock()
        mock_store.get.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="nonexistent-note",
                importance="high",
            )

        assert result is None
        mock_store.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_fields_update(
        self, notes_service: NotesService
    ) -> None:
        """Should update multiple fields in one call."""
        metadata = MockMetadata(
            note_type="autre",
            importance="normal",
            auto_enrich=True,
        )
        mock_store = MagicMock()
        mock_store.get.return_value = metadata
        mock_store.save.return_value = None

        with patch(
            "src.passepartout.note_metadata.NoteMetadataStore",
            return_value=mock_store,
        ):
            result = await notes_service.update_note_metadata(
                note_id="test-note-1",
                note_type="projet",
                importance="high",
                auto_enrich=False,
            )

        assert result is not None
        assert metadata._note_type == "projet"
        assert metadata._importance == "high"
        assert metadata.auto_enrich is False
        mock_store.save.assert_called_once()
