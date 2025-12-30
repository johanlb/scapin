"""
Tests for Display Manager (Phase 1)

Tests the DisplayManager that renders email processing events sequentially.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from rich.console import Console
from io import StringIO

from src.cli.display_manager import DisplayManager
from src.core.events import EventType, ProcessingEvent, EventBus


class TestDisplayManager:
    """Test DisplayManager"""

    def setup_method(self):
        """Create test fixtures"""
        # Create console with StringIO to capture output
        self.output = StringIO()
        self.console = Console(file=self.output, width=80, legacy_windows=False)
        self.event_bus = EventBus()

    def test_init(self):
        """Test DisplayManager initialization"""
        display = DisplayManager(self.console)

        assert display.console is self.console
        assert display.event_bus is not None
        assert display._is_active is False
        assert display.stats["accounts_processed"] == 0
        assert display.stats["emails_processed"] == 0

    def test_init_without_console(self):
        """Test DisplayManager creates console if not provided"""
        display = DisplayManager()

        assert display.console is not None
        assert isinstance(display.console, Console)

    def test_start_subscribes_to_events(self):
        """Test that start() subscribes to all relevant events"""
        display = DisplayManager(self.console)

        # Mock the event bus
        display.event_bus = Mock()

        display.start()

        # Verify subscriptions
        assert display.event_bus.subscribe.call_count >= 8  # At least 8 event types
        assert display._is_active is True

    def test_start_when_already_active(self):
        """Test starting when already active (should not double-subscribe)"""
        display = DisplayManager(self.console)
        display.event_bus = Mock()

        display.start()
        first_call_count = display.event_bus.subscribe.call_count

        # Start again
        display.start()

        # Should not subscribe again
        assert display.event_bus.subscribe.call_count == first_call_count

    def test_stop(self):
        """Test stopping display manager"""
        display = DisplayManager(self.console)
        display._is_active = True

        display.stop()

        assert display._is_active is False

    def test_on_processing_started(self):
        """Test processing started event handler"""
        display = DisplayManager(self.console)

        event = ProcessingEvent(event_type=EventType.PROCESSING_STARTED)
        display._on_processing_started(event)

        output = self.output.getvalue()
        assert "PKM Email Processing Started" in output

    def test_on_account_started(self):
        """Test account started event handler"""
        display = DisplayManager(self.console)

        event = ProcessingEvent(
            event_type=EventType.ACCOUNT_STARTED,
            account_id="personal",
            account_name="Personal (iCloud)",
        )
        display._on_account_started(event)

        output = self.output.getvalue()
        assert "Personal (iCloud)" in output
        assert display.current_account_id == "personal"
        assert display.current_account_name == "Personal (iCloud)"

    def test_on_account_completed(self):
        """Test account completed event handler"""
        display = DisplayManager(self.console)
        display.current_account_name = "Test Account"

        event = ProcessingEvent(
            event_type=EventType.ACCOUNT_COMPLETED,
            metadata={"stats": {"total_processed": 25}},
        )
        display._on_account_completed(event)

        output = self.output.getvalue()
        assert "Account Completed" in output
        assert "25" in output
        assert display.stats["accounts_processed"] == 1

    def test_on_email_completed(self):
        """Test email completed event handler"""
        display = DisplayManager(self.console)

        event = ProcessingEvent(
            event_type=EventType.EMAIL_COMPLETED,
            email_id=123,
            subject="Test Email",
            from_address="test@example.com",
            preview="This is a test email content preview",
            action="archive",
            confidence=95,
            category="work",
            current=5,
            total=10,
            metadata={"executed": True},
        )
        display._on_email_completed(event)

        output = self.output.getvalue()
        assert "Test Email" in output
        assert "test@example.com" in output
        assert "ARCHIVE" in output
        assert "95%" in output
        assert "5/10" in output
        assert display.stats["emails_processed"] == 1
        assert display.stats["emails_auto_executed"] == 1

    def test_on_email_queued(self):
        """Test email queued event handler"""
        display = DisplayManager(self.console)

        event = ProcessingEvent(
            event_type=EventType.EMAIL_QUEUED,
            email_id=456,
            subject="Queued Email",
            from_address="queued@example.com",
            action="task",
            confidence=75,
            category="personal",
        )
        display._on_email_queued(event)

        output = self.output.getvalue()
        assert "QUEUED FOR REVIEW" in output
        assert "Queued Email" in output
        assert "queued@example.com" in output
        assert display.stats["emails_queued"] == 1

    def test_on_email_error(self):
        """Test email error event handler"""
        display = DisplayManager(self.console)

        event = ProcessingEvent(
            event_type=EventType.EMAIL_ERROR,
            email_id=789,
            subject="Error Email",
            from_address="error@example.com",
            error="Connection timeout",
            error_type="TimeoutError",
        )
        display._on_email_error(event)

        output = self.output.getvalue()
        assert "ERROR" in output
        assert "Error Email" in output
        assert "Connection timeout" in output
        assert display.stats["emails_errored"] == 1

    def test_get_confidence_color(self):
        """Test confidence color mapping"""
        display = DisplayManager(self.console)

        assert display._get_confidence_color(95) == "green"
        assert display._get_confidence_color(85) == "yellow"
        assert display._get_confidence_color(70) == "orange"
        assert display._get_confidence_color(50) == "red"

    def test_render_confidence_bar(self):
        """Test confidence bar rendering"""
        display = DisplayManager(self.console)

        bar_95 = display._render_confidence_bar(95)
        assert "███" in bar_95  # 3 filled blocks (95/100*4 = 3.8 -> 3)
        assert "95%" in bar_95

        bar_50 = display._render_confidence_bar(50)
        assert "██" in bar_50  # 2 filled blocks
        assert "░░" in bar_50  # 2 empty blocks
        assert "50%" in bar_50

        bar_100 = display._render_confidence_bar(100)
        assert "████" in bar_100  # 4 filled blocks for 100%
        assert "100%" in bar_100

    def test_action_icons(self):
        """Test that action icons are defined"""
        assert DisplayManager.ACTION_ICONS["archive"] == "📦"
        assert DisplayManager.ACTION_ICONS["delete"] == "🗑️"
        assert DisplayManager.ACTION_ICONS["task"] == "✅"
        assert DisplayManager.ACTION_ICONS["reference"] == "📚"
        assert DisplayManager.ACTION_ICONS["reply"] == "↩️"

    def test_category_icons(self):
        """Test that category icons are defined"""
        assert DisplayManager.CATEGORY_ICONS["work"] == "💼"
        assert DisplayManager.CATEGORY_ICONS["personal"] == "👤"
        assert DisplayManager.CATEGORY_ICONS["finance"] == "💰"
        assert DisplayManager.CATEGORY_ICONS["shopping"] == "🛒"

    def test_show_final_summary(self):
        """Test final summary display"""
        display = DisplayManager(self.console)

        # Set some stats
        display.stats["accounts_processed"] = 2
        display.stats["emails_processed"] = 50
        display.stats["emails_auto_executed"] = 35
        display.stats["emails_queued"] = 15
        display.stats["emails_errored"] = 2

        display._show_final_summary()

        output = self.output.getvalue()
        assert "Processing Summary" in output
        assert "50" in output  # emails processed
        assert "35" in output  # auto-executed
        assert "15" in output  # queued

    def test_integration_with_event_bus(self):
        """Test integration with EventBus"""
        display = DisplayManager(self.console)

        # Use real event bus for this test
        display.start()

        # Emit events
        display.event_bus.emit(
            ProcessingEvent(event_type=EventType.PROCESSING_STARTED)
        )

        display.event_bus.emit(
            ProcessingEvent(
                event_type=EventType.EMAIL_COMPLETED,
                email_id=123,
                subject="Integration Test",
                from_address="test@example.com",
                action="archive",
                confidence=90,
                category="work",
            )
        )

        display.stop()

        # Verify output contains expected content
        output = self.output.getvalue()
        assert "PKM Email Processing Started" in output
        assert "Integration Test" in output
        assert "Processing Summary" in output


class TestDisplayManagerCreation:
    """Test display manager creation helper"""

    def test_create_display_manager(self):
        """Test create_display_manager helper function"""
        from src.cli.display_manager import create_display_manager

        display = create_display_manager()
        assert isinstance(display, DisplayManager)
        assert display.console is not None
