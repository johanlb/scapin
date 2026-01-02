"""
Interactive Review Mode

Manual review interface for low-confidence emails queued for approval.

Users can:
    - View email details and AI recommendation
    - Approve (execute as recommended)
    - Modify (change action and execute)
    - Reject (keep in inbox)
    - Skip (leave in queue for later)

AI corrections are tracked for future learning.

Usage:
    from src.jeeves.review_mode import InteractiveReviewMode

    review_mode = InteractiveReviewMode()
    review_mode.run()
"""

import sys
from datetime import datetime
from typing import Any, Optional

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.core.config_manager import get_config
from src.integrations.storage.queue_storage import get_queue_storage
from src.monitoring.logger import get_logger

logger = get_logger("review_mode")
console = Console()

# Custom style
custom_style = Style(
    [
        ("qmark", "fg:#FFD700 bold"),
        ("question", "bold"),
        ("answer", "fg:#5FD7FF bold"),
        ("pointer", "fg:#FFD700 bold"),
        ("highlighted", "fg:#FFD700 bold"),
        ("selected", "fg:#5FD7FF"),
        ("separator", "fg:#6C6C6C"),
        ("instruction", "fg:#858585"),
        ("text", ""),
        ("disabled", "fg:#858585 italic"),
    ]
)


class InteractiveReviewMode:
    """
    Interactive review mode for queued emails

    Display email cards with AI recommendations and allow manual review.
    """

    def __init__(self):
        """Initialize review mode"""
        self.queue_storage = get_queue_storage()
        self.config = get_config()

        # Stats
        self.reviewed = 0
        self.approved = 0
        self.modified = 0
        self.rejected = 0
        self.skipped = 0

    def run(self) -> int:
        """
        Run interactive review mode

        Returns:
            Exit code (0 = success)
        """
        try:
            # Load queue
            queue_items = self.queue_storage.load_queue(status="pending")

            if not queue_items:
                console.print()
                console.print("[dim]No items in queue to review[/dim]")
                console.print()
                return 0

            console.print()
            console.print(Panel.fit(
                f"[bold magenta]📋 Review Mode[/bold magenta]\n"
                f"[dim]{len(queue_items)} items to review[/dim]",
                border_style="magenta",
            ))
            console.print()

            # Review each item
            for idx, item in enumerate(queue_items):
                try:
                    if not self._review_item(item, idx + 1, len(queue_items)):
                        # User cancelled
                        break
                except KeyboardInterrupt:
                    console.print("\n[yellow]⚠ Review cancelled[/yellow]")
                    break

            # Show summary
            self._show_summary()

            return 0

        except Exception as e:
            logger.error(f"Review mode error: {e}", exc_info=True)
            console.print(f"\n[red]✗ Error: {e}[/red]")
            return 1

    def _review_item(self, item: dict[str, Any], current: int, total: int) -> bool:
        """
        Review a single queue item

        Args:
            item: Queue item dictionary
            current: Current item number
            total: Total items

        Returns:
            True to continue, False to cancel review
        """
        # Extract data
        metadata = item.get("metadata", {})
        analysis = item.get("analysis", {})
        content = item.get("content", {})

        subject = metadata.get("subject", "(No Subject)")
        from_address = metadata.get("from_address", "Unknown")
        from_name = metadata.get("from_name", "")
        email_date = metadata.get("date")
        preview = content.get("preview", "")

        recommended_action = analysis.get("action", "unknown")
        confidence = analysis.get("confidence", 0)
        category = analysis.get("category", "unknown")
        reasoning = analysis.get("reasoning", "No reasoning provided")

        # Format email date/age
        age_str = self._format_email_age(email_date)

        # Render email card
        console.print()
        console.print(self._render_email_card(
            subject=subject,
            from_address=from_address,
            from_name=from_name,
            email_date=email_date,
            age_str=age_str,
            recommended_action=recommended_action,
            confidence=confidence,
            category=category,
            reasoning=reasoning,
            preview=preview,
            current=current,
            total=total,
        ))

        # Ask for decision
        console.print()
        choices = [
            "✓ Approve - Execute as recommended",
            "✎ Modify - Change action and execute",
            "✗ Reject - Keep in inbox (no action)",
            "⏭  Skip - Leave in queue for later",
            "❌ Cancel - Exit review mode",
        ]

        decision = questionary.select(
            "What would you like to do?",
            choices=choices,
            style=custom_style,
        ).ask()

        if not decision:
            return False

        # Handle decision
        if "Cancel" in decision:
            return False
        elif "Approve" in decision:
            self._approve_item(item, recommended_action)
        elif "Modify" in decision:
            self._modify_item(item, recommended_action)
        elif "Reject" in decision:
            self._reject_item(item)
        elif "Skip" in decision:
            self._skip_item(item)

        return True

    def _approve_item(self, item: dict[str, Any], recommended_action: str):
        """
        Approve and execute recommended action

        Args:
            item: Queue item
            recommended_action: AI recommended action
        """
        console.print()
        console.print(f"[green]✓ Approved - executing {recommended_action}...[/green]")

        # Execute the action
        success = self._execute_email_action(item, recommended_action)

        if not success:
            console.print("[yellow]⚠ Action execution failed - item remains in queue[/yellow]")
            return

        # Update item status
        self.queue_storage.update_item(
            item["id"],
            {
                "status": "approved",
                "reviewed_at": datetime.now().isoformat(),
                "review_decision": "approve",
                "executed_action": recommended_action,
            },
        )

        # Remove from queue
        self.queue_storage.remove_item(item["id"])

        self.reviewed += 1
        self.approved += 1

        logger.info(
            "Email approved and executed",
            extra={
                "item_id": item["id"],
                "action": recommended_action,
                "subject": item["metadata"]["subject"],
            },
        )

    def _modify_item(self, item: dict[str, Any], recommended_action: str):
        """
        Modify action and execute

        Args:
            item: Queue item
            recommended_action: AI recommended action
        """
        console.print()
        console.print(f"[yellow]Current recommendation: {recommended_action}[/yellow]")
        console.print()

        # Select new action
        action_choices = [
            {"name": "📦 ARCHIVE - Move to archive folder", "value": "archive"},
            {"name": "🗑️  DELETE - Move to delete folder", "value": "delete"},
            {"name": "✅ TASK - Create OmniFocus task", "value": "task"},
            {"name": "📚 REFERENCE - Save to reference folder", "value": "reference"},
            {"name": "↩️  REPLY - Flag for reply", "value": "reply"},
        ]

        new_action = questionary.select(
            "Select new action:",
            choices=action_choices,
            style=custom_style,
        ).ask()

        if not new_action:
            console.print("[yellow]⚠ Action change cancelled[/yellow]")
            return

        console.print()
        console.print(f"[yellow]✎ Modified: {recommended_action} → {new_action}[/yellow]")
        console.print(f"[dim]Executing {new_action}...[/dim]")

        # Execute the modified action
        success = self._execute_email_action(item, new_action)

        if not success:
            console.print("[yellow]⚠ Action execution failed - item remains in queue[/yellow]")
            return

        # Update item status and track correction for AI learning
        self.queue_storage.update_item(
            item["id"],
            {
                "status": "modified",
                "reviewed_at": datetime.now().isoformat(),
                "review_decision": "modify",
                "executed_action": new_action,
                "ai_recommended": recommended_action,
                "user_corrected": new_action,
            },
        )

        # Remove from queue
        self.queue_storage.remove_item(item["id"])

        self.reviewed += 1
        self.modified += 1

        logger.info(
            "Email modified and executed",
            extra={
                "item_id": item["id"],
                "ai_action": recommended_action,
                "user_action": new_action,
                "subject": item["metadata"]["subject"],
            },
        )

    def _reject_item(self, item: dict[str, Any]):
        """
        Reject - keep in inbox

        Args:
            item: Queue item
        """
        console.print()
        console.print("[red]✗ Rejected - keeping in inbox (no action)[/red]")

        # Update item status
        self.queue_storage.update_item(
            item["id"],
            {
                "status": "rejected",
                "reviewed_at": datetime.now().isoformat(),
                "review_decision": "reject",
            },
        )

        # Remove from queue
        self.queue_storage.remove_item(item["id"])

        self.reviewed += 1
        self.rejected += 1

        logger.info(
            "Email rejected",
            extra={"item_id": item["id"], "subject": item["metadata"]["subject"]},
        )

    def _skip_item(self, item: dict[str, Any]):
        """
        Skip - leave in queue

        Args:
            item: Queue item
        """
        console.print()
        console.print("[dim]⏭  Skipped - left in queue[/dim]")

        # No action needed - item stays in queue
        self.skipped += 1

        logger.debug("Email skipped", extra={"item_id": item["id"]})

    def _execute_email_action(self, item: dict[str, Any], action: str) -> bool:
        """
        Execute email action (move to folder or create task)

        Args:
            item: Queue item with metadata
            action: Action to execute (archive, delete, reference, task, reply)

        Returns:
            True if successful, False otherwise
        """
        try:
            from src.core.config_manager import get_config
            from src.integrations.email.imap_client import IMAPClient

            # Get config for the account
            config = get_config()
            account_id = item.get("account_id")

            if account_id:
                account_config = config.email.get_account(account_id)
                if not account_config:
                    logger.error(f"Account not found: {account_id}")
                    return False
            else:
                # Use default account
                account_config = config.email.get_default_account()
                if not account_config:
                    logger.error("No default account configured")
                    return False

            # Create IMAP client
            imap_client = IMAPClient(account_config)

            # Execute action based on type
            email_id = item["metadata"]["id"]
            folder = item["metadata"]["folder"]

            if action in ["archive", "delete", "reference"]:
                # Map action to folder
                folder_map = {
                    "archive": account_config.archive_folder,
                    "delete": account_config.delete_folder,
                    "reference": account_config.reference_folder,
                }

                target_folder = folder_map.get(action)
                if not target_folder:
                    logger.error(f"Target folder not configured for action: {action}")
                    return False

                # Move email
                imap_client.move_email(email_id, folder, target_folder)
                logger.info(f"Moved email {email_id} to {target_folder}")

            elif action == "task":
                # Create OmniFocus task
                try:
                    from src.integrations.apple.omnifocus import create_task_from_email

                    task_data = {
                        "name": item["metadata"]["subject"],
                        "note": f"From: {item['metadata']['from_address']}\n\n{item['content']['preview']}",
                    }

                    create_task_from_email(task_data)
                    logger.info(f"Created task for email: {item['metadata']['subject']}")

                    # Also archive the email
                    imap_client.move_email(
                        email_id, folder, account_config.archive_folder
                    )

                except ImportError:
                    logger.warning("OmniFocus integration not available")
                    return False

            elif action == "reply":
                # For reply, just flag the email
                logger.info(f"Flagged email {email_id} for reply")
                # Note: Actual reply flagging would require IMAP flag support
                console.print(
                    "[yellow]Note: Reply action currently only marks for review[/yellow]"
                )

            else:
                logger.error(f"Unknown action: {action}")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}", exc_info=True)
            return False

    def _render_email_card(
        self,
        subject: str,
        from_address: str,
        from_name: str,
        email_date: Optional[str],
        age_str: str,
        recommended_action: str,
        confidence: int,
        category: str,
        reasoning: str,
        preview: str,
        current: int,
        total: int,
    ) -> Panel:
        """
        Render email card with AI recommendation

        Returns:
            Rich Panel with formatted email details
        """
        # Build content
        content = Text()

        # Email details
        content.append(f"{subject}\n", style="bold")
        if from_name:
            content.append(f"From: {from_name} <{from_address}>\n", style="dim")
        else:
            content.append(f"From: {from_address}\n", style="dim")

        if email_date:
            content.append(f"Date: {age_str}\n", style="dim")

        content.append("\n")

        # AI Recommendation section
        content.append("AI Recommends:\n", style="bold cyan")

        # Action with icon
        action_icons = {
            "archive": "📦",
            "delete": "🗑️",
            "task": "✅",
            "reference": "📚",
            "reply": "↩️",
            "defer": "⏰",
            "keep": "📥",
        }
        action_icon = action_icons.get(recommended_action, "📧")
        content.append(f"  {action_icon} {recommended_action.upper()}\n", style="bold")

        # Confidence bar
        confidence_bar = self._render_confidence_bar(confidence)
        content.append("  Confidence: ")
        content.append(confidence_bar)
        content.append("\n")

        # Category
        category_icons = {
            "work": "💼",
            "personal": "👤",
            "finance": "💰",
            "shopping": "🛒",
            "newsletter": "📰",
            "social": "👥",
            "notification": "🔔",
        }
        category_icon = category_icons.get(category, "📁")
        content.append(f"  Category: {category_icon} {category}\n", style="dim")

        # Reasoning
        content.append(f"  Reasoning: {reasoning}\n", style="dim italic")

        # Preview
        if preview:
            content.append("\n")
            content.append(f"{preview}...\n", style="dim italic")

        return Panel(
            content,
            title=f"Item {current}/{total}",
            border_style="magenta",
            padding=(1, 2),
        )

    def _render_confidence_bar(self, confidence: int) -> Text:
        """
        Render confidence bar

        Args:
            confidence: Confidence percentage (0-100)

        Returns:
            Formatted confidence bar
        """
        # Determine color
        if confidence >= 90:
            color = "green"
        elif confidence >= 80:
            color = "yellow"
        elif confidence >= 65:
            color = "orange"
        else:
            color = "red"

        # Build bar (4 blocks)
        filled = int((confidence / 100) * 4)
        empty = 4 - filled

        bar = "█" * filled + "░" * empty
        text = Text()
        text.append(f"{bar} {confidence}%", style=color)

        return text

    def _format_email_age(self, email_date_str: Optional[str]) -> str:
        """
        Format email age as relative time

        Args:
            email_date_str: ISO format date string

        Returns:
            Human-readable age string
        """
        if not email_date_str:
            return "Unknown date"

        try:
            from datetime import timezone

            from src.utils import now_utc

            email_date = datetime.fromisoformat(email_date_str.replace("Z", "+00:00"))

            # Ensure timezone-aware
            if email_date.tzinfo is None:
                email_date = email_date.replace(tzinfo=timezone.utc)

            now = now_utc()
            delta = now - email_date

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

        except Exception:
            return "Unknown date"

    def _show_summary(self):
        """Display review session summary"""
        console.print()
        console.print(Panel.fit(
            f"[bold magenta]Review Summary[/bold magenta]\n\n"
            f"Total reviewed: {self.reviewed}\n"
            f"  [green]✓[/green] Approved: {self.approved}\n"
            f"  [yellow]✎[/yellow] Modified: {self.modified}\n"
            f"  [red]✗[/red] Rejected: {self.rejected}\n"
            f"  [dim]⏭[/dim]  Skipped: {self.skipped}",
            border_style="magenta",
        ))
        console.print()

        logger.info(
            "Review session completed",
            extra={
                "reviewed": self.reviewed,
                "approved": self.approved,
                "modified": self.modified,
                "rejected": self.rejected,
                "skipped": self.skipped,
            },
        )


if __name__ == "__main__":
    review_mode = InteractiveReviewMode()
    sys.exit(review_mode.run())
