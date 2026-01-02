"""
Unit Tests for QueueStorage

Tests the JSON-based queue storage system for manual review.
"""

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.schemas import EmailAction, EmailAnalysis, EmailCategory, EmailMetadata
from src.integrations.storage.queue_storage import QueueStorage, get_queue_storage


@pytest.fixture
def temp_queue_dir():
    """Create temporary queue directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def queue_storage(temp_queue_dir):
    """Create QueueStorage instance with temp directory"""
    return QueueStorage(queue_dir=temp_queue_dir)


@pytest.fixture
def sample_metadata():
    """Create sample EmailMetadata"""
    return EmailMetadata(
        id=12345,
        subject="Test Email Subject",
        from_address="sender@example.com",
        from_name="Test Sender",
        to_addresses=["recipient@example.com"],
        date=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        has_attachments=False,
        folder="INBOX",
        message_id="<test@example.com>",
        in_reply_to=None,
        references=[],
    )


@pytest.fixture
def sample_analysis():
    """Create sample EmailAnalysis"""
    return EmailAnalysis(
        action=EmailAction.ARCHIVE,
        confidence=75,
        category=EmailCategory.NEWSLETTER,
        reasoning="This appears to be a newsletter based on content patterns.",
        destination=None,
    )


class TestQueueStorageInit:
    """Test QueueStorage initialization"""

    def test_init_creates_directory(self, temp_queue_dir):
        """Test that initialization creates queue directory"""
        queue_dir = temp_queue_dir / "queue"
        assert not queue_dir.exists()

        storage = QueueStorage(queue_dir=queue_dir)

        assert queue_dir.exists()
        assert queue_dir.is_dir()

    def test_init_with_existing_directory(self, temp_queue_dir):
        """Test initialization with existing directory"""
        queue_dir = temp_queue_dir / "existing"
        queue_dir.mkdir(parents=True, exist_ok=True)

        storage = QueueStorage(queue_dir=queue_dir)

        assert queue_dir.exists()
        assert queue_dir.is_dir()

    def test_init_default_directory(self):
        """Test initialization with default directory"""
        storage = QueueStorage()

        assert storage.queue_dir == Path("data/queue")


class TestQueueStorageSaveItem:
    """Test QueueStorage.save_item()"""

    def test_save_item_creates_file(self, queue_storage, sample_metadata, sample_analysis):
        """Test that save_item creates a JSON file"""
        content_preview = "This is a preview of the email content."

        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview=content_preview,
            account_id="personal",
        )

        # Check file exists
        file_path = queue_storage.queue_dir / f"{item_id}.json"
        assert file_path.exists()
        assert file_path.is_file()

    def test_save_item_content_structure(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test that saved item has correct structure"""
        content_preview = "Preview content here."

        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview=content_preview,
            account_id="work",
        )

        # Load file
        file_path = queue_storage.queue_dir / f"{item_id}.json"
        with open(file_path, encoding="utf-8") as f:
            item = json.load(f)

        # Verify structure
        assert item["id"] == item_id
        assert item["account_id"] == "work"
        assert "queued_at" in item
        assert item["status"] == "pending"
        assert item["reviewed_at"] is None
        assert item["review_decision"] is None

        # Verify metadata
        assert item["metadata"]["id"] == 12345
        assert item["metadata"]["subject"] == "Test Email Subject"
        assert item["metadata"]["from_address"] == "sender@example.com"
        assert item["metadata"]["from_name"] == "Test Sender"

        # Verify analysis
        assert item["analysis"]["action"] == "archive"
        assert item["analysis"]["confidence"] == 75
        assert item["analysis"]["category"] == "newsletter"
        assert "newsletter" in item["analysis"]["reasoning"].lower()

        # Verify content
        assert item["content"]["preview"] == "Preview content here."

    def test_save_item_truncates_preview(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test that preview is truncated to 200 chars"""
        long_preview = "A" * 300

        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview=long_preview,
        )

        item = queue_storage.get_item(item_id)
        assert len(item["content"]["preview"]) == 200

    def test_save_item_without_account_id(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test saving item without account_id"""
        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Test",
            account_id=None,
        )

        item = queue_storage.get_item(item_id)
        assert item["account_id"] is None

    def test_save_item_returns_unique_ids(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test that each save returns unique ID"""
        ids = set()
        for _ in range(10):
            item_id = queue_storage.save_item(
                metadata=sample_metadata,
                analysis=sample_analysis,
                content_preview="Test",
            )
            ids.add(item_id)

        assert len(ids) == 10


class TestQueueStorageLoadQueue:
    """Test QueueStorage.load_queue()"""

    def test_load_empty_queue(self, queue_storage):
        """Test loading from empty queue"""
        items = queue_storage.load_queue()

        assert items == []

    def test_load_queue_all_items(self, queue_storage, sample_metadata, sample_analysis):
        """Test loading all items"""
        # Save 3 items
        for i in range(3):
            queue_storage.save_item(
                metadata=sample_metadata,
                analysis=sample_analysis,
                content_preview=f"Preview {i}",
            )

        items = queue_storage.load_queue()

        assert len(items) == 3

    def test_load_queue_filter_by_account(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test filtering by account_id"""
        # Save items for different accounts
        queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Personal 1",
            account_id="personal",
        )
        queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Work 1",
            account_id="work",
        )
        queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Personal 2",
            account_id="personal",
        )

        # Load personal items
        items = queue_storage.load_queue(account_id="personal")

        assert len(items) == 2
        assert all(item["account_id"] == "personal" for item in items)

    def test_load_queue_filter_by_status(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test filtering by status"""
        # Save items
        id1 = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Pending",
        )
        id2 = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Approved",
        )

        # Update one to approved
        queue_storage.update_item(id2, {"status": "approved"})

        # Load pending items
        pending = queue_storage.load_queue(status="pending")
        assert len(pending) == 1
        assert pending[0]["id"] == id1

        # Load approved items
        approved = queue_storage.load_queue(status="approved")
        assert len(approved) == 1
        assert approved[0]["id"] == id2

    def test_load_queue_sorted_by_date(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test that items are sorted by queued_at (oldest first)"""
        import time

        ids = []
        for i in range(3):
            item_id = queue_storage.save_item(
                metadata=sample_metadata,
                analysis=sample_analysis,
                content_preview=f"Item {i}",
            )
            ids.append(item_id)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        items = queue_storage.load_queue()

        # Verify oldest first
        assert items[0]["id"] == ids[0]
        assert items[1]["id"] == ids[1]
        assert items[2]["id"] == ids[2]


class TestQueueStorageGetItem:
    """Test QueueStorage.get_item()"""

    def test_get_existing_item(self, queue_storage, sample_metadata, sample_analysis):
        """Test getting an existing item"""
        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        item = queue_storage.get_item(item_id)

        assert item is not None
        assert item["id"] == item_id

    def test_get_nonexistent_item(self, queue_storage):
        """Test getting a non-existent item"""
        item = queue_storage.get_item("nonexistent-id")

        assert item is None


class TestQueueStorageUpdateItem:
    """Test QueueStorage.update_item()"""

    def test_update_item_success(self, queue_storage, sample_metadata, sample_analysis):
        """Test successful item update"""
        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        success = queue_storage.update_item(
            item_id,
            {
                "status": "approved",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "review_decision": "approve",
            },
        )

        assert success is True

        # Verify update
        item = queue_storage.get_item(item_id)
        assert item["status"] == "approved"
        assert item["review_decision"] == "approve"
        assert item["reviewed_at"] is not None

    def test_update_nonexistent_item(self, queue_storage):
        """Test updating non-existent item"""
        success = queue_storage.update_item("nonexistent", {"status": "approved"})

        assert success is False

    def test_update_item_partial(self, queue_storage, sample_metadata, sample_analysis):
        """Test partial update preserves other fields"""
        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Original",
        )

        original = queue_storage.get_item(item_id)
        original_subject = original["metadata"]["subject"]

        # Update only status
        queue_storage.update_item(item_id, {"status": "modified"})

        # Verify other fields preserved
        updated = queue_storage.get_item(item_id)
        assert updated["status"] == "modified"
        assert updated["metadata"]["subject"] == original_subject


class TestQueueStorageRemoveItem:
    """Test QueueStorage.remove_item()"""

    def test_remove_existing_item(self, queue_storage, sample_metadata, sample_analysis):
        """Test removing an existing item"""
        item_id = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        # Verify file exists
        file_path = queue_storage.queue_dir / f"{item_id}.json"
        assert file_path.exists()

        # Remove
        success = queue_storage.remove_item(item_id)

        assert success is True
        assert not file_path.exists()

    def test_remove_nonexistent_item(self, queue_storage):
        """Test removing non-existent item"""
        success = queue_storage.remove_item("nonexistent")

        assert success is False


class TestQueueStorageGetQueueSize:
    """Test QueueStorage.get_queue_size()"""

    def test_get_queue_size_empty(self, queue_storage):
        """Test size of empty queue"""
        size = queue_storage.get_queue_size()

        assert size == 0

    def test_get_queue_size_with_items(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test size with items"""
        for i in range(5):
            queue_storage.save_item(
                metadata=sample_metadata,
                analysis=sample_analysis,
                content_preview=f"Item {i}",
            )

        size = queue_storage.get_queue_size()

        assert size == 5

    def test_get_queue_size_filter_by_account(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test size filtered by account"""
        queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Personal",
            account_id="personal",
        )
        queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Work",
            account_id="work",
        )

        size_personal = queue_storage.get_queue_size(account_id="personal")
        size_work = queue_storage.get_queue_size(account_id="work")

        assert size_personal == 1
        assert size_work == 1


class TestQueueStorageClearQueue:
    """Test QueueStorage.clear_queue()"""

    def test_clear_empty_queue(self, queue_storage):
        """Test clearing empty queue"""
        deleted = queue_storage.clear_queue()

        assert deleted == 0

    def test_clear_all_items(self, queue_storage, sample_metadata, sample_analysis):
        """Test clearing all items"""
        for i in range(5):
            queue_storage.save_item(
                metadata=sample_metadata,
                analysis=sample_analysis,
                content_preview=f"Item {i}",
            )

        deleted = queue_storage.clear_queue()

        assert deleted == 5
        assert queue_storage.get_queue_size() == 0

    def test_clear_queue_by_account(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test clearing items for specific account"""
        for i in range(3):
            queue_storage.save_item(
                metadata=sample_metadata,
                analysis=sample_analysis,
                content_preview="Personal",
                account_id="personal",
            )
        for i in range(2):
            queue_storage.save_item(
                metadata=sample_metadata,
                analysis=sample_analysis,
                content_preview="Work",
                account_id="work",
            )

        deleted = queue_storage.clear_queue(account_id="personal")

        assert deleted == 3
        assert queue_storage.get_queue_size(account_id="personal") == 0
        assert queue_storage.get_queue_size(account_id="work") == 2


class TestQueueStorageGetStats:
    """Test QueueStorage.get_stats()"""

    def test_get_stats_empty(self, queue_storage):
        """Test stats for empty queue"""
        stats = queue_storage.get_stats()

        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["by_account"] == {}
        assert stats["oldest_item"] is None
        assert stats["newest_item"] is None

    def test_get_stats_with_items(
        self, queue_storage, sample_metadata, sample_analysis
    ):
        """Test stats with items"""
        import time

        # Save items with different statuses and accounts
        id1 = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Pending 1",
            account_id="personal",
        )
        time.sleep(0.01)

        id2 = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Pending 2",
            account_id="work",
        )
        time.sleep(0.01)

        id3 = queue_storage.save_item(
            metadata=sample_metadata,
            analysis=sample_analysis,
            content_preview="Approved",
            account_id="personal",
        )

        # Update one status
        queue_storage.update_item(id3, {"status": "approved"})

        stats = queue_storage.get_stats()

        assert stats["total"] == 3
        assert stats["by_status"]["pending"] == 2
        assert stats["by_status"]["approved"] == 1
        assert stats["by_account"]["personal"] == 2
        assert stats["by_account"]["work"] == 1
        assert stats["oldest_item"] is not None
        assert stats["newest_item"] is not None


class TestQueueStorageThreadSafety:
    """Test thread safety of QueueStorage"""

    def test_concurrent_saves(self, queue_storage, sample_metadata, sample_analysis):
        """Test concurrent save operations"""
        import threading

        def save_items():
            for _ in range(10):
                queue_storage.save_item(
                    metadata=sample_metadata,
                    analysis=sample_analysis,
                    content_preview="Concurrent test",
                )

        threads = [threading.Thread(target=save_items) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 50 items total
        assert queue_storage.get_queue_size() == 50


class TestQueueStorageSingleton:
    """Test get_queue_storage singleton"""

    def test_singleton_returns_same_instance(self):
        """Test that get_queue_storage returns same instance"""
        storage1 = get_queue_storage()
        storage2 = get_queue_storage()

        assert storage1 is storage2

    def test_singleton_thread_safe(self):
        """Test singleton is thread-safe"""
        import threading

        instances = []

        def get_instance():
            instances.append(get_queue_storage())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)
