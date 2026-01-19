"""
Unit Tests for Péripétie v2.4 Models and Migration

Tests the new state/resolution model and migration from legacy status.
"""

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.models.peripetie import (
    ErrorType,
    PeripetieError,
    PeripetieResolution,
    PeripetieSnooze,
    PeripetieState,
    PeripetieTimestamps,
    ResolutionType,
    ResolvedBy,
    migrate_legacy_status,
    state_to_tab,
)
from src.core.schemas import EmailAction, EmailAnalysis, EmailCategory, EmailMetadata
from src.integrations.storage.queue_storage import QueueStorage

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_queue_dir():
    """Create temporary queue directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def queue_storage(temp_queue_dir):
    """Create QueueStorage instance with temp directory"""
    return QueueStorage(queue_dir=temp_queue_dir)


@pytest.fixture
def sample_analysis():
    """Create sample EmailAnalysis"""
    return EmailAnalysis(
        action=EmailAction.ARCHIVE,
        confidence=75,
        category=EmailCategory.NEWSLETTER,
        reasoning="Newsletter content detected.",
        destination=None,
    )


def create_metadata_with_unique_id(index: int = 0) -> EmailMetadata:
    """Create EmailMetadata with a unique message_id"""
    import uuid

    return EmailMetadata(
        id=12345 + index,
        subject=f"Test Email {index}",
        from_address="sender@example.com",
        from_name="Test Sender",
        to_addresses=["recipient@example.com"],
        date=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        has_attachments=False,
        folder="INBOX",
        message_id=f"<{uuid.uuid4()}@example.com>",
        in_reply_to=None,
        references=[],
    )


# =============================================================================
# Test PeripetieState Enum
# =============================================================================


class TestPeripetieState:
    """Test PeripetieState enum values"""

    def test_state_values(self):
        """Test all state values exist"""
        assert PeripetieState.QUEUED.value == "queued"
        assert PeripetieState.ANALYZING.value == "analyzing"
        assert PeripetieState.AWAITING_REVIEW.value == "awaiting_review"
        assert PeripetieState.PROCESSED.value == "processed"
        assert PeripetieState.ERROR.value == "error"

    def test_state_is_string_enum(self):
        """Test that state values can be used as strings"""
        assert str(PeripetieState.QUEUED) == "PeripetieState.QUEUED"
        assert PeripetieState.QUEUED.value == "queued"


class TestResolutionType:
    """Test ResolutionType enum values"""

    def test_resolution_values(self):
        """Test all resolution type values exist"""
        assert ResolutionType.AUTO_APPLIED.value == "auto_applied"
        assert ResolutionType.MANUAL_APPROVED.value == "manual_approved"
        assert ResolutionType.MANUAL_MODIFIED.value == "manual_modified"
        assert ResolutionType.MANUAL_REJECTED.value == "manual_rejected"
        assert ResolutionType.MANUAL_SKIPPED.value == "manual_skipped"


class TestErrorType:
    """Test ErrorType enum values"""

    def test_error_values(self):
        """Test all error type values exist"""
        assert ErrorType.ANALYSIS_FAILED.value == "analysis_failed"
        assert ErrorType.ACTION_FAILED.value == "action_failed"
        assert ErrorType.ENRICHMENT_FAILED.value == "enrichment_failed"
        assert ErrorType.TIMEOUT.value == "timeout"


class TestResolvedBy:
    """Test ResolvedBy enum values"""

    def test_resolved_by_values(self):
        """Test all resolved_by values exist"""
        assert ResolvedBy.SYSTEM.value == "system"
        assert ResolvedBy.USER.value == "user"


# =============================================================================
# Test migrate_legacy_status
# =============================================================================


class TestMigrateLegacyStatus:
    """Test legacy status to v2.4 state migration"""

    def test_pending_to_awaiting_review(self):
        """Test pending maps to awaiting_review with no resolution"""
        state, resolution = migrate_legacy_status("pending")
        assert state == PeripetieState.AWAITING_REVIEW
        assert resolution is None

    def test_approved_to_processed_manual_approved(self):
        """Test approved maps to processed with manual_approved"""
        state, resolution = migrate_legacy_status("approved")
        assert state == PeripetieState.PROCESSED
        assert resolution == ResolutionType.MANUAL_APPROVED

    def test_rejected_to_processed_manual_rejected(self):
        """Test rejected maps to processed with manual_rejected"""
        state, resolution = migrate_legacy_status("rejected")
        assert state == PeripetieState.PROCESSED
        assert resolution == ResolutionType.MANUAL_REJECTED

    def test_skipped_to_processed_manual_skipped(self):
        """Test skipped maps to processed with manual_skipped"""
        state, resolution = migrate_legacy_status("skipped")
        assert state == PeripetieState.PROCESSED
        assert resolution == ResolutionType.MANUAL_SKIPPED

    def test_unknown_status_defaults_to_awaiting_review(self):
        """Test unknown status defaults to awaiting_review"""
        state, resolution = migrate_legacy_status("unknown_status")
        assert state == PeripetieState.AWAITING_REVIEW
        assert resolution is None


# =============================================================================
# Test state_to_tab
# =============================================================================


class TestStateToTab:
    """Test state to UI tab mapping"""

    def test_queued_maps_to_in_progress(self):
        """Test queued state maps to in_progress tab"""
        assert state_to_tab(PeripetieState.QUEUED) == "in_progress"

    def test_analyzing_maps_to_in_progress(self):
        """Test analyzing state maps to in_progress tab"""
        assert state_to_tab(PeripetieState.ANALYZING) == "in_progress"

    def test_awaiting_review_maps_to_to_process(self):
        """Test awaiting_review state maps to to_process tab"""
        assert state_to_tab(PeripetieState.AWAITING_REVIEW) == "to_process"

    def test_awaiting_review_with_snooze_maps_to_snoozed(self):
        """Test awaiting_review with snooze maps to snoozed tab"""
        assert state_to_tab(PeripetieState.AWAITING_REVIEW, has_snooze=True) == "snoozed"

    def test_processed_maps_to_history(self):
        """Test processed state maps to history tab"""
        assert state_to_tab(PeripetieState.PROCESSED) == "history"

    def test_error_maps_to_errors(self):
        """Test error state maps to errors tab"""
        assert state_to_tab(PeripetieState.ERROR) == "errors"


# =============================================================================
# Test Pydantic Models
# =============================================================================


class TestPeripetieResolution:
    """Test PeripetieResolution model"""

    def test_create_resolution(self):
        """Test creating a resolution"""
        now = datetime.now(timezone.utc)
        resolution = PeripetieResolution(
            type=ResolutionType.MANUAL_APPROVED,
            action_taken="archive",
            resolved_at=now,
            resolved_by=ResolvedBy.USER,
            confidence_at_resolution=0.85,
            user_modified_action=False,
            original_action=None,
        )
        assert resolution.type == ResolutionType.MANUAL_APPROVED
        assert resolution.action_taken == "archive"
        assert resolution.resolved_at == now
        assert resolution.resolved_by == ResolvedBy.USER
        assert resolution.confidence_at_resolution == 0.85

    def test_resolution_with_modification(self):
        """Test resolution with user modification"""
        resolution = PeripetieResolution(
            type=ResolutionType.MANUAL_MODIFIED,
            action_taken="delete",
            resolved_at=datetime.now(timezone.utc),
            resolved_by=ResolvedBy.USER,
            confidence_at_resolution=0.75,
            user_modified_action=True,
            original_action="archive",
        )
        assert resolution.user_modified_action is True
        assert resolution.original_action == "archive"


class TestPeripetieSnooze:
    """Test PeripetieSnooze model"""

    def test_create_snooze(self):
        """Test creating a snooze"""
        now = datetime.now(timezone.utc)
        snooze = PeripetieSnooze(
            until=now,
            created_at=now,
            reason="Deal with this tomorrow",
            snooze_option="tomorrow",
        )
        assert snooze.until == now
        assert snooze.created_at == now
        assert snooze.reason == "Deal with this tomorrow"
        assert snooze.snooze_option == "tomorrow"


class TestPeripetieError:
    """Test PeripetieError model"""

    def test_create_error(self):
        """Test creating an error"""
        now = datetime.now(timezone.utc)
        error = PeripetieError(
            type=ErrorType.ANALYSIS_FAILED,
            message="AI analysis timed out",
            occurred_at=now,
            retry_count=2,
            retryable=True,
        )
        assert error.type == ErrorType.ANALYSIS_FAILED
        assert error.message == "AI analysis timed out"
        assert error.retry_count == 2
        assert error.retryable is True


class TestPeripetieTimestamps:
    """Test PeripetieTimestamps model"""

    def test_create_timestamps(self):
        """Test creating timestamps"""
        now = datetime.now(timezone.utc)
        timestamps = PeripetieTimestamps(
            queued_at=now,
            analysis_started_at=now,
            analysis_completed_at=now,
            reviewed_at=now,
        )
        assert timestamps.queued_at == now
        assert timestamps.analysis_started_at == now


# =============================================================================
# Test QueueStorage v2.4 Methods
# =============================================================================


class TestQueueStorageSaveItemV24:
    """Test that save_item creates v2.4 structure"""

    def test_save_item_creates_v24_fields(self, queue_storage, sample_analysis):
        """Test that new items have v2.4 fields"""
        metadata = create_metadata_with_unique_id(0)
        item_id = queue_storage.save_item(
            metadata=metadata,
            analysis=sample_analysis,
            content_preview="Test content",
        )

        item = queue_storage.get_item(item_id)

        # Check v2.4 fields exist
        assert "state" in item
        assert "resolution" in item
        assert "snooze" in item
        assert "error" in item
        assert "timestamps" in item

        # Check default values
        assert item["state"] == "awaiting_review"
        assert item["resolution"] is None
        assert item["snooze"] is None
        assert item["error"] is None

        # Check timestamps structure
        assert "queued_at" in item["timestamps"]
        assert "analysis_completed_at" in item["timestamps"]


class TestQueueStorageLoadByState:
    """Test QueueStorage.load_queue_by_state()"""

    def test_load_by_state_awaiting_review(self, queue_storage, sample_analysis):
        """Test loading items by awaiting_review state"""
        # Create items
        for i in range(3):
            metadata = create_metadata_with_unique_id(i)
            queue_storage.save_item(
                metadata=metadata,
                analysis=sample_analysis,
                content_preview=f"Item {i}",
            )

        items = queue_storage.load_queue_by_state(state="awaiting_review")
        assert len(items) == 3

    def test_load_by_tab_to_process(self, queue_storage, sample_analysis):
        """Test loading items by to_process tab"""
        for i in range(2):
            metadata = create_metadata_with_unique_id(i)
            queue_storage.save_item(
                metadata=metadata,
                analysis=sample_analysis,
                content_preview=f"Item {i}",
            )

        items = queue_storage.load_queue_by_state(tab="to_process")
        assert len(items) == 2

    def test_load_by_state_excludes_snoozed(self, queue_storage, sample_analysis):
        """Test that include_snoozed=False excludes snoozed items"""
        # Create normal item
        metadata1 = create_metadata_with_unique_id(0)
        item_id1 = queue_storage.save_item(
            metadata=metadata1,
            analysis=sample_analysis,
            content_preview="Normal item",
        )

        # Create snoozed item
        metadata2 = create_metadata_with_unique_id(1)
        item_id2 = queue_storage.save_item(
            metadata=metadata2,
            analysis=sample_analysis,
            content_preview="Snoozed item",
        )
        now = datetime.now(timezone.utc)
        queue_storage.set_snooze(item_id2, until=now, reason="later")

        # Load without snoozed
        items = queue_storage.load_queue_by_state(
            state="awaiting_review", include_snoozed=False
        )
        assert len(items) == 1
        assert items[0]["id"] == item_id1


class TestQueueStorageSetState:
    """Test QueueStorage.set_state()"""

    def test_set_state_to_processed(self, queue_storage, sample_analysis):
        """Test setting state to processed with resolution"""
        metadata = create_metadata_with_unique_id(0)
        item_id = queue_storage.save_item(
            metadata=metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        now = datetime.now(timezone.utc)
        success = queue_storage.set_state(
            item_id,
            new_state=PeripetieState.PROCESSED,
            resolution={
                "type": "manual_approved",
                "action_taken": "archive",
                "resolved_at": now.isoformat(),
                "resolved_by": "user",
            },
        )

        assert success is True

        item = queue_storage.get_item(item_id)
        assert item["state"] == "processed"
        assert item["resolution"] is not None
        assert item["resolution"]["type"] == "manual_approved"
        assert item["resolution"]["action_taken"] == "archive"

    def test_set_state_to_error(self, queue_storage, sample_analysis):
        """Test setting state to error"""
        metadata = create_metadata_with_unique_id(0)
        item_id = queue_storage.save_item(
            metadata=metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        now = datetime.now(timezone.utc)
        success = queue_storage.set_state(
            item_id,
            new_state=PeripetieState.ERROR,
            error={
                "type": "analysis_failed",
                "message": "AI service unavailable",
                "occurred_at": now.isoformat(),
            },
        )

        assert success is True

        item = queue_storage.get_item(item_id)
        assert item["state"] == "error"
        assert item["error"] is not None
        assert item["error"]["type"] == "analysis_failed"
        assert item["error"]["message"] == "AI service unavailable"


class TestQueueStorageSnooze:
    """Test QueueStorage snooze methods"""

    def test_set_snooze(self, queue_storage, sample_analysis):
        """Test setting snooze on an item"""
        metadata = create_metadata_with_unique_id(0)
        item_id = queue_storage.save_item(
            metadata=metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        now = datetime.now(timezone.utc)
        success = queue_storage.set_snooze(
            item_id,
            until=now,
            reason="Will review tomorrow",
        )

        assert success is True

        item = queue_storage.get_item(item_id)
        assert item["snooze"] is not None
        assert item["snooze"]["reason"] == "Will review tomorrow"

    def test_clear_snooze(self, queue_storage, sample_analysis):
        """Test clearing snooze from an item"""
        metadata = create_metadata_with_unique_id(0)
        item_id = queue_storage.save_item(
            metadata=metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        # Set snooze
        now = datetime.now(timezone.utc)
        queue_storage.set_snooze(item_id, until=now, reason="later")

        # Clear snooze
        success = queue_storage.clear_snooze(item_id)

        assert success is True

        item = queue_storage.get_item(item_id)
        assert item["snooze"] is None

    def test_get_snoozed_items(self, queue_storage, sample_analysis):
        """Test getting all snoozed items"""
        # Create normal item
        metadata1 = create_metadata_with_unique_id(0)
        queue_storage.save_item(
            metadata=metadata1,
            analysis=sample_analysis,
            content_preview="Normal",
        )

        # Create snoozed item
        metadata2 = create_metadata_with_unique_id(1)
        item_id2 = queue_storage.save_item(
            metadata=metadata2,
            analysis=sample_analysis,
            content_preview="Snoozed",
        )
        now = datetime.now(timezone.utc)
        queue_storage.set_snooze(item_id2, until=now, reason="later")

        snoozed = queue_storage.get_snoozed_items()
        assert len(snoozed) == 1
        assert snoozed[0]["id"] == item_id2


class TestQueueStorageStatsV24:
    """Test QueueStorage.get_stats() v2.4 fields"""

    def test_stats_include_v24_fields(self, queue_storage, sample_analysis):
        """Test that stats include v2.4 fields"""
        # Create items
        for i in range(3):
            metadata = create_metadata_with_unique_id(i)
            queue_storage.save_item(
                metadata=metadata,
                analysis=sample_analysis,
                content_preview=f"Item {i}",
            )

        stats = queue_storage.get_stats()

        # Check v2.4 fields exist
        assert "by_state" in stats
        assert "by_resolution" in stats
        assert "by_tab" in stats
        assert "snoozed_count" in stats
        assert "error_count" in stats

        # Check values
        assert stats["by_state"]["awaiting_review"] == 3
        assert stats["by_tab"]["to_process"] == 3
        assert stats["snoozed_count"] == 0
        assert stats["error_count"] == 0


class TestQueueStorageMigrateItem:
    """Test QueueStorage.migrate_item_to_v24()"""

    def test_migrate_legacy_item(self, queue_storage, sample_analysis, temp_queue_dir):
        """Test migrating a legacy item to v2.4 format"""
        # Create a legacy item directly (without v2.4 fields)
        import uuid

        item_id = str(uuid.uuid4())
        legacy_item = {
            "id": item_id,
            "account_id": "test",
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "reviewed_at": None,
            "review_decision": None,
            "metadata": {
                "id": 12345,
                "subject": "Test",
                "from_address": "test@example.com",
            },
            "analysis": {
                "action": "archive",
                "confidence": 75,
            },
            "content": {"preview": "Test content"},
        }

        # Save legacy item directly to disk
        file_path = temp_queue_dir / f"{item_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(legacy_item, f)

        # Migrate
        success = queue_storage.migrate_item_to_v24(item_id)
        assert success is True

        # Verify migrated
        item = queue_storage.get_item(item_id)
        assert item["state"] == "awaiting_review"
        assert item["resolution"] is None
        assert "timestamps" in item

    def test_migrate_approved_item(self, queue_storage, sample_analysis, temp_queue_dir):
        """Test migrating an approved legacy item"""
        import uuid

        item_id = str(uuid.uuid4())
        legacy_item = {
            "id": item_id,
            "account_id": "test",
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "status": "approved",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_decision": "approve",
            "metadata": {
                "id": 12345,
                "subject": "Test",
                "from_address": "test@example.com",
            },
            "analysis": {
                "action": "archive",
                "confidence": 85,
            },
            "content": {"preview": "Test content"},
        }

        file_path = temp_queue_dir / f"{item_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(legacy_item, f)

        success = queue_storage.migrate_item_to_v24(item_id)
        assert success is True

        item = queue_storage.get_item(item_id)
        assert item["state"] == "processed"
        assert item["resolution"] is not None
        assert item["resolution"]["type"] == "manual_approved"

    def test_skip_already_migrated(self, queue_storage, sample_analysis):
        """Test that already migrated items are skipped"""
        metadata = create_metadata_with_unique_id(0)
        item_id = queue_storage.save_item(
            metadata=metadata,
            analysis=sample_analysis,
            content_preview="Test",
        )

        # Item is already v2.4, migrate should return False (no migration needed)
        success = queue_storage.migrate_item_to_v24(item_id)
        assert success is False
