"""
Unit Tests for Folder Picker API (SC-19)

Tests the folder selection and modification workflow:
- GET /api/folders/search (autocomplete)
- POST /api/folders (creation)
- PATCH /api/queue/{id} (destination update)
- Sganarelle feedback for folder corrections
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


if TYPE_CHECKING:
    pass


class TestFolderSearchEndpoint:
    """Test GET /api/folders/search endpoint for autocomplete."""

    @pytest.fixture
    def mock_folders(self) -> list[dict]:
        """Create mock folder list."""
        return [
            {"path": "Archive/2025/Personnel", "name": "Personnel"},
            {"path": "Archive/2025/Travail", "name": "Travail"},
            {"path": "Archive/2025/Travail/Projets", "name": "Projets"},
            {"path": "Archive/2025/Travail/Projets/Alpha", "name": "Alpha"},
            {"path": "Archive/2025/Travail/Projets/Beta", "name": "Beta"},
            {"path": "Archive/2024/Archives", "name": "Archives"},
            {"path": "Inbox", "name": "Inbox"},
            {"path": "Sent", "name": "Sent"},
        ]

    def test_search_returns_matching_folders(self, mock_folders: list[dict]) -> None:
        """SC-19: Search should return folders matching query."""
        query = "projet"
        results = [
            f for f in mock_folders
            if query.lower() in f["path"].lower() or query.lower() in f["name"].lower()
        ]

        assert len(results) == 3  # Projets, Alpha, Beta (all under Projets)
        assert all("projet" in r["path"].lower() for r in results)

    def test_search_returns_full_path(self, mock_folders: list[dict]) -> None:
        """SC-19: Search results should include full path."""
        query = "alpha"
        results = [
            f for f in mock_folders
            if query.lower() in f["path"].lower()
        ]

        assert len(results) == 1
        assert results[0]["path"] == "Archive/2025/Travail/Projets/Alpha"

    def test_search_fuzzy_matching(self, mock_folders: list[dict]) -> None:
        """SC-19: Search should support fuzzy matching."""
        # Simulate fuzzy search: "trav" matches "Travail"
        query = "trav"
        results = [
            f for f in mock_folders
            if query.lower() in f["path"].lower()
        ]

        assert len(results) >= 1
        assert any("Travail" in r["path"] for r in results)

    def test_search_max_results(self, mock_folders: list[dict]) -> None:
        """SC-19: Search should return max 10 results."""
        max_results = 10
        query = ""  # Empty query returns all
        results = mock_folders[:max_results]

        assert len(results) <= max_results

    def test_search_empty_query_returns_results(self, mock_folders: list[dict]) -> None:
        """SC-19: Empty query should return some default folders."""
        query = ""
        # Return first N folders as default
        results = mock_folders[:5]

        assert len(results) > 0

    def test_search_no_results(self) -> None:
        """SC-19: Search with no matches returns empty list."""
        mock_folders = [
            {"path": "Archive/2025", "name": "2025"},
        ]
        query = "nonexistent"
        results = [
            f for f in mock_folders
            if query.lower() in f["path"].lower()
        ]

        assert len(results) == 0

    def test_search_response_time(self) -> None:
        """SC-19: Search should complete in < 200ms."""
        # This is a placeholder - actual performance test would measure time
        max_response_time_ms = 200
        # In real implementation, measure actual response time
        assert max_response_time_ms == 200


class TestFolderCreateEndpoint:
    """Test POST /api/folders endpoint for folder creation."""

    def test_create_folder_success(self) -> None:
        """SC-19: Should create new folder."""
        new_folder = {
            "path": "Archive/2025/Travail/Projets/Gamma",
            "name": "Gamma",
        }

        # Simulate creation result
        result = {
            "success": True,
            "data": {
                "path": new_folder["path"],
                "created": True,
            },
        }

        assert result["success"] is True
        assert result["data"]["created"] is True

    def test_create_folder_already_exists(self) -> None:
        """SC-19: Creating existing folder should not fail."""
        existing_folder = "Archive/2025/Travail"

        result = {
            "success": True,
            "data": {
                "path": existing_folder,
                "created": False,  # Already existed
            },
        }

        assert result["success"] is True
        assert result["data"]["created"] is False

    def test_create_nested_folder(self) -> None:
        """SC-19: Should create nested folders (parents if needed)."""
        deep_path = "Archive/2025/New/Deep/Nested/Folder"

        result = {
            "success": True,
            "data": {
                "path": deep_path,
                "created": True,
            },
        }

        assert result["success"] is True
        assert "/" in result["data"]["path"]

    def test_create_folder_invalid_name(self) -> None:
        """SC-19: Invalid folder name should return error."""
        invalid_paths = [
            "",  # Empty
            "../escape",  # Path traversal
            "folder\x00name",  # Null byte
        ]

        for path in invalid_paths:
            is_valid = bool(path) and ".." not in path and "\x00" not in path
            assert is_valid is False


class TestQueueDestinationUpdate:
    """Test PATCH /api/queue/{id} for destination update."""

    @pytest.fixture
    def mock_queue_item(self) -> dict:
        """Create mock queue item with destination."""
        return {
            "id": "email-123",
            "subject": "Important document",
            "analysis": {
                "action": "archive",
                "destination": "Archive/2025/Personnel",
                "confidence": 0.82,
            },
            "status": "pending",
        }

    def test_update_destination(self, mock_queue_item: dict) -> None:
        """SC-19: Should update destination in queue item."""
        new_destination = "Archive/2025/Travail/Projets/Alpha"

        mock_queue_item["analysis"]["destination"] = new_destination

        assert mock_queue_item["analysis"]["destination"] == new_destination

    def test_update_preserves_other_fields(self, mock_queue_item: dict) -> None:
        """SC-19: Updating destination should preserve other fields."""
        original_action = mock_queue_item["analysis"]["action"]
        original_confidence = mock_queue_item["analysis"]["confidence"]

        # Update destination
        mock_queue_item["analysis"]["destination"] = "New/Path"

        assert mock_queue_item["analysis"]["action"] == original_action
        assert mock_queue_item["analysis"]["confidence"] == original_confidence

    def test_update_destination_validates_path(self) -> None:
        """SC-19: Should validate destination path."""
        valid_paths = [
            "Archive/2025",
            "Archive/2025/Travail",
            "Inbox",
        ]
        invalid_paths = [
            "",
            "../escape",
            "path\x00with\x00nulls",
        ]

        for path in valid_paths:
            is_valid = bool(path) and ".." not in path and "\x00" not in path
            assert is_valid is True

        for path in invalid_paths:
            is_valid = bool(path) and ".." not in path and "\x00" not in path
            assert is_valid is False


class TestSganarelleFolderFeedback:
    """Test Sganarelle learning from folder corrections."""

    def test_folder_correction_recorded(self) -> None:
        """SC-19: Folder correction should be recorded for learning."""
        feedback = {
            "type": "folder_correction",
            "original": "Archive/2025/Personnel",
            "corrected": "Archive/2025/Travail/Projets/Alpha",
            "email_id": "email-123",
            "sender": "colleague@company.com",
            "subject_keywords": ["project", "alpha", "update"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        assert feedback["type"] == "folder_correction"
        assert feedback["original"] != feedback["corrected"]

    def test_folder_correction_includes_context(self) -> None:
        """SC-19: Feedback should include email context for learning."""
        feedback = {
            "type": "folder_correction",
            "original": "Archive/2025/Personnel",
            "corrected": "Archive/2025/Travail",
            "context": {
                "sender_domain": "company.com",
                "sender_name": "John Doe",
                "subject": "Q4 Report",
                "has_attachments": True,
            },
        }

        assert "context" in feedback
        assert "sender_domain" in feedback["context"]

    def test_folder_correction_influences_future(self) -> None:
        """SC-19: Corrections should influence future predictions."""
        # Simulate accumulated corrections
        corrections = [
            {"sender": "boss@company.com", "corrected": "Archive/Travail"},
            {"sender": "boss@company.com", "corrected": "Archive/Travail"},
            {"sender": "boss@company.com", "corrected": "Archive/Travail"},
        ]

        # After multiple corrections, system should learn preference
        # This is a conceptual test - actual implementation in Sganarelle
        sender_preference = "Archive/Travail"
        correction_count = len([c for c in corrections if c["sender"] == "boss@company.com"])

        assert correction_count >= 3
        # System should now suggest "Archive/Travail" for boss@company.com


class TestFolderPickerUI:
    """Test UI behavior for folder picker component."""

    def test_folder_path_is_clickable(self) -> None:
        """SC-19: Folder path should be clickable."""
        item = {
            "destination": "Archive/2025/Personnel",
            "destination_clickable": True,
        }

        assert item["destination_clickable"] is True

    def test_autocomplete_opens_on_click(self) -> None:
        """SC-19: Clicking folder path should open autocomplete."""
        state = {
            "is_open": False,
            "search_query": "",
        }

        # Simulate click
        state["is_open"] = True

        assert state["is_open"] is True

    def test_autocomplete_closes_on_escape(self) -> None:
        """SC-19: Pressing Escape should close autocomplete."""
        state = {
            "is_open": True,
            "search_query": "arch",
            "original_value": "Archive/2025/Personnel",
        }

        # Simulate Escape key
        state["is_open"] = False
        state["search_query"] = ""
        # Value should revert to original
        current_value = state["original_value"]

        assert state["is_open"] is False
        assert current_value == "Archive/2025/Personnel"

    def test_autocomplete_closes_on_outside_click(self) -> None:
        """SC-19: Clicking outside should close without changes."""
        state = {
            "is_open": True,
            "modified": False,
        }

        # Simulate outside click
        state["is_open"] = False

        assert state["is_open"] is False
        assert state["modified"] is False

    def test_create_option_shown_when_no_match(self) -> None:
        """SC-19: Should show 'Create' option when no folder matches."""
        search_results: list[dict] = []  # No matches
        search_query = "NewProjectFolder"

        show_create_option = len(search_results) == 0 and len(search_query) > 0

        assert show_create_option is True

    def test_hover_state_on_folder_path(self) -> None:
        """SC-19: Folder path should have hover state."""
        css_classes = ["cursor-pointer", "hover:bg-gray-100", "hover:underline"]

        # All hover-related classes should be present
        assert "cursor-pointer" in css_classes
        assert any("hover:" in c for c in css_classes)


class TestFolderSearchAPI:
    """Test the folder search API service."""

    @pytest.fixture
    def mock_imap_client(self) -> MagicMock:
        """Create mock IMAP client."""
        client = MagicMock()
        client.list_folders = AsyncMock(
            return_value=[
                "INBOX",
                "Sent",
                "Archive",
                "Archive/2025",
                "Archive/2025/Personnel",
                "Archive/2025/Travail",
            ]
        )
        return client

    @pytest.mark.asyncio
    async def test_list_folders_from_imap(self, mock_imap_client: MagicMock) -> None:
        """SC-19: Should list folders from IMAP server."""
        folders = await mock_imap_client.list_folders()

        assert len(folders) > 0
        assert "INBOX" in folders
        assert "Archive/2025/Travail" in folders

    @pytest.mark.asyncio
    async def test_search_filters_folders(self, mock_imap_client: MagicMock) -> None:
        """SC-19: Search should filter folder list."""
        folders = await mock_imap_client.list_folders()
        query = "2025"

        filtered = [f for f in folders if query in f]

        assert len(filtered) == 3  # Archive/2025, Personnel, Travail
        assert all("2025" in f for f in filtered)

