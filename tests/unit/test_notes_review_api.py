"""Tests for Notes Review API endpoints"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.frontin.api.models.notes import (
    NoteMetadataResponse,
    NotesDueResponse,
    PostponeReviewResponse,
    RecordReviewResponse,
    ReviewConfigResponse,
    ReviewStatsResponse,
    ReviewWorkloadResponse,
    TriggerReviewResponse,
)
from src.frontin.api.routers.notes import router
from src.frontin.api.services.notes_review_service import NotesReviewService
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import NoteType


@pytest.fixture
def app():
    """Create test FastAPI app"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/notes")
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def temp_db():
    """Create a temporary database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def metadata_store(temp_db):
    """Create metadata store"""
    return NoteMetadataStore(temp_db)


@pytest.fixture
def scheduler(metadata_store):
    """Create scheduler"""
    return NoteScheduler(metadata_store)


@pytest.fixture
def mock_review_service():
    """Create mock review service"""
    service = MagicMock(spec=NotesReviewService)
    return service


class TestReviewModels:
    """Tests for review API models"""

    def test_note_metadata_response(self):
        """Should create NoteMetadataResponse correctly"""
        response = NoteMetadataResponse(
            note_id="test-001",
            note_type="personne",
            easiness_factor=2.3,
            repetition_number=5,
            interval_hours=48.0,
            next_review=datetime.now(timezone.utc),
            last_quality=4,
            review_count=10,
            auto_enrich=True,
            importance="high",
        )
        assert response.note_id == "test-001"
        assert response.easiness_factor == 2.3
        assert response.review_count == 10

    def test_record_review_response(self):
        """Should create RecordReviewResponse correctly"""
        response = RecordReviewResponse(
            note_id="test-001",
            quality=4,
            new_easiness_factor=2.4,
            new_interval_hours=24.0,
            new_repetition_number=3,
            next_review=datetime.now(timezone.utc),
            quality_assessment="Excellent - minor fixes only",
        )
        assert response.quality == 4
        assert response.new_easiness_factor == 2.4

    def test_review_stats_response(self):
        """Should create ReviewStatsResponse correctly"""
        response = ReviewStatsResponse(
            total_notes=100,
            by_type={"personne": 30, "projet": 20},
            by_importance={"high": 10, "normal": 80},
            total_due=15,
            reviewed_today=5,
            avg_easiness_factor=2.3,
        )
        assert response.total_notes == 100
        assert response.total_due == 15

    def test_review_workload_response(self):
        """Should create ReviewWorkloadResponse correctly"""
        response = ReviewWorkloadResponse(
            workload={"2026-01-05": 10, "2026-01-06": 8},
            total_upcoming=18,
        )
        assert response.total_upcoming == 18
        assert response.workload["2026-01-05"] == 10


class TestNotesReviewService:
    """Tests for NotesReviewService"""

    @pytest.fixture
    def config(self):
        """Create mock config"""
        config = MagicMock()
        config.storage_dir = "data"
        return config

    @pytest.fixture
    def service(self, config, temp_db):
        """Create service with temp db"""
        with patch.object(
            NotesReviewService, "_get_store"
        ) as mock_get_store:
            store = NoteMetadataStore(temp_db)
            mock_get_store.return_value = store
            svc = NotesReviewService(config=config)
            svc._metadata_store = store
            svc._scheduler = NoteScheduler(store)
            yield svc

    @pytest.mark.asyncio
    async def test_get_notes_due_empty(self, service, metadata_store):
        """Should return empty list when no notes due"""
        result = await service.get_notes_due()
        assert isinstance(result, NotesDueResponse)
        assert result.total == 0
        assert len(result.notes) == 0

    @pytest.mark.asyncio
    async def test_get_notes_due_with_notes(self, service, metadata_store):
        """Should return notes that are due"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        metadata = NoteMetadata(
            note_id="due-note",
            note_type=NoteType.PERSONNE,
            next_review=past,
        )
        metadata_store.save(metadata)

        result = await service.get_notes_due()
        assert result.total == 1
        assert result.notes[0].note_id == "due-note"

    @pytest.mark.asyncio
    async def test_get_note_metadata_not_found(self, service):
        """Should return None for non-existent note"""
        result = await service.get_note_metadata("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_note_metadata_found(self, service, metadata_store):
        """Should return metadata for existing note"""
        metadata = NoteMetadata(
            note_id="test-note",
            note_type=NoteType.PROJET,
            easiness_factor=2.3,
        )
        metadata_store.save(metadata)

        result = await service.get_note_metadata("test-note")
        assert result is not None
        assert result.note_id == "test-note"
        assert result.easiness_factor == 2.3

    @pytest.mark.asyncio
    async def test_record_review(self, service, metadata_store):
        """Should record review and update scheduling"""
        metadata = NoteMetadata(
            note_id="review-test",
            note_type=NoteType.PERSONNE,
            easiness_factor=2.5,
            repetition_number=2,
            interval_hours=12.0,
        )
        metadata_store.save(metadata)

        result = await service.record_review("review-test", quality=4)
        assert result is not None
        assert result.note_id == "review-test"
        assert result.quality == 4
        assert result.new_repetition_number == 3

    @pytest.mark.asyncio
    async def test_record_review_not_found(self, service):
        """Should return None for non-existent note"""
        result = await service.record_review("nonexistent", quality=4)
        assert result is None

    @pytest.mark.asyncio
    async def test_postpone_review(self, service, metadata_store):
        """Should postpone review"""
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="postpone-test",
            next_review=now,
        )
        metadata_store.save(metadata)

        result = await service.postpone_review("postpone-test", hours=24.0)
        assert result is not None
        assert result.hours_postponed == 24.0
        # Should be approximately 24 hours in future
        delta = result.new_next_review - now
        assert 23 < delta.total_seconds() / 3600 < 25

    @pytest.mark.asyncio
    async def test_trigger_immediate_review(self, service, metadata_store):
        """Should trigger immediate review"""
        future = datetime.now(timezone.utc) + timedelta(days=7)
        metadata = NoteMetadata(
            note_id="trigger-test",
            next_review=future,
        )
        metadata_store.save(metadata)

        result = await service.trigger_immediate_review("trigger-test")
        assert result is not None
        assert result.triggered is True
        # Should be now (not in the future)
        assert result.next_review <= datetime.now(timezone.utc) + timedelta(seconds=5)

    @pytest.mark.asyncio
    async def test_get_review_stats(self, service, metadata_store):
        """Should return review statistics"""
        # Add some test data
        metadata_store.save(NoteMetadata(note_id="p1", note_type=NoteType.PERSONNE))
        metadata_store.save(NoteMetadata(note_id="p2", note_type=NoteType.PROJET))

        result = await service.get_review_stats()
        assert isinstance(result, ReviewStatsResponse)
        assert result.total_notes == 2

    @pytest.mark.asyncio
    async def test_estimate_workload(self, service, metadata_store):
        """Should estimate workload"""
        now = datetime.now(timezone.utc)
        for i in range(5):
            metadata_store.save(
                NoteMetadata(
                    note_id=f"workload-{i}",
                    next_review=now + timedelta(days=i),
                )
            )

        result = await service.estimate_workload(days=7)
        assert isinstance(result, ReviewWorkloadResponse)
        assert len(result.workload) == 7
        assert result.total_upcoming >= 5

    @pytest.mark.asyncio
    async def test_get_review_configs(self, service):
        """Should return all review configs"""
        result = await service.get_review_configs()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(c, ReviewConfigResponse) for c in result)
        # Check that common types are present
        type_names = [c.note_type for c in result]
        assert "personne" in type_names
        assert "projet" in type_names


class TestNotesReviewEndpoints:
    """Tests for Notes Review API endpoints"""

    @pytest.fixture
    def mock_service(self):
        """Create mock review service"""
        return AsyncMock(spec=NotesReviewService)

    @pytest.fixture
    def mock_client(self, app, mock_service):
        """Create client with mocked dependency"""
        from src.frontin.api.auth import TokenData
        from src.frontin.api.deps import get_current_user, get_notes_review_service

        app.dependency_overrides[get_notes_review_service] = lambda: mock_service
        # Mock authentication - return a valid user with all required fields
        now = datetime.now(timezone.utc)
        mock_token = TokenData(sub="test-user", exp=now + timedelta(hours=1), iat=now)
        app.dependency_overrides[get_current_user] = lambda: mock_token
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_get_notes_due(self, mock_client, mock_service):
        """GET /api/notes/reviews/due should return notes due"""
        mock_service.get_notes_due.return_value = NotesDueResponse(
            notes=[
                NoteMetadataResponse(
                    note_id="test-001",
                    note_type="personne",
                    easiness_factor=2.5,
                    repetition_number=0,
                    interval_hours=2.0,
                    next_review=datetime.now(timezone.utc),
                    review_count=0,
                    auto_enrich=True,
                    importance="normal",
                )
            ],
            total=1,
        )

        response = mock_client.get("/api/notes/reviews/due")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 1

    def test_get_review_stats(self, mock_client, mock_service):
        """GET /api/notes/reviews/stats should return statistics"""
        mock_service.get_review_stats.return_value = ReviewStatsResponse(
            total_notes=50,
            by_type={"personne": 20, "projet": 30},
            by_importance={"high": 10, "normal": 40},
            total_due=5,
            reviewed_today=3,
            avg_easiness_factor=2.4,
        )

        response = mock_client.get("/api/notes/reviews/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_notes"] == 50

    def test_get_review_workload(self, mock_client, mock_service):
        """GET /api/notes/reviews/workload should return workload forecast"""
        mock_service.estimate_workload.return_value = ReviewWorkloadResponse(
            workload={"2026-01-05": 10, "2026-01-06": 8},
            total_upcoming=18,
        )

        response = mock_client.get("/api/notes/reviews/workload?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_upcoming"] == 18

    def test_get_review_configs(self, mock_client, mock_service):
        """GET /api/notes/reviews/configs should return configurations"""
        mock_service.get_review_configs.return_value = [
            ReviewConfigResponse(
                note_type="personne",
                base_interval_hours=2.0,
                max_interval_days=30,
                easiness_factor=2.3,
                auto_enrich=True,
                skip_revision=False,
            )
        ]

        response = mock_client.get("/api/notes/reviews/configs")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_get_note_metadata(self, mock_client, mock_service):
        """GET /api/notes/{id}/metadata should return metadata"""
        mock_service.get_note_metadata.return_value = NoteMetadataResponse(
            note_id="test-001",
            note_type="personne",
            easiness_factor=2.3,
            repetition_number=5,
            interval_hours=24.0,
            review_count=10,
            auto_enrich=True,
            importance="high",
        )

        response = mock_client.get("/api/notes/test-001/metadata")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["note_id"] == "test-001"

    def test_get_note_metadata_not_found(self, mock_client, mock_service):
        """GET /api/notes/{id}/metadata should return 200 with null data for missing note"""
        mock_service.get_note_metadata.return_value = None

        response = mock_client.get("/api/notes/nonexistent/metadata")
        # Changed behavior: returns 200 with null data instead of 404
        # This is normal for unscheduled notes
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is None

    def test_record_review(self, mock_client, mock_service):
        """POST /api/notes/{id}/review should record review"""
        mock_service.record_review.return_value = RecordReviewResponse(
            note_id="test-001",
            quality=4,
            new_easiness_factor=2.4,
            new_interval_hours=48.0,
            new_repetition_number=3,
            next_review=datetime.now(timezone.utc),
            quality_assessment="Excellent",
        )

        response = mock_client.post(
            "/api/notes/test-001/review",
            json={"quality": 4},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["quality"] == 4

    def test_record_review_invalid_quality(self, mock_client, mock_service):
        """POST /api/notes/{id}/review should reject invalid quality"""
        response = mock_client.post(
            "/api/notes/test-001/review",
            json={"quality": 10},  # Invalid - must be 0-5
        )
        assert response.status_code == 422

    def test_postpone_review(self, mock_client, mock_service):
        """POST /api/notes/{id}/postpone should postpone review"""
        mock_service.postpone_review.return_value = PostponeReviewResponse(
            note_id="test-001",
            hours_postponed=24.0,
            new_next_review=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        response = mock_client.post(
            "/api/notes/test-001/postpone",
            json={"hours": 24.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["hours_postponed"] == 24.0

    def test_trigger_immediate_review(self, mock_client, mock_service):
        """POST /api/notes/{id}/trigger should trigger immediate review"""
        mock_service.trigger_immediate_review.return_value = TriggerReviewResponse(
            note_id="test-001",
            triggered=True,
            next_review=datetime.now(timezone.utc),
        )

        response = mock_client.post("/api/notes/test-001/trigger")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["triggered"] is True

    def test_trigger_review_not_found(self, mock_client, mock_service):
        """POST /api/notes/{id}/trigger should return 404 for missing note"""
        mock_service.trigger_immediate_review.return_value = None

        response = mock_client.post("/api/notes/nonexistent/trigger")
        assert response.status_code == 404
