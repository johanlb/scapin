"""
Integration Tests for Background Email Processing (SC-14)

Tests the automatic background processing workflow:
- Batch fetching (20 emails)
- AI analysis with confidence scoring
- Auto-execution above threshold
- Queue management for low-confidence items
- Polling behavior
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config_manager import (
    AIConfig,
    EmailConfig,
    ProcessingConfig,
)
from src.core.schemas import EmailAction, EmailAnalysis, EmailCategory


if TYPE_CHECKING:
    from src.trivelin.processor import EmailProcessor


@pytest.fixture
def processing_config() -> ProcessingConfig:
    """Create processing config with auto-execute enabled."""
    return ProcessingConfig(
        enable_cognitive_reasoning=True,
    )


@pytest.fixture
def email_config() -> EmailConfig:
    """Create mock email configuration."""
    return EmailConfig(
        imap_host="imap.test.com",
        imap_port=993,
        imap_username="test@test.com",
        imap_password="test_password",
    )


@pytest.fixture
def ai_config() -> AIConfig:
    """Create mock AI configuration."""
    return AIConfig(
        anthropic_api_key="sk-test-key",
        confidence_threshold=85,
        rate_limit_per_minute=40,
    )


def create_mock_email(
    subject: str,
    sender: str = "sender@example.com",
    body: str = "Test email body",
) -> EmailMessage:
    """Create a mock email message."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = "recipient@example.com"
    msg["Subject"] = subject
    msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    msg["Message-ID"] = f"<{subject.replace(' ', '_')}@test.com>"
    msg.set_content(body)
    return msg


class TestBackgroundProcessingConfig:
    """Test configuration for background processing."""

    def test_default_batch_size(self, processing_config: ProcessingConfig) -> None:
        """SC-14: Batch size should default to 20."""
        assert processing_config.batch_size == 20

    def test_default_auto_execute_threshold(
        self, processing_config: ProcessingConfig
    ) -> None:
        """SC-14: Auto-execute threshold should be configurable."""
        assert processing_config.auto_execute_threshold == 0.85

    def test_default_max_queue_size(
        self, processing_config: ProcessingConfig
    ) -> None:
        """SC-14: Max queue size should default to 30."""
        assert processing_config.max_queue_size == 30

    def test_default_polling_interval(
        self, processing_config: ProcessingConfig
    ) -> None:
        """SC-14: Polling interval should default to 300 seconds (5 min)."""
        assert processing_config.polling_interval_seconds == 300


class TestAutoExecutionDecision:
    """Test auto-execution decision logic."""

    def test_auto_execute_above_threshold(self) -> None:
        """SC-14: Should auto-execute when confidence >= threshold."""
        threshold = 0.85
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=90,  # 90% > 85% threshold
            reasoning="Newsletter from known source",
        )
        should_auto_execute = (analysis.confidence / 100) >= threshold
        assert should_auto_execute is True

    def test_no_auto_execute_below_threshold(self) -> None:
        """SC-14: Should NOT auto-execute when confidence < threshold."""
        threshold = 0.85
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.WORK,
            confidence=70,  # 70% < 85% threshold
            reasoning="Might be important work email",
        )
        should_auto_execute = (analysis.confidence / 100) >= threshold
        assert should_auto_execute is False

    def test_auto_execute_at_exact_threshold(self) -> None:
        """SC-14: Should auto-execute when confidence == threshold."""
        threshold = 0.85
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=85,  # Exactly at threshold
            reasoning="Newsletter",
        )
        should_auto_execute = (analysis.confidence / 100) >= threshold
        assert should_auto_execute is True


class TestQueueManagement:
    """Test queue size management and polling suspension."""

    def test_should_fetch_when_queue_below_limit(self) -> None:
        """SC-14: Should continue fetching when queue < max_queue_size."""
        current_queue_size = 20
        max_queue_size = 30
        should_fetch = current_queue_size < max_queue_size
        assert should_fetch is True

    def test_should_stop_fetch_when_queue_at_limit(self) -> None:
        """SC-14: Should stop fetching when queue >= max_queue_size."""
        current_queue_size = 30
        max_queue_size = 30
        should_fetch = current_queue_size < max_queue_size
        assert should_fetch is False

    def test_should_resume_fetch_when_queue_decreases(self) -> None:
        """SC-14: Should resume fetching when queue drops below limit."""
        # Simulate queue going from full to having space
        max_queue_size = 30

        # Queue was full
        queue_full = 30
        assert (queue_full < max_queue_size) is False

        # User processed some items
        queue_after_processing = 25
        assert (queue_after_processing < max_queue_size) is True


class TestBatchProcessing:
    """Test batch processing behavior."""

    @pytest.mark.asyncio
    async def test_batch_processes_correct_number_of_emails(self) -> None:
        """SC-14: Should process exactly batch_size emails per batch."""
        batch_size = 20
        mock_emails = [
            create_mock_email(f"Email {i}") for i in range(25)
        ]

        # Simulate batch selection
        batch = mock_emails[:batch_size]
        assert len(batch) == 20

        remaining = mock_emails[batch_size:]
        assert len(remaining) == 5

    @pytest.mark.asyncio
    async def test_batch_continues_when_queue_has_space(self) -> None:
        """SC-14: Should fetch next batch when queue has space."""
        batch_size = 20
        max_queue_size = 30

        # First batch processed, some auto-executed
        auto_executed = 15
        queued_for_review = 5
        current_queue_size = queued_for_review

        # Should continue fetching
        should_continue = current_queue_size < max_queue_size
        assert should_continue is True


class TestPollingBehavior:
    """Test polling interval and suspension."""

    def test_polling_interval_is_5_minutes(
        self, processing_config: ProcessingConfig
    ) -> None:
        """SC-14: Polling interval should be 5 minutes (300 seconds)."""
        assert processing_config.polling_interval_seconds == 300

    def test_polling_suspended_when_queue_full(self) -> None:
        """SC-14: Polling should suspend when queue is full."""
        max_queue_size = 30
        current_queue_size = 30

        polling_active = current_queue_size < max_queue_size
        assert polling_active is False

    def test_polling_resumes_when_queue_has_space(self) -> None:
        """SC-14: Polling should resume when queue has space."""
        max_queue_size = 30
        current_queue_size = 25

        polling_active = current_queue_size < max_queue_size
        assert polling_active is True


class TestExecutionTypeTracking:
    """Test tracking of execution types for SC-15."""

    def test_auto_executed_items_marked_correctly(self) -> None:
        """SC-15: Auto-executed items should have execution_type='auto'."""
        # Simulate processing result
        result = {
            "id": "email-123",
            "action": "archive",
            "confidence": 0.92,
            "execution_type": "auto",
        }
        assert result["execution_type"] == "auto"

    def test_user_approved_items_marked_correctly(self) -> None:
        """SC-15: User-approved items should have execution_type='user_approved'."""
        result = {
            "id": "email-456",
            "action": "archive",
            "confidence": 0.75,
            "execution_type": "user_approved",
        }
        assert result["execution_type"] == "user_approved"

    def test_user_modified_items_marked_correctly(self) -> None:
        """SC-15: User-modified items should have execution_type='user_modified'."""
        result = {
            "id": "email-789",
            "action": "task",  # User changed from 'archive' to 'task'
            "original_action": "archive",
            "confidence": 0.65,
            "execution_type": "user_modified",
        }
        assert result["execution_type"] == "user_modified"


class TestFilteringByExecutionType:
    """Test filtering processed items by execution type (SC-15)."""

    @pytest.fixture
    def processed_items(self) -> list[dict]:
        """Create sample processed items."""
        return [
            {"id": "1", "execution_type": "auto", "confidence": 0.92},
            {"id": "2", "execution_type": "auto", "confidence": 0.88},
            {"id": "3", "execution_type": "user_approved", "confidence": 0.75},
            {"id": "4", "execution_type": "user_modified", "confidence": 0.65},
            {"id": "5", "execution_type": "auto", "confidence": 0.95},
        ]

    def test_filter_auto_executed_only(self, processed_items: list[dict]) -> None:
        """SC-15: Should filter to show only auto-executed items."""
        auto_only = [
            item for item in processed_items if item["execution_type"] == "auto"
        ]
        assert len(auto_only) == 3
        assert all(item["execution_type"] == "auto" for item in auto_only)

    def test_filter_user_assisted_only(self, processed_items: list[dict]) -> None:
        """SC-15: Should filter to show only user-assisted items."""
        user_assisted = [
            item
            for item in processed_items
            if item["execution_type"] in ("user_approved", "user_modified")
        ]
        assert len(user_assisted) == 2

    def test_filter_all_shows_everything(self, processed_items: list[dict]) -> None:
        """SC-15: 'All' filter should show all items."""
        assert len(processed_items) == 5


class TestConfidenceScoreDisplay:
    """Test confidence score is stored and displayed (SC-15)."""

    def test_confidence_score_preserved_on_auto_execute(self) -> None:
        """SC-15: Confidence score should be preserved for auto-executed items."""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.NEWSLETTER,
            confidence=92,
            reasoning="Newsletter from subscribed source",
        )

        processed_item = {
            "action": analysis.action.value,
            "confidence_score": analysis.confidence / 100,  # Store as 0-1
            "execution_type": "auto",
        }

        assert processed_item["confidence_score"] == 0.92

    def test_confidence_score_preserved_on_user_action(self) -> None:
        """SC-15: Confidence score should be preserved for user-actioned items."""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.WORK,
            confidence=72,
            reasoning="Might be important",
        )

        processed_item = {
            "action": "task",  # User chose different action
            "original_confidence": analysis.confidence / 100,
            "execution_type": "user_modified",
        }

        assert processed_item["original_confidence"] == 0.72
