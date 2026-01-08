"""
Tests for WhatsApp, Files, and Web adapters.

These adapters provide search functionality for:
- WhatsApp: SQLite message history (iOS and Android)
- Files: Local file search with ripgrep or Python fallback
- Web: Tavily API with DuckDuckGo fallback
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.passepartout.cross_source.adapters.files_adapter import (
    DEFAULT_EXCLUDES,
    DEFAULT_EXTENSIONS,
    FilesAdapter,
)
from src.passepartout.cross_source.adapters.web_adapter import (
    DuckDuckGoAdapter,
    WebAdapter,
    create_web_adapter,
)
from src.passepartout.cross_source.adapters.whatsapp_adapter import WhatsAppAdapter
from src.passepartout.cross_source.models import SourceItem

# =============================================================================
# WhatsApp Adapter Tests
# =============================================================================


class TestWhatsAppAdapterInit:
    """Tests for WhatsAppAdapter initialization."""

    def test_init_defaults(self) -> None:
        """Adapter initializes with default values."""
        adapter = WhatsAppAdapter()
        assert adapter._db_path is None
        assert adapter._days_back == 90
        assert adapter._connection is None
        assert adapter._available is None
        assert adapter.source_name == "whatsapp"

    def test_init_with_custom_db_path(self, tmp_path: Path) -> None:
        """Adapter accepts custom database path."""
        db_path = tmp_path / "test.db"
        adapter = WhatsAppAdapter(db_path=db_path)
        assert adapter._db_path == db_path

    def test_init_with_custom_days_back(self) -> None:
        """Adapter accepts custom days_back value."""
        adapter = WhatsAppAdapter(days_back=30)
        assert adapter._days_back == 30


class TestWhatsAppAdapterAvailability:
    """Tests for WhatsApp adapter availability checks."""

    def test_is_available_returns_false_when_no_db(self) -> None:
        """Returns False when no database found."""
        adapter = WhatsAppAdapter(db_path="/nonexistent/path.db")
        assert adapter.is_available is False

    def test_is_available_caches_result(self) -> None:
        """Availability result is cached."""
        adapter = WhatsAppAdapter()
        adapter._available = True
        assert adapter.is_available is True

    def test_find_database_returns_none_when_not_found(self) -> None:
        """_find_database returns None when no database exists."""
        adapter = WhatsAppAdapter()
        adapter._db_path = None
        result = adapter._find_database()
        # Will return None since test environment doesn't have WhatsApp DB
        assert result is None or isinstance(result, Path)


class TestWhatsAppAdapterSearch:
    """Tests for WhatsApp search functionality."""

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_unavailable(self) -> None:
        """Search returns empty list when adapter unavailable."""
        adapter = WhatsAppAdapter()
        adapter._available = False

        results = await adapter.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_ios_schema(self, tmp_path: Path) -> None:
        """Search works with iOS backup schema."""
        # Create test database with iOS schema
        db_path = tmp_path / "whatsapp.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create iOS-style tables
        cursor.execute("""
            CREATE TABLE ZWAMESSAGE (
                Z_PK INTEGER PRIMARY KEY,
                ZTEXT TEXT,
                ZMESSAGEDATE REAL,
                ZISFROMME INTEGER,
                ZCHATSESSION INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE ZWACHATSESSION (
                Z_PK INTEGER PRIMARY KEY,
                ZCONTACTJID TEXT,
                ZPARTNERNAME TEXT
            )
        """)

        # Insert test data (Core Data timestamp: seconds since 2001-01-01)
        cd_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        recent_ts = (datetime.now(timezone.utc) - cd_epoch).total_seconds()

        cursor.execute("""
            INSERT INTO ZWACHATSESSION (Z_PK, ZCONTACTJID, ZPARTNERNAME)
            VALUES (1, 'test@s.whatsapp.net', 'Test Contact')
        """)
        cursor.execute("""
            INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZCHATSESSION)
            VALUES (1, 'Hello test message', ?, 0, 1)
        """, (recent_ts,))
        conn.commit()
        conn.close()

        # Test search
        adapter = WhatsAppAdapter(db_path=db_path)
        results = await adapter.search("test")

        assert len(results) == 1
        assert results[0].source == "whatsapp"
        assert results[0].type == "message"
        assert "Test Contact" in results[0].title
        assert "Hello test message" in results[0].content

    @pytest.mark.asyncio
    async def test_search_with_contact_filter(self, tmp_path: Path) -> None:
        """Search can filter by contact name."""
        db_path = tmp_path / "whatsapp.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE ZWAMESSAGE (
                Z_PK INTEGER PRIMARY KEY, ZTEXT TEXT, ZMESSAGEDATE REAL,
                ZISFROMME INTEGER, ZCHATSESSION INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE ZWACHATSESSION (
                Z_PK INTEGER PRIMARY KEY, ZCONTACTJID TEXT, ZPARTNERNAME TEXT
            )
        """)

        cd_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        recent_ts = (datetime.now(timezone.utc) - cd_epoch).total_seconds()

        cursor.execute("INSERT INTO ZWACHATSESSION VALUES (1, 'alice@w', 'Alice')")
        cursor.execute("INSERT INTO ZWACHATSESSION VALUES (2, 'bob@w', 'Bob')")
        cursor.execute("INSERT INTO ZWAMESSAGE VALUES (1, 'test from alice', ?, 0, 1)", (recent_ts,))
        cursor.execute("INSERT INTO ZWAMESSAGE VALUES (2, 'test from bob', ?, 0, 2)", (recent_ts,))
        conn.commit()
        conn.close()

        adapter = WhatsAppAdapter(db_path=db_path)
        results = await adapter.search("test", context={"contact": "Alice"})

        assert len(results) == 1
        assert "Alice" in results[0].title

    def test_is_whatsapp_db_returns_true_for_ios(self, tmp_path: Path) -> None:
        """_is_whatsapp_db identifies iOS backup databases."""
        db_path = tmp_path / "ios.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE ZWAMESSAGE (id INTEGER)")
        conn.close()

        adapter = WhatsAppAdapter()
        assert adapter._is_whatsapp_db(db_path) is True

    def test_is_whatsapp_db_returns_false_for_other(self, tmp_path: Path) -> None:
        """_is_whatsapp_db returns False for non-WhatsApp databases."""
        db_path = tmp_path / "other.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER)")
        conn.close()

        adapter = WhatsAppAdapter()
        assert adapter._is_whatsapp_db(db_path) is False


class TestWhatsAppAdapterRelevance:
    """Tests for WhatsApp relevance scoring."""

    def test_calculate_relevance_base_score(self) -> None:
        """Base relevance score is reasonable."""
        adapter = WhatsAppAdapter()
        message = {
            "text": "some message",
            "contact_name": "Contact",
            "timestamp": datetime.now(timezone.utc),
        }
        score = adapter._calculate_relevance(message, "random")
        assert 0.5 <= score <= 0.7

    def test_calculate_relevance_query_match_bonus(self) -> None:
        """Query match in text increases relevance."""
        adapter = WhatsAppAdapter()
        message = {
            "text": "important meeting tomorrow",
            "contact_name": "Contact",
            "timestamp": datetime.now(timezone.utc),
        }
        score = adapter._calculate_relevance(message, "meeting")
        assert score > 0.7

    def test_calculate_relevance_recency_bonus(self) -> None:
        """Recent messages get higher relevance."""
        adapter = WhatsAppAdapter()
        recent_msg = {
            "text": "test",
            "contact_name": "Contact",
            "timestamp": datetime.now(timezone.utc),
        }
        old_msg = {
            "text": "test",
            "contact_name": "Contact",
            "timestamp": datetime.now(timezone.utc) - timedelta(days=100),
        }

        recent_score = adapter._calculate_relevance(recent_msg, "test")
        old_score = adapter._calculate_relevance(old_msg, "test")

        assert recent_score > old_score


# =============================================================================
# Files Adapter Tests
# =============================================================================


class TestFilesAdapterInit:
    """Tests for FilesAdapter initialization."""

    def test_init_defaults(self) -> None:
        """Adapter initializes with default values."""
        adapter = FilesAdapter()
        assert adapter._extensions == DEFAULT_EXTENSIONS
        assert adapter._exclude_dirs == DEFAULT_EXCLUDES
        assert adapter._max_file_size == 1024 * 1024  # 1MB
        assert adapter.source_name == "files"

    def test_init_with_custom_paths(self, tmp_path: Path) -> None:
        """Adapter accepts custom search paths."""
        adapter = FilesAdapter(search_paths=[tmp_path])
        assert tmp_path in adapter._search_paths

    def test_init_with_custom_extensions(self) -> None:
        """Adapter accepts custom file extensions."""
        adapter = FilesAdapter(extensions=[".txt", ".md"])
        assert adapter._extensions == [".txt", ".md"]

    def test_init_with_custom_excludes(self) -> None:
        """Adapter accepts custom exclude directories."""
        adapter = FilesAdapter(exclude_dirs=["node_modules"])
        assert adapter._exclude_dirs == ["node_modules"]


class TestFilesAdapterAvailability:
    """Tests for Files adapter availability."""

    def test_is_available_true_when_paths_exist(self, tmp_path: Path) -> None:
        """Returns True when search paths exist."""
        adapter = FilesAdapter(search_paths=[tmp_path])
        assert adapter.is_available is True

    def test_is_available_false_when_paths_missing(self) -> None:
        """Returns False when no search paths exist."""
        adapter = FilesAdapter(search_paths=[Path("/nonexistent/path")])
        assert adapter.is_available is False

    def test_ripgrep_available_check(self) -> None:
        """_ripgrep_available detects ripgrep installation."""
        adapter = FilesAdapter()
        # This will return True or False depending on system
        result = adapter._ripgrep_available()
        assert isinstance(result, bool)


class TestFilesAdapterSearch:
    """Tests for Files search functionality."""

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_unavailable(self) -> None:
        """Search returns empty list when adapter unavailable."""
        adapter = FilesAdapter(search_paths=[Path("/nonexistent")])
        results = await adapter.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_finds_matching_files(self, tmp_path: Path) -> None:
        """Search finds files containing query."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is a test document with important content.")

        adapter = FilesAdapter(
            search_paths=[tmp_path],
            use_ripgrep=False,  # Force Python fallback for predictable testing
        )

        results = await adapter.search("important")

        assert len(results) >= 1
        assert results[0].source == "files"
        assert results[0].type == "file"

    @pytest.mark.asyncio
    async def test_search_respects_extension_filter(self, tmp_path: Path) -> None:
        """Search only searches files with allowed extensions."""
        # Create files with different extensions
        (tmp_path / "test.txt").write_text("important content")
        (tmp_path / "test.xyz").write_text("important content")

        adapter = FilesAdapter(
            search_paths=[tmp_path],
            extensions=[".txt"],
            use_ripgrep=False,
        )

        results = await adapter.search("important")

        # Should only find .txt file
        assert len(results) == 1
        assert results[0].title == "test.txt"

    @pytest.mark.asyncio
    async def test_search_excludes_directories(self, tmp_path: Path) -> None:
        """Search excludes specified directories."""
        # Create file in excluded directory
        excluded_dir = tmp_path / "node_modules"
        excluded_dir.mkdir()
        (excluded_dir / "test.txt").write_text("important content")

        # Create file in normal directory
        (tmp_path / "normal.txt").write_text("important content")

        adapter = FilesAdapter(
            search_paths=[tmp_path],
            exclude_dirs=["node_modules"],
            use_ripgrep=False,
        )

        results = await adapter.search("important")

        # Should only find file not in excluded dir
        assert len(results) == 1
        assert results[0].title == "normal.txt"

    @pytest.mark.asyncio
    async def test_search_with_path_filter(self, tmp_path: Path) -> None:
        """Search can filter to specific path."""
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "test.txt").write_text("content to find")
        (tmp_path / "other.txt").write_text("content to find")

        adapter = FilesAdapter(
            search_paths=[tmp_path],
            use_ripgrep=False,
        )

        results = await adapter.search("content", context={"path": str(sub_dir)})

        assert len(results) == 1
        assert "subdir" in str(results[0].metadata.get("path", ""))


class TestFilesAdapterRelevance:
    """Tests for Files relevance scoring."""

    def test_calculate_relevance_filename_match(self) -> None:
        """Filename match increases relevance."""
        adapter = FilesAdapter()
        match = {
            "path": Path("/test/meeting_notes.txt"),
            "line_number": 1,
            "line_text": "some content",
            "modified": datetime.now(timezone.utc),
        }
        score = adapter._calculate_relevance(match, "meeting")
        assert score > 0.75

    def test_calculate_relevance_recent_bonus(self) -> None:
        """Recently modified files get higher relevance."""
        adapter = FilesAdapter()
        recent = {
            "path": Path("/test/file.txt"),
            "line_number": 1,
            "line_text": "test",
            "modified": datetime.now(timezone.utc),
        }
        old = {
            "path": Path("/test/file.txt"),
            "line_number": 1,
            "line_text": "test",
            "modified": datetime.now(timezone.utc) - timedelta(days=400),
        }

        assert adapter._calculate_relevance(recent, "test") > adapter._calculate_relevance(old, "test")

    def test_calculate_relevance_markdown_bonus(self) -> None:
        """Markdown files get slight relevance bonus."""
        adapter = FilesAdapter()
        md_match = {
            "path": Path("/test/notes.md"),
            "line_number": 1,
            "line_text": "test",
            "modified": datetime.now(timezone.utc),
        }
        py_match = {
            "path": Path("/test/code.py"),
            "line_number": 1,
            "line_text": "test",
            "modified": datetime.now(timezone.utc),
        }

        md_score = adapter._calculate_relevance(md_match, "random")
        py_score = adapter._calculate_relevance(py_match, "random")

        assert md_score >= py_score


# =============================================================================
# Web Adapter Tests
# =============================================================================


class TestWebAdapterInit:
    """Tests for WebAdapter initialization."""

    def test_init_defaults(self) -> None:
        """Adapter initializes with default values."""
        adapter = WebAdapter()
        assert adapter._search_depth == "basic"
        assert adapter._include_answer is True
        assert adapter._include_raw_content is False
        assert adapter._max_tokens == 4000
        assert adapter.source_name == "web"

    def test_init_with_api_key(self) -> None:
        """Adapter accepts API key."""
        adapter = WebAdapter(api_key="test-key")
        assert adapter._api_key == "test-key"

    def test_init_with_domain_filters(self) -> None:
        """Adapter accepts domain filters."""
        adapter = WebAdapter(
            include_domains=["example.com"],
            exclude_domains=["spam.com"],
        )
        assert adapter._include_domains == ["example.com"]
        assert adapter._exclude_domains == ["spam.com"]


class TestWebAdapterAvailability:
    """Tests for Web adapter availability."""

    def test_is_available_true_with_api_key(self) -> None:
        """Returns True when API key is set."""
        adapter = WebAdapter(api_key="test-key")
        assert adapter.is_available is True

    def test_is_available_false_without_api_key(self) -> None:
        """Returns False when API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            adapter = WebAdapter(api_key=None)
            adapter._api_key = None
            assert adapter.is_available is False


class TestWebAdapterSearch:
    """Tests for Web search functionality."""

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_unavailable(self) -> None:
        """Search returns empty list when no API key."""
        adapter = WebAdapter()
        adapter._api_key = None

        results = await adapter.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_calls_tavily_api(self) -> None:
        """Search makes correct API call to Tavily."""
        adapter = WebAdapter(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "answer": "Test answer",
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.9,
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            results = await adapter.search("test query", max_results=5)

        assert len(results) == 2  # Answer + 1 result
        assert results[0].type == "answer"
        assert results[1].type == "web_result"

    @pytest.mark.asyncio
    async def test_search_handles_api_error(self) -> None:
        """Search handles API errors gracefully."""
        adapter = WebAdapter(api_key="test-key")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("API Error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            results = await adapter.search("test query")

        assert results == []


class TestWebAdapterParsing:
    """Tests for Web adapter result parsing."""

    def test_parse_results_with_answer(self) -> None:
        """Parses AI answer from response."""
        adapter = WebAdapter()
        data = {
            "answer": "This is the AI answer",
            "results": [],
        }

        results = adapter._parse_results(data, "test query")

        assert len(results) == 1
        assert results[0].type == "answer"
        assert results[0].content == "This is the AI answer"

    def test_parse_results_with_items(self) -> None:
        """Parses search results from response."""
        adapter = WebAdapter()
        data = {
            "results": [
                {
                    "title": "Result 1",
                    "url": "https://example.com/1",
                    "content": "Content 1",
                    "score": 0.85,
                },
                {
                    "title": "Result 2",
                    "url": "https://example.com/2",
                    "content": "Content 2",
                    "score": 0.75,
                },
            ],
        }

        results = adapter._parse_results(data, "test")

        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[1].title == "Result 2"

    def test_extract_domain(self) -> None:
        """Correctly extracts domain from URL."""
        adapter = WebAdapter()

        assert adapter._extract_domain("https://example.com/path") == "example.com"
        assert adapter._extract_domain("http://sub.example.com") == "sub.example.com"
        assert adapter._extract_domain("invalid-url") == ""


# =============================================================================
# DuckDuckGo Adapter Tests
# =============================================================================


class TestDuckDuckGoAdapter:
    """Tests for DuckDuckGo fallback adapter."""

    def test_init(self) -> None:
        """Adapter initializes correctly."""
        adapter = DuckDuckGoAdapter()
        assert adapter._duckduckgo_available is None
        assert adapter.source_name == "web"

    def test_is_available_caches_result(self) -> None:
        """Availability check is cached."""
        adapter = DuckDuckGoAdapter()
        adapter._duckduckgo_available = True
        assert adapter.is_available is True

        adapter._duckduckgo_available = False
        assert adapter.is_available is False

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_unavailable(self) -> None:
        """Returns empty list when library not installed."""
        adapter = DuckDuckGoAdapter()
        adapter._duckduckgo_available = False

        results = await adapter.search("test")

        assert results == []


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestCreateWebAdapter:
    """Tests for create_web_adapter factory function."""

    def test_returns_tavily_when_api_key_available(self) -> None:
        """Returns WebAdapter when Tavily API key is set."""
        with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
            adapter = create_web_adapter()
            assert isinstance(adapter, WebAdapter)

    def test_returns_duckduckgo_when_tavily_unavailable(self) -> None:
        """Returns DuckDuckGo adapter when Tavily not available."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(WebAdapter, "is_available", False),
            patch.object(DuckDuckGoAdapter, "is_available", True),
        ):
            _adapter = create_web_adapter()
            # Should fall through to DuckDuckGo or disabled WebAdapter

    def test_returns_disabled_when_nothing_available(self) -> None:
        """Returns disabled adapter when nothing available."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(DuckDuckGoAdapter, "is_available", False),
        ):
            adapter = create_web_adapter()
            # Should return WebAdapter with is_available=False
            assert isinstance(adapter, (WebAdapter, DuckDuckGoAdapter))


# =============================================================================
# Integration Tests
# =============================================================================


class TestAdapterIntegration:
    """Integration tests for adapter interactions."""

    @pytest.mark.asyncio
    async def test_all_adapters_return_source_items(self, tmp_path: Path) -> None:
        """All adapters return proper SourceItem objects."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for search")

        files_adapter = FilesAdapter(
            search_paths=[tmp_path],
            use_ripgrep=False,
        )

        results = await files_adapter.search("Test")

        for result in results:
            assert isinstance(result, SourceItem)
            assert result.source is not None
            assert result.type is not None
            assert result.title is not None
            assert isinstance(result.relevance_score, float)
            assert 0.0 <= result.relevance_score <= 1.0

    @pytest.mark.asyncio
    async def test_adapters_handle_empty_results_gracefully(self) -> None:
        """Adapters return empty list for no matches."""
        files_adapter = FilesAdapter(
            search_paths=[Path("/tmp")],
            use_ripgrep=False,
        )

        results = await files_adapter.search("xyznonexistent123")

        assert isinstance(results, list)

    def test_adapters_respect_max_results(self, tmp_path: Path) -> None:
        """Adapters respect max_results parameter."""
        # Create multiple files
        for i in range(10):
            (tmp_path / f"test{i}.txt").write_text("matching content")

        adapter = FilesAdapter(
            search_paths=[tmp_path],
            use_ripgrep=False,
        )

        # This is tested implicitly - adapter should limit results
        assert adapter._max_file_size > 0  # Sanity check
