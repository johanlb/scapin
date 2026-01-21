"""
Tests for Memory Cycles API Endpoints

Tests all Memory Cycles v2 endpoints:
- GET /api/briefing/filage
- POST /api/briefing/lecture/{note_id}/start
- POST /api/briefing/lecture/{note_id}/complete
- GET /api/briefing/lecture/{note_id}/stats
- POST /api/briefing/filage/add/{note_id}
- POST /api/briefing/retouche/{note_id}
"""

from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app
from src.frontin.api.deps import get_metadata_store, get_scheduler
from src.passepartout.filage_service import Filage, FilageLecture
from src.passepartout.lecture_service import LectureResult, LectureSession
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import NoteType
from src.passepartout.retouche_reviewer import RetoucheResult


@pytest.fixture
def mock_metadata_store() -> MagicMock:
    """Create a mock NoteMetadataStore"""
    return MagicMock(spec=NoteMetadataStore)


@pytest.fixture
def mock_scheduler() -> MagicMock:
    """Create a mock NoteScheduler"""
    return MagicMock(spec=NoteScheduler)


@pytest.fixture
def client(mock_metadata_store: MagicMock, mock_scheduler: MagicMock) -> TestClient:
    """Create test client with dependency overrides"""
    app = create_app()

    def override_metadata_store() -> Generator[MagicMock, None, None]:
        yield mock_metadata_store

    def override_scheduler() -> Generator[MagicMock, None, None]:
        yield mock_scheduler

    app.dependency_overrides[get_metadata_store] = override_metadata_store
    app.dependency_overrides[get_scheduler] = override_scheduler

    return TestClient(app)


@pytest.fixture
def sample_filage() -> Filage:
    """Create sample Filage"""
    now = datetime.now(timezone.utc)
    lectures = [
        FilageLecture(
            note_id="note-001",
            note_title="Test Note 1",
            note_type=NoteType.PERSONNE,
            priority=1,
            reason="Questions en attente",
            quality_score=75,
            questions_pending=True,
            questions_count=3,
        ),
        FilageLecture(
            note_id="note-002",
            note_title="Test Note 2",
            note_type=NoteType.ENTITE,  # Changed from CONCEPT
            priority=3,
            reason="SM-2 révision due",
            quality_score=60,
            questions_pending=False,
            questions_count=0,
        ),
    ]
    return Filage(
        date="2026-01-21",
        generated_at=now.isoformat(),
        lectures=lectures,
        total_lectures=2,
        events_today=0,
        notes_with_questions=1,
    )


@pytest.fixture
def sample_lecture_session() -> LectureSession:
    """Create sample LectureSession"""
    return LectureSession(
        session_id="session-001",
        note_id="note-001",
        note_title="Test Note",
        note_content="# Test Note\n\nContent here.\n\n## Questions pour Johan\n- Question 1?\n- Question 2?",
        started_at=datetime.now(timezone.utc).isoformat(),
        quality_score=75,
        questions=["Question 1?", "Question 2?"],
    )


@pytest.fixture
def sample_lecture_result() -> LectureResult:
    """Create sample LectureResult"""
    return LectureResult(
        note_id="note-001",
        quality_rating=4,
        next_lecture=datetime.now(timezone.utc).isoformat(),
        interval_hours=72.0,
        answers_recorded=2,
        questions_remaining=0,
        success=True,
    )


@pytest.fixture
def sample_metadata() -> NoteMetadata:
    """Create sample NoteMetadata"""
    now = datetime.now(timezone.utc)
    return NoteMetadata(
        note_id="note-001",
        note_type=NoteType.PERSONNE,
        created_at=now,
        updated_at=now,
        quality_score=75,
        lecture_count=5,
        lecture_ef=2.5,
        lecture_interval=48.0,
        questions_pending=True,
        questions_count=2,
    )


class TestFilageEndpoint:
    """Tests for GET /api/briefing/filage endpoint"""

    def test_get_filage_success(self, client: TestClient, sample_filage: Filage) -> None:
        """Test getting filage returns success"""
        with (
            patch(
                "src.passepartout.filage_service.FilageService"
            ) as MockFilageService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.generate_filage = AsyncMock(return_value=sample_filage)
            MockFilageService.return_value = mock_service

            response = client.get("/api/briefing/filage")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

    def test_get_filage_includes_lectures(
        self, client: TestClient, sample_filage: Filage
    ) -> None:
        """Test filage includes lecture data"""
        with (
            patch(
                "src.passepartout.filage_service.FilageService"
            ) as MockFilageService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.generate_filage = AsyncMock(return_value=sample_filage)
            MockFilageService.return_value = mock_service

            response = client.get("/api/briefing/filage")

            data = response.json()["data"]
            assert data["total_lectures"] == 2
            assert len(data["lectures"]) == 2
            assert data["lectures"][0]["note_id"] == "note-001"
            assert data["lectures"][0]["questions_pending"] is True


class TestLectureStartEndpoint:
    """Tests for POST /api/briefing/lecture/{note_id}/start endpoint"""

    def test_start_lecture_success(
        self, client: TestClient, sample_lecture_session: LectureSession
    ) -> None:
        """Test starting a lecture returns session"""
        with (
            patch(
                "src.passepartout.lecture_service.LectureService"
            ) as MockLectureService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.start_lecture.return_value = sample_lecture_session
            MockLectureService.return_value = mock_service

            response = client.post("/api/briefing/lecture/note-001/start")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["session_id"] == "session-001"
            assert data["data"]["note_id"] == "note-001"
            assert len(data["data"]["questions"]) == 2

    def test_start_lecture_not_found(self, client: TestClient) -> None:
        """Test starting lecture for nonexistent note returns 404"""
        with (
            patch(
                "src.passepartout.lecture_service.LectureService"
            ) as MockLectureService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.start_lecture.return_value = None
            MockLectureService.return_value = mock_service

            response = client.post("/api/briefing/lecture/nonexistent/start")

            assert response.status_code == 404


class TestLectureCompleteEndpoint:
    """Tests for POST /api/briefing/lecture/{note_id}/complete endpoint"""

    def test_complete_lecture_success(
        self, client: TestClient, sample_lecture_result: LectureResult
    ) -> None:
        """Test completing a lecture successfully"""
        with (
            patch(
                "src.passepartout.lecture_service.LectureService"
            ) as MockLectureService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.complete_lecture.return_value = sample_lecture_result
            MockLectureService.return_value = mock_service

            response = client.post(
                "/api/briefing/lecture/note-001/complete",
                json={"quality": 4},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["quality_rating"] == 4
            assert data["data"]["success"] is True

    def test_complete_lecture_with_answers(
        self, client: TestClient, sample_lecture_result: LectureResult
    ) -> None:
        """Test completing lecture with answers"""
        with (
            patch(
                "src.passepartout.lecture_service.LectureService"
            ) as MockLectureService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.complete_lecture.return_value = sample_lecture_result
            MockLectureService.return_value = mock_service

            response = client.post(
                "/api/briefing/lecture/note-001/complete",
                json={"quality": 4, "answers": {"0": "Answer 1", "1": "Answer 2"}},
            )

            assert response.status_code == 200

    def test_complete_lecture_invalid_quality(self, client: TestClient) -> None:
        """Test completing lecture with invalid quality fails validation"""
        response = client.post(
            "/api/briefing/lecture/note-001/complete",
            json={"quality": 10},  # Invalid: must be 0-5
        )

        assert response.status_code == 422  # Validation error


class TestLectureStatsEndpoint:
    """Tests for GET /api/briefing/lecture/{note_id}/stats endpoint"""

    def test_get_lecture_stats_success(self, client: TestClient) -> None:
        """Test getting lecture stats"""
        stats = {
            "note_id": "note-001",
            "lecture_count": 5,
            "lecture_ef": 2.5,
            "lecture_interval_hours": 48.0,
            "lecture_next": "2026-01-22T06:00:00Z",
            "lecture_last": "2026-01-20T10:00:00Z",
            "quality_score": 75,
            "questions_pending": True,
            "questions_count": 2,
        }
        with (
            patch(
                "src.passepartout.lecture_service.LectureService"
            ) as MockLectureService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.get_lecture_stats.return_value = stats
            MockLectureService.return_value = mock_service

            response = client.get("/api/briefing/lecture/note-001/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["lecture_count"] == 5
            assert data["data"]["questions_pending"] is True

    def test_get_lecture_stats_not_found(self, client: TestClient) -> None:
        """Test getting stats for nonexistent note returns 404"""
        with (
            patch(
                "src.passepartout.lecture_service.LectureService"
            ) as MockLectureService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_service = MagicMock()
            mock_service.get_lecture_stats.return_value = None
            MockLectureService.return_value = mock_service

            response = client.get("/api/briefing/lecture/nonexistent/stats")

            assert response.status_code == 404


class TestAddToFilageEndpoint:
    """Tests for POST /api/briefing/filage/add/{note_id} endpoint"""

    def test_add_to_filage_success(
        self, client: TestClient, mock_scheduler: MagicMock
    ) -> None:
        """Test adding note to filage successfully"""
        mock_scheduler.trigger_immediate_review.return_value = True

        response = client.post("/api/briefing/filage/add/note-001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["note_id"] == "note-001"
        mock_scheduler.trigger_immediate_review.assert_called_once_with("note-001")

    def test_add_to_filage_note_not_found(
        self, client: TestClient, mock_scheduler: MagicMock
    ) -> None:
        """Test adding nonexistent note to filage"""
        mock_scheduler.trigger_immediate_review.return_value = False

        response = client.post("/api/briefing/filage/add/nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["data"]["message"].lower()


class TestRetoucheEndpoint:
    """Tests for POST /api/briefing/retouche/{note_id} endpoint"""

    def test_trigger_retouche_success(
        self,
        client: TestClient,
        mock_metadata_store: MagicMock,
        sample_metadata: NoteMetadata,
    ) -> None:
        """Test triggering retouche successfully"""
        retouche_result = RetoucheResult(
            note_id="note-001",
            success=True,
            quality_before=70,
            quality_after=85,
            actions=[],
            questions_added=1,
            model_used="claude-3-5-haiku",
            escalated=False,
            reasoning="Note quality improved",
        )

        # Configure mock metadata store (injected via dependency override)
        mock_metadata_store.get.return_value = sample_metadata

        with (
            patch(
                "src.passepartout.retouche_reviewer.RetoucheReviewer"
            ) as MockRetouche,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_reviewer = MagicMock()
            mock_reviewer.review_note = AsyncMock(return_value=retouche_result)
            MockRetouche.return_value = mock_reviewer

            response = client.post("/api/briefing/retouche/note-001")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["success"] is True
            assert data["data"]["improvements_count"] == 0  # Empty actions list

    def test_trigger_retouche_failure(
        self,
        client: TestClient,
        mock_metadata_store: MagicMock,
    ) -> None:
        """Test retouche failure handling"""
        retouche_result = RetoucheResult(
            note_id="note-001",
            success=False,
            quality_before=None,
            quality_after=0,
            actions=[],
            model_used="claude-3-5-haiku",
            error="Note not found",
        )

        # Configure mock metadata store (injected via dependency override)
        mock_metadata_store.get.return_value = None

        with (
            patch(
                "src.passepartout.retouche_reviewer.RetoucheReviewer"
            ) as MockRetouche,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            mock_reviewer = MagicMock()
            mock_reviewer.review_note = AsyncMock(return_value=retouche_result)
            MockRetouche.return_value = mock_reviewer

            response = client.post("/api/briefing/retouche/note-001")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["success"] is False


class TestMemoryCyclesIntegration:
    """Integration tests for Memory Cycles workflow"""

    def test_full_lecture_workflow(
        self,
        client: TestClient,
        sample_filage: Filage,
        sample_lecture_session: LectureSession,
        sample_lecture_result: LectureResult,
    ) -> None:
        """Test complete lecture workflow: filage → start → complete"""
        with (
            patch(
                "src.passepartout.filage_service.FilageService"
            ) as MockFilageService,
            patch(
                "src.passepartout.lecture_service.LectureService"
            ) as MockLectureService,
            patch("src.passepartout.note_manager.get_note_manager"),
        ):
            # Mock FilageService
            mock_filage_service = MagicMock()
            mock_filage_service.generate_filage = AsyncMock(return_value=sample_filage)
            MockFilageService.return_value = mock_filage_service

            # Mock LectureService
            mock_lecture_service = MagicMock()
            mock_lecture_service.start_lecture.return_value = sample_lecture_session
            mock_lecture_service.complete_lecture.return_value = sample_lecture_result
            MockLectureService.return_value = mock_lecture_service

            # Step 1: Get filage
            filage_response = client.get("/api/briefing/filage")
            assert filage_response.status_code == 200
            filage_data = filage_response.json()["data"]
            assert filage_data["total_lectures"] == 2

            # Step 2: Start lecture for first note
            note_id = filage_data["lectures"][0]["note_id"]
            start_response = client.post(f"/api/briefing/lecture/{note_id}/start")
            assert start_response.status_code == 200
            session_data = start_response.json()["data"]
            assert session_data["note_id"] == note_id

            # Step 3: Complete lecture
            complete_response = client.post(
                f"/api/briefing/lecture/{note_id}/complete",
                json={"quality": 4},
            )
            assert complete_response.status_code == 200
            result_data = complete_response.json()["data"]
            assert result_data["success"] is True
            assert result_data["quality_rating"] == 4
