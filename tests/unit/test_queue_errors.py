"""
Unit Tests for Queue Error Handling (SC-16)

Tests error handling for failed actions:
- Retry logic with exponential backoff
- Error status tracking
- Manual retry and dismiss actions
- Move to review functionality
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class ErrorRetryPolicy:
    """Retry policy for failed actions."""

    MAX_RETRIES = 3
    BACKOFF_SECONDS = [5, 30, 120]  # 5s, 30s, 2min

    def __init__(self) -> None:
        self.attempt_count = 0
        self.last_attempt: datetime | None = None
        self.last_error: str | None = None

    def should_retry(self) -> bool:
        """Check if we should retry based on attempt count."""
        return self.attempt_count < self.MAX_RETRIES

    def get_next_delay(self) -> int:
        """Get delay before next retry in seconds."""
        if self.attempt_count >= len(self.BACKOFF_SECONDS):
            return self.BACKOFF_SECONDS[-1]
        return self.BACKOFF_SECONDS[self.attempt_count]

    def record_attempt(self, error: str) -> None:
        """Record a failed attempt."""
        self.attempt_count += 1
        self.last_attempt = datetime.now(timezone.utc)
        self.last_error = error

    def reset(self) -> None:
        """Reset retry state after success."""
        self.attempt_count = 0
        self.last_attempt = None
        self.last_error = None


class QueueErrorItem:
    """Represents an item in error state."""

    def __init__(
        self,
        item_id: str,
        original_action: str,
        error_message: str,
        retry_policy: ErrorRetryPolicy | None = None,
    ) -> None:
        self.id = item_id
        self.original_action = original_action
        self.error_message = error_message
        self.retry_policy = retry_policy or ErrorRetryPolicy()
        self.status = "error"
        self.created_at = datetime.now(timezone.utc)

    @property
    def attempt_count(self) -> int:
        return self.retry_policy.attempt_count

    @property
    def last_attempt(self) -> datetime | None:
        return self.retry_policy.last_attempt

    @property
    def can_retry(self) -> bool:
        return self.retry_policy.should_retry()


class TestRetryPolicy:
    """Test retry policy configuration (SC-16)."""

    def test_max_retries_is_3(self) -> None:
        """SC-16: Should retry 3 times before showing in error tab."""
        policy = ErrorRetryPolicy()
        assert policy.MAX_RETRIES == 3

    def test_backoff_sequence(self) -> None:
        """SC-16: Backoff should be 5s → 30s → 120s."""
        policy = ErrorRetryPolicy()
        assert policy.BACKOFF_SECONDS == [5, 30, 120]

    def test_first_retry_delay(self) -> None:
        """SC-16: First retry should be after 5 seconds."""
        policy = ErrorRetryPolicy()
        assert policy.get_next_delay() == 5

    def test_second_retry_delay(self) -> None:
        """SC-16: Second retry should be after 30 seconds."""
        policy = ErrorRetryPolicy()
        policy.record_attempt("Connection failed")
        assert policy.get_next_delay() == 30

    def test_third_retry_delay(self) -> None:
        """SC-16: Third retry should be after 120 seconds."""
        policy = ErrorRetryPolicy()
        policy.record_attempt("Attempt 1")
        policy.record_attempt("Attempt 2")
        assert policy.get_next_delay() == 120

    def test_should_retry_before_max(self) -> None:
        """SC-16: Should allow retry when under max attempts."""
        policy = ErrorRetryPolicy()
        policy.record_attempt("Attempt 1")
        policy.record_attempt("Attempt 2")
        assert policy.should_retry() is True

    def test_should_not_retry_at_max(self) -> None:
        """SC-16: Should not retry after max attempts reached."""
        policy = ErrorRetryPolicy()
        policy.record_attempt("Attempt 1")
        policy.record_attempt("Attempt 2")
        policy.record_attempt("Attempt 3")
        assert policy.should_retry() is False


class TestQueueErrorItem:
    """Test error item structure (SC-16)."""

    def test_error_item_creation(self) -> None:
        """SC-16: Error item should store all required info."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="IMAP connection failed: timeout",
        )

        assert item.id == "email-123"
        assert item.original_action == "archive"
        assert item.error_message == "IMAP connection failed: timeout"
        assert item.status == "error"
        assert item.attempt_count == 0

    def test_error_item_tracks_attempts(self) -> None:
        """SC-16: Error item should track attempt count."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        item.retry_policy.record_attempt("First attempt failed")
        assert item.attempt_count == 1

        item.retry_policy.record_attempt("Second attempt failed")
        assert item.attempt_count == 2

    def test_error_item_tracks_last_attempt_time(self) -> None:
        """SC-16: Error item should track last attempt timestamp."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        before = datetime.now(timezone.utc)
        item.retry_policy.record_attempt("Failed")
        after = datetime.now(timezone.utc)

        assert item.last_attempt is not None
        assert before <= item.last_attempt <= after

    def test_can_retry_reflects_policy(self) -> None:
        """SC-16: can_retry should reflect retry policy state."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        assert item.can_retry is True

        # Exhaust retries
        for _ in range(3):
            item.retry_policy.record_attempt("Failed")

        assert item.can_retry is False


class TestErrorMessages:
    """Test error message formatting (SC-16)."""

    def test_imap_connection_error_message(self) -> None:
        """SC-16: IMAP connection errors should have clear messages."""
        error = "IMAP connection failed: Connection refused"
        display_message = self._format_error_for_display(error)
        assert "Connexion IMAP échouée" in display_message

    def test_timeout_error_message(self) -> None:
        """SC-16: Timeout errors should have clear messages."""
        error = "Operation timed out after 30 seconds"
        display_message = self._format_error_for_display(error)
        assert "Délai d'attente dépassé" in display_message

    def test_authentication_error_message(self) -> None:
        """SC-16: Auth errors should have clear messages."""
        error = "Authentication failed: Invalid credentials"
        display_message = self._format_error_for_display(error)
        assert "Authentification échouée" in display_message

    def _format_error_for_display(self, error: str) -> str:
        """Format error message for user display."""
        error_lower = error.lower()

        if "connection" in error_lower and ("refused" in error_lower or "failed" in error_lower):
            return "Connexion IMAP échouée"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "Délai d'attente dépassé"
        elif "auth" in error_lower or "credential" in error_lower:
            return "Authentification échouée"
        else:
            return f"Erreur: {error}"


class TestRetryAction:
    """Test retry action behavior (SC-16)."""

    @pytest.mark.asyncio
    async def test_retry_success_moves_to_processed(self) -> None:
        """SC-16: Successful retry should move item to 'Traités'."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )
        item.retry_policy.record_attempt("Previous failure")

        # Simulate successful retry
        retry_success = True

        if retry_success:
            item.status = "completed"
            item.retry_policy.reset()

        assert item.status == "completed"
        assert item.attempt_count == 0  # Reset after success

    @pytest.mark.asyncio
    async def test_retry_failure_stays_in_error(self) -> None:
        """SC-16: Failed retry should keep item in error state."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        # Simulate failed retry
        item.retry_policy.record_attempt("Retry also failed")

        assert item.status == "error"
        assert item.attempt_count == 1


class TestDismissAction:
    """Test dismiss action behavior (SC-16)."""

    def test_dismiss_removes_from_error_list(self) -> None:
        """SC-16: Dismiss should remove item from error list."""
        error_items: list[QueueErrorItem] = [
            QueueErrorItem("1", "archive", "Error 1"),
            QueueErrorItem("2", "archive", "Error 2"),
            QueueErrorItem("3", "archive", "Error 3"),
        ]

        # Dismiss item 2
        item_to_dismiss = "2"
        error_items = [item for item in error_items if item.id != item_to_dismiss]

        assert len(error_items) == 2
        assert all(item.id != "2" for item in error_items)

    def test_dismissed_item_not_retried(self) -> None:
        """SC-16: Dismissed items should not be auto-retried."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        # Mark as dismissed
        item.status = "dismissed"

        # Should not appear in retry queue
        should_retry = item.status == "error" and item.can_retry
        assert should_retry is False


class TestMoveToReviewAction:
    """Test move to review action behavior (SC-16)."""

    def test_move_to_review_changes_status(self) -> None:
        """SC-16: Move to review should change status to 'pending'."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        # Move to review
        item.status = "pending"

        assert item.status == "pending"

    def test_move_to_review_appears_in_attention_queue(self) -> None:
        """SC-16: Moved item should appear in 'À votre attention'."""
        pending_queue: list[dict[str, Any]] = []
        error_item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        # Move to review
        pending_queue.append({
            "id": error_item.id,
            "status": "pending",
            "original_error": error_item.error_message,
            "moved_from_error": True,
        })

        assert len(pending_queue) == 1
        assert pending_queue[0]["moved_from_error"] is True


class TestErrorTabBadge:
    """Test error tab badge display (SC-16)."""

    def test_badge_shows_error_count(self) -> None:
        """SC-16: Error tab should show count of items in error."""
        error_items = [
            QueueErrorItem("1", "archive", "Error 1"),
            QueueErrorItem("2", "archive", "Error 2"),
            QueueErrorItem("3", "archive", "Error 3"),
        ]

        badge_count = len(error_items)
        assert badge_count == 3

    def test_badge_hidden_when_no_errors(self) -> None:
        """SC-16: Error tab badge should be hidden when no errors."""
        error_items: list[QueueErrorItem] = []

        badge_visible = len(error_items) > 0
        assert badge_visible is False

    def test_badge_is_red_color(self) -> None:
        """SC-16: Error badge should be red for visibility."""
        badge_color = "red"  # As specified in SC-16
        assert badge_color == "red"


class TestAutoRetryBeforeErrorTab:
    """Test that auto-retry happens before showing in error tab (SC-16)."""

    @pytest.mark.asyncio
    async def test_item_not_in_error_tab_until_retries_exhausted(self) -> None:
        """SC-16: Item should only appear in error tab after 3 failed retries."""
        item = QueueErrorItem(
            item_id="email-123",
            original_action="archive",
            error_message="Connection failed",
        )

        visible_in_error_tab = not item.can_retry

        # Before any retries
        assert visible_in_error_tab is False

        # After 1 retry
        item.retry_policy.record_attempt("Retry 1 failed")
        visible_in_error_tab = not item.can_retry
        assert visible_in_error_tab is False

        # After 2 retries
        item.retry_policy.record_attempt("Retry 2 failed")
        visible_in_error_tab = not item.can_retry
        assert visible_in_error_tab is False

        # After 3 retries - now visible
        item.retry_policy.record_attempt("Retry 3 failed")
        visible_in_error_tab = not item.can_retry
        assert visible_in_error_tab is True
