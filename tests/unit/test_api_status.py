"""
Tests for Status API Endpoint

Tests GET /api/status endpoint and StatusService.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.state_manager import ProcessingState
from src.frontin.api.app import create_app
from src.frontin.api.deps import get_cached_config
from src.frontin.api.models.responses import (
    ComponentStatus,
    SessionStatsResponse,
    SystemStatusResponse,
)
from src.frontin.api.services.status_service import StatusService


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

    # Integration configs
    config.teams.enabled = True
    config.calendar.enabled = True
    config.briefing.enabled = True
    config.ai.model = "claude-3-5-haiku-20241022"

    return config


@pytest.fixture
def mock_state_manager() -> MagicMock:
    """Create mock state manager"""
    state = MagicMock()
    state.processing_state = ProcessingState.IDLE
    state.stats.emails_processed = 10
    state.stats.emails_skipped = 2
    state.stats.archived = 5
    state.stats.deleted = 3
    state.stats.referenced = 2
    state.stats.tasks_created = 1
    state.stats.confidence_avg = 85.5
    state.stats.duration_minutes = 15
    state.get.return_value = None
    return state


@pytest.fixture
def client(mock_config: MagicMock) -> TestClient:
    """Create test client with mocked config"""
    app = create_app()
    app.dependency_overrides[get_cached_config] = lambda: mock_config
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestStatusResponseModels:
    """Tests for Status Pydantic models"""

    def test_component_status_defaults(self) -> None:
        """Test ComponentStatus has correct structure"""
        component = ComponentStatus(
            name="email",
            state="active",
        )

        assert component.name == "email"
        assert component.state == "active"
        assert component.last_activity is None
        assert component.details is None

    def test_component_status_with_all_fields(self) -> None:
        """Test ComponentStatus with all fields"""
        now = datetime.now(timezone.utc)
        component = ComponentStatus(
            name="teams",
            state="idle",
            last_activity=now,
            details="2 unread messages",
        )

        assert component.name == "teams"
        assert component.state == "idle"
        assert component.last_activity == now
        assert component.details == "2 unread messages"

    def test_session_stats_response_defaults(self) -> None:
        """Test SessionStatsResponse defaults"""
        stats = SessionStatsResponse()

        assert stats.emails_processed == 0
        assert stats.emails_skipped == 0
        assert stats.actions_taken == 0
        assert stats.tasks_created == 0
        assert stats.average_confidence == 0.0
        assert stats.session_duration_minutes == 0

    def test_session_stats_response_with_values(self) -> None:
        """Test SessionStatsResponse with values"""
        stats = SessionStatsResponse(
            emails_processed=25,
            emails_skipped=5,
            actions_taken=20,
            tasks_created=3,
            average_confidence=88.5,
            session_duration_minutes=30,
        )

        assert stats.emails_processed == 25
        assert stats.actions_taken == 20
        assert stats.average_confidence == 88.5

    def test_system_status_response_minimal(self) -> None:
        """Test SystemStatusResponse with minimal required fields"""
        status = SystemStatusResponse(
            state="idle",
            uptime_seconds=100.0,
        )

        assert status.state == "idle"
        assert status.current_task is None
        assert status.active_connections == 0
        assert status.components == []
        assert status.uptime_seconds == 100.0
        assert status.last_activity is None

    def test_system_status_response_full(self) -> None:
        """Test SystemStatusResponse with all fields"""
        now = datetime.now(timezone.utc)
        status = SystemStatusResponse(
            state="running",
            current_task="Processing email: Test Subject...",
            active_connections=2,
            components=[
                ComponentStatus(name="email", state="active"),
                ComponentStatus(name="teams", state="idle"),
            ],
            session_stats=SessionStatsResponse(emails_processed=10),
            uptime_seconds=3600.0,
            last_activity=now,
        )

        assert status.state == "running"
        assert status.current_task == "Processing email: Test Subject..."
        assert status.active_connections == 2
        assert len(status.components) == 2
        assert status.session_stats.emails_processed == 10
        assert status.last_activity == now


class TestStatusService:
    """Tests for StatusService"""

    @pytest.mark.asyncio
    async def test_get_status_idle(
        self, mock_config: MagicMock, mock_state_manager: MagicMock
    ) -> None:
        """Test get_status returns idle state"""
        with (
            patch(
                "src.frontin.api.services.status_service.get_config",
                return_value=mock_config,
            ),
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 0

            service = StatusService()
            status = await service.get_status()

            assert status.state == "idle"
            assert status.current_task is None
            assert status.active_connections == 0
            assert status.uptime_seconds > 0

    @pytest.mark.asyncio
    async def test_get_status_running_with_email(
        self, mock_config: MagicMock, mock_state_manager: MagicMock
    ) -> None:
        """Test get_status when processing email"""
        mock_state_manager.processing_state = ProcessingState.RUNNING
        mock_state_manager.get.side_effect = lambda key, default=None: {
            "current_email_subject": "Important: Meeting Tomorrow",
        }.get(key, default)

        with (
            patch(
                "src.frontin.api.services.status_service.get_config",
                return_value=mock_config,
            ),
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 1

            service = StatusService()
            status = await service.get_status()

            assert status.state == "running"
            assert status.current_task is not None
            assert "Important: Meeting Tomorrow" in status.current_task
            assert status.active_connections == 1

    @pytest.mark.asyncio
    async def test_get_status_components(
        self, mock_config: MagicMock, mock_state_manager: MagicMock
    ) -> None:
        """Test components are properly built"""
        with (
            patch(
                "src.frontin.api.services.status_service.get_config",
                return_value=mock_config,
            ),
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 0

            service = StatusService()
            status = await service.get_status()

            # Should have components for email, teams, calendar, notes, queue
            component_names = [c.name for c in status.components]
            assert "email" in component_names
            assert "teams" in component_names
            assert "calendar" in component_names
            assert "notes" in component_names
            assert "queue" in component_names

    @pytest.mark.asyncio
    async def test_get_status_session_stats(
        self, mock_config: MagicMock, mock_state_manager: MagicMock
    ) -> None:
        """Test session stats are populated"""
        with (
            patch(
                "src.frontin.api.services.status_service.get_config",
                return_value=mock_config,
            ),
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 0

            service = StatusService()
            status = await service.get_status()

            assert status.session_stats.emails_processed == 10
            assert status.session_stats.emails_skipped == 2
            # actions_taken = archived (5) + deleted (3) + referenced (2)
            assert status.session_stats.actions_taken == 10
            assert status.session_stats.tasks_created == 1
            assert status.session_stats.average_confidence == 85.5
            assert status.session_stats.session_duration_minutes == 15

    @pytest.mark.asyncio
    async def test_get_status_disabled_integrations(
        self, mock_state_manager: MagicMock
    ) -> None:
        """Test status with disabled integrations"""
        config = MagicMock()
        config.email.get_enabled_accounts.return_value = []
        config.teams.enabled = False
        config.calendar.enabled = False

        with (
            patch(
                "src.frontin.api.services.status_service.get_config",
                return_value=config,
            ),
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 0

            service = StatusService()
            status = await service.get_status()

            # Find components and check states
            for component in status.components:
                if component.name == "email" or component.name == "teams" or component.name == "calendar":
                    assert component.state == "disabled"


class TestStatusEndpoint:
    """Tests for GET /api/status endpoint"""

    def test_status_endpoint_success(
        self, client: TestClient, mock_state_manager: MagicMock
    ) -> None:
        """Test GET /api/status returns success"""
        with (
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 0

            response = client.get("/api/status")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "timestamp" in data

    def test_status_endpoint_data_structure(
        self, client: TestClient, mock_state_manager: MagicMock
    ) -> None:
        """Test GET /api/status returns correct data structure"""
        with (
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 2

            response = client.get("/api/status")

            assert response.status_code == 200
            data = response.json()["data"]

            # Check required fields
            assert "state" in data
            assert "current_task" in data
            assert "active_connections" in data
            assert "components" in data
            assert "session_stats" in data
            assert "uptime_seconds" in data
            assert "last_activity" in data

            # Check values
            assert data["state"] == "idle"
            assert data["active_connections"] == 2
            assert isinstance(data["components"], list)
            assert isinstance(data["session_stats"], dict)
            assert data["uptime_seconds"] > 0

    def test_status_endpoint_components(
        self, client: TestClient, mock_state_manager: MagicMock
    ) -> None:
        """Test GET /api/status returns component statuses"""
        with (
            patch(
                "src.frontin.api.services.status_service.get_state_manager",
                return_value=mock_state_manager,
            ),
            patch(
                "src.frontin.api.services.status_service.get_connection_manager"
            ) as mock_ws,
        ):
            mock_ws.return_value.active_connection_count = 0

            response = client.get("/api/status")

            assert response.status_code == 200
            components = response.json()["data"]["components"]

            # Should have 5 components
            assert len(components) == 5

            # Check component structure
            for component in components:
                assert "name" in component
                assert "state" in component
                assert component["state"] in ["active", "idle", "disabled", "error"]
