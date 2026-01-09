"""
Unit Tests for Valets Stats Service

Tests the aggregation of real statistics from valet workers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.jeeves.api.services.valets_stats_service import (
    ValetsStatsService,
    get_valets_stats_service,
)


class TestValetsStatsService:
    """Test ValetsStatsService class."""

    def test_init(self) -> None:
        """Test service initialization."""
        service = ValetsStatsService()
        assert service._last_refresh is not None

    def test_empty_stats(self) -> None:
        """Test empty stats structure."""
        service = ValetsStatsService()
        empty = service._empty_stats()

        assert empty["status"] == "idle"
        assert empty["current_task"] is None
        assert empty["tasks_today"] == 0
        assert empty["errors_today"] == 0
        assert empty["details"] == {}

    def test_get_trivelin_stats_with_state_manager(self) -> None:
        """Test getting Trivelin stats from state manager."""
        service = ValetsStatsService()

        with patch("src.core.state_manager.get_state_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.processing_state.value = "running"
            mock_manager.stats.emails_processed = 10
            mock_manager.stats.emails_failed = 2
            mock_manager.stats.emails_skipped = 1
            mock_manager.stats.archived = 5
            mock_manager.stats.deleted = 3
            mock_manager.stats.tasks_created = 2
            mock_manager.stats.notes_enriched = 1
            mock_manager.stats.confidence_avg = 0.87
            mock_manager.stats.duration_minutes = 15
            mock.return_value = mock_manager

            stats = service.get_trivelin_stats()

            assert stats["status"] == "running"
            assert stats["tasks_today"] == 10
            assert stats["errors_today"] == 2
            assert stats["details"]["emails_processed"] == 10
            assert stats["details"]["confidence_avg"] == 0.87

    def test_get_trivelin_stats_error_handling(self) -> None:
        """Test Trivelin stats with error returns empty stats."""
        service = ValetsStatsService()

        with patch(
            "src.core.state_manager.get_state_manager",
            side_effect=Exception("Test error"),
        ):
            stats = service.get_trivelin_stats()

            # Should return empty stats on error
            assert stats["status"] == "idle"
            assert stats["tasks_today"] == 0

    def test_get_sancho_stats_with_router(self) -> None:
        """Test getting Sancho stats from AI router."""
        service = ValetsStatsService()

        with patch("src.sancho.router.get_ai_router") as mock:
            mock_router = MagicMock()
            mock_router.get_ai_metrics.return_value = {
                "total_requests": 50,
                "total_tokens": 10000,
                "total_cost_usd": 0.25,
                "avg_duration_ms": 150,
                "p95_duration_ms": 500,
                "errors_by_type": {"rate_limit": 2, "timeout": 1},
            }
            mock.return_value = mock_router

            stats = service.get_sancho_stats()

            assert stats["tasks_today"] == 50
            assert stats["errors_today"] == 3  # 2 + 1
            assert stats["details"]["total_tokens"] == 10000

    def test_get_sganarelle_stats_handles_missing_singleton(self) -> None:
        """Test Sganarelle stats returns empty stats when singleton not available."""
        service = ValetsStatsService()

        # The get_learning_engine singleton doesn't exist yet
        # Service should gracefully return empty stats
        stats = service.get_sganarelle_stats()

        assert stats["status"] == "idle"
        # Will be 0 because there's no learning engine singleton yet
        assert "tasks_today" in stats

    def test_get_jeeves_stats_running(self) -> None:
        """Test getting Jeeves stats (always running even without rate limiter)."""
        service = ValetsStatsService()

        # Jeeves should always be running if the API is responding
        stats = service.get_jeeves_stats()

        assert stats["status"] == "running"
        assert stats["current_task"] == "Serving API requests"

    def test_get_all_stats(self) -> None:
        """Test getting stats for all valets."""
        service = ValetsStatsService()

        # Mock all the methods
        with patch.object(service, "get_trivelin_stats", return_value={"tasks_today": 10}), \
             patch.object(service, "get_sancho_stats", return_value={"tasks_today": 50}), \
             patch.object(service, "get_passepartout_stats", return_value={"tasks_today": 20}), \
             patch.object(service, "get_planchet_stats", return_value={"tasks_today": 5}), \
             patch.object(service, "get_figaro_stats", return_value={"tasks_today": 15}), \
             patch.object(service, "get_sganarelle_stats", return_value={"tasks_today": 25}), \
             patch.object(service, "get_jeeves_stats", return_value={"tasks_today": 100, "status": "running"}):
            all_stats = service.get_all_stats()

            assert len(all_stats) == 7
            assert all_stats["trivelin"]["tasks_today"] == 10
            assert all_stats["sancho"]["tasks_today"] == 50
            assert all_stats["jeeves"]["status"] == "running"

    def test_get_aggregate_metrics(self) -> None:
        """Test aggregate metrics calculation."""
        service = ValetsStatsService()

        with patch.object(service, "get_all_stats") as mock:
            mock.return_value = {
                "trivelin": {
                    "status": "idle",
                    "tasks_today": 10,
                    "errors_today": 2,
                    "details": {"confidence_avg": 85},
                },
                "sancho": {
                    "status": "idle",
                    "tasks_today": 50,
                    "errors_today": 3,
                    "details": {},
                },
                "jeeves": {
                    "status": "running",
                    "tasks_today": 100,
                    "errors_today": 0,
                    "details": {},
                },
                "sganarelle": {
                    "status": "idle",
                    "tasks_today": 25,
                    "errors_today": 0,
                    "details": {"avg_confidence": 0.82},
                },
                "passepartout": {"status": "idle", "tasks_today": 0, "errors_today": 0, "details": {}},
                "planchet": {"status": "idle", "tasks_today": 0, "errors_today": 0, "details": {}},
                "figaro": {"status": "idle", "tasks_today": 0, "errors_today": 0, "details": {}},
            }

            metrics = service.get_aggregate_metrics()

            assert metrics["total_tasks_today"] == 185  # 10+50+100+25
            assert metrics["total_errors_today"] == 5  # 2+3
            assert metrics["active_workers"] == 1  # Only jeeves is running
            assert metrics["timestamp"] is not None


class TestValetsStatsServiceSingleton:
    """Test singleton pattern."""

    def test_get_valets_stats_service_returns_singleton(self) -> None:
        """Test that get_valets_stats_service returns same instance."""
        service1 = get_valets_stats_service()
        service2 = get_valets_stats_service()

        assert service1 is service2


class TestValetsRouterIntegration:
    """Test the router endpoints with mocked service."""

    def _create_mock_stats_service(self) -> MagicMock:
        """Create mock stats service with all methods."""
        mock = MagicMock()
        mock._empty_stats.return_value = {
            "status": "idle",
            "current_task": None,
            "tasks_today": 0,
            "errors_today": 0,
            "details": {},
        }

        # Define return values for each valet
        base_stats = {
            "status": "idle",
            "current_task": None,
            "tasks_today": 10,
            "errors_today": 1,
            "details": {"avg_duration_ms": 150, "p95_duration_ms": 500},
        }

        mock.get_trivelin_stats.return_value = base_stats.copy()
        mock.get_sancho_stats.return_value = {**base_stats, "details": {"total_tokens": 1000, "total_requests": 10}}
        mock.get_passepartout_stats.return_value = base_stats.copy()
        mock.get_planchet_stats.return_value = base_stats.copy()
        mock.get_figaro_stats.return_value = base_stats.copy()
        mock.get_sganarelle_stats.return_value = base_stats.copy()
        mock.get_jeeves_stats.return_value = {**base_stats, "status": "running", "current_task": "Serving API requests"}

        mock.get_aggregate_metrics.return_value = {
            "total_tasks_today": 50,
            "total_errors_today": 2,
            "active_workers": 1,
            "avg_confidence": 0.85,
            "timestamp": datetime.now(timezone.utc),
        }
        mock.get_all_stats.return_value = {
            "trivelin": base_stats.copy(),
            "sancho": base_stats.copy(),
            "passepartout": base_stats.copy(),
            "planchet": base_stats.copy(),
            "figaro": base_stats.copy(),
            "sganarelle": base_stats.copy(),
            "jeeves": {**base_stats, "status": "running"},
        }
        return mock

    @pytest.mark.asyncio
    async def test_get_valets_dashboard_uses_real_stats(self) -> None:
        """Test dashboard endpoint uses real stats."""
        mock_service = self._create_mock_stats_service()
        with patch(
            "src.jeeves.api.routers.valets.get_valets_stats_service",
            return_value=mock_service,
        ):
            from src.jeeves.api.routers.valets import get_valets_dashboard

            response = await get_valets_dashboard(None)

            assert response.success is True
            assert response.data.total_tasks_today == 50
            assert response.data.avg_confidence == 0.85

    @pytest.mark.asyncio
    async def test_get_valets_metrics_uses_real_stats(self) -> None:
        """Test metrics endpoint uses real stats."""
        mock_service = self._create_mock_stats_service()
        with patch(
            "src.jeeves.api.routers.valets.get_valets_stats_service",
            return_value=mock_service,
        ):
            from src.jeeves.api.routers.valets import get_valets_metrics

            response = await get_valets_metrics(period="today", _user=None)

            assert response.success is True
            assert response.data.period == "today"
