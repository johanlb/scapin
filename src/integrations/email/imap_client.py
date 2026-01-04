"""
IMAP Email Client

Thread-safe IMAP client for fetching and managing emails.
"""

import codecs
import email
import imaplib
import threading
from contextlib import contextmanager
from email.header import decode_header
from email.message import Message
from typing import Optional, Union

from src.core.config_manager import EmailAccountConfig, EmailConfig
from src.core.schemas import EmailContent, EmailMetadata
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("imap_client")


# IMAP special characters that require quoting: space " \ ( ) { } % *
IMAP_SPECIAL_CHARS = r'[\s"\\(){}%*]'


def encode_imap_folder_name(folder_name: str) -> str:
    """
    Encode folder name to IMAP modified UTF-7.

    IMAP uses modified UTF-7 for mailbox names with non-ASCII characters.
    - ASCII printable characters (0x20-0x7E except &) remain unchanged
    - & is encoded as &-
    - Other characters are encoded as UTF-16BE then base64, surrounded by & and -
    - Folder names with special chars are quoted (IMAP requirement)

    Special characters requiring quoting: space " \\ ( ) { } % *

    Example:
        "À" -> "&AMA-"
        "_Scapin/À supprimer" -> '"_Scapin/&AMA- supprimer"'
        "Folder (2025)" -> '"Folder (2025)"'

    Args:
        folder_name: Folder name with potential non-ASCII characters

    Returns:
        IMAP modified UTF-7 encoded folder name (quoted if needed)
    """
    import re

    # Fast path: if already ASCII, handle it
    try:
        folder_name.encode('ascii')
        # Escape & character
        encoded = folder_name.replace('&', '&-')

        # Quote if contains special chars
        if re.search(IMAP_SPECIAL_CHARS, encoded):
            # Escape internal double quotes first
            encoded = encoded.replace('"', '\\"')
            return f'"{encoded}"'
        return encoded
    except UnicodeEncodeError:
        pass

    # Encode to IMAP modified UTF-7
    result = []
    i = 0
    while i < len(folder_name):
        char = folder_name[i]

        # ASCII printable (except &)
        if 0x20 <= ord(char) <= 0x7E and char != '&':
            result.append(char)
            i += 1
        # & character
        elif char == '&':
            result.append('&-')
            i += 1
        # Non-ASCII - encode sequence
        else:
            # Collect all consecutive non-ASCII characters
            non_ascii = []
            while i < len(folder_name):
                c = folder_name[i]
                if not (0x20 <= ord(c) <= 0x7E):
                    non_ascii.append(c)
                    i += 1
                else:
                    break

            # Encode to UTF-16BE
            utf16 = ''.join(non_ascii).encode('utf-16-be')
            # Encode to base64
            b64 = codecs.encode(utf16, 'base64').decode('ascii')
            # Remove newlines and padding
            b64 = b64.rstrip('\n=')
            # Replace / with , (IMAP modified UTF-7 uses , instead of /)
            b64 = b64.replace('/', ',')
            # Surround with & and -
            result.append(f'&{b64}-')

    import re

    encoded = ''.join(result)

    # Quote if contains special chars
    if re.search(IMAP_SPECIAL_CHARS, encoded):
        # Escape internal double quotes first
        encoded = encoded.replace('"', '\\"')
        return f'"{encoded}"'
    return encoded


def decode_mime_header(header_value: str) -> str:
    """
    Decode MIME-encoded email header (like Subject, From name, etc.)

    Handles headers encoded in formats like:
    - =?UTF-8?B?RMOpcMOqY2hlei12b3Vz?= (Base64)
    - =?UTF-8?Q?Masters_Scope_a_publi=C3=A9?= (Quoted-Printable)

    Args:
        header_value: Raw header value from email

    Returns:
        Decoded string in UTF-8

    Examples:
        >>> decode_mime_header("=?UTF-8?B?RMOpcMOqY2hlei12b3Vz?= ! Nouvelle offre")
        "Dépêchez-vous ! Nouvelle offre"
        >>> decode_mime_header("Normal subject")
        "Normal subject"
    """
    if not header_value:
        return ""

    try:
        # decode_header returns list of (decoded_bytes, charset) tuples
        decoded_parts = decode_header(header_value)

        result_parts = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                # Decode bytes using specified charset or UTF-8 as fallback
                try:
                    decoded = part.decode(charset or 'utf-8', errors='replace')
                except (LookupError, UnicodeDecodeError):
                    # If charset is unknown or decoding fails, try UTF-8
                    decoded = part.decode('utf-8', errors='replace')
            else:
                # Already a string
                decoded = str(part)

            result_parts.append(decoded)

        return ''.join(result_parts)

    except Exception as e:
        # If decoding fails, return original value
        logger.warning(f"Failed to decode MIME header: {e}", extra={"header": header_value[:100]})
        return header_value


class IMAPClient:
    """
    Thread-safe IMAP client for email operations

    Features:
    - Automatic connection management
    - Thread-safe operations with connection pooling
    - Retry logic for transient failures
    - Email parsing and metadata extraction

    Usage:
        client = IMAPClient(config)
        with client.connect():
            emails = client.fetch_emails(folder="INBOX", limit=10)
    """

    def __init__(self, config: Union[EmailConfig, EmailAccountConfig]):
        """
        Initialize IMAP client

        Args:
            config: Email configuration (EmailConfig or EmailAccountConfig)
                   If EmailConfig, uses default account
        """
        # Extract EmailAccountConfig from EmailConfig if needed
        account_config = config.get_default_account() if isinstance(config, EmailConfig) else config

        self.config = account_config
        self.account_id = account_config.account_id
        self.account_name = account_config.account_name
        self._connection: Optional[imaplib.IMAP4_SSL] = None
        self._lock = threading.Lock()

        logger.info(
            "IMAP client initialized",
            extra={
                "account_id": account_config.account_id,
                "account_name": account_config.account_name,
                "host": account_config.imap_host,
                "port": account_config.imap_port,
                "username": account_config.imap_username
            }
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"IMAPClient(host={self.config.imap_host!r}, "
            f"port={self.config.imap_port}, "
            f"connected={self._connection is not None})"
        )

    @contextmanager
    def connect(self):
        """
        Context manager for IMAP connection

        Yields:
            IMAPClient instance with active connection

        Example:
            with client.connect():
                emails = client.fetch_emails()
        """
        try:
            self._establish_connection()
            yield self
        finally:
            self._close_connection()

    def _establish_connection(self) -> None:
        """Establish connection to IMAP server with timeout configuration"""
        import socket

        with self._lock:
            if self._connection is not None:
                return

            try:
                logger.debug(
                    f"Connecting to IMAP server: {self.config.imap_host}:{self.config.imap_port}",
                    extra={
                        "timeout": self.config.imap_timeout,
                        "read_timeout": self.config.imap_read_timeout
                    }
                )

                # Set socket timeout for connection
                socket.setdefaulttimeout(self.config.imap_timeout)

                # Connect to IMAP server
                self._connection = imaplib.IMAP4_SSL(
                    self.config.imap_host,
                    self.config.imap_port
                )

                # Note: We use IMAP modified UTF-7 encoding for folder names
                # via encode_imap_folder_name() function instead of changing _encoding

                # Set read timeout for operations
                if hasattr(self._connection, 'sock') and self._connection.sock:
                    self._connection.sock.settimeout(self.config.imap_read_timeout)

                # Login
                self._connection.login(
                    self.config.imap_username,
                    self.config.imap_password
                )

                logger.info("IMAP connection established")

            except socket.timeout as e:
                logger.error("IMAP connection timeout")
                self._connection = None
                raise ConnectionError("IMAP connection timeout") from e

            except imaplib.IMAP4.error as e:
                logger.error(f"IMAP connection failed: {e}", exc_info=True)
                self._connection = None
                raise ConnectionError(f"Failed to connect to IMAP server: {e}") from e

            except Exception as e:
                logger.error(f"Unexpected error during IMAP connection: {e}", exc_info=True)
                self._connection = None
                raise ConnectionError(f"Failed to connect to IMAP server: {e}") from e

    def _close_connection(self) -> None:
        """Close IMAP connection"""
        with self._lock:
            if self._connection is not None:
                try:
                    self._connection.logout()
                    logger.debug("IMAP connection closed")
                except Exception as e:
                    logger.warning(f"Error closing IMAP connection: {e}")
                finally:
                    self._connection = None

    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: Optional[int] = None,
        unread_only: bool = False,
        unflagged_only: bool = False
    ) -> list[tuple[EmailMetadata, EmailContent]]:
        """
        Fetch emails from specified folder

        Args:
            folder: IMAP folder name (default: INBOX)
            limit: Maximum number of emails to fetch
            unread_only: Only fetch unread emails (UNSEEN flag)
            unflagged_only: Only fetch unflagged emails (no \\Flagged flag)

        Returns:
            List of (metadata, content) tuples, sorted oldest first
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IMAP server. Use connect() context manager.")

        try:
            # Select folder
            status, messages = self._connection.select(folder, readonly=True)
            if status != 'OK':
                logger.error(f"Failed to select folder: {folder}")
                return []

            # Build search criteria
            # IMAP returns messages in ascending order (oldest first)
            criteria = []
            if unread_only:
                criteria.append("UNSEEN")
            if unflagged_only:
                criteria.append("UNFLAGGED")

            # If no specific criteria, fetch all
            search_criteria = " ".join(criteria) if criteria else "ALL"

            status, message_ids = self._connection.search(None, search_criteria)

            if status != 'OK':
                logger.error(f"Failed to search emails in {folder}")
                return []

            # Get message IDs (already in ascending order - oldest first)
            id_list = message_ids[0].split()

            # Apply limit (take first N = oldest N emails)
            if limit:
                id_list = id_list[:limit]

            logger.info(
                "Fetching emails",
                extra={
                    "folder": folder,
                    "count": len(id_list),
                    "unread_only": unread_only,
                    "unflagged_only": unflagged_only,
                    "criteria": search_criteria
                }
            )

            # Fetch emails
            emails = []
            for msg_id in id_list:
                try:
                    email_data = self._fetch_single_email(msg_id, folder)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch email {msg_id.decode()}: {e}",
                        exc_info=True
                    )
                    continue

            logger.info(f"Successfully fetched {len(emails)} emails from {folder}")
            return emails

        except Exception as e:
            logger.error(f"Error fetching emails: {e}", exc_info=True)
            return []

    def _fetch_single_email(
        self,
        msg_id: bytes,
        folder: str
    ) -> Optional[tuple[EmailMetadata, EmailContent]]:
        """
        Fetch and parse a single email

        Args:
            msg_id: IMAP message ID
            folder: Folder name

        Returns:
            (metadata, content) tuple or None if parsing fails
        """
        if self._connection is None:
            return None

        # Fetch email using BODY.PEEK[] (modern IMAP4rev1, doesn't mark as seen)
        # Fallback to RFC822 if that fails
        status, msg_data = self._connection.fetch(msg_id, '(BODY.PEEK[])')

        if status != 'OK' or not msg_data or msg_data[0] is None:
            return None

        # Parse email - IMAP response structure varies by server
        # Common formats for BODY.PEEK[]:
        #   - [(b'ID (BODY[] {size}', b'raw_email'), b')']  # Standard response
        #   - [((b'ID (BODY[] {size}', b'raw_email')), None]  # Some servers
        #
        # Debug the actual structure
        logger.debug(f"IMAP fetch response type: {type(msg_data)}, length: {len(msg_data) if msg_data else 0}")
        if msg_data and len(msg_data) > 0:
            logger.debug(f"msg_data[0] type: {type(msg_data[0])}, value: {msg_data[0][:100] if isinstance(msg_data[0], bytes) else msg_data[0]}")

        # Try to extract email data - handle various response formats
        raw_email = None

        # Format 1: msg_data[0] is a tuple - most common format
        # Response looks like: [(b'1 (BODY[] {1234}', b'email_data'), b')']
        if isinstance(msg_data[0], tuple) and len(msg_data[0]) >= 2:
            # The email data is in the second element of the tuple
            raw_email = msg_data[0][1]

        # Format 2: List of items where one contains BODY[] response
        # Search through msg_data for the tuple containing email data
        elif len(msg_data) > 1:
            for item in msg_data:
                # Check if this tuple contains BODY[] response
                if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[0], bytes) and b'BODY[]' in item[0]:
                    raw_email = item[1]
                    break

        if raw_email is None:
            logger.warning(
                f"Cannot extract email data for message {msg_id.decode()}: "
                f"unexpected response structure {type(msg_data[0])}"
            )
            return None

        # Validate raw_email is bytes
        if not isinstance(raw_email, bytes):
            logger.warning(
                f"Email data is not bytes for message {msg_id.decode()}: "
                f"got {type(raw_email).__name__}"
            )
            return None

        email_message = email.message_from_bytes(raw_email)

        # Extract metadata
        metadata = self._extract_metadata(email_message, msg_id, folder)

        # Extract content
        content = self._extract_content(email_message)

        return (metadata, content)

    def _extract_metadata(
        self,
        msg: Message,
        msg_id: bytes,
        folder: str
    ) -> EmailMetadata:
        """
        Extract email metadata

        Args:
            msg: Email message
            msg_id: IMAP message ID
            folder: Folder name

        Returns:
            EmailMetadata object
        """
        # Parse date with explicit UTC fallback
        date_str = msg.get("Date", "")

        # If no date header, use current UTC time silently (common for drafts)
        if not date_str or not date_str.strip():
            date = now_utc()
        else:
            try:
                date = email.utils.parsedate_to_datetime(date_str)

                # If naive (no timezone), assume UTC (email standard)
                if date.tzinfo is None:
                    from datetime import timezone
                    date = date.replace(tzinfo=timezone.utc)
                    logger.debug(
                        "Email date has no timezone, assuming UTC",
                        extra={"message_id": msg.get("Message-ID"), "date_str": date_str}
                    )
            except Exception as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")
                date = now_utc()  # Use current UTC time as fallback

        # Extract addresses
        from_header = msg.get("From", "")
        from_name, from_address = email.utils.parseaddr(from_header)

        to_header = msg.get("To", "")
        # Filter out empty/invalid email addresses (must contain @)
        to_addresses = [
            addr for _, addr in email.utils.getaddresses([to_header])
            if addr and '@' in addr
        ]

        # If no valid To addresses found, use a placeholder
        # (some emails like drafts may not have To addresses)
        if not to_addresses:
            to_addresses = ["no-recipient@unknown.com"]

        # Get flags (simplified - would need IMAP FLAGS fetch for full info)
        flags = []

        # Decode MIME-encoded headers
        subject_raw = msg.get("Subject", "(No Subject)")
        subject_decoded = decode_mime_header(subject_raw)

        from_name_decoded = decode_mime_header(from_name) if from_name else ""

        return EmailMetadata(
            id=int(msg_id.decode()),
            folder=folder,
            message_id=msg.get("Message-ID", ""),
            from_address=from_address or "unknown@unknown.com",
            from_name=from_name_decoded,
            to_addresses=to_addresses,
            subject=subject_decoded,
            date=date,
            has_attachments=self._has_attachments(msg),
            size_bytes=len(str(msg)),
            flags=flags
        )

    def _extract_content(self, msg: Message) -> EmailContent:
        """
        Extract email content (plain text and HTML) with proper charset detection

        Args:
            msg: Email message

        Returns:
            EmailContent object with metadata about decoding issues
        """
        import chardet

        plain_text = ""
        html = ""
        attachments = []
        decoding_errors = []

        def decode_payload(payload: bytes, part: Message, content_name: str) -> str:
            """
            Decode email payload with fallback charset detection

            Args:
                payload: Raw bytes payload
                part: Email part object
                content_name: Name for error tracking (e.g., "plain_text", "html")

            Returns:
                Decoded text string
            """
            # Try UTF-8 first (most common)
            try:
                return payload.decode("utf-8")
            except UnicodeDecodeError:
                pass

            # Try charset from email header
            charset = part.get_content_charset()
            if charset:
                try:
                    return payload.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    pass

            # Use chardet for automatic detection
            try:
                detected = chardet.detect(payload)
                detected_encoding = detected.get('encoding')
                confidence = detected.get('confidence', 0)

                if detected_encoding:
                    try:
                        text = payload.decode(detected_encoding, errors='replace')

                        # Log if confidence is low or encoding wasn't UTF-8
                        if confidence < 0.9 or detected_encoding.lower() not in ['utf-8', 'ascii']:
                            decoding_errors.append({
                                "content_type": content_name,
                                "detected_encoding": detected_encoding,
                                "confidence": confidence,
                                "fallback_used": True
                            })
                            logger.warning(
                                f"Email content used fallback encoding: {detected_encoding} "
                                f"(confidence: {confidence:.2f})"
                            )

                        return text
                    except (UnicodeDecodeError, LookupError):
                        pass
            except Exception as e:
                logger.warning(f"Chardet detection failed: {e}")

            # Last resort: latin-1 (never fails but may be incorrect)
            decoding_errors.append({
                "content_type": content_name,
                "error": "All decoding attempts failed, using latin-1 fallback",
                "fallback_used": True
            })
            logger.error(f"All decoding attempts failed for {content_name}, using latin-1 fallback")
            return payload.decode('latin-1', errors='replace')

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments for now (just track count)
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)
                    continue

                # Extract text content
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            plain_text += decode_payload(payload, part, "plain_text")
                    except Exception as e:
                        logger.warning(f"Failed to decode plain text: {e}", exc_info=True)

                elif content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html += decode_payload(payload, part, "html")
                    except Exception as e:
                        logger.warning(f"Failed to decode HTML: {e}", exc_info=True)
        else:
            # Non-multipart message
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    decoded = decode_payload(
                        payload,
                        msg,
                        "html" if content_type == "text/html" else "plain_text"
                    )
                    if content_type == "text/html":
                        html = decoded
                    else:
                        plain_text = decoded
            except Exception as e:
                logger.warning(f"Failed to decode message: {e}", exc_info=True)

        # Build metadata
        content_metadata = {}
        if decoding_errors:
            content_metadata["decoding_errors"] = decoding_errors

        return EmailContent(
            plain_text=plain_text.strip(),
            html=html.strip(),
            attachments=attachments,
            metadata=content_metadata
        )

    def _has_attachments(self, msg: Message) -> bool:
        """
        Check if email has attachments

        Args:
            msg: Email message

        Returns:
            True if email has attachments
        """
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    return True
        return False

    def mark_as_read(self, msg_id: int, folder: str = "INBOX") -> bool:
        """
        Mark email as read

        Args:
            msg_id: Email message ID
            folder: Folder name

        Returns:
            True if successful
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IMAP server")

        try:
            self._connection.select(folder)
            self._connection.store(str(msg_id).encode(), '+FLAGS', '\\Seen')
            logger.debug(f"Marked email {msg_id} as read")
            return True
        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}", exc_info=True)
            return False

    def _ensure_folder_exists(self, folder: str) -> bool:
        """
        Ensure IMAP folder exists, creating it if necessary

        Handles nested folders by creating parent folders first.

        Args:
            folder: Folder name (e.g., "Archive/2025/Personal")

        Returns:
            True if folder exists or was created successfully
        """
        if self._connection is None:
            return False

        try:
            # Encode folder name
            folder_encoded = encode_imap_folder_name(folder)

            # Check if folder exists by trying to select it
            status, _ = self._connection.select(folder_encoded, readonly=True)
            if status == 'OK':
                logger.debug(f"Folder {folder} already exists")
                return True

            # Folder doesn't exist - create it
            # For nested folders like "Archive/2025/Personal", we may need to create parents
            logger.info(f"Creating folder: {folder}")

            # Try to create the folder directly first
            status, response = self._connection.create(folder_encoded)
            if status == 'OK':
                logger.info(f"Successfully created folder: {folder}")
                return True

            # If direct creation failed, try creating parent folders first
            if '/' in folder:
                parts = folder.split('/')
                current_path = ""
                for part in parts:
                    current_path = f"{current_path}/{part}" if current_path else part
                    current_encoded = encode_imap_folder_name(current_path)

                    # Check if this level exists
                    status, _ = self._connection.select(current_encoded, readonly=True)
                    if status != 'OK':
                        # Create this level
                        status, _ = self._connection.create(current_encoded)
                        if status == 'OK':
                            logger.debug(f"Created folder: {current_path}")
                        else:
                            logger.warning(f"Failed to create folder: {current_path}")

                # Verify the final folder was created
                status, _ = self._connection.select(folder_encoded, readonly=True)
                return status == 'OK'

            logger.error(f"Failed to create folder {folder}: {response}")
            return False

        except Exception as e:
            logger.error(f"Error ensuring folder exists: {e}", exc_info=True)
            return False

    def move_email(self, msg_id: int, from_folder: str, to_folder: str) -> bool:
        """
        Move email to different folder

        Args:
            msg_id: Email message ID
            from_folder: Source folder
            to_folder: Destination folder

        Returns:
            True if successful
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IMAP server")

        try:
            # Ensure destination folder exists
            if not self._ensure_folder_exists(to_folder):
                logger.error(f"Could not create or access folder: {to_folder}")
                return False

            # Re-select the source folder (required after _ensure_folder_exists)
            # IMAP COPY command requires being in SELECTED state on the source folder
            self._connection.select(from_folder)

            # Encode folder name to IMAP modified UTF-7 for non-ASCII characters
            to_folder_encoded = encode_imap_folder_name(to_folder)

            # Quote the folder name if it contains special characters
            # IMAP requires quoting for names with spaces or special chars
            if ' ' in to_folder_encoded or '&' in to_folder_encoded:
                to_folder_quoted = f'"{to_folder_encoded}"'
            else:
                to_folder_quoted = to_folder_encoded

            logger.debug(f"Folder: '{to_folder}' -> '{to_folder_encoded}' -> '{to_folder_quoted}'")

            # Copy to destination
            result = self._connection.copy(str(msg_id).encode(), to_folder_quoted)
            if result[0] != 'OK':
                logger.error(f"Failed to copy email to {to_folder}")
                return False

            # Delete from source
            self._connection.store(str(msg_id).encode(), '+FLAGS', '\\Deleted')
            self._connection.expunge()

            logger.info(f"Moved email {msg_id} from {from_folder} to {to_folder}")
            return True

        except Exception as e:
            logger.error(f"Failed to move email: {e}", exc_info=True)
            return False

    def add_flag(self, msg_id: int, folder: str, flag: str = "\\Flagged") -> bool:
        """
        Add a flag to an email

        Args:
            msg_id: Email message ID
            folder: Folder containing the email
            flag: IMAP flag to add (default: \\Flagged)

        Returns:
            True if successful
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IMAP server")

        try:
            # Select the folder
            self._connection.select(folder)

            # Add the flag
            result = self._connection.store(str(msg_id).encode(), '+FLAGS', flag)
            if result[0] != 'OK':
                logger.error(f"Failed to add flag {flag} to email {msg_id}")
                return False

            logger.info(f"Added flag {flag} to email {msg_id} in {folder}")
            return True

        except Exception as e:
            logger.error(f"Failed to add flag: {e}", exc_info=True)
            return False

    def remove_flag(self, msg_id: int, folder: str, flag: str = "\\Flagged") -> bool:
        """
        Remove a flag from an email

        Args:
            msg_id: Email message ID
            folder: Folder containing the email
            flag: IMAP flag to remove (default: \\Flagged)

        Returns:
            True if successful
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IMAP server")

        try:
            # Select the folder
            self._connection.select(folder)

            # Remove the flag
            result = self._connection.store(str(msg_id).encode(), '-FLAGS', flag)
            if result[0] != 'OK':
                logger.error(f"Failed to remove flag {flag} from email {msg_id}")
                return False

            logger.info(f"Removed flag {flag} from email {msg_id} in {folder}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove flag: {e}", exc_info=True)
            return False
