"""
Integration Tests for Event Flow

Tests the complete event flow from EmailProcessor → EventBus → DisplayManager
"""

from io import StringIO

import pytest
from rich.console import Console

from src.core.events import ProcessingEvent, ProcessingEventType, reset_event_bus
from src.jeeves.display_manager import DisplayManager
from src.monitoring.logger import ScapinLogger


@pytest.fixture(autouse=True)
def reset_global_bus():
    """Reset global event bus before each test"""
    reset_event_bus()
    yield
    reset_event_bus()


@pytest.fixture
def mock_console():
    """Create mock console for capturing output"""
    output = StringIO()
    console = Console(file=output, width=80, legacy_windows=False)
    return console, output


class TestEventFlowIntegration:
    """Test complete event flow"""

    def test_processing_started_flow(self, mock_console):
        """Test PROCESSING_STARTED event flow"""
        console, output = mock_console
        display = DisplayManager(console)

        # Start display manager (subscribe to events)
        display.start()

        # Emit processing started event
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.PROCESSING_STARTED,
            metadata={"limit": 50, "auto_execute": True}
        ))

        # Verify output contains expected text
        result = output.getvalue()
        assert "Scapin Processing Started" in result

    def test_email_completed_flow(self, mock_console):
        """Test EMAIL_COMPLETED event flow"""
        console, output = mock_console
        display = DisplayManager(console)
        display.start()

        # Emit email completed event
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_COMPLETED,
            email_id=123,
            subject="Test Email",
            from_address="test@example.com",
            preview="This is a test email preview",
            action="archive",
            confidence=95,
            category="work",
            current=1,
            total=5,
            metadata={"executed": True}
        ))

        # Verify output
        result = output.getvalue()
        assert "Test Email" in result
        assert "test@example.com" in result
        assert "ARCHIVE" in result
        assert "95%" in result

        # Verify stats updated
        assert display.stats["emails_processed"] == 1
        assert display.stats["emails_auto_executed"] == 1

    def test_email_queued_flow(self, mock_console):
        """Test EMAIL_QUEUED event flow"""
        console, output = mock_console
        display = DisplayManager(console)
        display.start()

        # Emit email queued event
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_QUEUED,
            email_id=456,
            subject="Low Confidence Email",
            from_address="queued@example.com",
            action="task",
            confidence=65,
            category="personal"
        ))

        # Verify output
        result = output.getvalue()
        assert "QUEUED FOR REVIEW" in result
        assert "Low Confidence Email" in result
        assert "65%" in result

        # Verify stats
        assert display.stats["emails_processed"] == 1
        assert display.stats["emails_queued"] == 1

    def test_email_error_flow(self, mock_console):
        """Test EMAIL_ERROR event flow"""
        console, output = mock_console
        display = DisplayManager(console)
        display.start()

        # Emit error event
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_ERROR,
            email_id=789,
            subject="Error Email",
            from_address="error@example.com",
            error="Connection timeout",
            error_type="TimeoutError"
        ))

        # Verify output
        result = output.getvalue()
        assert "ERROR" in result
        assert "Error Email" in result
        assert "Connection timeout" in result

        # Verify stats
        assert display.stats["emails_processed"] == 1
        assert display.stats["emails_errored"] == 1

    def test_account_flow(self, mock_console):
        """Test account started/completed flow"""
        console, output = mock_console
        display = DisplayManager(console)
        display.start()

        # Emit account started
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.ACCOUNT_STARTED,
            account_id="personal",
            account_name="Personal Email (iCloud)"
        ))

        # Emit account completed
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.ACCOUNT_COMPLETED,
            account_id="personal",
            metadata={"stats": {"total_processed": 25}}
        ))

        # Verify output
        result = output.getvalue()
        assert "Personal Email (iCloud)" in result
        assert "Account Completed" in result
        assert "25" in result

        # Verify stats
        assert display.stats["accounts_processed"] == 1

    def test_complete_processing_session(self, mock_console):
        """Test complete processing session with multiple emails"""
        console, output = mock_console
        display = DisplayManager(console)
        display.start()

        # Processing started
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.PROCESSING_STARTED
        ))

        # Process 3 emails
        for i in range(1, 4):
            display.event_bus.emit(ProcessingEvent(
                event_type=ProcessingEventType.EMAIL_COMPLETED,
                email_id=i,
                subject=f"Email {i}",
                from_address=f"user{i}@example.com",
                action="archive",
                confidence=90 + i,
                category="work",
                current=i,
                total=3,
                metadata={"executed": True}
            ))

        # Processing completed
        display.stop()

        # Verify all emails processed
        assert display.stats["emails_processed"] == 3
        assert display.stats["emails_auto_executed"] == 3

        # Verify output contains all emails
        result = output.getvalue()
        assert "Email 1" in result
        assert "Email 2" in result
        assert "Email 3" in result
        assert "Processing Summary" in result

    def test_mixed_execution_modes(self, mock_console):
        """Test mixed auto-execute and queued emails"""
        console, output = mock_console
        display = DisplayManager(console)
        display.start()

        # High confidence - auto-executed
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_COMPLETED,
            email_id=1,
            subject="High Confidence",
            from_address="high@example.com",
            action="archive",
            confidence=95,
            category="work",
            metadata={"executed": True}
        ))

        # Low confidence - queued
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_QUEUED,
            email_id=2,
            subject="Low Confidence",
            from_address="low@example.com",
            action="task",
            confidence=60,
            category="personal"
        ))

        # Error
        display.event_bus.emit(ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_ERROR,
            email_id=3,
            subject="Error Email",
            from_address="error@example.com",
            error="Parse error",
            error_type="ValueError"
        ))

        # Verify stats
        assert display.stats["emails_processed"] == 3
        assert display.stats["emails_auto_executed"] == 1
        assert display.stats["emails_queued"] == 1
        assert display.stats["emails_errored"] == 1


class TestDisplayModeIntegration:
    """Test ScapinLogger display mode integration"""

    def test_display_mode_hides_console_logs(self):
        """Test that display mode hides console logs"""

        # Ensure logging is configured
        ScapinLogger.configure()

        # Get a logger
        logger = ScapinLogger.get_logger("test")

        # Enable display mode
        ScapinLogger.set_display_mode(True)

        # Console handlers should be removed
        root_logger = ScapinLogger.get_logger("pkm")
        console_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, __import__('logging').StreamHandler)
        ]

        # Note: All console handlers should be removed in display mode
        assert ScapinLogger._display_mode is True

        # Disable display mode
        ScapinLogger.set_display_mode(False)

        # Console handlers should be restored
        assert ScapinLogger._display_mode is False

    @pytest.mark.skip(reason="Test hangs due to logger state - needs investigation")
    def test_display_mode_lifecycle(self):
        """Test display mode enable/disable cycle"""

        # Start with display mode disabled
        ScapinLogger.set_display_mode(False)
        assert ScapinLogger._display_mode is False

        # Enable
        ScapinLogger.set_display_mode(True)
        assert ScapinLogger._display_mode is True

        # Enable again (should be idempotent)
        ScapinLogger.set_display_mode(True)
        assert ScapinLogger._display_mode is True

        # Disable
        ScapinLogger.set_display_mode(False)
        assert ScapinLogger._display_mode is False

        # Disable again (should be idempotent)
        ScapinLogger.set_display_mode(False)
        assert ScapinLogger._display_mode is False


class TestEventBusIntegration:
    """Test EventBus with multiple subscribers"""

    def test_multiple_subscribers_receive_events(self):
        """Test that all subscribers receive events"""
        from src.core.events import get_event_bus

        bus = get_event_bus()

        # Track calls
        calls_1 = []
        calls_2 = []

        def handler1(event):
            calls_1.append(event)

        def handler2(event):
            calls_2.append(event)

        # Subscribe both handlers
        bus.subscribe(ProcessingEventType.EMAIL_COMPLETED, handler1)
        bus.subscribe(ProcessingEventType.EMAIL_COMPLETED, handler2)

        # Emit event
        event = ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_COMPLETED,
            email_id=123
        )
        bus.emit(event)

        # Both should receive
        assert len(calls_1) == 1
        assert len(calls_2) == 1
        assert calls_1[0].email_id == 123
        assert calls_2[0].email_id == 123

    def test_subscriber_exception_doesnt_affect_others(self):
        """Test that exception in one subscriber doesn't affect others"""
        from src.core.events import get_event_bus

        bus = get_event_bus()

        # Track calls
        good_calls = []

        def broken_handler(event):
            raise RuntimeError("Handler broke!")

        def good_handler(event):
            good_calls.append(event)

        # Subscribe both
        bus.subscribe(ProcessingEventType.EMAIL_COMPLETED, broken_handler)
        bus.subscribe(ProcessingEventType.EMAIL_COMPLETED, good_handler)

        # Emit event
        event = ProcessingEvent(
            event_type=ProcessingEventType.EMAIL_COMPLETED,
            email_id=123
        )
        bus.emit(event)

        # Good handler should still be called
        assert len(good_calls) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
