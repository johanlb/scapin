"""
Unit Tests for IMAP Client

Tests for email fetching and IMAP operations.
"""

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from src.core.config_manager import EmailConfig
from src.core.schemas import EmailContent, EmailMetadata
from src.integrations.email.imap_client import IMAPClient


@pytest.fixture
def email_config():
    """Create test email configuration"""
    return EmailConfig(
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="test@example.com",
        imap_password="test_password",
        inbox_folder="INBOX",
        archive_folder="Archive"
    )


@pytest.fixture
def imap_client(email_config):
    """Create IMAP client with test config"""
    return IMAPClient(email_config)


@pytest.fixture
def sample_email_message():
    """Create sample email message"""
    msg = EmailMessage()
    msg['From'] = '"John Doe" <john@example.com>'
    msg['To'] = 'test@example.com'
    msg['Subject'] = 'Test Email'
    msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
    msg['Message-ID'] = '<test123@example.com>'
    msg.set_content('This is a test email.')
    return msg


class TestIMAPClientInit:
    """Test IMAP client initialization"""

    def test_init_with_config(self, email_config):
        """Test initialization with config"""
        client = IMAPClient(email_config)
        # IMAPClient extracts default account from EmailConfig
        assert client.config == email_config.get_default_account()
        assert client._connection is None

    def test_init_creates_lock(self, imap_client):
        """Test that initialization creates a thread lock"""
        assert hasattr(imap_client, '_lock')


class TestIMAPConnection:
    """Test IMAP connection management"""

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_connect_context_manager(self, mock_imap, imap_client):
        """Test connect context manager"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])

        with imap_client.connect():
            assert imap_client._connection is not None

        # Should be closed after context
        assert imap_client._connection is None
        mock_connection.logout.assert_called_once()

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_establish_connection_success(self, mock_imap, imap_client):
        """Test successful connection establishment"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])

        imap_client._establish_connection()

        assert imap_client._connection is not None
        mock_imap.assert_called_once_with('imap.example.com', 993)
        mock_connection.login.assert_called_once_with('test@example.com', 'test_password')

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_establish_connection_failure(self, mock_imap, imap_client):
        """Test connection failure handling"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError, match="Failed to connect to IMAP server"):
            imap_client._establish_connection()

        assert imap_client._connection is None


class TestEmailFetching:
    """Test email fetching operations"""

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_fetch_emails_basic(self, mock_imap, imap_client, sample_email_message):
        """Test basic email fetching"""
        # Setup mock connection
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])

        # Mock email fetch - batch format: (header_with_BODY[], raw_email), b')'
        raw_email = sample_email_message.as_bytes()
        batch_response = [
            (b'1 (BODY[] {%d}' % len(raw_email), raw_email),
            b')',
        ]

        # The implementation uses uid() for all operations
        def uid_side_effect(command, *args):
            if command == "SEARCH":
                return ('OK', [b'1'])
            elif command == "FETCH":
                return ('OK', batch_response)
            return ('OK', [b'Success'])

        mock_connection.uid.side_effect = uid_side_effect

        with imap_client.connect():
            emails = imap_client.fetch_emails(folder="INBOX", limit=1)

        assert len(emails) == 1
        metadata, content = emails[0]
        assert isinstance(metadata, EmailMetadata)
        assert isinstance(content, EmailContent)
        assert metadata.subject == 'Test Email'
        assert metadata.from_address == 'john@example.com'

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_fetch_emails_with_limit(self, mock_imap, imap_client, sample_email_message):
        """Test fetching with limit applies correctly"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'5'])

        # Mock batch response with 2 emails (limited from 5)
        raw_email = sample_email_message.as_bytes()
        batch_response = [
            (b'1 (BODY[] {%d}' % len(raw_email), raw_email),
            b')',
            (b'2 (BODY[] {%d}' % len(raw_email), raw_email),
            b')',
        ]

        # Track FETCH calls
        fetch_calls = []

        def uid_side_effect(command, *args):
            if command == "SEARCH":
                return ('OK', [b'1 2 3 4 5'])
            elif command == "FETCH":
                fetch_calls.append(args)
                return ('OK', batch_response)
            return ('OK', [b'Success'])

        mock_connection.uid.side_effect = uid_side_effect

        with imap_client.connect():
            emails = imap_client.fetch_emails(folder="INBOX", limit=2)

        # With batch fetching, we should have exactly 1 fetch call for all emails in the batch
        assert len(fetch_calls) == 1
        # The fetch should have been called with both message IDs (1,2 - the 2 most recent after reverse)
        # After reversal and limit: [5,4,3,2,1] -> limit 2 -> [5,4] -> sort back -> [4,5]
        fetch_arg = fetch_calls[0][0]  # First FETCH call, first argument (msg_set)
        # fetch_arg is a string like "4,5", check it contains both IDs
        assert '4' in fetch_arg and '5' in fetch_arg

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_fetch_emails_unread_only(self, mock_imap, imap_client):
        """Test fetching unread emails only"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'0'])

        # Track uid calls
        uid_calls = []

        def uid_side_effect(command, *args):
            uid_calls.append((command, args))
            if command == "SEARCH":
                return ('OK', [b''])
            return ('OK', [b'Success'])

        mock_connection.uid.side_effect = uid_side_effect

        with imap_client.connect():
            imap_client.fetch_emails(folder="INBOX", unread_only=True)

        # Should search for UNSEEN via uid command
        search_calls = [c for c in uid_calls if c[0] == "SEARCH"]
        assert len(search_calls) >= 1
        # The search criteria should contain UNSEEN
        assert "UNSEEN" in search_calls[0][1][1]

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_fetch_emails_empty_folder(self, mock_imap, imap_client):
        """Test fetching from empty folder"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'0'])

        def uid_side_effect(command, *args):
            if command == "SEARCH":
                return ('OK', [b''])
            return ('OK', [b'Success'])

        mock_connection.uid.side_effect = uid_side_effect

        with imap_client.connect():
            emails = imap_client.fetch_emails(folder="INBOX")

        assert emails == []

    def test_fetch_emails_not_connected(self, imap_client):
        """Test fetching without connection raises error"""
        with pytest.raises(RuntimeError, match="Not connected"):
            imap_client.fetch_emails()


class TestEmailMetadataExtraction:
    """Test email metadata extraction"""

    def test_extract_metadata_basic(self, imap_client, sample_email_message):
        """Test basic metadata extraction"""
        metadata = imap_client._extract_metadata(
            sample_email_message,
            b'123',
            'INBOX'
        )

        assert metadata.id == 123
        assert metadata.folder == 'INBOX'
        assert metadata.subject == 'Test Email'
        assert metadata.from_address == 'john@example.com'
        assert metadata.from_name == 'John Doe'
        assert 'test@example.com' in metadata.to_addresses
        # Implementation strips angle brackets from message_id
        assert metadata.message_id == 'test123@example.com'

    def test_extract_metadata_no_from_name(self, imap_client):
        """Test metadata extraction without from name"""
        msg = EmailMessage()
        msg['From'] = 'test@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Test'
        msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
        msg.set_content('Test')

        metadata = imap_client._extract_metadata(msg, b'1', 'INBOX')

        assert metadata.from_address == 'test@example.com'
        assert metadata.from_name == ''

    def test_has_attachments_true(self, imap_client):
        """Test attachment detection"""
        msg = EmailMessage()
        msg['From'] = 'test@example.com'
        msg['Subject'] = 'Test'

        # Add attachment
        msg.add_attachment(b'file content', maintype='application', subtype='pdf', filename='test.pdf')

        has_attachments = imap_client._has_attachments(msg)
        assert has_attachments is True

    def test_has_attachments_false(self, imap_client, sample_email_message):
        """Test no attachments"""
        has_attachments = imap_client._has_attachments(sample_email_message)
        assert has_attachments is False


class TestEmailContentExtraction:
    """Test email content extraction"""

    def test_extract_content_plain_text(self, imap_client):
        """Test plain text extraction"""
        msg = EmailMessage()
        msg.set_content('This is plain text content.')

        content = imap_client._extract_content(msg)

        assert content.plain_text == 'This is plain text content.'
        assert content.html == ''

    def test_extract_content_html(self, imap_client):
        """Test HTML extraction"""
        msg = EmailMessage()
        msg.set_content('Plain text')
        msg.add_alternative('<p>HTML content</p>', subtype='html')

        content = imap_client._extract_content(msg)

        assert 'Plain text' in content.plain_text or content.plain_text == 'Plain text'
        assert '<p>HTML content</p>' in content.html

    def test_extract_content_with_attachments(self, imap_client):
        """Test content extraction with attachments"""
        msg = EmailMessage()
        msg.set_content('Email with attachment')
        msg.add_attachment(b'data', maintype='application', subtype='pdf', filename='test.pdf')

        content = imap_client._extract_content(msg)

        assert 'test.pdf' in content.attachments


class TestEmailActions:
    """Test email actions (mark as read, move)"""

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_mark_as_read(self, mock_imap, imap_client):
        """Test marking email as read"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])

        # Track uid STORE calls
        store_calls = []

        def uid_side_effect(command, *args):
            if command == "STORE":
                store_calls.append(args)
            return ('OK', [b'Success'])

        mock_connection.uid.side_effect = uid_side_effect

        with imap_client.connect():
            result = imap_client.mark_as_read(123, "INBOX")

        assert result is True
        assert len(store_calls) >= 1  # At least one STORE call for \\Seen flag

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_move_email(self, mock_imap, imap_client):
        """Test moving email to different folder"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])
        mock_connection.select.return_value = ('OK', [b'1'])

        # Track uid COPY and STORE calls
        uid_calls = []

        def uid_side_effect(command, *args):
            uid_calls.append((command, args))
            return ('OK', [b'Success'])

        mock_connection.uid.side_effect = uid_side_effect

        with imap_client.connect():
            result = imap_client.move_email(123, "INBOX", "Archive")

        assert result is True
        # Should have COPY and STORE (for delete flag) calls
        copy_calls = [c for c in uid_calls if c[0] == "COPY"]
        store_calls = [c for c in uid_calls if c[0] == "STORE"]
        assert len(copy_calls) >= 1
        assert len(store_calls) >= 1
        # Note: Implementation explicitly does NOT call expunge() to avoid
        # shifting sequence numbers for other operations

    def test_mark_as_read_not_connected(self, imap_client):
        """Test mark as read without connection raises error"""
        with pytest.raises(RuntimeError, match="Not connected"):
            imap_client.mark_as_read(123)

    def test_move_email_not_connected(self, imap_client):
        """Test move email without connection raises error"""
        with pytest.raises(RuntimeError, match="Not connected"):
            imap_client.move_email(123, "INBOX", "Archive")


class TestIMAPRobustness:
    """Test IMAP robustness against real-world issues"""

    def test_extract_metadata_empty_to_addresses(self, imap_client):
        """Test handling of emails without valid To addresses"""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = ''  # Empty To field
        msg['Subject'] = 'Test'
        msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
        msg.set_content('Test')

        metadata = imap_client._extract_metadata(msg, b'1', 'INBOX')

        # Should use placeholder instead of empty list
        assert len(metadata.to_addresses) > 0
        assert 'no-recipient@unknown.com' in metadata.to_addresses

    def test_extract_metadata_invalid_to_addresses(self, imap_client):
        """Test filtering of invalid email addresses (no @)"""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'invalid-email, valid@example.com'
        msg['Subject'] = 'Test'
        msg['Date'] = 'Mon, 15 Jan 2025 10:30:00 +0000'
        msg.set_content('Test')

        metadata = imap_client._extract_metadata(msg, b'1', 'INBOX')

        # Should only include valid email
        assert 'valid@example.com' in metadata.to_addresses
        assert 'invalid-email' not in metadata.to_addresses

    def test_extract_metadata_empty_date(self, imap_client):
        """Test handling of emails without Date header"""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Test'
        # No Date header
        msg.set_content('Test')

        metadata = imap_client._extract_metadata(msg, b'1', 'INBOX')

        # Should use current UTC time as fallback
        assert metadata.date is not None
        assert metadata.date.tzinfo is not None  # Must have timezone

    def test_extract_metadata_naive_datetime(self, imap_client):
        """Test handling of dates without timezone"""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Test'
        msg['Date'] = '15 Jan 2025 10:30:00'  # No timezone
        msg.set_content('Test')

        metadata = imap_client._extract_metadata(msg, b'1', 'INBOX')

        # Should assume UTC for naive datetimes
        assert metadata.date.tzinfo is not None

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_fetch_single_email_invalid_response_structure(self, mock_imap, imap_client):
        """Test handling of invalid IMAP response structures"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])

        # Simulate malformed IMAP response (integer instead of bytes/tuple)
        # This is what we saw in the real bug
        # Implementation uses uid("FETCH", ...) not fetch()
        mock_connection.uid.return_value = ('OK', [(123, None)])

        imap_client._connection = mock_connection
        result = imap_client._fetch_single_email(b'123', 'INBOX')

        # Should return None for truly invalid structure (non-bytes content)
        assert result is None

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_fetch_single_email_empty_response(self, mock_imap, imap_client):
        """Test handling of empty IMAP fetch response"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])

        # Empty response - implementation uses uid("FETCH", ...)
        mock_connection.uid.return_value = ('OK', None)

        imap_client._connection = mock_connection
        result = imap_client._fetch_single_email(b'123', 'INBOX')

        # Should return None
        assert result is None

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_fetch_single_email_not_ok_status(self, mock_imap, imap_client):
        """Test handling of non-OK IMAP fetch status"""
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.return_value = ('OK', [b'Success'])

        # Non-OK status - implementation uses uid("FETCH", ...)
        mock_connection.uid.return_value = ('NO', [b'Error'])

        imap_client._connection = mock_connection
        result = imap_client._fetch_single_email(b'123', 'INBOX')

        # Should return None
        assert result is None

    def test_extract_content_charset_detection(self, imap_client):
        """Test charset detection for non-UTF8 content"""
        msg = EmailMessage()
        # Simulate ISO-8859-1 encoded content
        msg.set_content('Test content', charset='iso-8859-1')

        content = imap_client._extract_content(msg)

        # Should decode successfully
        assert 'Test content' in content.plain_text

    def test_extract_content_malformed_encoding(self, imap_client):
        """Test handling of malformed encoding"""
        msg = EmailMessage()
        msg.set_content('Test')

        # This should not crash even with encoding issues
        content = imap_client._extract_content(msg)

        assert isinstance(content, EmailContent)

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_connection_timeout(self, mock_imap, imap_client):
        """Test handling of connection timeout"""
        import socket

        mock_connection = MagicMock()
        mock_imap.side_effect = socket.timeout("Connection timeout")

        with pytest.raises(ConnectionError, match="timeout"):
            imap_client._establish_connection()

    @patch('src.integrations.email.imap_client.imaplib.IMAP4_SSL')
    def test_login_failure(self, mock_imap, imap_client):
        """Test handling of authentication failure"""
        import imaplib

        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.login.side_effect = imaplib.IMAP4.error("Authentication failed")

        with pytest.raises(ConnectionError, match="Failed to connect"):
            imap_client._establish_connection()

        # Connection should be cleared
        assert imap_client._connection is None
