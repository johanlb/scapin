"""
Tests for OmniFocusClient — AppleScript Integration

Ce module teste le client OmniFocus pour la création de tâches.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.integrations.apple.omnifocus import (
    OmniFocusClient,
    OmniFocusError,
    OmniFocusNotAvailableError,
    OmniFocusTask,
    OmniFocusTaskCreationError,
    create_omnifocus_client,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create a basic OmniFocus client"""
    return OmniFocusClient(default_project="Inbox", timeout=30)


@pytest.fixture
def client_with_project():
    """Create client with custom default project"""
    return OmniFocusClient(default_project="Scapin Tasks")


# ============================================================================
# Initialization Tests
# ============================================================================


class TestOmniFocusClientInit:
    """Tests for OmniFocusClient initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        client = OmniFocusClient()

        assert client.default_project == "Inbox"
        assert client.timeout == 30
        assert client._is_available is None

    def test_init_custom_values(self):
        """Test initialization with custom values"""
        client = OmniFocusClient(
            default_project="Work Tasks",
            timeout=60,
        )

        assert client.default_project == "Work Tasks"
        assert client.timeout == 60


# ============================================================================
# OmniFocusTask Dataclass Tests
# ============================================================================


class TestOmniFocusTask:
    """Tests for OmniFocusTask dataclass"""

    def test_task_creation(self):
        """Test basic task creation"""
        task = OmniFocusTask(
            task_id="task_123",
            title="Test Task",
        )

        assert task.task_id == "task_123"
        assert task.title == "Test Task"
        assert task.project is None
        assert task.due_date is None
        assert task.note is None
        assert task.created_at is not None

    def test_task_with_all_fields(self):
        """Test task with all fields"""
        due = datetime(2026, 1, 15)
        created = datetime(2026, 1, 10)

        task = OmniFocusTask(
            task_id="task_456",
            title="Full Task",
            project="Project Alpha",
            due_date=due,
            note="Task notes here",
            created_at=created,
        )

        assert task.project == "Project Alpha"
        assert task.due_date == due
        assert task.note == "Task notes here"
        assert task.created_at == created


# ============================================================================
# Availability Tests
# ============================================================================


class TestOmniFocusAvailability:
    """Tests for is_available method"""

    @pytest.mark.asyncio
    async def test_is_available_true(self, client):
        """Test when OmniFocus is available"""
        with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock:
            mock.return_value = "true"

            result = await client.is_available()

            assert result is True
            assert client._is_available is True

    @pytest.mark.asyncio
    async def test_is_available_false(self, client):
        """Test when OmniFocus is not available"""
        with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock:
            mock.return_value = "false"

            result = await client.is_available()

            assert result is False
            assert client._is_available is False

    @pytest.mark.asyncio
    async def test_is_available_cached(self, client):
        """Test that availability is cached"""
        client._is_available = True

        # Should not call AppleScript
        result = await client.is_available()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_available_error(self, client):
        """Test when AppleScript fails"""
        with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("AppleScript error")

            result = await client.is_available()

            assert result is False
            assert client._is_available is False


# ============================================================================
# Task Creation Tests
# ============================================================================


class TestCreateTask:
    """Tests for create_task method"""

    @pytest.mark.asyncio
    async def test_create_task_basic(self, client):
        """Test basic task creation"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = True
            with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock_script:
                mock_script.return_value = "task_abc123"

                task = await client.create_task(title="Test Task")

                assert task.task_id == "task_abc123"
                assert task.title == "Test Task"
                assert task.project == "Inbox"

    @pytest.mark.asyncio
    async def test_create_task_with_all_options(self, client):
        """Test task creation with all options"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = True
            with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock_script:
                mock_script.return_value = "task_full"

                task = await client.create_task(
                    title="Full Task",
                    project="Work",
                    due_date="2026-01-15",
                    note="Task notes",
                    defer_date="2026-01-10",
                    tags=["urgent", "scapin"],
                )

                assert task.task_id == "task_full"
                assert task.title == "Full Task"
                assert task.project == "Work"
                assert task.due_date == datetime(2026, 1, 15)
                assert task.note == "Task notes"

    @pytest.mark.asyncio
    async def test_create_task_not_available(self, client):
        """Test task creation when OmniFocus unavailable"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock:
            mock.return_value = False

            with pytest.raises(OmniFocusNotAvailableError):
                await client.create_task(title="Test Task")

    @pytest.mark.asyncio
    async def test_create_task_script_error(self, client):
        """Test task creation when AppleScript fails"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = True
            with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock_script:
                mock_script.side_effect = OmniFocusError("Script failed")

                with pytest.raises(OmniFocusTaskCreationError):
                    await client.create_task(title="Test Task")

    @pytest.mark.asyncio
    async def test_create_task_invalid_due_date(self, client):
        """Test task creation with invalid due date format"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = True
            with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock_script:
                mock_script.return_value = "task_123"

                task = await client.create_task(
                    title="Task",
                    due_date="invalid-date",
                )

                # Should still create task, just without parsed due_date
                assert task.task_id == "task_123"
                assert task.due_date is None


# ============================================================================
# Get Projects/Tags Tests
# ============================================================================


class TestGetProjectsAndTags:
    """Tests for get_projects and get_tags methods"""

    @pytest.mark.asyncio
    async def test_get_projects(self, client):
        """Test getting projects list"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = True
            with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock_script:
                mock_script.return_value = "Inbox, Work, Personal"

                projects = await client.get_projects()

                assert projects == ["Inbox", "Work", "Personal"]

    @pytest.mark.asyncio
    async def test_get_projects_empty(self, client):
        """Test getting empty projects list"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = True
            with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock_script:
                mock_script.return_value = ""

                projects = await client.get_projects()

                assert projects == []

    @pytest.mark.asyncio
    async def test_get_projects_not_available(self, client):
        """Test getting projects when OmniFocus unavailable"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock:
            mock.return_value = False

            projects = await client.get_projects()

            assert projects == []

    @pytest.mark.asyncio
    async def test_get_tags(self, client):
        """Test getting tags list"""
        with patch.object(client, "is_available", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = True
            with patch.object(client, "_run_applescript", new_callable=AsyncMock) as mock_script:
                mock_script.return_value = "urgent, scapin, home"

                tags = await client.get_tags()

                assert tags == ["urgent", "scapin", "home"]


# ============================================================================
# AppleScript Building Tests
# ============================================================================


class TestBuildAppleScript:
    """Tests for _build_create_task_script"""

    def test_build_basic_script(self, client):
        """Test building basic task script"""
        script = client._build_create_task_script(
            title="Test Task",
            project="Inbox",
            due_date=None,
            note=None,
            defer_date=None,
            tags=[],
        )

        assert 'name:"Test Task"' in script
        assert "OmniFocus" in script
        assert "make new" in script

    def test_build_script_with_due_date(self, client):
        """Test building script with due date"""
        script = client._build_create_task_script(
            title="Task",
            project="Work",
            due_date="2026-01-15",
            note=None,
            defer_date=None,
            tags=[],
        )

        assert "set year of dueDate to 2026" in script
        assert "set month of dueDate to 1" in script
        assert "set day of dueDate to 15" in script
        assert "due date:dueDate" in script

    def test_build_script_with_note(self, client):
        """Test building script with note"""
        script = client._build_create_task_script(
            title="Task",
            project="Work",
            due_date=None,
            note="Important note here",
            defer_date=None,
            tags=[],
        )

        assert 'note:"Important note here"' in script

    def test_build_script_with_tags(self, client):
        """Test building script with tags"""
        script = client._build_create_task_script(
            title="Task",
            project="Work",
            due_date=None,
            note=None,
            defer_date=None,
            tags=["urgent", "scapin"],
        )

        assert '"urgent"' in script
        assert '"scapin"' in script
        assert "tagNames" in script


# ============================================================================
# String Escaping Tests
# ============================================================================


class TestStringEscaping:
    """Tests for _escape_applescript_string"""

    def test_escape_simple_string(self, client):
        """Test escaping simple string"""
        result = client._escape_applescript_string("Simple text")
        assert result == "Simple text"

    def test_escape_quotes(self, client):
        """Test escaping quotes"""
        result = client._escape_applescript_string('Text with "quotes"')
        assert result == 'Text with \\"quotes\\"'

    def test_escape_backslashes(self, client):
        """Test escaping backslashes"""
        result = client._escape_applescript_string("Path\\to\\file")
        assert result == "Path\\\\to\\\\file"

    def test_escape_newlines(self, client):
        """Test escaping newlines"""
        result = client._escape_applescript_string("Line1\nLine2")
        assert result == "Line1\\nLine2"

    def test_escape_empty_string(self, client):
        """Test escaping empty string"""
        result = client._escape_applescript_string("")
        assert result == ""

    def test_escape_none(self, client):
        """Test escaping None (should return empty)"""
        result = client._escape_applescript_string(None)
        assert result == ""


# ============================================================================
# AppleScript Execution Tests
# ============================================================================


class TestAppleScriptExecution:
    """Tests for _execute_osascript"""

    def test_execute_success(self, client):
        """Test successful execution"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="result",
                stderr="",
            )

            result = client._execute_osascript("test script")

            assert result == "result"
            mock_run.assert_called_once()

    def test_execute_error(self, client):
        """Test execution with error"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error message",
            )

            with pytest.raises(OmniFocusError) as exc:
                client._execute_osascript("test script")

            assert "Error message" in str(exc.value)

    def test_execute_timeout(self, client):
        """Test execution timeout"""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

            with pytest.raises(OmniFocusError) as exc:
                client._execute_osascript("test script")

            assert "timed out" in str(exc.value)

    def test_execute_osascript_not_found(self, client):
        """Test when osascript is not found"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(OmniFocusError) as exc:
                client._execute_osascript("test script")

            assert "osascript command not found" in str(exc.value)


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateOmniFocusClient:
    """Tests for create_omnifocus_client factory"""

    def test_create_default(self):
        """Test factory with defaults"""
        client = create_omnifocus_client()

        assert client.default_project == "Inbox"

    def test_create_with_project(self):
        """Test factory with custom project"""
        client = create_omnifocus_client(default_project="Custom")

        assert client.default_project == "Custom"

    def test_create_with_config(self):
        """Test factory with config dict"""
        config = {"omnifocus_default_project": "Config Project"}

        client = create_omnifocus_client(config=config)

        assert client.default_project == "Config Project"

    def test_create_project_override_config(self):
        """Test that explicit project overrides config"""
        config = {"omnifocus_default_project": "Config Project"}

        client = create_omnifocus_client(
            default_project="Override",
            config=config,
        )

        assert client.default_project == "Override"


# ============================================================================
# Exception Tests
# ============================================================================


class TestExceptions:
    """Tests for exception hierarchy"""

    def test_omnifocus_error_base(self):
        """Test base exception"""
        err = OmniFocusError("Test error")
        assert str(err) == "Test error"
        assert isinstance(err, Exception)

    def test_not_available_error(self):
        """Test not available exception"""
        err = OmniFocusNotAvailableError("Not running")
        assert str(err) == "Not running"
        assert isinstance(err, OmniFocusError)

    def test_task_creation_error(self):
        """Test task creation exception"""
        err = OmniFocusTaskCreationError("Creation failed")
        assert str(err) == "Creation failed"
        assert isinstance(err, OmniFocusError)
