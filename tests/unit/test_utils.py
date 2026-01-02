"""
Unit Tests for Utility Functions

Tests for file, string, and date utilities.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.utils.date_utils import (
    end_of_day,
    format_datetime,
    is_business_hours,
    is_same_day,
    next_business_day,
    now_utc,
    parse_date,
    start_of_day,
    time_ago,
)
from src.utils.file_utils import (
    atomic_write,
    ensure_dir,
    get_file_hash,
    get_file_size,
    list_files,
    safe_read_file,
    safe_write_file,
)
from src.utils.string_utils import (
    camel_to_snake,
    extract_email,
    extract_urls,
    normalize_whitespace,
    sanitize_filename,
    slugify,
    snake_to_camel,
    strip_html,
    truncate,
    word_count,
)

# ============================================================================
# File Utils Tests
# ============================================================================

class TestFileUtils:
    """Test file utility functions"""

    def test_ensure_dir_creates_directory(self, tmp_path: Path):
        """Test ensure_dir creates directory"""
        new_dir = tmp_path / "test" / "nested" / "dir"
        result = ensure_dir(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_ensure_dir_existing_directory(self, tmp_path: Path):
        """Test ensure_dir with existing directory"""
        result = ensure_dir(tmp_path)
        assert result.exists()
        assert result == tmp_path

    def test_safe_read_file_success(self, tmp_path: Path):
        """Test safe_read_file reads file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        content = safe_read_file(test_file)
        assert content == "Hello World"

    def test_safe_read_file_nonexistent(self, tmp_path: Path):
        """Test safe_read_file with nonexistent file"""
        content = safe_read_file(tmp_path / "nonexistent.txt")
        assert content is None

    def test_safe_write_file_success(self, tmp_path: Path):
        """Test safe_write_file writes file"""
        test_file = tmp_path / "test.txt"
        result = safe_write_file(test_file, "Test content")
        assert result is True
        assert test_file.read_text() == "Test content"

    def test_safe_write_file_creates_parents(self, tmp_path: Path):
        """Test safe_write_file creates parent directories"""
        test_file = tmp_path / "nested" / "dir" / "test.txt"
        result = safe_write_file(test_file, "Test content")
        assert result is True
        assert test_file.exists()

    def test_atomic_write_success(self, tmp_path: Path):
        """Test atomic_write writes file"""
        test_file = tmp_path / "test.txt"
        result = atomic_write(test_file, "Atomic content")
        assert result is True
        assert test_file.read_text() == "Atomic content"

    def test_list_files_basic(self, tmp_path: Path):
        """Test list_files lists files"""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        (tmp_path / "file3.md").touch()

        txt_files = list_files(tmp_path, "*.txt")
        assert len(txt_files) == 2

    def test_list_files_recursive(self, tmp_path: Path):
        """Test list_files with recursive search"""
        (tmp_path / "file1.txt").touch()
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "file2.txt").touch()

        all_files = list_files(tmp_path, "*.txt", recursive=True)
        assert len(all_files) == 2

    def test_get_file_hash_sha256(self, tmp_path: Path):
        """Test get_file_hash calculates hash"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        hash_value = get_file_hash(test_file)
        assert hash_value is not None
        assert len(hash_value) == 64  # SHA256 hex digest length

    def test_get_file_hash_nonexistent(self, tmp_path: Path):
        """Test get_file_hash with nonexistent file"""
        hash_value = get_file_hash(tmp_path / "nonexistent.txt")
        assert hash_value is None

    def test_get_file_size_success(self, tmp_path: Path):
        """Test get_file_size returns correct size"""
        test_file = tmp_path / "test.txt"
        content = "Hello World"
        test_file.write_text(content)

        size = get_file_size(test_file)
        assert size == len(content.encode())


# ============================================================================
# String Utils Tests
# ============================================================================

class TestStringUtils:
    """Test string utility functions"""

    def test_truncate_short_text(self):
        """Test truncate with text shorter than limit"""
        result = truncate("Short text", 100)
        assert result == "Short text"

    def test_truncate_long_text(self):
        """Test truncate with text longer than limit"""
        long_text = "This is a very long text that should be truncated"
        result = truncate(long_text, 20)
        assert len(result) <= 23  # 20 + "..."
        assert result.endswith("...")

    def test_sanitize_filename_invalid_chars(self):
        """Test sanitize_filename removes invalid characters"""
        result = sanitize_filename("file<>:\"/\\|?*.txt")
        assert "<" not in result
        assert ">" not in result
        assert result.endswith(".txt")

    def test_sanitize_filename_long_name(self):
        """Test sanitize_filename truncates long names"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_extract_email_valid(self):
        """Test extract_email finds email"""
        text = "Contact me at john@example.com for details"
        email = extract_email(text)
        assert email == "john@example.com"

    def test_extract_email_no_email(self):
        """Test extract_email with no email"""
        text = "No email here"
        email = extract_email(text)
        assert email is None

    def test_extract_urls_multiple(self):
        """Test extract_urls finds multiple URLs"""
        text = "Visit https://example.com and http://test.org"
        urls = extract_urls(text)
        assert len(urls) == 2
        assert "https://example.com" in urls

    def test_slugify_basic(self):
        """Test slugify creates URL-friendly slug"""
        result = slugify("Hello World!")
        assert result == "hello-world"

    def test_slugify_unicode(self):
        """Test slugify handles unicode"""
        result = slugify("Café Münchën")
        assert "cafe" in result.lower()

    def test_normalize_whitespace_multiple_spaces(self):
        """Test normalize_whitespace removes extra spaces"""
        text = "Hello    World  \n\t  Test"
        result = normalize_whitespace(text)
        assert result == "Hello World Test"

    def test_strip_html_basic(self):
        """Test strip_html removes HTML tags"""
        html = "<p>Hello <b>World</b></p>"
        result = strip_html(html)
        assert result == "Hello World"

    def test_strip_html_entities(self):
        """Test strip_html decodes HTML entities"""
        html = "Hello&nbsp;&lt;World&gt;"
        result = strip_html(html)
        assert result == "Hello <World>"

    def test_camel_to_snake_basic(self):
        """Test camel_to_snake conversion"""
        assert camel_to_snake("camelCase") == "camel_case"
        assert camel_to_snake("PascalCase") == "pascal_case"

    def test_snake_to_camel_basic(self):
        """Test snake_to_camel conversion"""
        assert snake_to_camel("snake_case") == "snakeCase"
        assert snake_to_camel("snake_case", capitalize_first=True) == "SnakeCase"

    def test_word_count_basic(self):
        """Test word_count counts words"""
        assert word_count("Hello world") == 2
        assert word_count("One two three four") == 4


# ============================================================================
# Date Utils Tests
# ============================================================================

class TestDateUtils:
    """Test date utility functions"""

    def test_now_utc_has_timezone(self):
        """Test now_utc returns timezone-aware datetime"""
        dt = now_utc()
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc

    def test_parse_date_iso_format(self):
        """Test parse_date with ISO format"""
        dt = parse_date("2025-01-15T10:30:00Z")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_date_date_only(self):
        """Test parse_date with date only"""
        dt = parse_date("2025-01-15")
        assert dt is not None
        assert dt.year == 2025

    def test_parse_date_invalid(self):
        """Test parse_date with invalid date"""
        dt = parse_date("not a date")
        assert dt is None

    def test_format_datetime_iso(self):
        """Test format_datetime with ISO format"""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_datetime(dt, "iso")
        assert "2025-01-15" in result

    def test_format_datetime_friendly(self):
        """Test format_datetime with friendly format"""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_datetime(dt, "friendly")
        assert "January" in result
        assert "2025" in result

    def test_time_ago_just_now(self):
        """Test time_ago for recent time"""
        dt = now_utc() - timedelta(seconds=30)
        result = time_ago(dt)
        assert result == "just now"

    def test_time_ago_minutes(self):
        """Test time_ago for minutes"""
        dt = now_utc() - timedelta(minutes=5)
        result = time_ago(dt)
        assert "minute" in result

    def test_time_ago_hours(self):
        """Test time_ago for hours"""
        dt = now_utc() - timedelta(hours=2)
        result = time_ago(dt)
        assert "hour" in result

    def test_time_ago_days(self):
        """Test time_ago for days"""
        dt = now_utc() - timedelta(days=3)
        result = time_ago(dt)
        assert "day" in result

    def test_is_business_hours_weekday(self):
        """Test is_business_hours on weekday"""
        # Monday at 10 AM
        dt = datetime(2025, 1, 13, 10, 0, 0, tzinfo=timezone.utc)
        assert is_business_hours(dt, start_hour=9, end_hour=17) is True

    def test_is_business_hours_weekend(self):
        """Test is_business_hours on weekend"""
        # Saturday at 10 AM
        dt = datetime(2025, 1, 11, 10, 0, 0, tzinfo=timezone.utc)
        assert is_business_hours(dt, weekdays_only=True) is False

    def test_next_business_day_friday(self):
        """Test next_business_day from Friday skips weekend"""
        friday = datetime(2025, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        next_day = next_business_day(friday)
        # Should be Monday
        assert next_day.weekday() == 0  # Monday

    def test_is_same_day_true(self):
        """Test is_same_day returns True for same day"""
        dt1 = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        assert is_same_day(dt1, dt2) is True

    def test_is_same_day_false(self):
        """Test is_same_day returns False for different days"""
        dt1 = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 16, 10, 0, 0, tzinfo=timezone.utc)
        assert is_same_day(dt1, dt2) is False

    def test_start_of_day(self):
        """Test start_of_day returns midnight"""
        dt = datetime(2025, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_end_of_day(self):
        """Test end_of_day returns last moment"""
        dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
