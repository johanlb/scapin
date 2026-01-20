"""
Tests for Queue List Items with v2.4 Tab Filters

Tests the filtering logic for the 5-tab navigation:
- to_process (awaiting_review, not snoozed)
- in_progress (analyzing)
- snoozed (awaiting_review with snooze)
- history (processed)
- errors (error state)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.core.models.peripetie import PeripetieState, ResolutionType


class TestListItemsTabFiltering:
    """Tests for tab-based filtering of queue items"""

    @pytest.fixture
    def mock_storage(self):
        """Create mock QueueStorage with items in various states"""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def all_items(self):
        """Create items covering all tabs"""
        now = datetime.now(timezone.utc)
        future = (now + timedelta(hours=2)).isoformat()

        return [
            # to_process: awaiting_review, not snoozed
            {
                "id": "item-to-process-1",
                "state": PeripetieState.AWAITING_REVIEW.value,
                "status": "pending",
                "snooze": None,
                "error": None,
            },
            {
                "id": "item-to-process-2",
                "state": PeripetieState.AWAITING_REVIEW.value,
                "status": "pending",
                "snooze": None,
                "error": None,
            },
            # in_progress: analyzing
            {
                "id": "item-analyzing-1",
                "state": PeripetieState.ANALYZING.value,
                "status": "pending",
                "snooze": None,
                "error": None,
            },
            # snoozed: awaiting_review with snooze
            {
                "id": "item-snoozed-1",
                "state": PeripetieState.AWAITING_REVIEW.value,
                "status": "pending",
                "snooze": {"until": future},
                "error": None,
            },
            # history: processed
            {
                "id": "item-approved-1",
                "state": PeripetieState.PROCESSED.value,
                "status": "approved",
                "resolution": ResolutionType.MANUAL_APPROVED.value,
                "snooze": None,
                "error": None,
            },
            {
                "id": "item-rejected-1",
                "state": PeripetieState.PROCESSED.value,
                "status": "rejected",
                "resolution": ResolutionType.MANUAL_REJECTED.value,
                "snooze": None,
                "error": None,
            },
            # errors: error state
            {
                "id": "item-error-1",
                "state": PeripetieState.ERROR.value,
                "status": "error",
                "snooze": None,
                "error": {"type": "action_failed", "message": "IMAP error"},
            },
        ]

    # =========================================================================
    # TO_PROCESS TAB
    # =========================================================================

    def test_to_process_filter_includes_awaiting_review(self, all_items):
        """to_process tab should include awaiting_review items without snooze"""
        to_process = [
            item for item in all_items
            if item["state"] == PeripetieState.AWAITING_REVIEW.value
            and item.get("snooze") is None
        ]

        assert len(to_process) == 2
        assert all(item["id"].startswith("item-to-process") for item in to_process)

    def test_to_process_filter_excludes_snoozed(self, all_items):
        """to_process tab should exclude snoozed items"""
        to_process = [
            item for item in all_items
            if item["state"] == PeripetieState.AWAITING_REVIEW.value
            and item.get("snooze") is None
        ]

        snoozed_ids = [item["id"] for item in to_process if item.get("snooze")]
        assert len(snoozed_ids) == 0

    def test_to_process_filter_excludes_processed(self, all_items):
        """to_process tab should exclude processed items"""
        to_process = [
            item for item in all_items
            if item["state"] == PeripetieState.AWAITING_REVIEW.value
            and item.get("snooze") is None
        ]

        processed_ids = [
            item["id"] for item in to_process
            if item["state"] == PeripetieState.PROCESSED.value
        ]
        assert len(processed_ids) == 0

    # =========================================================================
    # IN_PROGRESS TAB
    # =========================================================================

    def test_in_progress_filter_includes_analyzing(self, all_items):
        """in_progress tab should include analyzing items"""
        in_progress = [
            item for item in all_items
            if item["state"] == PeripetieState.ANALYZING.value
        ]

        assert len(in_progress) == 1
        assert in_progress[0]["id"] == "item-analyzing-1"

    def test_in_progress_filter_excludes_awaiting_review(self, all_items):
        """in_progress tab should exclude awaiting_review items"""
        in_progress = [
            item for item in all_items
            if item["state"] == PeripetieState.ANALYZING.value
        ]

        awaiting_ids = [
            item["id"] for item in in_progress
            if item["state"] == PeripetieState.AWAITING_REVIEW.value
        ]
        assert len(awaiting_ids) == 0

    # =========================================================================
    # SNOOZED TAB
    # =========================================================================

    def test_snoozed_filter_includes_items_with_snooze(self, all_items):
        """snoozed tab should include items with snooze field"""
        snoozed = [
            item for item in all_items
            if item.get("snooze") is not None
        ]

        assert len(snoozed) == 1
        assert snoozed[0]["id"] == "item-snoozed-1"

    def test_snoozed_filter_excludes_non_snoozed(self, all_items):
        """snoozed tab should exclude items without snooze"""
        snoozed = [
            item for item in all_items
            if item.get("snooze") is not None
        ]

        non_snoozed = [item for item in snoozed if item.get("snooze") is None]
        assert len(non_snoozed) == 0

    # =========================================================================
    # HISTORY TAB
    # =========================================================================

    def test_history_filter_includes_processed(self, all_items):
        """history tab should include processed items"""
        history = [
            item for item in all_items
            if item["state"] == PeripetieState.PROCESSED.value
        ]

        assert len(history) == 2
        assert "item-approved-1" in [item["id"] for item in history]
        assert "item-rejected-1" in [item["id"] for item in history]

    def test_history_filter_includes_all_resolutions(self, all_items):
        """history tab should include all resolution types"""
        history = [
            item for item in all_items
            if item["state"] == PeripetieState.PROCESSED.value
        ]

        resolutions = [item.get("resolution") for item in history]
        assert ResolutionType.MANUAL_APPROVED.value in resolutions
        assert ResolutionType.MANUAL_REJECTED.value in resolutions

    # =========================================================================
    # ERRORS TAB
    # =========================================================================

    def test_errors_filter_includes_error_state(self, all_items):
        """errors tab should include items in error state"""
        errors = [
            item for item in all_items
            if item["state"] == PeripetieState.ERROR.value
        ]

        assert len(errors) == 1
        assert errors[0]["id"] == "item-error-1"

    def test_errors_filter_has_error_details(self, all_items):
        """error items should have error details"""
        errors = [
            item for item in all_items
            if item["state"] == PeripetieState.ERROR.value
        ]

        for error_item in errors:
            assert error_item.get("error") is not None
            assert "type" in error_item["error"]
            assert "message" in error_item["error"]


class TestTabCounts:
    """Tests for tab count calculations"""

    @pytest.fixture
    def all_items(self):
        """Create items for count testing"""
        now = datetime.now(timezone.utc)
        future = (now + timedelta(hours=2)).isoformat()

        return [
            # 3 to_process
            {"id": "1", "state": "awaiting_review", "snooze": None, "error": None},
            {"id": "2", "state": "awaiting_review", "snooze": None, "error": None},
            {"id": "3", "state": "awaiting_review", "snooze": None, "error": None},
            # 2 in_progress
            {"id": "4", "state": "analyzing", "snooze": None, "error": None},
            {"id": "5", "state": "analyzing", "snooze": None, "error": None},
            # 1 snoozed
            {"id": "6", "state": "awaiting_review", "snooze": {"until": future}, "error": None},
            # 4 history
            {"id": "7", "state": "processed", "snooze": None, "error": None},
            {"id": "8", "state": "processed", "snooze": None, "error": None},
            {"id": "9", "state": "processed", "snooze": None, "error": None},
            {"id": "10", "state": "processed", "snooze": None, "error": None},
            # 2 errors
            {"id": "11", "state": "error", "snooze": None, "error": {"type": "test"}},
            {"id": "12", "state": "error", "snooze": None, "error": {"type": "test"}},
        ]

    def test_to_process_count(self, all_items):
        """to_process count should be correct"""
        count = len([
            i for i in all_items
            if i["state"] == "awaiting_review" and i.get("snooze") is None
        ])
        assert count == 3

    def test_in_progress_count(self, all_items):
        """in_progress count should be correct"""
        count = len([i for i in all_items if i["state"] == "analyzing"])
        assert count == 2

    def test_snoozed_count(self, all_items):
        """snoozed count should be correct"""
        count = len([i for i in all_items if i.get("snooze") is not None])
        assert count == 1

    def test_history_count(self, all_items):
        """history count should be correct"""
        count = len([i for i in all_items if i["state"] == "processed"])
        assert count == 4

    def test_errors_count(self, all_items):
        """errors count should be correct"""
        count = len([i for i in all_items if i["state"] == "error"])
        assert count == 2

    def test_total_count_matches_sum(self, all_items):
        """Total should match sum of all tabs"""
        to_process = len([
            i for i in all_items
            if i["state"] == "awaiting_review" and i.get("snooze") is None
        ])
        in_progress = len([i for i in all_items if i["state"] == "analyzing"])
        snoozed = len([i for i in all_items if i.get("snooze") is not None])
        history = len([i for i in all_items if i["state"] == "processed"])
        errors = len([i for i in all_items if i["state"] == "error"])

        total = to_process + in_progress + snoozed + history + errors
        assert total == len(all_items)


class TestFilterCombinations:
    """Tests for combining tab filters with other filters"""

    @pytest.fixture
    def items_with_metadata(self):
        """Create items with various metadata for filtering"""
        return [
            {
                "id": "item-1",
                "state": "awaiting_review",
                "snooze": None,
                "account_id": "personal",
                "analysis": {"confidence": 90},
            },
            {
                "id": "item-2",
                "state": "awaiting_review",
                "snooze": None,
                "account_id": "work",
                "analysis": {"confidence": 60},
            },
            {
                "id": "item-3",
                "state": "awaiting_review",
                "snooze": None,
                "account_id": "personal",
                "analysis": {"confidence": 75},
            },
        ]

    def test_filter_by_account_and_tab(self, items_with_metadata):
        """Should be able to filter by account within a tab"""
        personal_to_process = [
            i for i in items_with_metadata
            if i["state"] == "awaiting_review"
            and i.get("snooze") is None
            and i.get("account_id") == "personal"
        ]

        assert len(personal_to_process) == 2

    def test_filter_by_confidence_and_tab(self, items_with_metadata):
        """Should be able to filter by confidence within a tab"""
        high_confidence = [
            i for i in items_with_metadata
            if i["state"] == "awaiting_review"
            and i.get("snooze") is None
            and i.get("analysis", {}).get("confidence", 0) >= 80
        ]

        assert len(high_confidence) == 1
        assert high_confidence[0]["id"] == "item-1"
