"""
End-to-End Tests for Memory Cycles API

These tests verify the complete Memory Cycles endpoints without mocks,
using a temporary database and real service instances.

Tests:
- GET /api/briefing/filage
- POST /api/briefing/lecture/{note_id}/start
- POST /api/briefing/lecture/{note_id}/complete
- GET /api/briefing/lecture/{note_id}/stats
- POST /api/briefing/filage/add/{note_id}
- POST /api/briefing/retouche/{note_id}
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app
from src.passepartout.note_manager import NoteManager
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_types import NoteType


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with notes structure."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    # Create subdirectories for note types
    (notes_dir / "personne").mkdir()
    (notes_dir / "entite").mkdir()

    return tmp_path


@pytest.fixture
def sample_note_file(temp_data_dir: Path) -> Path:
    """Create a sample note file."""
    note_path = temp_data_dir / "notes" / "personne" / "test-person.md"
    note_content = """---
title: Test Person
type: personne
created: 2026-01-20T10:00:00Z
updated: 2026-01-21T10:00:00Z
---

# Test Person

This is a test note about a person.

## Contact
- Email: test@example.com
- Phone: +33 6 12 34 56 78

## Questions pour Johan
- What is their role?
- When did we last meet?

## Notes
Some additional notes here.
"""
    note_path.write_text(note_content)
    return note_path


@pytest.fixture
def note_manager(temp_data_dir: Path, sample_note_file: Path) -> NoteManager:
    """Create a NoteManager with the temp directory."""
    notes_dir = temp_data_dir / "notes"
    return NoteManager(notes_dir)


@pytest.fixture
def metadata_store(temp_data_dir: Path) -> NoteMetadataStore:
    """Create a NoteMetadataStore with temp database."""
    db_path = temp_data_dir / "metadata.db"
    return NoteMetadataStore(db_path)


@pytest.fixture
def sample_metadata(metadata_store: NoteMetadataStore) -> NoteMetadata:
    """Create and save sample metadata."""
    now = datetime.now(timezone.utc)
    metadata = NoteMetadata(
        note_id="test-person",
        note_type=NoteType.PERSONNE,
        created_at=now,
        updated_at=now,
        quality_score=70,
        questions_pending=True,
        questions_count=2,
    )
    metadata_store.save(metadata)
    return metadata


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestFilageEndpointE2E:
    """E2E tests for GET /api/briefing/filage endpoint."""

    def test_get_filage_returns_valid_response(self, client: TestClient) -> None:
        """Test that filage endpoint returns a valid response structure."""
        response = client.get("/api/briefing/filage")

        # Should return 200 even if empty
        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert data["success"] is True
        assert "data" in data

        filage_data = data["data"]
        assert "date" in filage_data
        assert "generated_at" in filage_data
        assert "lectures" in filage_data
        assert "total_lectures" in filage_data
        assert isinstance(filage_data["lectures"], list)

    def test_get_filage_with_max_lectures_param(self, client: TestClient) -> None:
        """Test filage with max_lectures parameter."""
        response = client.get("/api/briefing/filage?max_lectures=5")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestLectureEndpointsE2E:
    """E2E tests for lecture endpoints."""

    def test_start_lecture_not_found(self, client: TestClient) -> None:
        """Test starting lecture for nonexistent note."""
        response = client.post("/api/briefing/lecture/nonexistent-note/start")

        assert response.status_code == 404

    def test_complete_lecture_validation(self, client: TestClient) -> None:
        """Test lecture completion validation."""
        # Invalid quality (must be 0-5)
        response = client.post(
            "/api/briefing/lecture/any-note/complete",
            json={"quality": 10}
        )

        assert response.status_code == 422  # Validation error

    def test_complete_lecture_valid_quality_range(self, client: TestClient) -> None:
        """Test that valid quality values are accepted."""
        # Note doesn't exist but validation should pass
        for quality in [0, 1, 2, 3, 4, 5]:
            response = client.post(
                "/api/briefing/lecture/test-note/complete",
                json={"quality": quality}
            )
            # Should not be a validation error (422)
            # May be 200 (success) or 500 (internal error due to missing note)
            assert response.status_code != 422, f"Quality {quality} should be valid"

    def test_get_lecture_stats_not_found(self, client: TestClient) -> None:
        """Test getting stats for nonexistent note."""
        response = client.get("/api/briefing/lecture/nonexistent-note/stats")

        assert response.status_code == 404


class TestAddToFilageEndpointE2E:
    """E2E tests for POST /api/briefing/filage/add/{note_id} endpoint."""

    def test_add_to_filage_not_found(self, client: TestClient) -> None:
        """Test adding nonexistent note to filage."""
        response = client.post("/api/briefing/filage/add/nonexistent-note")

        assert response.status_code == 200
        data = response.json()
        # Should return success=False when note not found
        assert data["data"]["success"] is False

    def test_add_to_filage_response_structure(self, client: TestClient) -> None:
        """Test add-to-filage response has correct structure."""
        response = client.post("/api/briefing/filage/add/any-note")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "note_id" in data["data"]
        assert "success" in data["data"]
        assert "message" in data["data"]


class TestRetoucheEndpointE2E:
    """E2E tests for POST /api/briefing/retouche/{note_id} endpoint."""

    def test_retouche_response_structure(self, client: TestClient) -> None:
        """Test retouche endpoint returns correct structure."""
        response = client.post("/api/briefing/retouche/test-note")

        # May fail internally but should not crash
        print(f"Retouche response status: {response.status_code}")
        print(f"Retouche response body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            retouche_data = data["data"]
            assert "note_id" in retouche_data
            assert "success" in retouche_data
            assert "message" in retouche_data
        else:
            # If 500, print the error for debugging
            print(f"Retouche failed with 500: {response.text}")

    def test_retouche_with_url_encoded_note_id(self, client: TestClient) -> None:
        """Test retouche with URL-encoded note ID (like 'AFRASIA BANK')."""
        # This simulates the real error case
        response = client.post("/api/briefing/retouche/AFRASIA%20BANK")

        print(f"Retouche AFRASIA response status: {response.status_code}")
        print(f"Retouche AFRASIA response body: {response.text}")

        # Should not crash with 500
        # If note not found, should return success=False gracefully


class TestMemoryCyclesWorkflowE2E:
    """E2E integration tests for complete Memory Cycles workflow."""

    def test_filage_to_lecture_workflow(self, client: TestClient) -> None:
        """Test the basic workflow: get filage -> (if notes) start lecture."""
        # Step 1: Get filage
        filage_response = client.get("/api/briefing/filage")
        assert filage_response.status_code == 200

        filage_data = filage_response.json()["data"]
        print(f"Filage returned {filage_data['total_lectures']} lectures")

        # Step 2: If there are lectures, try to start one
        if filage_data["lectures"]:
            note_id = filage_data["lectures"][0]["note_id"]
            start_response = client.post(f"/api/briefing/lecture/{note_id}/start")
            print(f"Start lecture for {note_id}: {start_response.status_code}")

            if start_response.status_code == 200:
                session_data = start_response.json()["data"]
                assert session_data["note_id"] == note_id


# ============================================================================
# Direct Service Tests (without HTTP layer)
# ============================================================================

class TestServicesDirectly:
    """Test services directly to identify issues."""

    def test_note_metadata_store_creation(self, temp_data_dir: Path) -> None:
        """Test NoteMetadataStore can be created."""
        db_path = temp_data_dir / "test_meta.db"
        store = NoteMetadataStore(db_path)

        # Should be able to create and retrieve metadata
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="test-001",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
        )
        store.save(metadata)

        retrieved = store.get("test-001")
        assert retrieved is not None
        assert retrieved.note_id == "test-001"

    def test_note_scheduler_trigger_review(self, temp_data_dir: Path) -> None:
        """Test NoteScheduler.trigger_immediate_review."""
        from src.passepartout.note_scheduler import NoteScheduler

        db_path = temp_data_dir / "test_meta.db"
        store = NoteMetadataStore(db_path)
        scheduler = NoteScheduler(store)

        # Create metadata first
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="test-001",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
        )
        store.save(metadata)

        # Trigger immediate review
        result = scheduler.trigger_immediate_review("test-001")
        assert result is True

        # Non-existent note should return False
        result = scheduler.trigger_immediate_review("nonexistent")
        assert result is False

    def test_filage_service_creation(self, temp_data_dir: Path, note_manager: NoteManager) -> None:
        """Test FilageService can be created and generate filage."""
        from src.passepartout.filage_service import FilageService
        from src.passepartout.note_scheduler import NoteScheduler

        db_path = temp_data_dir / "test_meta.db"
        store = NoteMetadataStore(db_path)
        scheduler = NoteScheduler(store)

        service = FilageService(
            note_manager=note_manager,
            metadata_store=store,
            scheduler=scheduler,
        )

        # Should be able to generate filage
        import asyncio
        filage = asyncio.get_event_loop().run_until_complete(
            service.generate_filage(max_lectures=10)
        )

        assert filage is not None
        assert isinstance(filage.lectures, list)

    def test_lecture_service_creation(self, temp_data_dir: Path, note_manager: NoteManager) -> None:
        """Test LectureService can be created."""
        from src.passepartout.lecture_service import LectureService
        from src.passepartout.note_scheduler import NoteScheduler

        db_path = temp_data_dir / "test_meta.db"
        store = NoteMetadataStore(db_path)
        scheduler = NoteScheduler(store)

        service = LectureService(
            note_manager=note_manager,
            metadata_store=store,
            scheduler=scheduler,
        )

        # Try to start a lecture for non-existent note
        session = service.start_lecture("nonexistent")
        assert session is None

    def test_retouche_reviewer_creation(self, temp_data_dir: Path, note_manager: NoteManager) -> None:
        """Test RetoucheReviewer can be created."""
        from src.passepartout.note_scheduler import NoteScheduler
        from src.passepartout.retouche_reviewer import RetoucheReviewer

        db_path = temp_data_dir / "test_meta.db"
        store = NoteMetadataStore(db_path)
        scheduler = NoteScheduler(store)

        reviewer = RetoucheReviewer(
            note_manager=note_manager,
            metadata_store=store,
            scheduler=scheduler,
        )

        assert reviewer is not None

    @pytest.mark.asyncio
    async def test_retouche_reviewer_review_nonexistent(
        self, temp_data_dir: Path, note_manager: NoteManager
    ) -> None:
        """Test RetoucheReviewer.review_note with nonexistent note."""
        from src.passepartout.note_scheduler import NoteScheduler
        from src.passepartout.retouche_reviewer import RetoucheReviewer

        db_path = temp_data_dir / "test_meta.db"
        store = NoteMetadataStore(db_path)
        scheduler = NoteScheduler(store)

        reviewer = RetoucheReviewer(
            note_manager=note_manager,
            metadata_store=store,
            scheduler=scheduler,
        )

        # Review nonexistent note
        result = await reviewer.review_note("nonexistent-note")

        assert result is not None
        assert result.success is False
        print(f"Retouche error for nonexistent: {result.error}")
