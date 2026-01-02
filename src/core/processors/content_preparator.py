"""
Content Preparator

Prepares email content for AI analysis by truncating, cleaning, and formatting.

Responsibilities:
- Truncate oversized content intelligently
- Clean HTML (remove scripts, styles)
- Preserve important content (beginning > end)
- Add truncation markers for transparency
"""

import re
from typing import Optional

from src.core.schemas import EmailContent


class ContentPreparator:
    """
    Prepares email content for AI analysis

    Handles content truncation and HTML cleaning to ensure content
    is within size limits and safe for AI processing.

    Usage:
        preparator = ContentPreparator(max_truncate_kb=200)
        prepared = preparator.prepare(content, truncate=True)
    """

    def __init__(self, max_content_truncate_kb: int = 200):
        """
        Initialize preparator

        Args:
            max_content_truncate_kb: Soft size limit for truncation in KB
        """
        self.max_content_truncate_kb = max_content_truncate_kb

    def prepare(
        self,
        content: EmailContent,
        truncate: bool = False
    ) -> EmailContent:
        """
        Prepare content for AI analysis

        Process:
        1. Truncate if requested and over limit
        2. Clean HTML (remove scripts/styles)
        3. Return prepared content

        Args:
            content: Original email content
            truncate: Whether to truncate oversized content

        Returns:
            Prepared EmailContent (may be truncated)
        """
        # Start with original content
        plain_text = content.plain_text
        html = content.html

        # Clean HTML first (even if not truncating)
        if html:
            html = self._clean_html(html)

        # Truncate if requested
        if truncate:
            max_bytes = self.max_content_truncate_kb * 1_024
            plain_text, html = self._truncate_content(
                plain_text, html, max_bytes
            )

        # Return prepared content
        return EmailContent(
            plain_text=plain_text,
            html=html,
            preview=content.preview  # Preserve preview
        )

    def _truncate_content(
        self,
        plain_text: Optional[str],
        html: Optional[str],
        max_bytes: int
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Truncate content intelligently

        Strategy:
        - Prioritize plain text over HTML
        - Truncate from end (preserve beginning)
        - Add clear truncation marker
        - Drop HTML if plain text is truncated

        Args:
            plain_text: Plain text content
            html: HTML content
            max_bytes: Maximum size in bytes

        Returns:
            Tuple of (truncated_plain, truncated_html)
        """
        # Handle None plain_text
        if plain_text is None:
            return None, html

        plain = plain_text

        # Calculate size of plain text
        plain_size = len(plain.encode('utf-8'))

        # If plain text exceeds limit, truncate it
        if plain_size > max_bytes:
            # Reserve 50 bytes for truncation marker
            truncate_at = max_bytes - 50

            # Truncate plain text
            truncated = plain.encode('utf-8')[:truncate_at].decode('utf-8', errors='ignore')

            # Add marker
            truncated += "\n\n[... Content truncated for size ...]"

            # Drop HTML when plain text is truncated
            return truncated, None

        # Plain text fits, check if we have room for HTML
        if html:
            html_size = len(html.encode('utf-8'))
            total_size = plain_size + html_size

            if total_size > max_bytes:
                # Drop HTML, keep plain text
                return plain, None

        # Both fit
        return plain, html

    def _clean_html(self, html: str) -> str:
        """
        Clean HTML content

        Removes:
        - <script> tags and content
        - <style> tags and content
        - Potentially dangerous elements

        Args:
            html: Original HTML content

        Returns:
            Cleaned HTML (safe for AI analysis)
        """
        # Remove <script> tags and content
        html = re.sub(
            r'<script[^>]*>.*?</script>',
            '',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Remove <style> tags and content
        html = re.sub(
            r'<style[^>]*>.*?</style>',
            '',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        return html.strip()
