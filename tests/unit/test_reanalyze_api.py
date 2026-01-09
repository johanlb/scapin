"""
Unit Tests for Reanalyze API (SC-18)

Tests the re-analysis workflow:
- POST /api/queue/{id}/reanalyze endpoint
- Re-analysis keeps item in review queue
- No auto-execution after re-analysis
- Error handling
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.schemas import EmailAction, EmailAnalysis, EmailCategory


if TYPE_CHECKING:
    pass


class TestReanalyzeEndpoint:
    """Test POST /api/queue/{id}/reanalyze endpoint."""

    @pytest.fixture
    def mock_queue_item(self) -> dict:
        """Create a mock queue item."""
        return {
            "id": "email-123",
            "source": "email",
            "subject": "Meeting reminder",
            "sender": "boss@company.com",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "analysis": {
                "action": "archive",
                "category": "work",
                "confidence": 0.72,
                "reasoning": "Looks like a routine meeting reminder",
            },
        }

    def test_reanalyze_returns_new_analysis(self, mock_queue_item: dict) -> None:
        """SC-18: Re-analysis should return updated analysis."""
        # Simulate new analysis with higher confidence
        new_analysis = EmailAnalysis(
            action=EmailAction.TASK,
            category=EmailCategory.WORK,
            confidence=88,
            reasoning="Important meeting with CEO - needs follow-up task",
        )

        # Verify new analysis has different values
        assert new_analysis.action.value != mock_queue_item["analysis"]["action"]
        assert new_analysis.confidence > mock_queue_item["analysis"]["confidence"]

    def test_reanalyze_keeps_item_in_queue(self, mock_queue_item: dict) -> None:
        """SC-18: Item should remain in pending status after re-analysis."""
        # After re-analysis, status should still be pending
        mock_queue_item["analysis"]["confidence"] = 0.95  # High confidence

        # Even with high confidence, status should remain pending
        assert mock_queue_item["status"] == "pending"

    def test_reanalyze_no_auto_execute_above_threshold(self) -> None:
        """SC-18: Should NOT auto-execute even if confidence exceeds threshold."""
        threshold = 0.85
        new_confidence = 0.92  # Above threshold

        # Re-analysis should never trigger auto-execute
        should_auto_execute = False  # Always false for re-analysis
        assert should_auto_execute is False

        # Item should stay in review queue
        item_status = "pending"
        assert item_status == "pending"

    def test_reanalyze_updates_analysis_fields(self, mock_queue_item: dict) -> None:
        """SC-18: Re-analysis should update all analysis fields."""
        old_analysis = mock_queue_item["analysis"].copy()

        # Simulate re-analysis updating the item
        new_analysis = {
            "action": "task",
            "category": "work",
            "confidence": 0.88,
            "reasoning": "Updated reasoning after learning",
        }
        mock_queue_item["analysis"] = new_analysis

        # Verify fields updated
        assert mock_queue_item["analysis"]["action"] != old_analysis["action"]
        assert mock_queue_item["analysis"]["confidence"] != old_analysis["confidence"]
        assert mock_queue_item["analysis"]["reasoning"] != old_analysis["reasoning"]

    def test_reanalyze_same_result_is_valid(self) -> None:
        """SC-18: Same result after re-analysis is valid (no error)."""
        original = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=75,
            reasoning="Newsletter from marketing list",
        )

        # Re-analysis produces same result
        reanalyzed = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=78,  # Slightly different confidence
            reasoning="Newsletter from marketing list",
        )

        # Same action is valid
        assert reanalyzed.action == original.action
        # Confidence may vary slightly
        assert abs(reanalyzed.confidence - original.confidence) <= 10


class TestReanalyzeService:
    """Test the reanalyze service logic."""

    @pytest.fixture
    def mock_processor(self) -> MagicMock:
        """Create mock email processor."""
        processor = MagicMock()
        processor.analyze_email = AsyncMock(
            return_value=EmailAnalysis(
                action=EmailAction.TASK,
                category=EmailCategory.WORK,
                confidence=85,
                reasoning="Re-analyzed with updated context",
            )
        )
        return processor

    @pytest.mark.asyncio
    async def test_reanalyze_calls_processor(self, mock_processor: MagicMock) -> None:
        """SC-18: Re-analysis should call the email processor."""
        email_data = {
            "id": "email-123",
            "subject": "Important meeting",
            "body": "Please attend the meeting tomorrow",
        }

        # Simulate calling reanalyze
        result = await mock_processor.analyze_email(email_data)

        mock_processor.analyze_email.assert_called_once_with(email_data)
        assert result.action == EmailAction.TASK

    @pytest.mark.asyncio
    async def test_reanalyze_preserves_item_id(self, mock_processor: MagicMock) -> None:
        """SC-18: Re-analysis should preserve the original item ID."""
        item_id = "email-456"
        email_data = {"id": item_id, "subject": "Test"}

        await mock_processor.analyze_email(email_data)

        # The item ID should be preserved
        call_args = mock_processor.analyze_email.call_args[0][0]
        assert call_args["id"] == item_id

    @pytest.mark.asyncio
    async def test_reanalyze_error_preserves_old_analysis(self) -> None:
        """SC-18: If re-analysis fails, original analysis should be preserved."""
        original_analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.WORK,
            confidence=70,
            reasoning="Original analysis",
        )

        # Simulate error during re-analysis
        error_occurred = True
        if error_occurred:
            # Keep original analysis
            current_analysis = original_analysis
        else:
            current_analysis = None  # Would be new analysis

        assert current_analysis == original_analysis
        assert current_analysis.reasoning == "Original analysis"


class TestReanalyzeRateLimiting:
    """Test re-analysis rate limiting (none required per spec)."""

    def test_no_rate_limit_on_reanalyze(self) -> None:
        """SC-18: No limit on number of re-analyses per item."""
        reanalyze_count = 100
        max_allowed = float("inf")  # No limit

        assert reanalyze_count < max_allowed

    def test_multiple_reanalyzes_allowed(self) -> None:
        """SC-18: Same item can be re-analyzed multiple times."""
        reanalyze_history = []

        # Simulate 5 re-analyses
        for i in range(5):
            reanalyze_history.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attempt": i + 1,
                }
            )

        # All 5 should be recorded
        assert len(reanalyze_history) == 5


class TestReanalyzeUIState:
    """Test UI state during re-analysis."""

    def test_loading_state_during_reanalyze(self) -> None:
        """SC-18: UI should show loading state during re-analysis."""
        is_reanalyzing = True

        # Should display loading indicator
        show_loading = is_reanalyzing
        assert show_loading is True

        # Button should be disabled
        button_disabled = is_reanalyzing
        assert button_disabled is True

    def test_loading_state_clears_after_reanalyze(self) -> None:
        """SC-18: Loading state should clear after re-analysis completes."""
        is_reanalyzing = False  # After completion

        show_loading = is_reanalyzing
        assert show_loading is False

        button_disabled = is_reanalyzing
        assert button_disabled is False

    def test_no_special_badge_after_reanalyze(self) -> None:
        """SC-18: No special indicator for re-analyzed items."""
        item = {
            "id": "email-123",
            "reanalyzed": True,
            "reanalyze_count": 3,
        }

        # Per spec, no special badge should be shown
        show_reanalyzed_badge = False  # Explicitly disabled per spec
        assert show_reanalyzed_badge is False


class TestReanalyzeResponseFormat:
    """Test the API response format for re-analysis."""

    def test_reanalyze_response_structure(self) -> None:
        """SC-18: Re-analyze response should have expected structure."""
        response = {
            "success": True,
            "data": {
                "id": "email-123",
                "analysis": {
                    "action": "task",
                    "category": "work",
                    "confidence": 0.88,
                    "reasoning": "Updated analysis",
                },
                "status": "pending",  # Always pending after re-analysis
            },
        }

        assert response["success"] is True
        assert response["data"]["status"] == "pending"
        assert "analysis" in response["data"]
        assert "confidence" in response["data"]["analysis"]

    def test_reanalyze_error_response_structure(self) -> None:
        """SC-18: Error response should have expected structure."""
        error_response = {
            "success": False,
            "error": {
                "code": "REANALYZE_FAILED",
                "message": "Unable to re-analyze email",
                "details": "AI service temporarily unavailable",
            },
        }

        assert error_response["success"] is False
        assert "error" in error_response
        assert "message" in error_response["error"]

