"""
Unit Tests for ErrorStore

Tests all ErrorStore functionality including:
- Database initialization
- Error saving and retrieval
- Filtering and statistics
- Thread safety
- Context manager usage
"""

import pytest
import sqlite3
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

from src.core.error_store import ErrorStore, get_error_store, reset_error_store
from src.core.error_manager import (
    SystemError,
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def error_store(temp_db):
    """Create ErrorStore instance with temp database"""
    store = ErrorStore(db_path=temp_db)
    yield store


@pytest.fixture
def sample_error():
    """Create a sample SystemError for testing"""
    return SystemError(
        id="test-error-001",
        timestamp=datetime.now(),
        category=ErrorCategory.IMAP,
        severity=ErrorSeverity.MEDIUM,
        exception_type="ConnectionError",
        exception_message="Failed to connect to IMAP server",
        traceback="Traceback...",
        component="imap_client",
        operation="connect",
        context={"host": "imap.example.com", "port": 993},
        recovery_strategy=RecoveryStrategy.RETRY,
        recovery_attempted=False,
        recovery_successful=None,
        recovery_attempts=0,
        max_recovery_attempts=3,
        resolved=False,
        resolved_at=None,
        notes=""
    )


class TestErrorStoreInit:
    """Test ErrorStore initialization"""

    def test_init_creates_database(self):
        """Test that initialization creates database file"""
        import tempfile

        # Create temp path without creating the file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=True) as f:
            temp_path = Path(f.name)

        # Now file should not exist
        assert not temp_path.exists()

        # Initialize ErrorStore
        store = ErrorStore(db_path=temp_path)
        assert temp_path.exists()

        # Cleanup
        temp_path.unlink()

    def test_init_creates_schema(self, temp_db):
        """Test that initialization creates proper schema"""
        store = ErrorStore(db_path=temp_db)
        
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='errors'")
        assert cursor.fetchone() is not None
        
        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        assert 'idx_errors_timestamp' in indexes
        assert 'idx_errors_category' in indexes
        assert 'idx_errors_severity' in indexes
        assert 'idx_errors_resolved' in indexes
        
        conn.close()

    def test_init_default_path(self):
        """Test initialization with default path from config"""
        reset_error_store()
        # This will use config default
        store = get_error_store()
        assert store.db_path.exists()


class TestErrorStoreSave:
    """Test error saving functionality"""

    def test_save_error_basic(self, error_store, sample_error):
        """Test saving a basic error"""
        result = error_store.save_error(sample_error)
        assert result is True

    def test_save_error_persists(self, error_store, sample_error):
        """Test that saved error can be retrieved"""
        error_store.save_error(sample_error)
        retrieved = error_store.get_error(sample_error.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_error.id
        assert retrieved.exception_type == sample_error.exception_type
        assert retrieved.category == sample_error.category
        assert retrieved.severity == sample_error.severity

    def test_save_error_with_special_chars(self, error_store):
        """Test saving error with special characters in message"""
        error = SystemError(
            id="test-special-001",
            timestamp=datetime.now(),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.LOW,
            exception_type="ValueError",
            exception_message="Invalid folder: _PKM/À supprimer with émojis 🎉",
            traceback="Traceback...",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.SKIP,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )
        
        assert error_store.save_error(error) is True
        retrieved = error_store.get_error("test-special-001")
        assert retrieved.exception_message == error.exception_message

    def test_save_error_replace(self, error_store, sample_error):
        """Test that saving same ID replaces existing error"""
        error_store.save_error(sample_error)
        
        # Modify and save again
        sample_error.resolved = True
        sample_error.resolved_at = datetime.now()
        error_store.save_error(sample_error)
        
        retrieved = error_store.get_error(sample_error.id)
        assert retrieved.resolved is True

    def test_update_error(self, error_store, sample_error):
        """Test update_error method"""
        error_store.save_error(sample_error)
        
        sample_error.recovery_attempted = True
        sample_error.recovery_successful = True
        result = error_store.update_error(sample_error)
        
        assert result is True
        retrieved = error_store.get_error(sample_error.id)
        assert retrieved.recovery_attempted is True
        assert retrieved.recovery_successful is True


class TestErrorStoreRetrieval:
    """Test error retrieval functionality"""

    def test_get_error_not_found(self, error_store):
        """Test retrieving non-existent error"""
        result = error_store.get_error("non-existent")
        assert result is None

    def test_get_recent_errors_empty(self, error_store):
        """Test get_recent_errors on empty database"""
        results = error_store.get_recent_errors()
        assert results == []

    def test_get_recent_errors_limit(self, error_store):
        """Test get_recent_errors respects limit"""
        # Create 20 errors
        for i in range(20):
            error = SystemError(
                id=f"test-{i:03d}",
                timestamp=datetime.now(),
                category=ErrorCategory.IMAP,
                severity=ErrorSeverity.LOW,
                exception_type="TestError",
                exception_message=f"Error {i}",
                traceback="",
                component="test",
                operation="test",
                context={},
                recovery_strategy=RecoveryStrategy.SKIP,
                recovery_attempted=False,
                recovery_successful=None,
                recovery_attempts=0,
                max_recovery_attempts=3,
                resolved=False,
                resolved_at=None,
                notes=""
            )
            error_store.save_error(error)
        
        results = error_store.get_recent_errors(limit=10)
        assert len(results) == 10

    def test_get_recent_errors_order(self, error_store):
        """Test that recent errors are ordered newest first"""
        # Create errors with different timestamps
        for i in range(3):
            error = SystemError(
                id=f"test-{i:03d}",
                timestamp=datetime.now() - timedelta(hours=i),
                category=ErrorCategory.IMAP,
                severity=ErrorSeverity.LOW,
                exception_type="TestError",
                exception_message=f"Error {i}",
                traceback="",
                component="test",
                operation="test",
                context={},
                recovery_strategy=RecoveryStrategy.SKIP,
                recovery_attempted=False,
                recovery_successful=None,
                recovery_attempts=0,
                max_recovery_attempts=3,
                resolved=False,
                resolved_at=None,
                notes=""
            )
            error_store.save_error(error)
        
        results = error_store.get_recent_errors()
        # Most recent should be first
        assert results[0].id == "test-000"
        assert results[-1].id == "test-002"

    def test_get_recent_errors_filter_category(self, error_store):
        """Test filtering by category"""
        # Create errors with different categories
        for cat in [ErrorCategory.IMAP, ErrorCategory.AI, ErrorCategory.NETWORK]:
            error = SystemError(
                id=f"test-{cat.value}",
                timestamp=datetime.now(),
                category=cat,
                severity=ErrorSeverity.LOW,
                exception_type="TestError",
                exception_message="Test",
                traceback="",
                component="test",
                operation="test",
                context={},
                recovery_strategy=RecoveryStrategy.SKIP,
                recovery_attempted=False,
                recovery_successful=None,
                recovery_attempts=0,
                max_recovery_attempts=3,
                resolved=False,
                resolved_at=None,
                notes=""
            )
            error_store.save_error(error)
        
        results = error_store.get_recent_errors(category=ErrorCategory.AI)
        assert len(results) == 1
        assert results[0].category == ErrorCategory.AI

    def test_get_recent_errors_filter_severity(self, error_store):
        """Test filtering by severity"""
        for sev in [ErrorSeverity.LOW, ErrorSeverity.CRITICAL]:
            error = SystemError(
                id=f"test-{sev.value}",
                timestamp=datetime.now(),
                category=ErrorCategory.IMAP,
                severity=sev,
                exception_type="TestError",
                exception_message="Test",
                traceback="",
                component="test",
                operation="test",
                context={},
                recovery_strategy=RecoveryStrategy.SKIP,
                recovery_attempted=False,
                recovery_successful=None,
                recovery_attempts=0,
                max_recovery_attempts=3,
                resolved=False,
                resolved_at=None,
                notes=""
            )
            error_store.save_error(error)
        
        results = error_store.get_recent_errors(severity=ErrorSeverity.CRITICAL)
        assert len(results) == 1
        assert results[0].severity == ErrorSeverity.CRITICAL

    def test_get_recent_errors_filter_resolved(self, error_store):
        """Test filtering by resolved status"""
        for resolved in [True, False]:
            error = SystemError(
                id=f"test-{resolved}",
                timestamp=datetime.now(),
                category=ErrorCategory.IMAP,
                severity=ErrorSeverity.LOW,
                exception_type="TestError",
                exception_message="Test",
                traceback="",
                component="test",
                operation="test",
                context={},
                recovery_strategy=RecoveryStrategy.SKIP,
                recovery_attempted=False,
                recovery_successful=None,
                recovery_attempts=0,
                max_recovery_attempts=3,
                resolved=resolved,
                resolved_at=datetime.now() if resolved else None,
                notes=""
            )
            error_store.save_error(error)
        
        results = error_store.get_recent_errors(resolved=True)
        assert len(results) == 1
        assert results[0].resolved is True


class TestErrorStoreStats:
    """Test statistics functionality"""

    def test_get_error_count_empty(self, error_store):
        """Test count on empty database"""
        count = error_store.get_error_count()
        assert count == 0

    def test_get_error_count_total(self, error_store):
        """Test total error count"""
        for i in range(5):
            error = SystemError(
                id=f"test-{i}",
                timestamp=datetime.now(),
                category=ErrorCategory.IMAP,
                severity=ErrorSeverity.LOW,
                exception_type="TestError",
                exception_message="Test",
                traceback="",
                component="test",
                operation="test",
                context={},
                recovery_strategy=RecoveryStrategy.SKIP,
                recovery_attempted=False,
                recovery_successful=None,
                recovery_attempts=0,
                max_recovery_attempts=3,
                resolved=False,
                resolved_at=None,
                notes=""
            )
            error_store.save_error(error)
        
        assert error_store.get_error_count() == 5

    def test_get_error_stats(self, error_store):
        """Test comprehensive error statistics"""
        # Create diverse errors
        categories = [ErrorCategory.IMAP, ErrorCategory.AI, ErrorCategory.IMAP]
        severities = [ErrorSeverity.LOW, ErrorSeverity.CRITICAL, ErrorSeverity.MEDIUM]
        resolved_states = [True, False, False]
        
        for i, (cat, sev, res) in enumerate(zip(categories, severities, resolved_states)):
            error = SystemError(
                id=f"test-{i}",
                timestamp=datetime.now(),
                category=cat,
                severity=sev,
                exception_type="TestError",
                exception_message="Test",
                traceback="",
                component="test",
                operation="test",
                context={},
                recovery_strategy=RecoveryStrategy.RETRY,
                recovery_attempted=i % 2 == 0,
                recovery_successful=True if i % 2 == 0 else None,
                recovery_attempts=0,
                max_recovery_attempts=3,
                resolved=res,
                resolved_at=datetime.now() if res else None,
                notes=""
            )
            error_store.save_error(error)
        
        stats = error_store.get_error_stats()

        assert stats["total_errors"] == 3
        assert stats["by_category"]["imap"] == 2
        assert stats["by_category"]["ai"] == 1
        assert stats["by_severity"]["low"] == 1
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_severity"]["medium"] == 1
        assert stats["resolved"] == 1
        assert stats["unresolved"] == 2
        assert stats["recovery_attempted"] == 2
        assert stats["recovery_successful"] == 2


class TestErrorStoreClear:
    """Test error clearing functionality"""

    def test_clear_resolved_errors(self, error_store):
        """Test clearing old resolved errors"""
        # Create old resolved error
        old_error = SystemError(
            id="old-resolved",
            timestamp=datetime.now() - timedelta(days=60),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.LOW,
            exception_type="TestError",
            exception_message="Old resolved",
            traceback="",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.SKIP,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=True,
            resolved_at=datetime.now() - timedelta(days=60),
            notes=""
        )
        error_store.save_error(old_error)
        
        # Create recent resolved error
        recent_error = SystemError(
            id="recent-resolved",
            timestamp=datetime.now(),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.LOW,
            exception_type="TestError",
            exception_message="Recent resolved",
            traceback="",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.SKIP,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=True,
            resolved_at=datetime.now(),
            notes=""
        )
        error_store.save_error(recent_error)
        
        # Clear errors older than 30 days
        deleted = error_store.clear_resolved_errors(older_than_days=30)
        
        assert deleted == 1
        assert error_store.get_error("old-resolved") is None
        assert error_store.get_error("recent-resolved") is not None

    def test_clear_resolved_errors_keeps_unresolved(self, error_store):
        """Test that unresolved errors are not deleted"""
        # Create old unresolved error
        error = SystemError(
            id="old-unresolved",
            timestamp=datetime.now() - timedelta(days=60),
            category=ErrorCategory.IMAP,
            severity=ErrorSeverity.LOW,
            exception_type="TestError",
            exception_message="Old unresolved",
            traceback="",
            component="test",
            operation="test",
            context={},
            recovery_strategy=RecoveryStrategy.SKIP,
            recovery_attempted=False,
            recovery_successful=None,
            recovery_attempts=0,
            max_recovery_attempts=3,
            resolved=False,
            resolved_at=None,
            notes=""
        )
        error_store.save_error(error)
        
        deleted = error_store.clear_resolved_errors(older_than_days=30)
        
        assert deleted == 0
        assert error_store.get_error("old-unresolved") is not None


class TestErrorStoreThreadSafety:
    """Test thread safety of ErrorStore"""

    def test_concurrent_saves(self, error_store):
        """Test that concurrent saves don't cause corruption"""
        def save_errors(thread_id, count):
            for i in range(count):
                error = SystemError(
                    id=f"thread-{thread_id}-{i}",
                    timestamp=datetime.now(),
                    category=ErrorCategory.IMAP,
                    severity=ErrorSeverity.LOW,
                    exception_type="TestError",
                    exception_message=f"Thread {thread_id} error {i}",
                    traceback="",
                    component="test",
                    operation="test",
                    context={},
                    recovery_strategy=RecoveryStrategy.SKIP,
                    recovery_attempted=False,
                    recovery_successful=None,
                    recovery_attempts=0,
                    max_recovery_attempts=3,
                    resolved=False,
                    resolved_at=None,
                    notes=""
                )
                error_store.save_error(error)
        
        # Create 10 threads, each saving 10 errors
        threads = []
        for i in range(10):
            t = threading.Thread(target=save_errors, args=(i, 10))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have 100 errors total
        count = error_store.get_error_count()
        assert count == 100

    def test_concurrent_reads_writes(self, error_store):
        """Test concurrent reads and writes"""
        results = []
        
        def writer():
            for i in range(50):
                error = SystemError(
                    id=f"write-{i}",
                    timestamp=datetime.now(),
                    category=ErrorCategory.IMAP,
                    severity=ErrorSeverity.LOW,
                    exception_type="TestError",
                    exception_message="Test",
                    traceback="",
                    component="test",
                    operation="test",
                    context={},
                    recovery_strategy=RecoveryStrategy.SKIP,
                    recovery_attempted=False,
                    recovery_successful=None,
                    recovery_attempts=0,
                    max_recovery_attempts=3,
                    resolved=False,
                    resolved_at=None,
                    notes=""
                )
                error_store.save_error(error)
        
        def reader():
            for _ in range(50):
                count = error_store.get_error_count()
                results.append(count)
        
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        
        writer_thread.start()
        reader_thread.start()
        
        writer_thread.join()
        reader_thread.join()
        
        # All operations should complete without error
        assert len(results) == 50


class TestErrorStoreSingleton:
    """Test singleton pattern"""

    def test_get_error_store_singleton(self):
        """Test that get_error_store returns same instance"""
        reset_error_store()
        
        store1 = get_error_store()
        store2 = get_error_store()
        
        assert store1 is store2

    def test_reset_error_store(self):
        """Test that reset creates new instance"""
        reset_error_store()
        
        store1 = get_error_store()
        reset_error_store()
        store2 = get_error_store()
        
        assert store1 is not store2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
