"""
Tests for V2EmailProcessor — Workflow v2.1 Integration

Ce module teste l'intégration complète du pipeline v2.1.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.config_manager import WorkflowV2Config
from src.core.models.v2_models import (
    AnalysisResult,
    EmailAction,
    EnrichmentResult,
    Extraction,
    ExtractionType,
    ImportanceLevel,
    NoteAction,
)
from src.trivelin.v2_processor import (
    V2EmailProcessor,
    V2ProcessingResult,
    create_v2_processor,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Create a test configuration"""
    return WorkflowV2Config(
        enabled=True,
        default_model="haiku",
        escalation_model="sonnet",
        escalation_threshold=0.7,
        auto_apply_threshold=0.85,
        context_notes_count=3,
        omnifocus_enabled=False,
    )


@pytest.fixture
def mock_event():
    """Create a mock PerceivedEvent"""
    event = MagicMock()
    event.event_id = "test_event_123"
    event.event_type = MagicMock()
    event.event_type.value = "information"
    event.title = "Meeting Notes - Project Alpha"
    event.content = "Budget approved for 50k€. Marc will deliver MVP by March 15."
    event.source = "email"
    event.timestamp = datetime.now(timezone.utc)
    event.metadata = {"from_address": "marc@example.com"}
    return event


@pytest.fixture
def mock_analysis_result():
    """Create a mock analysis result"""
    return AnalysisResult(
        extractions=[
            Extraction(
                info="Budget approved 50k€",
                type=ExtractionType.DECISION,
                importance=ImportanceLevel.HAUTE,
                note_cible="Project Alpha",
                note_action=NoteAction.ENRICHIR,
                omnifocus=False,
            ),
            Extraction(
                info="MVP delivery March 15 (Marc)",
                type=ExtractionType.DEADLINE,
                importance=ImportanceLevel.HAUTE,
                note_cible="Project Alpha",
                note_action=NoteAction.ENRICHIR,
                omnifocus=True,
            ),
        ],
        action=EmailAction.ARCHIVE,
        confidence=0.92,
        raisonnement="Budget decision and deadline identified",
        model_used="haiku",
        tokens_used=500,
        duration_ms=1200.0,
    )


@pytest.fixture
def mock_enrichment_result():
    """Create a mock enrichment result"""
    return EnrichmentResult(
        notes_updated=["note_alpha_123"],
        notes_created=[],
        tasks_created=["task_deadline_456"],
        errors=[],
    )


@pytest.fixture
def mock_ai_router():
    """Create a mock AI router"""
    router = MagicMock()
    router._call_claude = MagicMock(
        return_value=(
            '{"extractions": [], "action": "archive", "confidence": 0.9, "raisonnement": "test"}',
            {"total_tokens": 100},
        )
    )
    return router


@pytest.fixture
def mock_note_manager():
    """Create a mock note manager"""
    manager = MagicMock()
    manager.create_note.return_value = "note_new_123"
    manager.add_info.return_value = True
    manager.get_note_by_title.return_value = None
    return manager


# ============================================================================
# V2ProcessingResult Tests
# ============================================================================


class TestV2ProcessingResult:
    """Tests for V2ProcessingResult dataclass"""

    def test_successful_result(self, mock_analysis_result, mock_enrichment_result):
        """Test successful processing result"""
        result = V2ProcessingResult(
            success=True,
            event_id="test_123",
            analysis=mock_analysis_result,
            enrichment=mock_enrichment_result,
            email_action=EmailAction.ARCHIVE,
            auto_applied=True,
            duration_ms=1500.0,
        )

        assert result.success is True
        assert result.extraction_count == 2
        assert result.notes_affected == 1
        assert result.tasks_created == 1
        assert result.auto_applied is True

    def test_failed_result(self):
        """Test failed processing result"""
        result = V2ProcessingResult(
            success=False,
            event_id="test_456",
            error="Analysis failed",
            duration_ms=500.0,
        )

        assert result.success is False
        assert result.extraction_count == 0
        assert result.notes_affected == 0
        assert result.error == "Analysis failed"

    def test_result_without_enrichment(self, mock_analysis_result):
        """Test result without enrichment (low confidence)"""
        result = V2ProcessingResult(
            success=True,
            event_id="test_789",
            analysis=mock_analysis_result,
            enrichment=None,
            email_action=EmailAction.QUEUE,
            auto_applied=False,
        )

        assert result.success is True
        assert result.extraction_count == 2
        assert result.notes_affected == 0
        assert result.auto_applied is False


# ============================================================================
# V2EmailProcessor Initialization Tests
# ============================================================================


class TestV2EmailProcessorInit:
    """Tests for V2EmailProcessor initialization"""

    def test_init_with_config(self, mock_config, mock_ai_router, mock_note_manager):
        """Test initialization with provided config"""
        with patch("src.trivelin.v2_processor.ContextEngine") as MockContextEngine:
            MockContextEngine.return_value = MagicMock()

            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            assert processor.config == mock_config
            assert processor.ai_router == mock_ai_router
            assert processor.note_manager == mock_note_manager
            assert processor.multi_pass_analyzer is not None
            assert processor.enricher is not None

    def test_init_omnifocus_disabled(self, mock_config, mock_ai_router, mock_note_manager):
        """Test initialization with OmniFocus disabled"""
        mock_config.omnifocus_enabled = False

        with patch("src.trivelin.v2_processor.ContextEngine"):
            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            assert processor.omnifocus_client is None


# ============================================================================
# Process Event Tests
# ============================================================================


class TestProcessEvent:
    """Tests for process_event method"""

    @pytest.mark.asyncio
    async def test_process_event_high_confidence(
        self,
        mock_config,
        mock_ai_router,
        mock_note_manager,
        mock_event,
        mock_analysis_result,
        mock_enrichment_result,
    ):
        """Test processing with high confidence triggers auto-apply"""
        with patch("src.trivelin.v2_processor.ContextEngine") as MockCE:
            MockCE.return_value = MagicMock()

            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            # Mock analyzer
            processor.multi_pass_analyzer.analyze = AsyncMock(return_value=mock_analysis_result)

            # Mock enricher
            processor.enricher.apply = AsyncMock(return_value=mock_enrichment_result)

            # Mock context retrieval
            processor._get_context_notes = AsyncMock(return_value=[])

            result = await processor.process_event(mock_event, auto_apply=True)

            assert result.success is True
            assert result.auto_applied is True
            processor.multi_pass_analyzer.analyze.assert_called_once()
            processor.enricher.apply.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_event_low_confidence_no_apply(
        self, mock_config, mock_ai_router, mock_note_manager, mock_event
    ):
        """Test processing with low confidence does not auto-apply"""
        # Create low confidence analysis
        low_conf_analysis = AnalysisResult(
            extractions=[],
            action=EmailAction.QUEUE,
            confidence=0.6,  # Below threshold
            raisonnement="Low confidence",
            model_used="haiku",
            tokens_used=300,
            duration_ms=800.0,
        )

        with patch("src.trivelin.v2_processor.ContextEngine"):
            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            processor.multi_pass_analyzer.analyze = AsyncMock(return_value=low_conf_analysis)
            processor._get_context_notes = AsyncMock(return_value=[])

            result = await processor.process_event(mock_event, auto_apply=True)

            assert result.success is True
            assert result.auto_applied is False
            assert result.enrichment is None

    @pytest.mark.asyncio
    async def test_process_event_auto_apply_disabled(
        self, mock_config, mock_ai_router, mock_note_manager, mock_event, mock_analysis_result
    ):
        """Test processing with auto_apply=False"""
        with patch("src.trivelin.v2_processor.ContextEngine"):
            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            processor.multi_pass_analyzer.analyze = AsyncMock(return_value=mock_analysis_result)
            processor._get_context_notes = AsyncMock(return_value=[])

            result = await processor.process_event(mock_event, auto_apply=False)

            assert result.success is True
            assert result.auto_applied is False
            assert result.enrichment is None

    @pytest.mark.asyncio
    async def test_process_event_error_handling(
        self, mock_config, mock_ai_router, mock_note_manager, mock_event
    ):
        """Test error handling during processing"""
        with patch("src.trivelin.v2_processor.ContextEngine"):
            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            processor.multi_pass_analyzer.analyze = AsyncMock(side_effect=Exception("API error"))
            processor._get_context_notes = AsyncMock(return_value=[])

            result = await processor.process_event(mock_event)

            assert result.success is False
            assert "API error" in result.error


# ============================================================================
# Batch Processing Tests
# ============================================================================


class TestProcessBatch:
    """Tests for process_batch method"""

    @pytest.mark.asyncio
    async def test_process_batch(
        self,
        mock_config,
        mock_ai_router,
        mock_note_manager,
        mock_event,
        mock_analysis_result,
        mock_enrichment_result,
    ):
        """Test batch processing multiple events"""
        events = [mock_event, mock_event, mock_event]

        with patch("src.trivelin.v2_processor.ContextEngine"):
            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            processor.multi_pass_analyzer.analyze = AsyncMock(return_value=mock_analysis_result)
            processor.enricher.apply = AsyncMock(return_value=mock_enrichment_result)
            processor._get_context_notes = AsyncMock(return_value=[])

            results = await processor.process_batch(events)

            assert len(results) == 3
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_process_batch_partial_failure(
        self, mock_config, mock_ai_router, mock_note_manager, mock_event, mock_analysis_result
    ):
        """Test batch processing with some failures"""
        events = [mock_event, mock_event]

        with patch("src.trivelin.v2_processor.ContextEngine"):
            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            # First succeeds, second fails
            processor.multi_pass_analyzer.analyze = AsyncMock(
                side_effect=[
                    mock_analysis_result,
                    Exception("Second failed"),
                ]
            )
            processor._get_context_notes = AsyncMock(return_value=[])

            results = await processor.process_batch(events)

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False


# ============================================================================
# Context Retrieval Tests
# ============================================================================


class TestContextRetrieval:
    """Tests for _get_context_notes method"""

    @pytest.mark.asyncio
    async def test_get_context_notes_success(
        self, mock_config, mock_ai_router, mock_note_manager, mock_event
    ):
        """Test successful context retrieval"""
        # Mock ContextItem structure
        mock_context_item = MagicMock()
        mock_context_item.content = "# Project Alpha\n\nProject notes content here"
        mock_context_item.relevance_score = 0.85
        mock_context_item.type = "semantic"
        mock_context_item.metadata = {
            "note_title": "Project Alpha",
            "note_type": "project",
            "note_id": "note_123",
        }

        mock_context_result = MagicMock()
        mock_context_result.context_items = [mock_context_item]

        with patch("src.trivelin.v2_processor.ContextEngine") as MockCE:
            mock_ce_instance = MagicMock()
            mock_ce_instance.retrieve_context = AsyncMock(return_value=mock_context_result)
            MockCE.return_value = mock_ce_instance

            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            context_notes = await processor._get_context_notes(mock_event)

            assert len(context_notes) == 1
            assert context_notes[0].title == "Project Alpha"
            assert context_notes[0].relevance == 0.85

    @pytest.mark.asyncio
    async def test_get_context_notes_error_returns_empty(
        self, mock_config, mock_ai_router, mock_note_manager, mock_event
    ):
        """Test that context retrieval errors return empty list"""
        with patch("src.trivelin.v2_processor.ContextEngine") as MockCE:
            mock_ce_instance = MagicMock()
            mock_ce_instance.retrieve_context = AsyncMock(side_effect=Exception("Search failed"))
            MockCE.return_value = mock_ce_instance

            processor = V2EmailProcessor(
                config=mock_config,
                ai_router=mock_ai_router,
                note_manager=mock_note_manager,
            )

            context_notes = await processor._get_context_notes(mock_event)

            assert context_notes == []


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateV2Processor:
    """Tests for create_v2_processor factory"""

    def test_create_with_config(self, mock_config):
        """Test factory with provided config"""
        with patch("src.trivelin.v2_processor.get_config") as mock_get_config:
            mock_app_config = MagicMock()
            mock_app_config.ai = MagicMock()
            mock_app_config.storage.notes_path = "/tmp/notes"
            mock_get_config.return_value = mock_app_config

            with patch("src.trivelin.v2_processor.get_ai_router"):
                with patch("src.trivelin.v2_processor.NoteManager"):
                    with patch("src.trivelin.v2_processor.ContextEngine"):
                        processor = create_v2_processor(config=mock_config)

                        assert processor.config == mock_config
