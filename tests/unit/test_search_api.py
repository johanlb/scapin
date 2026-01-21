"""
Tests for Search API

Tests for global search models, service, and router.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.config_manager import ScapinConfig
from src.frontin.api.models.search import (
    CalendarSearchResultItem,
    EmailSearchResultItem,
    GlobalSearchResponse,
    NoteSearchResultItem,
    RecentSearchesResponse,
    RecentSearchItem,
    SearchResultCounts,
    SearchResultsByType,
    SearchResultType,
    TeamsSearchResultItem,
)
from src.frontin.api.services.search_service import (
    SearchService,
    _highlight_matches,
    _text_match_score,
)

# =============================================================================
# Model Tests
# =============================================================================


class TestSearchModels:
    """Test search Pydantic models"""

    def test_search_result_type_enum(self):
        """Test SearchResultType enum values"""
        assert SearchResultType.NOTE == "note"
        assert SearchResultType.EMAIL == "email"
        assert SearchResultType.CALENDAR == "calendar"
        assert SearchResultType.TEAMS == "teams"

    def test_note_search_result_item(self):
        """Test NoteSearchResultItem creation"""
        item = NoteSearchResultItem(
            id="note-123",
            title="Meeting Notes",
            excerpt="Discussion about project...",
            score=0.85,
            timestamp=datetime.now(timezone.utc),
            path="Work/Projects",
            tags=["meeting", "project"],
        )
        assert item.id == "note-123"
        assert item.type == SearchResultType.NOTE
        assert item.score == 0.85
        assert item.path == "Work/Projects"
        assert "meeting" in item.tags

    def test_email_search_result_item(self):
        """Test EmailSearchResultItem creation"""
        item = EmailSearchResultItem(
            id="email-456",
            title="Re: Project Update",
            excerpt="Here's the latest...",
            score=0.75,
            timestamp=datetime.now(timezone.utc),
            from_address="john@example.com",
            from_name="John Doe",
            status="pending",
        )
        assert item.id == "email-456"
        assert item.type == SearchResultType.EMAIL
        assert item.from_address == "john@example.com"
        assert item.status == "pending"

    def test_calendar_search_result_item(self):
        """Test CalendarSearchResultItem creation"""
        now = datetime.now(timezone.utc)
        item = CalendarSearchResultItem(
            id="event-789",
            title="Team Standup",
            excerpt="Daily standup meeting",
            score=0.9,
            timestamp=now,
            start=now,
            end=now,
            location="Room 101",
            organizer="Jane",
        )
        assert item.id == "event-789"
        assert item.type == SearchResultType.CALENDAR
        assert item.location == "Room 101"

    def test_teams_search_result_item(self):
        """Test TeamsSearchResultItem creation"""
        item = TeamsSearchResultItem(
            id="msg-abc",
            title="Team Discussion",
            excerpt="About the release...",
            score=0.7,
            timestamp=datetime.now(timezone.utc),
            chat_id="chat-123",
            sender="Alice",
        )
        assert item.id == "msg-abc"
        assert item.type == SearchResultType.TEAMS
        assert item.chat_id == "chat-123"

    def test_search_results_by_type(self):
        """Test SearchResultsByType creation"""
        results = SearchResultsByType()
        assert results.notes == []
        assert results.emails == []
        assert results.calendar == []
        assert results.teams == []

    def test_search_result_counts(self):
        """Test SearchResultCounts creation"""
        counts = SearchResultCounts(notes=5, emails=10, calendar=2, teams=3)
        assert counts.notes == 5
        assert counts.emails == 10
        assert counts.calendar == 2
        assert counts.teams == 3

    def test_global_search_response(self):
        """Test GlobalSearchResponse creation"""
        response = GlobalSearchResponse(
            query="meeting",
            total=20,
            search_time_ms=15.5,
        )
        assert response.query == "meeting"
        assert response.total == 20
        assert response.search_time_ms == 15.5
        assert response.results.notes == []

    def test_recent_search_item(self):
        """Test RecentSearchItem creation"""
        item = RecentSearchItem(
            query="project update",
            timestamp=datetime.now(timezone.utc),
            result_count=15,
        )
        assert item.query == "project update"
        assert item.result_count == 15

    def test_recent_searches_response(self):
        """Test RecentSearchesResponse creation"""
        response = RecentSearchesResponse(
            searches=[
                RecentSearchItem(
                    query="test",
                    timestamp=datetime.now(timezone.utc),
                    result_count=5,
                )
            ],
            total=1,
        )
        assert len(response.searches) == 1
        assert response.total == 1


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Test search helper functions"""

    def test_highlight_matches_basic(self):
        """Test basic highlight matching"""
        text = "This is a test document about meetings and projects."
        result = _highlight_matches(text, "meetings")
        assert "meetings" in result.lower()

    def test_highlight_matches_no_match(self):
        """Test highlight with no matches"""
        text = "This is a test document."
        result = _highlight_matches(text, "nonexistent")
        assert result == text

    def test_highlight_matches_empty_text(self):
        """Test highlight with empty text"""
        result = _highlight_matches("", "test")
        assert result == ""

    def test_highlight_matches_empty_query(self):
        """Test highlight with empty query"""
        text = "Some text here"
        result = _highlight_matches(text, "")
        assert result == text

    def test_highlight_matches_long_text(self):
        """Test highlight with long text (truncation)"""
        text = "A" * 500
        result = _highlight_matches(text, "test")
        assert len(result) <= 210  # 200 + "..."

    def test_text_match_score_exact(self):
        """Test text match score with exact match"""
        score = _text_match_score("Meeting with John tomorrow", "meeting")
        assert score > 0

    def test_text_match_score_phrase(self):
        """Test text match score with phrase"""
        score = _text_match_score("Meeting with John tomorrow", "meeting with john")
        assert score > 0.5  # Multiple words matching + phrase bonus

    def test_text_match_score_no_match(self):
        """Test text match score with no match"""
        score = _text_match_score("Meeting with John", "zebra")
        assert score == 0.0

    def test_text_match_score_empty_text(self):
        """Test text match score with empty text"""
        score = _text_match_score("", "test")
        assert score == 0.0

    def test_text_match_score_empty_query(self):
        """Test text match score with empty query"""
        score = _text_match_score("Some text", "")
        assert score == 0.0

    def test_text_match_score_start_bonus(self):
        """Test text match score with match at beginning"""
        # Use longer text so the bonus makes a difference
        score_start = _text_match_score("meeting with team tomorrow", "meeting")
        score_middle = _text_match_score("tomorrow we have a meeting", "meeting")
        # Both should have high scores, but start should be slightly higher due to bonus
        assert score_start >= score_middle  # Start bonus (or equal if both match well)


# =============================================================================
# Service Tests
# =============================================================================


class TestSearchService:
    """Test SearchService"""

    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        config = MagicMock(spec=ScapinConfig)
        config.notes_dir = None
        return config

    @pytest.fixture
    def service(self, mock_config):
        """Create service instance"""
        return SearchService(config=mock_config)

    @pytest.fixture
    def temp_queue_dir(self):
        """Create temporary queue directory with test data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()

            # Create test queue items
            items = [
                {
                    "id": "item-1",
                    "account_id": "personal",
                    "queued_at": "2026-01-05T10:00:00+00:00",
                    "metadata": {
                        "id": "123",
                        "subject": "Meeting Tomorrow",
                        "from_address": "john@example.com",
                        "from_name": "John Doe",
                        "date": "2026-01-05T09:00:00+00:00",
                        "has_attachments": False,
                    },
                    "content": {"preview": "Let's discuss the project status"},
                    "analysis": {"action": "archive", "confidence": 0.8},
                    "status": "pending",
                },
                {
                    "id": "item-2",
                    "account_id": "work",
                    "queued_at": "2026-01-05T11:00:00+00:00",
                    "metadata": {
                        "id": "456",
                        "subject": "Project Update Required",
                        "from_address": "jane@company.com",
                        "from_name": "Jane Smith",
                        "date": "2026-01-05T10:00:00+00:00",
                        "has_attachments": True,
                    },
                    "content": {"preview": "Please send the quarterly report"},
                    "analysis": {"action": "task", "confidence": 0.9},
                    "status": "pending",
                },
            ]

            for item in items:
                file_path = queue_dir / f"{item['id']}.json"
                with open(file_path, "w") as f:
                    json.dump(item, f)

            yield queue_dir

    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service._note_manager is None
        assert service._queue_storage is None
        assert service._recent_searches == []

    def test_add_recent_search(self, service):
        """Test adding recent search"""
        service._add_recent_search("test query", 10)
        assert len(service._recent_searches) == 1
        assert service._recent_searches[0].query == "test query"
        assert service._recent_searches[0].result_count == 10

    def test_add_recent_search_limit(self, service):
        """Test recent search list respects limit"""
        service._max_recent_searches = 5
        for i in range(10):
            service._add_recent_search(f"query {i}", i)
        assert len(service._recent_searches) == 5

    @pytest.mark.asyncio
    async def test_search_notes_with_mock(self, service):
        """Test notes search with mocked NoteManager"""
        # Create mock note
        mock_note = MagicMock()
        mock_note.note_id = "note-123"
        mock_note.title = "Test Note"
        mock_note.content = "This is a test note about meetings"
        mock_note.tags = ["test"]
        mock_note.updated_at = datetime.now(timezone.utc)
        mock_note.created_at = datetime.now(timezone.utc)
        mock_note.metadata = {"path": "Tests"}

        # Mock NoteManager
        # Note: search_notes returns L2 distance, which is converted to similarity
        # using formula: similarity = 1 / (1 + distance)
        # To get a similarity score of ~0.85, we need distance ≈ 0.176
        l2_distance = 0.176
        expected_score = 1.0 / (1.0 + l2_distance)  # ≈ 0.85
        mock_manager = MagicMock()
        mock_manager.search_notes.return_value = [(mock_note, l2_distance)]
        service._note_manager = mock_manager

        results = await service._search_notes("meetings", 10, None, None)

        assert len(results) == 1
        assert results[0].id == "note-123"
        assert abs(results[0].score - expected_score) < 0.01  # Allow small float error
        mock_manager.search_notes.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_emails_with_mock(self, service, temp_queue_dir):
        """Test email search with queue storage"""
        from src.integrations.storage.queue_storage import QueueStorage

        service._queue_storage = QueueStorage(queue_dir=temp_queue_dir)

        results = await service._search_emails("meeting", 10, None, None)

        assert len(results) == 1
        assert results[0].title == "Meeting Tomorrow"
        assert results[0].from_name == "John Doe"

    @pytest.mark.asyncio
    async def test_search_emails_project_query(self, service, temp_queue_dir):
        """Test email search with different query"""
        from src.integrations.storage.queue_storage import QueueStorage

        service._queue_storage = QueueStorage(queue_dir=temp_queue_dir)

        results = await service._search_emails("project", 10, None, None)

        # Both items mention "project"
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_calendar_not_implemented(self, service):
        """Test calendar search returns empty (not implemented)"""
        results = await service._search_calendar("test", 10, None, None)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_teams_not_implemented(self, service):
        """Test teams search returns empty (not implemented)"""
        results = await service._search_teams("test", 10, None, None)
        assert results == []

    @pytest.mark.asyncio
    async def test_global_search(self, service, temp_queue_dir):
        """Test global search across types"""
        from src.integrations.storage.queue_storage import QueueStorage

        service._queue_storage = QueueStorage(queue_dir=temp_queue_dir)

        # Mock notes to return empty
        mock_manager = MagicMock()
        mock_manager.search_notes.return_value = []
        service._note_manager = mock_manager

        response = await service.search(
            query="meeting",
            types=[SearchResultType.EMAIL],
            limit_per_type=10,
        )

        assert response.query == "meeting"
        assert response.counts.emails == 1
        assert response.total == 1
        assert response.search_time_ms > 0

    @pytest.mark.asyncio
    async def test_get_recent_searches(self, service):
        """Test getting recent searches"""
        service._add_recent_search("query 1", 5)
        service._add_recent_search("query 2", 10)

        response = await service.get_recent_searches(limit=5)

        assert len(response.searches) == 2
        assert response.searches[0].query == "query 2"  # Most recent first
        assert response.total == 2


# =============================================================================
# Router Tests
# =============================================================================


class TestSearchRouter:
    """Test search router endpoints"""

    @pytest.fixture
    def mock_service(self):
        """Create mock search service"""
        service = MagicMock(spec=SearchService)
        return service

    @pytest.fixture
    def app(self, mock_service):
        """Create test FastAPI app with mocked service"""
        from src.frontin.api.routers import search as search_module

        app = FastAPI()

        # Override dependency
        def get_mock_service():
            return mock_service

        app.include_router(search_module.router, prefix="/api/search")
        app.dependency_overrides[search_module._get_search_service] = get_mock_service

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_global_search_endpoint(self, client, mock_service):
        """Test GET /api/search endpoint"""
        mock_service.search.return_value = GlobalSearchResponse(
            query="test",
            results=SearchResultsByType(),
            total=0,
            counts=SearchResultCounts(),
            search_time_ms=10.0,
        )

        response = client.get("/api/search?q=test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["query"] == "test"

    @pytest.mark.asyncio
    async def test_global_search_with_types(self, client, mock_service):
        """Test search with type filter"""
        mock_service.search.return_value = GlobalSearchResponse(
            query="test",
            total=0,
            search_time_ms=5.0,
        )

        response = client.get("/api/search?q=test&types=note,email")

        assert response.status_code == 200
        mock_service.search.assert_called_once()
        call_kwargs = mock_service.search.call_args.kwargs
        assert SearchResultType.NOTE in call_kwargs["types"]
        assert SearchResultType.EMAIL in call_kwargs["types"]

    @pytest.mark.asyncio
    async def test_global_search_with_limit(self, client, mock_service):
        """Test search with limit"""
        mock_service.search.return_value = GlobalSearchResponse(
            query="test",
            total=0,
            search_time_ms=5.0,
        )

        response = client.get("/api/search?q=test&limit=20")

        assert response.status_code == 200
        call_kwargs = mock_service.search.call_args.kwargs
        assert call_kwargs["limit_per_type"] == 20

    @pytest.mark.asyncio
    async def test_global_search_with_date_range(self, client, mock_service):
        """Test search with date filters"""
        mock_service.search.return_value = GlobalSearchResponse(
            query="test",
            total=0,
            search_time_ms=5.0,
        )

        response = client.get(
            "/api/search?q=test"
            "&date_from=2026-01-01T00:00:00"
            "&date_to=2026-01-31T23:59:59"
        )

        assert response.status_code == 200
        call_kwargs = mock_service.search.call_args.kwargs
        assert call_kwargs["date_from"] is not None
        assert call_kwargs["date_to"] is not None

    def test_global_search_query_required(self, client, mock_service):
        """Test search requires query parameter"""
        response = client.get("/api/search")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_recent_searches_endpoint(self, client, mock_service):
        """Test GET /api/search/recent endpoint"""
        mock_service.get_recent_searches.return_value = RecentSearchesResponse(
            searches=[
                RecentSearchItem(
                    query="test query",
                    timestamp=datetime.now(timezone.utc),
                    result_count=5,
                )
            ],
            total=1,
        )

        response = client.get("/api/search/recent")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["searches"]) == 1

    @pytest.mark.asyncio
    async def test_recent_searches_with_limit(self, client, mock_service):
        """Test recent searches with limit"""
        mock_service.get_recent_searches.return_value = RecentSearchesResponse(
            searches=[],
            total=0,
        )

        response = client.get("/api/search/recent?limit=50")

        assert response.status_code == 200
        mock_service.get_recent_searches.assert_called_once_with(limit=50)


# =============================================================================
# Cross-Source Search Tests
# =============================================================================


class TestCrossSourceModels:
    """Test cross-source search models"""

    def test_cross_source_type_enum(self):
        """Test CrossSourceType enum values"""
        from src.frontin.api.models.search import CrossSourceType

        assert CrossSourceType.EMAIL.value == "email"
        assert CrossSourceType.CALENDAR.value == "calendar"
        assert CrossSourceType.ICLOUD_CALENDAR.value == "icloud_calendar"
        assert CrossSourceType.TEAMS.value == "teams"
        assert CrossSourceType.WHATSAPP.value == "whatsapp"
        assert CrossSourceType.FILES.value == "files"
        assert CrossSourceType.WEB.value == "web"

    def test_cross_source_search_request(self):
        """Test CrossSourceSearchRequest model"""
        from src.frontin.api.models.search import (
            CrossSourceSearchRequest,
            CrossSourceType,
        )

        request = CrossSourceSearchRequest(
            query="meeting with John",
            sources=[CrossSourceType.CALENDAR, CrossSourceType.TEAMS],
            max_results=30,
            min_relevance=0.5,
            include_content=False,
        )

        assert request.query == "meeting with John"
        assert len(request.sources) == 2
        assert request.max_results == 30
        assert request.min_relevance == 0.5
        assert request.include_content is False

    def test_cross_source_search_request_defaults(self):
        """Test CrossSourceSearchRequest default values"""
        from src.frontin.api.models.search import CrossSourceSearchRequest

        request = CrossSourceSearchRequest(query="test")

        assert request.sources is None
        assert request.max_results == 20
        assert request.min_relevance == 0.3
        assert request.include_content is True

    def test_cross_source_result_item(self):
        """Test CrossSourceResultItem model"""
        from src.frontin.api.models.search import CrossSourceResultItem

        item = CrossSourceResultItem(
            source="calendar",
            type="event",
            title="Team Meeting",
            content="Weekly sync",
            timestamp=datetime.now(timezone.utc),
            relevance_score=0.9,
            final_score=0.85,
            url="https://calendar.com/event/123",
            metadata={"attendees": 5},
        )

        assert item.source == "calendar"
        assert item.type == "event"
        assert item.title == "Team Meeting"
        assert item.relevance_score == 0.9
        assert item.final_score == 0.85
        assert item.metadata["attendees"] == 5

    def test_cross_source_search_response(self):
        """Test CrossSourceSearchResponse model"""
        from src.frontin.api.models.search import (
            CrossSourceResultItem,
            CrossSourceSearchResponse,
        )

        response = CrossSourceSearchResponse(
            query="test",
            items=[
                CrossSourceResultItem(
                    source="email",
                    type="message",
                    title="Test email",
                    relevance_score=0.8,
                    final_score=0.75,
                )
            ],
            total_results=1,
            sources_searched=["email", "calendar"],
            sources_available=["email", "calendar", "teams"],
            search_time_ms=50.0,
            cached=True,
        )

        assert response.query == "test"
        assert len(response.items) == 1
        assert response.total_results == 1
        assert "email" in response.sources_searched
        assert response.cached is True


class TestCrossSourceService:
    """Test cross-source search service"""

    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        config = MagicMock(spec=ScapinConfig)
        config.notes_dir = None
        return config

    @pytest.fixture
    def service(self, mock_config):
        """Create service instance"""
        return SearchService(config=mock_config)

    @pytest.mark.asyncio
    async def test_cross_source_search_basic(self, service):
        """Test cross-source search with mocked engine"""
        from src.frontin.api.models.search import CrossSourceSearchRequest

        # Create a mock SourceItem
        mock_source_item = MagicMock()
        mock_source_item.source = "calendar"
        mock_source_item.type = "event"
        mock_source_item.title = "Team Meeting"
        mock_source_item.content = "Weekly sync"
        mock_source_item.timestamp = datetime.now(timezone.utc)
        mock_source_item.relevance_score = 0.9
        mock_source_item.final_score = 0.85
        mock_source_item.url = None
        mock_source_item.metadata = {}

        # Create mock search result
        mock_result = MagicMock()
        mock_result.items = [mock_source_item]
        mock_result.sources_searched = ["calendar"]
        mock_result.from_cache = False

        # Mock the engine
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=mock_result)
        mock_engine.available_sources = ["calendar", "email"]

        with patch(
            "src.passepartout.cross_source.create_cross_source_engine"
        ) as mock_create:
            mock_create.return_value = mock_engine

            request = CrossSourceSearchRequest(query="meeting")
            response = await service.cross_source_search(request)

            assert response.query == "meeting"
            assert response.total_results == 1
            assert len(response.items) == 1
            assert response.items[0].source == "calendar"
            assert response.items[0].title == "Team Meeting"

    @pytest.mark.asyncio
    async def test_cross_source_search_with_source_filter(self, service):
        """Test cross-source search with source filtering"""
        from src.frontin.api.models.search import (
            CrossSourceSearchRequest,
            CrossSourceType,
        )

        mock_result = MagicMock()
        mock_result.items = []
        mock_result.sources_searched = ["calendar"]
        mock_result.from_cache = False

        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=mock_result)
        mock_engine.available_sources = ["calendar"]

        with patch(
            "src.passepartout.cross_source.create_cross_source_engine"
        ) as mock_create:
            mock_create.return_value = mock_engine

            request = CrossSourceSearchRequest(
                query="meeting",
                sources=[CrossSourceType.CALENDAR],
            )
            await service.cross_source_search(request)

            mock_engine.search.assert_called_once()
            call_kwargs = mock_engine.search.call_args.kwargs
            assert call_kwargs["preferred_sources"] == ["calendar"]

    @pytest.mark.asyncio
    async def test_cross_source_search_min_relevance_filter(self, service):
        """Test that results below min_relevance are filtered out"""
        from src.frontin.api.models.search import CrossSourceSearchRequest

        # Create items with different relevance scores
        high_score_item = MagicMock()
        high_score_item.source = "calendar"
        high_score_item.type = "event"
        high_score_item.title = "High Score"
        high_score_item.content = "Content"
        high_score_item.timestamp = datetime.now(timezone.utc)
        high_score_item.relevance_score = 0.8
        high_score_item.final_score = 0.8
        high_score_item.url = None
        high_score_item.metadata = {}

        low_score_item = MagicMock()
        low_score_item.source = "email"
        low_score_item.type = "message"
        low_score_item.title = "Low Score"
        low_score_item.content = "Content"
        low_score_item.timestamp = datetime.now(timezone.utc)
        low_score_item.relevance_score = 0.2
        low_score_item.final_score = 0.2
        low_score_item.url = None
        low_score_item.metadata = {}

        mock_result = MagicMock()
        mock_result.items = [high_score_item, low_score_item]
        mock_result.sources_searched = ["calendar", "email"]
        mock_result.from_cache = False

        mock_engine = MagicMock()
        mock_engine.search = AsyncMock(return_value=mock_result)
        mock_engine.available_sources = ["calendar", "email"]

        with patch(
            "src.passepartout.cross_source.create_cross_source_engine"
        ) as mock_create:
            mock_create.return_value = mock_engine

            request = CrossSourceSearchRequest(
                query="test",
                min_relevance=0.5,  # Should filter out low_score_item
            )
            response = await service.cross_source_search(request)

            assert response.total_results == 1
            assert response.items[0].title == "High Score"

    @pytest.mark.asyncio
    async def test_cross_source_search_error_handling(self, service):
        """Test cross-source search handles errors gracefully"""
        from src.frontin.api.models.search import CrossSourceSearchRequest

        with patch(
            "src.passepartout.cross_source.create_cross_source_engine"
        ) as mock_create:
            mock_create.side_effect = Exception("Engine creation failed")

            request = CrossSourceSearchRequest(query="test")
            response = await service.cross_source_search(request)

            # Should return empty response on error
            assert response.query == "test"
            assert response.total_results == 0
            assert len(response.items) == 0


class TestCrossSourceRouter:
    """Test cross-source search router endpoint"""

    @pytest.fixture
    def mock_service(self):
        """Create mock search service"""
        service = MagicMock(spec=SearchService)
        return service

    @pytest.fixture
    def app(self, mock_service):
        """Create test FastAPI app with mocked service"""
        from src.frontin.api.routers import search as search_module

        app = FastAPI()

        def get_mock_service():
            return mock_service

        app.include_router(search_module.router, prefix="/api/search")
        app.dependency_overrides[search_module._get_search_service] = get_mock_service

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_cross_source_search_endpoint(self, client, mock_service):
        """Test POST /api/search/cross-source endpoint"""
        from src.frontin.api.models.search import (
            CrossSourceResultItem,
            CrossSourceSearchResponse,
        )

        mock_service.cross_source_search.return_value = CrossSourceSearchResponse(
            query="meeting",
            items=[
                CrossSourceResultItem(
                    source="calendar",
                    type="event",
                    title="Team Meeting",
                    relevance_score=0.9,
                    final_score=0.85,
                )
            ],
            total_results=1,
            sources_searched=["calendar"],
            sources_available=["calendar", "email", "teams"],
            search_time_ms=25.0,
            cached=False,
        )

        response = client.post(
            "/api/search/cross-source",
            json={"query": "meeting"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["query"] == "meeting"
        assert data["data"]["total_results"] == 1
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["source"] == "calendar"

    @pytest.mark.asyncio
    async def test_cross_source_search_with_options(self, client, mock_service):
        """Test POST /api/search/cross-source with all options"""
        from src.frontin.api.models.search import CrossSourceSearchResponse

        mock_service.cross_source_search.return_value = CrossSourceSearchResponse(
            query="project update",
            items=[],
            total_results=0,
            sources_searched=["calendar", "teams"],
            sources_available=["calendar", "teams"],
            search_time_ms=15.0,
            cached=False,
        )

        response = client.post(
            "/api/search/cross-source",
            json={
                "query": "project update",
                "sources": ["calendar", "teams"],
                "max_results": 50,
                "min_relevance": 0.5,
                "include_content": False,
            },
        )

        assert response.status_code == 200
        mock_service.cross_source_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_cross_source_search_query_required(self, client, mock_service):
        """Test POST /api/search/cross-source requires query"""
        response = client.post(
            "/api/search/cross-source",
            json={},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_cross_source_search_query_min_length(self, client, mock_service):
        """Test query minimum length validation"""
        response = client.post(
            "/api/search/cross-source",
            json={"query": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_cross_source_search_error_response(self, client, mock_service):
        """Test error handling in cross-source endpoint"""
        mock_service.cross_source_search.side_effect = Exception("Search failed")

        response = client.post(
            "/api/search/cross-source",
            json={"query": "test"},
        )

        assert response.status_code == 500
