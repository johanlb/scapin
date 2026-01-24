"""
Unit Tests for SC-20: AutoFetchManager

Tests the AutoFetchManager singleton that handles automatic fetching
of emails, Teams messages, and calendar events.

Architecture decisions (2026-01-24):
- Trigger: Event-driven after approve/reject (debounced)
- Startup: Fetch immédiat si queue < startup_threshold (20)
- Runtime: Fetch si queue < low_threshold (5)
- Cooldowns: 2min email/teams, 5min calendar
- Default: Activé par défaut

See: docs/plans/workflow-cleanup-autofetch.md
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.frontin.api.services.autofetch_manager import (
    AutoFetchManager,
    FetchSource,
    get_autofetch_manager,
)


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    config = MagicMock()
    config.autofetch.enabled = True
    config.autofetch.low_threshold = 5
    config.autofetch.startup_threshold = 20
    config.autofetch.fetch_limit = 20
    config.autofetch.email_cooldown_minutes = 2
    config.autofetch.teams_cooldown_minutes = 2
    config.autofetch.calendar_cooldown_minutes = 5
    return config


@pytest.fixture
def autofetch_manager():
    """Create a fresh AutoFetchManager for testing."""
    # Reset singleton for clean tests
    AutoFetchManager._instance = None
    return AutoFetchManager()


class TestAutoFetchManagerInit:
    """Tests for AutoFetchManager initialization."""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """AutoFetchManager should be a singleton."""
        AutoFetchManager._instance = None
        manager1 = await AutoFetchManager.get_instance()
        manager2 = await AutoFetchManager.get_instance()
        assert manager1 is manager2

    def test_last_fetch_initialized_empty(self, autofetch_manager):
        """last_fetch dict should be empty on init."""
        assert autofetch_manager._last_fetch == {}

    def test_fetch_in_progress_initialized(self, autofetch_manager):
        """fetch_in_progress should be False for all sources."""
        for source in FetchSource:
            assert autofetch_manager._fetch_in_progress[source] is False


class TestAutoFetchManagerCooldown:
    """Tests for cooldown tracking."""

    def test_is_source_eligible_no_previous_fetch(self, autofetch_manager):
        """Source should be eligible if never fetched before."""
        assert autofetch_manager.is_source_eligible(FetchSource.EMAIL) is True

    def test_is_source_eligible_fetch_in_progress(self, autofetch_manager):
        """Source should NOT be eligible if fetch is in progress."""
        autofetch_manager._fetch_in_progress[FetchSource.EMAIL] = True
        assert autofetch_manager.is_source_eligible(FetchSource.EMAIL) is False

    @patch("src.frontin.api.services.autofetch_manager.get_config")
    def test_is_source_eligible_cooldown_not_elapsed(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """Source should NOT be eligible if cooldown not elapsed."""
        mock_get_config.return_value = mock_config
        autofetch_manager._last_fetch[FetchSource.EMAIL] = datetime.now()
        assert autofetch_manager.is_source_eligible(FetchSource.EMAIL) is False

    @patch("src.frontin.api.services.autofetch_manager.get_config")
    def test_is_source_eligible_cooldown_elapsed(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """Source should be eligible if cooldown has elapsed."""
        mock_get_config.return_value = mock_config
        autofetch_manager._last_fetch[FetchSource.EMAIL] = datetime.now() - timedelta(
            minutes=5
        )
        assert autofetch_manager.is_source_eligible(FetchSource.EMAIL) is True


class TestAutoFetchManagerQueueCheck:
    """Tests for queue threshold checks."""

    @pytest.mark.asyncio
    @patch("src.frontin.api.services.autofetch_manager.get_config")
    async def test_check_disabled_returns_disabled(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """Should return disabled status when autofetch is disabled."""
        mock_config.autofetch.enabled = False
        mock_get_config.return_value = mock_config

        result = await autofetch_manager.check_and_fetch_if_needed(is_startup=False)

        assert result["status"] == "disabled"
        assert result["fetched"] == 0

    @pytest.mark.asyncio
    @patch("src.frontin.api.services.autofetch_manager.get_config")
    async def test_check_sufficient_queue(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """Should return sufficient when queue is above threshold."""
        mock_get_config.return_value = mock_config

        mock_queue_service = MagicMock()
        mock_queue_service._storage.get_stats.return_value = {
            "by_state": {"awaiting_review": 10, "analyzing": 0}
        }

        result = await autofetch_manager.check_and_fetch_if_needed(
            is_startup=False, queue_service=mock_queue_service
        )

        assert result["status"] == "sufficient"
        assert result["fetched"] == 0
        assert result["active_count"] == 10

    @pytest.mark.asyncio
    @patch("src.frontin.api.services.autofetch_manager.get_config")
    async def test_check_uses_startup_threshold_at_startup(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """Should use startup_threshold when is_startup=True."""
        mock_get_config.return_value = mock_config

        mock_queue_service = MagicMock()
        mock_queue_service._storage.get_stats.return_value = {
            "by_state": {"awaiting_review": 15, "analyzing": 0}
        }

        # 15 items: < startup_threshold (20), but >= low_threshold (5)
        result = await autofetch_manager.check_and_fetch_if_needed(
            is_startup=True, queue_service=mock_queue_service
        )

        # Should try to fetch because 15 < 20 (startup threshold)
        assert result["threshold"] == 20


class TestAutoFetchManagerEventDriven:
    """Tests for event-driven fetch triggering."""

    @pytest.mark.asyncio
    @patch("src.frontin.api.services.autofetch_manager.get_config")
    async def test_on_item_processed_does_nothing_when_disabled(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """on_item_processed should do nothing when disabled."""
        mock_config.autofetch.enabled = False
        mock_get_config.return_value = mock_config

        # Should not raise and should not schedule task
        await autofetch_manager.on_item_processed()

        assert autofetch_manager._debounce_task is None

    @pytest.mark.asyncio
    @patch("src.frontin.api.services.autofetch_manager.get_config")
    async def test_on_item_processed_schedules_debounced_check(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """on_item_processed should schedule a debounced check."""
        mock_get_config.return_value = mock_config

        await autofetch_manager.on_item_processed()

        assert autofetch_manager._debounce_task is not None
        assert not autofetch_manager._debounce_task.done()

        # Cancel the task to cleanup
        autofetch_manager._debounce_task.cancel()

    @pytest.mark.asyncio
    @patch("src.frontin.api.services.autofetch_manager.get_config")
    async def test_on_item_processed_cancels_previous_task(
        self, mock_get_config, autofetch_manager, mock_config
    ):
        """on_item_processed should cancel previous debounce task."""
        mock_get_config.return_value = mock_config

        # First call
        await autofetch_manager.on_item_processed()
        first_task = autofetch_manager._debounce_task

        # Second call should cancel the first
        await autofetch_manager.on_item_processed()
        second_task = autofetch_manager._debounce_task

        # The new task should be different from the first
        assert second_task is not first_task
        # The first task should be cancelling (cancel() was called)
        assert first_task.cancelling() or first_task.cancelled() or first_task.done()

        # Cleanup
        second_task.cancel()


class TestAutoFetchManagerHelper:
    """Tests for helper function."""

    @pytest.mark.asyncio
    async def test_get_autofetch_manager_returns_singleton(self):
        """get_autofetch_manager should return the singleton."""
        AutoFetchManager._instance = None
        manager1 = await get_autofetch_manager()
        manager2 = await get_autofetch_manager()
        assert manager1 is manager2
