"""
Tests for FolderPreferencesStore

Tests the folder preference learning system including:
- Recording archive actions
- Getting suggestions based on patterns
- Time decay scoring
- Recent and popular folders tracking
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.integrations.email.folder_preferences import (
    FolderPreference,
    FolderPreferencesStore,
    FolderSuggestion,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def store(temp_db: str) -> FolderPreferencesStore:
    """Create a test store instance."""
    return FolderPreferencesStore(db_path=temp_db)


class TestFolderPreferencesStore:
    """Test FolderPreferencesStore functionality."""

    def test_init_creates_tables(self, store: FolderPreferencesStore) -> None:
        """Test that initialization creates required tables."""
        with store._get_cursor() as cursor:
            # Check folder_preferences table
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='folder_preferences'
            """)
            assert cursor.fetchone() is not None

            # Check recent_folders table
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='recent_folders'
            """)
            assert cursor.fetchone() is not None

    def test_record_archive_sender(self, store: FolderPreferencesStore) -> None:
        """Test recording archive with sender email."""
        store.record_archive(
            folder="Archive/Work",
            sender_email="john@example.com",
            subject="Test subject"
        )

        with store._get_cursor() as cursor:
            cursor.execute("""
                SELECT pattern_type, pattern, folder, count
                FROM folder_preferences
                WHERE pattern_type = 'sender'
            """)
            row = cursor.fetchone()
            assert row is not None
            assert row["pattern"] == "john@example.com"
            assert row["folder"] == "Archive/Work"
            assert row["count"] == 1

    def test_record_archive_domain(self, store: FolderPreferencesStore) -> None:
        """Test that domain is extracted from sender email."""
        store.record_archive(
            folder="Archive/Work",
            sender_email="john@company.com"
        )

        with store._get_cursor() as cursor:
            cursor.execute("""
                SELECT pattern, folder FROM folder_preferences
                WHERE pattern_type = 'domain'
            """)
            row = cursor.fetchone()
            assert row is not None
            assert row["pattern"] == "company.com"
            assert row["folder"] == "Archive/Work"

    def test_record_archive_keywords(self, store: FolderPreferencesStore) -> None:
        """Test keyword extraction from subject."""
        store.record_archive(
            folder="Archive/Projects",
            subject="Invoice #12345 from Client ABC"
        )

        with store._get_cursor() as cursor:
            cursor.execute("""
                SELECT pattern FROM folder_preferences
                WHERE pattern_type = 'keyword'
            """)
            keywords = {row["pattern"] for row in cursor.fetchall()}
            assert "invoice" in keywords
            assert "client" in keywords

    def test_record_archive_increments_count(self, store: FolderPreferencesStore) -> None:
        """Test that repeated archives increment count."""
        store.record_archive(folder="Archive", sender_email="john@example.com")
        store.record_archive(folder="Archive", sender_email="john@example.com")
        store.record_archive(folder="Archive", sender_email="john@example.com")

        with store._get_cursor() as cursor:
            cursor.execute("""
                SELECT count FROM folder_preferences
                WHERE pattern_type = 'sender' AND pattern = 'john@example.com'
            """)
            row = cursor.fetchone()
            assert row is not None
            assert row["count"] == 3

    def test_get_suggestions_by_sender(self, store: FolderPreferencesStore) -> None:
        """Test getting suggestions based on sender."""
        # Record some archives
        store.record_archive(folder="Archive/Work", sender_email="john@company.com")
        store.record_archive(folder="Archive/Work", sender_email="john@company.com")
        store.record_archive(folder="Archive/Personal", sender_email="jane@other.com")

        suggestions = store.get_suggestions(sender_email="john@company.com")

        assert len(suggestions) >= 1
        assert suggestions[0].folder == "Archive/Work"
        assert suggestions[0].confidence > 0

    def test_get_suggestions_by_domain(self, store: FolderPreferencesStore) -> None:
        """Test getting suggestions based on domain."""
        # Record archives from different senders at same domain
        store.record_archive(folder="Archive/Company", sender_email="alice@bigcorp.com")
        store.record_archive(folder="Archive/Company", sender_email="bob@bigcorp.com")
        store.record_archive(folder="Archive/Company", sender_email="carol@bigcorp.com")

        # New sender from same domain should get suggestion
        suggestions = store.get_suggestions(sender_email="dave@bigcorp.com")

        assert len(suggestions) >= 1
        assert suggestions[0].folder == "Archive/Company"

    def test_get_suggestions_by_keywords(self, store: FolderPreferencesStore) -> None:
        """Test getting suggestions based on subject keywords."""
        # Record archives with similar keywords
        store.record_archive(folder="Archive/Invoices", subject="Invoice from Vendor A")
        store.record_archive(folder="Archive/Invoices", subject="Invoice from Vendor B")
        store.record_archive(folder="Archive/Invoices", subject="Invoice for Services")

        suggestions = store.get_suggestions(subject="New Invoice #123")

        assert len(suggestions) >= 1
        assert suggestions[0].folder == "Archive/Invoices"

    def test_get_suggestions_confidence_normalization(
        self, store: FolderPreferencesStore
    ) -> None:
        """Test that confidence is normalized 0-1."""
        store.record_archive(folder="Archive", sender_email="test@example.com")

        suggestions = store.get_suggestions(sender_email="test@example.com")

        assert len(suggestions) >= 1
        assert 0 <= suggestions[0].confidence <= 1

    def test_get_suggestions_limit(self, store: FolderPreferencesStore) -> None:
        """Test suggestion limit parameter."""
        # Create many different folder preferences
        for i in range(10):
            store.record_archive(
                folder=f"Archive/Folder{i}",
                sender_email=f"user{i}@example.com"
            )

        suggestions = store.get_suggestions(subject="test", limit=3)
        # May return fewer if not enough match the query
        assert len(suggestions) <= 3

    def test_get_suggestions_empty(self, store: FolderPreferencesStore) -> None:
        """Test suggestions return empty list when no matches."""
        suggestions = store.get_suggestions(
            sender_email="unknown@nowhere.com",
            subject="Random subject"
        )
        assert suggestions == []

    def test_get_recent_folders(self, store: FolderPreferencesStore) -> None:
        """Test getting recently used folders."""
        store.record_archive(folder="Archive/A", sender_email="a@example.com")
        store.record_archive(folder="Archive/B", sender_email="b@example.com")
        store.record_archive(folder="Archive/C", sender_email="c@example.com")

        recent = store.get_recent_folders(limit=5)

        assert len(recent) == 3
        # Most recent should be first
        assert recent[0] == "Archive/C"

    def test_get_popular_folders(self, store: FolderPreferencesStore) -> None:
        """Test getting popular folders by usage."""
        # Create different usage counts
        store.record_archive(folder="Archive/Rare", sender_email="a@example.com")
        for _ in range(5):
            store.record_archive(folder="Archive/Popular", sender_email="b@example.com")
        for _ in range(3):
            store.record_archive(folder="Archive/Medium", sender_email="c@example.com")

        popular = store.get_popular_folders(limit=5)

        assert len(popular) == 3
        # Most popular should be first
        assert popular[0] == "Archive/Popular"
        assert popular[1] == "Archive/Medium"
        assert popular[2] == "Archive/Rare"

    def test_extract_keywords_filters_stopwords(
        self, store: FolderPreferencesStore
    ) -> None:
        """Test that common words are filtered from keywords."""
        keywords = store._extract_keywords(
            "Re: The invoice for the project is attached"
        )

        # Stopwords should be filtered
        assert "the" not in keywords
        assert "for" not in keywords
        assert "is" not in keywords
        assert "re" not in keywords

        # Meaningful words should remain
        assert "invoice" in keywords
        assert "project" in keywords

    def test_extract_keywords_max_5(self, store: FolderPreferencesStore) -> None:
        """Test keyword extraction returns max 5 keywords."""
        keywords = store._extract_keywords(
            "Quarterly financial report analysis summary document review meeting notes"
        )
        assert len(keywords) <= 5

    def test_extract_keywords_min_length(self, store: FolderPreferencesStore) -> None:
        """Test keywords have minimum length of 3."""
        keywords = store._extract_keywords("A to do it by me")
        # All short words should be filtered
        assert all(len(k) >= 3 for k in keywords)

    def test_clear_old_preferences(self, store: FolderPreferencesStore) -> None:
        """Test clearing old preferences."""
        # Record an archive (creates both sender and domain patterns)
        store.record_archive(folder="Archive", sender_email="test@example.com")

        # Count how many records were created
        with store._get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM folder_preferences")
            initial_count = cursor.fetchone()[0]
            assert initial_count >= 1  # At least sender pattern

            # Manually set last_used to old date
            cursor.execute("""
                UPDATE folder_preferences
                SET last_used = datetime('now', '-200 days')
            """)

        # Clear old entries
        deleted = store.clear_old_preferences(days=180)

        # Should have deleted all records
        assert deleted == initial_count

        # Verify all are gone
        with store._get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM folder_preferences")
            count = cursor.fetchone()[0]
            assert count == 0


class TestFolderSuggestion:
    """Test FolderSuggestion dataclass."""

    def test_folder_suggestion_creation(self) -> None:
        """Test creating a FolderSuggestion."""
        suggestion = FolderSuggestion(
            folder="Archive/Test",
            confidence=0.85,
            reason="Sender: test@example.com"
        )

        assert suggestion.folder == "Archive/Test"
        assert suggestion.confidence == 0.85
        assert suggestion.reason == "Sender: test@example.com"


class TestFolderPreference:
    """Test FolderPreference dataclass."""

    def test_folder_preference_creation(self) -> None:
        """Test creating a FolderPreference."""
        pref = FolderPreference(
            pattern_type="sender",
            pattern="test@example.com",
            folder="Archive",
            count=5,
            last_used=datetime.now(),
            score=15.0
        )

        assert pref.pattern_type == "sender"
        assert pref.pattern == "test@example.com"
        assert pref.folder == "Archive"
        assert pref.count == 5
        assert pref.score == 15.0
