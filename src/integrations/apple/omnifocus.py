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
import contextlib
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import numpy as np

from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.passepartout.embeddings import EmbeddingGenerator

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
    completed: bool = False

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DuplicateCheckResult:
    """Result of duplicate task check"""

    is_duplicate: bool
    existing_task: Optional[OmniFocusTask] = None
    similarity_score: float = 0.0
    reason: str = ""


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
        use_semantic_similarity: bool = True,
    ):
        """
        Initialize the OmniFocus client.

        Args:
            default_project: Default project for tasks without explicit project
            timeout: AppleScript execution timeout in seconds
            use_semantic_similarity: Use embeddings for semantic duplicate detection
        """
        self.default_project = default_project
        self.timeout = timeout
        self._is_available: Optional[bool] = None
        self._use_semantic = use_semantic_similarity
        self._embedder: Optional[EmbeddingGenerator] = None

    def _get_embedder(self) -> Optional["EmbeddingGenerator"]:
        """
        Lazy-load the embedding generator.

        Returns:
            EmbeddingGenerator instance or None if not available/disabled
        """
        if not self._use_semantic:
            return None

        if self._embedder is None:
            try:
                from src.passepartout.embeddings import EmbeddingGenerator
                self._embedder = EmbeddingGenerator()
                logger.info("Loaded embedding generator for semantic similarity")
            except Exception as e:
                logger.warning(f"Failed to load embeddings, falling back to token-only: {e}")
                self._use_semantic = False
                return None

        return self._embedder

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

    async def search_tasks(
        self,
        query: str,
        include_completed: bool = False,
        limit: int = 50,
    ) -> list[OmniFocusTask]:
        """
        Search for tasks matching a query string.

        Args:
            query: Search string (matches title)
            include_completed: Whether to include completed tasks
            limit: Maximum number of results

        Returns:
            List of matching OmniFocusTask objects
        """
        if not await self.is_available():
            return []

        query_escaped = self._escape_applescript_string(query.lower())
        completed_filter = "" if include_completed else "and completed of t is false"

        script = f'''
        tell application "OmniFocus"
            set matchingTasks to {{}}
            set taskCount to 0
            repeat with t in (flattened tasks of default document)
                if taskCount >= {limit} then exit repeat
                set taskName to name of t
                if taskName contains "{query_escaped}" {completed_filter} then
                    set taskId to id of t
                    set taskProject to ""
                    try
                        set taskProject to name of containing project of t
                    end try
                    set taskDue to ""
                    try
                        set taskDue to due date of t as string
                    end try
                    set taskCompleted to completed of t
                    set end of matchingTasks to taskId & "|||" & taskName & "|||" & taskProject & "|||" & taskDue & "|||" & taskCompleted
                    set taskCount to taskCount + 1
                end if
            end repeat
            set AppleScript's text item delimiters to ":::"
            return matchingTasks as string
        end tell
        '''

        try:
            result = await self._run_applescript(script)
            if not result.strip():
                return []

            tasks = []
            for task_str in result.split(":::"):
                task_str = task_str.strip()
                if not task_str:
                    continue
                parts = task_str.split("|||")
                if len(parts) >= 5:
                    task_id, title, project, due_str, completed_str = parts[:5]
                    due_date = None
                    if due_str and due_str != "missing value":
                        with contextlib.suppress(Exception):
                            due_date = self._parse_applescript_date(due_str)
                    tasks.append(OmniFocusTask(
                        task_id=task_id,
                        title=title,
                        project=project if project else None,
                        due_date=due_date,
                        completed=completed_str.lower() == "true",
                    ))
            return tasks
        except Exception as e:
            logger.warning(f"Failed to search OmniFocus tasks: {e}")
            return []

    async def check_duplicate(
        self,
        title: str,
        due_date: Optional[str] = None,
        project: Optional[str] = None,
        similarity_threshold: float = 0.8,
    ) -> DuplicateCheckResult:
        """
        Check if a similar task already exists in OmniFocus.

        Uses fuzzy matching to detect potential duplicates based on:
        - Title similarity (primary)
        - Same due date (if provided)
        - Same project (if provided)

        Args:
            title: Proposed task title
            due_date: Proposed due date (YYYY-MM-DD)
            project: Proposed project name
            similarity_threshold: Minimum similarity score (0.0-1.0) to consider duplicate

        Returns:
            DuplicateCheckResult with is_duplicate flag and details
        """
        if not await self.is_available():
            return DuplicateCheckResult(
                is_duplicate=False,
                reason="OmniFocus not available"
            )

        # Extract keywords from title for search
        keywords = self._extract_keywords(title)
        if not keywords:
            return DuplicateCheckResult(
                is_duplicate=False,
                reason="No keywords extracted from title"
            )

        # Search for tasks containing any keyword
        all_matches: list[OmniFocusTask] = []
        for keyword in keywords[:3]:  # Limit to 3 keywords to avoid too many searches
            matches = await self.search_tasks(keyword, include_completed=False)
            all_matches.extend(matches)

        # Deduplicate by task_id
        seen_ids: set[str] = set()
        unique_matches: list[OmniFocusTask] = []
        for task in all_matches:
            if task.task_id not in seen_ids:
                seen_ids.add(task.task_id)
                unique_matches.append(task)

        if not unique_matches:
            return DuplicateCheckResult(
                is_duplicate=False,
                reason="No similar tasks found"
            )

        # Check each match for similarity
        best_match: Optional[OmniFocusTask] = None
        best_score = 0.0

        for task in unique_matches:
            score = self._calculate_similarity(
                title, task.title, due_date, task.due_date, project, task.project
            )
            if score > best_score:
                best_score = score
                best_match = task

        if best_score >= similarity_threshold and best_match:
            return DuplicateCheckResult(
                is_duplicate=True,
                existing_task=best_match,
                similarity_score=best_score,
                reason=f"Similar task found: '{best_match.title}' (score: {best_score:.2f})"
            )

        return DuplicateCheckResult(
            is_duplicate=False,
            similarity_score=best_score,
            reason=f"No duplicate found (best score: {best_score:.2f})"
        )

    async def create_task_if_not_duplicate(
        self,
        title: str,
        project: Optional[str] = None,
        due_date: Optional[str] = None,
        note: Optional[str] = None,
        defer_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        similarity_threshold: float = 0.8,
    ) -> tuple[Optional[OmniFocusTask], DuplicateCheckResult]:
        """
        Create a task only if no duplicate exists.

        First checks for duplicates, then creates the task if none found.

        Args:
            title: Task title
            project: Project name
            due_date: Due date (YYYY-MM-DD)
            note: Task note
            defer_date: Defer date (YYYY-MM-DD)
            tags: Tag names
            similarity_threshold: Minimum similarity to consider duplicate

        Returns:
            Tuple of (created_task or None, DuplicateCheckResult)
        """
        # Check for duplicates first
        check_result = await self.check_duplicate(
            title=title,
            due_date=due_date,
            project=project,
            similarity_threshold=similarity_threshold,
        )

        if check_result.is_duplicate:
            logger.info(
                f"Skipping duplicate task: '{title}' - {check_result.reason}"
            )
            return None, check_result

        # No duplicate found, create the task
        task = await self.create_task(
            title=title,
            project=project,
            due_date=due_date,
            note=note,
            defer_date=defer_date,
            tags=tags,
        )

        return task, check_result

    def _extract_keywords(self, title: str) -> list[str]:
        """
        Extract meaningful keywords from a task title for search.

        Filters out common stop words and short words.

        Args:
            title: Task title

        Returns:
            List of keywords (longest first)
        """
        # French and English stop words
        stop_words = {
            # French
            "le", "la", "les", "un", "une", "des", "du", "de", "à", "au", "aux",
            "et", "ou", "mais", "donc", "car", "ni", "que", "qui", "quoi",
            "pour", "par", "sur", "sous", "avec", "sans", "dans", "en",
            "ce", "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes",
            "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs",
            "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
            "être", "avoir", "faire", "dire", "aller", "voir", "pouvoir",
            # English
            "the", "a", "an", "and", "or", "but", "if", "then", "else",
            "for", "to", "from", "with", "without", "in", "on", "at", "by",
            "this", "that", "these", "those", "my", "your", "his", "her",
            "its", "our", "their", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "can", "could", "should", "may", "might", "must",
        }

        # Tokenize and filter
        words = title.lower().split()
        keywords = [
            w for w in words
            if len(w) >= 3 and w not in stop_words and w.isalnum()
        ]

        # Sort by length (longer words are more specific)
        keywords.sort(key=len, reverse=True)

        return keywords

    def _calculate_similarity(
        self,
        title1: str,
        title2: str,
        due1: Optional[str],
        due2: Optional[datetime],
        project1: Optional[str],
        project2: Optional[str],
    ) -> float:
        """
        Calculate similarity score between two tasks.

        Uses hybrid approach:
        - Semantic similarity (embeddings) if available
        - Token-based (Jaccard) as fallback
        - Takes the MAX of both for best detection

        Weights:
        - Title similarity: 70%
        - Due date match: 20%
        - Project match: 10%

        Args:
            title1, title2: Task titles
            due1: First task due date (YYYY-MM-DD string)
            due2: Second task due date (datetime)
            project1, project2: Project names

        Returns:
            Similarity score (0.0-1.0)
        """
        # Token-based similarity (always available)
        token_score = self._token_similarity(title1.lower(), title2.lower())

        # Semantic similarity (if embeddings available)
        semantic_score = self._semantic_similarity(title1, title2)

        # Take the MAX of token and semantic for title score
        # This catches both exact matches AND semantic equivalents
        title_score = max(token_score, semantic_score)

        logger.debug(
            f"Title similarity: token={token_score:.2f}, semantic={semantic_score:.2f}, "
            f"final={title_score:.2f}"
        )

        # Due date match (20% weight)
        due_score = 0.0
        if due1 and due2:
            try:
                due1_dt = datetime.strptime(due1, "%Y-%m-%d")
                # Check if same day
                if due1_dt.date() == due2.date():
                    due_score = 1.0
                # Check if within 1 day
                elif abs((due1_dt.date() - due2.date()).days) <= 1:
                    due_score = 0.5
            except (ValueError, AttributeError):
                pass

        # Project match (10% weight)
        project_score = 0.0
        if project1 and project2:
            if project1.lower() == project2.lower():
                project_score = 1.0
            elif project1.lower() in project2.lower() or project2.lower() in project1.lower():
                project_score = 0.5

        # Weighted combination
        return title_score * 0.7 + due_score * 0.2 + project_score * 0.1

    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity using embeddings.

        Uses cosine similarity between embedding vectors.
        Falls back to 0.0 if embeddings are not available.

        Args:
            text1, text2: Texts to compare

        Returns:
            Similarity score (0.0-1.0)
        """
        embedder = self._get_embedder()
        if embedder is None:
            return 0.0

        try:
            # Generate embeddings (normalized by default)
            emb1 = embedder.embed_text(text1)
            emb2 = embedder.embed_text(text2)

            # Cosine similarity (embeddings are already normalized)
            similarity = float(np.dot(emb1, emb2))

            # Clamp to [0, 1] (in case of numerical errors)
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.warning(f"Semantic similarity failed: {e}")
            return 0.0

    def _token_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate token-based similarity between two strings.

        Uses Jaccard similarity on word tokens.

        Args:
            s1, s2: Strings to compare

        Returns:
            Similarity score (0.0-1.0)
        """
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def _parse_applescript_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse AppleScript date string to datetime.

        AppleScript dates vary by locale, try common formats.

        Args:
            date_str: Date string from AppleScript

        Returns:
            Parsed datetime or None
        """
        # Common formats to try
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d %B %Y %H:%M:%S",
            "%B %d, %Y %H:%M:%S",
            "%A %d %B %Y à %H:%M:%S",  # French locale
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

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
