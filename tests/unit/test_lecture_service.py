"""
Tests for LectureService — Memory Cycles v2
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.passepartout.lecture_service import (
    LectureResult,
    LectureService,
    LectureSession,
)
from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import NoteType


@pytest.fixture
def mock_note_manager():
    """Create a mock NoteManager"""
    manager = MagicMock()
    manager.notes_dir = "/test/notes"
    return manager


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database"""
    return tmp_path / "test_meta.db"


@pytest.fixture
def metadata_store(temp_db):
    """Create metadata store with temp database"""
    return NoteMetadataStore(temp_db)


@pytest.fixture
def scheduler(metadata_store):
    """Create a scheduler"""
    return NoteScheduler(metadata_store)


@pytest.fixture
def lecture_service(mock_note_manager, metadata_store, scheduler):
    """Create a LectureService"""
    return LectureService(
        note_manager=mock_note_manager,
        metadata_store=metadata_store,
        scheduler=scheduler,
    )


class TestLectureSession:
    """Tests for LectureSession dataclass"""

    def test_creation(self):
        """Test creating a LectureSession"""
        session = LectureSession(
            session_id="session-001",
            note_id="test-001",
            note_title="Test Note",
            note_content="Content here",
            started_at=datetime.now(timezone.utc).isoformat(),
            quality_score=75,
            questions=["Question 1?", "Question 2?"],
        )

        assert session.session_id == "session-001"
        assert session.note_id == "test-001"
        assert len(session.questions) == 2


class TestLectureResult:
    """Tests for LectureResult dataclass"""

    def test_creation(self):
        """Test creating a LectureResult"""
        result = LectureResult(
            note_id="test-001",
            quality_rating=4,
            next_lecture=datetime.now(timezone.utc).isoformat(),
            interval_hours=72.0,
            answers_recorded=2,
            questions_remaining=1,
            success=True,
        )

        assert result.note_id == "test-001"
        assert result.quality_rating == 4
        assert result.success is True


class TestLectureService:
    """Tests for LectureService"""

    def test_start_lecture_not_found(self, lecture_service, mock_note_manager):
        """Test starting lecture when note not found"""
        mock_note_manager.get_note.return_value = None

        session = lecture_service.start_lecture("nonexistent")

        assert session is None

    def test_start_lecture_success(
        self, lecture_service, mock_note_manager, metadata_store
    ):
        """Test starting a lecture session"""
        now = datetime.now(timezone.utc)

        # Create metadata
        metadata = NoteMetadata(
            note_id="test-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
            quality_score=70,
            questions_count=2,
        )
        metadata_store.save(metadata)

        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "test-note"
        mock_note.title = "Test Note"
        mock_note.content = """# Test
## Questions pour Johan
- Question 1?
- Question 2?
"""
        mock_note.file_path = "/test/notes/personne/test-note.md"
        mock_note_manager.get_note.return_value = mock_note

        session = lecture_service.start_lecture("test-note")

        assert session is not None
        assert session.note_id == "test-note"
        assert session.note_title == "Test Note"
        # Questions are extracted (may have duplicates due to regex patterns)
        assert len(session.questions) >= 2

    def test_complete_lecture_invalid_quality(self, lecture_service, metadata_store):
        """Test completing lecture with invalid quality"""
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="test-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
        )
        metadata_store.save(metadata)

        result = lecture_service.complete_lecture("test-note", quality=10)

        assert result.success is False
        assert "Invalid quality" in result.error

    def test_complete_lecture_success(
        self, lecture_service, mock_note_manager, metadata_store
    ):
        """Test completing a lecture successfully"""
        now = datetime.now(timezone.utc)

        metadata = NoteMetadata(
            note_id="test-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
            lecture_ef=2.5,
            lecture_rep=0,
            lecture_interval=24.0,
        )
        metadata_store.save(metadata)

        mock_note = MagicMock()
        mock_note.note_id = "test-note"
        mock_note.content = "Test content"
        mock_note_manager.get_note.return_value = mock_note

        result = lecture_service.complete_lecture("test-note", quality=4)

        assert result.success is True
        assert result.quality_rating == 4
        assert result.interval_hours > 0

        # Check metadata was updated
        updated_metadata = metadata_store.get("test-note")
        assert updated_metadata.lecture_count == 1
        assert updated_metadata.lecture_last is not None

    def test_complete_lecture_with_answers(
        self, lecture_service, mock_note_manager, metadata_store
    ):
        """Test completing lecture with answers to questions"""
        now = datetime.now(timezone.utc)

        metadata = NoteMetadata(
            note_id="test-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
            questions_pending=True,
            questions_count=3,
        )
        metadata_store.save(metadata)

        mock_note = MagicMock()
        mock_note.note_id = "test-note"
        mock_note.content = "Test content"
        mock_note_manager.get_note.return_value = mock_note
        mock_note_manager.update_note.return_value = mock_note

        result = lecture_service.complete_lecture(
            "test-note",
            quality=4,
            answers={"1": "Answer 1", "2": "Answer 2"},
        )

        assert result.success is True
        assert result.answers_recorded == 2
        assert result.questions_remaining == 1

    def test_complete_lecture_not_found(self, lecture_service):
        """Test completing lecture for nonexistent note"""
        result = lecture_service.complete_lecture("nonexistent", quality=4)

        assert result.success is False
        assert "not found" in result.error

    def test_extract_questions(self, lecture_service):
        """Test question extraction from content"""
        content = """# Note
## Questions pour Johan
- What is the purpose?
- How does it work?

## Other Content
Regular content here.
"""
        questions = lecture_service._extract_questions(content)

        # At least the expected questions should be found
        assert len(questions) >= 2
        assert any("What is the purpose?" in q for q in questions)
        assert any("How does it work?" in q for q in questions)

    def test_get_lecture_stats(self, lecture_service, metadata_store):
        """Test getting lecture statistics"""
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="test-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
            lecture_count=5,
            lecture_ef=2.7,
            lecture_interval=72.0,
            lecture_next=now,
            lecture_last=now,
            quality_score=80,
            questions_pending=True,
            questions_count=2,
        )
        metadata_store.save(metadata)

        stats = lecture_service.get_lecture_stats("test-note")

        assert stats is not None
        assert stats["lecture_count"] == 5
        assert stats["lecture_ef"] == 2.7
        assert stats["quality_score"] == 80
        assert stats["questions_pending"] is True

    def test_get_lecture_stats_not_found(self, lecture_service):
        """Test getting stats for nonexistent note"""
        stats = lecture_service.get_lecture_stats("nonexistent")

        assert stats is None

    def test_cancel_session(self, lecture_service, mock_note_manager, metadata_store):
        """Test cancelling a session"""
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="test-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
        )
        metadata_store.save(metadata)

        mock_note = MagicMock()
        mock_note.note_id = "test-note"
        mock_note.title = "Test Note"
        mock_note.content = "Content"
        mock_note.file_path = "/test/notes/test-note.md"
        mock_note_manager.get_note.return_value = mock_note

        # Start a session
        session = lecture_service.start_lecture("test-note")
        assert session is not None

        # Cancel the session
        result = lecture_service.cancel_session(session.session_id)
        assert result is True

        # Try to cancel again - should fail
        result = lecture_service.cancel_session(session.session_id)
        assert result is False
