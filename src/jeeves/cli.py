"""
PKM CLI Application

Main CLI entry point using Typer and Rich for elegant interface.
"""

from typing import Optional

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
from src.monitoring.logger import LogFormat, LogLevel, PKMLogger, get_logger

# Create Typer app
app = typer.Typer(
    name="pkm",
    help="PKM Email Processor - Intelligent email management system",
    add_completion=False,
)

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
        "healthy": {
            "with_text": "[green]✓ Healthy[/green]",
            "emoji_only": "[green]✓[/green]"
        },
        "degraded": {
            "with_text": "[yellow]⚠ Degraded[/yellow]",
            "emoji_only": "[yellow]⚠[/yellow]"
        },
        "unhealthy": {
            "with_text": "[red]✗ Unhealthy[/red]",
            "emoji_only": "[red]✗[/red]"
        },
        "unknown": {
            "with_text": "[dim]? Unknown[/dim]",
            "emoji_only": "[dim]?[/dim]"
        }
    }

    format_key = "with_text" if include_text else "emoji_only"
    return status_formats.get(status.value, status_formats["unknown"])[format_key]


def version_callback(value: bool):
    """Show version and exit"""
    if value:
        console.print("[bold cyan]PKM Email Processor[/bold cyan] v2.0.0")
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
    PKM Email Processor - Intelligent email management

    Process emails with AI, extract knowledge, manage tasks.
    """
    # Configure logging
    level = LogLevel.DEBUG if verbose else LogLevel.INFO
    fmt = LogFormat.JSON if log_format == "json" else LogFormat.TEXT
    PKMLogger.configure(level=level, format=fmt)

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
    confidence: int = typer.Option(90, "--confidence", "-c", help="Confidence threshold for auto mode"),
    unread_only: bool = typer.Option(False, "--unread-only", help="Only process unread emails (UNSEEN flag)"),
    unflagged_only: bool = typer.Option(True, "--unflagged-only/--all", help="Only process unflagged emails (default: True)"),
):
    """
    Process emails from inbox

    Analyzes emails and recommends actions (archive, delete, reference, task).
    By default, processes unflagged emails (not marked/starred) from oldest to newest.
    """
    from src.jeeves.display_manager import DisplayManager
    from src.trivelin.processor import EmailProcessor

    console.print(Panel.fit(
        "[bold cyan]PKM Email Processor[/bold cyan]\n"
        "Processing your inbox...",
        border_style="cyan"
    ))

    mode = "auto" if auto else "manual"
    filters = []
    if unread_only:
        filters.append("unread")
    if unflagged_only:
        filters.append("unflagged")
    filter_str = " + ".join(filters) if filters else "all emails"

    console.print(f"[dim]Mode: {mode} | Confidence: {confidence}% | Filter: {filter_str} | Limit: {limit or 'None'}[/dim]\n")

    try:
        # Enable display mode BEFORE initialization to hide all console logs
        PKMLogger.set_display_mode(True)

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
                unflagged_only=unflagged_only
            )
        finally:
            # Always restore console logs
            PKMLogger.set_display_mode(False)
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
                    "QUEUE": "dim"
                }
                action_color = action_colors.get(email.analysis.action.value, "white")

                table.add_row(
                    email.metadata.subject[:40],
                    email.metadata.from_address[:25],
                    f"[{action_color}]{email.analysis.action.value}[/{action_color}]",
                    email.analysis.category.value,
                    f"{email.analysis.confidence}%"
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

    console.print(Panel.fit(
        "[bold magenta]📋 Review Queue[/bold magenta]\n"
        "Loading queued emails for review...",
        border_style="magenta"
    ))

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
    date_str: Optional[str] = typer.Option(None, "--date", "-d", help="Date for journal (YYYY-MM-DD)"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Interactive mode with questions"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    output_format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown or json)"),
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

    console.print(Panel.fit(
        f"[bold blue]Journal du {journal_date}[/bold blue]",
        border_style="blue"
    ))

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
        if output_format == "json":
            output_content = entry.to_json()
        else:
            output_content = entry.to_markdown()

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
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Interactive review mode"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum messages per poll"),
    since: Optional[str] = typer.Option(None, "--since", "-s", help="Only fetch messages after this datetime (ISO format)"),
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

    console.print(Panel.fit(
        "[bold blue]Microsoft Teams Integration[/bold blue]",
        border_style="blue"
    ))

    # Parse since datetime if provided
    since_dt: Optional[datetime] = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            console.print(f"[red]Invalid datetime format: {since}[/red]")
            console.print("[dim]Expected format: YYYY-MM-DDTHH:MM:SS[/dim]")
            raise typer.Exit(1) from None

    try:
        # Initialize processor
        processor = TeamsProcessor()

        if poll:
            # Continuous polling mode
            console.print(f"[green]Polling every {config.teams.poll_interval_seconds}s. Press Ctrl+C to stop.[/green]\n")

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
                console.print(f"[green]OK[/green] Processed {summary.successful}/{summary.total} messages")
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
                            "[green]OK[/green]" if result.success
                            else "[yellow]Skipped[/yellow]" if result.skipped
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
            default=False
        ):
            console.print("[yellow]Cancelled[/yellow]")
            return

        deleted = queue_storage.clear_queue(account_id=account)
        console.print(f"[green]✓ Cleared {deleted} items from queue[/green]")
        return

    if process_queue:
        # Launch review mode
        console.print(Panel.fit(
            "[bold yellow]📋 Processing Queue[/bold yellow]",
            border_style="yellow"
        ))

        try:
            review_mode = InteractiveReviewMode()
            exit_code = review_mode.run()
            raise typer.Exit(code=exit_code)
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            raise typer.Exit(code=1) from None

    # Show queue stats
    console.print(Panel.fit(
        "[bold yellow]📋 Queue Status[/bold yellow]",
        border_style="yellow"
    ))

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
        console.print(Panel.fit(
            "[bold magenta]Migrate Secrets to Keychain[/bold magenta]\n"
            "Moving credentials from .env to secure storage...",
            border_style="magenta"
        ))

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
            console.print("  1. Verify secrets are accessible: [cyan]python3 pkm.py secrets --list[/cyan]")
            console.print("  2. Remove migrated secrets from .env file for better security")
            console.print("  3. The app will automatically use keychain first, then fallback to .env")

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
        console.print("[yellow]Use --migrate to migrate secrets or --list to view stored secrets[/yellow]")


@app.command()
def health():
    """
    Check system health

    Verifies all system components (IMAP, AI, storage, config, git).
    """
    console.print(Panel.fit(
        "[bold green]System Health Check[/bold green]",
        border_style="green"
    ))

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
        response_time = (
            f"{check.response_time_ms:.0f}ms"
            if check.response_time_ms
            else "N/A"
        )

        table.add_row(
            check.service,
            status,
            check.message,
            response_time
        )

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
    include_health: bool = typer.Option(True, "--health/--no-health", help="Include health summary"),
):
    """
    Show comprehensive statistics

    Display session stats, queue status, health summary, and processing metrics.
    """
    console.print(Panel.fit(
        "[bold blue]📊 System Statistics[/bold blue]",
        border_style="blue"
    ))

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

        confidence_table.add_row("Average Confidence", f"{session_stats.get('confidence_avg', 0):.1f}%")

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
        queue_table.add_row("Pending Review", str(queue_stats.get("by_status", {}).get("pending", 0)))
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
            with Live(Spinner("dots", text="[dim]Checking system health...[/dim]"), console=console, transient=True):
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
                console.print(f"\n[yellow]⚠ {len(system_health.unhealthy_services)} services need attention[/yellow]")

        except Exception as e:
            console.print(f"[yellow]⚠ Could not fetch health status: {e}[/yellow]")

    # Processing state
    console.print(f"\n[dim]State: {state_dict.get('processing_state', 'idle')} | Duration: {session_stats.get('duration_minutes', 0)} min[/dim]")
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
    console.print(Panel.fit(
        "[bold cyan]Configuration[/bold cyan]",
        border_style="cyan"
    ))

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

            console.print(Panel(account_table, title=f"[bold]{account.account_name}[/bold]", border_style="cyan"))

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
        integrations_table.add_row("OmniFocus", "Enabled" if cfg.integrations.omnifocus_enabled else "Disabled")
        integrations_table.add_row("Apple Notes Sync", "Enabled" if cfg.integrations.apple_notes_sync_enabled else "Disabled")
        integrations_table.add_row("Sync Interval", f"{cfg.integrations.sync_interval_minutes} min")
        console.print(integrations_table)

    except Exception as e:
        console.print(f"[red]✗ Configuration error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def settings(
    set_confidence: Optional[int] = typer.Option(None, "--set-confidence", help="Set AI confidence threshold (0-100)"),
    set_rate_limit: Optional[int] = typer.Option(None, "--set-rate-limit", help="Set AI rate limit (requests/min)"),
    list_accounts: bool = typer.Option(False, "--list-accounts", help="List all email accounts"),
    enable_account: Optional[str] = typer.Option(None, "--enable-account", help="Enable account by ID"),
    disable_account: Optional[str] = typer.Option(None, "--disable-account", help="Disable account by ID"),
):
    """
    Manage application settings

    Modify AI settings, manage accounts, and configure integrations.
    """
    console.print(Panel.fit(
        "[bold magenta]⚙ Settings Management[/bold magenta]",
        border_style="magenta"
    ))

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
                    status
                )

            console.print(accounts_table)
            console.print()
            return

        # Set confidence threshold
        if set_confidence is not None:
            if not (MIN_CONFIDENCE_THRESHOLD <= set_confidence <= MAX_CONFIDENCE_THRESHOLD):
                console.print(f"[red]✗ Confidence threshold must be between {MIN_CONFIDENCE_THRESHOLD} and {MAX_CONFIDENCE_THRESHOLD}[/red]")
                raise typer.Exit(1)

            console.print(f"[yellow]Setting confidence threshold to {set_confidence}%...[/yellow]")
            console.print("[yellow]Note: This requires updating .env file:[/yellow]")
            console.print(f"  AI__CONFIDENCE_THRESHOLD={set_confidence}")
            console.print("\n[dim]Please update your .env file manually for now[/dim]")
            return

        # Set rate limit
        if set_rate_limit is not None:
            if not (MIN_RATE_LIMIT <= set_rate_limit <= MAX_RATE_LIMIT):
                console.print(f"[red]✗ Rate limit must be between {MIN_RATE_LIMIT} and {MAX_RATE_LIMIT}[/red]")
                raise typer.Exit(1)

            console.print(f"[yellow]Setting rate limit to {set_rate_limit} requests/min...[/yellow]")
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
                i for i, acc in enumerate(cfg.email.accounts)
                if acc.account_id == account_id_to_modify
            )

            console.print("[yellow]Note: Account enable/disable requires updating .env file:[/yellow]")
            console.print(f"  EMAIL__ACCOUNTS__{account_index}__ENABLED={new_status}")
            console.print(f"\n[dim]This will {'enable' if enable_account else 'disable'} account: {account.account_name}[/dim]")
            console.print("[dim]Please update your .env file manually and restart the application[/dim]")
            return

        # No options provided - show current settings summary
        console.print("\n[bold cyan]Current Settings:[/bold cyan]\n")

        settings_table = Table(show_header=False, box=None)
        settings_table.add_column("Setting", style="cyan")
        settings_table.add_column("Value", style="bold")

        settings_table.add_row("AI Confidence Threshold", f"{cfg.ai.confidence_threshold}%")
        settings_table.add_row("AI Rate Limit", f"{cfg.ai.rate_limit_per_minute} requests/min")
        settings_table.add_row("Email Accounts", f"{len(cfg.email.get_enabled_accounts())} enabled")
        settings_table.add_row("OmniFocus Integration", "Enabled" if cfg.integrations.omnifocus_enabled else "Disabled")
        settings_table.add_row("Backup Enabled", "Yes" if cfg.storage.backup_enabled else "No")

        console.print(settings_table)

        console.print("\n[dim]Use --help to see available options for modifying settings[/dim]")
        console.print()

    except Exception as e:
        console.print(f"[red]✗ Settings error: {e}[/red]")
        logger = get_logger("cli")
        logger.error(f"Settings command failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


def run():
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    run()
