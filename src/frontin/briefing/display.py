"""
Briefing Display

Rich-based display for briefings with multi-layer information presentation.

Design Philosophy (from DESIGN_PHILOSOPHY.md):
- Layer 1 (5s): Quick overview with icons and counters
- Layer 2 (2min): Detailed item lists with context
- Layer 3 (optional): Full AI reasoning and confidence scores
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.core.events import EventSource
from src.frontin.briefing.models import (
    AttendeeContext,
    BriefingItem,
    MorningBriefing,
    PreMeetingBriefing,
    _extract_display_name,
    _format_duration,
)


class BriefingDisplay:
    """
    Rich-based briefing display

    Renders briefings with multi-layer information hierarchy:
    - Quick overview for 5-second scan
    - Detailed tables for 2-minute review
    - Optional full details and AI insights

    Usage:
        display = BriefingDisplay(console)
        display.render_morning_briefing(briefing)
        display.render_pre_meeting_briefing(pre_meeting)
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        """
        Initialize display with Rich console

        Args:
            console: Rich Console instance (default: new console)
        """
        self.console = console or Console()

    def render_morning_briefing(
        self,
        briefing: MorningBriefing,
        show_details: bool = True,
    ) -> None:
        """
        Render morning briefing in layers

        Args:
            briefing: MorningBriefing to render
            show_details: Whether to show detailed sections
        """
        # Layer 1: Quick Overview (5 sec scan)
        self._render_overview(briefing)

        if not show_details:
            return

        # Layer 2: Urgent Items
        if briefing.urgent_items:
            self.console.print()
            self._render_urgent_items(briefing.urgent_items)

        # Layer 3: Today's Schedule
        if briefing.calendar_today:
            self.console.print()
            self._render_calendar(briefing.calendar_today)

        # Layer 4: Pending Communications
        if briefing.emails_pending or briefing.teams_unread:
            self.console.print()
            self._render_pending(briefing)

        # AI Summary (optional layer 5)
        if briefing.ai_summary:
            self.console.print()
            self._render_summary(briefing.ai_summary)

    def render_pre_meeting_briefing(
        self,
        briefing: PreMeetingBriefing,
        show_details: bool = True,
    ) -> None:
        """
        Render pre-meeting briefing

        Args:
            briefing: PreMeetingBriefing to render
            show_details: Whether to show detailed sections
        """
        # Header with time until meeting
        self._render_meeting_header(briefing)

        if not show_details:
            return

        # Meeting details (URL, location)
        if briefing.meeting_url or briefing.location:
            self.console.print()
            self._render_meeting_details(briefing)

        # Attendees
        if briefing.attendees:
            self.console.print()
            self._render_attendees(briefing.attendees)

        # Recent communications
        if briefing.recent_emails or briefing.recent_teams:
            self.console.print()
            self._render_recent_communications(briefing)

        # Talking points
        if briefing.talking_points:
            self.console.print()
            self._render_talking_points(briefing.talking_points)

    def _render_overview(self, briefing: MorningBriefing) -> None:
        """Render quick stats overview (Layer 1)"""
        overview = Text()

        # Urgent count with color
        if briefing.urgent_count > 0:
            overview.append("  ", style="bold red")
            overview.append(f"{briefing.urgent_count} ", style="bold red")
            overview.append("urgent  ", style="red")

        # Meetings count
        overview.append("  ", style="bold cyan")
        overview.append(f"{briefing.meetings_today} ", style="bold cyan")
        overview.append("meetings  ", style="cyan")

        # Emails count
        email_count = len(briefing.emails_pending)
        if email_count > 0:
            overview.append("  ", style="bold yellow")
            overview.append(f"{email_count} ", style="bold yellow")
            overview.append("emails  ", style="yellow")

        # Teams count
        teams_count = len(briefing.teams_unread)
        if teams_count > 0:
            overview.append("  ", style="bold blue")
            overview.append(f"{teams_count} ", style="bold blue")
            overview.append("teams", style="blue")

        # If no items at all
        if briefing.total_items == 0:
            overview.append("No pending items", style="dim")

        self.console.print(Panel(
            overview,
            title=f"Morning Briefing - {briefing.date.strftime('%A, %B %d')}",
            border_style="green",
        ))

    def _render_urgent_items(self, items: list[BriefingItem]) -> None:
        """Render urgent items table"""
        table = Table(
            title="Urgent Items",
            show_header=True,
            border_style="red",
        )
        table.add_column("Time", style="cyan", width=12)
        table.add_column("Source", width=8)
        table.add_column("Item", style="white", no_wrap=False)
        table.add_column("From", style="dim", width=20, no_wrap=True)

        for item in items:
            source_text = self._source_badge(item.event.source)
            title = _truncate(item.event.title, 50)
            from_name = _extract_display_name(item.event.from_person)

            table.add_row(
                item.time_context,
                source_text,
                title,
                _truncate(from_name, 18),
            )

        self.console.print(table)

    def _render_calendar(self, items: list[BriefingItem]) -> None:
        """Render today's calendar"""
        table = Table(
            title="Today's Schedule",
            show_header=True,
            border_style="cyan",
        )
        table.add_column("Time", style="cyan", width=10)
        table.add_column("Event", style="white", no_wrap=False)
        table.add_column("Duration", style="dim", width=8)
        table.add_column("Attendees", style="dim", width=10, justify="right")

        for item in items:
            meta = item.event.metadata
            duration = meta.get("duration_minutes", 0)
            dur_str = _format_duration(duration)
            attendees = meta.get("attendee_count", 0)
            att_str = str(attendees) if attendees else "-"

            table.add_row(
                item.time_context,
                _truncate(item.event.title, 45),
                dur_str,
                att_str,
            )

        self.console.print(table)

    def _render_pending(self, briefing: MorningBriefing) -> None:
        """Render pending emails and Teams messages"""
        table = Table(
            title="Pending Communications",
            show_header=True,
            border_style="yellow",
        )
        table.add_column("Time", style="dim", width=10)
        table.add_column("Source", width=8)
        table.add_column("From", style="cyan", width=20, no_wrap=True)
        table.add_column("Subject", style="white", no_wrap=False)

        # Add emails
        for item in briefing.emails_pending[:5]:
            from_name = _extract_display_name(item.event.from_person)
            table.add_row(
                item.time_context,
                self._source_badge(EventSource.EMAIL),
                _truncate(from_name, 18),
                _truncate(item.event.title, 40),
            )

        # Add Teams messages
        for item in briefing.teams_unread[:5]:
            from_name = _extract_display_name(item.event.from_person)
            table.add_row(
                item.time_context,
                self._source_badge(EventSource.TEAMS),
                _truncate(from_name, 18),
                _truncate(item.event.title, 40),
            )

        self.console.print(table)

    def _render_summary(self, summary: str) -> None:
        """Render AI summary"""
        self.console.print(Panel(
            summary,
            title="Summary",
            border_style="dim",
        ))

    def _render_meeting_header(self, briefing: PreMeetingBriefing) -> None:
        """Render pre-meeting briefing header"""
        header = Text()
        header.append(briefing.event.title, style="bold white")

        if briefing.minutes_until_start > 0:
            header.append(f"  (in {briefing.minutes_until_start} min)", style="cyan")
        elif briefing.minutes_until_start == 0:
            header.append("  (starting now)", style="yellow bold")
        else:
            header.append("  (in progress)", style="green")

        self.console.print(Panel(
            header,
            title="Pre-Meeting Briefing",
            border_style="cyan",
        ))

    def _render_meeting_details(self, briefing: PreMeetingBriefing) -> None:
        """Render meeting details (URL, location)"""
        if briefing.meeting_url:
            self.console.print(
                f"[bold blue]Join:[/bold blue] {briefing.meeting_url}"
            )
        if briefing.location:
            self.console.print(
                f"[dim]Location:[/dim] {briefing.location}"
            )

    def _render_attendees(self, attendees: list[AttendeeContext]) -> None:
        """Render attendee list with context"""
        table = Table(
            title="Attendees",
            show_header=True,
            border_style="blue",
        )
        table.add_column("Name", style="white", no_wrap=True)
        table.add_column("Role", style="dim", width=12)
        table.add_column("Interactions", style="cyan", width=12, justify="right")
        table.add_column("Context", style="dim", no_wrap=False)

        for att in attendees:
            role = "Organizer" if att.is_organizer else ""
            interactions = str(att.interaction_count) if att.interaction_count > 0 else "-"
            context = att.relationship_hint or ""

            table.add_row(
                _truncate(att.name, 25),
                role,
                interactions,
                context,
            )

        self.console.print(table)

    def _render_recent_communications(
        self,
        briefing: PreMeetingBriefing,
    ) -> None:
        """Render recent communications with attendees"""
        lines: list[str] = []

        if briefing.recent_emails:
            lines.append(
                f"[yellow]{len(briefing.recent_emails)} recent email(s)[/yellow]"
            )

        if briefing.recent_teams:
            lines.append(
                f"[blue]{len(briefing.recent_teams)} recent Teams message(s)[/blue]"
            )

        if lines:
            self.console.print(Panel(
                "\n".join(lines),
                title="Recent Communications",
                border_style="dim",
            ))

    def _render_talking_points(self, points: list[str]) -> None:
        """Render talking points"""
        content = Text()
        for i, point in enumerate(points):
            if i > 0:
                content.append("\n")
            content.append(f"  {point}", style="white")

        self.console.print(Panel(
            content,
            title="Talking Points",
            border_style="green",
        ))

    def _source_badge(self, source: EventSource) -> str:
        """Get styled badge for event source"""
        badges = {
            EventSource.EMAIL: "[yellow]Email[/yellow]",
            EventSource.CALENDAR: "[cyan]Cal[/cyan]",
            EventSource.TEAMS: "[blue]Teams[/blue]",
            EventSource.FILE: "[dim]File[/dim]",
            EventSource.TASK: "[green]Task[/green]",
        }
        return badges.get(source, "[dim]?[/dim]")


def _truncate(text: str, max_length: int) -> str:
    """Truncate text with ellipsis if too long (result is exactly max_length)"""
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return "..."[:max_length]
    return text[:max_length - 3] + "..."
