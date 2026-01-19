"""
Tests for Stats API Router

Tests overview and by-source stats endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.frontin.api.app import create_app
from src.frontin.api.deps import get_cached_config, get_current_user
from src.frontin.api.models.stats import StatsBySourceResponse, StatsOverviewResponse
from src.frontin.api.services.stats_service import StatsService


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock configuration"""
    config = MagicMock()

    # Email config
    account = MagicMock()
    account.account_id = "test"
    account.imap_username = "test@example.com"
    account.enabled = True
    config.email.get_enabled_accounts.return_value = [account]

    # Auth config - disable for tests
    config.auth.enabled = False
    config.auth.warn_disabled_in_production = False

    # Integration configs
    config.teams.enabled = True
    config.calendar.enabled = True
    config.briefing.enabled = True
    config.ai.model = "claude-3-5-haiku-20241022"

    # Environment
    config.environment = "test"

    return config


@pytest.fixture
def client(mock_config: MagicMock) -> TestClient:
    """Create test client with mocked config and disabled auth"""
    app = create_app()
    app.dependency_overrides[get_cached_config] = lambda: mock_config
    # Disable auth by returning None (simulates auth disabled)
    app.dependency_overrides[get_current_user] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestStatsModels:
    """Tests for Stats Pydantic models"""

    def test_stats_overview_response_defaults(self) -> None:
        """Test StatsOverviewResponse has correct defaults"""
        overview = StatsOverviewResponse(uptime_seconds=100.0)

        assert overview.total_processed == 0
        assert overview.total_pending == 0
        assert overview.sources_active == 0
        assert overview.uptime_seconds == 100.0
        assert overview.last_activity is None
        assert overview.email_processed == 0
        assert overview.email_queued == 0
        assert overview.teams_messages == 0
        assert overview.teams_unread == 0
        assert overview.calendar_events_today == 0
        assert overview.calendar_events_week == 0
        assert overview.notes_due == 0
        assert overview.notes_reviewed_today == 0

    def test_stats_overview_response_with_values(self) -> None:
        """Test StatsOverviewResponse with custom values"""
        now = datetime.now(timezone.utc)
        overview = StatsOverviewResponse(
            total_processed=100,
            total_pending=10,
            sources_active=3,
            uptime_seconds=3600.0,
            last_activity=now,
            email_processed=50,
            email_queued=5,
            teams_messages=30,
            teams_unread=2,
            calendar_events_today=3,
            calendar_events_week=10,
            notes_due=15,
            notes_reviewed_today=5,
        )

        assert overview.total_processed == 100
        assert overview.total_pending == 10
        assert overview.sources_active == 3
        assert overview.uptime_seconds == 3600.0
        assert overview.last_activity == now
        assert overview.email_processed == 50
        assert overview.teams_messages == 30
        assert overview.notes_due == 15

    def test_stats_by_source_response_all_none(self) -> None:
        """Test StatsBySourceResponse with all sources None"""
        response = StatsBySourceResponse()

        assert response.email is None
        assert response.teams is None
        assert response.calendar is None
        assert response.queue is None
        assert response.notes is None


class TestStatsService:
    """Tests for StatsService"""

    @pytest.fixture
    def mock_services(self) -> dict:
        """Create mock services"""
        email_service = MagicMock()
        email_service.get_stats = AsyncMock(
            return_value={
                "emails_processed": 100,
                "emails_auto_executed": 80,
                "emails_archived": 60,
                "emails_deleted": 10,
                "emails_queued": 5,
                "emails_skipped": 5,
                "tasks_created": 10,
                "average_confidence": 0.85,
                "processing_mode": "cognitive",
            }
        )

        queue_service = MagicMock()
        queue_service.get_stats = AsyncMock(
            return_value={
                "total": 5,
                "by_status": {"pending": 3, "approved": 2},
                "by_account": {"work": 3, "personal": 2},
            }
        )

        teams_service = MagicMock()
        teams_service.get_stats = AsyncMock(
            return_value={
                "total_chats": 20,
                "unread_chats": 3,
                "messages_processed": 50,
                "messages_flagged": 5,
            }
        )

        notes_service = MagicMock()
        notes_service.get_review_stats = AsyncMock(
            return_value=MagicMock(
                total_notes=200,
                by_type={"projet": 50, "personne": 30},
                by_importance={"high": 20, "medium": 100},
                total_due=15,
                reviewed_today=5,
                avg_easiness_factor=2.5,
            )
        )

        return {
            "email": email_service,
            "queue": queue_service,
            "teams": teams_service,
            "notes": notes_service,
        }

    @pytest.mark.asyncio
    async def test_get_overview_aggregates_stats(self, mock_services: dict) -> None:
        """Test get_overview aggregates stats from all sources"""
        with (
            patch("src.frontin.api.services.stats_service.get_config") as mock_config,
            patch(
                "src.frontin.api.services.stats_service.get_state_manager"
            ) as mock_state,
            patch(
                "src.frontin.api.services.stats_service.EmailService",
                return_value=mock_services["email"],
            ),
            patch(
                "src.frontin.api.services.stats_service.QueueService",
                return_value=mock_services["queue"],
            ),
            patch(
                "src.frontin.api.services.stats_service.TeamsService",
                return_value=mock_services["teams"],
            ),
            patch(
                "src.frontin.api.services.stats_service.NotesReviewService",
                return_value=mock_services["notes"],
            ),
        ):
            config = MagicMock()
            config.email.get_enabled_accounts.return_value = [MagicMock()]
            config.teams.enabled = True
            config.calendar.enabled = True
            mock_config.return_value = config

            # Mock state manager to return calendar values
            state = MagicMock()
            state.get.side_effect = lambda key, default=None: {
                "calendar_events_today": 3,
                "calendar_events_week": 10,
                "calendar_meetings_online": 2,
                "calendar_meetings_in_person": 1,
                "calendar_last_poll": None,
                "last_activity": None,
            }.get(key, default)
            mock_state.return_value = state

            service = StatsService()
            overview = await service.get_overview()

            assert overview.email_processed == 100
            assert overview.email_queued == 5
            assert overview.teams_messages == 50
            assert overview.teams_unread == 3
            assert overview.notes_due == 15
            assert overview.notes_reviewed_today == 5
            assert overview.total_processed == 150  # 100 emails + 50 teams
            assert overview.total_pending == 23  # 5 queue + 3 unread + 15 notes
            assert overview.calendar_events_today == 3
            assert overview.calendar_events_week == 10

    @pytest.mark.asyncio
    async def test_get_overview_handles_service_errors(self) -> None:
        """Test get_overview handles service errors gracefully"""
        with (
            patch("src.frontin.api.services.stats_service.get_config") as mock_config,
            patch(
                "src.frontin.api.services.stats_service.get_state_manager"
            ) as mock_state,
            patch(
                "src.frontin.api.services.stats_service.EmailService"
            ) as mock_email_cls,
            patch(
                "src.frontin.api.services.stats_service.QueueService"
            ) as mock_queue_cls,
            patch(
                "src.frontin.api.services.stats_service.TeamsService"
            ),
            patch(
                "src.frontin.api.services.stats_service.NotesReviewService"
            ) as mock_notes_cls,
        ):
            config = MagicMock()
            config.email.get_enabled_accounts.return_value = []
            config.teams.enabled = False
            config.calendar.enabled = False
            mock_config.return_value = config

            state = MagicMock()
            state.get.return_value = 0  # Return 0 for all state values
            mock_state.return_value = state

            # All services raise exceptions
            mock_email_service = MagicMock()
            mock_email_service.get_stats = AsyncMock(
                side_effect=Exception("Email error")
            )
            mock_email_cls.return_value = mock_email_service

            mock_queue_service = MagicMock()
            mock_queue_service.get_stats = AsyncMock(
                side_effect=Exception("Queue error")
            )
            mock_queue_cls.return_value = mock_queue_service

            mock_notes_service = MagicMock()
            mock_notes_service.get_review_stats = AsyncMock(
                side_effect=Exception("Notes error")
            )
            mock_notes_cls.return_value = mock_notes_service

            service = StatsService()
            overview = await service.get_overview()

            # Should return zeros instead of crashing
            assert overview.email_processed == 0
            assert overview.teams_messages == 0
            assert overview.notes_due == 0

    @pytest.mark.asyncio
    async def test_get_by_source_returns_all_sources(
        self, mock_services: dict
    ) -> None:
        """Test get_by_source returns stats for all sources"""
        with (
            patch("src.frontin.api.services.stats_service.get_config") as mock_config,
            patch(
                "src.frontin.api.services.stats_service.get_state_manager"
            ) as mock_state,
            patch(
                "src.frontin.api.services.stats_service.EmailService",
                return_value=mock_services["email"],
            ),
            patch(
                "src.frontin.api.services.stats_service.QueueService",
                return_value=mock_services["queue"],
            ),
            patch(
                "src.frontin.api.services.stats_service.TeamsService",
                return_value=mock_services["teams"],
            ),
            patch(
                "src.frontin.api.services.stats_service.NotesReviewService",
                return_value=mock_services["notes"],
            ),
        ):
            config = MagicMock()
            config.email.get_enabled_accounts.return_value = [MagicMock()]
            config.teams.enabled = True
            config.calendar.enabled = True
            mock_config.return_value = config

            state = MagicMock()
            state.get.return_value = 0
            mock_state.return_value = state

            service = StatsService()
            by_source = await service.get_by_source()

            assert by_source.email is not None
            assert by_source.email.emails_processed == 100
            assert by_source.teams is not None
            assert by_source.teams.total_chats == 20
            assert by_source.queue is not None
            assert by_source.queue.total == 5
            assert by_source.notes is not None
            assert by_source.notes.total_notes == 200


class TestStatsOverviewEndpoint:
    """Tests for /api/stats/overview endpoint"""

    def test_overview_returns_success(self, client: TestClient) -> None:
        """Test overview endpoint returns success response"""
        # Patch the service that's instantiated in the router dependency
        mock_overview = StatsOverviewResponse(
            total_processed=100,
            total_pending=10,
            sources_active=3,
            uptime_seconds=3600.0,
            email_processed=50,
            teams_messages=30,
            calendar_events_today=3,
            calendar_events_week=10,
        )

        with patch.object(
            StatsService, "get_overview", new=AsyncMock(return_value=mock_overview)
        ):
            response = client.get("/api/stats/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["total_processed"] == 100
        assert data["data"]["total_pending"] == 10
        assert data["data"]["sources_active"] == 3
        assert data["data"]["uptime_seconds"] == 3600.0
        assert data["data"]["email_processed"] == 50
        assert data["data"]["teams_messages"] == 30

    def test_overview_has_timestamp(self, client: TestClient) -> None:
        """Test overview response includes timestamp"""
        mock_overview = StatsOverviewResponse(uptime_seconds=100.0)

        with patch.object(
            StatsService, "get_overview", new=AsyncMock(return_value=mock_overview)
        ):
            response = client.get("/api/stats/overview")

        data = response.json()
        assert "timestamp" in data

    def test_overview_returns_all_fields(self, client: TestClient) -> None:
        """Test overview endpoint returns all expected fields"""
        mock_overview = StatsOverviewResponse(
            total_processed=100,
            total_pending=10,
            sources_active=3,
            uptime_seconds=3600.0,
            last_activity=datetime.now(timezone.utc),
            email_processed=50,
            email_queued=5,
            teams_messages=30,
            teams_unread=3,
            calendar_events_today=3,
            calendar_events_week=10,
            notes_due=15,
            notes_reviewed_today=5,
        )

        with patch.object(
            StatsService, "get_overview", new=AsyncMock(return_value=mock_overview)
        ):
            response = client.get("/api/stats/overview")

        data = response.json()["data"]
        assert "total_processed" in data
        assert "total_pending" in data
        assert "sources_active" in data
        assert "uptime_seconds" in data
        assert "email_processed" in data
        assert "email_queued" in data
        assert "teams_messages" in data
        assert "teams_unread" in data
        assert "calendar_events_today" in data
        assert "calendar_events_week" in data
        assert "notes_due" in data
        assert "notes_reviewed_today" in data


class TestStatsBySourceEndpoint:
    """Tests for /api/stats/by-source endpoint"""

    def test_by_source_returns_success(self, client: TestClient) -> None:
        """Test by-source endpoint returns success response"""
        mock_response = StatsBySourceResponse()

        with patch.object(
            StatsService, "get_by_source", new=AsyncMock(return_value=mock_response)
        ):
            response = client.get("/api/stats/by-source")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_by_source_includes_all_sources(self, client: TestClient) -> None:
        """Test by-source includes all source types"""
        mock_response = StatsBySourceResponse()

        with patch.object(
            StatsService, "get_by_source", new=AsyncMock(return_value=mock_response)
        ):
            response = client.get("/api/stats/by-source")

        data = response.json()
        # All source keys should be present (even if null)
        assert "email" in data["data"]
        assert "teams" in data["data"]
        assert "calendar" in data["data"]
        assert "queue" in data["data"]
        assert "notes" in data["data"]

    def test_by_source_has_timestamp(self, client: TestClient) -> None:
        """Test by-source response includes timestamp"""
        mock_response = StatsBySourceResponse()

        with patch.object(
            StatsService, "get_by_source", new=AsyncMock(return_value=mock_response)
        ):
            response = client.get("/api/stats/by-source")

        data = response.json()
        assert "timestamp" in data
