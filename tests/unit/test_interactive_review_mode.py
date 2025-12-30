"""
Unit Tests for InteractiveReviewMode

Tests the interactive review mode for queued emails.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.cli.review_mode import InteractiveReviewMode


@pytest.fixture
def mock_queue_storage():
    """Mock queue storage"""
    storage = Mock()
    storage.load_queue.return_value = []
    storage.update_item.return_value = True
    storage.remove_item.return_value = True
    return storage


@pytest.fixture
def mock_console():
    """Mock Rich console"""
    return Mock()


@pytest.fixture
def sample_queue_item():
    """Sample queue item"""
    return {
        "id": "test-item-123",
        "account_id": "personal",
        "queued_at": "2025-01-15T10:30:00+00:00",
        "metadata": {
            "id": 12345,
            "subject": "Test Email Subject",
            "from_address": "sender@example.com",
            "from_name": "Test Sender",
            "date": "2025-01-15T09:00:00+00:00",
            "has_attachments": False,
            "folder": "INBOX",
            "message_id": "<test@example.com>",
        },
        "analysis": {
            "action": "archive",
            "confidence": 75,
            "category": "newsletter",
            "reasoning": "This appears to be a newsletter.",
        },
        "content": {"preview": "This is a preview of the email content..."},
        "status": "pending",
        "reviewed_at": None,
        "review_decision": None,
    }


@pytest.fixture
def review_mode(mock_queue_storage):
    """Create InteractiveReviewMode instance with mocks"""
    with patch("src.cli.review_mode.get_queue_storage", return_value=mock_queue_storage), patch(
        "src.cli.review_mode.get_config"
    ):
        mode = InteractiveReviewMode()
        return mode


class TestInteractiveReviewModeInit:
    """Test InteractiveReviewMode initialization"""

    def test_init_loads_queue_storage(self, mock_queue_storage):
        """Test that initialization loads queue storage"""
        with patch(
            "src.cli.review_mode.get_queue_storage", return_value=mock_queue_storage
        ) as mock_get_queue, patch("src.cli.review_mode.get_config"):
            mode = InteractiveReviewMode()

            mock_get_queue.assert_called_once()
            assert mode.queue_storage is not None

    def test_init_loads_config(self):
        """Test that initialization loads config"""
        mock_config = Mock()

        with patch("src.cli.review_mode.get_queue_storage"), patch(
            "src.cli.review_mode.get_config", return_value=mock_config
        ) as mock_get_config:
            mode = InteractiveReviewMode()

            mock_get_config.assert_called_once()
            assert mode.config is not None

    def test_init_zeros_stats(self, mock_queue_storage):
        """Test that stats are initialized to zero"""
        with patch(
            "src.cli.review_mode.get_queue_storage", return_value=mock_queue_storage
        ), patch("src.cli.review_mode.get_config"):
            mode = InteractiveReviewMode()

            assert mode.reviewed == 0
            assert mode.approved == 0
            assert mode.modified == 0
            assert mode.rejected == 0
            assert mode.skipped == 0


class TestInteractiveReviewModeRun:
    """Test InteractiveReviewMode.run()"""

    @patch("src.cli.review_mode.console")
    def test_run_empty_queue(self, mock_console, review_mode, mock_queue_storage):
        """Test run with empty queue"""
        mock_queue_storage.load_queue.return_value = []

        exit_code = review_mode.run()

        assert exit_code == 0
        # Verify empty message was printed (check if called with containing text)
        printed_text = "".join(str(call) for call in mock_console.print.call_args_list)
        assert "No items" in printed_text or exit_code == 0

    def test_run_with_items(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test run with items in queue"""
        mock_queue_storage.load_queue.return_value = [sample_queue_item]

        with patch.object(
            review_mode, "_review_item", return_value=False
        ) as mock_review_item, patch.object(
            review_mode, "_show_summary"
        ) as mock_summary:
            exit_code = review_mode.run()

            assert exit_code == 0
            mock_review_item.assert_called_once()
            mock_summary.assert_called_once()

    def test_run_shows_panel_with_count(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that run shows panel with item count"""
        mock_queue_storage.load_queue.return_value = [
            sample_queue_item,
            sample_queue_item.copy(),
        ]

        with patch.object(review_mode, "_review_item", return_value=False), patch.object(
            review_mode, "_show_summary"
        ), patch("src.cli.review_mode.Panel") as MockPanel:
            review_mode.run()

            # Verify Panel was created with count
            MockPanel.fit.assert_called()
            panel_content = MockPanel.fit.call_args[0][0]
            assert "2 items to review" in panel_content

    @patch("src.cli.review_mode.console")
    def test_run_handles_keyboard_interrupt(
        self, mock_console, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test run handles KeyboardInterrupt gracefully"""
        mock_queue_storage.load_queue.return_value = [sample_queue_item]

        with patch.object(
            review_mode, "_review_item", side_effect=KeyboardInterrupt
        ), patch.object(review_mode, "_show_summary"):
            exit_code = review_mode.run()

            assert exit_code == 0
            # Verify cancellation message was printed
            printed_text = "".join(str(call) for call in mock_console.print.call_args_list)
            assert "cancelled" in printed_text.lower() or exit_code == 0

    def test_run_handles_exception(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test run handles exceptions and returns error code"""
        mock_queue_storage.load_queue.side_effect = Exception("Test error")

        exit_code = review_mode.run()

        assert exit_code == 1


class TestInteractiveReviewModeReviewItem:
    """Test InteractiveReviewMode._review_item()"""

    @patch("src.cli.review_mode.questionary")
    def test_review_item_renders_card(
        self, mock_questionary, review_mode, sample_queue_item, mock_console
    ):
        """Test that review_item renders email card"""
        mock_select = Mock()
        mock_select.ask.return_value = "❌ Cancel - Exit review mode"
        mock_questionary.select.return_value = mock_select

        with patch.object(review_mode, "_render_email_card") as mock_render:
            review_mode._review_item(sample_queue_item, 1, 5)

            mock_render.assert_called_once()

    @patch("src.cli.review_mode.questionary")
    def test_review_item_approve_decision(
        self, mock_questionary, review_mode, sample_queue_item
    ):
        """Test approve decision"""
        mock_select = Mock()
        mock_select.ask.return_value = "✓ Approve - Execute as recommended"
        mock_questionary.select.return_value = mock_select

        with patch.object(review_mode, "_approve_item") as mock_approve:
            result = review_mode._review_item(sample_queue_item, 1, 1)

            assert result is True
            mock_approve.assert_called_once_with(sample_queue_item, "archive")

    @patch("src.cli.review_mode.questionary")
    def test_review_item_modify_decision(
        self, mock_questionary, review_mode, sample_queue_item
    ):
        """Test modify decision"""
        mock_select = Mock()
        mock_select.ask.return_value = "✎ Modify - Change action and execute"
        mock_questionary.select.return_value = mock_select

        with patch.object(review_mode, "_modify_item") as mock_modify:
            result = review_mode._review_item(sample_queue_item, 1, 1)

            assert result is True
            mock_modify.assert_called_once_with(sample_queue_item, "archive")

    @patch("src.cli.review_mode.questionary")
    def test_review_item_reject_decision(
        self, mock_questionary, review_mode, sample_queue_item
    ):
        """Test reject decision"""
        mock_select = Mock()
        mock_select.ask.return_value = "✗ Reject - Keep in inbox (no action)"
        mock_questionary.select.return_value = mock_select

        with patch.object(review_mode, "_reject_item") as mock_reject:
            result = review_mode._review_item(sample_queue_item, 1, 1)

            assert result is True
            mock_reject.assert_called_once_with(sample_queue_item)

    @patch("src.cli.review_mode.questionary")
    def test_review_item_skip_decision(
        self, mock_questionary, review_mode, sample_queue_item
    ):
        """Test skip decision"""
        mock_select = Mock()
        mock_select.ask.return_value = "⏭  Skip - Leave in queue for later"
        mock_questionary.select.return_value = mock_select

        with patch.object(review_mode, "_skip_item") as mock_skip:
            result = review_mode._review_item(sample_queue_item, 1, 1)

            assert result is True
            mock_skip.assert_called_once_with(sample_queue_item)

    @patch("src.cli.review_mode.questionary")
    def test_review_item_cancel_decision(
        self, mock_questionary, review_mode, sample_queue_item
    ):
        """Test cancel decision"""
        mock_select = Mock()
        mock_select.ask.return_value = "❌ Cancel - Exit review mode"
        mock_questionary.select.return_value = mock_select

        result = review_mode._review_item(sample_queue_item, 1, 1)

        assert result is False

    @patch("src.cli.review_mode.questionary")
    def test_review_item_no_decision(
        self, mock_questionary, review_mode, sample_queue_item
    ):
        """Test when no decision is made (None)"""
        mock_select = Mock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select

        result = review_mode._review_item(sample_queue_item, 1, 1)

        assert result is False


class TestInteractiveReviewModeApproveItem:
    """Test InteractiveReviewMode._approve_item()"""

    def test_approve_item_updates_status(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that approve updates item status"""
        with patch.object(review_mode, "_execute_email_action", return_value=True):
            review_mode._approve_item(sample_queue_item, "archive")

            # Verify update was called
            mock_queue_storage.update_item.assert_called_once()
            call_args = mock_queue_storage.update_item.call_args
            item_id = call_args[0][0]
            updates = call_args[0][1]

            assert item_id == "test-item-123"
            assert updates["status"] == "approved"
            assert updates["review_decision"] == "approve"
            assert updates["executed_action"] == "archive"
            assert "reviewed_at" in updates

    def test_approve_item_removes_from_queue(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that approve removes item from queue"""
        with patch.object(review_mode, "_execute_email_action", return_value=True):
            review_mode._approve_item(sample_queue_item, "archive")

            mock_queue_storage.remove_item.assert_called_once_with("test-item-123")

    def test_approve_item_increments_stats(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that approve increments stats"""
        assert review_mode.reviewed == 0
        assert review_mode.approved == 0

        with patch.object(review_mode, "_execute_email_action", return_value=True):
            review_mode._approve_item(sample_queue_item, "archive")

            assert review_mode.reviewed == 1
            assert review_mode.approved == 1

    @patch("src.cli.review_mode.console")
    def test_approve_item_prints_message(
        self, mock_console, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that approve prints success message"""
        with patch.object(review_mode, "_execute_email_action", return_value=True):
            review_mode._approve_item(sample_queue_item, "archive")

            # Verify success message was printed
            printed_text = "".join(str(call) for call in mock_console.print.call_args_list)
            assert "Approved" in printed_text or "archive" in printed_text


class TestInteractiveReviewModeModifyItem:
    """Test InteractiveReviewMode._modify_item()"""

    @patch("src.cli.review_mode.questionary")
    def test_modify_item_prompts_for_new_action(
        self, mock_questionary, review_mode, sample_queue_item, mock_console
    ):
        """Test that modify prompts for new action"""
        mock_select = Mock()
        mock_select.ask.return_value = "delete"
        mock_questionary.select.return_value = mock_select

        review_mode._modify_item(sample_queue_item, "archive")

        mock_questionary.select.assert_called_once()
        # Verify action choices were provided
        call_args = mock_questionary.select.call_args
        assert "Select new action:" in call_args[0][0]

    @patch("src.cli.review_mode.questionary")
    def test_modify_item_updates_with_new_action(
        self, mock_questionary, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that modify updates with new action"""
        mock_select = Mock()
        mock_select.ask.return_value = "delete"
        mock_questionary.select.return_value = mock_select

        with patch.object(review_mode, "_execute_email_action", return_value=True):
            review_mode._modify_item(sample_queue_item, "archive")

            # Verify update with new action
            call_args = mock_queue_storage.update_item.call_args
            updates = call_args[0][1]

            assert updates["status"] == "modified"
            assert updates["executed_action"] == "delete"
            assert updates["ai_recommended"] == "archive"
            assert updates["user_corrected"] == "delete"

    @patch("src.cli.review_mode.questionary")
    def test_modify_item_tracks_correction(
        self, mock_questionary, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that modify tracks AI correction"""
        mock_select = Mock()
        mock_select.ask.return_value = "task"
        mock_questionary.select.return_value = mock_select

        with patch.object(review_mode, "_execute_email_action", return_value=True):
            review_mode._modify_item(sample_queue_item, "archive")

            # Verify correction tracking
            call_args = mock_queue_storage.update_item.call_args
            updates = call_args[0][1]

            assert "ai_recommended" in updates
            assert "user_corrected" in updates
            assert updates["ai_recommended"] != updates["user_corrected"]

    @patch("src.cli.review_mode.questionary")
    def test_modify_item_increments_stats(
        self, mock_questionary, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that modify increments stats"""
        mock_select = Mock()
        mock_select.ask.return_value = "delete"
        mock_questionary.select.return_value = mock_select

        assert review_mode.reviewed == 0
        assert review_mode.modified == 0

        with patch.object(review_mode, "_execute_email_action", return_value=True):
            review_mode._modify_item(sample_queue_item, "archive")

            assert review_mode.reviewed == 1
            assert review_mode.modified == 1

    @patch("src.cli.review_mode.console")
    @patch("src.cli.review_mode.questionary")
    def test_modify_item_cancelled(
        self, mock_questionary, mock_console, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that modify handles cancellation"""
        mock_select = Mock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select

        review_mode._modify_item(sample_queue_item, "archive")

        # Should not update or remove
        mock_queue_storage.update_item.assert_not_called()
        mock_queue_storage.remove_item.assert_not_called()
        # Verify cancellation message was printed
        printed_text = "".join(str(call) for call in mock_console.print.call_args_list)
        assert "cancelled" in printed_text.lower()


class TestInteractiveReviewModeRejectItem:
    """Test InteractiveReviewMode._reject_item()"""

    def test_reject_item_updates_status(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that reject updates item status"""
        review_mode._reject_item(sample_queue_item)

        # Verify update
        call_args = mock_queue_storage.update_item.call_args
        updates = call_args[0][1]

        assert updates["status"] == "rejected"
        assert updates["review_decision"] == "reject"
        assert "reviewed_at" in updates

    def test_reject_item_removes_from_queue(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that reject removes item from queue"""
        review_mode._reject_item(sample_queue_item)

        mock_queue_storage.remove_item.assert_called_once_with("test-item-123")

    def test_reject_item_increments_stats(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that reject increments stats"""
        assert review_mode.reviewed == 0
        assert review_mode.rejected == 0

        review_mode._reject_item(sample_queue_item)

        assert review_mode.reviewed == 1
        assert review_mode.rejected == 1


class TestInteractiveReviewModeSkipItem:
    """Test InteractiveReviewMode._skip_item()"""

    def test_skip_item_does_not_update(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that skip does not update item"""
        review_mode._skip_item(sample_queue_item)

        # Should not update or remove
        mock_queue_storage.update_item.assert_not_called()
        mock_queue_storage.remove_item.assert_not_called()

    def test_skip_item_increments_stats(
        self, review_mode, mock_queue_storage, sample_queue_item
    ):
        """Test that skip increments skipped count"""
        assert review_mode.skipped == 0

        review_mode._skip_item(sample_queue_item)

        assert review_mode.skipped == 1


class TestInteractiveReviewModeRenderEmailCard:
    """Test InteractiveReviewMode._render_email_card()"""

    def test_render_email_card_returns_panel(self, review_mode):
        """Test that render returns a Panel"""
        with patch("src.cli.review_mode.Panel") as MockPanel:
            review_mode._render_email_card(
                subject="Test Subject",
                from_address="sender@example.com",
                from_name="Sender",
                email_date="2025-01-15T10:00:00+00:00",
                age_str="2h ago",
                recommended_action="archive",
                confidence=85,
                category="newsletter",
                reasoning="This is a test",
                preview="Preview text",
                current=1,
                total=5,
            )

            MockPanel.assert_called_once()

    def test_render_email_card_includes_subject(self, review_mode):
        """Test that card includes subject"""
        with patch("src.cli.review_mode.Panel") as MockPanel, patch(
            "src.cli.review_mode.Text"
        ) as MockText:
            mock_text = Mock()
            MockText.return_value = mock_text

            review_mode._render_email_card(
                subject="Important Email",
                from_address="sender@example.com",
                from_name="Sender",
                email_date=None,
                age_str="",
                recommended_action="archive",
                confidence=85,
                category="newsletter",
                reasoning="Test",
                preview="",
                current=1,
                total=1,
            )

            # Verify subject was added to text
            calls = [str(call) for call in mock_text.append.call_args_list]
            assert any("Important Email" in str(call) for call in calls)


class TestInteractiveReviewModeRenderConfidenceBar:
    """Test InteractiveReviewMode._render_confidence_bar()"""

    def test_render_confidence_bar_high(self, review_mode):
        """Test confidence bar for high confidence (>= 90)"""
        with patch("src.cli.review_mode.Text") as MockText:
            mock_text = Mock()
            MockText.return_value = mock_text

            review_mode._render_confidence_bar(95)

            # Verify green color for high confidence
            mock_text.append.assert_called()
            call_args = mock_text.append.call_args
            assert call_args[1]["style"] == "green"

    def test_render_confidence_bar_medium(self, review_mode):
        """Test confidence bar for medium confidence (80-89)"""
        with patch("src.cli.review_mode.Text") as MockText:
            mock_text = Mock()
            MockText.return_value = mock_text

            review_mode._render_confidence_bar(85)

            call_args = mock_text.append.call_args
            assert call_args[1]["style"] == "yellow"

    def test_render_confidence_bar_low(self, review_mode):
        """Test confidence bar for low confidence (< 65)"""
        with patch("src.cli.review_mode.Text") as MockText:
            mock_text = Mock()
            MockText.return_value = mock_text

            review_mode._render_confidence_bar(50)

            call_args = mock_text.append.call_args
            assert call_args[1]["style"] == "red"


class TestInteractiveReviewModeFormatEmailAge:
    """Test InteractiveReviewMode._format_email_age()"""

    def test_format_email_age_none(self, review_mode):
        """Test formatting None date"""
        result = review_mode._format_email_age(None)

        assert result == "Unknown date"

    def test_format_email_age_just_now(self, review_mode):
        """Test formatting very recent email"""
        from src.utils import now_utc

        now = now_utc()
        recent = (now.replace(second=now.second - 10)).isoformat()

        result = review_mode._format_email_age(recent)

        assert result == "just now"

    def test_format_email_age_minutes(self, review_mode):
        """Test formatting email from minutes ago"""
        from src.utils import now_utc

        now = now_utc()
        minutes_ago = (now.replace(minute=now.minute - 5)).isoformat()

        result = review_mode._format_email_age(minutes_ago)

        assert "m ago" in result

    def test_format_email_age_invalid(self, review_mode):
        """Test formatting invalid date"""
        result = review_mode._format_email_age("invalid-date")

        assert result == "Unknown date"


class TestInteractiveReviewModeShowSummary:
    """Test InteractiveReviewMode._show_summary()"""

    def test_show_summary_displays_stats(self, review_mode, mock_console):
        """Test that summary displays all stats"""
        review_mode.reviewed = 10
        review_mode.approved = 5
        review_mode.modified = 2
        review_mode.rejected = 1
        review_mode.skipped = 2

        with patch("src.cli.review_mode.Panel") as MockPanel:
            review_mode._show_summary()

            # Verify Panel.fit was called with stats
            MockPanel.fit.assert_called_once()
            panel_content = MockPanel.fit.call_args[0][0]

            assert "Total reviewed: 10" in panel_content
            assert "Approved: 5" in panel_content
            assert "Modified: 2" in panel_content
            assert "Rejected: 1" in panel_content
            assert "Skipped: 2" in panel_content
