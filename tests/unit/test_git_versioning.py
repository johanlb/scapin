"""
Tests for Git Versioning Manager

Tests the GitVersionManager class and its integration with NoteManager.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.passepartout.git_versioning import GitVersionManager, NoteDiff, NoteVersion


class TestGitVersionManager:
    """Tests for GitVersionManager class"""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def git_manager(self, temp_notes_dir):
        """Create a GitVersionManager instance"""
        return GitVersionManager(temp_notes_dir)

    def test_init_creates_repo(self, temp_notes_dir):
        """Test that initializing creates a Git repository"""
        manager = GitVersionManager(temp_notes_dir)

        assert manager.repo is not None
        assert (temp_notes_dir / ".git").exists()
        # Compare resolved paths to handle macOS /var -> /private/var symlink
        assert manager.notes_dir.resolve() == temp_notes_dir.resolve()

    def test_init_creates_gitignore(self, temp_notes_dir):
        """Test that initial commit creates .gitignore"""
        GitVersionManager(temp_notes_dir)

        gitignore = temp_notes_dir / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".DS_Store" in content
        assert ".vector_index/" in content

    def test_init_opens_existing_repo(self, temp_notes_dir):
        """Test that re-initialization opens existing repo"""
        # Create first manager
        manager1 = GitVersionManager(temp_notes_dir)
        initial_commit = list(manager1.repo.iter_commits())[0].hexsha

        # Create second manager (should open existing repo)
        manager2 = GitVersionManager(temp_notes_dir)
        reopened_commit = list(manager2.repo.iter_commits())[0].hexsha

        assert initial_commit == reopened_commit

    def test_commit_new_file(self, git_manager, temp_notes_dir):
        """Test committing a new note file"""
        # Create a note file
        note_file = temp_notes_dir / "test-note.md"
        note_file.write_text("# Test Note\n\nContent here")

        # Commit
        commit_hash = git_manager.commit("test-note.md", "Create note", "Test Note")

        assert commit_hash is not None
        assert len(commit_hash) == 7  # Short hash

        # Verify commit exists
        commits = list(git_manager.repo.iter_commits())
        assert len(commits) == 2  # Initial + our commit
        assert "Create note (Test Note)" in commits[0].message

    def test_commit_no_changes_returns_none(self, git_manager, temp_notes_dir):
        """Test that committing with no changes returns None"""
        # Create and commit a file
        note_file = temp_notes_dir / "test-note.md"
        note_file.write_text("# Test Note\n\nContent")
        git_manager.commit("test-note.md", "Create note")

        # Try to commit again without changes
        result = git_manager.commit("test-note.md", "No changes")

        assert result is None

    def test_commit_nonexistent_file(self, git_manager):
        """Test committing a file that doesn't exist"""
        result = git_manager.commit("nonexistent.md", "Try commit")
        assert result is None

    def test_commit_delete(self, git_manager, temp_notes_dir):
        """Test committing deletion of a note"""
        # Create and commit a file
        note_file = temp_notes_dir / "to-delete.md"
        note_file.write_text("# To Delete\n\nThis will be deleted")
        git_manager.commit("to-delete.md", "Create note")

        # Delete the file
        note_file.unlink()

        # Commit deletion
        commit_hash = git_manager.commit_delete("to-delete.md", "To Delete")

        assert commit_hash is not None
        commits = list(git_manager.repo.iter_commits())
        assert "Delete note: To Delete" in commits[0].message


class TestVersionHistory:
    """Tests for version history operations"""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def git_manager_with_history(self, temp_notes_dir):
        """Create a GitVersionManager with version history"""
        manager = GitVersionManager(temp_notes_dir)

        # Create a note with multiple versions
        note_file = temp_notes_dir / "versioned-note.md"

        note_file.write_text("# Version 1\n\nInitial content")
        manager.commit("versioned-note.md", "Create note", "Versioned Note")

        note_file.write_text("# Version 2\n\nUpdated content")
        manager.commit("versioned-note.md", "Update note", "Versioned Note")

        note_file.write_text("# Version 3\n\nFinal content")
        manager.commit("versioned-note.md", "Update note", "Versioned Note")

        return manager

    def test_list_versions(self, git_manager_with_history):
        """Test listing versions for a note"""
        versions = git_manager_with_history.list_versions("versioned-note.md")

        assert len(versions) == 3
        assert all(isinstance(v, NoteVersion) for v in versions)
        # Most recent first
        assert "Version 3" in versions[0].message or "Update note" in versions[0].message

    def test_list_versions_limit(self, git_manager_with_history):
        """Test limiting number of versions returned"""
        versions = git_manager_with_history.list_versions("versioned-note.md", limit=2)
        assert len(versions) == 2

    def test_list_versions_nonexistent_file(self, git_manager_with_history):
        """Test listing versions for a file that doesn't exist"""
        versions = git_manager_with_history.list_versions("nonexistent.md")
        assert versions == []

    def test_version_has_correct_attributes(self, git_manager_with_history):
        """Test that versions have all required attributes"""
        versions = git_manager_with_history.list_versions("versioned-note.md")

        for v in versions:
            assert len(v.version_id) == 7
            assert len(v.full_hash) == 40
            assert isinstance(v.message, str)
            assert isinstance(v.timestamp, datetime)
            assert v.author == "Scapin"


class TestVersionRetrieval:
    """Tests for retrieving specific versions"""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def git_manager_with_content(self, temp_notes_dir):
        """Create a GitVersionManager with different content versions"""
        manager = GitVersionManager(temp_notes_dir)

        note_file = temp_notes_dir / "content-note.md"

        note_file.write_text("Version 1 content")
        manager.commit("content-note.md", "V1")

        note_file.write_text("Version 2 content")
        manager.commit("content-note.md", "V2")

        return manager

    def test_get_version(self, git_manager_with_content):
        """Test retrieving content at a specific version"""
        versions = git_manager_with_content.list_versions("content-note.md")

        # Get older version (V1)
        v1 = versions[-1]  # Oldest
        content = git_manager_with_content.get_version("content-note.md", v1.version_id)

        assert content == "Version 1 content"

    def test_get_version_with_full_hash(self, git_manager_with_content):
        """Test retrieving version with full hash"""
        versions = git_manager_with_content.list_versions("content-note.md")
        v1 = versions[-1]

        content = git_manager_with_content.get_version("content-note.md", v1.full_hash)

        assert content == "Version 1 content"

    def test_get_version_invalid_hash(self, git_manager_with_content):
        """Test retrieving with invalid version hash"""
        content = git_manager_with_content.get_version("content-note.md", "invalid")
        assert content is None


class TestDiff:
    """Tests for diff generation"""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def git_manager_for_diff(self, temp_notes_dir):
        """Create a GitVersionManager for diff testing"""
        manager = GitVersionManager(temp_notes_dir)

        note_file = temp_notes_dir / "diff-note.md"

        note_file.write_text("Line 1\nLine 2\nLine 3")
        manager.commit("diff-note.md", "V1")

        note_file.write_text("Line 1\nLine 2 modified\nLine 3\nLine 4 added")
        manager.commit("diff-note.md", "V2")

        return manager

    def test_diff_between_versions(self, git_manager_for_diff):
        """Test generating diff between two versions"""
        versions = git_manager_for_diff.list_versions("diff-note.md")
        v1 = versions[-1]
        v2 = versions[0]

        diff = git_manager_for_diff.diff("diff-note.md", v1.version_id, v2.version_id)

        assert diff is not None
        assert isinstance(diff, NoteDiff)
        assert diff.additions > 0
        assert diff.deletions > 0
        assert "Line 2 modified" in diff.diff_text
        assert "Line 4 added" in diff.diff_text

    def test_diff_no_changes(self, temp_notes_dir):
        """Test diff when there are no changes between versions"""
        manager = GitVersionManager(temp_notes_dir)

        note_file = temp_notes_dir / "no-change.md"
        note_file.write_text("Same content")
        manager.commit("no-change.md", "V1")

        # Force a second commit (e.g., via other file)
        other_file = temp_notes_dir / "other.md"
        other_file.write_text("Other content")
        manager.commit("other.md", "Other")

        versions = manager.list_versions("no-change.md")
        # Only one version for this file
        assert len(versions) == 1


class TestRestore:
    """Tests for version restoration"""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def git_manager_for_restore(self, temp_notes_dir):
        """Create a GitVersionManager for restore testing"""
        manager = GitVersionManager(temp_notes_dir)

        note_file = temp_notes_dir / "restore-note.md"

        note_file.write_text("Original content")
        manager.commit("restore-note.md", "Original")

        note_file.write_text("Modified content")
        manager.commit("restore-note.md", "Modified")

        return manager

    def test_restore_version(self, git_manager_for_restore, temp_notes_dir):
        """Test restoring a note to a previous version"""
        versions = git_manager_for_restore.list_versions("restore-note.md")
        original_version = versions[-1]

        success = git_manager_for_restore.restore(
            "restore-note.md", original_version.version_id
        )

        assert success is True

        # Verify content was restored
        note_file = temp_notes_dir / "restore-note.md"
        assert note_file.read_text() == "Original content"

        # Verify new commit was created
        new_versions = git_manager_for_restore.list_versions("restore-note.md")
        assert len(new_versions) == 3
        assert "Restore to version" in new_versions[0].message

    def test_restore_invalid_version(self, git_manager_for_restore):
        """Test restoring to an invalid version"""
        success = git_manager_for_restore.restore("restore-note.md", "invalid")
        assert success is False


class TestStats:
    """Tests for repository statistics"""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_get_stats(self, temp_notes_dir):
        """Test getting repository statistics"""
        manager = GitVersionManager(temp_notes_dir)

        # Create a note
        note_file = temp_notes_dir / "stats-note.md"
        note_file.write_text("Content")
        manager.commit("stats-note.md", "Create")

        stats = manager.get_stats()

        assert stats["initialized"] is True
        assert stats["commit_count"] == 2  # Initial + our commit
        assert stats["is_dirty"] is False
        assert "path" in stats


class TestNoteVersionDataclass:
    """Tests for NoteVersion dataclass"""

    def test_to_dict(self):
        """Test NoteVersion.to_dict()"""
        now = datetime.now(timezone.utc)
        version = NoteVersion(
            version_id="abc1234",
            full_hash="abc1234567890abcdef1234567890abcdef12345",
            message="Test commit",
            timestamp=now,
            author="Test Author",
        )

        d = version.to_dict()

        assert d["version_id"] == "abc1234"
        assert d["full_hash"] == "abc1234567890abcdef1234567890abcdef12345"
        assert d["message"] == "Test commit"
        assert d["timestamp"] == now.isoformat()
        assert d["author"] == "Test Author"


class TestNoteDiffDataclass:
    """Tests for NoteDiff dataclass"""

    def test_to_dict(self):
        """Test NoteDiff.to_dict()"""
        diff = NoteDiff(
            note_id="test-note",
            from_version="abc1234",
            to_version="def5678",
            additions=5,
            deletions=2,
            diff_text="@@ -1,2 +1,3 @@\n-old\n+new",
            changes=[{"header": "@@ -1,2 +1,3 @@", "lines": ["-old", "+new"]}],
        )

        d = diff.to_dict()

        assert d["note_id"] == "test-note"
        assert d["from_version"] == "abc1234"
        assert d["to_version"] == "def5678"
        assert d["additions"] == 5
        assert d["deletions"] == 2
        assert "old" in d["diff_text"]
        assert len(d["changes"]) == 1


class TestNoteManagerGitIntegration:
    """Tests for NoteManager integration with Git"""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder"""
        from unittest.mock import MagicMock

        embedder = MagicMock()
        embedder.get_dimension.return_value = 384
        embedder.generate.return_value = [0.0] * 384
        return embedder

    @pytest.fixture
    def mock_vector_store(self, mock_embedder):
        """Create a mock vector store"""
        from unittest.mock import MagicMock

        store = MagicMock()
        store.add = MagicMock()
        store.remove = MagicMock()
        store.get_document = MagicMock(return_value=None)
        store.get_stats = MagicMock(return_value={"active_docs": 0})
        return store

    def test_note_manager_creates_git_repo(
        self, temp_notes_dir, mock_embedder, mock_vector_store
    ):
        """Test that NoteManager creates Git repo when git_enabled=True"""
        from src.passepartout.note_manager import NoteManager

        manager = NoteManager(
            temp_notes_dir,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            auto_index=False,
            git_enabled=True,
        )

        assert manager.git is not None
        assert (temp_notes_dir / ".git").exists()

    def test_note_manager_no_git_when_disabled(
        self, temp_notes_dir, mock_embedder, mock_vector_store
    ):
        """Test that NoteManager doesn't create Git repo when git_enabled=False"""
        from src.passepartout.note_manager import NoteManager

        manager = NoteManager(
            temp_notes_dir,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            auto_index=False,
            git_enabled=False,
        )

        assert manager.git is None
        assert not (temp_notes_dir / ".git").exists()

    def test_create_note_commits(
        self, temp_notes_dir, mock_embedder, mock_vector_store
    ):
        """Test that creating a note creates a Git commit"""
        from src.passepartout.note_manager import NoteManager

        manager = NoteManager(
            temp_notes_dir,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            auto_index=False,
            git_enabled=True,
        )
        manager.create_note("Test Note", "Content here")

        # Check commit was created
        commits = list(manager.git.repo.iter_commits())
        assert len(commits) == 2  # Initial + create
        assert "Create note" in commits[0].message
        assert "Test Note" in commits[0].message

    def test_update_note_commits(
        self, temp_notes_dir, mock_embedder, mock_vector_store
    ):
        """Test that updating a note creates a Git commit"""
        from src.passepartout.note_manager import NoteManager

        manager = NoteManager(
            temp_notes_dir,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            auto_index=False,
            git_enabled=True,
        )
        note_id = manager.create_note("Test Note", "Original content")

        manager.update_note(note_id, content="Updated content")

        # Check commit was created
        commits = list(manager.git.repo.iter_commits())
        assert len(commits) == 3  # Initial + create + update
        assert "Update note" in commits[0].message

    def test_delete_note_commits(
        self, temp_notes_dir, mock_embedder, mock_vector_store
    ):
        """Test that deleting a note creates a Git commit"""
        from src.passepartout.note_manager import NoteManager

        manager = NoteManager(
            temp_notes_dir,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            auto_index=False,
            git_enabled=True,
        )
        note_id = manager.create_note("Test Note", "To be deleted")

        manager.delete_note(note_id)

        # Check soft delete (move to trash) commit was created
        commits = list(manager.git.repo.iter_commits())
        assert len(commits) == 3  # Initial + create + move to trash
        assert "Move note" in commits[0].message  # Soft delete = move to _Supprimées
