"""
Display Manager for PKM Email Processor

Provides sequential, beautiful display of email processing events using Rich.
Subscribes to EventBus and renders events as they arrive.
"""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.core.processing_events import ProcessingEvent, ProcessingEventType, get_event_bus
from src.monitoring.logger import PKMLogger
from src.utils import now_utc

logger = PKMLogger.get_logger(__name__)


class DisplayManager:
    """
    Manages sequential display of email processing events

    Subscribes to EventBus and renders beautiful, sequential output
    even when backend processes emails in parallel.

    Features:
        - Icon-based visual indicators
        - Confidence bars with colors
        - Content previews (80 chars)
        - Account separation
        - Progress tracking
        - Statistics tracking

    Example:
        display = DisplayManager(console)
        display.start()  # Subscribe to events
        # ... processing happens ...
        display.stop()   # Unsubscribe and show summary
    """

    # Icon mappings (class attributes for testing)
    ACTION_ICONS = {
        "archive": "📦",
        "delete": "🗑️",
        "task": "✅",
        "reference": "📚",
        "reply": "↩️",
        "skip": "⏭️",
        "queue": "📥"
    }

    CATEGORY_ICONS = {
        "work": "💼",
        "personal": "👤",
        "finance": "💰",
        "art": "🎨",
        "newsletter": "📰",
        "shopping": "🛒",
        "travel": "✈️",
        "health": "🏥",
        "social": "👥",
        "spam": "🚫"
    }

    # Color schemes by action
    ACTION_COLORS = {
        "archive": "cyan",
        "delete": "red",
        "task": "green",
        "reference": "blue",
        "reply": "yellow",
        "skip": "dim",
        "queue": "magenta"
    }

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize display manager

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()
        self.event_bus = get_event_bus()

        # State tracking
        self._is_active = False
        self.current_account_id: Optional[str] = None
        self.current_account_name: Optional[str] = None

        # Statistics
        self.stats: dict[str, int] = {
            "accounts_processed": 0,
            "emails_processed": 0,
            "emails_auto_executed": 0,
            "emails_queued": 0,
            "emails_errored": 0
        }

        logger.debug("DisplayManager initialized")

    def start(self) -> None:
        """
        Start display manager (subscribe to events)

        Subscribes to all relevant events for display.
        Safe to call multiple times (won't double-subscribe).
        """
        if self._is_active:
            logger.debug("DisplayManager already active")
            return

        # Subscribe to events
        self.event_bus.subscribe(ProcessingEventType.PROCESSING_STARTED, self._on_processing_started)
        self.event_bus.subscribe(ProcessingEventType.ACCOUNT_STARTED, self._on_account_started)
        self.event_bus.subscribe(ProcessingEventType.ACCOUNT_COMPLETED, self._on_account_completed)
        self.event_bus.subscribe(ProcessingEventType.EMAIL_COMPLETED, self._on_email_completed)
        self.event_bus.subscribe(ProcessingEventType.EMAIL_QUEUED, self._on_email_queued)
        self.event_bus.subscribe(ProcessingEventType.EMAIL_ERROR, self._on_email_error)
        self.event_bus.subscribe(ProcessingEventType.BATCH_COMPLETED, self._on_batch_completed)
        self.event_bus.subscribe(ProcessingEventType.PROCESSING_COMPLETED, self._show_final_summary)

        self._is_active = True

        logger.debug("DisplayManager started (subscribed to events)")

    def stop(self) -> None:
        """
        Stop display manager and show final summary

        Displays final summary and sets active to False.
        Does NOT unsubscribe (EventBus will be cleared separately).
        """
        if not self._is_active:
            return

        self._show_final_summary()
        self._is_active = False

        logger.debug("DisplayManager stopped")

    def _on_processing_started(self, _event: ProcessingEvent) -> None:
        """
        Handle processing started event

        Args:
            event: Processing started event
        """
        self.console.print()
        self.console.print(Panel.fit(
            "[bold cyan]PKM Email Processing Started[/bold cyan]\n"
            "[dim]Processing emails with AI-powered classification[/dim]",
            border_style="cyan"
        ))

        logger.debug("Processing started event displayed")

    def _on_account_started(self, event: ProcessingEvent) -> None:
        """
        Handle account started event

        Args:
            event: Account started event
        """
        self.current_account_id = event.account_id
        self.current_account_name = event.account_name or event.account_id

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]Processing Account: {self.current_account_name}[/bold cyan]\n"
            f"[dim]{event.account_id}[/dim]",
            border_style="cyan"
        ))

        logger.debug(f"Account started: {event.account_id}")

    def _on_account_completed(self, event: ProcessingEvent) -> None:
        """
        Handle account completed event

        Args:
            event: Account completed event
        """
        self.stats["accounts_processed"] += 1

        stats = event.metadata.get("stats", {})
        total_processed = stats.get("total_processed", 0)

        account_name = self.current_account_name or event.account_name or "Unknown"

        self.console.print(Panel.fit(
            f"[bold green]✓ Account Completed: {account_name}[/bold green]\n"
            f"[dim]Processed: {total_processed} emails[/dim]",
            border_style="green"
        ))

        logger.debug(f"Account completed: {event.account_id}")

    def _on_email_completed(self, event: ProcessingEvent) -> None:
        """
        Render completed email with beautiful formatting

        Args:
            event: Email completed event
        """
        self.stats["emails_processed"] += 1

        # Check if executed
        if event.metadata.get("executed", False):
            self.stats["emails_auto_executed"] += 1

        # Get icons
        action_icon = self.ACTION_ICONS.get(event.action, "📧")
        category_icon = self.CATEGORY_ICONS.get(event.category, "📁")

        # Get color
        color = self.ACTION_COLORS.get(event.action, "white")

        # Build confidence bar
        confidence_bar = self._render_confidence_bar(event.confidence)

        # Truncate preview
        preview = event.preview or ""
        if len(preview) > 80:
            preview = preview[:77] + "..."

        # Build content
        content = Text()
        content.append(f"{action_icon} ", style="bold")
        content.append(f"{(event.action or 'unknown').upper()}", style=f"bold {color}")
        content.append("  ")
        content.append(confidence_bar)
        content.append(f"  {category_icon}\n\n", style="dim")

        content.append(f"{event.subject}\n", style="bold")
        content.append(f"From: {event.from_address}\n", style="dim")

        # Add email date and age
        if event.email_date:
            age = self._format_email_age(event.email_date)
            date_str = event.email_date.strftime("%Y-%m-%d %H:%M")
            content.append(f"Date: {date_str} ({age})\n", style="dim")

        if preview:
            content.append(f"\n{preview}", style="dim italic")

        # Build title
        title = f"Email {event.current}/{event.total}" if event.current and event.total else "Email"

        # Render panel
        self.console.print(Panel(
            content,
            title=title,
            border_style=color,
            padding=(0, 1)
        ))

        logger.debug(f"Displayed email {event.email_id}: {event.subject}")

    def _on_email_queued(self, event: ProcessingEvent) -> None:
        """
        Handle email queued event (low confidence)

        Args:
            event: Email queued event
        """
        self.stats["emails_processed"] += 1
        self.stats["emails_queued"] += 1

        # Build confidence bar
        confidence_bar = self._render_confidence_bar(event.confidence)

        # Build content
        content = Text()
        content.append("📥 ", style="bold")
        content.append("QUEUED FOR REVIEW", style="bold magenta")
        content.append("  ")
        content.append(confidence_bar)
        content.append("\n\n")

        content.append(f"{event.subject}\n", style="bold")
        content.append(f"From: {event.from_address}\n", style="dim")

        # Add email date and age
        if event.email_date:
            age = self._format_email_age(event.email_date)
            date_str = event.email_date.strftime("%Y-%m-%d %H:%M")
            content.append(f"Date: {date_str} ({age})\n", style="dim")

        # Add reason (fixed markup rendering)
        content.append("\nAI confidence below threshold - queued for manual review", style="dim italic")

        # Render panel
        self.console.print(Panel(
            content,
            title="Email Queued",
            border_style="magenta",
            padding=(0, 1)
        ))

        logger.debug(f"Displayed queued email {event.email_id}")

    def _on_email_error(self, event: ProcessingEvent) -> None:
        """
        Handle email error event

        Args:
            event: Email error event
        """
        self.stats["emails_processed"] += 1
        self.stats["emails_errored"] += 1

        # Build content
        content = Text()
        content.append("⚠️  ", style="bold")
        content.append("ERROR", style="bold red")
        content.append("\n\n")

        if event.subject:
            content.append(f"{event.subject}\n", style="bold")
        if event.from_address:
            content.append(f"From: {event.from_address}\n", style="dim")

        # Add email date and age
        if event.email_date:
            age = self._format_email_age(event.email_date)
            date_str = event.email_date.strftime("%Y-%m-%d %H:%M")
            content.append(f"Date: {date_str} ({age})\n", style="dim")

        # Add error details (fixed markup rendering)
        content.append(f"\n{event.error_type or 'Error'}: {event.error or 'Unknown error'}", style="red")

        # Render panel
        self.console.print(Panel(
            content,
            title="Email Error",
            border_style="red",
            padding=(0, 1)
        ))

        logger.debug(f"Displayed error for email {event.email_id}")

    def _on_batch_completed(self, event: ProcessingEvent) -> None:
        """
        Handle batch completion

        Args:
            event: Batch completed event
        """
        stats = event.metadata.get("stats", {})

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold green]✓ Batch Processing Complete[/bold green]\n\n"
            f"Total Emails: {stats.get('total_emails', 0)}\n"
            f"Auto-Executed: {stats.get('emails_auto_executed', 0)}\n"
            f"Queued: {stats.get('emails_queued', 0)}\n"
            f"Errors: {stats.get('emails_errored', 0)}",
            border_style="green"
        ))

        logger.debug("Batch completed event displayed")

    def _show_final_summary(self, _event: Optional[ProcessingEvent] = None) -> None:
        """
        Display final processing summary

        Args:
            event: Optional processing completed event
        """
        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]Processing Summary[/bold cyan]\n\n"
            f"Accounts Processed: {self.stats['accounts_processed']}\n"
            f"Total Emails: {self.stats['emails_processed']}\n"
            f"Auto-Executed: {self.stats['emails_auto_executed']}\n"
            f"Queued for Review: {self.stats['emails_queued']}\n"
            f"Errors: {self.stats['emails_errored']}",
            border_style="cyan"
        ))

        logger.debug("Final summary displayed")

    def _render_confidence_bar(self, confidence: Optional[int]) -> Text:
        """
        Render confidence as a colored bar

        Args:
            confidence: Confidence percentage (0-100)

        Returns:
            Formatted confidence bar with color

        Examples:
            95% → ████ 95% (green)
            75% → ███░ 75% (yellow)
            55% → ██░░ 55% (orange)
            35% → █░░░ 35% (red)
        """
        if confidence is None:
            return Text("░░░░ --", style="dim")

        # Determine color
        color = self._get_confidence_color(confidence)

        # Build bar (4 blocks)
        filled = int((confidence / 100) * 4)
        empty = 4 - filled

        bar = "█" * filled + "░" * empty
        text = Text()
        text.append(f"{bar} {confidence}%", style=color)

        return text

    def _get_confidence_color(self, confidence: int) -> str:
        """
        Get color for confidence level

        Args:
            confidence: Confidence percentage (0-100)

        Returns:
            Color name for Rich

        Examples:
            95 → "green"
            85 → "yellow"
            70 → "orange"
            50 → "red"
        """
        if confidence >= 90:
            return "green"
        elif confidence >= 80:
            return "yellow"
        elif confidence >= 65:
            return "orange"
        else:
            return "red"

    def _format_email_age(self, email_date: Optional[datetime]) -> str:
        """
        Format email age as relative time

        Args:
            email_date: Email sent date

        Returns:
            Human-readable age string

        Examples:
            2 hours ago → "2h ago"
            3 days ago → "3d ago"
            1 month ago → "1mo ago"
        """
        if not email_date:
            return "Unknown age"

        # Ensure both datetimes are timezone-aware for comparison
        now = now_utc()

        # If email_date is naive, assume UTC
        if email_date.tzinfo is None:
            from datetime import timezone
            email_date = email_date.replace(tzinfo=timezone.utc)

        delta = now - email_date

        # Calculate different time units
        seconds = delta.total_seconds()
        minutes = seconds / 60
        hours = minutes / 60
        days = delta.days

        if seconds < 60:
            return "just now"
        elif minutes < 60:
            return f"{int(minutes)}m ago"
        elif hours < 24:
            return f"{int(hours)}h ago"
        elif days < 7:
            return f"{days}d ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks}w ago"
        elif days < 365:
            months = days // 30
            return f"{months}mo ago"
        else:
            years = days // 365
            return f"{years}y ago"

    def clear(self) -> None:
        """Clear console"""
        self.console.clear()

    def print(self, *args, **kwargs) -> None:
        """
        Print to console (passthrough to Rich console)

        Args:
            *args: Positional arguments for console.print()
            **kwargs: Keyword arguments for console.print()
        """
        self.console.print(*args, **kwargs)


def create_display_manager(console: Optional[Console] = None) -> DisplayManager:
    """
    Create and return a DisplayManager instance

    Helper function for easy display manager creation.

    Args:
        console: Optional Rich Console instance

    Returns:
        DisplayManager instance
    """
    return DisplayManager(console=console)
