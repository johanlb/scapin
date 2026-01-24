"""Tests for Retouche API endpoints"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.frontin.api.models.retouche import (
    ActionResultResponse,
    PendingRetoucheActionResponse,
    RetoucheQueueResponse,
)
from src.frontin.api.routers.retouche import router
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore


@pytest.fixture
def app():
    """Create test FastAPI app"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/retouche")
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


class TestRetoucheModels:
    """Tests for retouche API models"""

    def test_pending_action_response(self):
        """Should create PendingRetoucheActionResponse correctly"""
        response = PendingRetoucheActionResponse(
            action_id="action-001",
            note_id="note-001",
            note_title="Test Note",
            note_path="Personnes",
            action_type="merge_into",
            confidence=0.85,
            reasoning="Similar content found",
            target_note_id="note-002",
            target_note_title="Target Note",
            created_at=datetime.now(timezone.utc),
        )

        assert response.action_id == "action-001"
        assert response.action_type == "merge_into"
        assert response.confidence == 0.85
        assert response.target_note_id == "note-002"

    def test_retouche_queue_response(self):
        """Should create RetoucheQueueResponse correctly"""
        action = PendingRetoucheActionResponse(
            action_id="action-001",
            note_id="note-001",
            note_title="Test Note",
            note_path="",
            action_type="flag_obsolete",
            confidence=0.9,
            reasoning="Outdated content",
        )

        response = RetoucheQueueResponse(
            pending_actions=[action],
            total_count=1,
            by_type={"flag_obsolete": 1},
        )

        assert response.total_count == 1
        assert len(response.pending_actions) == 1
        assert response.by_type["flag_obsolete"] == 1

    def test_action_result_response(self):
        """Should create ActionResultResponse correctly"""
        response = ActionResultResponse(
            success=True,
            action_id="action-001",
            note_id="note-001",
            action_type="move_to_folder",
            message="Note moved to Projets",
            applied=True,
            rollback_available=True,
            rollback_token="rollback-token-123",
        )

        assert response.success is True
        assert response.applied is True
        assert response.rollback_available is True


# Note: API endpoint tests are skipped because they require authentication.
# For full API testing, see e2e tests.


class TestRetoucheMetadataIntegration:
    """Integration tests for retouche with metadata store"""

    def test_pending_actions_stored_in_metadata(self, metadata_store):
        """Should store pending actions in note metadata"""
        # Create metadata with pending action
        metadata = NoteMetadata(
            note_id="note-001",
            pending_actions=[
                {
                    "action_id": "action-001",
                    "action_type": "merge_into",
                    "target_note_id": "note-002",
                    "confidence": 0.7,
                    "reasoning": "Duplicate",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )

        metadata_store.save(metadata)
        retrieved = metadata_store.get("note-001")

        assert retrieved is not None
        assert len(retrieved.pending_actions) == 1
        assert retrieved.pending_actions[0]["action_type"] == "merge_into"

    def test_obsolete_flag_stored_in_metadata(self, metadata_store):
        """Should store obsolete flag in note metadata"""
        metadata = NoteMetadata(
            note_id="note-001",
            obsolete_flag=True,
            obsolete_reason="Content outdated since 2024",
        )

        metadata_store.save(metadata)
        retrieved = metadata_store.get("note-001")

        assert retrieved is not None
        assert retrieved.obsolete_flag is True
        assert "2024" in retrieved.obsolete_reason

    def test_get_notes_with_pending_actions(self, metadata_store):
        """Should query notes with pending actions"""
        # Create notes with and without pending actions
        meta_with_actions = NoteMetadata(
            note_id="note-with-actions",
            pending_actions=[{"action_id": "a1", "action_type": "score"}],
        )
        meta_without_actions = NoteMetadata(
            note_id="note-without-actions",
            pending_actions=[],
        )

        metadata_store.save(meta_with_actions)
        metadata_store.save(meta_without_actions)

        results = metadata_store.get_notes_with_pending_actions()

        assert len(results) >= 1
        note_ids = [m.note_id for m in results]
        assert "note-with-actions" in note_ids

    def test_get_obsolete_notes(self, metadata_store):
        """Should query obsolete notes"""
        meta_obsolete = NoteMetadata(
            note_id="obsolete-note",
            obsolete_flag=True,
            obsolete_reason="Deprecated",
        )
        meta_active = NoteMetadata(
            note_id="active-note",
            obsolete_flag=False,
        )

        metadata_store.save(meta_obsolete)
        metadata_store.save(meta_active)

        results = metadata_store.get_obsolete_notes()

        assert len(results) >= 1
        note_ids = [m.note_id for m in results]
        assert "obsolete-note" in note_ids
        assert "active-note" not in note_ids

    def test_clear_pending_action(self, metadata_store):
        """Should clear a specific pending action"""
        metadata = NoteMetadata(
            note_id="note-001",
            pending_actions=[
                {"id": "a1", "action_type": "merge_into"},
                {"id": "a2", "action_type": "move_to_folder"},
            ],
        )
        metadata_store.save(metadata)

        # Clear one action
        result = metadata_store.clear_pending_action("note-001", "a1")
        assert result is True

        retrieved = metadata_store.get("note-001")
        assert len(retrieved.pending_actions) == 1
        assert retrieved.pending_actions[0]["id"] == "a2"
