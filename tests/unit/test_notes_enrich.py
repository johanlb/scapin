"""
Tests for Notes Enrichment Endpoint

Tests the enrich_note method and endpoint:
- Default sources (cross_reference)
- Multiple sources
- Note not found handling
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.frontin.api.services.notes_service import NotesService


class MockNote:
    """Simple mock note for testing."""

    def __init__(
        self,
        note_id: str = "test-note-1",
        title: str = "Test Note",
        content: str = "# Test Note\n\nSome content with [[Link]] to another note.",
    ):
        self.note_id = note_id
        self.title = title
        self.content = content
        self.tags = []
        self.entities = []
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metadata = {"path": "Test", "pinned": False}


class MockMetadata:
    """Simple mock metadata for testing."""

    def __init__(
        self,
        note_id: str = "test-note-1",
        auto_enrich: bool = True,
        web_search_enabled: bool = False,
    ):
        self.note_id = note_id
        self.auto_enrich = auto_enrich
        self.web_search_enabled = web_search_enabled
        self.note_type = MagicMock(value="autre")
        self.importance = MagicMock(value="normal")


class MockEnrichmentResult:
    """Mock result from NoteEnricher."""

    def __init__(self, note_id: str = "test-note-1"):
        self.note_id = note_id
        self.enrichments = []
        self.gaps_identified = ["Section manquante: Contexte"]
        self.sources_used = []
        self.analysis_summary = "Aucun enrichissement identifié"


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock ScapinConfig."""
    config = MagicMock()
    config.notes_dir = "/tmp/notes"
    config.notes_metadata_path = "/tmp/notes/metadata.db"
    return config


@pytest.fixture
def mock_note_manager() -> MagicMock:
    """Create a mock NoteManager."""
    manager = MagicMock()
    return manager


@pytest.fixture
def notes_service(mock_config: MagicMock) -> NotesService:
    """Create a NotesService with mocked dependencies."""
    service = NotesService(config=mock_config)
    return service


class TestEnrichNote:
    """Tests for enrich_note method."""

    @pytest.mark.asyncio
    async def test_enrich_with_default_sources(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Enrich with default sources (cross_reference)."""
        note = MockNote()
        metadata = MockMetadata()
        enrichment_result = MockEnrichmentResult()

        mock_note_manager.get_note.return_value = note
        mock_note_manager.search_notes.return_value = []  # No linked notes found

        mock_store = MagicMock()
        mock_store.get.return_value = metadata

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=enrichment_result)

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.note_metadata.NoteMetadataStore",
                return_value=mock_store,
            ),
            patch(
                "src.passepartout.note_enricher.NoteEnricher",
                return_value=mock_enricher,
            ),
        ):
            result = await notes_service.enrich_note(note_id="test-note-1")

        assert result is not None
        assert result.note_id == "test-note-1"
        mock_enricher.enrich.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_with_multiple_sources(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Enrich with multiple sources."""
        note = MockNote()
        metadata = MockMetadata(web_search_enabled=True)
        enrichment_result = MockEnrichmentResult()

        mock_note_manager.get_note.return_value = note
        mock_note_manager.search_notes.return_value = []

        mock_store = MagicMock()
        mock_store.get.return_value = metadata

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=enrichment_result)

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.note_metadata.NoteMetadataStore",
                return_value=mock_store,
            ),
            patch(
                "src.passepartout.note_enricher.NoteEnricher",
                return_value=mock_enricher,
            ),
        ):
            result = await notes_service.enrich_note(
                note_id="test-note-1",
                sources=["cross_reference", "web_search"],
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_enrich_note_not_found(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Should return None if note not found."""
        mock_note_manager.get_note.return_value = None

        with patch.object(notes_service, "_get_manager", return_value=mock_note_manager):
            result = await notes_service.enrich_note(note_id="nonexistent-note")

        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_without_metadata_uses_defaults(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Should use default metadata if none exists."""
        note = MockNote()
        enrichment_result = MockEnrichmentResult()

        mock_note_manager.get_note.return_value = note
        mock_note_manager.search_notes.return_value = []

        mock_store = MagicMock()
        mock_store.get.return_value = None  # No metadata

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=enrichment_result)

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.note_metadata.NoteMetadataStore",
                return_value=mock_store,
            ),
            patch(
                "src.passepartout.note_enricher.NoteEnricher",
                return_value=mock_enricher,
            ),
        ):
            result = await notes_service.enrich_note(note_id="test-note-1")

        assert result is not None

    @pytest.mark.asyncio
    async def test_enrich_extracts_wikilinks(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Should extract wikilinks from content for cross-reference."""
        note = MockNote(content="# Test\n\nSee [[Alice]] and [[Bob]].")
        linked_note = MockNote(note_id="alice-note", title="Alice")
        metadata = MockMetadata()
        enrichment_result = MockEnrichmentResult()

        mock_note_manager.get_note.return_value = note
        # First search for Alice, then Bob
        mock_note_manager.search_notes.side_effect = [
            [(linked_note, 0.9)],  # Alice found
            [],  # Bob not found
        ]

        mock_store = MagicMock()
        mock_store.get.return_value = metadata

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=enrichment_result)

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.note_metadata.NoteMetadataStore",
                return_value=mock_store,
            ),
            patch(
                "src.passepartout.note_enricher.NoteEnricher",
                return_value=mock_enricher,
            ),
        ):
            result = await notes_service.enrich_note(
                note_id="test-note-1",
                sources=["cross_reference"],
            )

        assert result is not None
        # Verify search was called for each wikilink
        assert mock_note_manager.search_notes.call_count == 2

    @pytest.mark.asyncio
    async def test_enrich_web_search_requires_metadata_flag(
        self, notes_service: NotesService, mock_note_manager: MagicMock
    ) -> None:
        """Web search should only be enabled if metadata allows it."""
        note = MockNote()
        metadata = MockMetadata(web_search_enabled=False)  # Disabled
        enrichment_result = MockEnrichmentResult()

        mock_note_manager.get_note.return_value = note
        mock_note_manager.search_notes.return_value = []

        mock_store = MagicMock()
        mock_store.get.return_value = metadata

        captured_web_search = []

        class MockNoteEnricher:
            def __init__(self, ai_router=None, web_search_enabled=False):
                captured_web_search.append(web_search_enabled)

            async def enrich(self, note, metadata, context):
                return enrichment_result

        with (
            patch.object(notes_service, "_get_manager", return_value=mock_note_manager),
            patch(
                "src.passepartout.note_metadata.NoteMetadataStore",
                return_value=mock_store,
            ),
            patch(
                "src.passepartout.note_enricher.NoteEnricher",
                MockNoteEnricher,
            ),
        ):
            result = await notes_service.enrich_note(
                note_id="test-note-1",
                sources=["cross_reference", "web_search"],  # Request web search
            )

        assert result is not None
        # Web search should be False because metadata.web_search_enabled is False
        assert captured_web_search[0] is False
