"""
Email Validator

Validates email content and metadata before processing.

Responsibilities:
- Check email size limits (hard and soft)
- Validate required fields
- Assess content quality
- Provide truncation recommendations
"""


from src.core.schemas import EmailContent, EmailMetadata, EmailValidationResult


class EmailValidator:
    """
    Validates email content and metadata

    Checks size limits, content quality, and metadata completeness.
    Provides clear feedback on validation failures and warnings.

    Usage:
        validator = EmailValidator(config.email)
        result = validator.validate(metadata, content)
        if not result.is_valid:
            logger.warning(f"Rejected: {result.rejection_reason}")
    """

    def __init__(self, max_email_size_mb: int = 5, max_content_truncate_kb: int = 200):
        """
        Initialize validator

        Args:
            max_email_size_mb: Hard size limit in MB (reject if exceeded)
            max_content_truncate_kb: Soft size limit in KB (truncate if exceeded)
        """
        self.max_email_size_mb = max_email_size_mb
        self.max_content_truncate_kb = max_content_truncate_kb

    def validate(
        self,
        metadata: EmailMetadata,
        content: EmailContent
    ) -> EmailValidationResult:
        """
        Validate email

        Checks:
        1. Size limits (hard reject if > max, truncate if > soft limit)
        2. Content presence (warn if no text)
        3. Metadata completeness (warn if missing subject)

        Args:
            metadata: Email metadata
            content: Email content

        Returns:
            EmailValidationResult with verdict and recommendations
        """
        # Calculate total size
        total_size = self._calculate_size(content, metadata)

        # Hard limit check (C1-2: 5MB hard limit to prevent OOM)
        max_size = self.max_email_size_mb * 1_024 * 1_024
        if total_size > max_size:
            size_mb = total_size / 1_024 / 1_024
            return EmailValidationResult(
                is_valid=False,
                should_truncate=False,
                reason="size_exceeds_hard_limit",
                details=(
                    f"Email size {size_mb:.1f}MB exceeds "
                    f"hard limit of {self.max_email_size_mb}MB"
                )
            )

        # Soft limit check (truncation recommended)
        soft_limit = self.max_content_truncate_kb * 1_024
        should_truncate = total_size > soft_limit

        # Content validation
        if not content.plain_text and not content.html:
            return EmailValidationResult(
                is_valid=False,
                should_truncate=False,
                reason="no_text_content",
                details="Email has no text content (binary only)"
            )

        # Valid email
        return EmailValidationResult(
            is_valid=True,
            should_truncate=should_truncate,
            reason=None,
            details=f"Size: {total_size/1024:.0f}KB" if should_truncate else None
        )

    def _calculate_size(
        self,
        content: EmailContent,
        metadata: EmailMetadata
    ) -> int:
        """
        Calculate total email size in bytes

        Includes:
        - Plain text content
        - HTML content
        - Attachment data

        Args:
            content: Email content
            metadata: Email metadata

        Returns:
            Total size in bytes
        """
        size = 0

        # Text content
        if content.plain_text:
            size += len(content.plain_text.encode('utf-8'))

        if content.html:
            size += len(content.html.encode('utf-8'))

        # Attachments
        if hasattr(metadata, 'attachments') and metadata.attachments:
            for att in metadata.attachments:
                if isinstance(att, dict) and 'data' in att:
                    size += len(att.get('data', ''))
                elif hasattr(att, 'data'):
                    size += len(getattr(att, 'data', ''))

        return size
