"""
Interactive Menu System

Beautiful interactive menu with arrow-key navigation using questionary.

Features:
    - Main menu with 6 options
    - Account selection (multi-select for batch processing)
    - Mode selection (auto/manual/preview)
    - Settings management
    - Statistics viewing
    - Review queue access
    - Graceful Ctrl+C handling

Usage:
    from src.jeeves.menu import run_interactive_menu

    run_interactive_menu()

Or via CLI:
    python pkm.py menu
    python pkm.py  # Menu is default when no command specified
"""

import sys
from typing import Any, Optional

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel

from src.core.config_manager import EmailAccountConfig, get_config
from src.core.multi_account_processor import MultiAccountProcessor
from src.integrations.storage.queue_storage import get_queue_storage
from src.jeeves.display_manager import DisplayManager
from src.monitoring.logger import ScapinLogger, get_logger

logger = get_logger("menu")
console = Console()

# Custom style for questionary
custom_style = Style(
    [
        ("qmark", "fg:#FFD700 bold"),  # Question mark (gold)
        ("question", "bold"),  # Question text
        ("answer", "fg:#5FD7FF bold"),  # Selected answer (cyan)
        ("pointer", "fg:#FFD700 bold"),  # Pointer (gold)
        ("highlighted", "fg:#FFD700 bold"),  # Highlighted option
        ("selected", "fg:#5FD7FF"),  # Selected items in checkbox
        ("separator", "fg:#6C6C6C"),  # Separator
        ("instruction", "fg:#858585"),  # Instructions
        ("text", ""),  # Plain text
        ("disabled", "fg:#858585 italic"),  # Disabled option
    ]
)


class InteractiveMenu:
    """
    Interactive menu with questionary navigation

    Main menu → Process Emails / Review Queue / Statistics / Settings / Health / Exit
    """

    def __init__(self):
        """Initialize interactive menu"""
        self.config = get_config()
        self.queue_storage = get_queue_storage()
        self.running = True

    def run(self) -> int:
        """
        Run interactive menu loop

        Returns:
            Exit code (0 = success)
        """
        try:
            self._show_welcome()

            while self.running:
                try:
                    self._show_main_menu()
                except KeyboardInterrupt:
                    console.print("\n[yellow]⚠ Menu cancelled[/yellow]")
                    break

            self._show_goodbye()
            return 0

        except Exception as e:
            logger.error(f"Menu error: {e}", exc_info=True)
            console.print(f"\n[red]✗ Error: {e}[/red]")
            return 1

    def _show_welcome(self):
        """Display welcome banner"""
        console.print()
        console.print(Panel.fit(
            "[bold cyan]🧠 Scapin[/bold cyan]\n"
            "[dim]Intelligent Email Management with AI[/dim]\n\n"
            "[dim]Use ↑↓ arrows to navigate, Enter to select, Ctrl+C to exit[/dim]",
            border_style="cyan",
        ))
        console.print()

    def _show_goodbye(self):
        """Display goodbye message"""
        console.print()
        console.print(Panel.fit(
            "[bold green]✓ Thank you for using Scapin![/bold green]\n"
            "[dim]Your inbox is in good hands[/dim]",
            border_style="green",
        ))
        console.print()

    def _show_main_menu(self):
        """Display main menu and handle selection"""
        # Get queue stats for display
        queue_stats = self.queue_storage.get_stats()
        queue_count = queue_stats.get("total", 0)

        # Build choices
        choices = [
            "📧 Process Emails",
            f"👁️  Review Queue ({queue_count} items)",
            "📊 View Statistics",
            "⚙️  Settings",
            "🏥 System Health",
            "🚪 Exit",
        ]

        # Show menu
        choice = questionary.select(
            "What would you like to do?",
            choices=choices,
            style=custom_style,
        ).ask()

        # Handle selection
        if not choice or "Exit" in choice:
            self.running = False
        elif "Process Emails" in choice:
            self._process_emails_submenu()
        elif "Review Queue" in choice:
            self._review_queue_submenu()
        elif "View Statistics" in choice:
            self._view_statistics()
        elif "Settings" in choice:
            self._settings_submenu()
        elif "System Health" in choice:
            self._system_health()

    def _process_emails_submenu(self):
        """Process Emails submenu"""
        console.print()
        console.print("[bold cyan]Process Emails[/bold cyan]")
        console.print()

        try:
            # Step 1: Select accounts
            accounts = self._select_accounts()
            if not accounts:
                console.print("[yellow]⚠ No accounts selected[/yellow]")
                return

            # Step 2: Select mode
            mode = self._select_mode()
            if not mode:
                return

            # Step 3: Select limit
            limit = self._select_limit()

            # Step 4: Confirm
            console.print()
            console.print("[bold]Summary:[/bold]")
            console.print(f"  Accounts: {', '.join(a.account_name for a in accounts)}")
            console.print(f"  Mode: {mode['name']}")
            console.print(f"  Limit: {limit or 'All unread emails'}")
            console.print()

            if not questionary.confirm(
                "Proceed with processing?", default=True, style=custom_style
            ).ask():
                console.print("[yellow]⚠ Processing cancelled[/yellow]")
                return

            # Step 5: Execute
            self._execute_processing(accounts, mode, limit)

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Processing cancelled[/yellow]")

    def _select_accounts(self) -> list[EmailAccountConfig]:
        """
        Account selection with multi-select

        Returns:
            List of selected EmailAccountConfig objects
        """
        enabled_accounts = self.config.email.get_enabled_accounts()

        if len(enabled_accounts) == 0:
            console.print("[red]✗ No email accounts configured[/red]")
            return []

        if len(enabled_accounts) == 1:
            # Only one account, auto-select
            account = enabled_accounts[0]
            console.print(f"[dim]Using account: {account.account_name}[/dim]")
            return [account]

        # Multiple accounts - show checkbox
        choices = [
            {
                "name": f"{acc.account_name} ({acc.imap_username})",
                "value": acc.account_id,
            }
            for acc in enabled_accounts
        ]

        # Add "All Accounts" option
        choices.insert(0, {"name": "✓ All Accounts", "value": "ALL"})

        selected_ids = questionary.checkbox(
            "Select accounts to process:",
            choices=choices,
            style=custom_style,
        ).ask()

        if not selected_ids:
            return []

        # Handle "All Accounts" selection
        if "ALL" in selected_ids:
            return enabled_accounts

        # Return selected accounts
        return [
            acc for acc in enabled_accounts if acc.account_id in selected_ids
        ]

    def _select_mode(self) -> Optional[dict[str, Any]]:
        """
        Mode selection (auto/manual/preview)

        Returns:
            Dictionary with mode info or None if cancelled
        """
        choices = [
            {
                "name": "🤖 Auto Mode - Execute high-confidence decisions automatically",
                "value": {
                    "name": "Auto",
                    "auto_execute": True,
                    "confidence_threshold": 90,
                },
            },
            {
                "name": "👁️  Manual Mode - Queue all emails for review (learning mode)",
                "value": {
                    "name": "Manual",
                    "auto_execute": False,
                    "confidence_threshold": 100,  # Never auto-execute
                },
            },
            {
                "name": "📚 Preview Mode - Analyze without making changes",
                "value": {
                    "name": "Preview",
                    "auto_execute": False,
                    "confidence_threshold": 100,
                    "preview_only": True,
                },
            },
        ]

        mode = questionary.select(
            "Select processing mode:", choices=choices, style=custom_style
        ).ask()

        return mode

    def _select_limit(self) -> Optional[int]:
        """
        Limit selection

        Returns:
            Number of emails or None for unlimited
        """
        choices = [
            {"name": "10 emails", "value": 10},
            {"name": "50 emails", "value": 50},
            {"name": "100 emails", "value": 100},
            {"name": "All unread emails", "value": None},
        ]

        limit = questionary.select(
            "How many emails to process?", choices=choices, style=custom_style
        ).ask()

        return limit

    def _execute_processing(
        self,
        accounts: list[EmailAccountConfig],
        mode: dict[str, Any],
        limit: Optional[int],
    ):
        """
        Execute email processing

        Args:
            accounts: List of accounts to process
            mode: Processing mode configuration
            limit: Email limit
        """
        console.print()
        console.print("[bold cyan]Starting email processing...[/bold cyan]")
        console.print()

        try:
            # Enable display mode
            ScapinLogger.set_display_mode(True)

            # Initialize display manager
            display = DisplayManager(console)
            display.start()

            # Create multi-account processor
            processor = MultiAccountProcessor(accounts)

            # Process emails
            results = processor.process_all_accounts(
                limit=limit,
                auto_execute=mode["auto_execute"],
                confidence_threshold=mode.get("confidence_threshold", 90),
                unread_only=True,
            )

            # Stop display manager
            display.stop()

            # Show results summary
            console.print()
            console.print("[bold green]✓ Processing complete![/bold green]")
            console.print()
            console.print(f"  Accounts processed: {results['total_accounts']}")
            console.print(f"  Total emails: {results['total_emails']}")
            console.print(f"  Auto-executed: {results['total_auto_executed']}")
            console.print(f"  Queued for review: {results['total_queued']}")
            console.print(f"  Errors: {results['total_errors']}")
            console.print()

            # Prompt to return to menu
            questionary.press_any_key_to_continue(
                "Press any key to return to menu...", style=custom_style
            ).ask()

        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            console.print(f"\n[red]✗ Error: {e}[/red]")
            questionary.press_any_key_to_continue(style=custom_style).ask()

        finally:
            # Restore console logs
            ScapinLogger.set_display_mode(False)

    def _review_queue_submenu(self):
        """Review Queue submenu"""
        # This will be implemented in InteractiveReviewMode
        console.print()
        console.print("[bold magenta]Review Queue[/bold magenta]")
        console.print()

        queue_count = self.queue_storage.get_queue_size()

        if queue_count == 0:
            console.print("[dim]Queue is empty - no emails pending review[/dim]")
            console.print()
            questionary.press_any_key_to_continue(
                "Press any key to return to menu...", style=custom_style
            ).ask()
            return

        console.print(f"[dim]{queue_count} emails queued for review[/dim]")
        console.print()

        if questionary.confirm(
            "Start interactive review?", default=True, style=custom_style
        ).ask():
            # Import and run review mode
            from src.jeeves.review_mode import InteractiveReviewMode

            review_mode = InteractiveReviewMode()
            review_mode.run()

    def _view_statistics(self):
        """View statistics"""
        console.print()
        console.print(Panel.fit(
            "[bold cyan]📊 Statistics[/bold cyan]", border_style="cyan"
        ))
        console.print()

        # Queue stats
        queue_stats = self.queue_storage.get_stats()

        console.print("[bold]Queue Statistics:[/bold]")
        console.print(f"  Total items: {queue_stats['total']}")
        if queue_stats.get('by_status'):
            for status, count in queue_stats['by_status'].items():
                console.print(f"    - {status}: {count}")
        if queue_stats.get('by_account'):
            for account, count in queue_stats['by_account'].items():
                console.print(f"    - {account}: {count}")
        console.print()

        # Processing stats from state manager
        from src.core.state_manager import get_state_manager
        state = get_state_manager()

        console.print("[bold]Processing History:[/bold]")
        emails_processed = state.get("emails_processed_total", 0)
        emails_auto_executed = state.get("emails_auto_executed", 0)
        teams_processed = state.get("teams_messages_processed", 0)
        console.print(f"  Emails processed: {emails_processed}")
        console.print(f"  Auto-executed: {emails_auto_executed}")
        console.print(f"  Teams messages: {teams_processed}")
        console.print()

        # AI stats
        console.print("[bold]AI Performance:[/bold]")
        avg_confidence = state.get("avg_confidence", 0)
        ai_calls = state.get("ai_calls_total", 0)
        console.print(f"  Total AI calls: {ai_calls}")
        console.print(f"  Avg confidence: {avg_confidence:.1f}%" if avg_confidence else "  Avg confidence: N/A")
        console.print()

        questionary.press_any_key_to_continue(
            "Press any key to return to menu...", style=custom_style
        ).ask()

    def _settings_submenu(self):
        """Settings submenu"""
        console.print()
        console.print("[bold yellow]Settings[/bold yellow]")
        console.print()

        choices = [
            "📧 View Email Accounts",
            "🤖 View AI Settings",
            "💾 View Storage Settings",
            "🔗 View Integrations",
            "⬅️  Back to Main Menu",
        ]

        choice = questionary.select(
            "Select setting to view:",
            choices=choices,
            style=custom_style,
        ).ask()

        if not choice or "Back" in choice:
            return

        if "Email Accounts" in choice:
            self._show_email_accounts()
        elif "AI Settings" in choice:
            self._show_ai_settings()
        elif "Storage Settings" in choice:
            self._show_storage_settings()
        elif "Integrations" in choice:
            self._show_integrations()

    def _show_email_accounts(self):
        """Display email account settings"""
        console.print()
        console.print("[bold]Email Accounts[/bold]")
        console.print()

        accounts = self.config.email.get_enabled_accounts()

        if not accounts:
            console.print("[dim]No email accounts configured[/dim]")
        else:
            for i, acc in enumerate(accounts, 1):
                status = "[green]●[/green]" if acc.enabled else "[red]●[/red]"
                console.print(f"  {status} Account {i}: {acc.account_name}")
                console.print(f"      Server: {acc.imap_server}:{acc.imap_port}")
                console.print(f"      User: {acc.imap_username}")
                console.print()

        console.print()
        questionary.press_any_key_to_continue(style=custom_style).ask()

    def _show_ai_settings(self):
        """Display AI settings"""
        console.print()
        console.print("[bold]AI Settings[/bold]")
        console.print()

        ai_config = self.config.ai

        console.print(f"  Model: {ai_config.model}")
        console.print(f"  Temperature: {ai_config.temperature}")
        console.print(f"  Max tokens: {ai_config.max_tokens}")

        # Processing config
        proc_config = self.config.processing
        console.print()
        console.print("[bold]Processing Settings[/bold]")
        console.print()
        console.print(f"  Cognitive reasoning: {'Enabled' if proc_config.enable_cognitive_reasoning else 'Disabled'}")
        console.print(f"  Auto-execute threshold: {proc_config.auto_execute_threshold}%")
        console.print(f"  Context enrichment: {'Enabled' if proc_config.enable_context_enrichment else 'Disabled'}")
        console.print(f"  Context top-k: {proc_config.context_top_k}")

        console.print()
        questionary.press_any_key_to_continue(style=custom_style).ask()

    def _show_storage_settings(self):
        """Display storage settings"""
        console.print()
        console.print("[bold]Storage Settings[/bold]")
        console.print()

        storage_config = self.config.storage

        console.print(f"  Base directory: {storage_config.base_dir}")
        console.print(f"  Notes directory: {storage_config.notes_dir}")
        console.print(f"  Queue directory: {storage_config.queue_dir}")

        # Check if paths exist
        from pathlib import Path
        base_path = Path(storage_config.base_dir)
        if base_path.exists():
            console.print("  [green]✓[/green] Base directory exists")
        else:
            console.print("  [yellow]⚠[/yellow] Base directory does not exist")

        console.print()
        questionary.press_any_key_to_continue(style=custom_style).ask()

    def _show_integrations(self):
        """Display integration settings"""
        console.print()
        console.print("[bold]Integrations[/bold]")
        console.print()

        # Teams
        teams_status = "[green]●[/green] Enabled" if self.config.teams.enabled else "[dim]○ Disabled[/dim]"
        console.print(f"  Microsoft Teams: {teams_status}")
        if self.config.teams.enabled:
            console.print(f"      Poll interval: {self.config.teams.poll_interval_seconds}s")

        # Calendar
        calendar_status = "[green]●[/green] Enabled" if self.config.calendar.enabled else "[dim]○ Disabled[/dim]"
        console.print(f"  Microsoft Calendar: {calendar_status}")
        if self.config.calendar.enabled:
            console.print(f"      Days ahead: {self.config.calendar.days_ahead}")

        console.print()
        questionary.press_any_key_to_continue(style=custom_style).ask()

    def _system_health(self):
        """Display system health"""
        console.print()
        console.print(Panel.fit(
            "[bold green]System Health[/bold green]", border_style="green"
        ))
        console.print()

        import shutil
        from pathlib import Path

        # Check configuration
        try:
            config = get_config()
            console.print("[green]✓[/green] Configuration loaded")
        except Exception as e:
            console.print(f"[red]✗[/red] Configuration error: {e}")
            return

        # Email accounts
        console.print()
        console.print("[bold]Email[/bold]")
        accounts = config.email.get_enabled_accounts()
        if accounts:
            console.print(f"  [green]✓[/green] {len(accounts)} email account(s) configured")
            for acc in accounts:
                console.print(f"    - {acc.account_name} ({acc.imap_server})")
        else:
            console.print("  [yellow]⚠[/yellow] No email accounts configured")

        # Storage
        console.print()
        console.print("[bold]Storage[/bold]")
        base_path = Path(config.storage.base_dir)
        if base_path.exists():
            console.print(f"  [green]✓[/green] Data directory exists: {base_path}")
            # Check disk space
            _total, _used, free = shutil.disk_usage(base_path)
            free_gb = free / (1024 ** 3)
            if free_gb > 1:
                console.print(f"  [green]✓[/green] Disk space: {free_gb:.1f} GB free")
            else:
                console.print(f"  [yellow]⚠[/yellow] Low disk space: {free_gb:.2f} GB free")
        else:
            console.print(f"  [yellow]⚠[/yellow] Data directory missing: {base_path}")

        # Queue storage
        queue_path = Path(config.storage.queue_dir)
        if queue_path.exists():
            queue_files = list(queue_path.glob("*.json"))
            console.print(f"  [green]✓[/green] Queue storage: {len(queue_files)} items")
        else:
            console.print("  [dim]○[/dim] Queue directory not created yet")

        # Notes storage
        notes_path = Path(config.storage.notes_dir)
        if notes_path.exists():
            note_files = list(notes_path.rglob("*.md"))
            console.print(f"  [green]✓[/green] Notes storage: {len(note_files)} notes")
        else:
            console.print("  [dim]○[/dim] Notes directory not created yet")

        # AI Configuration
        console.print()
        console.print("[bold]AI Configuration[/bold]")
        if config.ai.anthropic_api_key:
            key_preview = config.ai.anthropic_api_key[:8] + "..." if len(config.ai.anthropic_api_key) > 8 else "***"
            console.print(f"  [green]✓[/green] API key configured ({key_preview})")
        else:
            console.print("  [red]✗[/red] No API key configured")
        console.print(f"  [dim]Model: {config.ai.model}[/dim]")

        # Integrations
        console.print()
        console.print("[bold]Integrations[/bold]")
        if config.teams.enabled:
            console.print("  [green]✓[/green] Microsoft Teams enabled")
        else:
            console.print("  [dim]○[/dim] Microsoft Teams disabled")

        if config.calendar.enabled:
            console.print("  [green]✓[/green] Microsoft Calendar enabled")
        else:
            console.print("  [dim]○[/dim] Microsoft Calendar disabled")

        # Processing pipeline
        console.print()
        console.print("[bold]Processing Pipeline[/bold]")
        if config.processing.enable_cognitive_reasoning:
            console.print("  [green]✓[/green] Cognitive reasoning enabled")
        else:
            console.print("  [dim]○[/dim] Cognitive reasoning disabled (legacy mode)")

        if config.processing.enable_context_enrichment:
            console.print("  [green]✓[/green] Context enrichment enabled")
        else:
            console.print("  [dim]○[/dim] Context enrichment disabled")

        console.print()
        questionary.press_any_key_to_continue(
            "Press any key to return to menu...", style=custom_style
        ).ask()


def run_interactive_menu() -> int:
    """
    Run interactive menu (entry point)

    Returns:
        Exit code (0 = success)
    """
    menu = InteractiveMenu()
    return menu.run()


if __name__ == "__main__":
    sys.exit(run_interactive_menu())
