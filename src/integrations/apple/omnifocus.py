"""
OmniFocus Client — AppleScript Integration

Client pour créer des tâches OmniFocus via AppleScript.

Ce module permet d'envoyer des tâches extraites des emails vers OmniFocus,
notamment pour les deadlines et engagements identifiés par le Workflow v2.1.

Usage:
    client = OmniFocusClient()
    task_id = await client.create_task(
        title="Livrer MVP",
        project="Projet Alpha",
        due_date="2026-01-15",
        note="Engagement de Marc"
    )
"""

import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.monitoring.logger import get_logger

logger = get_logger("omnifocus")


class OmniFocusError(Exception):
    """Base exception for OmniFocus errors"""

    pass


class OmniFocusNotAvailableError(OmniFocusError):
    """OmniFocus is not installed or not accessible"""

    pass


class OmniFocusTaskCreationError(OmniFocusError):
    """Failed to create task in OmniFocus"""

    pass


@dataclass
class OmniFocusTask:
    """Represents a task created in OmniFocus"""

    task_id: str
    title: str
    project: Optional[str] = None
    due_date: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class OmniFocusClient:
    """
    Client for OmniFocus integration via AppleScript.

    Creates tasks in OmniFocus for deadlines and engagements
    extracted from emails by the analysis pipeline.

    Attributes:
        default_project: Default project for new tasks
        timeout: AppleScript execution timeout in seconds

    Example:
        >>> client = OmniFocusClient(default_project="Inbox")
        >>> task = await client.create_task(
        ...     title="Review proposal",
        ...     due_date="2026-01-20",
        ...     note="From: marc@example.com"
        ... )
        >>> print(task.task_id)
    """

    def __init__(
        self,
        default_project: str = "Inbox",
        timeout: int = 30,
    ):
        """
        Initialize the OmniFocus client.

        Args:
            default_project: Default project for tasks without explicit project
            timeout: AppleScript execution timeout in seconds
        """
        self.default_project = default_project
        self.timeout = timeout
        self._is_available: Optional[bool] = None

    async def is_available(self) -> bool:
        """
        Check if OmniFocus is installed and accessible.

        Returns:
            True if OmniFocus is available, False otherwise
        """
        if self._is_available is not None:
            return self._is_available

        script = 'tell application "System Events" to return (name of processes) contains "OmniFocus"'

        try:
            result = await self._run_applescript(script)
            self._is_available = result.strip().lower() == "true"
            return self._is_available
        except Exception as e:
            logger.warning(f"OmniFocus availability check failed: {e}")
            self._is_available = False
            return False

    async def create_task(
        self,
        title: str,
        project: Optional[str] = None,
        due_date: Optional[str] = None,
        note: Optional[str] = None,
        defer_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> OmniFocusTask:
        """
        Create a new task in OmniFocus.

        Args:
            title: Task title (required)
            project: Project name (uses default_project if None)
            due_date: Due date in YYYY-MM-DD format
            note: Additional note/description
            defer_date: Defer date in YYYY-MM-DD format
            tags: List of tag names to apply

        Returns:
            OmniFocusTask with task details including generated ID

        Raises:
            OmniFocusNotAvailableError: If OmniFocus is not accessible
            OmniFocusTaskCreationError: If task creation fails
        """
        if not await self.is_available():
            raise OmniFocusNotAvailableError(
                "OmniFocus is not installed or not running"
            )

        project = project or self.default_project
        tags = tags or []

        # Validate date formats before building script
        validated_due_date = self._validate_date(due_date)
        validated_defer_date = self._validate_date(defer_date)

        # Build AppleScript
        script = self._build_create_task_script(
            title=title,
            project=project,
            due_date=validated_due_date,
            note=note,
            defer_date=validated_defer_date,
            tags=tags,
        )

        try:
            result = await self._run_applescript(script)
            task_id = result.strip() or f"task_{datetime.now().timestamp()}"

            # Parse due_date if provided
            parsed_due_date = None
            if due_date:
                try:
                    parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Invalid due_date format: {due_date}")

            task = OmniFocusTask(
                task_id=task_id,
                title=title,
                project=project,
                due_date=parsed_due_date,
                note=note,
            )

            logger.info(
                f"Created OmniFocus task: {title} "
                f"(project={project}, due={due_date})"
            )
            return task

        except OmniFocusNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Failed to create OmniFocus task: {e}")
            raise OmniFocusTaskCreationError(f"Task creation failed: {e}") from e

    async def get_projects(self) -> list[str]:
        """
        Get list of available projects in OmniFocus.

        Returns:
            List of project names
        """
        if not await self.is_available():
            return []

        script = '''
        tell application "OmniFocus"
            set projectNames to {}
            repeat with proj in (flattened projects of default document)
                set end of projectNames to name of proj
            end repeat
            return projectNames
        end tell
        '''

        try:
            result = await self._run_applescript(script)
            # Parse AppleScript list format: "item1, item2, item3"
            if not result.strip():
                return []
            return [p.strip() for p in result.split(",") if p.strip()]
        except Exception as e:
            logger.warning(f"Failed to get OmniFocus projects: {e}")
            return []

    async def get_tags(self) -> list[str]:
        """
        Get list of available tags in OmniFocus.

        Returns:
            List of tag names
        """
        if not await self.is_available():
            return []

        script = '''
        tell application "OmniFocus"
            set tagNames to {}
            repeat with t in (flattened tags of default document)
                set end of tagNames to name of t
            end repeat
            return tagNames
        end tell
        '''

        try:
            result = await self._run_applescript(script)
            if not result.strip():
                return []
            return [t.strip() for t in result.split(",") if t.strip()]
        except Exception as e:
            logger.warning(f"Failed to get OmniFocus tags: {e}")
            return []

    def _build_create_task_script(
        self,
        title: str,
        project: str,
        due_date: Optional[str],
        note: Optional[str],
        defer_date: Optional[str],
        tags: list[str],
    ) -> str:
        """
        Build AppleScript for task creation.

        Args:
            title: Task title
            project: Project name
            due_date: Due date (YYYY-MM-DD)
            note: Task note
            defer_date: Defer date (YYYY-MM-DD)
            tags: Tag names

        Returns:
            AppleScript string
        """
        # Escape strings for AppleScript
        title_escaped = self._escape_applescript_string(title)
        project_escaped = self._escape_applescript_string(project)
        note_escaped = self._escape_applescript_string(note or "")

        # Build properties
        properties = [f'name:"{title_escaped}"']

        if note:
            properties.append(f'note:"{note_escaped}"')

        # Build date formatting
        date_setup = ""
        if due_date:
            date_setup += f'''
            set dueDate to current date
            set year of dueDate to {due_date[:4]}
            set month of dueDate to {int(due_date[5:7])}
            set day of dueDate to {int(due_date[8:10])}
            set hours of dueDate to 17
            set minutes of dueDate to 0
            set seconds of dueDate to 0
            '''
            properties.append("due date:dueDate")

        if defer_date:
            date_setup += f'''
            set deferDate to current date
            set year of deferDate to {defer_date[:4]}
            set month of deferDate to {int(defer_date[5:7])}
            set day of deferDate to {int(defer_date[8:10])}
            set hours of deferDate to 9
            set minutes of deferDate to 0
            set seconds of deferDate to 0
            '''
            properties.append("defer date:deferDate")

        properties_str = ", ".join(properties)

        # Build tag application
        tag_script = ""
        if tags:
            tag_names = ", ".join(f'"{self._escape_applescript_string(t)}"' for t in tags)
            tag_script = f'''
            set tagNames to {{{tag_names}}}
            repeat with tagName in tagNames
                try
                    set theTag to first flattened tag of default document whose name is tagName
                    add theTag to tags of newTask
                end try
            end repeat
            '''

        script = f'''
        tell application "OmniFocus"
            tell default document
                {date_setup}

                -- Find or create project
                set targetProject to missing value
                try
                    set targetProject to first flattened project whose name is "{project_escaped}"
                end try

                if targetProject is missing value then
                    -- Use inbox if project not found
                    set newTask to make new inbox task with properties {{{properties_str}}}
                else
                    set newTask to make new task with properties {{{properties_str}}} at end of tasks of targetProject
                end if

                {tag_script}

                return id of newTask
            end tell
        end tell
        '''

        return script

    def _validate_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Validate date string format.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            Validated date string or None if invalid
        """
        if not date_str:
            return None

        import re

        # Check YYYY-MM-DD format
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            logger.warning(f"Invalid date format: {date_str}, expected YYYY-MM-DD")
            return None

        # Validate it's a real date
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            logger.warning(f"Invalid date value: {date_str}")
            return None

    def _escape_applescript_string(self, s: str) -> str:
        """
        Escape a string for use in AppleScript.

        Args:
            s: String to escape

        Returns:
            Escaped string safe for AppleScript
        """
        if not s:
            return ""
        # Escape backslashes first, then quotes
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    async def _run_applescript(self, script: str) -> str:
        """
        Execute AppleScript asynchronously.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output as string

        Raises:
            OmniFocusError: If script execution fails
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_osascript,
                script,
            )
            return result
        except Exception as e:
            raise OmniFocusError(f"AppleScript execution failed: {e}") from e

    def _execute_osascript(self, script: str) -> str:
        """
        Execute AppleScript synchronously using osascript.

        Args:
            script: AppleScript code

        Returns:
            Script output

        Raises:
            OmniFocusError: If execution fails
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                raise OmniFocusError(f"AppleScript error: {error_msg}")

            return result.stdout

        except subprocess.TimeoutExpired as e:
            raise OmniFocusError(
                f"AppleScript execution timed out after {self.timeout}s"
            ) from e
        except FileNotFoundError as e:
            raise OmniFocusError("osascript command not found (not on macOS?)") from e


# Factory function
def create_omnifocus_client(
    default_project: Optional[str] = None,
    config: Optional[dict] = None,
) -> OmniFocusClient:
    """
    Create an OmniFocusClient with optional configuration.

    Args:
        default_project: Override default project (takes precedence over config)
        config: Optional config dict with omnifocus settings

    Returns:
        Configured OmniFocusClient
    """
    # Explicit default_project takes precedence over config
    if default_project is not None:
        project = default_project
    elif config:
        project = config.get("omnifocus_default_project", "Inbox")
    else:
        project = "Inbox"

    return OmniFocusClient(default_project=project)
