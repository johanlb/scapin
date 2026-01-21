"""
End-to-End Tests for Email Processing

Tests complete email processing workflow based on real bugs discovered.
"""

from datetime import timezone
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from src.core.config_manager import AIConfig, EmailConfig
from src.core.schemas import EmailAction, EmailCategory
from src.integrations.email.imap_client import IMAPClient
from src.sancho.router import AIRouter


def setup_imap_mock_for_uid(mock_connection, raw_emails: list[bytes], search_ids: str = "1"):
    """
    Setup IMAP mock to use uid() command properly.

    The IMAPClient implementation uses uid() for all operations:
    - uid("SEARCH", ...) for searching
    - uid("FETCH", ...) for fetching

    Args:
        mock_connection: The MagicMock connection object
        raw_emails: List of raw email bytes to return
        search_ids: Space-separated string of message IDs (e.g., "1" or "1 2")
    """
    # Build batch response from raw emails
    batch_response = []
    for i, raw_email in enumerate(raw_emails, 1):
        batch_response.append((f'{i} (BODY[] {{{len(raw_email)}}}'.encode(), raw_email))
        batch_response.append(b')')

    def uid_side_effect(command, *args):
        if command == "SEARCH":
            return ('OK', [search_ids.encode()])
        elif command == "FETCH":
            return ('OK', batch_response)
        return ('OK', [b'Success'])

    mock_connection.uid.side_effect = uid_side_effect


@pytest.fixture
def mock_email_config():
    """Create mock email configuration"""
    return EmailConfig(
        imap_host="imap.test.com",
        imap_port=993,
        imap_username="test@test.com",
        imap_password="test_password"
    )


@pytest.fixture
def mock_ai_config():
    """Create mock AI configuration"""
    return AIConfig(
        anthropic_api_key="sk-test-key",
        confidence_threshold=90,
        rate_limit_per_minute=40
    )


class TestEmailProcessingE2E:
    """End-to-end tests for complete email processing workflow"""

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    @patch('anthropic.Anthropic')
    def test_process_email_with_missing_to_addresses(
        self,
        mock_anthropic,
        mock_imap,
        mock_email_config,
        mock_ai_config
    ):
        """
        Test: Email without To addresses (Bug discovered during testing)

        This simulates emails like drafts or BCCs that may not have To addresses.
        Should use placeholder email instead of empty list.
        """
        # Create email without To field
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = ''  # Empty To field
        msg['Subject'] = 'Draft Email'
        msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
        msg.set_content('This is a draft email with no recipients.')

        # Setup mock IMAP using uid() properly
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])
        setup_imap_mock_for_uid(mock_connection, [msg.as_bytes()])

        # Setup mock AI response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='''```json
{
    "action": "archive",
    "category": "other",
    "confidence": 85,
    "reasoning": "Draft email",
    "priority": "low"
}
```''')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        # Create IMAP client and fetch email
        imap_client = IMAPClient(mock_email_config)

        with imap_client.connect():
            emails = imap_client.fetch_emails(limit=1)

        # Should successfully fetch email with placeholder To address
        assert len(emails) == 1
        metadata, content = emails[0]

        # Bug fix: Should have placeholder instead of empty list
        assert len(metadata.to_addresses) > 0
        assert 'no-recipient@unknown.com' in metadata.to_addresses

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_process_email_with_missing_date_header(
        self,
        mock_imap,
        mock_email_config
    ):
        """
        Test: Email without Date header (Bug discovered during testing)

        Some emails may not have a Date header. Should fallback to current UTC time.
        """
        # Create email without Date field
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Email Without Date'
        # No Date header
        msg.set_content('This email has no date.')

        # Setup mock IMAP using uid() properly
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])
        setup_imap_mock_for_uid(mock_connection, [msg.as_bytes()])

        # Create IMAP client and fetch email
        imap_client = IMAPClient(mock_email_config)

        with imap_client.connect():
            emails = imap_client.fetch_emails(limit=1)

        # Should successfully fetch email with fallback date
        assert len(emails) == 1
        metadata, content = emails[0]

        # Bug fix: Should have a valid timezone-aware datetime
        assert metadata.date is not None
        assert metadata.date.tzinfo is not None
        assert metadata.date.tzinfo == timezone.utc

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    @patch('anthropic.Anthropic')
    @patch('src.sancho.templates.get_template_manager')
    def test_process_email_with_uppercase_enums_from_ai(
        self,
        mock_get_tm,
        mock_anthropic,
        mock_imap,
        mock_email_config,
        mock_ai_config
    ):
        """
        Test: AI returns uppercase enum values (Bug discovered during testing)

        Claude sometimes returns "DELETE" instead of "delete", "SPAM" instead of "spam".
        Should normalize to lowercase before validation.
        """
        # Mock template manager to return a simple prompt
        mock_tm = MagicMock()
        mock_tm.render.return_value = "Analyze this email"
        mock_get_tm.return_value = mock_tm

        # Create normal email
        msg = EmailMessage()
        msg['From'] = 'spammer@spam.com'
        msg['To'] = 'victim@example.com'
        msg['Subject'] = 'Buy cheap viagra!'
        msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
        msg.set_content('This is obvious spam.')

        # Setup mock IMAP using uid() properly
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])
        setup_imap_mock_for_uid(mock_connection, [msg.as_bytes()])

        # Setup mock AI response with UPPERCASE enums
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='''```json
{
    "action": "DELETE",
    "category": "SPAM",
    "confidence": 95,
    "reasoning": "Obvious spam email",
    "priority": "LOW"
}
```''')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        # Create AI router
        ai_router = AIRouter(mock_ai_config)
        ai_router.anthropic = mock_client

        # Create IMAP client and fetch email
        imap_client = IMAPClient(mock_email_config)

        with imap_client.connect():
            emails = imap_client.fetch_emails(limit=1)

        metadata, content = emails[0]

        # Analyze email
        analysis = ai_router.analyze_email(metadata, content)

        # Bug fix: Should successfully parse despite uppercase enums
        assert analysis is not None
        assert analysis.action == EmailAction.DELETE  # Normalized to lowercase
        assert analysis.category == EmailCategory.SPAM  # Normalized to lowercase
        assert analysis.confidence == 95

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_process_email_with_malformed_imap_response(
        self,
        mock_imap,
        mock_email_config
    ):
        """
        Test: Malformed IMAP response structure (Bug discovered during testing)

        Some IMAP servers return unexpected response structures.
        Should handle gracefully and skip the email.
        """
        # Create a valid email message
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Valid Email'
        msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
        msg.set_content('Valid email content')

        # Setup mock IMAP with mixed malformed and valid response
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])

        raw_email = msg.as_bytes()
        # Build custom response with malformed entry
        batch_response = [
            b'malformed_response',  # Malformed entry (should be skipped)
            (b'2 (BODY[] {%d}' % len(raw_email), raw_email),  # Valid entry
            b')',
        ]

        def uid_side_effect(command, *args):
            if command == "SEARCH":
                return ('OK', [b'1 2'])
            elif command == "FETCH":
                return ('OK', batch_response)
            return ('OK', [b'Success'])

        mock_connection.uid.side_effect = uid_side_effect

        # Create IMAP client and fetch emails
        imap_client = IMAPClient(mock_email_config)

        with imap_client.connect():
            emails = imap_client.fetch_emails(limit=2)

        # Our code is robust enough to skip malformed entries
        # and parse the valid ones
        assert len(emails) >= 1

        # Should have successfully fetched the valid email
        valid_emails = [e for e in emails if e[0].subject == 'Valid Email']
        assert len(valid_emails) == 1

    def test_processing_stats_with_missing_methods(self):
        """
        Test: StateManager missing get_average_confidence() method

        (Bug discovered during testing that caused AttributeError crash)
        Should gracefully handle missing methods with fallback values.
        """
        from src.core.state_manager import StateManager

        # Create state manager
        state = StateManager()

        # Add some confidence scores
        state.add_confidence_score(90)
        state.add_confidence_score(95)
        state.add_confidence_score(85)

        # Bug fix: Should have get_average_confidence method
        assert hasattr(state, 'get_average_confidence')
        avg = state.get_average_confidence()

        # Should return correct average
        assert avg == 90.0  # (90 + 95 + 85) / 3

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_connection_error_handling(
        self,
        mock_imap,
        mock_email_config
    ):
        """
        Test: IMAP connection errors should be handled gracefully

        Should raise ConnectionError with helpful message.
        """
        import imaplib

        # Setup mock IMAP to fail login
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.side_effect = imaplib.IMAP4.error("Bad credentials")

        # Create IMAP client
        imap_client = IMAPClient(mock_email_config)

        # Bug fix: Should raise ConnectionError, not imaplib.IMAP4.error
        with pytest.raises(ConnectionError, match="Failed to connect"):
            imap_client._establish_connection()

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_invalid_email_addresses_filtered(
        self,
        mock_imap,
        mock_email_config
    ):
        """
        Test: Invalid email addresses without @ should be filtered

        Some email headers may contain invalid addresses.
        Should filter them out to prevent Pydantic validation errors.
        """
        # Create email with mix of valid and invalid addresses
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'valid@example.com, invalid-email, another@example.com'
        msg['Subject'] = 'Test Email'
        msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
        msg.set_content('Test content')

        # Setup mock IMAP using uid() properly
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])
        setup_imap_mock_for_uid(mock_connection, [msg.as_bytes()])

        # Create IMAP client and fetch email
        imap_client = IMAPClient(mock_email_config)

        with imap_client.connect():
            emails = imap_client.fetch_emails(limit=1)

        # Bug fix: Should only include valid email addresses
        assert len(emails) == 1
        metadata, content = emails[0]

        # Should have filtered out invalid addresses
        assert 'valid@example.com' in metadata.to_addresses
        assert 'another@example.com' in metadata.to_addresses
        assert 'invalid-email' not in metadata.to_addresses
