"""
Tests for Multi-Pass Analysis API Models (v2.3)

Tests for PassHistoryEntryResponse and MultiPassMetadataResponse models.
"""

import pytest
from pydantic import ValidationError

from src.jeeves.api.models.queue import (
    MultiPassMetadataResponse,
    PassHistoryEntryResponse,
    QueueItemAnalysis,
)


class TestPassHistoryEntryResponse:
    """Tests for PassHistoryEntryResponse model"""

    def test_minimal_valid_entry(self) -> None:
        """Test creating entry with only required fields"""
        entry = PassHistoryEntryResponse(
            pass_number=1,
            pass_type="blind",
            model="haiku",
        )

        assert entry.pass_number == 1
        assert entry.pass_type == "blind"
        assert entry.model == "haiku"
        # Check defaults
        assert entry.duration_ms == 0.0
        assert entry.tokens == 0
        assert entry.confidence_before == 0.0
        assert entry.confidence_after == 0.0
        assert entry.context_searched is False
        assert entry.notes_found == 0
        assert entry.escalation_triggered is False

    def test_full_entry(self) -> None:
        """Test creating entry with all fields"""
        entry = PassHistoryEntryResponse(
            pass_number=2,
            pass_type="refine",
            model="sonnet",
            duration_ms=1234.5,
            tokens=589,
            confidence_before=0.67,
            confidence_after=0.85,
            context_searched=True,
            notes_found=3,
            escalation_triggered=False,
        )

        assert entry.pass_number == 2
        assert entry.pass_type == "refine"
        assert entry.model == "sonnet"
        assert entry.duration_ms == 1234.5
        assert entry.tokens == 589
        assert entry.confidence_before == 0.67
        assert entry.confidence_after == 0.85
        assert entry.context_searched is True
        assert entry.notes_found == 3
        assert entry.escalation_triggered is False

    def test_pass_types(self) -> None:
        """Test all valid pass types"""
        for pass_type in ["blind", "refine", "deep", "expert"]:
            entry = PassHistoryEntryResponse(
                pass_number=1,
                pass_type=pass_type,
                model="haiku",
            )
            assert entry.pass_type == pass_type

    def test_models(self) -> None:
        """Test all valid models"""
        for model in ["haiku", "sonnet", "opus"]:
            entry = PassHistoryEntryResponse(
                pass_number=1,
                pass_type="blind",
                model=model,
            )
            assert entry.model == model

    def test_missing_required_field(self) -> None:
        """Test that missing required fields raise validation error"""
        with pytest.raises(ValidationError):
            PassHistoryEntryResponse(
                pass_number=1,
                # missing pass_type and model
            )

    def test_json_serialization(self) -> None:
        """Test JSON serialization"""
        entry = PassHistoryEntryResponse(
            pass_number=3,
            pass_type="deep",
            model="sonnet",
            confidence_before=0.85,
            confidence_after=0.92,
        )

        json_data = entry.model_dump()
        assert json_data["pass_number"] == 3
        assert json_data["pass_type"] == "deep"
        assert json_data["model"] == "sonnet"


class TestMultiPassMetadataResponse:
    """Tests for MultiPassMetadataResponse model"""

    def test_minimal_valid_metadata(self) -> None:
        """Test creating metadata with only required fields"""
        metadata = MultiPassMetadataResponse(
            passes_count=1,
            final_model="haiku",
        )

        assert metadata.passes_count == 1
        assert metadata.final_model == "haiku"
        # Check defaults
        assert metadata.models_used == []
        assert metadata.escalated is False
        assert metadata.stop_reason == ""
        assert metadata.high_stakes is False
        assert metadata.total_tokens == 0
        assert metadata.total_duration_ms == 0.0
        assert metadata.pass_history == []

    def test_full_metadata(self) -> None:
        """Test creating metadata with all fields"""
        pass_history = [
            PassHistoryEntryResponse(
                pass_number=1,
                pass_type="blind",
                model="haiku",
                confidence_before=0.0,
                confidence_after=0.67,
            ),
            PassHistoryEntryResponse(
                pass_number=2,
                pass_type="refine",
                model="sonnet",
                confidence_before=0.67,
                confidence_after=0.85,
                context_searched=True,
                notes_found=3,
            ),
            PassHistoryEntryResponse(
                pass_number=3,
                pass_type="refine",
                model="sonnet",
                confidence_before=0.85,
                confidence_after=0.92,
            ),
        ]

        metadata = MultiPassMetadataResponse(
            passes_count=3,
            final_model="sonnet",
            models_used=["haiku", "sonnet", "sonnet"],
            escalated=True,
            stop_reason="confidence_sufficient",
            high_stakes=False,
            total_tokens=1247,
            total_duration_ms=2345.6,
            pass_history=pass_history,
        )

        assert metadata.passes_count == 3
        assert metadata.final_model == "sonnet"
        assert metadata.models_used == ["haiku", "sonnet", "sonnet"]
        assert metadata.escalated is True
        assert metadata.stop_reason == "confidence_sufficient"
        assert metadata.high_stakes is False
        assert metadata.total_tokens == 1247
        assert metadata.total_duration_ms == 2345.6
        assert len(metadata.pass_history) == 3

    def test_stop_reasons(self) -> None:
        """Test various stop reasons"""
        for stop_reason in ["confidence_sufficient", "max_passes", "no_changes"]:
            metadata = MultiPassMetadataResponse(
                passes_count=2,
                final_model="sonnet",
                stop_reason=stop_reason,
            )
            assert metadata.stop_reason == stop_reason

    def test_high_stakes_flag(self) -> None:
        """Test high stakes flag"""
        metadata = MultiPassMetadataResponse(
            passes_count=5,
            final_model="opus",
            high_stakes=True,
        )
        assert metadata.high_stakes is True

    def test_json_serialization_with_history(self) -> None:
        """Test JSON serialization includes nested pass history"""
        metadata = MultiPassMetadataResponse(
            passes_count=2,
            final_model="sonnet",
            models_used=["haiku", "sonnet"],
            pass_history=[
                PassHistoryEntryResponse(
                    pass_number=1,
                    pass_type="blind",
                    model="haiku",
                ),
                PassHistoryEntryResponse(
                    pass_number=2,
                    pass_type="refine",
                    model="sonnet",
                ),
            ],
        )

        json_data = metadata.model_dump()
        assert len(json_data["pass_history"]) == 2
        assert json_data["pass_history"][0]["model"] == "haiku"
        assert json_data["pass_history"][1]["model"] == "sonnet"


class TestQueueItemAnalysisWithMultiPass:
    """Tests for QueueItemAnalysis with multi_pass field"""

    def test_analysis_without_multi_pass(self) -> None:
        """Test analysis works without multi_pass (legacy)"""
        analysis = QueueItemAnalysis(
            action="archive",
            confidence=85.0,
        )

        assert analysis.multi_pass is None

    def test_analysis_with_multi_pass(self) -> None:
        """Test analysis with multi_pass metadata"""
        multi_pass = MultiPassMetadataResponse(
            passes_count=3,
            final_model="sonnet",
            models_used=["haiku", "sonnet", "sonnet"],
            escalated=True,
            stop_reason="confidence_sufficient",
            total_tokens=1247,
            total_duration_ms=2345.6,
        )

        analysis = QueueItemAnalysis(
            action="reply",
            confidence=92.0,
            reasoning="Question directe nécessitant réponse",
            multi_pass=multi_pass,
        )

        assert analysis.multi_pass is not None
        assert analysis.multi_pass.passes_count == 3
        assert analysis.multi_pass.final_model == "sonnet"
        assert analysis.multi_pass.escalated is True

    def test_analysis_json_includes_multi_pass(self) -> None:
        """Test JSON serialization includes multi_pass"""
        analysis = QueueItemAnalysis(
            action="archive",
            confidence=75.0,
            multi_pass=MultiPassMetadataResponse(
                passes_count=1,
                final_model="haiku",
                stop_reason="confidence_sufficient",
            ),
        )

        json_data = analysis.model_dump()
        assert "multi_pass" in json_data
        assert json_data["multi_pass"]["passes_count"] == 1
        assert json_data["multi_pass"]["final_model"] == "haiku"


class TestBuildMultiPassMetadata:
    """Tests for QueueService._build_multi_pass_metadata method"""

    def test_build_metadata_single_pass(self) -> None:
        """Test building metadata for single pass analysis"""
        from unittest.mock import MagicMock
        from src.jeeves.api.services.queue_service import QueueService

        # Create mock result
        mock_confidence = MagicMock()
        mock_confidence.overall = 0.95

        mock_pass = MagicMock()
        mock_pass.pass_number = 1
        mock_pass.pass_type = MagicMock(value="blind")
        mock_pass.model_used = "haiku"
        mock_pass.duration_ms = 800.0
        mock_pass.tokens_used = 312
        mock_pass.confidence = mock_confidence

        mock_result = MagicMock()
        mock_result.passes_count = 1
        mock_result.final_model = "haiku"
        mock_result.escalated = False
        mock_result.stop_reason = "confidence_sufficient"
        mock_result.high_stakes = False
        mock_result.total_tokens = 312
        mock_result.total_duration_ms = 800.0
        mock_result.pass_history = [mock_pass]
        mock_result.retrieved_context = None

        # Create service and call method
        service = QueueService.__new__(QueueService)
        metadata = service._build_multi_pass_metadata(mock_result)

        assert metadata["passes_count"] == 1
        assert metadata["final_model"] == "haiku"
        assert metadata["models_used"] == ["haiku"]
        assert metadata["escalated"] is False
        assert len(metadata["pass_history"]) == 1
        assert metadata["pass_history"][0]["model"] == "haiku"
        assert metadata["pass_history"][0]["pass_type"] == "blind"

    def test_build_metadata_multi_pass_with_escalation(self) -> None:
        """Test building metadata for multi-pass analysis with escalation"""
        from unittest.mock import MagicMock
        from src.jeeves.api.services.queue_service import QueueService

        # Create mock passes
        def create_mock_pass(num: int, ptype: str, model: str, conf: float) -> MagicMock:
            mock_conf = MagicMock()
            mock_conf.overall = conf
            mock_pass = MagicMock()
            mock_pass.pass_number = num
            mock_pass.pass_type = MagicMock(value=ptype)
            mock_pass.model_used = model
            mock_pass.duration_ms = 500.0 * num
            mock_pass.tokens_used = 300 * num
            mock_pass.confidence = mock_conf
            return mock_pass

        mock_result = MagicMock()
        mock_result.passes_count = 3
        mock_result.final_model = "sonnet"
        mock_result.escalated = True
        mock_result.stop_reason = "confidence_sufficient"
        mock_result.high_stakes = False
        mock_result.total_tokens = 1800
        mock_result.total_duration_ms = 3000.0
        mock_result.pass_history = [
            create_mock_pass(1, "blind", "haiku", 0.67),
            create_mock_pass(2, "refine", "sonnet", 0.85),
            create_mock_pass(3, "refine", "sonnet", 0.92),
        ]
        mock_result.retrieved_context = {"notes": [{"id": "1"}, {"id": "2"}]}

        service = QueueService.__new__(QueueService)
        metadata = service._build_multi_pass_metadata(mock_result)

        assert metadata["passes_count"] == 3
        assert metadata["final_model"] == "sonnet"
        assert metadata["models_used"] == ["haiku", "sonnet", "sonnet"]
        assert metadata["escalated"] is True

        # Check pass history
        assert len(metadata["pass_history"]) == 3

        # Pass 1: blind, haiku
        assert metadata["pass_history"][0]["pass_type"] == "blind"
        assert metadata["pass_history"][0]["model"] == "haiku"
        assert metadata["pass_history"][0]["context_searched"] is False
        assert metadata["pass_history"][0]["escalation_triggered"] is False

        # Pass 2: refine, sonnet (escalation from haiku)
        assert metadata["pass_history"][1]["pass_type"] == "refine"
        assert metadata["pass_history"][1]["model"] == "sonnet"
        assert metadata["pass_history"][1]["context_searched"] is True
        assert metadata["pass_history"][1]["notes_found"] == 2
        assert metadata["pass_history"][1]["escalation_triggered"] is True

        # Pass 3: refine, sonnet (no escalation)
        assert metadata["pass_history"][2]["escalation_triggered"] is False

    def test_build_metadata_confidence_evolution(self) -> None:
        """Test that confidence_before and confidence_after are tracked correctly"""
        from unittest.mock import MagicMock
        from src.jeeves.api.services.queue_service import QueueService

        def create_mock_pass(num: int, conf: float) -> MagicMock:
            mock_conf = MagicMock()
            mock_conf.overall = conf
            mock_pass = MagicMock()
            mock_pass.pass_number = num
            mock_pass.pass_type = MagicMock(value="refine")
            mock_pass.model_used = "sonnet"
            mock_pass.duration_ms = 500.0
            mock_pass.tokens_used = 300
            mock_pass.confidence = mock_conf
            return mock_pass

        mock_result = MagicMock()
        mock_result.passes_count = 3
        mock_result.final_model = "sonnet"
        mock_result.escalated = False
        mock_result.stop_reason = "confidence_sufficient"
        mock_result.high_stakes = False
        mock_result.total_tokens = 900
        mock_result.total_duration_ms = 1500.0
        mock_result.pass_history = [
            create_mock_pass(1, 0.45),
            create_mock_pass(2, 0.72),
            create_mock_pass(3, 0.91),
        ]
        mock_result.retrieved_context = None

        service = QueueService.__new__(QueueService)
        metadata = service._build_multi_pass_metadata(mock_result)

        # Check confidence evolution
        assert metadata["pass_history"][0]["confidence_before"] == 0.0
        assert metadata["pass_history"][0]["confidence_after"] == 0.45

        assert metadata["pass_history"][1]["confidence_before"] == 0.45
        assert metadata["pass_history"][1]["confidence_after"] == 0.72

        assert metadata["pass_history"][2]["confidence_before"] == 0.72
        assert metadata["pass_history"][2]["confidence_after"] == 0.91


class TestBadgeCalculation:
    """Tests for badge calculation logic (to be used in frontend)"""

    def test_badge_fast_single_pass(self) -> None:
        """Test badge for fast single-pass analysis (⚡)"""
        metadata = MultiPassMetadataResponse(
            passes_count=1,
            final_model="haiku",
        )

        # Badge logic: ⚡ if passes_count == 1 and final_model == "haiku"
        is_fast = metadata.passes_count == 1 and metadata.final_model == "haiku"
        assert is_fast is True

    def test_badge_context_searched(self) -> None:
        """Test badge for context searched (🔍)"""
        metadata = MultiPassMetadataResponse(
            passes_count=2,
            final_model="sonnet",
            pass_history=[
                PassHistoryEntryResponse(
                    pass_number=1,
                    pass_type="blind",
                    model="haiku",
                ),
                PassHistoryEntryResponse(
                    pass_number=2,
                    pass_type="refine",
                    model="sonnet",
                    context_searched=True,
                    notes_found=3,
                ),
            ],
        )

        # Badge logic: 🔍 if any pass has context_searched == True
        has_context = any(p.context_searched for p in metadata.pass_history)
        assert has_context is True

    def test_badge_deep_analysis(self) -> None:
        """Test badge for deep analysis (🧠)"""
        metadata = MultiPassMetadataResponse(
            passes_count=4,
            final_model="sonnet",
        )

        # Badge logic: 🧠 if passes_count >= 3
        is_deep = metadata.passes_count >= 3
        assert is_deep is True

    def test_badge_opus_used(self) -> None:
        """Test badge for Opus used (🏆)"""
        metadata = MultiPassMetadataResponse(
            passes_count=5,
            final_model="opus",
            models_used=["haiku", "sonnet", "sonnet", "sonnet", "opus"],
        )

        # Badge logic: 🏆 if "opus" in models_used
        has_opus = "opus" in metadata.models_used
        assert has_opus is True

    def test_badges_cumulative(self) -> None:
        """Test that badges can be cumulative"""
        metadata = MultiPassMetadataResponse(
            passes_count=5,
            final_model="opus",
            models_used=["haiku", "sonnet", "sonnet", "sonnet", "opus"],
            pass_history=[
                PassHistoryEntryResponse(pass_number=1, pass_type="blind", model="haiku"),
                PassHistoryEntryResponse(
                    pass_number=2, pass_type="refine", model="sonnet", context_searched=True
                ),
                PassHistoryEntryResponse(pass_number=3, pass_type="refine", model="sonnet"),
                PassHistoryEntryResponse(pass_number=4, pass_type="deep", model="sonnet"),
                PassHistoryEntryResponse(pass_number=5, pass_type="expert", model="opus"),
            ],
        )

        # All badges should be applicable
        is_fast = metadata.passes_count == 1 and metadata.final_model == "haiku"  # False
        has_context = any(p.context_searched for p in metadata.pass_history)  # True (🔍)
        is_deep = metadata.passes_count >= 3  # True (🧠)
        has_opus = "opus" in metadata.models_used  # True (🏆)

        assert is_fast is False  # Not a fast analysis
        assert has_context is True  # Has 🔍
        assert is_deep is True  # Has 🧠
        assert has_opus is True  # Has 🏆
        # Expected badges: 🧠 🔍 🏆
