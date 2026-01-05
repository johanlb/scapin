"""
Tests for Notes API Router

Tests notes tree, listing, CRUD, search, and links endpoints.
"""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.jeeves.api.app import create_app
from src.jeeves.api.deps import get_notes_service
from src.jeeves.api.models.notes import (
    FolderNode,
    NoteLinksResponse,
    NoteResponse,
    NoteSearchResponse,
    NoteSearchResult,
    NotesTreeResponse,
    NoteSyncStatus,
    WikilinkResponse,
)


@pytest.fixture
def sample_note() -> NoteResponse:
    """Create a sample note response"""
    return NoteResponse(
        note_id="test-note-123",
        title="Test Note",
        content="# Test\n\nThis is test content with [[Link]].",
        excerpt="Test content preview...",
        path="Inbox",
        tags=["test", "sample"],
        entities=[],
        created_at=datetime(2026, 1, 5, 10, 0, 0),
        updated_at=datetime(2026, 1, 5, 11, 0, 0),
        pinned=False,
        metadata={"path": "Inbox", "pinned": False},
    )


@pytest.fixture
def sample_pinned_note() -> NoteResponse:
    """Create a sample pinned note"""
    return NoteResponse(
        note_id="pinned-note-456",
        title="Important Note",
        content="# Important\n\nThis note is pinned.",
        excerpt="Important note preview...",
        path="Work",
        tags=["important"],
        entities=[],
        created_at=datetime(2026, 1, 4, 10, 0, 0),
        updated_at=datetime(2026, 1, 4, 12, 0, 0),
        pinned=True,
        metadata={"path": "Work", "pinned": True},
    )


@pytest.fixture
def mock_notes_service(
    sample_note: NoteResponse, sample_pinned_note: NoteResponse
) -> MagicMock:
    """Create mock notes service"""
    service = MagicMock()

    # Sample folder tree
    folders = [
        FolderNode(name="Inbox", path="Inbox", note_count=1, children=[]),
        FolderNode(
            name="Work",
            path="Work",
            note_count=2,
            children=[
                FolderNode(name="Projects", path="Work/Projects", note_count=1, children=[])
            ],
        ),
    ]

    # Sample tree response
    tree = NotesTreeResponse(
        folders=folders,
        pinned=[sample_pinned_note],
        recent=[sample_note, sample_pinned_note],
        total_notes=3,
    )

    # Sample search response
    search_results = NoteSearchResponse(
        query="test",
        results=[
            NoteSearchResult(note=sample_note, score=0.95, highlights=["test content"])
        ],
        total=1,
    )

    # Sample links response
    links = NoteLinksResponse(
        note_id="test-note-123",
        outgoing=[
            WikilinkResponse(
                text="Link",
                target_id="other-note-789",
                target_title="Other Note",
                exists=True,
            )
        ],
        incoming=[
            WikilinkResponse(
                text="Test Note",
                target_id="referring-note-111",
                target_title="Referring Note",
                exists=True,
            )
        ],
    )

    # Sample sync status
    sync_status = NoteSyncStatus(
        last_sync=None,
        syncing=False,
        notes_synced=0,
        errors=[],
    )

    # Mock async methods
    service.get_notes_tree = AsyncMock(return_value=tree)
    service.list_notes = AsyncMock(return_value=([sample_note, sample_pinned_note], 2))
    service.get_note = AsyncMock(return_value=sample_note)
    service.create_note = AsyncMock(return_value=sample_note)
    service.update_note = AsyncMock(return_value=sample_note)
    service.delete_note = AsyncMock(return_value=True)
    service.search_notes = AsyncMock(return_value=search_results)
    service.get_note_links = AsyncMock(return_value=links)
    service.toggle_pin = AsyncMock(return_value=sample_pinned_note)
    service.get_sync_status = AsyncMock(return_value=sync_status)
    service.sync_apple_notes = AsyncMock(return_value=sync_status)

    return service


@pytest.fixture
def client(mock_notes_service: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked service"""
    app = create_app()
    app.dependency_overrides[get_notes_service] = lambda: mock_notes_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetNotesTree:
    """Tests for GET /api/notes/tree endpoint"""

    def test_tree_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test getting notes tree returns success"""
        response = client.get("/api/notes/tree")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_tree_includes_folders(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test tree includes folder structure"""
        response = client.get("/api/notes/tree")

        data = response.json()["data"]
        assert "folders" in data
        assert len(data["folders"]) == 2
        assert data["folders"][0]["name"] == "Inbox"
        assert data["folders"][1]["name"] == "Work"

    def test_tree_includes_nested_folders(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test tree includes nested folder structure"""
        response = client.get("/api/notes/tree")

        data = response.json()["data"]
        work_folder = data["folders"][1]
        assert len(work_folder["children"]) == 1
        assert work_folder["children"][0]["name"] == "Projects"

    def test_tree_includes_pinned_notes(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test tree includes pinned notes"""
        response = client.get("/api/notes/tree")

        data = response.json()["data"]
        assert "pinned" in data
        assert len(data["pinned"]) == 1
        assert data["pinned"][0]["pinned"] is True

    def test_tree_includes_recent_notes(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test tree includes recent notes"""
        response = client.get("/api/notes/tree")

        data = response.json()["data"]
        assert "recent" in data
        assert len(data["recent"]) == 2

    def test_tree_includes_total_count(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test tree includes total notes count"""
        response = client.get("/api/notes/tree")

        data = response.json()["data"]
        assert data["total_notes"] == 3

    def test_tree_accepts_recent_limit(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test tree accepts recent_limit parameter"""
        response = client.get("/api/notes/tree?recent_limit=5")

        assert response.status_code == 200
        mock_notes_service.get_notes_tree.assert_called_once()
        call_kwargs = mock_notes_service.get_notes_tree.call_args[1]
        assert call_kwargs["recent_limit"] == 5


class TestListNotes:
    """Tests for GET /api/notes endpoint"""

    def test_list_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test listing notes returns success"""
        response = client.get("/api/notes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_list_includes_pagination(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test listing includes pagination info"""
        response = client.get("/api/notes?page=1&page_size=20")

        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "has_more" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_filters_by_path(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test listing can filter by path"""
        response = client.get("/api/notes?path=Work")

        assert response.status_code == 200
        mock_notes_service.list_notes.assert_called_once()
        call_kwargs = mock_notes_service.list_notes.call_args[1]
        assert call_kwargs["path"] == "Work"

    def test_list_filters_by_tags(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test listing can filter by tags"""
        response = client.get("/api/notes?tags=test,sample")

        assert response.status_code == 200
        mock_notes_service.list_notes.assert_called_once()
        call_kwargs = mock_notes_service.list_notes.call_args[1]
        assert call_kwargs["tags"] == ["test", "sample"]

    def test_list_filters_pinned_only(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test listing can filter pinned only"""
        response = client.get("/api/notes?pinned=true")

        assert response.status_code == 200
        mock_notes_service.list_notes.assert_called_once()
        call_kwargs = mock_notes_service.list_notes.call_args[1]
        assert call_kwargs["pinned_only"] is True


class TestGetNote:
    """Tests for GET /api/notes/{note_id} endpoint"""

    def test_get_note_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test getting single note returns success"""
        response = client.get("/api/notes/test-note-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["note_id"] == "test-note-123"

    def test_get_note_includes_content(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test note includes full content"""
        response = client.get("/api/notes/test-note-123")

        data = response.json()["data"]
        assert "content" in data
        assert "# Test" in data["content"]

    def test_get_note_not_found(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test getting non-existent note returns 404"""
        mock_notes_service.get_note = AsyncMock(return_value=None)

        response = client.get("/api/notes/non-existent")

        assert response.status_code == 404


class TestCreateNote:
    """Tests for POST /api/notes endpoint"""

    def test_create_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test creating note returns success"""
        response = client.post(
            "/api/notes",
            json={"title": "New Note", "content": "Note content"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_create_with_all_fields(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test creating note with all optional fields"""
        response = client.post(
            "/api/notes",
            json={
                "title": "New Note",
                "content": "Note content",
                "path": "Work/Projects",
                "tags": ["new", "project"],
                "pinned": True,
            },
        )

        assert response.status_code == 200
        mock_notes_service.create_note.assert_called_once()
        call_kwargs = mock_notes_service.create_note.call_args[1]
        assert call_kwargs["title"] == "New Note"
        assert call_kwargs["path"] == "Work/Projects"
        assert call_kwargs["tags"] == ["new", "project"]
        assert call_kwargs["pinned"] is True

    def test_create_requires_title(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test creating note requires title"""
        response = client.post(
            "/api/notes",
            json={"content": "Note content"},
        )

        assert response.status_code == 422  # Validation error

    def test_create_requires_content(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test creating note requires content"""
        response = client.post(
            "/api/notes",
            json={"title": "New Note"},
        )

        assert response.status_code == 422  # Validation error


class TestUpdateNote:
    """Tests for PATCH /api/notes/{note_id} endpoint"""

    def test_update_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test updating note returns success"""
        response = client.patch(
            "/api/notes/test-note-123",
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_update_partial_fields(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test updating only some fields"""
        response = client.patch(
            "/api/notes/test-note-123",
            json={"tags": ["updated", "tags"]},
        )

        assert response.status_code == 200
        mock_notes_service.update_note.assert_called_once()
        call_kwargs = mock_notes_service.update_note.call_args[1]
        assert call_kwargs["tags"] == ["updated", "tags"]
        assert call_kwargs["title"] is None  # Not updated

    def test_update_not_found(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test updating non-existent note returns 404"""
        mock_notes_service.update_note = AsyncMock(return_value=None)

        response = client.patch(
            "/api/notes/non-existent",
            json={"title": "Updated"},
        )

        assert response.status_code == 404


class TestDeleteNote:
    """Tests for DELETE /api/notes/{note_id} endpoint"""

    def test_delete_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test deleting note returns success"""
        response = client.delete("/api/notes/test-note-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_not_found(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test deleting non-existent note returns 404"""
        mock_notes_service.delete_note = AsyncMock(return_value=False)

        response = client.delete("/api/notes/non-existent")

        assert response.status_code == 404


class TestSearchNotes:
    """Tests for GET /api/notes/search endpoint"""

    def test_search_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test search returns success"""
        response = client.get("/api/notes/search?q=test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_search_includes_results(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test search includes results with scores"""
        response = client.get("/api/notes/search?q=test")

        data = response.json()["data"]
        assert data["query"] == "test"
        assert len(data["results"]) == 1
        assert "score" in data["results"][0]
        assert data["results"][0]["score"] == 0.95

    def test_search_requires_query(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test search requires query parameter"""
        response = client.get("/api/notes/search")

        assert response.status_code == 422  # Validation error

    def test_search_with_tags_filter(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test search can filter by tags"""
        response = client.get("/api/notes/search?q=test&tags=sample,work")

        assert response.status_code == 200
        mock_notes_service.search_notes.assert_called_once()
        call_kwargs = mock_notes_service.search_notes.call_args[1]
        assert call_kwargs["tags"] == ["sample", "work"]

    def test_search_with_limit(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test search respects limit parameter"""
        response = client.get("/api/notes/search?q=test&limit=5")

        assert response.status_code == 200
        mock_notes_service.search_notes.assert_called_once()
        call_kwargs = mock_notes_service.search_notes.call_args[1]
        assert call_kwargs["limit"] == 5


class TestGetNoteLinks:
    """Tests for GET /api/notes/{note_id}/links endpoint"""

    def test_links_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test getting links returns success"""
        response = client.get("/api/notes/test-note-123/links")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_links_includes_outgoing(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test links includes outgoing wikilinks"""
        response = client.get("/api/notes/test-note-123/links")

        data = response.json()["data"]
        assert "outgoing" in data
        assert len(data["outgoing"]) == 1
        assert data["outgoing"][0]["text"] == "Link"
        assert data["outgoing"][0]["exists"] is True

    def test_links_includes_incoming(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test links includes incoming backlinks"""
        response = client.get("/api/notes/test-note-123/links")

        data = response.json()["data"]
        assert "incoming" in data
        assert len(data["incoming"]) == 1
        assert data["incoming"][0]["target_title"] == "Referring Note"

    def test_links_not_found(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test links for non-existent note returns 404"""
        mock_notes_service.get_note_links = AsyncMock(return_value=None)

        response = client.get("/api/notes/non-existent/links")

        assert response.status_code == 404


class TestTogglePin:
    """Tests for POST /api/notes/{note_id}/pin endpoint"""

    def test_toggle_pin_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test toggling pin returns success"""
        response = client.post("/api/notes/test-note-123/pin")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["pinned"] is True  # From sample_pinned_note

    def test_toggle_pin_not_found(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test toggling pin for non-existent note returns 404"""
        mock_notes_service.toggle_pin = AsyncMock(return_value=None)

        response = client.post("/api/notes/non-existent/pin")

        assert response.status_code == 404


class TestSyncStatus:
    """Tests for GET /api/notes/sync/status endpoint"""

    def test_sync_status_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test getting sync status returns success"""
        response = client.get("/api/notes/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_sync_status_includes_info(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test sync status includes all info"""
        response = client.get("/api/notes/sync/status")

        data = response.json()["data"]
        assert "last_sync" in data
        assert "syncing" in data
        assert "notes_synced" in data
        assert "errors" in data


class TestTriggerSync:
    """Tests for POST /api/notes/sync endpoint"""

    def test_trigger_sync_returns_success(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test triggering sync returns success"""
        response = client.post("/api/notes/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_trigger_sync_calls_service(
        self, client: TestClient, mock_notes_service: MagicMock
    ) -> None:
        """Test triggering sync calls the service method"""
        response = client.post("/api/notes/sync")

        assert response.status_code == 200
        mock_notes_service.sync_apple_notes.assert_called_once()
