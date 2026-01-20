"""
Tests for FilageService — Memory Cycles v2
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.passepartout.filage_service import (
    Filage,
    FilageLecture,
    FilageService,
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
def filage_service(mock_note_manager, metadata_store, scheduler):
    """Create a FilageService"""
    return FilageService(
        note_manager=mock_note_manager,
        metadata_store=metadata_store,
        scheduler=scheduler,
    )


class TestFilageLecture:
    """Tests for FilageLecture dataclass"""

    def test_creation(self):
        """Test creating a FilageLecture"""
        lecture = FilageLecture(
            note_id="test-001",
            note_title="Test Note",
            note_type=NoteType.PERSONNE,
            priority=1,
            reason="Questions en attente",
            quality_score=75,
            questions_pending=True,
            questions_count=3,
        )

        assert lecture.note_id == "test-001"
        assert lecture.priority == 1
        assert lecture.questions_pending is True


class TestFilage:
    """Tests for Filage dataclass"""

    def test_creation(self):
        """Test creating a Filage"""
        filage = Filage(
            date="2026-01-20",
            generated_at=datetime.now(timezone.utc).isoformat(),
            lectures=[],
            total_lectures=0,
            events_today=0,
            notes_with_questions=0,
        )

        assert filage.date == "2026-01-20"
        assert filage.total_lectures == 0


class TestFilageService:
    """Tests for FilageService"""

    @pytest.mark.asyncio
    async def test_generate_empty_filage(self, filage_service, mock_note_manager):
        """Test generating filage when no notes are due"""
        mock_note_manager.get_note.return_value = None

        filage = await filage_service.generate_filage(max_lectures=20)

        assert filage.total_lectures == 0
        assert filage.lectures == []

    @pytest.mark.asyncio
    async def test_generate_filage_with_questions(
        self, filage_service, metadata_store, mock_note_manager
    ):
        """Test filage prioritizes notes with pending questions"""
        # Create note with questions
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="questions-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
            questions_pending=True,
            questions_count=3,
            quality_score=60,
        )
        metadata_store.save(metadata)

        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "questions-note"
        mock_note.title = "Note with Questions"
        mock_note_manager.get_note.return_value = mock_note

        filage = await filage_service.generate_filage(max_lectures=20)

        assert filage.total_lectures == 1
        assert filage.notes_with_questions == 1
        assert filage.lectures[0].note_id == "questions-note"
        assert filage.lectures[0].reason == "Questions en attente"

    @pytest.mark.asyncio
    async def test_generate_filage_with_due_lectures(
        self, filage_service, metadata_store, mock_note_manager
    ):
        """Test filage includes notes due for Lecture"""
        # Create note due for lecture
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="due-lecture",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
            lecture_next=now - timedelta(hours=1),  # Due 1 hour ago
            quality_score=70,
        )
        metadata_store.save(metadata)

        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "due-lecture"
        mock_note.title = "Due Lecture Note"
        mock_note_manager.get_note.return_value = mock_note

        filage = await filage_service.generate_filage(max_lectures=20)

        assert filage.total_lectures >= 1

    @pytest.mark.asyncio
    async def test_generate_filage_max_limit(
        self, filage_service, metadata_store, mock_note_manager
    ):
        """Test filage respects max_lectures limit for questions notes"""
        now = datetime.now(timezone.utc)

        # Create 10 notes with questions (priority 1 is limited to 5)
        for i in range(10):
            metadata = NoteMetadata(
                note_id=f"note-{i}",
                note_type=NoteType.PERSONNE,
                created_at=now,
                updated_at=now,
                questions_pending=True,
                questions_count=1,
            )
            metadata_store.save(metadata)

        # Setup mock note
        mock_note = MagicMock()
        mock_note.title = "Test Note"
        mock_note_manager.get_note.side_effect = lambda note_id: (
            setattr(mock_note, "note_id", note_id) or mock_note
        )

        filage = await filage_service.generate_filage(max_lectures=20)

        # Questions notes are limited to 5 in priority 1
        assert filage.total_lectures == 5
        assert len(filage.lectures) == 5
        assert filage.notes_with_questions == 5

    def test_is_filage_hour(self, filage_service):
        """Test filage hour detection"""
        # Test at different hours (UTC+1 assumed for Paris)
        # 5 AM UTC = 6 AM Paris
        filage_time = datetime(2026, 1, 20, 5, 0, 0, tzinfo=timezone.utc)
        assert filage_service.is_filage_hour(filage_time) is True

        # 10 AM UTC = 11 AM Paris
        non_filage_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
        assert filage_service.is_filage_hour(non_filage_time) is False

    @pytest.mark.asyncio
    async def test_get_lecture_for_note(
        self, filage_service, metadata_store, mock_note_manager
    ):
        """Test getting lecture info for a specific note"""
        now = datetime.now(timezone.utc)
        metadata = NoteMetadata(
            note_id="specific-note",
            note_type=NoteType.PERSONNE,
            created_at=now,
            updated_at=now,
            questions_pending=True,
            questions_count=2,
            quality_score=80,
        )
        metadata_store.save(metadata)

        mock_note = MagicMock()
        mock_note.note_id = "specific-note"
        mock_note.title = "Specific Note"
        mock_note_manager.get_note.return_value = mock_note

        lecture = await filage_service.get_lecture_for_note("specific-note")

        assert lecture is not None
        assert lecture.note_id == "specific-note"
        assert lecture.questions_pending is True

    @pytest.mark.asyncio
    async def test_get_lecture_for_nonexistent_note(self, filage_service):
        """Test getting lecture for nonexistent note"""
        lecture = await filage_service.get_lecture_for_note("nonexistent")

        assert lecture is None
