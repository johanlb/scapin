"""
Tests for Workflow v2.1 API Models and Router Logic

Ce module teste les modèles API et la logique du workflow d'extraction de connaissances.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock


# ============================================================================
# Model Validation Tests
# ============================================================================


class TestExtractionResponse:
    """Tests for ExtractionResponse model"""

    def test_extraction_response_model(self):
        """Test ExtractionResponse model"""
        from src.jeeves.api.models.workflow import ExtractionResponse

        extraction = ExtractionResponse(
            info="Test info",
            type="decision",
            importance="haute",
            note_cible="Test Note",
            note_action="enrichir",
            omnifocus=False,
        )

        assert extraction.info == "Test info"
        assert extraction.type == "decision"
        assert extraction.importance == "haute"
        assert extraction.note_cible == "Test Note"
        assert extraction.note_action == "enrichir"
        assert extraction.omnifocus is False

    def test_extraction_response_with_omnifocus(self):
        """Test ExtractionResponse with omnifocus enabled"""
        from src.jeeves.api.models.workflow import ExtractionResponse

        extraction = ExtractionResponse(
            info="Deadline task",
            type="deadline",
            importance="haute",
            note_cible="Project Alpha",
            note_action="enrichir",
            omnifocus=True,
        )

        assert extraction.omnifocus is True


class TestWorkflowConfigResponse:
    """Tests for WorkflowConfigResponse model"""

    def test_workflow_config_response_model(self):
        """Test WorkflowConfigResponse model"""
        from src.jeeves.api.models.workflow import WorkflowConfigResponse

        config = WorkflowConfigResponse(
            enabled=True,
            default_model="haiku",
            escalation_model="sonnet",
            escalation_threshold=0.7,
            auto_apply_threshold=0.85,
            context_notes_count=3,
            omnifocus_enabled=False,
            omnifocus_default_project="Inbox",
        )

        assert config.enabled is True
        assert config.default_model == "haiku"
        assert config.escalation_model == "sonnet"
        assert config.escalation_threshold == 0.7
        assert config.auto_apply_threshold == 0.85
        assert config.context_notes_count == 3
        assert config.omnifocus_enabled is False
        assert config.omnifocus_default_project == "Inbox"

    def test_workflow_config_response_disabled(self):
        """Test WorkflowConfigResponse when disabled"""
        from src.jeeves.api.models.workflow import WorkflowConfigResponse

        config = WorkflowConfigResponse(
            enabled=False,
            default_model="haiku",
            escalation_model="sonnet",
            escalation_threshold=0.7,
            auto_apply_threshold=0.85,
            context_notes_count=3,
            omnifocus_enabled=False,
            omnifocus_default_project="Inbox",
        )

        assert config.enabled is False


class TestV2ProcessingResponse:
    """Tests for V2ProcessingResponse model"""

    def test_v2_processing_response_success(self):
        """Test V2ProcessingResponse model for successful processing"""
        from src.jeeves.api.models.workflow import V2ProcessingResponse

        response = V2ProcessingResponse(
            success=True,
            event_id="test_123",
            email_action="archive",
            duration_ms=500.0,
            auto_applied=True,
            timestamp=datetime.now(timezone.utc),
        )

        assert response.success is True
        assert response.event_id == "test_123"
        assert response.email_action == "archive"
        assert response.auto_applied is True

    def test_v2_processing_response_failure(self):
        """Test V2ProcessingResponse model for failed processing"""
        from src.jeeves.api.models.workflow import V2ProcessingResponse

        response = V2ProcessingResponse(
            success=False,
            event_id="test_456",
            error="Analysis failed",
            email_action="rien",
            duration_ms=100.0,
            auto_applied=False,
            timestamp=datetime.now(timezone.utc),
        )

        assert response.success is False
        assert response.error == "Analysis failed"
        assert response.auto_applied is False


class TestAnalysisResultResponse:
    """Tests for AnalysisResultResponse model"""

    def test_analysis_result_response(self):
        """Test AnalysisResultResponse model"""
        from src.jeeves.api.models.workflow import (
            AnalysisResultResponse,
            ExtractionResponse,
        )

        response = AnalysisResultResponse(
            extractions=[
                ExtractionResponse(
                    info="Budget approved",
                    type="decision",
                    importance="haute",
                    note_cible="Project Alpha",
                    note_action="enrichir",
                    omnifocus=False,
                )
            ],
            action="archive",
            confidence=0.92,
            raisonnement="Budget decision identified",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1200.0,
            escalated=False,
        )

        assert len(response.extractions) == 1
        assert response.action == "archive"
        assert response.confidence == 0.92
        assert response.escalated is False

    def test_analysis_result_response_escalated(self):
        """Test AnalysisResultResponse when escalated"""
        from src.jeeves.api.models.workflow import AnalysisResultResponse

        response = AnalysisResultResponse(
            extractions=[],
            action="queue",
            confidence=0.75,
            raisonnement="Low confidence, escalated",
            model_used="sonnet",
            tokens_used=800,
            duration_ms=2500.0,
            escalated=True,
        )

        assert response.escalated is True
        assert response.model_used == "sonnet"


class TestEnrichmentResultResponse:
    """Tests for EnrichmentResultResponse model"""

    def test_enrichment_result_response(self):
        """Test EnrichmentResultResponse model"""
        from src.jeeves.api.models.workflow import EnrichmentResultResponse

        response = EnrichmentResultResponse(
            notes_updated=["note_123", "note_456"],
            notes_created=["note_new"],
            tasks_created=["task_789"],
            errors=[],
            success=True,
        )

        assert len(response.notes_updated) == 2
        assert len(response.notes_created) == 1
        assert len(response.tasks_created) == 1
        assert response.success is True

    def test_enrichment_result_response_with_errors(self):
        """Test EnrichmentResultResponse with errors"""
        from src.jeeves.api.models.workflow import EnrichmentResultResponse

        response = EnrichmentResultResponse(
            notes_updated=[],
            notes_created=[],
            tasks_created=[],
            errors=["Failed to create note", "OmniFocus unavailable"],
            success=False,
        )

        assert len(response.errors) == 2
        assert response.success is False


class TestWorkflowStatsResponse:
    """Tests for WorkflowStatsResponse model"""

    def test_workflow_stats_response(self):
        """Test WorkflowStatsResponse model"""
        from src.jeeves.api.models.workflow import WorkflowStatsResponse

        stats = WorkflowStatsResponse(
            events_processed=100,
            extractions_total=250,
            extractions_auto_applied=200,
            notes_created=50,
            notes_updated=150,
            tasks_created=25,
            escalations=10,
            average_confidence=0.87,
            average_duration_ms=1500.0,
        )

        assert stats.events_processed == 100
        assert stats.extractions_total == 250
        assert stats.average_confidence == 0.87

    def test_workflow_stats_response_defaults(self):
        """Test WorkflowStatsResponse default values"""
        from src.jeeves.api.models.workflow import WorkflowStatsResponse

        stats = WorkflowStatsResponse()

        assert stats.events_processed == 0
        assert stats.extractions_total == 0
        assert stats.average_confidence == 0.0


# ============================================================================
# Request Model Tests
# ============================================================================


class TestAnalyzeEmailRequest:
    """Tests for AnalyzeEmailRequest model"""

    def test_analyze_email_request(self):
        """Test AnalyzeEmailRequest model"""
        from src.jeeves.api.models.workflow import AnalyzeEmailRequest

        request = AnalyzeEmailRequest(
            email_id="msg_123",
            auto_apply=True,
        )

        assert request.email_id == "msg_123"
        assert request.auto_apply is True

    def test_analyze_email_request_auto_apply_default(self):
        """Test AnalyzeEmailRequest default auto_apply value"""
        from src.jeeves.api.models.workflow import AnalyzeEmailRequest

        request = AnalyzeEmailRequest(email_id="msg_456")

        assert request.auto_apply is True  # Default


class TestApplyExtractionsRequest:
    """Tests for ApplyExtractionsRequest model"""

    def test_apply_extractions_request(self):
        """Test ApplyExtractionsRequest model"""
        from src.jeeves.api.models.workflow import (
            ApplyExtractionsRequest,
            ExtractionResponse,
        )

        request = ApplyExtractionsRequest(
            event_id="event_123",
            extractions=[
                ExtractionResponse(
                    info="Test extraction",
                    type="fait",
                    importance="moyenne",
                    note_cible="Test Note",
                    note_action="enrichir",
                    omnifocus=False,
                )
            ],
        )

        assert request.event_id == "event_123"
        assert len(request.extractions) == 1


# ============================================================================
# Router Helper Function Tests
# ============================================================================


class TestGetV2Processor:
    """Tests for _get_v2_processor helper"""

    def test_get_processor_workflow_disabled(self):
        """Test that disabled workflow raises HTTPException"""
        from unittest.mock import patch

        mock_config = MagicMock()
        mock_config.workflow_v2.enabled = False

        with patch(
            "src.jeeves.api.routers.workflow.get_config",
            return_value=mock_config
        ):
            from src.jeeves.api.routers.workflow import _get_v2_processor
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                _get_v2_processor()

            assert exc_info.value.status_code == 400
            assert "not enabled" in exc_info.value.detail


# ============================================================================
# Stats Tracking Tests
# ============================================================================


class TestStatsTracking:
    """Tests for workflow stats tracking"""

    def test_stats_module_variable_exists(self):
        """Test that stats tracking variable exists"""
        from src.jeeves.api.routers import workflow

        assert hasattr(workflow, "_workflow_stats")
        assert "events_processed" in workflow._workflow_stats
        assert "extractions_total" in workflow._workflow_stats
        assert "notes_created" in workflow._workflow_stats

    def test_stats_can_be_updated(self):
        """Test that stats can be updated"""
        from src.jeeves.api.routers import workflow

        original_count = workflow._workflow_stats["events_processed"]
        workflow._workflow_stats["events_processed"] += 1

        assert workflow._workflow_stats["events_processed"] == original_count + 1

        # Reset
        workflow._workflow_stats["events_processed"] = original_count
