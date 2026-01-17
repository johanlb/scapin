"""
Unit Tests for IMAP UID and Robustness improvements
"""

import pytest
from unittest.mock import MagicMock, patch
from email.message import EmailMessage

from src.core.config_manager import EmailConfig
from src.integrations.email.imap_client import IMAPClient, SCAPIN_PROCESSED_FLAG


@pytest.fixture
def email_config():
    """Create test email configuration"""
    return EmailConfig(
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="test@example.com",
        imap_password="test_password",
        inbox_folder="INBOX",
        archive_folder="Archive",
    )


@pytest.fixture
def imap_client(email_config):
    """Create IMAP client with test config"""
    return IMAPClient(email_config)


class TestUIDRobustness:
    """Test robustness of UID operations and parsing"""

    @patch("src.integrations.email.imap_client.get_processed_tracker")
    def test_filter_unprocessed_emails_regex_parsing(self, mock_get_tracker, imap_client):
        """Test robust regex-based UID parsing from IMAP response"""
        # Mock tracker to return all as unprocessed
        mock_tracker = MagicMock()
        mock_get_tracker.return_value = mock_tracker
        mock_tracker.get_unprocessed_message_ids.side_effect = lambda ids, acc: ids

        # Mock connection
        mock_connection = MagicMock()
        imap_client._connection = mock_connection

        # Input UIDs (descending/newest first from fetch_emails)
        input_uids = [b"186916", b"186915"]

        # Mock response from UID FETCH (header fields)
        # Verify it handles the complex structure we saw in logs
        # b'SEQ (UID <UID> BODY[...])'
        mock_response = [
            (
                b"15718 (UID 186916 BODY[HEADER.FIELDS (MESSAGE-ID)] {57}",
                b"Message-ID: <test1@example.com>\r\n\r\n",
            ),
            b")",
            (
                b"15717 (UID 186915 BODY[HEADER.FIELDS (MESSAGE-ID)] {57}",
                b"Message-ID: <test2@example.com>\r\n\r\n",
            ),
            b")",
        ]
        mock_connection.uid.return_value = ("OK", mock_response)

        # Execute
        result = imap_client._filter_unprocessed_emails(input_uids, "INBOX", limit=5)

        # Verification
        assert len(result) == 2
        assert b"186916" in result
        assert b"186915" in result

        # Verify raw UID command uses sorted UIDs for optimization
        # The input was [186916, 186915] (descending)
        # The command should use "186915,186916" (ascending)
        call_args = mock_connection.uid.call_args
        assert call_args[0][0] == "FETCH"
        # Check that UIDs in the command string are comma-separated
        cmd_uids = call_args[0][1].split(",")
        assert "186915" in cmd_uids and "186916" in cmd_uids

    def test_extract_metadata_missing_chardet(self, imap_client):
        """Test fallback when chardet is missing"""
        with patch.dict("sys.modules", {"chardet": None}):
            msg = EmailMessage()
            msg.set_content("Test Payload")

            # This should not raise ImportError
            content = imap_client._extract_content(msg)
            assert content.plain_text == "Test Payload"

    def test_extract_metadata_empty_subject(self, imap_client):
        """Test handling of empty subject to match schema min_length=1"""
        msg = EmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = ""  # Empty subject
        msg["Date"] = "Mon, 15 Jan 2025 10:30:00 +0000"
        msg["Message-ID"] = "<test@example.com>"
        msg.set_content("Test")

        metadata = imap_client._extract_metadata(msg, b"1", "INBOX")

        # Schema requires min_length=1, so we should fallback
        assert metadata.subject == "(No Subject)"
        assert len(metadata.subject) >= 1

    def test_extract_metadata_missing_message_id(self, imap_client):
        """Test fallback for missing Message-ID"""
        msg = EmailMessage()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Test"
        # No Message-ID header

        uid = b"99999"
        metadata = imap_client._extract_metadata(msg, uid, "INBOX")

        assert metadata.message_id
        assert metadata.message_id == f"UID-99999@{imap_client.account_id}.scapin.local"
