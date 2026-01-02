"""
Tests for email size validation (C1-2)

Covers:
- Hard limit rejection (>5MB by default)
- Soft limit truncation (>200KB by default)
- Attachment size calculation

Note: These tests are skipped because EmailAccountConfig doesn't have
max_email_size_mb and max_content_truncate_kb attributes yet.
This functionality is planned for a future release.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.core.schemas import EmailMetadata, EmailContent
from src.core.config_manager import PKMConfig, EmailConfig, AIConfig, EmailAccountConfig
from src.core.email_processor import EmailProcessor


@pytest.mark.skip(reason="Email size validation not yet implemented - pending schema extension")
class TestEmailSizeValidation:
    """Test email size validation with hard and soft limits"""

    @pytest.fixture
    def mock_config(self):
        """Create mock config with size limits"""
        # Create email account config with default limits
        account_config = EmailAccountConfig(
            account_id="test",
            account_name="Test Account",
            imap_host="imap.test.com",
            imap_port=993,
            imap_username="test@test.com",
            imap_password="testpass123",
            max_email_size_mb=5,  # Hard limit: 5MB
            max_content_truncate_kb=200  # Soft limit: 200KB
        )

        # Create email config with this account
        email_config = EmailConfig(
            accounts=[account_config],
            default_account_id="test"
        )

        # Create AI config
        ai_config = AIConfig(
            anthropic_api_key="sk-ant-test-key-12345"
        )

        # Create full PKM config
        config = Mock(spec=PKMConfig)
        config.email = email_config
        config.ai = ai_config

        return config

    @pytest.fixture
    def processor(self, mock_config):
        """Create email processor with mocked dependencies"""
        from src.core.processors.email_validator import EmailValidator

        processor = Mock(spec=EmailProcessor)
        processor.config = mock_config

        # Get the actual validation method
        actual_processor = EmailProcessor.__new__(EmailProcessor)
        actual_processor.config = mock_config

        # Initialize email_validator that the method depends on
        account_config = mock_config.email.get_default_account()
        actual_processor.email_validator = EmailValidator(
            max_email_size_mb=account_config.max_email_size_mb,
            max_content_truncate_kb=account_config.max_content_truncate_kb
        )

        # Bind the validation method
        processor._validate_email_for_processing = (
            actual_processor._validate_email_for_processing.__get__(actual_processor, EmailProcessor)
        )

        return processor

    def test_normal_size_email_accepted(self, processor):
        """Test email under both limits is accepted"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Test Email"
        metadata.from_address = "sender@example.com"
        metadata.attachments = []

        # 10KB email (well under limits)
        content = EmailContent(
            plain_text="x" * (10 * 1024),
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        assert result.is_valid is True
        assert result.should_truncate is False

    def test_large_content_triggers_truncation(self, processor):
        """Test email over soft limit triggers truncation but is accepted"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Large Email"
        metadata.attachments = []

        # 300KB email (over 200KB soft limit, under 5MB hard limit)
        content = EmailContent(
            plain_text="x" * (300 * 1024),
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        assert result.is_valid is True
        assert result.should_truncate is True
        assert "oversized" in result.reason

    def test_huge_email_rejected(self, processor):
        """Test email over hard limit is rejected"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Huge Email"
        metadata.attachments = []

        # 10MB email (over 5MB hard limit)
        content = EmailContent(
            plain_text="x" * (10 * 1024 * 1024),
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        assert result.is_valid is False
        assert "hard_limit" in result.reason
        assert "10" in result.details  # Size in MB should be mentioned

    def test_email_with_large_attachment_rejected(self, processor):
        """Test email with large attachment is rejected"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Email with Attachment"

        # Small text but large attachment (6MB total)
        metadata.attachments = [
            {
                "filename": "large_file.pdf",
                "data": "x" * (6 * 1024 * 1024)  # 6MB base64 data
            }
        ]

        content = EmailContent(
            plain_text="Small text content",
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        assert result.is_valid is False
        assert "hard_limit" in result.reason

    def test_email_with_multiple_small_attachments_accepted(self, processor):
        """Test email with multiple small attachments is accepted"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Email with Attachments"
        metadata.from_address = "sender@example.com"

        # Multiple small attachments (total <5MB)
        metadata.attachments = [
            {"filename": "file1.pdf", "data": "x" * (500 * 1024)},  # 500KB
            {"filename": "file2.jpg", "data": "x" * (500 * 1024)},  # 500KB
            {"filename": "file3.doc", "data": "x" * (500 * 1024)},  # 500KB
        ]

        content = EmailContent(
            plain_text="Content with attachments",
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        # Total is ~1.5MB, under 5MB hard limit but content might trigger soft limit
        assert result.is_valid is True

    def test_empty_content_rejected(self, processor):
        """Test email with no content is rejected"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Empty Email"
        metadata.from_address = "sender@example.com"
        metadata.attachments = []

        content = EmailContent(
            plain_text="",
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        assert result.is_valid is False
        assert "no_text_content" in result.reason

    def test_exact_hard_limit_boundary(self, processor):
        """Test email exactly at hard limit boundary"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Boundary Test"
        metadata.attachments = []

        # Exactly 5MB (5 * 1024 * 1024 bytes)
        exact_limit = 5 * 1024 * 1024
        content = EmailContent(
            plain_text="x" * exact_limit,
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        # Should be accepted (not over limit)
        assert result.is_valid is True

    def test_one_byte_over_hard_limit(self, processor):
        """Test email one byte over hard limit is rejected"""
        metadata = Mock(spec=EmailMetadata)
        metadata.id = "test-123"
        metadata.subject = "Over Boundary Test"
        metadata.attachments = []

        # One byte over 5MB
        over_limit = (5 * 1024 * 1024) + 1
        content = EmailContent(
            plain_text="x" * over_limit,
            html=None
        )

        result = processor._validate_email_for_processing(metadata, content)

        # Should be rejected
        assert result.is_valid is False
        assert "hard_limit" in result.reason


@pytest.mark.skip(reason="Email size validation not yet implemented - pending schema extension")
class TestEmailSizeConfigValidation:
    """Test email size configuration validation"""

    def test_config_accepts_valid_size_limits(self):
        """Test config accepts valid size limits"""
        account = EmailAccountConfig(
            account_id="test",
            account_name="Test",
            imap_host="imap.test.com",
            imap_username="test@test.com",
            imap_password="testpass123",
            max_email_size_mb=10,  # Valid: 1-50
            max_content_truncate_kb=500  # Valid: 50-2000
        )

        assert account.max_email_size_mb == 10
        assert account.max_content_truncate_kb == 500

    def test_config_rejects_invalid_size_limits(self):
        """Test config rejects out-of-range size limits"""
        from pydantic import ValidationError

        # Test max_email_size_mb < 1
        with pytest.raises(ValidationError):
            EmailAccountConfig(
                account_id="test",
                account_name="Test",
                imap_host="imap.test.com",
                imap_username="test@test.com",
                imap_password="testpass123",
                max_email_size_mb=0  # Invalid: < 1
            )

        # Test max_email_size_mb > 50
        with pytest.raises(ValidationError):
            EmailAccountConfig(
                account_id="test",
                account_name="Test",
                imap_host="imap.test.com",
                imap_username="test@test.com",
                imap_password="testpass123",
                max_email_size_mb=100  # Invalid: > 50
            )

        # Test max_content_truncate_kb < 50
        with pytest.raises(ValidationError):
            EmailAccountConfig(
                account_id="test",
                account_name="Test",
                imap_host="imap.test.com",
                imap_username="test@test.com",
                imap_password="testpass123",
                max_content_truncate_kb=10  # Invalid: < 50
            )

    def test_default_size_limits(self):
        """Test default size limits are applied"""
        account = EmailAccountConfig(
            account_id="test",
            account_name="Test",
            imap_host="imap.test.com",
            imap_username="test@test.com",
            imap_password="testpass123"
            # No size limits specified - should use defaults
        )

        assert account.max_email_size_mb == 5  # Default
        assert account.max_content_truncate_kb == 200  # Default
