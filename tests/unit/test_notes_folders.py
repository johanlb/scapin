"""
Tests for Notes Folder API

Tests folder creation and listing endpoints.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.jeeves.api.app import create_app
from src.jeeves.api.deps import get_cached_config
from src.jeeves.api.models.notes import FolderCreateResponse, FolderListResponse
from src.jeeves.api.services.notes_service import NotesService
from src.passepartout.note_manager import NoteManager


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock configuration"""
    config = MagicMock()
    config.notes_dir = None  # Use default
    return config


@pytest.fixture
def client(mock_config: MagicMock) -> TestClient:
    """Create test client with mocked config"""
    app = create_app()
    app.dependency_overrides[get_cached_config] = lambda: mock_config
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestNoteManagerFolderMethods:
    """Tests for NoteManager folder methods"""

    def test_create_folder_simple(self) -> None:
        """Test creating a simple folder"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            result = manager.create_folder("Projects")

            assert result.exists()
            assert result.is_dir()
            # Use samefile to handle macOS /var vs /private/var
            assert result.samefile(Path(tmpdir) / "Projects")

    def test_create_folder_nested(self) -> None:
        """Test creating nested folders"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            result = manager.create_folder("Clients/ABC/2026")

            assert result.exists()
            assert result.is_dir()
            assert (Path(tmpdir) / "Clients").exists()
            assert (Path(tmpdir) / "Clients" / "ABC").exists()
            assert (Path(tmpdir) / "Clients" / "ABC" / "2026").exists()

    def test_create_folder_idempotent(self) -> None:
        """Test creating folder that already exists succeeds"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            # Create first time
            result1 = manager.create_folder("Projects")
            # Create second time (should not fail)
            result2 = manager.create_folder("Projects")

            assert result1 == result2
            assert result2.exists()

    def test_create_folder_empty_path_fails(self) -> None:
        """Test that empty path raises ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            with pytest.raises(ValueError, match="cannot be empty"):
                manager.create_folder("")

            with pytest.raises(ValueError, match="cannot be empty"):
                manager.create_folder("   ")

    def test_create_folder_traversal_attack_fails(self) -> None:
        """Test that path traversal is blocked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            with pytest.raises(ValueError, match="Invalid path component"):
                manager.create_folder("../outside")

            with pytest.raises(ValueError, match="Invalid path component"):
                manager.create_folder("Projects/../../../etc")

            with pytest.raises(ValueError, match="Invalid path component"):
                manager.create_folder("./current")

    def test_create_folder_invalid_characters_fails(self) -> None:
        """Test that invalid characters are rejected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            with pytest.raises(ValueError, match="Invalid characters"):
                manager.create_folder("Projects:test")

            with pytest.raises(ValueError, match="Invalid characters"):
                manager.create_folder("Projects<test>")

    def test_create_folder_normalizes_slashes(self) -> None:
        """Test that leading/trailing slashes are normalized"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            result = manager.create_folder("/Projects/ABC/")

            assert result.exists()
            # Use samefile to handle macOS /var vs /private/var
            assert result.samefile(Path(tmpdir) / "Projects" / "ABC")

    def test_list_folders_empty(self) -> None:
        """Test listing folders when none exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            folders = manager.list_folders()

            assert folders == []

    def test_list_folders(self) -> None:
        """Test listing folders"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            # Create some folders
            manager.create_folder("Projects")
            manager.create_folder("Clients/ABC")
            manager.create_folder("Archive/2025")

            folders = manager.list_folders()

            # Convert to set for easier comparison (order doesn't matter)
            folder_set = set(folders)
            assert "Projects" in folder_set
            assert "Clients" in folder_set
            assert "Clients/ABC" in folder_set
            assert "Archive" in folder_set
            assert "Archive/2025" in folder_set
            # Should have at least 5 folders
            assert len(folders) >= 5

    def test_list_folders_excludes_hidden(self) -> None:
        """Test that hidden folders are excluded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NoteManager(Path(tmpdir), auto_index=False, git_enabled=False)

            # Create visible folder
            manager.create_folder("Projects")
            # Create hidden folder manually (create_folder might reject it)
            hidden_root = Path(tmpdir) / ".hidden"
            hidden_root.mkdir()
            hidden_internal = Path(tmpdir) / "Projects" / ".internal"
            hidden_internal.mkdir()

            folders = manager.list_folders()

            folder_set = set(folders)
            assert "Projects" in folder_set
            assert ".hidden" not in folder_set
            # Hidden inside visible should also be excluded
            for f in folders:
                assert not f.startswith(".")
                assert "/." not in f


class TestNotesService:
    """Tests for NotesService folder methods"""

    @pytest.mark.asyncio
    async def test_create_folder_new(self) -> None:
        """Test creating a new folder via service"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.notes_dir = tmpdir
            service = NotesService(config=config)

            result = await service.create_folder("Projects/New")

            assert result.path == "Projects/New"
            assert result.created is True
            assert Path(result.absolute_path).exists()

    @pytest.mark.asyncio
    async def test_create_folder_existing(self) -> None:
        """Test creating a folder that already exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.notes_dir = tmpdir
            service = NotesService(config=config)

            # Create first time
            await service.create_folder("Projects")
            # Create second time
            result = await service.create_folder("Projects")

            assert result.path == "Projects"
            assert result.created is False  # Already existed

    @pytest.mark.asyncio
    async def test_list_folders(self) -> None:
        """Test listing folders via service"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.notes_dir = tmpdir
            service = NotesService(config=config)

            # Create some folders
            await service.create_folder("Projects")
            await service.create_folder("Clients/ABC")

            result = await service.list_folders()

            assert isinstance(result, FolderListResponse)
            folder_set = set(result.folders)
            assert "Projects" in folder_set
            assert "Clients" in folder_set
            assert "Clients/ABC" in folder_set
            # At least Projects, Clients, and Clients/ABC
            assert result.total >= 3


class TestFolderEndpoints:
    """Tests for folder API endpoints"""

    def test_create_folder_success(self, client: TestClient) -> None:
        """Test POST /api/notes/folders creates folder"""
        mock_response = FolderCreateResponse(
            path="Projects/New",
            absolute_path="/tmp/notes/Projects/New",
            created=True,
        )

        with patch.object(
            NotesService, "create_folder", return_value=mock_response
        ) as mock_method:
            response = client.post(
                "/api/notes/folders",
                json={"path": "Projects/New"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["path"] == "Projects/New"
        assert data["data"]["created"] is True
        mock_method.assert_called_once()

    def test_create_folder_invalid_path(self, client: TestClient) -> None:
        """Test POST /api/notes/folders with invalid path"""
        with patch.object(
            NotesService,
            "create_folder",
            side_effect=ValueError("Invalid path component: '..'"),
        ):
            response = client.post(
                "/api/notes/folders",
                json={"path": "../outside"},
            )

        assert response.status_code == 400
        assert "Invalid path component" in response.json()["detail"]

    def test_create_folder_empty_path(self, client: TestClient) -> None:
        """Test POST /api/notes/folders with empty path"""
        # Pydantic validation should catch empty path
        response = client.post(
            "/api/notes/folders",
            json={"path": ""},
        )

        assert response.status_code == 422  # Validation error

    def test_list_folders_success(self, client: TestClient) -> None:
        """Test GET /api/notes/folders returns folder list"""
        mock_response = FolderListResponse(
            folders=["Projects", "Clients", "Clients/ABC"],
            total=3,
        )

        with patch.object(
            NotesService, "list_folders", return_value=mock_response
        ):
            response = client.get("/api/notes/folders")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Projects" in data["data"]["folders"]
        assert data["data"]["total"] == 3

    def test_create_folder_has_timestamp(self, client: TestClient) -> None:
        """Test response includes timestamp"""
        mock_response = FolderCreateResponse(
            path="Projects",
            absolute_path="/tmp/notes/Projects",
            created=True,
        )

        with patch.object(
            NotesService, "create_folder", return_value=mock_response
        ):
            response = client.post(
                "/api/notes/folders",
                json={"path": "Projects"},
            )

        data = response.json()
        assert "timestamp" in data
