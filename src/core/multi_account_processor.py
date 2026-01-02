"""
Multi-Account Email Processor

Processes multiple email accounts sequentially with event-driven progress tracking.

Architecture:
    For each account:
        1. Emit ACCOUNT_STARTED event
        2. Create EmailProcessor for that account
        3. Process emails for account
        4. Emit ACCOUNT_COMPLETED event
        5. Aggregate results

Usage:
    from src.core.multi_account_processor import MultiAccountProcessor
    from src.core.config_manager import get_config

    config = get_config()
    accounts = config.email.get_enabled_accounts()

    processor = MultiAccountProcessor(accounts)
    results = processor.process_all_accounts(
        limit=50,
        auto_execute=True
    )

    print(f"Processed {results['total_emails']} emails across {results['total_accounts']} accounts")
"""

from typing import Any, Optional

from src.core.config_manager import EmailAccountConfig
from src.core.events import ProcessingEvent, ProcessingEventType, get_event_bus
from src.core.state_manager import get_state_manager
from src.monitoring.logger import get_logger
from src.trivelin.processor import EmailProcessor
from src.utils import now_utc

logger = get_logger("multi_account_processor")


class MultiAccountProcessor:
    """
    Process multiple email accounts sequentially

    Orchestrates email processing across multiple accounts with
    unified event tracking and result aggregation.
    """

    def __init__(self, accounts: list[EmailAccountConfig]):
        """
        Initialize multi-account processor

        Args:
            accounts: List of EmailAccountConfig to process
        """
        if not accounts:
            raise ValueError("At least one account must be provided")

        self.accounts = accounts
        self.event_bus = get_event_bus()
        self.state = get_state_manager()

        # Results storage
        self.results_by_account: dict[str, Any] = {}
        self.errors_by_account: dict[str, list[Exception]] = {}

        logger.info(
            f"MultiAccountProcessor initialized with {len(accounts)} accounts",
            extra={"account_count": len(accounts), "accounts": [a.account_id for a in accounts]},
        )

    def process_all_accounts(
        self,
        limit: Optional[int] = None,
        auto_execute: bool = False,
        confidence_threshold: Optional[int] = None,
        unread_only: bool = True,
    ) -> dict[str, Any]:
        """
        Process all configured accounts sequentially

        Args:
            limit: Maximum emails per account (None = unlimited)
            auto_execute: Auto-execute high-confidence decisions
            confidence_threshold: Minimum confidence for auto-execution
            unread_only: Only process unread emails

        Returns:
            Dictionary with aggregated results:
            {
                "total_accounts": int,
                "total_emails": int,
                "total_auto_executed": int,
                "total_queued": int,
                "total_errors": int,
                "accounts": {...}  # Per-account results
            }
        """
        logger.info(
            "Starting multi-account processing",
            extra={
                "account_count": len(self.accounts),
                "limit_per_account": limit,
                "auto_execute": auto_execute,
            },
        )

        # Track overall stats
        total_emails = 0
        total_auto_executed = 0
        total_queued = 0
        total_errors = 0
        total_accounts_processed = 0

        # Process each account sequentially
        for account in self.accounts:
            if not account.enabled:
                logger.info(f"Skipping disabled account: {account.account_id}")
                continue

            try:
                # Emit account started event
                self.event_bus.emit(
                    ProcessingEvent(
                        event_type=ProcessingEventType.ACCOUNT_STARTED,
                        account_id=account.account_id,
                        account_name=account.account_name,
                        metadata={
                            "host": account.imap_host,
                            "username": account.imap_username,
                        },
                    )
                )

                # Process account
                account_results = self._process_single_account(
                    account=account,
                    limit=limit,
                    auto_execute=auto_execute,
                    confidence_threshold=confidence_threshold,
                    unread_only=unread_only,
                )

                # Store results
                self.results_by_account[account.account_id] = account_results

                # Aggregate stats
                account_stats = account_results.get("stats", {})
                total_emails += account_stats.get("emails_processed", 0)
                total_auto_executed += account_stats.get("emails_auto_executed", 0)
                total_queued += account_stats.get("emails_queued", 0)
                total_accounts_processed += 1

                # Emit account completed event
                self.event_bus.emit(
                    ProcessingEvent(
                        event_type=ProcessingEventType.ACCOUNT_COMPLETED,
                        account_id=account.account_id,
                        account_name=account.account_name,
                        metadata={
                            "stats": account_stats,
                            "processed": account_stats.get("emails_processed", 0),
                        },
                    )
                )

            except Exception as e:
                logger.error(
                    f"Failed to process account {account.account_id}: {e}",
                    exc_info=True,
                    extra={"account_id": account.account_id},
                )

                # Store error
                if account.account_id not in self.errors_by_account:
                    self.errors_by_account[account.account_id] = []
                self.errors_by_account[account.account_id].append(e)

                total_errors += 1

                # Emit account error event
                self.event_bus.emit(
                    ProcessingEvent(
                        event_type=ProcessingEventType.ACCOUNT_ERROR,
                        account_id=account.account_id,
                        account_name=account.account_name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                )

        # Build aggregated results
        results = {
            "total_accounts": total_accounts_processed,
            "total_emails": total_emails,
            "total_auto_executed": total_auto_executed,
            "total_queued": total_queued,
            "total_errors": total_errors,
            "accounts": self.results_by_account,
            "errors": self.errors_by_account,
            "processed_at": now_utc().isoformat(),
        }

        logger.info(
            "Multi-account processing completed",
            extra={
                "total_accounts": total_accounts_processed,
                "total_emails": total_emails,
                "total_auto_executed": total_auto_executed,
                "total_queued": total_queued,
                "total_errors": total_errors,
            },
        )

        return results

    def _process_single_account(
        self,
        account: EmailAccountConfig,
        limit: Optional[int],
        auto_execute: bool,
        confidence_threshold: Optional[int],
        unread_only: bool,
    ) -> dict[str, Any]:
        """
        Process a single email account

        Args:
            account: EmailAccountConfig to process
            limit: Maximum emails to process
            auto_execute: Auto-execute high-confidence decisions
            confidence_threshold: Minimum confidence for auto-execution
            unread_only: Only process unread emails

        Returns:
            Dictionary with account processing results
        """
        logger.info(
            f"Processing account: {account.account_name}",
            extra={
                "account_id": account.account_id,
                "account_name": account.account_name,
                "limit": limit,
            },
        )

        # Create processor for this account
        processor = EmailProcessor()

        # Override the IMAP client with account-specific config
        from src.integrations.email.imap_client import IMAPClient
        processor.imap_client = IMAPClient(account)

        # Process emails
        processed_emails = processor.process_inbox(
            limit=limit,
            auto_execute=auto_execute,
            confidence_threshold=confidence_threshold,
            unread_only=unread_only,
        )

        # Get processing stats
        stats = processor.get_processing_stats()

        return {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "emails": processed_emails,
            "stats": stats,
            "processed_at": now_utc().isoformat(),
        }

    def get_summary(self) -> dict[str, Any]:
        """
        Get processing summary across all accounts

        Returns:
            Dictionary with summary statistics
        """
        total_emails = sum(
            results["stats"].get("emails_processed", 0)
            for results in self.results_by_account.values()
        )

        total_auto_executed = sum(
            results["stats"].get("emails_auto_executed", 0)
            for results in self.results_by_account.values()
        )

        total_queued = sum(
            results["stats"].get("emails_queued", 0)
            for results in self.results_by_account.values()
        )

        return {
            "accounts_processed": len(self.results_by_account),
            "total_emails": total_emails,
            "total_auto_executed": total_auto_executed,
            "total_queued": total_queued,
            "total_errors": len(self.errors_by_account),
            "accounts": list(self.results_by_account.keys()),
        }
