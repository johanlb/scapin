"""
Unit Tests for Event System

Tests EventBus, ProcessingEvent, and event handling.
"""

import pytest
import threading
import time
from datetime import datetime

from src.core.events import (
    EventType,
    ProcessingEvent,
    EventBus,
    get_event_bus,
    reset_event_bus
)


@pytest.fixture
def event_bus():
    """Create fresh EventBus for each test"""
    bus = EventBus()
    yield bus
    bus.clear()


@pytest.fixture(autouse=True)
def reset_global_bus():
    """Reset global event bus after each test"""
    yield
    reset_event_bus()


class TestEventType:
    """Test EventType enum"""

    def test_event_types_exist(self):
        """Test all event types are defined"""
        assert EventType.ACCOUNT_STARTED == "account_started"
        assert EventType.EMAIL_COMPLETED == "email_completed"
        assert EventType.BATCH_COMPLETED == "batch_completed"

    def test_event_type_is_string(self):
        """Test EventType values are strings"""
        assert isinstance(EventType.EMAIL_STARTED.value, str)
        assert EventType.EMAIL_STARTED.value == "email_started"


class TestProcessingEvent:
    """Test ProcessingEvent dataclass"""

    def test_create_minimal_event(self):
        """Test creating event with minimal fields"""
        event = ProcessingEvent(event_type=EventType.EMAIL_STARTED)

        assert event.event_type == EventType.EMAIL_STARTED
        assert isinstance(event.timestamp, datetime)
        assert event.email_id is None

    def test_create_full_event(self):
        """Test creating event with all fields"""
        event = ProcessingEvent(
            event_type=EventType.EMAIL_COMPLETED,
            account_id="personal",
            account_name="Personal Email",
            email_id=123,
            subject="Test Email",
            from_address="test@example.com",
            preview="This is a preview",
            action="archive",
            confidence=95,
            category="work",
            reasoning="High confidence work email",
            current=5,
            total=10,
            metadata={"extra": "data"}
        )

        assert event.event_type == EventType.EMAIL_COMPLETED
        assert event.account_id == "personal"
        assert event.email_id == 123
        assert event.subject == "Test Email"
        assert event.confidence == 95
        assert event.metadata["extra"] == "data"

    def test_event_str_representation(self):
        """Test string representation of event"""
        event = ProcessingEvent(
            event_type=EventType.EMAIL_COMPLETED,
            email_id=123,
            action="archive",
            current=5,
            total=10
        )

        str_repr = str(event)
        assert "[email_completed]" in str_repr
        assert "email=123" in str_repr
        assert "action=archive" in str_repr
        assert "5/10" in str_repr

    def test_error_event(self):
        """Test event with error"""
        event = ProcessingEvent(
            event_type=EventType.EMAIL_ERROR,
            email_id=123,
            error="Connection failed",
            error_type="ConnectionError"
        )

        assert event.error == "Connection failed"
        assert "error=Connection failed" in str(event)


class TestEventBus:
    """Test EventBus functionality"""

    def test_subscribe_to_event(self, event_bus):
        """Test subscribing to events"""
        called = []

        def handler(event):
            called.append(event)

        event_bus.subscribe(EventType.EMAIL_STARTED, handler)

        assert event_bus.get_subscriber_count(EventType.EMAIL_STARTED) == 1
        assert event_bus.get_subscriber_count() == 1

    def test_emit_event_calls_subscriber(self, event_bus):
        """Test that emitting calls subscribers"""
        called = []

        def handler(event):
            called.append(event)

        event_bus.subscribe(EventType.EMAIL_STARTED, handler)

        event = ProcessingEvent(
            event_type=EventType.EMAIL_STARTED,
            email_id=123
        )
        event_bus.emit(event)

        assert len(called) == 1
        assert called[0].email_id == 123

    def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers to same event"""
        calls_1 = []
        calls_2 = []

        def handler1(event):
            calls_1.append(event)

        def handler2(event):
            calls_2.append(event)

        event_bus.subscribe(EventType.EMAIL_STARTED, handler1)
        event_bus.subscribe(EventType.EMAIL_STARTED, handler2)

        event = ProcessingEvent(event_type=EventType.EMAIL_STARTED)
        event_bus.emit(event)

        assert len(calls_1) == 1
        assert len(calls_2) == 1

    def test_different_event_types(self, event_bus):
        """Test subscribers only receive their event type"""
        started_calls = []
        completed_calls = []

        def started_handler(event):
            started_calls.append(event)

        def completed_handler(event):
            completed_calls.append(event)

        event_bus.subscribe(EventType.EMAIL_STARTED, started_handler)
        event_bus.subscribe(EventType.EMAIL_COMPLETED, completed_handler)

        # Emit started event
        event_bus.emit(ProcessingEvent(event_type=EventType.EMAIL_STARTED))
        assert len(started_calls) == 1
        assert len(completed_calls) == 0

        # Emit completed event
        event_bus.emit(ProcessingEvent(event_type=EventType.EMAIL_COMPLETED))
        assert len(started_calls) == 1
        assert len(completed_calls) == 1

    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events"""
        called = []

        def handler(event):
            called.append(event)

        event_bus.subscribe(EventType.EMAIL_STARTED, handler)
        event_bus.unsubscribe(EventType.EMAIL_STARTED, handler)

        event_bus.emit(ProcessingEvent(event_type=EventType.EMAIL_STARTED))

        assert len(called) == 0
        assert event_bus.get_subscriber_count(EventType.EMAIL_STARTED) == 0

    def test_callback_exception_caught(self, event_bus):
        """Test that callback exceptions don't crash emit"""
        called_good = []

        def broken_handler(event):
            raise RuntimeError("Handler broke!")

        def good_handler(event):
            called_good.append(event)

        event_bus.subscribe(EventType.EMAIL_STARTED, broken_handler)
        event_bus.subscribe(EventType.EMAIL_STARTED, good_handler)

        # Should not raise, should call good_handler
        event_bus.emit(ProcessingEvent(event_type=EventType.EMAIL_STARTED))

        assert len(called_good) == 1

    def test_clear(self, event_bus):
        """Test clearing all subscribers"""
        def handler(event):
            pass

        event_bus.subscribe(EventType.EMAIL_STARTED, handler)
        event_bus.subscribe(EventType.EMAIL_COMPLETED, handler)

        assert event_bus.get_subscriber_count() == 2

        event_bus.clear()

        assert event_bus.get_subscriber_count() == 0
        assert event_bus.get_event_count() == 0

    def test_event_count(self, event_bus):
        """Test event counting"""
        assert event_bus.get_event_count() == 0

        for i in range(5):
            event_bus.emit(ProcessingEvent(event_type=EventType.EMAIL_STARTED))

        assert event_bus.get_event_count() == 5


class TestThreadSafety:
    """Test thread-safety of EventBus"""

    def test_concurrent_subscribe(self, event_bus):
        """Test concurrent subscriptions"""
        def subscribe_handler(thread_id):
            def handler(event):
                pass
            event_bus.subscribe(EventType.EMAIL_STARTED, handler)

        threads = []
        for i in range(10):
            t = threading.Thread(target=subscribe_handler, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert event_bus.get_subscriber_count(EventType.EMAIL_STARTED) == 10

    def test_concurrent_emit(self, event_bus):
        """Test concurrent event emission"""
        calls = []
        lock = threading.Lock()

        def handler(event):
            with lock:
                calls.append(event)

        event_bus.subscribe(EventType.EMAIL_STARTED, handler)

        def emit_events(count):
            for i in range(count):
                event_bus.emit(ProcessingEvent(
                    event_type=EventType.EMAIL_STARTED,
                    email_id=i
                ))

        threads = []
        for i in range(5):
            t = threading.Thread(target=emit_events, args=(10,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have 50 calls (5 threads × 10 events)
        assert len(calls) == 50


class TestGlobalEventBus:
    """Test global event bus singleton"""

    def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns same instance"""
        reset_event_bus()

        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2

    def test_reset_event_bus(self):
        """Test resetting creates new instance"""
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()

        assert bus1 is not bus2

    def test_singleton_thread_safe(self):
        """Test singleton is thread-safe"""
        reset_event_bus()

        instances = []
        lock = threading.Lock()

        def get_instance():
            bus = get_event_bus()
            with lock:
                instances.append(id(bus))

        threads = []
        for _ in range(50):
            t = threading.Thread(target=get_instance)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should get same instance
        assert len(set(instances)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
