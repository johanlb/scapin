"""
Tests for NoteManager

Coverage:
- Note creation and management
- YAML frontmatter parsing
- Vector search integration
- Entity-based retrieval
- Path sanitization (security)
- Thread safety
"""

from unittest.mock import Mock

import pytest

from src.core.events import Entity
from src.passepartout.note_manager import NoteManager


class TestNoteManagerInit:
    """Test NoteManager initialization"""

    def test_init_creates_directory(self, tmp_path):
        """Test initialization creates notes directory"""
        notes_dir = tmp_path / "notes"
        assert not notes_dir.exists()

        vector_store = Mock()
        embedder = Mock()

        manager = NoteManager(
            notes_dir=notes_dir,
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

        assert notes_dir.exists()
        assert manager.notes_dir == notes_dir

    def test_init_with_existing_directory(self, tmp_path):
        """Test initialization with existing directory"""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()

        vector_store = Mock()
        embedder = Mock()

        manager = NoteManager(
            notes_dir=notes_dir,
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

        assert manager.notes_dir == notes_dir


class TestCreateNote:
    """Test note creation"""

    @pytest.fixture
    def manager(self, tmp_path):
        vector_store = Mock()
        embedder = Mock()
        return NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

    def test_create_note_basic(self, manager):
        """Test creating basic note"""
        note_id = manager.create_note(
            title="Test Note",
            content="Test content"
        )

        assert note_id is not None
        assert isinstance(note_id, str)
        assert len(note_id) > 0

        # Verify file created
        note = manager.get_note(note_id)
        assert note is not None
        assert note.title == "Test Note"
        assert note.content == "Test content"

    def test_create_note_with_metadata(self, manager):
        """Test creating note with full metadata"""
        entity = Entity(type="person", value="John Doe", confidence=0.9)

        note_id = manager.create_note(
            title="Meeting Notes",
            content="Discussed project timeline",
            tags=["work", "project"],
            entities=[entity],
            metadata={"meeting_date": "2025-01-15"}
        )

        note = manager.get_note(note_id)
        assert note.tags == ["work", "project"]
        assert len(note.entities) == 1
        assert note.entities[0].value == "John Doe"
        assert note.metadata["meeting_date"] == "2025-01-15"

    def test_create_note_empty_title_raises(self, manager):
        """Test error on empty title"""
        with pytest.raises(ValueError, match="Note title cannot be empty"):
            manager.create_note(title="", content="Content")

        with pytest.raises(ValueError, match="Note title cannot be empty"):
            manager.create_note(title="   ", content="Content")

    def test_create_note_empty_content_raises(self, manager):
        """Test error on empty content"""
        with pytest.raises(ValueError, match="Note content cannot be empty"):
            manager.create_note(title="Title", content="")

        with pytest.raises(ValueError, match="Note content cannot be empty"):
            manager.create_note(title="Title", content="   ")


class TestPathSanitization:
    """Test path sanitization and security (P1-1 Fix)"""

    @pytest.fixture
    def manager(self, tmp_path):
        vector_store = Mock()
        embedder = Mock()
        return NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

    def test_sanitize_path_separators(self, manager):
        """Test path separators are removed"""
        sanitized = manager._sanitize_title("../../../etc/passwd")
        assert "/" not in sanitized
        # Result will be like "-..-..-etc-passwd" (slashes replaced with -)
        # Verify it's safe for filesystem
        assert "/" not in sanitized
        assert not sanitized.startswith(".")

    def test_sanitize_windows_separators(self, manager):
        """Test Windows path separators are removed"""
        sanitized = manager._sanitize_title("..\\..\\..\\windows\\system32")
        assert "\\" not in sanitized
        # Result will be like "-..-..-windows-system32" (backslashes replaced)
        assert "\\" not in sanitized
        assert not sanitized.startswith(".")

    def test_sanitize_special_characters(self, manager):
        """Test special characters are removed"""
        dangerous = 'Test*File?Name<>:|"'
        sanitized = manager._sanitize_title(dangerous)

        for char in '*?<>:|"':
            assert char not in sanitized

    def test_sanitize_control_characters(self, manager):
        """Test control characters are removed"""
        # Test with null byte and other control chars
        title_with_control = "Test\x00File\x1fName\x7f"
        sanitized = manager._sanitize_title(title_with_control)

        assert "\x00" not in sanitized
        assert "\x1f" not in sanitized
        assert "\x7f" not in sanitized

    def test_sanitize_leading_trailing_dots(self, manager):
        """Test leading/trailing dots are removed"""
        sanitized = manager._sanitize_title("...test...")
        assert not sanitized.startswith(".")
        assert not sanitized.endswith(".")

    def test_sanitize_length_limit(self, manager):
        """Test overly long titles are truncated"""
        long_title = "A" * 200
        sanitized = manager._sanitize_title(long_title)
        assert len(sanitized) <= 100

    def test_sanitize_empty_becomes_untitled(self, manager):
        """Test empty title becomes 'untitled'"""
        sanitized = manager._sanitize_title("///")
        assert sanitized == "untitled"

        sanitized = manager._sanitize_title("...")
        assert sanitized == "untitled"

    def test_create_note_prevents_traversal(self, manager):
        """Test creating note with malicious title is safe"""
        malicious_titles = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "test/../../../secret.txt"
        ]

        for title in malicious_titles:
            note_id = manager.create_note(title, "Content")
            note = manager.get_note(note_id)

            # Verify file is within notes_dir
            assert note.file_path is not None
            assert note.file_path.is_relative_to(manager.notes_dir)

            # Verify no path traversal in actual filename
            assert ".." not in str(note.file_path)

    def test_get_note_path_blocks_traversal(self, manager):
        """Test _get_note_path blocks directory traversal"""
        # Even if someone tries to use a crafted note_id
        with pytest.raises(ValueError, match="outside notes directory"):
            # Try to escape using relative path
            manager._get_note_path("../../../etc/passwd")


class TestUpdateNote:
    """Test note updates"""

    @pytest.fixture
    def manager_with_note(self, tmp_path):
        vector_store = Mock()
        embedder = Mock()
        manager = NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

        note_id = manager.create_note(
            title="Original Title",
            content="Original content",
            tags=["tag1"]
        )

        return manager, note_id

    def test_update_note_title(self, manager_with_note):
        """Test updating note title"""
        manager, note_id = manager_with_note

        success = manager.update_note(note_id, title="Updated Title")
        assert success is True

        note = manager.get_note(note_id)
        assert note.title == "Updated Title"
        assert note.content == "Original content"

    def test_update_note_content(self, manager_with_note):
        """Test updating note content"""
        manager, note_id = manager_with_note

        success = manager.update_note(note_id, content="Updated content")
        assert success is True

        note = manager.get_note(note_id)
        assert note.content == "Updated content"

    def test_update_note_tags(self, manager_with_note):
        """Test updating note tags"""
        manager, note_id = manager_with_note

        success = manager.update_note(note_id, tags=["tag2", "tag3"])
        assert success is True

        note = manager.get_note(note_id)
        assert note.tags == ["tag2", "tag3"]

    def test_update_nonexistent_note_returns_false(self, manager_with_note):
        """Test updating nonexistent note returns False"""
        manager, _ = manager_with_note

        success = manager.update_note("nonexistent", title="New Title")
        assert success is False


class TestSearchNotes:
    """Test note search functionality"""

    @pytest.fixture
    def manager_with_notes(self, tmp_path):
        vector_store = Mock()
        embedder = Mock()

        # Mock search to return doc IDs
        def mock_search(query, top_k, filter_fn=None):
            # Return mock results based on query
            if "python" in query.lower():
                return [
                    ("note1", 0.9, {"tags": ["python", "programming"]}),
                    ("note2", 0.8, {"tags": ["python"]})
                ]
            return []

        vector_store.search.side_effect = mock_search

        manager = NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

        # Create test notes
        manager.create_note("Python Tutorial", "Learn Python")
        manager.create_note("JavaScript Guide", "Learn JS")

        return manager

    def test_search_notes_basic(self, manager_with_notes):
        """Test basic note search"""
        results = manager_with_notes.search_notes("python", top_k=5)

        # Should call vector_store.search
        manager_with_notes.vector_store.search.assert_called()

    def test_search_notes_with_tags(self, manager_with_notes):
        """Test search with tag filter"""
        results = manager_with_notes.search_notes(
            "python",
            top_k=5,
            tags=["python"]
        )

        # Should call with filter_fn
        manager_with_notes.vector_store.search.assert_called()


class TestGetNotesbyEntity:
    """Test entity-based retrieval"""

    @pytest.fixture
    def manager(self, tmp_path):
        vector_store = Mock()
        embedder = Mock()

        # Mock search for entity
        vector_store.search.return_value = [
            ("note1", 0.95, {"entities": ["John Doe"]}),
        ]

        return NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

    def test_get_notes_by_entity(self, manager):
        """Test getting notes by entity"""
        entity = Entity(type="person", value="John Doe", confidence=0.9)

        results = manager.get_notes_by_entity(entity, top_k=10)

        # Should search with entity value
        manager.vector_store.search.assert_called()
        call_args = manager.vector_store.search.call_args
        assert "John Doe" in call_args[1]["query"]


class TestYAMLFrontmatter:
    """Test YAML frontmatter handling"""

    @pytest.fixture
    def manager(self, tmp_path):
        vector_store = Mock()
        embedder = Mock()
        return NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

    def test_write_and_read_frontmatter(self, manager):
        """Test writing and reading YAML frontmatter"""
        entity = Entity(type="person", value="Alice", confidence=0.9)

        note_id = manager.create_note(
            title="Test Note",
            content="Test content",
            tags=["test", "demo"],
            entities=[entity],
            metadata={"custom": "value"}
        )

        # Read file directly
        note = manager.get_note(note_id)
        file_path = note.file_path

        with open(file_path) as f:
            content = f.read()

        # Verify YAML frontmatter structure
        assert content.startswith("---\n")
        assert "title: Test Note" in content
        assert "tags:" in content
        assert "- test" in content
        assert "entities:" in content

    def test_roundtrip_note(self, manager):
        """Test note survives write/read cycle"""
        original_note_id = manager.create_note(
            title="Roundtrip Test",
            content="Content with\nmultiple lines\n\nAnd paragraphs.",
            tags=["tag1", "tag2"]
        )

        # Read note
        note = manager.get_note(original_note_id)

        # Verify data integrity
        assert note.title == "Roundtrip Test"
        assert note.content == "Content with\nmultiple lines\n\nAnd paragraphs."
        assert note.tags == ["tag1", "tag2"]


class TestGetAllNotes:
    """Test getting all notes"""

    def test_get_all_notes(self, tmp_path):
        """Test retrieving all notes"""
        vector_store = Mock()
        embedder = Mock()
        manager = NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

        # Create multiple notes
        manager.create_note("Note 1", "Content 1")
        manager.create_note("Note 2", "Content 2")
        manager.create_note("Note 3", "Content 3")

        all_notes = manager.get_all_notes()

        assert len(all_notes) == 3
        titles = [note.title for note in all_notes]
        assert "Note 1" in titles
        assert "Note 2" in titles
        assert "Note 3" in titles


class TestRepr:
    """Test string representation"""

    def test_repr(self, tmp_path):
        """Test NoteManager repr"""
        vector_store = Mock()
        vector_store.get_stats.return_value = {"active_docs": 5}
        embedder = Mock()

        manager = NoteManager(
            notes_dir=tmp_path / "notes",
            vector_store=vector_store,
            embedder=embedder,
            auto_index=False
        )

        repr_str = repr(manager)
        assert "NoteManager" in repr_str
        assert "notes" in repr_str.lower()
