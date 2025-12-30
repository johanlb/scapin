"""
Tests for Config Migration Script

Tests the migration from legacy single-account format to multi-account format.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from migrate_config import (
    read_env_file,
    is_legacy_format,
    migrate_to_multi_account,
    write_env_file,
    backup_env_file
)


class TestReadEnvFile:
    """Test reading .env files"""

    def test_read_simple_env_file(self, tmp_path):
        """Test reading a simple .env file"""
        env_file = tmp_path / ".env"
        env_file.write_text("""
EMAIL__IMAP_HOST=imap.mail.me.com
EMAIL__IMAP_USERNAME=user@icloud.com
EMAIL__IMAP_PASSWORD=secret123
""")

        env_vars = read_env_file(env_file)

        assert len(env_vars) == 3
        assert env_vars["EMAIL__IMAP_HOST"] == "imap.mail.me.com"
        assert env_vars["EMAIL__IMAP_USERNAME"] == "user@icloud.com"
        assert env_vars["EMAIL__IMAP_PASSWORD"] == "secret123"

    def test_read_env_file_with_quotes(self, tmp_path):
        """Test reading values with quotes"""
        env_file = tmp_path / ".env"
        env_file.write_text("""
EMAIL__IMAP_HOST="imap.mail.me.com"
EMAIL__IMAP_USERNAME='user@icloud.com'
""")

        env_vars = read_env_file(env_file)

        # Quotes should be removed
        assert env_vars["EMAIL__IMAP_HOST"] == "imap.mail.me.com"
        assert env_vars["EMAIL__IMAP_USERNAME"] == "user@icloud.com"

    def test_read_env_file_with_comments(self, tmp_path):
        """Test reading file with comments"""
        env_file = tmp_path / ".env"
        env_file.write_text("""
# This is a comment
EMAIL__IMAP_HOST=imap.mail.me.com

# Another comment
EMAIL__IMAP_USERNAME=user@icloud.com
""")

        env_vars = read_env_file(env_file)

        # Comments should be ignored
        assert len(env_vars) == 2
        assert "# This is a comment" not in env_vars

    def test_read_env_file_with_empty_lines(self, tmp_path):
        """Test reading file with empty lines"""
        env_file = tmp_path / ".env"
        env_file.write_text("""
EMAIL__IMAP_HOST=imap.mail.me.com

EMAIL__IMAP_USERNAME=user@icloud.com
""")

        env_vars = read_env_file(env_file)

        assert len(env_vars) == 2

    def test_read_nonexistent_file(self, tmp_path):
        """Test reading nonexistent file"""
        env_file = tmp_path / ".env.nonexistent"

        env_vars = read_env_file(env_file)

        assert env_vars == {}


class TestIsLegacyFormat:
    """Test legacy format detection"""

    def test_is_legacy_format_true(self):
        """Test detection of legacy format"""
        env_vars = {
            "EMAIL__IMAP_HOST": "imap.mail.me.com",
            "EMAIL__IMAP_USERNAME": "user@icloud.com",
            "EMAIL__IMAP_PASSWORD": "secret",
            "AI__ANTHROPIC_API_KEY": "sk-ant-xxx"
        }

        assert is_legacy_format(env_vars) is True

    def test_is_legacy_format_false_already_migrated(self):
        """Test detection when already migrated"""
        env_vars = {
            "EMAIL__ACCOUNTS__0__IMAP_HOST": "imap.mail.me.com",
            "EMAIL__ACCOUNTS__0__IMAP_USERNAME": "user@icloud.com",
            "EMAIL__ACCOUNTS__0__ACCOUNT_ID": "default",
            "AI__ANTHROPIC_API_KEY": "sk-ant-xxx"
        }

        assert is_legacy_format(env_vars) is False

    def test_is_legacy_format_false_no_email_config(self):
        """Test detection when no email config present"""
        env_vars = {
            "AI__ANTHROPIC_API_KEY": "sk-ant-xxx",
            "SOME_OTHER_VAR": "value"
        }

        assert is_legacy_format(env_vars) is False

    def test_is_legacy_format_mixed(self):
        """Test when both legacy and new format exist (shouldn't happen)"""
        env_vars = {
            "EMAIL__IMAP_HOST": "imap.mail.me.com",
            "EMAIL__ACCOUNTS__0__IMAP_HOST": "imap.gmail.com"
        }

        # Should return False (already has new format)
        assert is_legacy_format(env_vars) is False


class TestMigrateToMultiAccount:
    """Test migration logic"""

    def test_migrate_basic_config(self):
        """Test migrating basic email configuration"""
        legacy_vars = {
            "EMAIL__IMAP_HOST": "imap.mail.me.com",
            "EMAIL__IMAP_PORT": "993",
            "EMAIL__IMAP_USERNAME": "user@icloud.com",
            "EMAIL__IMAP_PASSWORD": "secret123",
            "AI__ANTHROPIC_API_KEY": "sk-ant-xxx"
        }

        migrated = migrate_to_multi_account(legacy_vars)

        # Check new account-specific keys
        assert migrated["EMAIL__ACCOUNTS__0__IMAP_HOST"] == "imap.mail.me.com"
        assert migrated["EMAIL__ACCOUNTS__0__IMAP_PORT"] == "993"
        assert migrated["EMAIL__ACCOUNTS__0__IMAP_USERNAME"] == "user@icloud.com"
        assert migrated["EMAIL__ACCOUNTS__0__IMAP_PASSWORD"] == "secret123"

        # Check account metadata
        assert migrated["EMAIL__ACCOUNTS__0__ACCOUNT_ID"] == "default"
        assert migrated["EMAIL__ACCOUNTS__0__ACCOUNT_NAME"] == "Default Account"
        assert migrated["EMAIL__ACCOUNTS__0__ENABLED"] == "true"

        # Check default account ID
        assert migrated["EMAIL__DEFAULT_ACCOUNT_ID"] == "default"

        # Check AI config preserved
        assert migrated["AI__ANTHROPIC_API_KEY"] == "sk-ant-xxx"

        # Check legacy keys removed
        assert "EMAIL__IMAP_HOST" not in migrated
        assert "EMAIL__IMAP_PORT" not in migrated

    def test_migrate_with_folders(self):
        """Test migrating configuration with folder settings"""
        legacy_vars = {
            "EMAIL__IMAP_HOST": "imap.mail.me.com",
            "EMAIL__IMAP_USERNAME": "user@icloud.com",
            "EMAIL__IMAP_PASSWORD": "secret",
            "EMAIL__INBOX_FOLDER": "INBOX",
            "EMAIL__ARCHIVE_FOLDER": "Archive",
            "EMAIL__REFERENCE_FOLDER": "Reference",
            "EMAIL__DELETE_FOLDER": "Trash"
        }

        migrated = migrate_to_multi_account(legacy_vars)

        # Check folder settings migrated
        assert migrated["EMAIL__ACCOUNTS__0__INBOX_FOLDER"] == "INBOX"
        assert migrated["EMAIL__ACCOUNTS__0__ARCHIVE_FOLDER"] == "Archive"
        assert migrated["EMAIL__ACCOUNTS__0__REFERENCE_FOLDER"] == "Reference"
        assert migrated["EMAIL__ACCOUNTS__0__DELETE_FOLDER"] == "Trash"

    def test_migrate_preserves_non_email_vars(self):
        """Test that non-email variables are preserved"""
        legacy_vars = {
            "EMAIL__IMAP_HOST": "imap.mail.me.com",
            "EMAIL__IMAP_USERNAME": "user@icloud.com",
            "EMAIL__IMAP_PASSWORD": "secret",
            "AI__ANTHROPIC_API_KEY": "sk-ant-xxx",
            "AI__CONFIDENCE_THRESHOLD": "90",
            "SOME_OTHER_VAR": "value123"
        }

        migrated = migrate_to_multi_account(legacy_vars)

        # Non-email vars should be preserved unchanged
        assert migrated["AI__ANTHROPIC_API_KEY"] == "sk-ant-xxx"
        assert migrated["AI__CONFIDENCE_THRESHOLD"] == "90"
        assert migrated["SOME_OTHER_VAR"] == "value123"


class TestWriteEnvFile:
    """Test writing .env files"""

    def test_write_simple_env_file(self, tmp_path):
        """Test writing a simple .env file"""
        env_file = tmp_path / ".env"
        env_vars = {
            "EMAIL__ACCOUNTS__0__ACCOUNT_ID": "default",
            "EMAIL__ACCOUNTS__0__IMAP_HOST": "imap.mail.me.com",
            "AI__ANTHROPIC_API_KEY": "sk-ant-xxx"
        }

        write_env_file(env_file, env_vars)

        # Read back and verify
        content = env_file.read_text()

        assert "EMAIL__ACCOUNTS__0__ACCOUNT_ID=default" in content
        assert "EMAIL__ACCOUNTS__0__IMAP_HOST=imap.mail.me.com" in content
        assert "AI__ANTHROPIC_API_KEY=sk-ant-xxx" in content

    def test_write_with_migrated_header(self, tmp_path):
        """Test writing with migration header"""
        env_file = tmp_path / ".env"
        env_vars = {
            "EMAIL__ACCOUNTS__0__ACCOUNT_ID": "default"
        }

        write_env_file(env_file, env_vars, migrated=True)

        content = env_file.read_text()

        # Should have migration header
        assert "Multi-Account Format" in content
        assert "Migrated:" in content

    def test_write_quotes_values_with_spaces(self, tmp_path):
        """Test that values with spaces are quoted"""
        env_file = tmp_path / ".env"
        env_vars = {
            "EMAIL__ACCOUNTS__0__ACCOUNT_NAME": "My Email Account"
        }

        write_env_file(env_file, env_vars)

        content = env_file.read_text()

        # Value with space should be quoted
        assert 'EMAIL__ACCOUNTS__0__ACCOUNT_NAME="My Email Account"' in content

    def test_write_groups_by_section(self, tmp_path):
        """Test that variables are grouped by section"""
        env_file = tmp_path / ".env"
        env_vars = {
            "EMAIL__ACCOUNTS__0__ACCOUNT_ID": "default",
            "EMAIL__ACCOUNTS__0__IMAP_HOST": "imap.mail.me.com",
            "EMAIL__ACCOUNTS__1__ACCOUNT_ID": "work",
            "EMAIL__ACCOUNTS__1__IMAP_HOST": "imap.gmail.com",
            "AI__ANTHROPIC_API_KEY": "sk-ant-xxx",
            "SOME_OTHER_VAR": "value"
        }

        write_env_file(env_file, env_vars)

        content = env_file.read_text()

        # Should have section headers
        assert "EMAIL ACCOUNTS" in content
        assert "AI CONFIGURATION" in content
        assert "OTHER CONFIGURATION" in content

        # Accounts should be grouped
        assert "Account 0: default" in content
        assert "Account 1: work" in content


class TestBackupEnvFile:
    """Test backup functionality"""

    def test_backup_creates_timestamped_file(self, tmp_path):
        """Test that backup creates timestamped file"""
        env_file = tmp_path / ".env"
        env_file.write_text("EMAIL__IMAP_HOST=imap.mail.me.com")

        backup_path = backup_env_file(env_file)

        # Backup should exist
        assert backup_path.exists()

        # Backup should have timestamp in name
        assert ".env.backup." in backup_path.name

        # Content should match original
        assert backup_path.read_text() == env_file.read_text()

    def test_backup_preserves_content(self, tmp_path):
        """Test that backup preserves exact content"""
        env_file = tmp_path / ".env"
        original_content = """
# Comment
EMAIL__IMAP_HOST=imap.mail.me.com
EMAIL__IMAP_USERNAME=user@icloud.com

# Another comment
EMAIL__IMAP_PASSWORD=secret123
"""
        env_file.write_text(original_content)

        backup_path = backup_env_file(env_file)

        assert backup_path.read_text() == original_content


class TestEndToEndMigration:
    """Test complete migration workflow"""

    def test_full_migration_workflow(self, tmp_path):
        """Test complete migration from legacy to multi-account"""
        # Create legacy .env file
        env_file = tmp_path / ".env"
        legacy_content = """# Legacy single-account configuration
EMAIL__IMAP_HOST=imap.mail.me.com
EMAIL__IMAP_PORT=993
EMAIL__IMAP_USERNAME=user@icloud.com
EMAIL__IMAP_PASSWORD=secret123
EMAIL__INBOX_FOLDER=INBOX
EMAIL__ARCHIVE_FOLDER=Archive

AI__ANTHROPIC_API_KEY=sk-ant-api-key-here
AI__CONFIDENCE_THRESHOLD=90
"""
        env_file.write_text(legacy_content)

        # Step 1: Read
        env_vars = read_env_file(env_file)
        assert len(env_vars) > 0

        # Step 2: Check legacy
        assert is_legacy_format(env_vars) is True

        # Step 3: Backup
        backup_path = backup_env_file(env_file)
        assert backup_path.exists()

        # Step 4: Migrate
        migrated_vars = migrate_to_multi_account(env_vars)

        # Step 5: Write
        write_env_file(env_file, migrated_vars, migrated=True)

        # Step 6: Verify migration
        new_content = env_file.read_text()

        # Should have new format keys
        assert "EMAIL__ACCOUNTS__0__IMAP_HOST=imap.mail.me.com" in new_content
        assert "EMAIL__ACCOUNTS__0__ACCOUNT_ID=default" in new_content
        assert "EMAIL__DEFAULT_ACCOUNT_ID=default" in new_content

        # Should preserve AI config
        assert "AI__ANTHROPIC_API_KEY=sk-ant-api-key-here" in new_content
        assert "AI__CONFIDENCE_THRESHOLD=90" in new_content

        # Should have migration header
        assert "Migrated:" in new_content

        # Step 7: Verify not legacy anymore
        new_env_vars = read_env_file(env_file)
        assert is_legacy_format(new_env_vars) is False

    def test_migration_idempotent(self, tmp_path):
        """Test that migrating already-migrated config is safe"""
        # Create already-migrated .env file
        env_file = tmp_path / ".env"
        migrated_content = """EMAIL__ACCOUNTS__0__ACCOUNT_ID=default
EMAIL__ACCOUNTS__0__IMAP_HOST=imap.mail.me.com
EMAIL__DEFAULT_ACCOUNT_ID=default
"""
        env_file.write_text(migrated_content)

        # Read and check
        env_vars = read_env_file(env_file)

        # Should not be detected as legacy
        assert is_legacy_format(env_vars) is False

        # Migrating should return unchanged
        migrated_vars = migrate_to_multi_account(env_vars)

        # Should be essentially the same (plus account metadata)
        assert migrated_vars["EMAIL__ACCOUNTS__0__IMAP_HOST"] == "imap.mail.me.com"
        assert migrated_vars["EMAIL__ACCOUNTS__0__ACCOUNT_ID"] == "default"
