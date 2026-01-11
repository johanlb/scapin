"""
Tests for PKMEnricher — Workflow v2.1 Knowledge Application

Ce module teste l'application des extractions au PKM.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.models.v2_models import (
    AnalysisResult,
    EmailAction,
    EnrichmentResult,
    Extraction,
    ExtractionType,
    ImportanceLevel,
    NoteAction,
)
from src.passepartout.enricher import PKMEnricher, create_enricher

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
def mock_calendar_client():
    """Create a mock CalendarClient"""
    client = AsyncMock()

    # Create mock event
    mock_event = MagicMock()
    mock_event.event_id = "event_789"
    client.create_event.return_value = mock_event

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
        calendar=False,
    )


@pytest.fixture
def sample_extraction_with_calendar():
    """Create a sample extraction with calendar event"""
    return Extraction(
        info="Réunion d'équipe le 25 janvier à 14h",
        type=ExtractionType.EVENEMENT,
        importance=ImportanceLevel.MOYENNE,
        note_cible="Réunions Équipe",
        note_action=NoteAction.ENRICHIR,
        omnifocus=False,
        calendar=True,
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
        assert "## Décisions" in content  # French section name
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

    def test_create_enricher_with_calendar(
        self, mock_note_manager, mock_calendar_client
    ):
        """Test factory with calendar client"""
        enricher = create_enricher(
            note_manager=mock_note_manager,
            omnifocus_enabled=False,
            calendar_client=mock_calendar_client,
            calendar_enabled=True,
        )

        assert enricher.calendar_client is mock_calendar_client
        assert enricher.calendar_enabled is True


# ============================================================================
# Calendar Integration Tests
# ============================================================================


class TestCalendarIntegration:
    """Tests for calendar event creation"""

    @pytest.fixture
    def enricher_with_calendar(self, mock_note_manager, mock_calendar_client):
        """Create enricher with calendar client"""
        return PKMEnricher(
            note_manager=mock_note_manager,
            calendar_client=mock_calendar_client,
            calendar_enabled=True,
        )

    def test_init_with_calendar(self, mock_note_manager, mock_calendar_client):
        """Test initialization with calendar client"""
        enricher = PKMEnricher(
            note_manager=mock_note_manager,
            calendar_client=mock_calendar_client,
            calendar_enabled=True,
        )

        assert enricher.calendar_client is mock_calendar_client
        assert enricher.calendar_enabled is True

    def test_init_without_calendar(self, mock_note_manager):
        """Test initialization without calendar client"""
        enricher = PKMEnricher(
            note_manager=mock_note_manager,
            calendar_enabled=True,  # enabled but no client
        )

        assert enricher.calendar_client is None
        assert enricher.calendar_enabled is False  # disabled because no client

    @pytest.mark.asyncio
    async def test_apply_extraction_with_calendar(
        self,
        enricher_with_calendar,
        mock_note_manager,
        mock_calendar_client,
        sample_extraction_with_calendar,
    ):
        """Test applying extraction that creates calendar event"""
        analysis = AnalysisResult(
            extractions=[sample_extraction_with_calendar],
            action=EmailAction.ARCHIVE,
            confidence=0.9,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1200.0,
        )

        result = await enricher_with_calendar.apply(analysis, "email_123")

        assert result.success is True
        assert len(result.notes_created) == 1
        assert len(result.events_created) == 1
        assert result.events_created[0] == "event_789"
        mock_calendar_client.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_calendar_disabled_no_event_created(
        self,
        mock_note_manager,
        mock_calendar_client,
        sample_extraction_with_calendar,
    ):
        """Test that calendar events are not created when disabled"""
        enricher = PKMEnricher(
            note_manager=mock_note_manager,
            calendar_client=mock_calendar_client,
            calendar_enabled=False,
        )

        analysis = AnalysisResult(
            extractions=[sample_extraction_with_calendar],
            action=EmailAction.ARCHIVE,
            confidence=0.9,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1200.0,
        )

        result = await enricher.apply(analysis, "email_123")

        assert result.success is True
        assert len(result.events_created) == 0
        mock_calendar_client.create_event.assert_not_called()


# ============================================================================
# DateTime Extraction Tests
# ============================================================================


class TestDateTimeExtraction:
    """Tests for _extract_datetime_from_info method"""

    @pytest.fixture
    def enricher(self, mock_note_manager):
        """Create enricher for testing"""
        return PKMEnricher(note_manager=mock_note_manager)

    def test_extract_iso_datetime(self, enricher):
        """Test extracting ISO format datetime - returns UTC"""
        result = enricher._extract_datetime_from_info("Event 2026-01-25 14:30")

        assert result is not None
        start, end = result
        assert start.year == 2026
        assert start.month == 1
        assert start.day == 25
        # 14:30 Paris (UTC+1 in winter) = 13:30 UTC
        assert start.hour == 13
        assert start.minute == 30

    def test_extract_french_date_with_time(self, enricher):
        """Test extracting French date with time - returns UTC"""
        result = enricher._extract_datetime_from_info("Réunion le 25 janvier à 14h30")

        assert result is not None
        start, end = result
        assert start.month == 1
        assert start.day == 25
        # 14:30 Paris (UTC+1 in winter) = 13:30 UTC
        assert start.hour == 13
        assert start.minute == 30

    def test_extract_french_date_without_time(self, enricher):
        """Test extracting French date without explicit time - returns UTC"""
        result = enricher._extract_datetime_from_info("Anniversaire le 15 mars")

        assert result is not None
        start, end = result
        assert start.month == 3
        assert start.day == 15
        # Default 9:00 Paris (UTC+1 in winter) = 8:00 UTC
        assert start.hour == 8

    def test_extract_date_with_hour_only(self, enricher):
        """Test extracting date with hour only (no minutes) - returns UTC"""
        result = enricher._extract_datetime_from_info("Meeting le 20 février à 10h")

        assert result is not None
        start, end = result
        assert start.month == 2
        assert start.day == 20
        # 10:00 Paris (UTC+1 in winter) = 9:00 UTC
        assert start.hour == 9
        assert start.minute == 0

    def test_extract_no_date(self, enricher):
        """Test that None is returned when no date found"""
        result = enricher._extract_datetime_from_info("Une note sans date")

        assert result is None

    def test_extract_event_duration(self, enricher):
        """Test that default duration is 1 hour"""
        result = enricher._extract_datetime_from_info("Meeting le 20 janvier à 14h")

        assert result is not None
        start, end = result
        # 14:00 Paris = 13:00 UTC (but duration check is independent of timezone)
        assert (end - start).total_seconds() == 3600  # 1 hour


# ============================================================================
# Timezone Indicator Tests
# ============================================================================


class TestTimezoneIndicators:
    """Tests for timezone indicator parsing (HF, HM, Paris)"""

    @pytest.fixture
    def enricher(self, mock_note_manager):
        """Create enricher for testing"""
        return PKMEnricher(note_manager=mock_note_manager)

    def test_extract_time_with_paris_indicator(self, enricher):
        """Test 9h Paris is parsed as Europe/Paris timezone"""
        result = enricher._extract_datetime_from_info(
            "Call le 20 janvier à 9h Paris"
        )

        assert result is not None
        start, end = result
        # 9:00 Paris (UTC+1 winter) = 8:00 UTC
        assert start.hour == 8
        assert start.minute == 0

    def test_extract_time_with_hf_indicator(self, enricher):
        """Test 14h HF (Heure France) is parsed as Europe/Paris timezone"""
        result = enricher._extract_datetime_from_info(
            "Réunion le 15 février à 14h HF"
        )

        assert result is not None
        start, end = result
        # 14:00 Paris (UTC+1 winter) = 13:00 UTC
        assert start.hour == 13
        assert start.minute == 0

    def test_extract_time_with_hm_indicator(self, enricher):
        """Test 10h HM (Heure Madagascar) is parsed as Indian/Antananarivo timezone"""
        result = enricher._extract_datetime_from_info(
            "Appel le 25 mars à 10h HM"
        )

        assert result is not None
        start, end = result
        # 10:00 Madagascar (UTC+3) = 7:00 UTC
        assert start.hour == 7
        assert start.minute == 0

    def test_extract_time_with_utc_indicator(self, enricher):
        """Test 12h UTC stays as UTC"""
        result = enricher._extract_datetime_from_info(
            "Sync le 10 avril à 12h UTC"
        )

        assert result is not None
        start, end = result
        # 12:00 UTC = 12:00 UTC (no conversion)
        assert start.hour == 12
        assert start.minute == 0

    def test_extract_time_case_insensitive(self, enricher):
        """Test timezone indicators are case-insensitive"""
        result = enricher._extract_datetime_from_info(
            "Meeting le 5 mai à 15h PARIS"
        )

        assert result is not None
        start, end = result
        # 15:00 Paris (UTC+2 summer) = 13:00 UTC
        # Note: May is in summer, so Paris is UTC+2
        assert start.hour == 13
        assert start.minute == 0

    def test_extract_time_without_indicator_uses_local(self, enricher):
        """Test that times without indicator default to local timezone (Paris)"""
        result = enricher._extract_datetime_from_info(
            "Réunion le 20 janvier à 14h"
        )

        assert result is not None
        start, end = result
        # 14:00 Paris (UTC+1 winter) = 13:00 UTC (default behavior)
        assert start.hour == 13

    def test_extract_time_with_minutes_and_tz(self, enricher):
        """Test parsing time with minutes and timezone indicator"""
        result = enricher._extract_datetime_from_info(
            "Call le 15 janvier à 9h30 HF"
        )

        assert result is not None
        start, end = result
        # 9:30 Paris (UTC+1) = 8:30 UTC
        assert start.hour == 8
        assert start.minute == 30

    def test_extract_time_with_maurice_indicator(self, enricher):
        """Test 9h Maurice (Port Louis) is parsed as Indian/Mauritius timezone"""
        result = enricher._extract_datetime_from_info(
            "Call le 20 janvier à 9h Maurice"
        )

        assert result is not None
        start, end = result
        # 9:00 Mauritius (UTC+4) = 5:00 UTC
        assert start.hour == 5
        assert start.minute == 0


# ============================================================================
# New V2.1.2 Field Tests
# ============================================================================


class TestExplicitTimezoneAndDuration:
    """Tests for explicit timezone and duration in _parse_explicit_datetime"""

    @pytest.fixture
    def enricher(self, mock_note_manager):
        """Create enricher for testing"""
        return PKMEnricher(note_manager=mock_note_manager)

    def test_explicit_timezone_hf(self, enricher):
        """Test explicit HF timezone in _parse_explicit_datetime"""
        result = enricher._parse_explicit_datetime(
            "2026-01-20", "14:00", timezone_str="HF"
        )

        assert result is not None
        start, end = result
        # 14:00 HF (Paris, UTC+1) = 13:00 UTC
        assert start.hour == 13
        assert start.minute == 0

    def test_explicit_timezone_hm(self, enricher):
        """Test explicit HM timezone in _parse_explicit_datetime"""
        result = enricher._parse_explicit_datetime(
            "2026-01-20", "10:00", timezone_str="HM"
        )

        assert result is not None
        start, end = result
        # 10:00 HM (Madagascar, UTC+3) = 7:00 UTC
        assert start.hour == 7
        assert start.minute == 0

    def test_explicit_timezone_maurice(self, enricher):
        """Test explicit Maurice timezone in _parse_explicit_datetime"""
        result = enricher._parse_explicit_datetime(
            "2026-01-20", "09:00", timezone_str="maurice"
        )

        assert result is not None
        start, end = result
        # 9:00 Maurice (UTC+4) = 5:00 UTC
        assert start.hour == 5
        assert start.minute == 0

    def test_explicit_duration_90_minutes(self, enricher):
        """Test explicit duration of 90 minutes"""
        result = enricher._parse_explicit_datetime(
            "2026-01-20", "14:00", duration_minutes=90
        )

        assert result is not None
        start, end = result
        # Duration should be 90 minutes
        assert (end - start).total_seconds() == 90 * 60

    def test_explicit_duration_30_minutes(self, enricher):
        """Test explicit duration of 30 minutes"""
        result = enricher._parse_explicit_datetime(
            "2026-01-20", "14:00", duration_minutes=30
        )

        assert result is not None
        start, end = result
        # Duration should be 30 minutes
        assert (end - start).total_seconds() == 30 * 60

    def test_default_duration_60_minutes(self, enricher):
        """Test default duration is 60 minutes when not specified"""
        result = enricher._parse_explicit_datetime(
            "2026-01-20", "14:00"
        )

        assert result is not None
        start, end = result
        # Default duration should be 60 minutes
        assert (end - start).total_seconds() == 60 * 60

    def test_combined_timezone_and_duration(self, enricher):
        """Test combining explicit timezone and duration"""
        result = enricher._parse_explicit_datetime(
            "2026-01-20", "10:00", timezone_str="HM", duration_minutes=120
        )

        assert result is not None
        start, end = result
        # 10:00 HM (UTC+3) = 7:00 UTC
        assert start.hour == 7
        # Duration should be 120 minutes
        assert (end - start).total_seconds() == 120 * 60


class TestExtractionNewFields:
    """Tests for new Extraction fields: priority, project, has_attachments"""

    @pytest.fixture
    def mock_note_manager(self):
        """Create a mock NoteManager"""
        from unittest.mock import MagicMock
        manager = MagicMock()
        manager.create_note.return_value = "note_new_123"
        manager.add_info.return_value = True
        manager.get_note_by_title.return_value = None
        return manager

    @pytest.fixture
    def mock_omnifocus_client(self):
        """Create a mock OmniFocusClient"""
        from unittest.mock import AsyncMock, MagicMock
        client = AsyncMock()
        client.is_available.return_value = True
        mock_task = MagicMock()
        mock_task.task_id = "task_456"
        client.create_task.return_value = mock_task
        return client

    @pytest.fixture
    def enricher_with_omnifocus(self, mock_note_manager, mock_omnifocus_client):
        """Create enricher with OmniFocus"""
        return PKMEnricher(
            note_manager=mock_note_manager,
            omnifocus_client=mock_omnifocus_client,
            omnifocus_enabled=True,
        )

    @pytest.mark.asyncio
    async def test_omnifocus_uses_explicit_project(
        self, enricher_with_omnifocus, mock_note_manager, mock_omnifocus_client
    ):
        """Test that explicit project field is used for OmniFocus tasks"""
        from src.core.models.v2_models import (
            AnalysisResult, EmailAction, Extraction, ExtractionType,
            ImportanceLevel, NoteAction
        )

        extraction = Extraction(
            info="Deadline urgente",
            type=ExtractionType.DEADLINE,
            importance=ImportanceLevel.HAUTE,
            note_cible="Notes Générales",
            note_action=NoteAction.CREER,
            omnifocus=True,
            date="2026-01-20",
            project="Mon Projet Spécifique",  # Explicit project
        )

        analysis = AnalysisResult(
            extractions=[extraction],
            action=EmailAction.ARCHIVE,
            confidence=0.9,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1000.0,
        )

        await enricher_with_omnifocus.apply(analysis, "email_test")

        # Check that create_task was called with the explicit project
        mock_omnifocus_client.create_task.assert_called_once()
        call_kwargs = mock_omnifocus_client.create_task.call_args.kwargs
        assert call_kwargs["project"] == "Mon Projet Spécifique"

    @pytest.mark.asyncio
    async def test_omnifocus_uses_explicit_date(
        self, enricher_with_omnifocus, mock_note_manager, mock_omnifocus_client
    ):
        """Test that explicit date field is used for OmniFocus tasks"""
        from src.core.models.v2_models import (
            AnalysisResult, EmailAction, Extraction, ExtractionType,
            ImportanceLevel, NoteAction
        )

        extraction = Extraction(
            info="Livraison importante",
            type=ExtractionType.DEADLINE,
            importance=ImportanceLevel.HAUTE,
            note_cible="Projet Test",
            note_action=NoteAction.CREER,
            omnifocus=True,
            date="2026-03-15",  # Explicit date
        )

        analysis = AnalysisResult(
            extractions=[extraction],
            action=EmailAction.ARCHIVE,
            confidence=0.9,
            raisonnement="Test",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1000.0,
        )

        await enricher_with_omnifocus.apply(analysis, "email_test")

        # Check that create_task was called with the explicit date
        mock_omnifocus_client.create_task.assert_called_once()
        call_kwargs = mock_omnifocus_client.create_task.call_args.kwargs
        assert call_kwargs["due_date"] == "2026-03-15"
