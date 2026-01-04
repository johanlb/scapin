"""
Tests for Email API Router

Tests email account listing, processing, and action execution endpoints.
"""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.jeeves.api.app import create_app
from src.jeeves.api.routers.email import _get_email_service


@pytest.fixture
def mock_email_service() -> MagicMock:
    """Create mock email service"""
    service = MagicMock()

    # Sample account
    service.sample_account = {
        "name": "personal",
        "email": "user@example.com",
        "enabled": True,
        "inbox_folder": "INBOX",
    }

    # Sample processed email
    service.sample_email = {
        "metadata": {
            "id": "email-123",
            "subject": "Test Email",
            "from_address": "sender@example.com",
            "from_name": "Test Sender",
            "date": "2026-01-04T09:00:00+00:00",
            "has_attachments": False,
            "folder": "INBOX",
        },
        "analysis": {
            "action": "archive",
            "confidence": 92,
            "category": "work",
            "reasoning": "Work-related content",
            "destination": "Archive",
        },
        "processed_at": "2026-01-04T10:00:00+00:00",
        "executed": True,
    }

    # Mock async methods
    service.get_accounts = AsyncMock(return_value=[service.sample_account])
    service.get_stats = AsyncMock(return_value={
        "emails_processed": 150,
        "emails_auto_executed": 120,
        "emails_archived": 100,
        "emails_deleted": 15,
        "emails_queued": 30,
        "emails_skipped": 5,
        "tasks_created": 10,
        "average_confidence": 87.5,
        "processing_mode": "auto",
    })
    service.process_inbox = AsyncMock(return_value={
        "total_processed": 10,
        "auto_executed": 8,
        "queued": 2,
        "skipped": 0,
        "emails": [service.sample_email],
    })
    service.analyze_email = AsyncMock(return_value=service.sample_email)
    service.execute_action = AsyncMock(return_value=True)

    return service


@pytest.fixture
def client(mock_email_service: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked service"""
    app = create_app()
    app.dependency_overrides[_get_email_service] = lambda: mock_email_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListEmailAccounts:
    """Tests for GET /api/email/accounts endpoint"""

    def test_accounts_returns_success(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test listing accounts returns success"""
        response = client.get("/api/email/accounts")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_accounts_includes_details(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test accounts include required fields"""
        response = client.get("/api/email/accounts")

        data = response.json()["data"][0]
        assert data["name"] == "personal"
        assert data["email"] == "user@example.com"
        assert data["enabled"] is True
        assert data["inbox_folder"] == "INBOX"


class TestGetEmailStats:
    """Tests for GET /api/email/stats endpoint"""

    def test_stats_returns_success(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test stats endpoint returns success"""
        response = client.get("/api/email/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stats_includes_counts(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test stats include all count fields"""
        response = client.get("/api/email/stats")

        data = response.json()["data"]
        assert data["emails_processed"] == 150
        assert data["emails_auto_executed"] == 120
        assert data["emails_archived"] == 100
        assert data["emails_deleted"] == 15
        assert data["emails_queued"] == 30
        assert data["tasks_created"] == 10
        assert data["average_confidence"] == 87.5


class TestProcessInbox:
    """Tests for POST /api/email/process endpoint"""

    def test_process_returns_success(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test processing inbox returns success"""
        response = client.post("/api/email/process")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_processed"] == 10

    def test_process_with_limit(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test processing with limit parameter"""
        response = client.post(
            "/api/email/process",
            json={"limit": 20},
        )

        assert response.status_code == 200
        mock_email_service.process_inbox.assert_called_once()
        call_kwargs = mock_email_service.process_inbox.call_args[1]
        assert call_kwargs["limit"] == 20

    def test_process_with_auto_execute(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test processing with auto_execute enabled"""
        response = client.post(
            "/api/email/process",
            json={"auto_execute": True, "confidence_threshold": 85},
        )

        assert response.status_code == 200
        call_kwargs = mock_email_service.process_inbox.call_args[1]
        assert call_kwargs["auto_execute"] is True
        assert call_kwargs["confidence_threshold"] == 85

    def test_process_unread_only(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test processing only unread emails"""
        response = client.post(
            "/api/email/process",
            json={"unread_only": True},
        )

        assert response.status_code == 200
        call_kwargs = mock_email_service.process_inbox.call_args[1]
        assert call_kwargs["unread_only"] is True

    def test_process_returns_processed_emails(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test process returns list of processed emails"""
        response = client.post("/api/email/process")

        data = response.json()["data"]
        assert "emails" in data
        assert len(data["emails"]) == 1
        assert data["emails"][0]["metadata"]["subject"] == "Test Email"


class TestAnalyzeEmail:
    """Tests for POST /api/email/analyze endpoint"""

    def test_analyze_returns_success(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test analyzing email returns success"""
        response = client.post(
            "/api/email/analyze",
            json={"email_id": "email-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_analyze_not_found(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test analyzing non-existent email returns 404"""
        mock_email_service.analyze_email = AsyncMock(return_value=None)

        response = client.post(
            "/api/email/analyze",
            json={"email_id": "non-existent"},
        )

        assert response.status_code == 404

    def test_analyze_requires_email_id(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test analyze requires email_id"""
        response = client.post(
            "/api/email/analyze",
            json={},
        )

        assert response.status_code == 422

    def test_analyze_with_folder(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test analyzing email in specific folder"""
        response = client.post(
            "/api/email/analyze",
            json={"email_id": "email-123", "folder": "Archive"},
        )

        assert response.status_code == 200
        call_kwargs = mock_email_service.analyze_email.call_args[1]
        assert call_kwargs["folder"] == "Archive"


class TestExecuteAction:
    """Tests for POST /api/email/execute endpoint"""

    def test_execute_returns_success(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test executing action returns success"""
        response = client.post(
            "/api/email/execute",
            json={"email_id": "email-123", "action": "archive"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["executed"] is True

    def test_execute_archive_with_destination(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test archiving to specific destination"""
        response = client.post(
            "/api/email/execute",
            json={"email_id": "email-123", "action": "archive", "destination": "Work"},
        )

        assert response.status_code == 200
        call_kwargs = mock_email_service.execute_action.call_args[1]
        assert call_kwargs["destination"] == "Work"

    def test_execute_delete(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test executing delete action"""
        response = client.post(
            "/api/email/execute",
            json={"email_id": "email-123", "action": "delete"},
        )

        assert response.status_code == 200
        call_kwargs = mock_email_service.execute_action.call_args[1]
        assert call_kwargs["action"] == "delete"

    def test_execute_failure(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test execute failure returns 400"""
        mock_email_service.execute_action = AsyncMock(return_value=False)

        response = client.post(
            "/api/email/execute",
            json={"email_id": "email-123", "action": "archive"},
        )

        assert response.status_code == 400

    def test_execute_requires_action(self, client: TestClient, mock_email_service: MagicMock) -> None:
        """Test execute requires action field"""
        response = client.post(
            "/api/email/execute",
            json={"email_id": "email-123"},
        )

        assert response.status_code == 422
