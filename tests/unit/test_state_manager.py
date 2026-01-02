"""
Unit tests for StateManager
"""

import threading
import time
from datetime import datetime

from src.core.state_manager import (
    ProcessingState,
    SessionStats,
    StateManager,
    get_state_manager,
)


class TestSessionStats:
    """Test SessionStats"""

    def test_session_stats_defaults(self):
        """Test SessionStats default values"""
        stats = SessionStats()

        assert stats.emails_processed == 0
        assert stats.archived == 0
        assert stats.deleted == 0
        assert isinstance(stats.start_time, datetime)
        assert stats.end_time is None

    def test_confidence_avg_calculation(self):
        """Test confidence average calculation"""
        stats = SessionStats()
        stats.confidence_scores = [80, 90, 100]

        assert stats.confidence_avg == 90.0

    def test_confidence_avg_empty(self):
        """Test confidence average with no scores"""
        stats = SessionStats()

        assert stats.confidence_avg == 0.0

    def test_duration_minutes(self):
        """Test duration calculation"""
        stats = SessionStats()
        time.sleep(0.1)  # Sleep briefly
        stats.end_time = datetime.now()

        assert stats.duration_minutes >= 0

    def test_emails_per_minute(self):
        """Test emails per minute calculation"""
        stats = SessionStats()
        stats.emails_processed = 60
        stats.end_time = datetime.now()

        # Should be around 60/duration
        assert stats.emails_per_minute >= 0


class TestStateManager:
    """Test StateManager"""

    def setup_method(self):
        """Create fresh StateManager for each test"""
        self.state = StateManager()

    def test_set_and_get(self):
        """Test basic set/get"""
        self.state.set("test_key", "test_value")

        assert self.state.get("test_key") == "test_value"

    def test_get_with_default(self):
        """Test get with default value"""
        value = self.state.get("nonexistent", default="default_value")

        assert value == "default_value"

    def test_delete(self):
        """Test deleting key"""
        self.state.set("test_key", "value")
        self.state.delete("test_key")

        assert self.state.get("test_key") is None

    def test_increment(self):
        """Test increment counter"""
        result = self.state.increment("counter")
        assert result == 1

        result = self.state.increment("counter")
        assert result == 2

        result = self.state.increment("counter", amount=5)
        assert result == 7

    def test_decrement(self):
        """Test decrement counter"""
        self.state.set("counter", 10)

        result = self.state.decrement("counter")
        assert result == 9

        result = self.state.decrement("counter", amount=5)
        assert result == 4

    def test_add_to_list(self):
        """Test adding to list"""
        self.state.add_to_list("items", "item1")
        self.state.add_to_list("items", "item2")

        items = self.state.get("items")
        assert items == ["item1", "item2"]

    def test_add_to_set(self):
        """Test adding to set"""
        self.state.add_to_set("unique_items", "a")
        self.state.add_to_set("unique_items", "b")
        self.state.add_to_set("unique_items", "a")  # Duplicate

        unique_items = self.state.get("unique_items")
        assert unique_items == {"a", "b"}

    def test_is_processed_and_mark_processed(self):
        """Test message ID tracking"""
        message_id = "msg-123"

        assert not self.state.is_processed(message_id)

        self.state.mark_processed(message_id)

        assert self.state.is_processed(message_id)

    def test_cache_entity(self):
        """Test entity caching"""
        entity_data = {"name": "John Doe", "email": "john@example.com"}

        self.state.cache_entity("person-123", entity_data)

        cached = self.state.get_cached_entity("person-123")
        assert cached == entity_data

    def test_get_cached_entity_nonexistent(self):
        """Test getting non-existent cached entity"""
        cached = self.state.get_cached_entity("nonexistent")

        assert cached is None

    def test_clear_caches(self):
        """Test clearing caches"""
        self.state.cache_entity("entity1", {"data": "value"})

        self.state.clear_caches()

        assert self.state.get_cached_entity("entity1") is None

    def test_reset_session(self):
        """Test resetting session"""
        self.state.stats.emails_processed = 10
        self.state.mark_processed("msg-123")
        self.state.processing_state = ProcessingState.RUNNING

        self.state.reset_session()

        assert self.state.stats.emails_processed == 0
        assert not self.state.is_processed("msg-123")
        assert self.state.processing_state == ProcessingState.IDLE

    def test_end_session(self):
        """Test ending session"""
        self.state.stats.emails_processed = 50

        final_stats = self.state.end_session()

        assert final_stats.emails_processed == 50
        assert final_stats.end_time is not None
        assert self.state.processing_state == ProcessingState.IDLE

    def test_processing_state(self):
        """Test processing state property"""
        assert self.state.processing_state == ProcessingState.IDLE

        self.state.processing_state = ProcessingState.RUNNING
        assert self.state.processing_state == ProcessingState.RUNNING

        self.state.processing_state = ProcessingState.PAUSED
        assert self.state.processing_state == ProcessingState.PAUSED

    def test_thread_safety(self):
        """Test thread-safe operations"""

        def increment_counter():
            for _ in range(1000):
                self.state.increment("thread_counter")

        threads = [threading.Thread(target=increment_counter) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should be exactly 5000 (5 threads * 1000 increments)
        assert self.state.get("thread_counter") == 5000

    def test_to_dict(self):
        """Test exporting state to dict"""
        self.state.set("test_key", "test_value")
        self.state.stats.emails_processed = 10
        self.state.mark_processed("msg-123")

        state_dict = self.state.to_dict()

        assert "state" in state_dict
        assert "processing_state" in state_dict
        assert "stats" in state_dict
        assert state_dict["stats"]["emails_processed"] == 10
        assert state_dict["processed_count"] == 1


class TestGetStateManager:
    """Test get_state_manager singleton"""

    def test_get_state_manager_returns_singleton(self):
        """Test get_state_manager returns same instance"""
        state1 = get_state_manager()
        state2 = get_state_manager()

        assert state1 is state2

    def test_get_state_manager_returns_state_manager(self):
        """Test get_state_manager returns StateManager instance"""
        state = get_state_manager()

        assert isinstance(state, StateManager)
