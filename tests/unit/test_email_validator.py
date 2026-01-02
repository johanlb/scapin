"""
Tests for EmailValidator

Covers validation logic for email size limits, content, and metadata.
"""

import pytest

from src.core.processors.email_validator import EmailValidator
from src.core.schemas import EmailContent, EmailMetadata
from src.utils import now_utc


@pytest.fixture
def validator():
    """Create EmailValidator instance with test limits"""
    return EmailValidator(
        max_email_size_mb=5,  # 5MB hard limit
        max_content_truncate_kb=100  # 100KB soft limit
    )


class TestValidation:
    """Test email validation"""

    def test_valid_small_email(self, validator):
        """Test validation of small valid email"""
        metadata = EmailMetadata(
            id=1,
            message_id="test@example.com",
            subject="Test Email",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            date=now_utc(),
            has_attachments=False,
            flags=[]
        )

        content = EmailContent(
            plain_text="This is a test email",
            html="<p>This is a test email</p>"
        )

        result = validator.validate(metadata, content)

        assert result.is_valid
        assert not result.should_truncate
        assert result.reason is None

    def test_email_exceeds_hard_limit(self, validator):
        """Test email exceeding hard size limit (5MB)"""
        metadata = EmailMetadata(
            id=1,
            message_id="test@example.com",
            subject="Large Email",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            date=now_utc(),
            has_attachments=False,
            flags=[]
        )

        # Create 6MB of content (exceeds 5MB limit)
        large_text = "A" * (6 * 1024 * 1024)
        content = EmailContent(plain_text=large_text, html=None)

        result = validator.validate(metadata, content)

        assert not result.is_valid
        assert not result.should_truncate
        assert result.reason == "size_exceeds_hard_limit"
        assert "6.0MB exceeds" in result.details
        assert "5MB" in result.details

    def test_email_exceeds_soft_limit(self, validator):
        """Test email exceeding soft limit (should truncate)"""
        metadata = EmailMetadata(
            id=1,
            message_id="test@example.com",
            subject="Medium Email",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            date=now_utc(),
            has_attachments=False,
            flags=[]
        )

        # Create 150KB content (exceeds 100KB soft limit but < 5MB hard limit)
        medium_text = "A" * (150 * 1024)
        content = EmailContent(plain_text=medium_text, html=None)

        result = validator.validate(metadata, content)

        assert result.is_valid
        assert result.should_truncate
        assert result.reason is None
        assert result.details is not None
        assert "150KB" in result.details or "Size:" in result.details

    def test_email_no_text_content(self, validator):
        """Test email with no text content"""
        metadata = EmailMetadata(
            id=1,
            message_id="test@example.com",
            subject="No Content",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            date=now_utc(),
            has_attachments=False,
            flags=[]
        )

        content = EmailContent(plain_text=None, html=None)

        result = validator.validate(metadata, content)

        assert not result.is_valid  # Invalid - no text content
        assert not result.should_truncate
        assert result.reason == "no_text_content"


class TestSizeCalculation:
    """Test size calculation"""

    def test_calculate_size_plain_text_only(self, validator):
        """Test size calculation with plain text only"""
        metadata = EmailMetadata(
            id=1,
            message_id="test@example.com",
            subject="Test",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            date=now_utc(),
            has_attachments=False,
            flags=[]
        )

        text = "Hello" * 100  # 500 bytes
        content = EmailContent(plain_text=text, html=None)

        size = validator._calculate_size(content, metadata)

        assert size == len(text.encode('utf-8'))

    def test_calculate_size_with_html(self, validator):
        """Test size calculation with both plain text and HTML"""
        metadata = EmailMetadata(
            id=1,
            message_id="test@example.com",
            subject="Test",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["recipient@example.com"],
            date=now_utc(),
            has_attachments=False,
            flags=[]
        )

        plain = "Hello"
        html = "<p>Hello</p>"
        content = EmailContent(plain_text=plain, html=html)

        size = validator._calculate_size(content, metadata)

        expected = len(plain.encode('utf-8')) + len(html.encode('utf-8'))
        assert size == expected
