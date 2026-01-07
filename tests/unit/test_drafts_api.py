"""
Tests for Drafts API

Tests DraftsService and Drafts Router endpoints.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.integrations.storage.draft_storage import (
    DraftStatus,
    DraftStorage,
)
from src.jeeves.api.models.drafts import (
    DraftCreateRequest,
    DraftResponse,
    DraftUpdateRequest,
    GenerateDraftRequest,
)
from src.jeeves.api.services.drafts_service import DraftsService


class TestDraftsModels:
    """Tests for Pydantic models"""

    def test_draft_response_model(self):
        """Should create valid DraftResponse"""
        response = DraftResponse(
            draft_id="test-123",
            email_id=456,
            account_email="test@example.com",
            subject="Re: Test",
            body="Test body",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert response.draft_id == "test-123"
        assert response.email_id == 456
        assert response.status == "draft"

    def test_draft_create_request(self):
        """Should create valid DraftCreateRequest"""
        request = DraftCreateRequest(
            email_id=123,
            account_email="user@example.com",
            subject="Re: Hello",
            body="My reply",
        )

        assert request.email_id == 123
        assert request.account_email == "user@example.com"
        assert request.body_format == "plain_text"

    def test_draft_update_request(self):
        """Should create valid DraftUpdateRequest with partial data"""
        request = DraftUpdateRequest(body="New body only")

        assert request.body == "New body only"
        assert request.subject is None
        assert request.to_addresses is None

    def test_generate_draft_request_defaults(self):
        """Should have sensible defaults"""
        request = GenerateDraftRequest(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Original content",
        )

        assert request.tone == "professional"
        assert request.language == "fr"
        assert request.include_original is True
        assert request.reply_intent == ""


class TestDraftsService:
    """Tests for DraftsService"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def service(self, temp_dir):
        """Create service with temp storage"""
        service = DraftsService()
        service._storage = DraftStorage(drafts_dir=temp_dir)
        return service

    @pytest.mark.asyncio
    async def test_list_drafts_empty(self, service):
        """Should return empty list when no drafts"""
        drafts = await service.list_drafts()
        assert drafts == []

    @pytest.mark.asyncio
    async def test_list_drafts_with_filters(self, service):
        """Should filter drafts by status and account"""
        # Create some drafts
        await service.create_draft(
            email_id=1,
            account_email="a@example.com",
            subject="Draft 1",
        )
        await service.create_draft(
            email_id=2,
            account_email="b@example.com",
            subject="Draft 2",
        )

        # Filter by account
        drafts = await service.list_drafts(account_email="a@example.com")
        assert len(drafts) == 1
        assert drafts[0].account_email == "a@example.com"

    @pytest.mark.asyncio
    async def test_get_draft(self, service):
        """Should get draft by ID"""
        created = await service.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
        )

        retrieved = await service.get_draft(created.draft_id)

        assert retrieved is not None
        assert retrieved.draft_id == created.draft_id

    @pytest.mark.asyncio
    async def test_get_draft_not_found(self, service):
        """Should return None for non-existent draft"""
        result = await service.get_draft("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_draft_manual(self, service):
        """Should create manual draft (not AI-generated)"""
        draft = await service.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Re: Test",
            body="My manual reply",
        )

        assert draft.ai_generated is False
        assert draft.subject == "Re: Test"
        assert draft.body == "My manual reply"

    @pytest.mark.asyncio
    async def test_update_draft(self, service):
        """Should update draft fields"""
        created = await service.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Original",
            body="Original body",
        )

        updated = await service.update_draft(
            created.draft_id,
            subject="Updated Subject",
            body="Updated body",
        )

        assert updated is not None
        assert updated.subject == "Updated Subject"
        assert updated.body == "Updated body"
        assert updated.user_edited is True

    @pytest.mark.asyncio
    async def test_mark_sent(self, service):
        """Should mark draft as sent"""
        draft = await service.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
        )

        sent = await service.mark_sent(draft.draft_id)

        assert sent is not None
        assert sent.status == DraftStatus.SENT
        assert sent.sent_at is not None

    @pytest.mark.asyncio
    async def test_discard_draft(self, service):
        """Should discard draft"""
        draft = await service.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
        )

        discarded = await service.discard_draft(draft.draft_id, "Changed mind")

        assert discarded is not None
        assert discarded.status == DraftStatus.DISCARDED
        assert discarded.discarded_at is not None

    @pytest.mark.asyncio
    async def test_delete_draft(self, service):
        """Should permanently delete draft"""
        draft = await service.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
        )

        deleted = await service.delete_draft(draft.draft_id)
        assert deleted is True

        # Verify gone
        retrieved = await service.get_draft(draft.draft_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """Should return correct statistics"""
        draft1 = await service.create_draft(
            email_id=1,
            account_email="a@example.com",
            subject="A",
        )
        await service.create_draft(
            email_id=2,
            account_email="b@example.com",
            subject="B",
        )
        await service.mark_sent(draft1.draft_id)

        stats = await service.get_stats()

        assert stats["total"] == 2
        assert stats["by_status"]["sent"] == 1
        assert stats["by_status"]["draft"] == 1


class TestDraftsEndpoints:
    """Tests for Drafts API endpoints"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_service(self, temp_dir):
        """Create mock service"""
        service = DraftsService()
        service._storage = DraftStorage(drafts_dir=temp_dir)
        return service

    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked service"""
        from src.jeeves.api.app import create_app
        from src.jeeves.api.services.drafts_service import get_drafts_service

        app = create_app()
        app.dependency_overrides[get_drafts_service] = lambda: mock_service

        return TestClient(app)

    def test_list_drafts_empty(self, client):
        """Should return empty list"""
        response = client.get("/api/drafts")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["total"] == 0

    def test_list_drafts_with_pagination(self, client, mock_service):
        """Should paginate results"""
        # Create some drafts
        for i in range(5):
            mock_service.storage.create_draft(
                email_id=i,
                account_email="test@example.com",
                subject=f"Draft {i}",
                body=f"Body {i}",
            )

        # Get first page
        response = client.get("/api/drafts?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["total"] == 5
        assert data["has_more"] is True

    def test_get_draft(self, client, mock_service):
        """Should get single draft"""
        draft = mock_service.storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test Draft",
            body="Test body",
        )

        response = client.get(f"/api/drafts/{draft.draft_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["draft_id"] == draft.draft_id
        assert data["data"]["subject"] == "Test Draft"

    def test_get_draft_not_found(self, client):
        """Should return 404 for non-existent draft"""
        response = client.get("/api/drafts/non-existent")

        assert response.status_code == 404

    def test_create_draft(self, client):
        """Should create draft"""
        response = client.post(
            "/api/drafts",
            json={
                "email_id": 123,
                "account_email": "test@example.com",
                "subject": "Re: Hello",
                "body": "My reply",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["subject"] == "Re: Hello"
        assert data["data"]["ai_generated"] is False

    def test_update_draft(self, client, mock_service):
        """Should update draft"""
        draft = mock_service.storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Original",
            body="Original body",
        )

        response = client.put(
            f"/api/drafts/{draft.draft_id}",
            json={"subject": "Updated", "body": "New body"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["subject"] == "Updated"
        assert data["data"]["body"] == "New body"
        assert data["data"]["user_edited"] is True

    def test_update_draft_not_found(self, client):
        """Should return 404 for non-existent draft"""
        response = client.put(
            "/api/drafts/non-existent",
            json={"body": "New body"},
        )

        assert response.status_code == 404

    def test_mark_sent(self, client, mock_service):
        """Should mark draft as sent"""
        draft = mock_service.storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Test body",
        )

        response = client.post(f"/api/drafts/{draft.draft_id}/send")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "sent"
        assert data["data"]["sent_at"] is not None

    def test_discard_draft(self, client, mock_service):
        """Should discard draft"""
        draft = mock_service.storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Test body",
        )

        response = client.post(
            f"/api/drafts/{draft.draft_id}/discard",
            json={"reason": "Changed my mind"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "discarded"

    def test_delete_draft(self, client, mock_service):
        """Should delete draft"""
        draft = mock_service.storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Test body",
        )

        response = client.delete(f"/api/drafts/{draft.draft_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted"] is True

        # Verify gone
        response = client.get(f"/api/drafts/{draft.draft_id}")
        assert response.status_code == 404

    def test_get_pending_drafts(self, client, mock_service):
        """Should list only pending drafts"""
        draft1 = mock_service.storage.create_draft(
            email_id=1,
            account_email="test@example.com",
            subject="Pending",
            body="Pending body",
        )
        draft2 = mock_service.storage.create_draft(
            email_id=2,
            account_email="test@example.com",
            subject="Will be sent",
            body="Sent body",
        )
        mock_service.storage.mark_sent(draft2.draft_id)

        response = client.get("/api/drafts/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["draft_id"] == draft1.draft_id

    def test_get_stats(self, client, mock_service):
        """Should return statistics"""
        draft1 = mock_service.storage.create_draft(
            email_id=1,
            account_email="a@example.com",
            subject="A",
            body="A body",
        )
        mock_service.storage.create_draft(
            email_id=2,
            account_email="b@example.com",
            subject="B",
            body="B body",
        )
        mock_service.storage.mark_sent(draft1.draft_id)

        response = client.get("/api/drafts/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 2
        assert data["data"]["by_status"]["sent"] == 1
        assert data["data"]["by_status"]["draft"] == 1

    def test_generate_draft(self, client, temp_dir):
        """Should generate AI-assisted draft"""
        from unittest.mock import patch

        from src.jeeves.api.app import create_app
        from src.jeeves.api.services.drafts_service import get_drafts_service

        # Create shared storage for both service and action
        shared_storage = DraftStorage(drafts_dir=temp_dir)

        # Create service with shared storage
        service = DraftsService()
        service._storage = shared_storage

        app = create_app()
        app.dependency_overrides[get_drafts_service] = lambda: service

        # Patch get_draft_storage to return our shared storage
        # This ensures the action uses the same storage as the service
        with patch(
            "src.figaro.actions.email.get_draft_storage",
            return_value=shared_storage,
        ):
            test_client = TestClient(app)

            response = test_client.post(
                "/api/drafts/generate",
                json={
                    "email_id": 123,
                    "account_email": "user@example.com",
                    "original_subject": "Hello",
                    "original_from": "sender@example.com",
                    "original_content": "This is the original email.",
                    "reply_intent": "Merci pour votre message",
                    "tone": "professional",
                    "language": "fr",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["ai_generated"] is True
        assert data["data"]["subject"] == "Re: Hello"
        assert "Bonjour" in data["data"]["body"]
        assert "Merci pour votre message" in data["data"]["body"]

    def test_filter_by_email_id(self, client, mock_service):
        """Should filter drafts by email ID"""
        mock_service.storage.create_draft(
            email_id=100,
            account_email="test@example.com",
            subject="Draft for 100",
            body="Body for 100",
        )
        mock_service.storage.create_draft(
            email_id=100,
            account_email="test@example.com",
            subject="Another for 100",
            body="Another body for 100",
        )
        mock_service.storage.create_draft(
            email_id=200,
            account_email="test@example.com",
            subject="Draft for 200",
            body="Body for 200",
        )

        response = client.get("/api/drafts?email_id=100")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(d["email_id"] == 100 for d in data["data"])
