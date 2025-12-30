"""
Unit Tests for ErrorManager

Tests all ErrorManager functionality including:
- Error recording and retrieval
- Context sanitization
- Memory limits (LRU cache)
- Thread safety
- Recovery handler registration
- Statistics tracking
"""

import pytest
import threading
import json
from datetime import datetime
from typing import List

from src.core.error_manager import (
    ErrorManager,
    SystemError,
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy,
    sanitize_context,
    get_error_manager,
    reset_error_manager
)


@pytest.fixture
def error_manager():
    """Create ErrorManager instance for testing"""
    # Use None for error_store to avoid database dependency
    manager = ErrorManager(error_store=None, max_in_memory_errors=100)
    yield manager


class TestContextSanitization:
    """Test context sanitization for JSON serializability"""

    def test_sanitize_empty_context(self):
        """Test sanitizing empty context"""
        result = sanitize_context(None)
        assert result == {}
        
        result = sanitize_context({})
        assert result == {}

    def test_sanitize_json_serializable(self):
        """Test that JSON-serializable values pass through"""
        context = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None
        }
        
        result = sanitize_context(context)
        assert result == context
        
        # Verify can be serialized
        json.dumps(result)

    def test_sanitize_thread_object(self):
        """Test sanitizing thread objects"""
        import threading
        
        context = {
            "thread": threading.current_thread(),
            "valid": "data"
        }
        
        result = sanitize_context(context)
        
        assert "valid" in result
        assert result["valid"] == "data"
        assert "thread" in result
        assert "<Thread" in result["thread"] or "MainThread" in result["thread"]

    def test_sanitize_lambda(self):
        """Test sanitizing lambda functions"""
        context = {
            "lambda": lambda x: x * 2,
            "valid": "data"
        }
        
        result = sanitize_context(context)
        
        assert result["valid"] == "data"
        assert "lambda" in result
        assert "<function" in result["lambda"] or "lambda" in result["lambda"]

    def test_sanitize_complex_objects(self):
        """Test sanitizing various non-serializable objects"""
        import sqlite3
        
        context = {
            "connection": sqlite3.connect(":memory:"),
            "set": {1, 2, 3},
            "bytes": b"binary data",
            "valid": "data"
        }
        
        result = sanitize_context(context)
        
        assert result["valid"] == "data"
        assert "connection" in result
        assert "set" in result
        assert "bytes" in result

    def test_sanitize_unprintable_object(self):
        """Test object that can't even be str()"""
        class UnprintableObject:
            def __str__(self):
                raise RuntimeError("Cannot print")
            def __repr__(self):
                raise RuntimeError("Cannot repr")
        
        context = {
            "unprintable": UnprintableObject(),
            "valid": "data"
        }
        
        result = sanitize_context(context)
        
        assert result["valid"] == "data"
        assert "unprintable" in result
        assert "UnprintableObject" in result["unprintable"]


class TestErrorRecording:
    """Test error recording functionality"""

    def test_record_error_basic(self, error_manager):
        """Test recording a basic error"""
        exc = ValueError("Test error")
        
        error = error_manager.record_error(
            exc,
            category=ErrorCategory.VALIDATION,
            component="test",
            operation="test_operation"
        )
        
        assert error is not None
        assert error.exception_type == "ValueError"
        assert error.exception_message == "Test error"
        assert error.category == ErrorCategory.VALIDATION
        assert error.component == "test"
        assert error.operation == "test_operation"

    def test_record_error_with_context(self, error_manager):
        """Test recording error with context"""
        exc = RuntimeError("Test")
        context = {
            "user_id": 123,
            "action": "process_email",
            "data": {"key": "value"}
        }
        
        error = error_manager.record_error(
            exc,
            category=ErrorCategory.IMAP,
            component="test",
            operation="test",
            context=context
        )
        
        assert error.context["user_id"] == 123
        assert error.context["action"] == "process_email"
        assert error.context["data"]["key"] == "value"

    def test_record_error_sanitizes_context(self, error_manager):
        """Test that context is sanitized on recording"""
        import threading
        
        exc = RuntimeError("Test")
        context = {
            "thread": threading.current_thread(),
            "lambda": lambda x: x,
            "valid": "data"
        }
        
        error = error_manager.record_error(
            exc,
            category=ErrorCategory.IMAP,
            component="test",
            operation="test",
            context=context
        )
        
        # Context should be sanitized
        assert error.context["valid"] == "data"
        assert isinstance(error.context["thread"], str)
        assert isinstance(error.context["lambda"], str)
        
        # Should be JSON serializable
        json.dumps(error.context)

    def test_record_error_increments_stats(self, error_manager):
        """Test that recording increments statistics"""
        assert error_manager.error_count == 0
        
        error_manager.record_error(
            ValueError("Test"),
            category=ErrorCategory.VALIDATION,
            component="test",
            operation="test"
        )
        
        assert error_manager.error_count == 1
        assert error_manager.errors_by_category[ErrorCategory.VALIDATION] == 1

    def test_record_multiple_categories(self, error_manager):
        """Test recording errors in multiple categories"""
        categories = [ErrorCategory.IMAP, ErrorCategory.AI, ErrorCategory.NETWORK]
        
        for cat in categories:
            error_manager.record_error(
                RuntimeError("Test"),
                category=cat,
                component="test",
                operation="test"
            )
        
        assert error_manager.error_count == 3
        for cat in categories:
            assert error_manager.errors_by_category[cat] == 1


class TestMemoryLimits:
    """Test memory limit functionality (LRU cache)"""

    def test_memory_limit_enforced(self):
        """Test that memory limit is enforced"""
        manager = ErrorManager(error_store=None, max_in_memory_errors=10)
        
        # Record 20 errors
        for i in range(20):
            manager.record_error(
                RuntimeError(f"Error {i}"),
                category=ErrorCategory.IMAP,
                component="test",
                operation="test"
            )
        
        # Should only keep 10 most recent
        assert len(manager._recent_errors) == 10
        
        # Should be most recent (10-19)
        recent = manager.get_recent_errors(limit=10)
        assert len(recent) == 10
        assert "Error 19" in recent[0].exception_message
        assert "Error 10" in recent[-1].exception_message

    def test_lru_behavior(self):
        """Test LRU (oldest removed first)"""
        manager = ErrorManager(error_store=None, max_in_memory_errors=5)
        
        # Add 10 errors
        for i in range(10):
            manager.record_error(
                RuntimeError(f"Error {i}"),
                category=ErrorCategory.IMAP,
                component="test",
                operation="test"
            )
        
        # Should keep last 5 (5-9)
        recent = manager.get_recent_errors(limit=10)
        assert len(recent) == 5
        messages = [e.exception_message for e in recent]
        
        assert any("Error 9" in msg for msg in messages)
        assert any("Error 5" in msg for msg in messages)
        assert not any("Error 0" in msg for msg in messages)
        assert not any("Error 4" in msg for msg in messages)


class TestRecoveryHandlers:
    """Test recovery handler registration and invocation"""

    def test_register_handler(self, error_manager):
        """Test registering a recovery handler"""
        handler_called = []

        def test_handler(error: SystemError) -> bool:
            handler_called.append(error)
            return True

        error_manager.register_recovery_handler(ErrorCategory.IMAP, test_handler)

        # Record error
        error = error_manager.record_error(
            RuntimeError("Test"),
            category=ErrorCategory.IMAP,
            component="test",
            operation="test"
        )

        # Explicitly attempt recovery
        error_manager.attempt_recovery(error)

        # Handler should be called
        assert len(handler_called) == 1
        assert handler_called[0] == error

    def test_handler_not_called_for_different_category(self, error_manager):
        """Test handler only called for registered category"""
        handler_called = []
        
        def test_handler(error: SystemError) -> bool:
            handler_called.append(error)
            return True
        
        error_manager.register_recovery_handler(ErrorCategory.IMAP, test_handler)
        
        # Record error with different category
        error_manager.record_error(
            RuntimeError("Test"),
            category=ErrorCategory.AI,
            component="test",
            operation="test"
        )
        
        # Handler should NOT be called
        assert len(handler_called) == 0

    def test_handler_success_marks_recovery(self, error_manager):
        """Test successful handler marks recovery_successful"""
        def success_handler(error: SystemError) -> bool:
            return True

        error_manager.register_recovery_handler(ErrorCategory.IMAP, success_handler)

        error = error_manager.record_error(
            RuntimeError("Test"),
            category=ErrorCategory.IMAP,
            component="test",
            operation="test"
        )

        # Attempt recovery
        result = error_manager.attempt_recovery(error)

        assert error.recovery_attempted is True
        assert error.recovery_successful is True
        assert result is True

    def test_handler_failure_marks_recovery(self, error_manager):
        """Test failed handler marks recovery_successful=False"""
        def failure_handler(error: SystemError) -> bool:
            return False

        error_manager.register_recovery_handler(ErrorCategory.IMAP, failure_handler)

        error = error_manager.record_error(
            RuntimeError("Test"),
            category=ErrorCategory.IMAP,
            component="test",
            operation="test"
        )

        # Attempt recovery
        result = error_manager.attempt_recovery(error)

        assert error.recovery_attempted is True
        assert error.recovery_successful is False
        assert result is False

    def test_handler_exception_caught(self, error_manager):
        """Test that handler exceptions are caught"""
        def broken_handler(error: SystemError) -> bool:
            raise RuntimeError("Handler broke!")

        error_manager.register_recovery_handler(ErrorCategory.IMAP, broken_handler)

        error = error_manager.record_error(
            RuntimeError("Test"),
            category=ErrorCategory.IMAP,
            component="test",
            operation="test"
        )

        # Should not raise, should handle gracefully
        result = error_manager.attempt_recovery(error)

        assert error.recovery_attempted is True
        assert error.recovery_successful is False
        assert result is False


class TestStatistics:
    """Test statistics retrieval"""

    def test_get_stats_empty(self, error_manager):
        """Test statistics on empty manager"""
        stats = error_manager.get_error_stats()
        
        assert stats["total_errors"] == 0
        assert stats["errors_by_category"] == {}

    def test_get_stats_populated(self, error_manager):
        """Test statistics with recorded errors"""
        # Record diverse errors
        for i in range(3):
            error_manager.record_error(
                RuntimeError("Test"),
                category=ErrorCategory.IMAP,
                component="test",
                operation="test"
            )
        
        for i in range(2):
            error_manager.record_error(
                RuntimeError("Test"),
                category=ErrorCategory.AI,
                component="test",
                operation="test"
            )
        
        stats = error_manager.get_error_stats()

        assert stats["total_errors"] == 5
        assert stats["errors_by_category"]["imap"] == 3
        assert stats["errors_by_category"]["ai"] == 2

    def test_reset_stats(self, error_manager):
        """Test resetting statistics"""
        # Record some errors
        for i in range(5):
            error_manager.record_error(
                RuntimeError("Test"),
                category=ErrorCategory.IMAP,
                component="test",
                operation="test"
            )
        
        assert error_manager.error_count == 5
        
        # Reset
        error_manager.reset_stats()
        
        assert error_manager.error_count == 0
        assert len(error_manager._recent_errors) == 0
        assert len(error_manager.errors_by_category) == 0


class TestThreadSafety:
    """Test thread safety of ErrorManager"""

    def test_concurrent_error_recording(self):
        """Test concurrent error recording from multiple threads"""
        manager = ErrorManager(error_store=None, max_in_memory_errors=1000)
        
        def record_errors(thread_id):
            for i in range(100):
                manager.record_error(
                    RuntimeError(f"Thread {thread_id} Error {i}"),
                    category=ErrorCategory.IMAP,
                    component="test",
                    operation="test"
                )
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=record_errors, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have 1000 total errors
        assert manager.error_count == 1000

    def test_concurrent_stats_access(self):
        """Test concurrent statistics access"""
        manager = ErrorManager(error_store=None)
        results = []
        
        def record_errors():
            for i in range(50):
                manager.record_error(
                    RuntimeError("Test"),
                    category=ErrorCategory.IMAP,
                    component="test",
                    operation="test"
                )
        
        def read_stats():
            for _ in range(50):
                stats = manager.get_error_stats()
                results.append(stats["total_errors"])
        
        writer = threading.Thread(target=record_errors)
        reader = threading.Thread(target=read_stats)
        
        writer.start()
        reader.start()
        
        writer.join()
        reader.join()
        
        # Should complete without crashes
        assert len(results) == 50


class TestSingleton:
    """Test singleton pattern"""

    def test_get_error_manager_singleton(self):
        """Test that get_error_manager returns same instance"""
        reset_error_manager()
        
        manager1 = get_error_manager()
        manager2 = get_error_manager()
        
        assert manager1 is manager2

    def test_reset_error_manager(self):
        """Test resetting creates new instance"""
        reset_error_manager()
        
        manager1 = get_error_manager()
        reset_error_manager()
        manager2 = get_error_manager()
        
        assert manager1 is not manager2

    def test_singleton_thread_safe(self):
        """Test singleton is thread-safe"""
        reset_error_manager()
        
        instances = []
        
        def get_instance():
            instances.append(id(get_error_manager()))
        
        threads = []
        for _ in range(100):
            t = threading.Thread(target=get_instance)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All threads should get same instance
        assert len(set(instances)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
