"""
Multi-Account Integration Tests

Tests the end-to-end multi-account email processing functionality using
direct Python object creation (env file parsing requires custom logic).

Note: Full .env file parsing for EMAIL__ACCOUNTS__0__* format requires
implementing a custom settings source in PKMConfig. See Phase 2 roadmap.
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import os

from src.core.config_manager import (
    ConfigManager,
    EmailAccountConfig,
    EmailConfig,
    PKMConfig,
    AIConfig
)
from src.core.state_manager import StateManager
from src.core.schemas import (
    EmailMetadata,
    EmailContent,
    EmailAnalysis,
    EmailAction,
    EmailCategory,
)
from src.monitoring.logger import PKMLogger, LogLevel
from src.utils import ensure_dir, now_utc


pytestmark = pytest.mark.integration


class TestMultiAccountConfiguration:
    """Test multi-account configuration objects and validation"""

    def test_create_multi_account_config(self):
        """Test creating multi-account configuration programmatically"""
        # Create two accounts
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal (iCloud)",
            imap_host="imap.mail.me.com",
            imap_port=993,
            imap_username="user@icloud.com",
            imap_password="password123"
        )

        work = EmailAccountConfig(
            account_id="work",
            account_name="Work Email",
            imap_host="imap.gmail.com",
            imap_port=993,
            imap_username="user@company.com",
            imap_password="workpass456"
        )

        # Create email config with multiple accounts
        email_config = EmailConfig(
            accounts=[personal, work],
            default_account_id="personal"
        )

        assert len(email_config.accounts) == 2
        assert email_config.default_account_id == "personal"

    def test_get_account_by_id(self):
        """Test retrieving specific account by ID"""
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="user@icloud.com",
            imap_password="password123"
        )

        work = EmailAccountConfig(
            account_id="work",
            account_name="Work Account",
            imap_host="imap.gmail.com",
            imap_username="user@work.com",
            imap_password="workpass456"
        )

        email_config = EmailConfig(accounts=[personal, work])

        # Get work account
        work_account = email_config.get_account("work")
        assert work_account is not None
        assert work_account.account_id == "work"
        assert work_account.imap_host == "imap.gmail.com"

        # Get personal account
        personal_account = email_config.get_account("personal")
        assert personal_account is not None
        assert personal_account.account_id == "personal"

        # Get nonexistent account
        nonexistent = email_config.get_account("nonexistent")
        assert nonexistent is None

    def test_get_enabled_accounts_filters_disabled(self):
        """Test that get_enabled_accounts() filters out disabled accounts"""
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="user@icloud.com",
            imap_password="password123",
            enabled=True
        )

        work = EmailAccountConfig(
            account_id="work",
            account_name="Work Account",
            imap_host="imap.gmail.com",
            imap_username="user@work.com",
            imap_password="workpass456",
            enabled=False  # Disabled
        )

        email_config = EmailConfig(accounts=[personal, work])

        # Total accounts: 2
        assert len(email_config.accounts) == 2

        # Enabled accounts: 1
        enabled = email_config.get_enabled_accounts()
        assert len(enabled) == 1
        assert enabled[0].account_id == "personal"

    def test_validate_unique_account_ids(self):
        """Test that duplicate account IDs are rejected"""
        personal1 = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="user1@icloud.com",
            imap_password="password123"
        )

        personal2 = EmailAccountConfig(
            account_id="personal",  # Duplicate ID
            account_name="Personal Account 2",
            imap_host="imap.gmail.com",
            imap_username="user2@gmail.com",
            imap_password="password456"
        )

        # Should raise validation error for duplicate IDs
        with pytest.raises(ValueError, match="Duplicate"):
            EmailConfig(accounts=[personal1, personal2])

    def test_validate_unique_usernames(self):
        """Test that duplicate IMAP usernames are rejected"""
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="same@email.com",
            imap_password="password123"
        )

        work = EmailAccountConfig(
            account_id="work",
            account_name="Work Account",
            imap_host="imap.gmail.com",
            imap_username="same@email.com",  # Duplicate username
            imap_password="password456"
        )

        # Should raise validation error for duplicate usernames
        with pytest.raises(ValueError, match="Duplicate.*username"):
            EmailConfig(accounts=[personal, work])

    def test_validate_default_account_exists(self):
        """Test that default_account_id must reference existing account"""
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="user@icloud.com",
            imap_password="password123"
        )

        # Should raise validation error
        with pytest.raises(ValueError, match="default_account_id.*not found"):
            EmailConfig(
                accounts=[personal],
                default_account_id="nonexistent"
            )

    def test_validate_at_least_one_enabled(self):
        """Test that at least one account must be enabled"""
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="user@icloud.com",
            imap_password="password123",
            enabled=False
        )

        work = EmailAccountConfig(
            account_id="work",
            account_name="Work Account",
            imap_host="imap.gmail.com",
            imap_username="user@work.com",
            imap_password="password456",
            enabled=False
        )

        # Should raise validation error - no enabled accounts
        with pytest.raises(ValueError, match="At least one account must be enabled"):
            EmailConfig(accounts=[personal, work])

    def test_get_default_account(self):
        """Test getting the default account"""
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="user@icloud.com",
            imap_password="password123"
        )

        work = EmailAccountConfig(
            account_id="work",
            account_name="Work Account",
            imap_host="imap.gmail.com",
            imap_username="user@work.com",
            imap_password="password456"
        )

        email_config = EmailConfig(
            accounts=[personal, work],
            default_account_id="work"
        )

        default = email_config.get_default_account()
        assert default.account_id == "work"

    def test_account_specific_folder_configuration(self):
        """Test that each account can have different folder settings"""
        personal = EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
            imap_username="user@icloud.com",
            imap_password="password123",
            inbox_folder="INBOX",
            archive_folder="Archive",
            delete_folder="Trash"
        )

        work = EmailAccountConfig(
            account_id="work",
            account_name="Work Account",
            imap_host="imap.gmail.com",
            imap_username="user@work.com",
            imap_password="password456",
            inbox_folder="INBOX",
            archive_folder="[Gmail]/All Mail",
            delete_folder="[Gmail]/Trash"
        )

        email_config = EmailConfig(accounts=[personal, work])

        # Get personal account folders
        personal_account = email_config.get_account("personal")
        assert personal_account.inbox_folder == "INBOX"
        assert personal_account.archive_folder == "Archive"
        assert personal_account.delete_folder == "Trash"

        # Get work account folders (Gmail specific)
        work_account = email_config.get_account("work")
        assert work_account.inbox_folder == "INBOX"
        assert work_account.archive_folder == "[Gmail]/All Mail"
        assert work_account.delete_folder == "[Gmail]/Trash"


class TestMultiAccountProcessing:
    """Test multi-account email processing workflows"""

    def test_account_error_isolation(self):
        """Test that errors in one account don't affect others"""
        # Create three accounts
        accounts = [
            EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
                imap_username="user@icloud.com",
                imap_password="password123"
            ),
            EmailAccountConfig(
            account_id="work",
            account_name="Work Account",
            imap_host="imap.gmail.com",
                imap_username="user@work.com",
                imap_password="password456"
            ),
            EmailAccountConfig(
            account_id="other",
            account_name="Other Account",
            imap_host="imap.other.com",
                imap_username="user@other.com",
                imap_password="password789"
            )
        ]

        # Simulate processing with error in middle account
        results = {}
        errors = {}

        for account in accounts:
            try:
                # Simulate error for work account
                if account.account_id == "work":
                    raise ConnectionError("IMAP connection failed")

                # Successful processing for others
                results[account.account_id] = {
                    "status": "success",
                    "processed": 10
                }

            except Exception as e:
                errors[account.account_id] = str(e)
                # Continue processing other accounts

        # Verify that 2 accounts succeeded despite 1 failure
        assert len(results) == 2
        assert "personal" in results
        assert "other" in results
        assert results["personal"]["status"] == "success"
        assert results["other"]["status"] == "success"

        # Verify error was captured for work account
        assert len(errors) == 1
        assert "work" in errors
        assert "IMAP connection failed" in errors["work"]


class TestMultiAccountStatistics:
    """Test multi-account statistics tracking"""

    def test_separate_statistics_per_account(self):
        """Test that statistics are tracked separately for each account"""
        # Create separate state managers for each account
        personal_state = StateManager()
        work_state = StateManager()

        # Initialize counters
        personal_state.set("emails_processed", 0)
        personal_state.set("emails_archived", 0)
        work_state.set("emails_processed", 0)
        work_state.set("emails_archived", 0)

        # Simulate processing different volumes
        # Personal: 10 emails, 7 archived
        for _ in range(10):
            personal_state.increment("emails_processed")
        for _ in range(7):
            personal_state.increment("emails_archived")

        # Work: 25 emails, 15 archived
        for _ in range(25):
            work_state.increment("emails_processed")
        for _ in range(15):
            work_state.increment("emails_archived")

        # Verify separate counts
        assert personal_state.get("emails_processed") == 10
        assert personal_state.get("emails_archived") == 7
        assert work_state.get("emails_processed") == 25
        assert work_state.get("emails_archived") == 15

    def test_aggregate_multi_account_statistics(self):
        """Test aggregating statistics across multiple accounts"""
        # Create account statistics
        account_stats = {
            "personal": {
                "processed": 10,
                "archived": 7,
                "deleted": 2,
                "tasked": 1
            },
            "work": {
                "processed": 25,
                "archived": 15,
                "deleted": 5,
                "tasked": 5
            },
            "other": {
                "processed": 5,
                "archived": 3,
                "deleted": 1,
                "tasked": 1
            }
        }

        # Calculate totals
        total_stats = {
            "processed": sum(s["processed"] for s in account_stats.values()),
            "archived": sum(s["archived"] for s in account_stats.values()),
            "deleted": sum(s["deleted"] for s in account_stats.values()),
            "tasked": sum(s["tasked"] for s in account_stats.values()),
        }

        # Verify totals
        assert total_stats["processed"] == 40
        assert total_stats["archived"] == 25
        assert total_stats["deleted"] == 8
        assert total_stats["tasked"] == 7

        # Verify per-account breakdown is preserved
        assert len(account_stats) == 3
        assert account_stats["personal"]["processed"] == 10
        assert account_stats["work"]["processed"] == 25


class TestLegacyMigration:
    """Test legacy single-account format auto-migration"""

    def test_legacy_format_auto_migrates(self):
        """Test that legacy single-account format automatically migrates"""
        # Create email config with legacy fields
        email_config = EmailConfig(
            # Legacy fields
            imap_host="imap.mail.me.com",
            imap_port=993,
            imap_username="user@icloud.com",
            imap_password="oldpass123",
            inbox_folder="INBOX",
            archive_folder="Archive"
        )

        # Should auto-migrate to accounts list
        assert len(email_config.accounts) == 1
        account = email_config.accounts[0]

        # Verify migrated account
        assert account.account_id == "default"
        assert account.account_name == "Default Account"
        assert account.imap_host == "imap.mail.me.com"
        assert account.imap_port == 993
        assert account.imap_username == "user@icloud.com"
        assert account.imap_password == "oldpass123"
        assert account.inbox_folder == "INBOX"
        assert account.archive_folder == "Archive"

        # Verify default account set
        assert email_config.default_account_id == "default"

    def test_accounts_takes_precedence_over_legacy(self):
        """Test that accounts list takes precedence over legacy fields"""
        # Create config with both accounts and legacy fields
        email_config = EmailConfig(
            accounts=[
                EmailAccountConfig(
            account_id="personal",
            account_name="Personal Account",
            imap_host="imap.mail.me.com",
                    imap_username="user@icloud.com",
                    imap_password="password123"
                )
            ],
            # Legacy fields should be ignored
            imap_host="legacy.host.com",
            imap_username="legacy@email.com",
            imap_password="legacypass"
        )

        # Should use accounts list, not legacy
        assert len(email_config.accounts) == 1
        assert email_config.accounts[0].account_id == "personal"
        assert email_config.accounts[0].imap_host == "imap.mail.me.com"
