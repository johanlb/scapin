"""
Scapin CLI Application

Main CLI entry point using Typer and Rich for elegant interface.
"""

import os
from typing import Optional

# Suppress HuggingFace tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.spinner import Spinner
from rich.table import Table

from src.core.config_manager import get_config
from src.core.schemas import ServiceStatus
from src.core.state_manager import get_state_manager
from src.monitoring.health import quick_health_check
from src.monitoring.logger import LogFormat, LogLevel, ScapinLogger, get_logger

# Create Typer apps
app = typer.Typer(
    name="pkm",
    help="Scapin - Intelligent email management system",
    add_completion=False,
)

notes_app = typer.Typer(
    name="notes",
    help="Manage notes and carnets",
    add_completion=False,
)
app.add_typer(notes_app, name="notes")

# Rich console
console = Console()

# Settings validation constants
MIN_CONFIDENCE_THRESHOLD = 0
MAX_CONFIDENCE_THRESHOLD = 100
MIN_RATE_LIMIT = 1
MAX_RATE_LIMIT = 100


def format_health_status(status: ServiceStatus, include_text: bool = True) -> str:
    """
    Format health status with emoji and optional text

    Args:
        status: ServiceStatus enum value
        include_text: If True, include status text (Healthy/Degraded/Unhealthy/Unknown)

    Returns:
        Formatted string with emoji and optional status text
    """
    # Status formatting with emoji
    status_formats = {
        "healthy": {"with_text": "[green]✓ Healthy[/green]", "emoji_only": "[green]✓[/green]"},
        "degraded": {
            "with_text": "[yellow]⚠ Degraded[/yellow]",
            "emoji_only": "[yellow]⚠[/yellow]",
        },
        "unhealthy": {"with_text": "[red]✗ Unhealthy[/red]", "emoji_only": "[red]✗[/red]"},
        "unknown": {"with_text": "[dim]? Unknown[/dim]", "emoji_only": "[dim]?[/dim]"},
    }

    format_key = "with_text" if include_text else "emoji_only"
    return status_formats.get(status.value, status_formats["unknown"])[format_key]


def version_callback(value: bool):
    """Show version and exit"""
    if value:
        console.print("[bold cyan]Scapin[/bold cyan] v2.0.0")
        console.print("Powered by Claude AI")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    _version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging",
    ),
    log_format: str = typer.Option(
        "text",
        "--log-format",
        help="Log format (text or json)",
    ),
):
    """
    Scapin - Intelligent email management

    Process emails with AI, extract knowledge, manage tasks.
    """
    # Configure logging
    level = LogLevel.DEBUG if verbose else LogLevel.INFO
    fmt = LogFormat.JSON if log_format == "json" else LogFormat.TEXT
    ScapinLogger.configure(level=level, format=fmt)

    # Store in context for subcommands
    ctx.obj = {
        "verbose": verbose,
        "log_format": log_format,
    }

    # If no subcommand specified, launch interactive menu
    if ctx.invoked_subcommand is None:
        from src.jeeves.menu import run_interactive_menu

        exit_code = run_interactive_menu()
        raise typer.Exit(code=exit_code)


@app.command()
def process(
    limit: int = typer.Option(None, "--limit", "-n", help="Max emails to process"),
    auto: bool = typer.Option(False, "--auto", help="Auto-process high confidence emails"),
    confidence: int = typer.Option(
        90, "--confidence", "-c", help="Confidence threshold for auto mode"
    ),
    unread_only: bool = typer.Option(
        False, "--unread-only", help="Only process unread emails (UNSEEN flag)"
    ),
    unflagged_only: bool = typer.Option(
        True, "--unflagged-only/--all", help="Only process unflagged emails (default: True)"
    ),
):
    """
    Process emails from inbox

    Analyzes emails and recommends actions (archive, delete, reference, task).
    By default, processes unflagged emails (not marked/starred) from oldest to newest.
    """
    from src.jeeves.display_manager import DisplayManager
    from src.trivelin.processor import EmailProcessor

    console.print(
        Panel.fit("[bold cyan]Scapin[/bold cyan]\nProcessing your inbox...", border_style="cyan")
    )

    mode = "auto" if auto else "manual"
    filters = []
    if unread_only:
        filters.append("unread")
    if unflagged_only:
        filters.append("unflagged")
    filter_str = " + ".join(filters) if filters else "all emails"

    console.print(
        f"[dim]Mode: {mode} | Confidence: {confidence}% | Filter: {filter_str} | Limit: {limit or 'None'}[/dim]\n"
    )

    try:
        # Enable display mode BEFORE initialization to hide all console logs
        ScapinLogger.set_display_mode(True)

        # Initialize display manager
        display = DisplayManager(console)
        display.start()

        # Initialize processor (will log to file only, not console)
        processor = EmailProcessor()

        try:
            # Process emails (events will be displayed by DisplayManager)
            results = processor.process_inbox(
                limit=limit,
                auto_execute=auto,
                confidence_threshold=confidence,
                unread_only=unread_only,
                unflagged_only=unflagged_only,
            )
        finally:
            # Always restore console logs
            ScapinLogger.set_display_mode(False)
            display.stop()

        # Display results
        if results:
            console.print(f"\n[green]✓[/green] Processed {len(results)} emails\n")

            # Create results table
            table = Table(title="Processing Results", show_header=True, header_style="bold")
            table.add_column("Subject", style="cyan", max_width=40)
            table.add_column("From", style="dim", max_width=25)
            table.add_column("Action", justify="center")
            table.add_column("Category", justify="center")
            table.add_column("Confidence", justify="right")

            for email in results[:20]:  # Show first 20
                # Action color
                action_colors = {
                    "ARCHIVE": "green",
                    "DELETE": "red",
                    "TASK": "yellow",
                    "REPLY": "blue",
                    "DEFER": "magenta",
                    "QUEUE": "dim",
                }
                action_color = action_colors.get(email.analysis.action.value, "white")

                table.add_row(
                    email.metadata.subject[:40],
                    email.metadata.from_address[:25],
                    f"[{action_color}]{email.analysis.action.value}[/{action_color}]",
                    email.analysis.category.value,
                    f"{email.analysis.confidence}%",
                )

            console.print(table)

            if len(results) > 20:
                console.print(f"\n[dim]... and {len(results) - 20} more[/dim]")

            # Show statistics
            stats = processor.get_processing_stats()
            console.print("\n[bold]Statistics:[/bold]")
            console.print(f"  • Processed: {stats['emails_processed']}")
            console.print(f"  • Archived: {stats['emails_archived']}")
            console.print(f"  • Deleted: {stats['emails_deleted']}")
            console.print(f"  • Tasks created: {stats['tasks_created']}")
            console.print(f"  • Queued for review: {stats['emails_queued']}")
            console.print(f"  • Average confidence: {stats['average_confidence']:.1f}%")

        else:
            console.print("[yellow]No emails to process[/yellow]")

    except ConnectionError as e:
        console.print(f"\n[red]✗ Connection Error:[/red] {e}")
        console.print("[yellow]Tip:[/yellow] Check your IMAP settings and network connection")
        logger = get_logger("cli")
        logger.error(f"IMAP connection failed: {e}", exc_info=True)
        raise typer.Exit(code=1) from None

    except PermissionError as e:
        console.print(f"\n[red]✗ Permission Error:[/red] {e}")
        console.print("[yellow]Tip:[/yellow] Check your IMAP credentials and app-specific password")
        logger = get_logger("cli")
        logger.error(f"Authentication failed: {e}", exc_info=True)
        raise typer.Exit(code=1) from None

    except ValueError as e:
        console.print(f"\n[red]✗ Configuration Error:[/red] {e}")
        console.print("[yellow]Tip:[/yellow] Check your .env file configuration")
        logger = get_logger("cli")
        logger.error(f"Configuration error: {e}", exc_info=True)
        raise typer.Exit(code=1) from None

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Processing interrupted by user[/yellow]")
        logger = get_logger("cli")
        logger.info("User interrupted processing")
        raise typer.Exit(code=130) from None

    except Exception as e:
        console.print(f"\n[red]✗ Unexpected Error:[/red] {e}")
        console.print(f"[dim]Type: {type(e).__name__}[/dim]")
        console.print("[yellow]Tip:[/yellow] Check logs for more details")
        logger = get_logger("cli")
        logger.error(f"Email processing failed: {e}", exc_info=True)
        raise typer.Exit(code=1) from None


@app.command()
def review(
    _limit: int = typer.Option(20, "--limit", "-n", help="Max decisions to review"),
):
    """
    Review queued emails

    Interactive review of low-confidence emails queued for manual approval.
    """
    from src.jeeves.review_mode import InteractiveReviewMode

    console.print(
        Panel.fit(
            "[bold magenta]📋 Review Queue[/bold magenta]\nLoading queued emails for review...",
            border_style="magenta",
        )
    )

    try:
        review_mode = InteractiveReviewMode()
        exit_code = review_mode.run()
        raise typer.Exit(code=exit_code)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Review cancelled by user[/yellow]")
        raise typer.Exit(code=130) from None

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        logger = get_logger("cli")
        logger.error(f"Review mode failed: {e}", exc_info=True)
        raise typer.Exit(code=1) from None


@app.command()
def journal(
    date_str: Optional[str] = typer.Option(
        None, "--date", "-d", help="Date for journal (YYYY-MM-DD)"
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i", help="Interactive mode with questions"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    output_format: str = typer.Option(
        "markdown", "--format", "-f", help="Output format (markdown or json)"
    ),
):
    """
    Generate and complete daily journal

    Creates a journal entry summarizing the day's email processing,
    asks targeted questions, and collects feedback for learning.
    """
    from datetime import date
    from pathlib import Path

    from rich.markdown import Markdown

    from src.jeeves.journal import (
        JournalGenerator,
        JournalInteractive,
        process_corrections,
    )

    # Parse date
    if date_str:
        try:
            journal_date = date.fromisoformat(date_str)
        except ValueError:
            console.print(f"[red]Invalid date format: {date_str}[/red]")
            console.print("[dim]Expected format: YYYY-MM-DD[/dim]")
            raise typer.Exit(1) from None
    else:
        journal_date = date.today()

    console.print(
        Panel.fit(f"[bold blue]Journal du {journal_date}[/bold blue]", border_style="blue")
    )

    try:
        # Generate draft journal
        generator = JournalGenerator()
        entry = generator.generate(journal_date)

        console.print(f"\n[green]OK[/green] {len(entry.emails_processed)} emails traites")
        console.print(f"[cyan]?[/cyan] {len(entry.questions)} questions")

        # Interactive mode
        if interactive and (entry.questions or entry.emails_processed):
            interactive_session = JournalInteractive(entry)
            entry = interactive_session.run()

        # Process corrections for learning
        if entry.corrections:
            result = process_corrections(entry)
            console.print(
                f"\n[green]OK[/green] {result.corrections_processed} corrections envoyees a Sganarelle"
            )

        # Output
        output_content = entry.to_json() if output_format == "json" else entry.to_markdown()

        if output:
            output_path = Path(output)
            output_path.write_text(output_content, encoding="utf-8")
            console.print(f"\n[green]OK[/green] Sauvegarde dans {output_path}")
        elif not interactive:
            # Only print output if not interactive (already shown in interactive mode)
            console.print()
            console.print(Markdown(output_content))

    except KeyboardInterrupt:
        console.print("\n[yellow]Journal interrompu[/yellow]")
        raise typer.Exit(130) from None

    except Exception as e:
        console.print(f"\n[red]Erreur: {e}[/red]")
        logger = get_logger("cli")
        logger.error(f"Journal command failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


@app.command()
def teams(
    poll: bool = typer.Option(False, "--poll", "-p", help="Continuous polling mode"),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i", help="Interactive review mode"
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum messages per poll"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only fetch messages after this datetime (ISO format)"
    ),
):
    """
    Process Microsoft Teams messages

    Fetches and processes Teams messages through the cognitive pipeline.
    Requires Microsoft account configuration in .env.
    """
    import asyncio
    from datetime import datetime

    from src.core.config_manager import get_config
    from src.trivelin.teams_processor import TeamsProcessor

    # Check if Teams is enabled
    config = get_config()
    if not config.teams.enabled:
        console.print("[red]Teams integration is not enabled[/red]")
        console.print("\n[yellow]To enable Teams integration:[/yellow]")
        console.print("  1. Create an Azure AD app registration")
        console.print("  2. Add these settings to your .env file:")
        console.print("     TEAMS__ENABLED=true")
        console.print("     TEAMS__ACCOUNT__CLIENT_ID=your-client-id")
        console.print("     TEAMS__ACCOUNT__TENANT_ID=your-tenant-id")
        console.print("\n[dim]See ROADMAP.md Phase 1.2 for details[/dim]")
        raise typer.Exit(1)

    console.print(
        Panel.fit("[bold blue]Microsoft Teams Integration[/bold blue]", border_style="blue")
    )

    # Parse since datetime if provided (validates format, TODO: pass to processor)
    if since:
        try:
            datetime.fromisoformat(since)  # Validate format
        except ValueError:
            console.print(f"[red]Invalid datetime format: {since}[/red]")
            console.print("[dim]Expected format: YYYY-MM-DDTHH:MM:SS[/dim]")
            raise typer.Exit(1) from None

    try:
        # Initialize processor
        processor = TeamsProcessor()

        if poll:
            # Continuous polling mode
            console.print(
                f"[green]Polling every {config.teams.poll_interval_seconds}s. Press Ctrl+C to stop.[/green]\n"
            )

            async def poll_loop():
                while True:
                    try:
                        summary = await processor.poll_and_process(limit=limit)
                        if summary.total > 0:
                            console.print(
                                f"[cyan]Processed {summary.successful}/{summary.total} messages "
                                f"({summary.failed} failed, {summary.skipped} skipped)[/cyan]"
                            )
                        await asyncio.sleep(config.teams.poll_interval_seconds)
                    except KeyboardInterrupt:
                        break

            asyncio.run(poll_loop())
            console.print("\n[yellow]Polling stopped[/yellow]")

        else:
            # Single run
            console.print("[dim]Fetching Teams messages...[/dim]\n")

            async def single_run():
                return await processor.poll_and_process(limit=limit)

            summary = asyncio.run(single_run())

            # Display results
            if summary.total == 0:
                console.print("[dim]No new messages to process[/dim]")
            else:
                console.print(
                    f"[green]OK[/green] Processed {summary.successful}/{summary.total} messages"
                )
                if summary.failed > 0:
                    console.print(f"[red]Failed: {summary.failed}[/red]")
                if summary.skipped > 0:
                    console.print(f"[dim]Skipped: {summary.skipped}[/dim]")

                # Show results table if interactive
                if interactive and summary.results:
                    from rich.table import Table

                    table = Table(title="Processing Results", show_header=True)
                    table.add_column("Message ID", style="cyan", max_width=20)
                    table.add_column("Status")
                    table.add_column("Actions")

                    for result in summary.results[:20]:  # Limit to 20 rows
                        status = (
                            "[green]OK[/green]"
                            if result.success
                            else "[yellow]Skipped[/yellow]"
                            if result.skipped
                            else "[red]Failed[/red]"
                        )
                        actions = ", ".join(result.actions_taken) if result.actions_taken else "-"
                        table.add_row(
                            result.message_id[:20],
                            status,
                            actions,
                        )

                    console.print(table)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise typer.Exit(130) from None

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger = get_logger("cli")
        logger.error(f"Teams command failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


@app.command()
def calendar(
    poll: bool = typer.Option(False, "--poll", "-p", help="Continuous polling mode"),
    briefing: bool = typer.Option(
        False, "--briefing", "-b", help="Show briefing of upcoming events"
    ),
    hours: int = typer.Option(24, "--hours", "-H", help="Hours ahead for briefing (default: 24)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum events per poll"),
):
    """
    Process Microsoft Calendar events

    Fetches and processes Calendar events through the cognitive pipeline.
    Use --briefing to see upcoming events for the day.
    Requires Microsoft account configuration in .env.
    """
    import asyncio

    from src.core.config_manager import get_config
    from src.trivelin.calendar_processor import CalendarProcessor

    # Check if Calendar is enabled
    config = get_config()
    if not config.calendar.enabled:
        console.print("[red]Calendar integration is not enabled[/red]")
        console.print("\n[yellow]To enable Calendar integration:[/yellow]")
        console.print("  1. Create an Azure AD app registration (or reuse Teams app)")
        console.print("  2. Add these settings to your .env file:")
        console.print("     CALENDAR__ENABLED=true")
        console.print("     CALENDAR__ACCOUNT__CLIENT_ID=your-client-id")
        console.print("     CALENDAR__ACCOUNT__TENANT_ID=your-tenant-id")
        console.print("\n[dim]See ROADMAP.md Phase 1.3 for details[/dim]")
        raise typer.Exit(1)

    console.print(
        Panel.fit("[bold green]Microsoft Calendar Integration[/bold green]", border_style="green")
    )

    try:
        # Initialize processor
        processor = CalendarProcessor()

        if briefing:
            # Show briefing of upcoming events
            console.print(f"[dim]Fetching events for next {hours} hours...[/dim]\n")

            async def get_briefing():
                return await processor.get_briefing(hours_ahead=hours)

            events = asyncio.run(get_briefing())

            if not events:
                console.print("[dim]No upcoming events[/dim]")
            else:
                from rich.table import Table

                table = Table(title=f"Upcoming Events (Next {hours}h)", show_header=True)
                table.add_column("Time", style="cyan", width=12)
                table.add_column("Subject", style="white", max_width=40)
                table.add_column("Duration", style="dim", width=8)
                table.add_column("Attendees", style="dim", width=8)
                table.add_column("Status", width=10)

                for event in events:
                    # Extract info from metadata
                    meta = event.metadata
                    is_all_day = meta.get("is_all_day", False)
                    duration = meta.get("duration_minutes", 0)
                    attendee_count = meta.get("attendee_count", 0)
                    response = meta.get("response_status", "none")
                    is_online = meta.get("is_online", False)

                    # Format time - use start from metadata, not occurred_at
                    # (occurred_at is when we received the notification, not event start)
                    if is_all_day:
                        time_str = "All Day"
                    else:
                        start_str = meta.get("start", "")
                        if start_str:
                            from datetime import datetime

                            start_dt = datetime.fromisoformat(start_str)
                            time_str = start_dt.strftime("%H:%M")
                        else:
                            time_str = "--:--"

                    # Format duration
                    if duration <= 0:
                        dur_str = "-"
                    elif duration >= 60:
                        dur_str = f"{duration // 60}h{duration % 60:02d}m"
                    else:
                        dur_str = f"{duration}m"

                    # Format status with color
                    if response == "accepted":
                        status = "[green]Accepted[/green]"
                    elif response == "tentativelyAccepted":
                        status = "[yellow]Tentative[/yellow]"
                    elif response == "declined":
                        status = "[red]Declined[/red]"
                    elif response == "notResponded":
                        status = "[cyan]Pending[/cyan]"
                    else:
                        status = "[dim]Organizer[/dim]"

                    # Add online indicator
                    subject = event.title
                    if is_online:
                        subject = f"[blue]●[/blue] {subject}"

                    table.add_row(
                        time_str,
                        subject[:40],
                        dur_str,
                        str(attendee_count) if attendee_count > 0 else "-",
                        status,
                    )

                console.print(table)
                console.print(f"\n[dim]Total: {len(events)} events[/dim]")

        elif poll:
            # Continuous polling mode
            console.print(
                f"[green]Polling every {config.calendar.poll_interval_seconds}s. Press Ctrl+C to stop.[/green]\n"
            )

            async def poll_loop():
                while True:
                    try:
                        summary = await processor.poll_and_process(limit=limit)
                        if summary.total > 0:
                            console.print(
                                f"[cyan]Processed {summary.successful}/{summary.total} events "
                                f"({summary.failed} failed, {summary.skipped} skipped)[/cyan]"
                            )
                        await asyncio.sleep(config.calendar.poll_interval_seconds)
                    except KeyboardInterrupt:
                        break

            asyncio.run(poll_loop())
            console.print("\n[yellow]Polling stopped[/yellow]")

        else:
            # Single run
            console.print("[dim]Fetching Calendar events...[/dim]\n")

            async def single_run():
                return await processor.poll_and_process(limit=limit)

            summary = asyncio.run(single_run())

            # Display results
            if summary.total == 0:
                console.print("[dim]No events to process[/dim]")
            else:
                console.print(
                    f"[green]OK[/green] Processed {summary.successful}/{summary.total} events"
                )
                if summary.failed > 0:
                    console.print(f"[red]Failed: {summary.failed}[/red]")
                if summary.skipped > 0:
                    console.print(f"[dim]Skipped: {summary.skipped}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise typer.Exit(130) from None

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger = get_logger("cli")
        logger.error(f"Calendar command failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


@app.command()
def queue(
    process_queue: bool = typer.Option(False, "--process", "-p", help="Process queued items"),
    clear: bool = typer.Option(False, "--clear", help="Clear the queue (destructive!)"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Filter by account ID"),
):
    """
    Manage review queue

    View queue statistics and manage queued emails awaiting review.
    """
    from src.integrations.storage.queue_storage import get_queue_storage
    from src.jeeves.review_mode import InteractiveReviewMode

    queue_storage = get_queue_storage()

    if clear:
        # Clear queue with confirmation
        if not typer.confirm(
            f"⚠️  Clear queue{f' for account {account}' if account else ''}? This cannot be undone!",
            default=False,
        ):
            console.print("[yellow]Cancelled[/yellow]")
            return

        deleted = queue_storage.clear_queue(account_id=account)
        console.print(f"[green]✓ Cleared {deleted} items from queue[/green]")
        return

    if process_queue:
        # Launch review mode
        console.print(
            Panel.fit("[bold yellow]📋 Processing Queue[/bold yellow]", border_style="yellow")
        )

        try:
            review_mode = InteractiveReviewMode()
            exit_code = review_mode.run()
            raise typer.Exit(code=exit_code)
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            raise typer.Exit(code=1) from None

    # Show queue stats
    console.print(Panel.fit("[bold yellow]📋 Queue Status[/bold yellow]", border_style="yellow"))

    stats = queue_storage.get_stats()

    if stats["total"] == 0:
        console.print("\n[dim]Queue is empty[/dim]\n")
        return

    # Create stats table
    table = Table(title="Queue Statistics", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Items", str(stats["total"]))

    # By status
    for status, count in stats["by_status"].items():
        table.add_row(f"  {status.title()}", str(count))

    console.print(table)

    # By account
    if stats["by_account"]:
        console.print("\n[bold]By Account:[/bold]")
        for acc_id, count in stats["by_account"].items():
            console.print(f"  {acc_id}: {count}")

    # Oldest/newest
    if stats["oldest_item"]:
        console.print(f"\n[dim]Oldest: {stats['oldest_item']}[/dim]")
        console.print(f"[dim]Newest: {stats['newest_item']}[/dim]")

    console.print("\n[cyan]Tip:[/cyan] Run [bold]pkm review[/bold] to process the queue")
    console.print()


@app.command()
def secrets(
    migrate: bool = typer.Option(False, "--migrate", help="Migrate secrets from .env to keychain"),
    list_keys: bool = typer.Option(False, "--list", help="List stored secrets"),
):
    """
    Manage secure credential storage

    Store API keys and passwords securely in macOS Keychain instead of .env file.
    """
    from src.core.secrets import (
        KEYRING_AVAILABLE,
        get_secret,
        migrate_from_env_to_keychain,
    )

    if not KEYRING_AVAILABLE:
        console.print("[red]✗ Keyring not available[/red]")
        console.print("Install with: [cyan]pip install keyring[/cyan]")
        raise typer.Exit(code=1)

    if migrate:
        console.print(
            Panel.fit(
                "[bold magenta]Migrate Secrets to Keychain[/bold magenta]\n"
                "Moving credentials from .env to secure storage...",
                border_style="magenta",
            )
        )

        # List of secrets to migrate
        secrets_to_migrate = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "MISTRAL_API_KEY",
            "IMAP_PASSWORD",
        ]

        results = migrate_from_env_to_keychain(secrets_to_migrate)

        # Display results
        console.print("\n[bold]Migration Results:[/bold]\n")
        for key, success in results.items():
            if success:
                console.print(f"  [green]✓[/green] {key}")
            else:
                console.print(f"  [red]✗[/red] {key} (not found in .env)")

        # Show next steps
        successful = sum(1 for s in results.values() if s)
        if successful > 0:
            console.print(f"\n[green]✓[/green] Migrated {successful} secrets to keychain")
            console.print("\n[yellow]Next steps:[/yellow]")
            console.print(
                "  1. Verify secrets are accessible: [cyan]python3 pkm.py secrets --list[/cyan]"
            )
            console.print("  2. Remove migrated secrets from .env file for better security")
            console.print(
                "  3. The app will automatically use keychain first, then fallback to .env"
            )

    elif list_keys:
        console.print("[bold]Checking stored secrets...[/bold]\n")

        secrets_to_check = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "MISTRAL_API_KEY",
            "IMAP_PASSWORD",
        ]

        for key in secrets_to_check:
            value = get_secret(key)
            if value:
                # Mask the value
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                console.print(f"  [green]✓[/green] {key}: {masked}")
            else:
                console.print(f"  [dim]○[/dim] {key}: [dim]not set[/dim]")

    else:
        console.print(
            "[yellow]Use --migrate to migrate secrets or --list to view stored secrets[/yellow]"
        )


@app.command()
def health():
    """
    Check system health

    Verifies all system components (IMAP, AI, storage, config, git).
    """
    console.print(Panel.fit("[bold green]System Health Check[/bold green]", border_style="green"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Checking system health...", total=None)

        # Run health checks
        system_health = quick_health_check()

        progress.update(task, completed=True)

    # Display results in table
    table = Table(title="Health Check Results", show_header=True, header_style="bold")
    table.add_column("Service", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Message")
    table.add_column("Response Time", justify="right")

    for check in system_health.checks:
        # Status emoji and color
        status = format_health_status(check.status, include_text=True)

        # Response time
        response_time = f"{check.response_time_ms:.0f}ms" if check.response_time_ms else "N/A"

        table.add_row(check.service, status, check.message, response_time)

    console.print(table)

    # Overall status
    if system_health.is_healthy:
        console.print("\n[green]✓ All systems healthy[/green]")
    else:
        console.print(f"\n[red]✗ {len(system_health.unhealthy_services)} services unhealthy[/red]")
        for service in system_health.unhealthy_services:
            console.print(f"  [red]•[/red] {service}")


@app.command()
def stats(
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed statistics"),
    include_queue: bool = typer.Option(True, "--queue/--no-queue", help="Include queue statistics"),
    include_health: bool = typer.Option(
        True, "--health/--no-health", help="Include health summary"
    ),
):
    """
    Show comprehensive statistics

    Display session stats, queue status, health summary, and processing metrics.
    """
    console.print(Panel.fit("[bold blue]📊 System Statistics[/bold blue]", border_style="blue"))

    # Session Statistics
    console.print("\n[bold cyan]Session Statistics:[/bold cyan]\n")

    state = get_state_manager()
    state_dict = state.to_dict()
    session_stats = state_dict.get("stats", {})

    session_table = Table(show_header=False, box=None)
    session_table.add_column("Metric", style="cyan")
    session_table.add_column("Value", justify="right", style="bold")

    session_table.add_row("Emails Processed", str(session_stats.get("emails_processed", 0)))
    session_table.add_row("Emails Skipped", str(session_stats.get("emails_skipped", 0)))
    session_table.add_row("Auto Executed", str(session_stats.get("emails_auto_executed", 0)))
    session_table.add_row("Queued for Review", str(session_stats.get("emails_queued", 0)))

    console.print(session_table)

    # Actions breakdown
    if detailed:
        console.print("\n[bold cyan]Actions Breakdown:[/bold cyan]\n")

        actions_table = Table(show_header=False, box=None)
        actions_table.add_column("Action", style="cyan")
        actions_table.add_column("Count", justify="right", style="bold")

        actions_table.add_row("📦 Archived", str(session_stats.get("archived", 0)))
        actions_table.add_row("🗑️  Deleted", str(session_stats.get("deleted", 0)))
        actions_table.add_row("📚 Referenced", str(session_stats.get("referenced", 0)))
        actions_table.add_row("✅ Tasks Created", str(session_stats.get("tasks_created", 0)))
        actions_table.add_row("↩️  Replies Needed", str(session_stats.get("replies_needed", 0)))

        console.print(actions_table)

        # Confidence metrics
        console.print("\n[bold cyan]Confidence Metrics:[/bold cyan]\n")
        confidence_table = Table(show_header=False, box=None)
        confidence_table.add_column("Metric", style="cyan")
        confidence_table.add_column("Value", justify="right", style="bold")

        confidence_table.add_row(
            "Average Confidence", f"{session_stats.get('confidence_avg', 0):.1f}%"
        )

        console.print(confidence_table)

    # Queue Statistics
    if include_queue:
        from src.integrations.storage.queue_storage import get_queue_storage

        console.print("\n[bold cyan]Queue Status:[/bold cyan]\n")

        queue_storage = get_queue_storage()
        queue_stats = queue_storage.get_stats()

        queue_table = Table(show_header=False, box=None)
        queue_table.add_column("Metric", style="cyan")
        queue_table.add_column("Value", justify="right", style="bold")

        queue_table.add_row("Total Items", str(queue_stats.get("total", 0)))
        queue_table.add_row(
            "Pending Review", str(queue_stats.get("by_status", {}).get("pending", 0))
        )
        queue_table.add_row("Approved", str(queue_stats.get("by_status", {}).get("approved", 0)))
        queue_table.add_row("Rejected", str(queue_stats.get("by_status", {}).get("rejected", 0)))

        console.print(queue_table)

        if queue_stats.get("oldest_item"):
            console.print(f"\n[dim]Oldest queued: {queue_stats['oldest_item']}[/dim]")

    # Health Summary
    if include_health:
        console.print("\n[bold cyan]System Health:[/bold cyan]\n")

        try:
            # Show spinner while checking health (can take a few seconds)
            with Live(
                Spinner("dots", text="[dim]Checking system health...[/dim]"),
                console=console,
                transient=True,
            ):
                system_health = quick_health_check()

            health_table = Table(show_header=False, box=None)
            health_table.add_column("Service", style="cyan")
            health_table.add_column("Status", justify="center")

            for check in system_health.checks:
                status = format_health_status(check.status, include_text=False)

                health_table.add_row(check.service.title(), status)

            console.print(health_table)

            if system_health.is_healthy:
                console.print("\n[green]All systems operational[/green]")
            else:
                console.print(
                    f"\n[yellow]⚠ {len(system_health.unhealthy_services)} services need attention[/yellow]"
                )

        except Exception as e:
            console.print(f"[yellow]⚠ Could not fetch health status: {e}[/yellow]")

    # Processing state
    console.print(
        f"\n[dim]State: {state_dict.get('processing_state', 'idle')} | Duration: {session_stats.get('duration_minutes', 0)} min[/dim]"
    )
    console.print()


@app.command()
def menu():
    """
    Launch interactive menu

    Interactive menu with arrow-key navigation for email processing,
    review queue, statistics, and settings.
    """
    from src.jeeves.menu import run_interactive_menu

    exit_code = run_interactive_menu()
    raise typer.Exit(code=exit_code)


@app.command()
def config(
    validate: bool = typer.Option(False, "--validate", help="Validate configuration"),
):
    """
    Show or validate configuration

    Display current configuration and validate settings.
    """
    console.print(Panel.fit("[bold cyan]Configuration[/bold cyan]", border_style="cyan"))

    try:
        cfg = get_config()

        if validate:
            console.print("[green]✓ Configuration is valid[/green]\n")

        # Show email accounts
        enabled_accounts = cfg.email.get_enabled_accounts()
        console.print(f"\n[bold cyan]Email Accounts:[/bold cyan] {len(enabled_accounts)} enabled\n")

        for account in enabled_accounts:
            account_table = Table(show_header=False, box=None, padding=(0, 2))
            account_table.add_column("Key", style="dim")
            account_table.add_column("Value")

            account_table.add_row("Account ID", account.account_id)
            account_table.add_row("Account Name", account.account_name)
            account_table.add_row("IMAP Host", account.imap_host)
            account_table.add_row("IMAP Port", str(account.imap_port))
            account_table.add_row("Username", str(account.imap_username))
            account_table.add_row("Max Workers", str(account.max_workers))
            account_table.add_row("Batch Size", str(account.batch_size))

            console.print(
                Panel(
                    account_table, title=f"[bold]{account.account_name}[/bold]", border_style="cyan"
                )
            )

        # AI config
        console.print("\n[bold cyan]AI Configuration:[/bold cyan]\n")
        ai_table = Table(show_header=False, box=None)
        ai_table.add_column("Key", style="dim")
        ai_table.add_column("Value")
        ai_table.add_row("Confidence Threshold", f"{cfg.ai.confidence_threshold}%")
        ai_table.add_row("Rate Limit", f"{cfg.ai.rate_limit_per_minute}/min")
        console.print(ai_table)

        # Storage
        console.print("\n[bold cyan]Storage:[/bold cyan]\n")
        storage_table = Table(show_header=False, box=None)
        storage_table.add_column("Key", style="dim")
        storage_table.add_column("Value")
        storage_table.add_row("Database", str(cfg.storage.database_path))
        storage_table.add_row("Notes Path", str(cfg.storage.notes_path))
        storage_table.add_row("Backup Enabled", "Yes" if cfg.storage.backup_enabled else "No")
        console.print(storage_table)

        # Integrations
        console.print("\n[bold cyan]Integrations:[/bold cyan]\n")
        integrations_table = Table(show_header=False, box=None)
        integrations_table.add_column("Key", style="dim")
        integrations_table.add_column("Value")
        integrations_table.add_row(
            "OmniFocus", "Enabled" if cfg.integrations.omnifocus_enabled else "Disabled"
        )
        integrations_table.add_row(
            "Apple Notes Sync",
            "Enabled" if cfg.integrations.apple_notes_sync_enabled else "Disabled",
        )
        integrations_table.add_row("Sync Interval", f"{cfg.integrations.sync_interval_minutes} min")
        console.print(integrations_table)

    except Exception as e:
        console.print(f"[red]✗ Configuration error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def settings(
    set_confidence: Optional[int] = typer.Option(
        None, "--set-confidence", help="Set AI confidence threshold (0-100)"
    ),
    set_rate_limit: Optional[int] = typer.Option(
        None, "--set-rate-limit", help="Set AI rate limit (requests/min)"
    ),
    list_accounts: bool = typer.Option(False, "--list-accounts", help="List all email accounts"),
    enable_account: Optional[str] = typer.Option(
        None, "--enable-account", help="Enable account by ID"
    ),
    disable_account: Optional[str] = typer.Option(
        None, "--disable-account", help="Disable account by ID"
    ),
):
    """
    Manage application settings

    Modify AI settings, manage accounts, and configure integrations.
    """
    console.print(
        Panel.fit("[bold magenta]⚙ Settings Management[/bold magenta]", border_style="magenta")
    )

    try:
        cfg = get_config()

        # List accounts
        if list_accounts:
            console.print("\n[bold cyan]Email Accounts:[/bold cyan]\n")

            accounts_table = Table(show_header=True, header_style="bold")
            accounts_table.add_column("ID", style="cyan")
            accounts_table.add_column("Name")
            accounts_table.add_column("Email")
            accounts_table.add_column("Host")
            accounts_table.add_column("Status")

            for account in cfg.email.accounts:
                status = "[green]Enabled[/green]" if account.enabled else "[dim]Disabled[/dim]"
                accounts_table.add_row(
                    account.account_id,
                    account.account_name,
                    str(account.imap_username),
                    account.imap_host,
                    status,
                )

            console.print(accounts_table)
            console.print()
            return

        # Set confidence threshold
        if set_confidence is not None:
            if not (MIN_CONFIDENCE_THRESHOLD <= set_confidence <= MAX_CONFIDENCE_THRESHOLD):
                console.print(
                    f"[red]✗ Confidence threshold must be between {MIN_CONFIDENCE_THRESHOLD} and {MAX_CONFIDENCE_THRESHOLD}[/red]"
                )
                raise typer.Exit(1)

            console.print(f"[yellow]Setting confidence threshold to {set_confidence}%...[/yellow]")
            console.print("[yellow]Note: This requires updating .env file:[/yellow]")
            console.print(f"  AI__CONFIDENCE_THRESHOLD={set_confidence}")
            console.print("\n[dim]Please update your .env file manually for now[/dim]")
            return

        # Set rate limit
        if set_rate_limit is not None:
            if not (MIN_RATE_LIMIT <= set_rate_limit <= MAX_RATE_LIMIT):
                console.print(
                    f"[red]✗ Rate limit must be between {MIN_RATE_LIMIT} and {MAX_RATE_LIMIT}[/red]"
                )
                raise typer.Exit(1)

            console.print(
                f"[yellow]Setting rate limit to {set_rate_limit} requests/min...[/yellow]"
            )
            console.print("[yellow]Note: This requires updating .env file:[/yellow]")
            console.print(f"  AI__RATE_LIMIT_PER_MINUTE={set_rate_limit}")
            console.print("\n[dim]Please update your .env file manually for now[/dim]")
            return

        # Enable/disable account
        if enable_account or disable_account:
            account_id_to_modify = enable_account or disable_account
            new_status = "true" if enable_account else "false"

            # Validate account exists
            account = cfg.email.get_account(account_id_to_modify)
            if not account:
                console.print(f"[red]✗ Account '{account_id_to_modify}' not found[/red]\n")
                console.print("Available accounts:")
                for acc in cfg.email.accounts:
                    console.print(f"  - {acc.account_id} ({acc.account_name})")
                raise typer.Exit(1)

            # Find the account index
            account_index = next(
                i
                for i, acc in enumerate(cfg.email.accounts)
                if acc.account_id == account_id_to_modify
            )

            console.print(
                "[yellow]Note: Account enable/disable requires updating .env file:[/yellow]"
            )
            console.print(f"  EMAIL__ACCOUNTS__{account_index}__ENABLED={new_status}")
            console.print(
                f"\n[dim]This will {'enable' if enable_account else 'disable'} account: {account.account_name}[/dim]"
            )
            console.print(
                "[dim]Please update your .env file manually and restart the application[/dim]"
            )
            return

        # No options provided - show current settings summary
        console.print("\n[bold cyan]Current Settings:[/bold cyan]\n")

        settings_table = Table(show_header=False, box=None)
        settings_table.add_column("Setting", style="cyan")
        settings_table.add_column("Value", style="bold")

        settings_table.add_row("AI Confidence Threshold", f"{cfg.ai.confidence_threshold}%")
        settings_table.add_row("AI Rate Limit", f"{cfg.ai.rate_limit_per_minute} requests/min")
        settings_table.add_row("Email Accounts", f"{len(cfg.email.get_enabled_accounts())} enabled")
        settings_table.add_row(
            "OmniFocus Integration", "Enabled" if cfg.integrations.omnifocus_enabled else "Disabled"
        )
        settings_table.add_row("Backup Enabled", "Yes" if cfg.storage.backup_enabled else "No")

        console.print(settings_table)

        console.print("\n[dim]Use --help to see available options for modifying settings[/dim]")
        console.print()

    except Exception as e:
        console.print(f"[red]✗ Settings error: {e}[/red]")
        logger = get_logger("cli")
        logger.error(f"Settings command failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


@app.command()
def briefing(
    morning: bool = typer.Option(False, "--morning", "-m", help="Generate morning briefing"),
    meeting: Optional[str] = typer.Option(
        None, "--meeting", "-M", help="Pre-meeting briefing for event ID"
    ),
    hours: int = typer.Option(24, "--hours", "-H", help="Hours ahead for calendar events"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save briefing to file (markdown)"
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Show only overview (no details)"),
):
    """
    Generate intelligent briefings

    Morning briefing: Synthesizes calendar, emails, and Teams for the day.
    Pre-meeting briefing: Provides context for an upcoming meeting.

    Examples:
        scapin briefing --morning
        scapin briefing --morning --hours 48
        scapin briefing --meeting "event123"
        scapin briefing --morning --output today.md
    """
    import asyncio
    from pathlib import Path

    from src.core.config_manager import get_config
    from src.jeeves.briefing import BriefingDisplay, BriefingGenerator

    config = get_config()

    if not config.briefing.enabled:
        console.print("[red]Briefing system is not enabled[/red]")
        console.print("\n[yellow]To enable briefing system:[/yellow]")
        console.print("  Add to your .env file:")
        console.print("     BRIEFING__ENABLED=true")
        raise typer.Exit(1)

    generator = BriefingGenerator(config=config.briefing)
    display = BriefingDisplay(console)

    try:
        if morning or (not meeting):
            # Morning briefing (default if no option provided)
            console.print(Panel.fit("[bold cyan]Morning Briefing[/bold cyan]", border_style="cyan"))

            # Override hours if provided
            if hours != 24:
                generator.config = config.briefing.model_copy(update={"morning_hours_ahead": hours})

            async def generate_morning():
                return await generator.generate_morning_briefing()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Generating briefing...", total=None)
                briefing_result = asyncio.run(generate_morning())

            # Display
            display.render_morning_briefing(
                briefing_result,
                show_details=not quiet,
            )

            # Save to file if requested
            if output:
                output_path = Path(output)
                output_path.write_text(briefing_result.to_markdown())
                console.print(f"\n[dim]Saved to {output}[/dim]")

        elif meeting:
            # Pre-meeting briefing
            console.print(
                Panel.fit("[bold cyan]Pre-Meeting Briefing[/bold cyan]", border_style="cyan")
            )

            from src.trivelin.calendar_processor import CalendarProcessor

            async def generate_pre_meeting():
                processor = CalendarProcessor()
                event = await processor.get_event(meeting)
                return await generator.generate_pre_meeting_briefing(event)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Fetching meeting context...", total=None)
                briefing_result = asyncio.run(generate_pre_meeting())

            # Display
            display.render_pre_meeting_briefing(
                briefing_result,
                show_details=not quiet,
            )

            # Save to file if requested
            if output:
                output_path = Path(output)
                output_path.write_text(briefing_result.to_markdown())
                console.print(f"\n[dim]Saved to {output}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise typer.Exit(130) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger = get_logger("cli")
        logger.error(f"Briefing command failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-H", help="API host"),
    port: int = typer.Option(8000, "--port", "-p", help="API port"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development"),
):
    """
    Start the Scapin API server

    Launches a FastAPI server exposing all Scapin functionality via REST API.

    Examples:
        scapin serve                    # Start on default port 8000
        scapin serve --port 8080        # Start on custom port
        scapin serve --reload           # Development mode with auto-reload
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[red]FastAPI/Uvicorn not installed[/red]")
        console.print("Install with: [cyan]pip install fastapi uvicorn[/cyan]")
        raise typer.Exit(1) from None

    console.print(
        Panel.fit(
            f"[bold green]Starting Scapin API[/bold green]\n\n"
            f"Host: [cyan]{host}:{port}[/cyan]\n"
            f"Docs: [cyan]http://{host}:{port}/docs[/cyan]\n"
            f"Health: [cyan]http://{host}:{port}/api/health[/cyan]",
            border_style="green",
        )
    )

    try:
        uvicorn.run(
            "src.jeeves.api.app:app",
            host=host,
            port=port,
            reload=reload,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Server error: {e}[/red]")
        raise typer.Exit(1) from None


@notes_app.command(name="review")
def notes_review(
    all_notes: bool = typer.Option(
        False, "--all", "-a", help="Schedule notes for immediate review"
    ),
    limit: int = typer.Option(None, "--limit", "-l", help="Limit number of notes to process"),
    process: bool = typer.Option(
        False, "--process", "-p", help="Actually run the review logic now (CLI mode)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Bypass SM-2 and process even if not due"
    ),
):
    """
    Batch review existing notes to trigger the Reflection Loop.

    Schedules notes for review and optionally processes them through Sancho
    to generate briefing enrichments and note updates.
    Always starts with the least recently modified notes.
    """
    import asyncio
    from pathlib import Path

    from src.core.config_manager import get_config
    from src.passepartout.note_manager import NoteManager
    from src.passepartout.note_reviewer import NoteReviewer
    from src.passepartout.note_scheduler import create_scheduler
    from src.sancho.router import AIRouter

    logger = get_logger("cli")
    config = get_config()
    notes_dir = Path(config.storage.notes_path)
    manager = NoteManager(notes_dir)
    scheduler = create_scheduler(config.storage.database_path.parent)

    console.print(
        Panel.fit("[bold cyan]Batch Note Review & Reflection[/bold cyan]", border_style="cyan")
    )

    # 1. Fetch metadata and sort by updated_at ASC (oldest first)
    console.print("[dim]Scanning vault metadata...[/dim]")
    # We use list_all from the metadata store because it's MUCH faster than reading all files
    all_meta = scheduler.store.list_all(limit=10000)

    # Fallback: if metadata store is empty, use NoteManager (slower but necessary for first run)
    if not all_meta:
        console.print(
            "[yellow]Metadata store is empty. Scanning all notes (this may take a moment)...[/yellow]"
        )
        all_notes_objs = manager.get_all_notes()
        sorted_notes = sorted(all_notes_objs, key=lambda n: n.updated_at)
        # Convert to a simple structure with note_id and updated_at for consistency
        sorted_meta = [
            type("obj", (object,), {"note_id": n.note_id, "updated_at": n.updated_at})()
            for n in sorted_notes
        ]
    else:
        # Sort by updated_at (oldest first)
        sorted_meta = sorted(all_meta, key=lambda m: m.updated_at)

    # Apply limit if we are ONLY scheduling
    items_to_schedule = sorted_meta
    if limit and all_notes and not process:
        items_to_schedule = sorted_meta[:limit]

    if all_notes:
        console.print(
            f"[cyan]Scheduling {len(items_to_schedule)} notes for review (oldest first)...[/cyan]"
        )
        for meta in items_to_schedule:
            scheduler.trigger_immediate_review(meta.note_id)
        console.print(f"[green]Done. {len(items_to_schedule)} notes scheduled.[/green]")

    if process:
        # Initialize AI components
        console.print("[dim]Initializing Sancho...[/dim]")
        ai_router = AIRouter(config=config.ai)
        reviewer = NoteReviewer(
            note_manager=manager,
            metadata_store=scheduler.store,
            scheduler=scheduler,
            ai_router=ai_router,
        )

        # Identify which notes to process
        notes_to_process_ids = []

        if force:
            # All notes in the store are candidates
            notes_to_process_ids = [m.note_id for m in sorted_meta]
        else:
            # Filter sorted list to keep only those due for review
            # For fallback objects (from NoteManager), we don't have is_due_for_review, so skip them
            notes_to_process_ids = [
                m.note_id
                for m in sorted_meta
                if hasattr(m, "is_due_for_review") and m.is_due_for_review()
            ]

        # Apply limit to execution
        if limit:
            notes_to_process_ids = notes_to_process_ids[:limit]

        if not notes_to_process_ids:
            console.print(
                "[yellow]No notes to process.[/yellow]\n"
                "[dim]Use --all to schedule or --force to process even if not due.[/dim]"
            )
            return

        console.print(
            f"[cyan]Processing {len(notes_to_process_ids)} notes through Sancho (oldest first)...[/cyan]\n"
        )

        async def run_reviews():
            from rich.table import Table

            count = 0
            for idx, note_id in enumerate(notes_to_process_ids, 1):
                # Get note for title
                note = manager.get_note(note_id)
                note_title = note.title if note else note_id

                # Header panel
                console.print(
                    Panel(
                        f"[bold cyan]{note_title}[/bold cyan]\n[dim]{note_id}[/dim]",
                        title=f"📝 Review {idx}/{len(notes_to_process_ids)}",
                        border_style="cyan",
                    )
                )

                try:
                    with console.status("[bold green]Analyzing note..."):
                        result = await reviewer.review_note(note_id)

                    # Display hygiene metrics if available
                    if (
                        result.analysis
                        and hasattr(result.analysis, "hygiene")
                        and result.analysis.hygiene
                    ):
                        hygiene = result.analysis.hygiene

                        hygiene_table = Table(
                            title="📊 Hygiene Metrics", show_header=False, box=None
                        )
                        hygiene_table.add_column("Metric", style="cyan", width=20)
                        hygiene_table.add_column("Value", style="white")

                        hygiene_table.add_row("Word Count", f"{hygiene.word_count} words")
                        hygiene_table.add_row(
                            "Frontmatter",
                            "✅ Valid"
                            if hygiene.frontmatter_valid
                            else f"❌ Issues: {', '.join(hygiene.frontmatter_issues)}",
                        )

                        if hygiene.broken_links:
                            hygiene_table.add_row(
                                "Broken Links", f"⚠️  {len(hygiene.broken_links)} found"
                            )

                        if hygiene.duplicate_candidates:
                            hygiene_table.add_row(
                                "Duplicates",
                                f"🔍 {len(hygiene.duplicate_candidates)} similar notes",
                            )

                        if hygiene.is_too_short:
                            hygiene_table.add_row("Length", "⚠️  Too short (< 100 words)")
                        elif hygiene.is_too_long:
                            hygiene_table.add_row("Length", "⚠️  Too long (> 2000 words)")

                        console.print(hygiene_table)
                        console.print()

                    # Display actions
                    total_actions = len(result.applied_actions) + len(result.pending_actions)

                    if result.applied_actions:
                        console.print("[bold green]✅ AUTO-APPLIED ACTIONS:[/bold green]")
                        for action in result.applied_actions:
                            action_icon = {
                                "fix_links": "🔗",
                                "validate": "✓",
                                "format": "📝",
                                "update": "➕",
                                "enrich": "🌟",
                            }.get(action.action_type, "•")
                            console.print(
                                f"  {action_icon} [cyan][{action.action_type.upper()}][/cyan] {action.reasoning} "
                                f"[dim](confidence: {action.confidence:.0%})[/dim]"
                            )
                        console.print()

                    if result.pending_actions:
                        console.print("[bold yellow]⏳ PENDING APPROVAL:[/bold yellow]")
                        for action in result.pending_actions:
                            action_icon = {
                                "merge": "🔀",
                                "split": "✂️",
                                "refactor": "🔄",
                            }.get(action.action_type, "•")
                            console.print(
                                f"  {action_icon} [yellow][{action.action_type.upper()}][/yellow] {action.reasoning} "
                                f"[dim](confidence: {action.confidence:.0%})[/dim]"
                            )
                        console.print()

                    if total_actions == 0:
                        console.print("[dim]No actions suggested.[/dim]\n")

                    # Quality score
                    quality_stars = "⭐" * result.quality
                    console.print(
                        f"✨ [bold]Quality Score:[/bold] {quality_stars} ({result.quality}/5)"
                    )

                    console.print("━" * 60 + "\n")
                    count += 1

                except Exception as e:
                    console.print(f"[red]❌ Error: {str(e)}[/red]\n")
                    logger.exception(f"Review failed for {note_id}")

            return count

        try:
            success_count = asyncio.run(run_reviews())
            console.print(
                f"\n[bold green]✅ Success![/bold green] Processed {success_count}/{len(notes_to_process_ids)} notes."
            )
            console.print(
                "[dim]High-confidence updates applied. Check pending actions for others.[/dim]"
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            raise typer.Exit(130) from None
        except Exception as e:
            console.print(f"\n[red]Global error: {e}[/red]")
            raise typer.Exit(1) from None


@notes_app.command("pending")
def notes_pending(
    action: str = typer.Argument(..., help="Action: list, approve, reject"),
    note_id: Optional[str] = typer.Argument(None, help="Note ID"),
    index: Optional[int] = typer.Argument(None, help="Action index (0-based)"),
):
    """
    Manage pending review actions.

    Examples:
        scapin notes pending list
        scapin notes pending approve my-note-id 0
        scapin notes pending reject my-note-id 1
    """
    from datetime import datetime, timezone
    from pathlib import Path

    from src.core.config_manager import get_config
    from src.passepartout.note_manager import NoteManager
    from src.passepartout.note_reviewer import ActionType, NoteReviewer, ReviewAction
    from src.passepartout.note_scheduler import create_scheduler
    from src.sancho.router import AIRouter

    logger = get_logger("cli")
    config = get_config()
    notes_dir = Path(config.storage.notes_path)
    manager = NoteManager(notes_dir)
    scheduler = create_scheduler(config.storage.database_path.parent)

    if action == "list":
        # List all notes with pending actions
        all_meta = scheduler.store.list_all(limit=10000)

        table = Table(title="📋 Pending Actions")
        table.add_column("Note", style="cyan", width=30)
        table.add_column("ID", style="dim", width=20)
        table.add_column("#", style="yellow", width=3)
        table.add_column("Action", style="green", width=12)
        table.add_column("Description", style="white", width=50)
        table.add_column("Conf", style="magenta", width=5)

        total_pending = 0
        for meta in all_meta:
            pending = [h for h in meta.enrichment_history if not h.applied]
            if pending:
                note = manager.get_note(meta.note_id)
                note_title = note.title if note else meta.note_id

                for idx, action in enumerate(pending):
                    table.add_row(
                        note_title[:30],
                        meta.note_id[:20],
                        str(idx),
                        action.action_type,
                        action.reasoning[:50] if action.reasoning else action.target[:50],
                        f"{action.confidence:.0%}",
                    )
                    total_pending += 1

        console.print(table)
        console.print(f"\n[bold]Total pending actions:[/bold] {total_pending}")
        console.print("[dim]Use 'scapin notes pending approve <note-id> <index>' to approve[/dim]")
        console.print("[dim]Use 'scapin notes pending reject <note-id> <index>' to reject[/dim]")

    elif action == "approve":
        if not note_id or index is None:
            console.print("[red]Error: note_id and index required[/red]")
            console.print("[dim]Usage: scapin notes pending approve <note-id> <index>[/dim]")
            raise typer.Exit(1)

        # Get metadata
        meta = scheduler.store.get(note_id)
        if not meta:
            console.print(f"[red]Note '{note_id}' not found[/red]")
            raise typer.Exit(1)

        # Find pending action
        pending = [h for h in meta.enrichment_history if not h.applied]
        if index >= len(pending):
            console.print(
                f"[red]Invalid index {index}. Note has {len(pending)} pending actions.[/red]"
            )
            raise typer.Exit(1)

        action_to_apply = pending[index]

        console.print("\n[bold cyan]Approving action:[/bold cyan]")
        console.print(f"  Type: {action_to_apply.action_type}")
        console.print(f"  Reasoning: {action_to_apply.reasoning}")
        console.print(f"  Confidence: {action_to_apply.confidence:.0%}\n")

        # Get note
        note = manager.get_note(note_id)
        if not note:
            console.print("[red]Note content not found[/red]")
            raise typer.Exit(1)

        # Convert EnrichmentRecord to ReviewAction
        review_action = ReviewAction(
            action_type=ActionType(action_to_apply.action_type),
            target=action_to_apply.target,
            content=action_to_apply.content,
            confidence=action_to_apply.confidence,
            reasoning=action_to_apply.reasoning,
        )

        # Initialize reviewer
        ai_router = AIRouter(config)
        reviewer = NoteReviewer(
            note_manager=manager,
            metadata_store=scheduler.store,
            scheduler=scheduler,
            ai_router=ai_router,
        )

        # Apply action
        with console.status("[bold green]Applying action..."):
            updated_content = reviewer._apply_action(note.content, review_action)

            # Save
            manager.update_note(note_id=note_id, content=updated_content)

            # Mark as applied in history
            action_to_apply.applied = True
            action_to_apply.timestamp = datetime.now(timezone.utc)
            scheduler.store.update(meta)

        console.print("[green]✅ Action approved and applied successfully![/green]")

    elif action == "reject":
        if not note_id or index is None:
            console.print("[red]Error: note_id and index required[/red]")
            console.print("[dim]Usage: scapin notes pending reject <note-id> <index>[/dim]")
            raise typer.Exit(1)

        # Get metadata
        meta = scheduler.store.get(note_id)
        if not meta:
            console.print(f"[red]Note '{note_id}' not found[/red]")
            raise typer.Exit(1)

        # Find pending action
        pending = [h for h in meta.enrichment_history if not h.applied]
        if index >= len(pending):
            console.print(
                f"[red]Invalid index {index}. Note has {len(pending)} pending actions.[/red]"
            )
            raise typer.Exit(1)

        action_to_reject = pending[index]

        console.print("\n[bold yellow]Rejecting action:[/bold yellow]")
        console.print(f"  Type: {action_to_reject.action_type}")
        console.print(f"  Reasoning: {action_to_reject.reasoning}")
        console.print(f"  Confidence: {action_to_reject.confidence:.0%}\n")

        # Remove from history
        meta.enrichment_history.remove(action_to_reject)
        scheduler.store.update(meta)

        console.print("[yellow]❌ Action rejected and removed from history[/yellow]")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[dim]Valid actions: list, approve, reject[/dim]")
        raise typer.Exit(1)


def run():
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    run()
