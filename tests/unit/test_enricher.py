"""
Tests for PKMEnricher — Workflow v2.1 Knowledge Application

Ce module teste l'application des extractions au PKM.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models.v2_models import (
    AnalysisResult,
    EmailAction,
    EnrichmentResult,
    Extraction,
    ExtractionType,
    ImportanceLevel,
    NoteAction,
)
from src.passepartout.enricher import PKMEnricher, EnricherError, create_enricher


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_note_manager():
    """Create a mock NoteManager"""
    manager = MagicMock()
    manager.create_note.return_value = "note_new_123"
    manager.add_info.return_value = True
    manager.get_note_by_title.return_value = None
    return manager


@pytest.fixture
def mock_omnifocus_client():
    """Create a mock OmniFocusClient"""
    client = AsyncMock()
    client.is_available.return_value = True

    # Create mock task
    mock_task = MagicMock()
    mock_task.task_id = "task_456"
    client.create_task.return_value = mock_task

    return client


@pytest.fixture
def mock_existing_note():
    """Create a mock existing note"""
    note = MagicMock()
    note.note_id = "note_existing_789"
    note.title = "Projet Alpha"
    return note


@pytest.fixture
def sample_extraction():
    """Create a sample extraction"""
    return Extraction(
        info="Budget validé 50k€",
        type=ExtractionType.DECISION,
        importance=ImportanceLevel.HAUTE,
        note_cible="Projet Alpha",
        note_action=NoteAction.ENRICHIR,
        omnifocus=False,
    )


@pytest.fixture
def sample_extraction_with_omnifocus():
    """Create a sample extraction with OmniFocus task"""
    return Extraction(
        info="Livraison MVP le 15 mars",
        type=ExtractionType.DEADLINE,
        importance=ImportanceLevel.HAUTE,
        note_cible="Projet Alpha",
        note_action=NoteAction.ENRICHIR,
        omnifocus=True,
    )


@pytest.fixture
def sample_extraction_create():
    """Create an extraction that requires note creation"""
    return Extraction(
        info="Marie Dupont, nouvelle directrice technique",
        type=ExtractionType.RELATION,
        importance=ImportanceLevel.HAUTE,
        note_cible="Marie Dupont",
        note_action=NoteAction.CREER,
        omnifocus=False,
    )


@pytest.fixture
def sample_analysis(sample_extraction):
    """Create a sample analysis result"""
    return AnalysisResult(
        extractions=[sample_extraction],
        action=EmailAction.ARCHIVE,
        confidence=0.92,
        raisonnement="Test analysis",
        model_used="haiku",
        tokens_used=500,
        duration_ms=1200.0,
    )


@pytest.fixture
def enricher(mock_note_manager, mock_omnifocus_client):
    """Create a PKMEnricher with mocks"""
    return PKMEnricher(
        note_manager=mock_note_manager,
        omnifocus_client=mock_omnifocus_client,
        omnifocus_enabled=True,
    )


# ============================================================================
# Initialization Tests
# ============================================================================


class TestPKMEnricherInit:
    """Tests for PKMEnricher initialization"""

    def test_init_with_all_params(self, mock_note_manager, mock_omnifocus_client):
        """Test initialization with all parameters"""
        enricher = PKMEnricher(
            note_manager=mock_note_manager,
            omnifocus_client=mock_omnifocus_client,
            omnifocus_enabled=True,
        )

        assert enricher.note_manager is mock_note_manager
        assert enricher.omnifocus_client is mock_omnifocus_client
        assert enricher.omnifocus_enabled is True

    def test_init_without_omnifocus(self, mock_note_manager):
        """Test initialization without OmniFocus client"""
        enricher = PKMEnricher(
            note_manager=mock_note_manager,
            omnifocus_client=None,
            omnifocus_enabled=True,
        )

        assert enricher.omnifocus_client is None
        assert enricher.omnifocus_enabled is False  # Auto-disabled without client

    def test_init_omnifocus_disabled(self, mock_note_manager, mock_omnifocus_client):
        """Test initialization with OmniFocus explicitly disabled"""
        enricher = PKMEnricher(
            note_manager=mock_note_manager,
            omnifocus_client=mock_omnifocus_client,
            omnifocus_enabled=False,
        )

        assert enricher.omnifocus_client is mock_omnifocus_client
        assert enricher.omnifocus_enabled is False


# ============================================================================
# Apply Tests
# ============================================================================


class TestPKMEnricherApply:
    """Tests for PKMEnricher.apply()"""

    @pytest.mark.asyncio
    async def test_apply_empty_extractions(self, enricher):
        """Test apply with no extractions"""
        analysis = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.95,
            raisonnement="No extractions",
            model_used="haiku",
            tokens_used=100,
            duration_ms=500.0,
        )

        result = await enricher.apply(analysis, "event_123")

        assert isinstance(result, EnrichmentResult)
        assert len(result.notes_updated) == 0
        assert len(result.notes_created) == 0
        assert len(result.tasks_created) == 0
        assert len(result.errors) == 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_apply_single_extraction_create(
        self, enricher, mock_note_manager, sample_extraction_create
    ):
        """Test apply with single extraction that creates note"""
        analysis = AnalysisResult(
            extractions=[sample_extraction_create],
            action=EmailAction.ARCHIVE,
            confidence=0.88,
            raisonnement="New person identified",
            model_used="haiku",
            tokens_used=400,
            duration_ms=1000.0,
        )

        result = await enricher.apply(analysis, "event_456")

        assert len(result.notes_created) == 1
        assert len(result.notes_updated) == 0
        assert result.notes_created[0] == "note_new_123"
        mock_note_manager.create_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_single_extraction_enrich(
        self, enricher, mock_note_manager, mock_existing_note, sample_extraction
    ):
        """Test apply with single extraction that enriches existing note"""
        # Setup: note exists
        mock_note_manager.get_note_by_title.return_value = mock_existing_note

        analysis = AnalysisResult(
            extractions=[sample_extraction],
            action=EmailAction.ARCHIVE,
            confidence=0.92,
            raisonnement="Budget decision",
            model_used="haiku",
            tokens_used=450,
            duration_ms=1100.0,
        )

        result = await enricher.apply(analysis, "event_789")

        assert len(result.notes_updated) == 1
        assert len(result.notes_created) == 0
        assert result.notes_updated[0] == "note_existing_789"
        mock_note_manager.add_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_extraction_with_omnifocus(
        self, enricher, mock_note_manager, mock_omnifocus_client,
        mock_existing_note, sample_extraction_with_omnifocus
    ):
        """Test apply with extraction that creates OmniFocus task"""
        mock_note_manager.get_note_by_title.return_value = mock_existing_note

        analysis = AnalysisResult(
            extractions=[sample_extraction_with_omnifocus],
            action=EmailAction.ARCHIVE,
            confidence=0.90,
            raisonnement="Deadline identified",
            model_used="haiku",
            tokens_used=400,
            duration_ms=1000.0,
        )

        result = await enricher.apply(analysis, "event_deadline")

        assert len(result.notes_updated) == 1
        assert len(result.tasks_created) == 1
        assert result.tasks_created[0] == "task_456"
        mock_omnifocus_client.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_multiple_extractions(
        self, enricher, mock_note_manager, mock_existing_note
    ):
        """Test apply with multiple extractions"""
        mock_note_manager.get_note_by_title.return_value = mock_existing_note

        extractions = [
            Extraction(
                info="Decision 1",
                type=ExtractionType.DECISION,
                importance=ImportanceLevel.HAUTE,
                note_cible="Projet Alpha",
                note_action=NoteAction.ENRICHIR,
                omnifocus=False,
            ),
            Extraction(
                info="Decision 2",
                type=ExtractionType.FAIT,
                importance=ImportanceLevel.MOYENNE,
                note_cible="Projet Alpha",
                note_action=NoteAction.ENRICHIR,
                omnifocus=False,
            ),
        ]

        analysis = AnalysisResult(
            extractions=extractions,
            action=EmailAction.ARCHIVE,
            confidence=0.85,
            raisonnement="Multiple extractions",
            model_used="sonnet",
            tokens_used=800,
            duration_ms=2000.0,
        )

        result = await enricher.apply(analysis, "event_multi")

        assert len(result.notes_updated) == 2
        assert len(result.notes_created) == 0
        assert mock_note_manager.add_info.call_count == 2

    @pytest.mark.asyncio
    async def test_apply_enrich_note_not_found_creates_new(
        self, enricher, mock_note_manager, sample_extraction
    ):
        """Test that enriching non-existent note creates it"""
        # Note not found
        mock_note_manager.get_note_by_title.return_value = None

        analysis = AnalysisResult(
            extractions=[sample_extraction],
            action=EmailAction.ARCHIVE,
            confidence=0.88,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=300,
            duration_ms=800.0,
        )

        result = await enricher.apply(analysis, "event_new")

        # Should create note since it doesn't exist
        assert len(result.notes_created) == 1
        mock_note_manager.create_note.assert_called_once()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestPKMEnricherErrors:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_apply_note_creation_error(self, enricher, mock_note_manager):
        """Test handling of note creation error"""
        mock_note_manager.create_note.side_effect = Exception("Database error")

        analysis = AnalysisResult(
            extractions=[
                Extraction(
                    info="Test info",
                    type=ExtractionType.FAIT,
                    importance=ImportanceLevel.MOYENNE,
                    note_cible="Test Note",
                    note_action=NoteAction.CREER,
                    omnifocus=False,
                )
            ],
            action=EmailAction.ARCHIVE,
            confidence=0.8,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=200,
            duration_ms=500.0,
        )

        result = await enricher.apply(analysis, "event_error")

        assert len(result.errors) == 1
        assert "Database error" in result.errors[0]
        assert result.success is False

    @pytest.mark.asyncio
    async def test_apply_add_info_returns_false(
        self, enricher, mock_note_manager, mock_existing_note, sample_extraction
    ):
        """Test handling when add_info returns False"""
        mock_note_manager.get_note_by_title.return_value = mock_existing_note
        mock_note_manager.add_info.return_value = False

        analysis = AnalysisResult(
            extractions=[sample_extraction],
            action=EmailAction.ARCHIVE,
            confidence=0.9,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=300,
            duration_ms=700.0,
        )

        result = await enricher.apply(analysis, "event_fail")

        assert len(result.errors) == 1
        assert "Failed to add info" in result.errors[0]

    @pytest.mark.asyncio
    async def test_apply_omnifocus_error_continues(
        self, enricher, mock_note_manager, mock_omnifocus_client,
        mock_existing_note, sample_extraction_with_omnifocus
    ):
        """Test that OmniFocus error doesn't stop enrichment"""
        from src.integrations.apple.omnifocus import OmniFocusError

        mock_note_manager.get_note_by_title.return_value = mock_existing_note
        mock_omnifocus_client.create_task.side_effect = OmniFocusError("OF not running")

        analysis = AnalysisResult(
            extractions=[sample_extraction_with_omnifocus],
            action=EmailAction.ARCHIVE,
            confidence=0.9,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=350,
            duration_ms=900.0,
        )

        result = await enricher.apply(analysis, "event_of_error")

        # Note should still be updated
        assert len(result.notes_updated) == 1
        # Task should not be created
        assert len(result.tasks_created) == 0
        # No error recorded (OmniFocus errors are warnings)
        assert len(result.errors) == 0


# ============================================================================
# Date Extraction Tests
# ============================================================================


class TestDateExtraction:
    """Tests for date extraction from info strings"""

    def test_extract_iso_date(self, enricher):
        """Test extraction of ISO format date"""
        info = "Livraison prévue le 2026-01-15"
        date = enricher._extract_date_from_info(info)
        assert date == "2026-01-15"

    def test_extract_french_date(self, enricher):
        """Test extraction of French format date"""
        info = "Réunion le 15 mars"
        date = enricher._extract_date_from_info(info)
        assert date is not None
        assert date.endswith("-03-15")

    def test_extract_french_date_with_er(self, enricher):
        """Test extraction of French date with 'er' suffix"""
        info = "Lancement le 1er avril"
        date = enricher._extract_date_from_info(info)
        assert date is not None
        assert "-04-01" in date

    def test_extract_no_date(self, enricher):
        """Test with no date in string"""
        info = "Budget validé pour le projet"
        date = enricher._extract_date_from_info(info)
        assert date is None


# ============================================================================
# Note Content Building Tests
# ============================================================================


class TestBuildNoteContent:
    """Tests for _build_note_content"""

    def test_build_content_decision(self, enricher):
        """Test content building for decision type"""
        extraction = Extraction(
            info="Budget approuvé",
            type=ExtractionType.DECISION,
            importance=ImportanceLevel.HAUTE,
            note_cible="Test",
            note_action=NoteAction.CREER,
        )

        content = enricher._build_note_content(extraction)

        assert "# Test" in content
        assert "## Decisions" in content
        assert "🔴" in content  # High importance
        assert "Budget approuvé" in content

    def test_build_content_moyenne_importance(self, enricher):
        """Test content building with moyenne importance"""
        extraction = Extraction(
            info="Fait notable",
            type=ExtractionType.FAIT,
            importance=ImportanceLevel.MOYENNE,
            note_cible="Test",
            note_action=NoteAction.CREER,
        )

        content = enricher._build_note_content(extraction)

        assert "🟡" in content  # Medium importance


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateEnricher:
    """Tests for create_enricher factory function"""

    def test_create_enricher_with_note_manager(self, mock_note_manager):
        """Test factory with provided note manager"""
        enricher = create_enricher(
            note_manager=mock_note_manager,
            omnifocus_enabled=False,
        )

        assert enricher.note_manager is mock_note_manager
        assert enricher.omnifocus_enabled is False

    def test_create_enricher_with_omnifocus(
        self, mock_note_manager, mock_omnifocus_client
    ):
        """Test factory with OmniFocus client"""
        enricher = create_enricher(
            note_manager=mock_note_manager,
            omnifocus_client=mock_omnifocus_client,
            omnifocus_enabled=True,
        )

        assert enricher.omnifocus_client is mock_omnifocus_client
        assert enricher.omnifocus_enabled is True
