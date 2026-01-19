"""
Tests for Queue API Router

Tests queue listing, approval, rejection, and modification endpoints.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app
from src.frontin.api.deps import get_queue_service


@pytest.fixture
def mock_queue_service() -> MagicMock:
    """Create mock queue service"""
    service = MagicMock()

    # Sample queue item
    service.sample_item = {
        "id": "test-queue-123",
        "account_id": "personal",
        "queued_at": "2026-01-04T10:00:00+00:00",
        "metadata": {
            "id": "email-456",
            "subject": "Test Email",
            "from_address": "sender@example.com",
            "from_name": "Test Sender",
            "date": "2026-01-04T09:00:00+00:00",
            "has_attachments": False,
            "folder": "INBOX",
        },
        "analysis": {
            "action": "archive",
            "confidence": 75,
            "category": "newsletter",
            "reasoning": "Newsletter content detected",
        },
        "content": {
            "preview": "This is a test email preview...",
        },
        "status": "pending",
        "reviewed_at": None,
        "review_decision": None,
    }

    # Mock async methods
    service.list_items = AsyncMock(return_value=([service.sample_item], 1))
    service.get_item = AsyncMock(return_value=service.sample_item)
    service.get_stats = AsyncMock(return_value={
        "total": 5,
        "by_status": {"pending": 3, "approved": 2},
        "by_account": {"personal": 3, "work": 2},
        "oldest_item": "2026-01-03T08:00:00+00:00",
        "newest_item": "2026-01-04T10:00:00+00:00",
    })
    service.approve_item = AsyncMock(return_value={**service.sample_item, "status": "approved"})
    service.modify_item = AsyncMock(return_value={**service.sample_item, "status": "modified"})
    service.reject_item = AsyncMock(return_value={**service.sample_item, "status": "rejected"})
    service.delete_item = AsyncMock(return_value=True)

    return service


@pytest.fixture
def client(mock_queue_service: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked service"""
    app = create_app()
    app.dependency_overrides[get_queue_service] = lambda: mock_queue_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListQueueItems:
    """Tests for GET /api/queue endpoint"""

    def test_list_returns_success(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test listing queue items returns success"""
        response = client.get("/api/queue")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["total"] == 1

    def test_list_includes_pagination(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test listing includes pagination info"""
        response = client.get("/api/queue?page=1&page_size=20")

        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "has_more" in data
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_filters_by_status(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test listing can filter by status"""
        response = client.get("/api/queue?status=approved")

        assert response.status_code == 200
        mock_queue_service.list_items.assert_called_once()
        call_kwargs = mock_queue_service.list_items.call_args[1]
        assert call_kwargs["status"] == "approved"

    def test_list_filters_by_account(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test listing can filter by account"""
        response = client.get("/api/queue?account_id=work")

        assert response.status_code == 200
        mock_queue_service.list_items.assert_called_once()
        call_kwargs = mock_queue_service.list_items.call_args[1]
        assert call_kwargs["account_id"] == "work"


class TestGetQueueStats:
    """Tests for GET /api/queue/stats endpoint"""

    def test_stats_returns_success(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test stats endpoint returns success"""
        response = client.get("/api/queue/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 5

    def test_stats_includes_breakdown(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test stats includes status and account breakdown"""
        response = client.get("/api/queue/stats")

        data = response.json()
        assert "by_status" in data["data"]
        assert "by_account" in data["data"]
        assert data["data"]["by_status"]["pending"] == 3


class TestGetQueueItem:
    """Tests for GET /api/queue/{item_id} endpoint"""

    def test_get_item_returns_success(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test getting single item returns success"""
        response = client.get("/api/queue/test-queue-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "test-queue-123"

    def test_get_item_not_found(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test getting non-existent item returns 404"""
        mock_queue_service.get_item = AsyncMock(return_value=None)

        response = client.get("/api/queue/non-existent")

        assert response.status_code == 404

    def test_get_item_includes_full_details(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test item includes all details"""
        response = client.get("/api/queue/test-queue-123")

        data = response.json()["data"]
        assert "metadata" in data
        assert "analysis" in data
        assert "content" in data
        assert data["metadata"]["subject"] == "Test Email"
        assert data["analysis"]["confidence"] == 75


class TestApproveQueueItem:
    """Tests for POST /api/queue/{item_id}/approve endpoint"""

    def test_approve_returns_success(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test approving item returns success"""
        response = client.post("/api/queue/test-queue-123/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "approved"

    def test_approve_with_modified_action(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test approving with modified action"""
        response = client.post(
            "/api/queue/test-queue-123/approve",
            json={"modified_action": "delete", "modified_category": "spam"},
        )

        assert response.status_code == 200
        mock_queue_service.approve_item.assert_called_once()
        call_kwargs = mock_queue_service.approve_item.call_args[1]
        assert call_kwargs["modified_action"] == "delete"
        assert call_kwargs["modified_category"] == "spam"

    def test_approve_not_found(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test approving non-existent item returns 404"""
        mock_queue_service.approve_item = AsyncMock(return_value=None)

        response = client.post("/api/queue/non-existent/approve")

        assert response.status_code == 404


class TestModifyQueueItem:
    """Tests for POST /api/queue/{item_id}/modify endpoint"""

    def test_modify_returns_success(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test modifying item returns success"""
        response = client.post(
            "/api/queue/test-queue-123/modify",
            json={"action": "delete"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_modify_requires_action(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test modifying requires action field"""
        response = client.post(
            "/api/queue/test-queue-123/modify",
            json={},
        )

        assert response.status_code == 422  # Validation error

    def test_modify_with_reasoning(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test modifying with reasoning"""
        response = client.post(
            "/api/queue/test-queue-123/modify",
            json={"action": "task", "reasoning": "Need to follow up"},
        )

        assert response.status_code == 200
        mock_queue_service.modify_item.assert_called_once()


class TestRejectQueueItem:
    """Tests for POST /api/queue/{item_id}/reject endpoint"""

    def test_reject_returns_success(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test rejecting item returns success"""
        response = client.post("/api/queue/test-queue-123/reject")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "rejected"

    def test_reject_with_reason(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test rejecting with reason"""
        response = client.post(
            "/api/queue/test-queue-123/reject",
            json={"reason": "Not relevant"},
        )

        assert response.status_code == 200
        mock_queue_service.reject_item.assert_called_once()
        call_kwargs = mock_queue_service.reject_item.call_args[1]
        assert call_kwargs["reason"] == "Not relevant"


class TestDeleteQueueItem:
    """Tests for DELETE /api/queue/{item_id} endpoint"""

    def test_delete_returns_success(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test deleting item returns success"""
        response = client.delete("/api/queue/test-queue-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] == "test-queue-123"

    def test_delete_not_found(self, client: TestClient, mock_queue_service: MagicMock) -> None:
        """Test deleting non-existent item returns 404"""
        mock_queue_service.delete_item = AsyncMock(return_value=False)

        response = client.delete("/api/queue/non-existent")

        assert response.status_code == 404
