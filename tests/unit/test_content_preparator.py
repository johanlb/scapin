"""
Tests for ContentPreparator

Covers content truncation, HTML cleaning, and preparation logic.
"""

import pytest

from src.core.processors.content_preparator import ContentPreparator
from src.core.schemas import EmailContent


@pytest.fixture
def preparator():
    """Create ContentPreparator instance with 100KB limit"""
    return ContentPreparator(max_content_truncate_kb=100)


class TestContentPreparation:
    """Test content preparation"""

    def test_prepare_small_content_no_truncate(self, preparator):
        """Test preparing small content without truncation"""
        content = EmailContent(
            plain_text="Hello, this is a test email.",
            html="<p>Hello, this is a test email.</p>"
        )

        prepared = preparator.prepare(content, truncate=False)

        assert prepared.plain_text == content.plain_text
        assert prepared.html is not None
        # HTML should be cleaned (no change for simple HTML)
        assert "<p>Hello" in prepared.html

    def test_prepare_cleans_html(self, preparator):
        """Test HTML cleaning removes scripts and styles"""
        content = EmailContent(
            plain_text="Test",
            html="""
                <html>
                <head>
                    <script>alert('xss')</script>
                    <style>.danger { color: red; }</style>
                </head>
                <body>
                    <!-- Comment -->
                    <p>Safe content</p>
                </body>
                </html>
            """
        )

        prepared = preparator.prepare(content, truncate=False)

        # Script, style, and comments should be removed
        assert "<script>" not in prepared.html
        assert "alert" not in prepared.html
        assert "<style>" not in prepared.html
        assert ".danger" not in prepared.html
        assert "<!--" not in prepared.html
        # Safe content should remain
        assert "Safe content" in prepared.html

    def test_truncate_oversized_plain_text(self, preparator):
        """Test truncation of oversized plain text"""
        # Create 150KB of text (exceeds 100KB limit)
        large_text = "A" * (150 * 1024)
        content = EmailContent(plain_text=large_text, html=None)

        prepared = preparator.prepare(content, truncate=True)

        # Should be truncated
        assert len(prepared.plain_text.encode('utf-8')) < 100 * 1024 + 100  # +100 for marker
        assert "[... Content truncated for size ...]" in prepared.plain_text
        # HTML should be dropped when plain text is truncated
        assert prepared.html is None

    def test_truncate_drops_html_if_total_exceeds_limit(self, preparator):
        """Test HTML is dropped if total size exceeds limit"""
        # Plain text: 80KB, HTML: 40KB = 120KB total (exceeds 100KB)
        plain_text = "A" * (80 * 1024)
        html_text = "<p>" + ("B" * (40 * 1024)) + "</p>"
        content = EmailContent(plain_text=plain_text, html=html_text)

        prepared = preparator.prepare(content, truncate=True)

        # Plain text fits, so it should be preserved
        assert prepared.plain_text == plain_text
        # HTML should be dropped to stay under limit
        assert prepared.html is None

    def test_both_fit_under_limit(self, preparator):
        """Test both plain text and HTML preserved when under limit"""
        plain_text = "A" * (40 * 1024)  # 40KB
        html_text = "<p>" + ("B" * (40 * 1024)) + "</p>"  # ~40KB
        content = EmailContent(plain_text=plain_text, html=html_text)

        prepared = preparator.prepare(content, truncate=True)

        # Both should be preserved
        assert prepared.plain_text == plain_text
        assert prepared.html is not None
        assert "B" in prepared.html

    def test_preserve_preview(self, preparator):
        """Test that preview is preserved during preparation"""
        content = EmailContent(
            plain_text="Full content here",
            html="<p>Full content here</p>",
            preview="Preview text"
        )

        prepared = preparator.prepare(content, truncate=False)

        assert prepared.preview == "Preview text"

    def test_no_truncate_when_disabled(self, preparator):
        """Test that truncate=False never truncates"""
        # Create oversized content
        large_text = "A" * (200 * 1024)
        content = EmailContent(plain_text=large_text, html=None)

        prepared = preparator.prepare(content, truncate=False)

        # Should NOT be truncated
        assert len(prepared.plain_text) == len(large_text)
        assert "[... Content truncated" not in prepared.plain_text


class TestHTMLCleaning:
    """Test HTML cleaning edge cases"""

    def test_clean_html_multiple_scripts(self, preparator):
        """Test removing multiple script tags"""
        html = """
            <script>bad1()</script>
            <p>Content</p>
            <script>bad2()</script>
        """

        cleaned = preparator._clean_html(html)

        assert "<script>" not in cleaned
        assert "bad1" not in cleaned
        assert "bad2" not in cleaned
        assert "Content" in cleaned

    def test_clean_html_inline_styles(self, preparator):
        """Test removing style tags"""
        html = """
            <style type="text/css">
                body { background: red; }
            </style>
            <p>Content</p>
        """

        cleaned = preparator._clean_html(html)

        assert "<style" not in cleaned
        assert "background" not in cleaned
        assert "Content" in cleaned

    def test_clean_html_nested_comments(self, preparator):
        """Test removing HTML comments"""
        html = """
            <!-- Comment 1 -->
            <p>Content</p>
            <!-- Comment 2 with <tags> inside -->
        """

        cleaned = preparator._clean_html(html)

        assert "<!--" not in cleaned
        assert "Comment 1" not in cleaned
        assert "Comment 2" not in cleaned
        assert "Content" in cleaned

    def test_clean_html_case_insensitive(self, preparator):
        """Test cleaning is case-insensitive"""
        html = """
            <SCRIPT>bad()</SCRIPT>
            <Style>bad</Style>
            <p>Content</p>
        """

        cleaned = preparator._clean_html(html)

        assert "SCRIPT" not in cleaned
        assert "Style" not in cleaned
        assert "bad" not in cleaned
        assert "Content" in cleaned


class TestTruncationEdgeCases:
    """Test truncation edge cases"""

    def test_truncate_unicode_safely(self, preparator):
        """Test truncation doesn't break unicode characters"""
        # Create text with unicode at the boundary
        text = "A" * (100 * 1024 - 10) + "日本語テスト"
        content = EmailContent(plain_text=text, html=None)

        prepared = preparator.prepare(content, truncate=True)

        # Should truncate without raising UnicodeDecodeError
        # (uses errors='ignore' when decoding)
        assert isinstance(prepared.plain_text, str)
        assert "[... Content truncated" in prepared.plain_text

    def test_truncate_empty_content(self, preparator):
        """Test truncating empty content"""
        content = EmailContent(plain_text="", html=None)

        prepared = preparator.prepare(content, truncate=True)

        assert prepared.plain_text == ""
        assert prepared.html is None

    def test_truncate_none_content(self, preparator):
        """Test truncating None content"""
        content = EmailContent(plain_text=None, html=None)

        prepared = preparator.prepare(content, truncate=True)

        assert prepared.plain_text is None
        assert prepared.html is None
