"""
Unit Tests for InteractiveMenu

Tests the interactive menu system with questionary.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from src.jeeves.menu import InteractiveMenu, run_interactive_menu
from src.core.config_manager import EmailAccountConfig, EmailConfig


@pytest.fixture
def mock_console():
    """Mock Rich console"""
    return Mock()


@pytest.fixture
def mock_config():
    """Mock configuration with multiple accounts"""
    account1 = EmailAccountConfig(
        account_id="personal",
        account_name="Personal (iCloud)",
        imap_host="imap.mail.me.com",
        imap_port=993,
        imap_username="user@me.com",
        imap_password="password1",
        enabled=True,
    )

    account2 = EmailAccountConfig(
        account_id="work",
        account_name="Work Email",
        imap_host="imap.gmail.com",
        imap_port=993,
        imap_username="user@company.com",
        imap_password="password2",
        enabled=True,
    )

    config = Mock()
    config.email = Mock()
    config.email.get_enabled_accounts.return_value = [account1, account2]
    config.email.get_account.side_effect = lambda aid: (
        account1 if aid == "personal" else account2
    )

    return config


@pytest.fixture
def mock_queue_storage():
    """Mock queue storage"""
    storage = Mock()
    storage.get_stats.return_value = {
        "total": 5,
        "by_status": {"pending": 5},
        "by_account": {"personal": 3, "work": 2},
    }
    storage.get_queue_size.return_value = 5
    storage.load_queue.return_value = []
    return storage


@pytest.fixture
def interactive_menu(mock_config, mock_queue_storage):
    """Create InteractiveMenu instance with mocks"""
    with patch("src.jeeves.menu.get_config", return_value=mock_config), patch(
        "src.jeeves.menu.get_queue_storage", return_value=mock_queue_storage
    ):
        menu = InteractiveMenu()
        return menu


class TestInteractiveMenuInit:
    """Test InteractiveMenu initialization"""

    def test_init_loads_config(self, mock_config, mock_queue_storage):
        """Test that initialization loads config"""
        with patch("src.jeeves.menu.get_config", return_value=mock_config) as mock_get_config, patch(
            "src.jeeves.menu.get_queue_storage", return_value=mock_queue_storage
        ):
            menu = InteractiveMenu()

            mock_get_config.assert_called_once()
            assert menu.config is not None

    def test_init_loads_queue_storage(self, mock_config, mock_queue_storage):
        """Test that initialization loads queue storage"""
        with patch("src.jeeves.menu.get_config", return_value=mock_config), patch(
            "src.jeeves.menu.get_queue_storage", return_value=mock_queue_storage
        ) as mock_get_queue:
            menu = InteractiveMenu()

            mock_get_queue.assert_called_once()
            assert menu.queue_storage is not None

    def test_init_sets_running_true(self, mock_config, mock_queue_storage):
        """Test that running flag is set to True"""
        with patch("src.jeeves.menu.get_config", return_value=mock_config), patch(
            "src.jeeves.menu.get_queue_storage", return_value=mock_queue_storage
        ):
            menu = InteractiveMenu()

            assert menu.running is True


class TestInteractiveMenuRun:
    """Test InteractiveMenu.run()"""

    def test_run_shows_welcome(self, interactive_menu):
        """Test that run shows welcome message"""
        with patch.object(
            interactive_menu, "_show_welcome"
        ) as mock_welcome, patch.object(
            interactive_menu, "_show_main_menu", side_effect=KeyboardInterrupt
        ), patch.object(
            interactive_menu, "_show_goodbye"
        ):
            interactive_menu.run()

            mock_welcome.assert_called_once()

    def test_run_shows_goodbye_on_exit(self, interactive_menu):
        """Test that run shows goodbye when exiting"""
        with patch.object(interactive_menu, "_show_welcome"), patch.object(
            interactive_menu, "_show_main_menu", side_effect=KeyboardInterrupt
        ), patch.object(interactive_menu, "_show_goodbye") as mock_goodbye:
            interactive_menu.run()

            mock_goodbye.assert_called_once()

    def test_run_returns_zero_on_success(self, interactive_menu):
        """Test that run returns 0 on success"""
        with patch.object(interactive_menu, "_show_welcome"), patch.object(
            interactive_menu, "_show_main_menu", side_effect=KeyboardInterrupt
        ), patch.object(interactive_menu, "_show_goodbye"):
            exit_code = interactive_menu.run()

            assert exit_code == 0

    def test_run_handles_keyboard_interrupt(self, interactive_menu, mock_console):
        """Test that run handles KeyboardInterrupt gracefully"""
        with patch.object(interactive_menu, "_show_welcome"), patch.object(
            interactive_menu, "_show_main_menu", side_effect=KeyboardInterrupt
        ), patch.object(interactive_menu, "_show_goodbye"), patch(
            "src.jeeves.menu.console", mock_console
        ):
            exit_code = interactive_menu.run()

            assert exit_code == 0
            # Should print cancellation message
            mock_console.print.assert_any_call("\n[yellow]⚠ Menu cancelled[/yellow]")

    def test_run_handles_exception(self, interactive_menu):
        """Test that run handles exceptions and returns error code"""
        with patch.object(interactive_menu, "_show_welcome"), patch.object(
            interactive_menu, "_show_main_menu", side_effect=Exception("Test error")
        ), patch("src.jeeves.menu.console"):
            exit_code = interactive_menu.run()

            assert exit_code == 1


class TestInteractiveMenuMainMenu:
    """Test InteractiveMenu._show_main_menu()"""

    @patch("src.jeeves.menu.questionary")
    def test_main_menu_shows_all_options(self, mock_questionary, interactive_menu):
        """Test that main menu shows all options"""
        mock_select = Mock()
        mock_select.ask.return_value = "🚪 Exit"
        mock_questionary.select.return_value = mock_select

        interactive_menu._show_main_menu()

        # Verify select was called with all options
        call_args = mock_questionary.select.call_args
        # Get choices from keyword args
        choices = call_args.kwargs.get("choices", call_args[0][1] if len(call_args[0]) > 1 else [])

        assert any("Process Emails" in choice for choice in choices)
        assert any("Review Queue" in choice for choice in choices)
        assert any("Statistics" in choice for choice in choices)
        assert any("Settings" in choice for choice in choices)
        assert any("System Health" in choice for choice in choices)
        assert any("Exit" in choice for choice in choices)

    @patch("src.jeeves.menu.questionary")
    def test_main_menu_shows_queue_count(
        self, mock_questionary, interactive_menu, mock_queue_storage
    ):
        """Test that main menu shows queue count"""
        mock_select = Mock()
        mock_select.ask.return_value = "🚪 Exit"
        mock_questionary.select.return_value = mock_select

        mock_queue_storage.get_stats.return_value = {"total": 10}

        interactive_menu._show_main_menu()

        # Verify queue count is displayed
        call_args = mock_questionary.select.call_args
        # Get choices from keyword args
        choices = call_args.kwargs.get("choices", call_args[0][1] if len(call_args[0]) > 1 else [])

        assert any("10 items" in choice for choice in choices)

    @patch("src.jeeves.menu.questionary")
    def test_main_menu_exit_selection(self, mock_questionary, interactive_menu):
        """Test selecting Exit from main menu"""
        mock_select = Mock()
        mock_select.ask.return_value = "🚪 Exit"
        mock_questionary.select.return_value = mock_select

        interactive_menu._show_main_menu()

        assert interactive_menu.running is False

    @patch("src.jeeves.menu.questionary")
    def test_main_menu_process_emails(self, mock_questionary, interactive_menu):
        """Test selecting Process Emails"""
        mock_select = Mock()
        mock_select.ask.return_value = "📧 Process Emails"
        mock_questionary.select.return_value = mock_select

        with patch.object(
            interactive_menu, "_process_emails_submenu"
        ) as mock_process:
            interactive_menu._show_main_menu()
            interactive_menu.running = False  # Stop loop

            mock_process.assert_called_once()


class TestInteractiveMenuSelectAccounts:
    """Test InteractiveMenu._select_accounts()"""

    def test_select_accounts_single_account(self, mock_config):
        """Test auto-selection when only one account"""
        with patch("src.jeeves.menu.get_config", return_value=mock_config), patch(
            "src.jeeves.menu.get_queue_storage"
        ):
            menu = InteractiveMenu()

            # Mock only one enabled account
            single_account = mock_config.email.get_enabled_accounts()[0]
            menu.config.email.get_enabled_accounts.return_value = [single_account]

            with patch("src.jeeves.menu.console"):
                accounts = menu._select_accounts()

                assert len(accounts) == 1
                assert accounts[0].account_id == "personal"

    @patch("src.jeeves.menu.questionary")
    def test_select_accounts_multiple_accounts(
        self, mock_questionary, interactive_menu
    ):
        """Test checkbox selection for multiple accounts"""
        mock_checkbox = Mock()
        mock_checkbox.ask.return_value = ["personal", "work"]
        mock_questionary.checkbox.return_value = mock_checkbox

        accounts = interactive_menu._select_accounts()

        assert len(accounts) == 2
        assert accounts[0].account_id == "personal"
        assert accounts[1].account_id == "work"

    @patch("src.jeeves.menu.questionary")
    def test_select_accounts_all_option(self, mock_questionary, interactive_menu):
        """Test selecting 'All Accounts' option"""
        mock_checkbox = Mock()
        mock_checkbox.ask.return_value = ["ALL"]
        mock_questionary.checkbox.return_value = mock_checkbox

        accounts = interactive_menu._select_accounts()

        # Should return all enabled accounts
        assert len(accounts) == 2

    @patch("src.jeeves.menu.questionary")
    def test_select_accounts_none_selected(self, mock_questionary, interactive_menu):
        """Test when no accounts selected"""
        mock_checkbox = Mock()
        mock_checkbox.ask.return_value = []
        mock_questionary.checkbox.return_value = mock_checkbox

        accounts = interactive_menu._select_accounts()

        assert accounts == []


class TestInteractiveMenuSelectMode:
    """Test InteractiveMenu._select_mode()"""

    @patch("src.jeeves.menu.questionary")
    def test_select_mode_auto(self, mock_questionary, interactive_menu):
        """Test selecting Auto mode"""
        mock_select = Mock()
        mock_select.ask.return_value = {
            "name": "Auto",
            "auto_execute": True,
            "confidence_threshold": 90,
        }
        mock_questionary.select.return_value = mock_select

        mode = interactive_menu._select_mode()

        assert mode["name"] == "Auto"
        assert mode["auto_execute"] is True
        assert mode["confidence_threshold"] == 90

    @patch("src.jeeves.menu.questionary")
    def test_select_mode_manual(self, mock_questionary, interactive_menu):
        """Test selecting Manual mode"""
        mock_select = Mock()
        mock_select.ask.return_value = {
            "name": "Manual",
            "auto_execute": False,
            "confidence_threshold": 100,
        }
        mock_questionary.select.return_value = mock_select

        mode = interactive_menu._select_mode()

        assert mode["name"] == "Manual"
        assert mode["auto_execute"] is False
        assert mode["confidence_threshold"] == 100

    @patch("src.jeeves.menu.questionary")
    def test_select_mode_preview(self, mock_questionary, interactive_menu):
        """Test selecting Preview mode"""
        mock_select = Mock()
        mock_select.ask.return_value = {
            "name": "Preview",
            "auto_execute": False,
            "confidence_threshold": 100,
            "preview_only": True,
        }
        mock_questionary.select.return_value = mock_select

        mode = interactive_menu._select_mode()

        assert mode["name"] == "Preview"
        assert mode.get("preview_only") is True


class TestInteractiveMenuSelectLimit:
    """Test InteractiveMenu._select_limit()"""

    @patch("src.jeeves.menu.questionary")
    def test_select_limit_10(self, mock_questionary, interactive_menu):
        """Test selecting 10 emails limit"""
        mock_select = Mock()
        mock_select.ask.return_value = 10
        mock_questionary.select.return_value = mock_select

        limit = interactive_menu._select_limit()

        assert limit == 10

    @patch("src.jeeves.menu.questionary")
    def test_select_limit_unlimited(self, mock_questionary, interactive_menu):
        """Test selecting unlimited (None)"""
        mock_select = Mock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select

        limit = interactive_menu._select_limit()

        assert limit is None


class TestInteractiveMenuProcessEmails:
    """Test InteractiveMenu._process_emails_submenu()"""

    @patch("src.jeeves.menu.questionary")
    @patch("src.jeeves.menu.console")
    def test_process_emails_cancelled_no_accounts(
        self, mock_console, mock_questionary, interactive_menu
    ):
        """Test cancellation when no accounts selected"""
        with patch.object(
            interactive_menu, "_select_accounts", return_value=[]
        ):
            interactive_menu._process_emails_submenu()

            # Should print warning
            mock_console.print.assert_any_call("[yellow]⚠ No accounts selected[/yellow]")

    @patch("src.jeeves.menu.questionary")
    @patch("src.jeeves.menu.console")
    def test_process_emails_cancelled_no_mode(
        self, mock_console, mock_questionary, interactive_menu, mock_config
    ):
        """Test cancellation when mode not selected"""
        account = mock_config.email.get_enabled_accounts()[0]

        with patch.object(
            interactive_menu, "_select_accounts", return_value=[account]
        ), patch.object(interactive_menu, "_select_mode", return_value=None):
            interactive_menu._process_emails_submenu()

            # Should return without error

    @patch("src.jeeves.menu.questionary")
    @patch("src.jeeves.menu.console")
    def test_process_emails_confirmation_rejected(
        self, mock_console, mock_questionary, interactive_menu, mock_config
    ):
        """Test when user rejects confirmation"""
        account = mock_config.email.get_enabled_accounts()[0]
        mode = {"name": "Auto", "auto_execute": True, "confidence_threshold": 90}

        mock_confirm = Mock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        with patch.object(
            interactive_menu, "_select_accounts", return_value=[account]
        ), patch.object(
            interactive_menu, "_select_mode", return_value=mode
        ), patch.object(
            interactive_menu, "_select_limit", return_value=10
        ):
            interactive_menu._process_emails_submenu()

            # Should print cancellation
            mock_console.print.assert_any_call("[yellow]⚠ Processing cancelled[/yellow]")

    @patch("src.jeeves.menu.questionary")
    @patch("src.jeeves.menu.console")
    def test_process_emails_executes_processing(
        self, mock_console, mock_questionary, interactive_menu, mock_config
    ):
        """Test successful processing execution"""
        account = mock_config.email.get_enabled_accounts()[0]
        mode = {"name": "Auto", "auto_execute": True, "confidence_threshold": 90}

        mock_confirm = Mock()
        mock_confirm.ask.return_value = True
        mock_questionary.confirm.return_value = mock_confirm

        with patch.object(
            interactive_menu, "_select_accounts", return_value=[account]
        ), patch.object(
            interactive_menu, "_select_mode", return_value=mode
        ), patch.object(
            interactive_menu, "_select_limit", return_value=10
        ), patch.object(
            interactive_menu, "_execute_processing"
        ) as mock_execute:
            interactive_menu._process_emails_submenu()

            mock_execute.assert_called_once_with([account], mode, 10)


class TestInteractiveMenuReviewQueue:
    """Test InteractiveMenu._review_queue_submenu()"""

    @patch("src.jeeves.menu.questionary")
    @patch("src.jeeves.menu.console")
    def test_review_queue_empty(
        self, mock_console, mock_questionary, interactive_menu, mock_queue_storage
    ):
        """Test review with empty queue"""
        mock_queue_storage.get_queue_size.return_value = 0

        mock_press = Mock()
        mock_press.ask.return_value = None
        mock_questionary.press_any_key_to_continue.return_value = mock_press

        interactive_menu._review_queue_submenu()

        # Should show empty message
        mock_console.print.assert_any_call(
            "[dim]Queue is empty - no emails pending review[/dim]"
        )

    @patch("src.jeeves.menu.questionary")
    @patch("src.jeeves.menu.console")
    def test_review_queue_confirmed(
        self, mock_console, mock_questionary, interactive_menu, mock_queue_storage
    ):
        """Test starting review when confirmed"""
        mock_queue_storage.get_queue_size.return_value = 5

        mock_confirm = Mock()
        mock_confirm.ask.return_value = True
        mock_questionary.confirm.return_value = mock_confirm

        # InteractiveReviewMode is imported inside the function, so patch at import location
        with patch("src.jeeves.review_mode.InteractiveReviewMode") as MockReviewMode:
            mock_review_instance = Mock()
            mock_review_instance.run.return_value = 0
            MockReviewMode.return_value = mock_review_instance

            interactive_menu._review_queue_submenu()

            MockReviewMode.assert_called_once()
            mock_review_instance.run.assert_called_once()


class TestInteractiveMenuStatistics:
    """Test InteractiveMenu._view_statistics()"""

    @patch("src.jeeves.menu.questionary")
    @patch("src.jeeves.menu.console")
    def test_view_statistics_displays_queue_stats(
        self, mock_console, mock_questionary, interactive_menu, mock_queue_storage
    ):
        """Test that statistics are displayed"""
        mock_queue_storage.get_stats.return_value = {
            "total": 10,
            "by_status": {"pending": 7, "approved": 3},
            "by_account": {"personal": 6, "work": 4},
        }

        mock_press = Mock()
        mock_press.ask.return_value = None
        mock_questionary.press_any_key_to_continue.return_value = mock_press

        interactive_menu._view_statistics()

        # Verify stats were printed
        mock_console.print.assert_any_call("[bold]Queue Statistics:[/bold]")


class TestRunInteractiveMenu:
    """Test run_interactive_menu() function"""

    @patch("src.jeeves.menu.InteractiveMenu")
    def test_run_interactive_menu(self, MockMenu):
        """Test run_interactive_menu creates and runs menu"""
        mock_instance = Mock()
        mock_instance.run.return_value = 0
        MockMenu.return_value = mock_instance

        exit_code = run_interactive_menu()

        MockMenu.assert_called_once()
        mock_instance.run.assert_called_once()
        assert exit_code == 0
