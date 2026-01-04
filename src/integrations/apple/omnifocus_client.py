"""
OmniFocus Client

Wrapper around OmniFocus MCP tools for task management.
Provides a clean Python interface for actions to interact with OmniFocus.

Also includes AppleScript-based methods for journaling data retrieval.
"""

import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Optional

from src.integrations.apple.omnifocus_models import (
    OmniFocusDailyStats,
    OmniFocusProject,
    OmniFocusTask,
    ProjectStatus,
    TaskStatus,
)
from src.monitoring.logger import get_logger

logger = get_logger("integrations.apple.omnifocus")


class OmniFocusClient:
    """
    Client for OmniFocus operations

    Wraps the MCP OmniFocus tools to provide a clean interface
    for task creation, editing, and querying.

    Note: This is a thin wrapper - actual implementation uses
    the MCP tools provided by the omnifocus-enhanced server.
    """

    def __init__(self):
        """Initialize OmniFocus client"""
        logger.debug("Initialized OmniFocus client")

    def add_task(
        self,
        name: str,
        _note: Optional[str] = None,
        project_name: Optional[str] = None,
        tags: list[str] = None,
        _due_date: Optional[str] = None,
        _defer_date: Optional[str] = None,
        _estimated_minutes: Optional[int] = None,
        _flagged: bool = False
    ) -> dict[str, Any]:
        """
        Add a new task to OmniFocus

        Args:
            name: Task name (required)
            note: Task notes
            project_name: Project to add task to
            tags: List of tags
            due_date: Due date (ISO format)
            defer_date: Defer date (ISO format)
            estimated_minutes: Estimated duration in minutes
            flagged: Whether task is flagged

        Returns:
            Dict with task details including 'id'

        Note: This method would call the MCP tool mcp__omnifocus-enhanced__add_omnifocus_task
        in a real implementation. For now, it's a placeholder that actions can call.
        """
        # In real implementation, this would call:
        # result = mcp__omnifocus-enhanced__add_omnifocus_task(...)

        # Placeholder implementation
        logger.info(
            f"Adding task to OmniFocus: {name}",
            extra={
                "task_name": name,
                "project": project_name,
                "tags": tags
            }
        )

        # Return mock result
        # In real implementation, this would come from MCP tool
        return {
            "id": f"task_{name.replace(' ', '_').lower()}",
            "name": name,
            "project": project_name,
            "status": "created"
        }

    def edit_task(
        self,
        task_id: Optional[str] = None,
        task_name: Optional[str] = None,
        new_status: Optional[str] = None,
        _new_name: Optional[str] = None,
        _new_note: Optional[str] = None,
        _new_due_date: Optional[str] = None,
        _new_defer_date: Optional[str] = None,
        _new_flagged: Optional[bool] = None,
        _add_tags: list[str] = None,
        _remove_tags: list[str] = None
    ) -> dict[str, Any]:
        """
        Edit an existing task

        Args:
            task_id: Task ID (preferred)
            task_name: Task name (alternative to task_id)
            new_status: New status (incomplete, completed, dropped)
            new_name: New task name
            new_note: New notes
            new_due_date: New due date
            new_defer_date: New defer date
            new_flagged: New flagged status
            add_tags: Tags to add
            remove_tags: Tags to remove

        Returns:
            Dict with updated task details

        Note: This method would call the MCP tool mcp__omnifocus-enhanced__edit_item
        """
        logger.info(
            f"Editing task: {task_id or task_name}",
            extra={
                "task_id": task_id,
                "task_name": task_name,
                "new_status": new_status
            }
        )

        # Placeholder implementation
        return {
            "id": task_id,
            "status": new_status or "updated"
        }

    def remove_task(
        self,
        task_id: Optional[str] = None,
        task_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Remove a task from OmniFocus

        Args:
            task_id: Task ID (preferred)
            task_name: Task name (alternative)

        Returns:
            Dict with removal status

        Note: This method would call the MCP tool mcp__omnifocus-enhanced__remove_item
        """
        logger.info(
            f"Removing task: {task_id or task_name}",
            extra={
                "task_id": task_id,
                "task_name": task_name
            }
        )

        # Placeholder implementation
        return {
            "id": task_id,
            "status": "removed"
        }

    def get_task_by_name(self, task_name: str) -> Optional[dict[str, Any]]:
        """
        Get task by name

        Args:
            task_name: Name of task to find

        Returns:
            Task dict or None if not found

        Note: This method would call the MCP tool mcp__omnifocus-enhanced__get_task_by_id
        with taskName parameter
        """
        logger.debug(f"Looking up task by name: {task_name}")

        # Placeholder implementation
        return {
            "id": f"task_{task_name.replace(' ', '_').lower()}",
            "name": task_name,
            "status": "active"
        }

    def get_task_by_id(self, task_id: str) -> Optional[dict[str, Any]]:
        """
        Get task by ID

        Args:
            task_id: Task ID

        Returns:
            Task dict or None if not found

        Note: This method would call the MCP tool mcp__omnifocus-enhanced__get_task_by_id
        """
        logger.debug(f"Looking up task by ID: {task_id}")

        # Placeholder implementation
        return {
            "id": task_id,
            "status": "active"
        }

    # ========================================================================
    # AppleScript-based methods for journaling data retrieval
    # ========================================================================

    def _run_applescript(self, script: str) -> Optional[str]:
        """
        Execute AppleScript and return output.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output as string, or None on error
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    f"AppleScript error: {result.stderr}",
                    extra={"returncode": result.returncode},
                )
                return None
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error("AppleScript execution timed out")
            return None
        except Exception as e:
            logger.error(f"AppleScript execution failed: {e}")
            return None

    def _parse_task_from_dict(self, data: dict[str, Any]) -> OmniFocusTask:
        """Parse a task dictionary into an OmniFocusTask object."""
        # Parse status
        status_str = data.get("status", "active").lower()
        status_map = {
            "active": TaskStatus.ACTIVE,
            "completed": TaskStatus.COMPLETED,
            "dropped": TaskStatus.DROPPED,
            "on hold": TaskStatus.ON_HOLD,
            "on_hold": TaskStatus.ON_HOLD,
        }
        status = status_map.get(status_str, TaskStatus.ACTIVE)

        # Parse dates
        def parse_date(val: Any) -> Optional[datetime]:
            if not val or val == "missing value":
                return None
            if isinstance(val, str):
                try:
                    # Try ISO format first
                    return datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        # Try common AppleScript date format
                        return datetime.strptime(val, "%A, %B %d, %Y at %I:%M:%S %p")
                    except ValueError:
                        return None
            return None

        # Parse tags
        tags_raw = data.get("tags", [])
        if isinstance(tags_raw, str):
            tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip())
        elif isinstance(tags_raw, list):
            tags = tuple(tags_raw)
        else:
            tags = ()

        return OmniFocusTask(
            task_id=data.get("id", ""),
            name=data.get("name", ""),
            status=status,
            created_at=parse_date(data.get("creation_date")),
            modified_at=parse_date(data.get("modification_date")),
            completed_at=parse_date(data.get("completion_date")),
            due_date=parse_date(data.get("due_date")),
            defer_date=parse_date(data.get("defer_date")),
            project_id=data.get("project_id"),
            project_name=data.get("project_name"),
            tags=tags,
            note=data.get("note") if data.get("note") != "missing value" else None,
            flagged=data.get("flagged", False),
            estimated_minutes=data.get("estimated_minutes"),
        )

    def _parse_project_from_dict(self, data: dict[str, Any]) -> OmniFocusProject:
        """Parse a project dictionary into an OmniFocusProject object."""
        # Parse status
        status_str = data.get("status", "active").lower()
        status_map = {
            "active": ProjectStatus.ACTIVE,
            "done": ProjectStatus.COMPLETED,
            "dropped": ProjectStatus.DROPPED,
            "on hold": ProjectStatus.ON_HOLD,
            "on_hold": ProjectStatus.ON_HOLD,
        }
        status = status_map.get(status_str, ProjectStatus.ACTIVE)

        # Parse dates
        def parse_date(val: Any) -> Optional[datetime]:
            if not val or val == "missing value":
                return None
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    return None
            return None

        # Parse tags
        tags_raw = data.get("tags", [])
        tags = tuple(tags_raw) if isinstance(tags_raw, list) else ()

        return OmniFocusProject(
            project_id=data.get("id", ""),
            name=data.get("name", ""),
            status=status,
            created_at=parse_date(data.get("creation_date")),
            modified_at=parse_date(data.get("modification_date")),
            completed_at=parse_date(data.get("completion_date")),
            due_date=parse_date(data.get("due_date")),
            folder_name=data.get("folder_name"),
            tags=tags,
            task_count=data.get("task_count", 0),
            remaining_tasks=data.get("remaining_tasks", 0),
            completed_tasks=data.get("completed_tasks", 0),
        )

    def get_completed_tasks_today(self) -> list[OmniFocusTask]:
        """
        Get all tasks completed today.

        Returns:
            List of OmniFocusTask objects completed today
        """
        script = '''
        tell application "OmniFocus"
            set today to current date
            set today's time to 0
            set tomorrow to today + (1 * days)
            set taskList to {}

            tell default document
                set completedTasks to every flattened task whose completed is true and completion date ≥ today and completion date < tomorrow
                repeat with t in completedTasks
                    set taskData to {|id|: id of t, |name|: name of t, |status|: "completed"}
                    try
                        set taskData to taskData & {|completion_date|: (completion date of t) as string}
                    end try
                    try
                        set taskData to taskData & {|creation_date|: (creation date of t) as string}
                    end try
                    try
                        set taskData to taskData & {|project_name|: name of containing project of t}
                    end try
                    try
                        set taskData to taskData & {|flagged|: flagged of t}
                    end try
                    set end of taskList to taskData
                end repeat
            end tell

            return taskList as string
        end tell
        '''

        result = self._run_applescript(script)
        if not result:
            logger.debug("No completed tasks found or OmniFocus not available")
            return []

        try:
            # Parse AppleScript record output
            tasks = self._parse_applescript_records(result)
            return [self._parse_task_from_dict(t) for t in tasks]
        except Exception as e:
            logger.error(f"Failed to parse completed tasks: {e}")
            return []

    def get_created_tasks_today(self) -> list[OmniFocusTask]:
        """
        Get all tasks created today.

        Returns:
            List of OmniFocusTask objects created today
        """
        script = '''
        tell application "OmniFocus"
            set today to current date
            set today's time to 0
            set tomorrow to today + (1 * days)
            set taskList to {}

            tell default document
                set createdTasks to every flattened task whose creation date ≥ today and creation date < tomorrow
                repeat with t in createdTasks
                    set taskData to {|id|: id of t, |name|: name of t}
                    try
                        if completed of t then
                            set taskData to taskData & {|status|: "completed"}
                        else
                            set taskData to taskData & {|status|: "active"}
                        end if
                    end try
                    try
                        set taskData to taskData & {|creation_date|: (creation date of t) as string}
                    end try
                    try
                        set taskData to taskData & {|project_name|: name of containing project of t}
                    end try
                    try
                        set taskData to taskData & {|flagged|: flagged of t}
                    end try
                    set end of taskList to taskData
                end repeat
            end tell

            return taskList as string
        end tell
        '''

        result = self._run_applescript(script)
        if not result:
            logger.debug("No created tasks found or OmniFocus not available")
            return []

        try:
            tasks = self._parse_applescript_records(result)
            return [self._parse_task_from_dict(t) for t in tasks]
        except Exception as e:
            logger.error(f"Failed to parse created tasks: {e}")
            return []

    def get_due_tasks_today(self) -> list[OmniFocusTask]:
        """
        Get all tasks due today.

        Returns:
            List of OmniFocusTask objects due today
        """
        script = '''
        tell application "OmniFocus"
            set today to current date
            set today's time to 0
            set tomorrow to today + (1 * days)
            set taskList to {}

            tell default document
                set dueTasks to every flattened task whose completed is false and due date ≥ today and due date < tomorrow
                repeat with t in dueTasks
                    set taskData to {|id|: id of t, |name|: name of t, |status|: "active"}
                    try
                        set taskData to taskData & {|due_date|: (due date of t) as string}
                    end try
                    try
                        set taskData to taskData & {|creation_date|: (creation date of t) as string}
                    end try
                    try
                        set taskData to taskData & {|project_name|: name of containing project of t}
                    end try
                    try
                        set taskData to taskData & {|flagged|: flagged of t}
                    end try
                    set end of taskList to taskData
                end repeat
            end tell

            return taskList as string
        end tell
        '''

        result = self._run_applescript(script)
        if not result:
            logger.debug("No due tasks found or OmniFocus not available")
            return []

        try:
            tasks = self._parse_applescript_records(result)
            return [self._parse_task_from_dict(t) for t in tasks]
        except Exception as e:
            logger.error(f"Failed to parse due tasks: {e}")
            return []

    def get_overdue_tasks(self) -> list[OmniFocusTask]:
        """
        Get all overdue tasks.

        Returns:
            List of overdue OmniFocusTask objects
        """
        script = '''
        tell application "OmniFocus"
            set today to current date
            set today's time to 0
            set taskList to {}

            tell default document
                set overdueTasks to every flattened task whose completed is false and due date < today and due date is not missing value
                repeat with t in overdueTasks
                    set taskData to {|id|: id of t, |name|: name of t, |status|: "active"}
                    try
                        set taskData to taskData & {|due_date|: (due date of t) as string}
                    end try
                    try
                        set taskData to taskData & {|creation_date|: (creation date of t) as string}
                    end try
                    try
                        set taskData to taskData & {|project_name|: name of containing project of t}
                    end try
                    try
                        set taskData to taskData & {|flagged|: flagged of t}
                    end try
                    set end of taskList to taskData
                end repeat
            end tell

            return taskList as string
        end tell
        '''

        result = self._run_applescript(script)
        if not result:
            logger.debug("No overdue tasks found or OmniFocus not available")
            return []

        try:
            tasks = self._parse_applescript_records(result)
            return [self._parse_task_from_dict(t) for t in tasks]
        except Exception as e:
            logger.error(f"Failed to parse overdue tasks: {e}")
            return []

    def _parse_applescript_records(self, output: str) -> list[dict[str, Any]]:
        """
        Parse AppleScript record output into list of dictionaries.

        AppleScript returns records in format like:
        {{|id|:"xxx", |name|:"Task 1"}, {|id|:"yyy", |name|:"Task 2"}}

        Args:
            output: Raw AppleScript output string

        Returns:
            List of parsed dictionaries
        """
        if not output or output == "{}" or output == "":
            return []

        # Try JSON-like parsing first (simpler output)
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Parse AppleScript record format
        records = []
        current_record: dict[str, Any] = {}
        depth = 0
        key = ""
        value = ""
        in_key = False
        in_value = False
        in_string = False

        i = 0
        while i < len(output):
            char = output[i]

            if char == "{":
                depth += 1
                if depth == 2:
                    current_record = {}
            elif char == "}":
                if depth == 2 and current_record:
                    if key and value:
                        current_record[key.strip("|")] = self._parse_value(value)
                    records.append(current_record)
                    current_record = {}
                    key = ""
                    value = ""
                    in_key = False
                    in_value = False
                depth -= 1
            elif depth == 2:
                if char == "|":
                    in_key = not in_key
                elif char == ":":
                    in_value = True
                    in_key = False
                elif char == ",":
                    if key and value:
                        current_record[key.strip("|")] = self._parse_value(value)
                    key = ""
                    value = ""
                    in_value = False
                elif char == '"':
                    in_string = not in_string
                    if in_value:
                        value += char
                elif in_key:
                    key += char
                elif in_value:
                    value += char

            i += 1

        return records

    def _parse_value(self, value: str) -> Any:
        """Parse a string value from AppleScript output."""
        value = value.strip()

        # Remove surrounding quotes
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]

        # Boolean values
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # Numeric values
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        return value

    def get_daily_stats(self, date: Optional[datetime] = None) -> OmniFocusDailyStats:
        """
        Get aggregated daily statistics for journaling.

        Args:
            date: Date to get stats for (defaults to today)

        Returns:
            OmniFocusDailyStats with all daily metrics
        """
        if date is None:
            date = datetime.now(timezone.utc)

        logger.info(f"Getting OmniFocus daily stats for {date.date()}")

        completed = self.get_completed_tasks_today()
        created = self.get_created_tasks_today()
        due = self.get_due_tasks_today()
        overdue = self.get_overdue_tasks()

        # Get unique projects modified
        projects_modified = set()
        for task in completed + created:
            if task.project_name:
                projects_modified.add(task.project_name)

        return OmniFocusDailyStats(
            date=date,
            tasks_completed=len(completed),
            tasks_created=len(created),
            tasks_due=len(due),
            tasks_overdue=len(overdue),
            completed_tasks=tuple(completed),
            created_tasks=tuple(created),
            due_tasks=tuple(due),
            projects_modified=tuple(sorted(projects_modified)),
        )

    def is_available(self) -> bool:
        """
        Check if OmniFocus is available on this system.

        Returns:
            True if OmniFocus is installed and accessible
        """
        script = '''
        try
            tell application "System Events"
                return exists (application process "OmniFocus")
            end tell
        on error
            return false
        end try
        '''
        result = self._run_applescript(script)
        return result is not None and result.lower() == "true"
