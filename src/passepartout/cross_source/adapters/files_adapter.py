"""
Files adapter for CrossSourceEngine.

Provides search functionality for local files using ripgrep (rg) or fallback
to Python glob+read for systems without ripgrep installed.

Searches in configured directories for text content matching the query.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.passepartout.cross_source.adapters.base import BaseAdapter
from src.passepartout.cross_source.models import SourceItem

logger = logging.getLogger("scapin.cross_source.files")

# Default file extensions to search
DEFAULT_EXTENSIONS = [
    ".txt", ".md", ".markdown", ".rst", ".org",
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".toml",
    ".html", ".css", ".scss",
    ".sh", ".bash", ".zsh",
    ".sql", ".csv",
]

# Directories to exclude
DEFAULT_EXCLUDES = [
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".venv", "venv",
    ".cache", ".npm", ".yarn",
    "dist", "build", "target",
    ".DS_Store", "Thumbs.db",
]

# Security constants
MAX_PATH_LENGTH = 4096
MAX_QUERY_LENGTH = 500


class FilesAdapter(BaseAdapter):
    """
    Local files adapter for cross-source queries.

    Uses ripgrep (rg) when available for fast searching, with fallback
    to Python-based search for compatibility.
    """

    _source_name = "files"

    def __init__(
        self,
        search_paths: list[Path | str] | None = None,
        extensions: list[str] | None = None,
        exclude_dirs: list[str] | None = None,
        use_ripgrep: bool = True,
        max_file_size_kb: int = 1024,
    ) -> None:
        """
        Initialize the Files adapter.

        Args:
            search_paths: Directories to search (default: ~/Documents, ~/Desktop)
            extensions: File extensions to include (default: common text files)
            exclude_dirs: Directories to exclude from search
            use_ripgrep: Whether to use ripgrep if available (default: True)
            max_file_size_kb: Maximum file size to search in KB (default: 1MB)
        """
        self._search_paths = [
            Path(p) for p in (search_paths or self._default_search_paths())
        ]
        self._extensions = extensions or DEFAULT_EXTENSIONS
        self._exclude_dirs = exclude_dirs or DEFAULT_EXCLUDES
        self._use_ripgrep = use_ripgrep and self._ripgrep_available()
        self._max_file_size = max_file_size_kb * 1024

    def _default_search_paths(self) -> list[Path]:
        """Get default search paths."""
        home = Path.home()
        paths = []
        for dirname in ["Documents", "Desktop", "Downloads"]:
            path = home / dirname
            if path.exists():
                paths.append(path)
        return paths or [home]

    def _ripgrep_available(self) -> bool:
        """Check if ripgrep is installed."""
        try:
            result = subprocess.run(
                ["rg", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _validate_path(self, path_str: str | None) -> Path | None:
        """
        Validate and sanitize a path to prevent path traversal attacks.

        Args:
            path_str: Path string to validate

        Returns:
            Validated Path or None if invalid
        """
        if not path_str or not isinstance(path_str, str):
            return None

        # Length check
        if len(path_str) > MAX_PATH_LENGTH:
            logger.warning("Path too long: %d chars", len(path_str))
            return None

        try:
            # Resolve the path to get absolute path and resolve symlinks
            path = Path(path_str).resolve()

            # Check if path is within one of the allowed search paths
            for allowed_path in self._search_paths:
                allowed_resolved = allowed_path.resolve()
                try:
                    # Check if path is relative to any allowed path
                    path.relative_to(allowed_resolved)
                    # Path is within allowed directory
                    if path.exists():
                        return path
                    else:
                        logger.warning("Path does not exist: %s", path)
                        return None
                except ValueError:
                    # Not relative to this allowed path, continue checking
                    continue

            # Path not within any allowed directory
            logger.warning(
                "Path traversal attempt blocked: %s not within allowed paths",
                path_str
            )
            return None

        except (OSError, ValueError) as e:
            logger.warning("Invalid path: %s - %s", path_str, e)
            return None

    def _validate_query(self, query: str) -> str:
        """Validate and sanitize search query."""
        if not query or not isinstance(query, str):
            return ""
        return query[:MAX_QUERY_LENGTH].strip()

    @property
    def is_available(self) -> bool:
        """Check if file search is available."""
        return any(p.exists() for p in self._search_paths)

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """
        Search local files for relevant content.

        Args:
            query: The search query string
            max_results: Maximum number of results to return
            context: Optional context with additional filters
                    - path: specific path to search
                    - extension: filter by extension
                    - modified_since: datetime filter

        Returns:
            List of SourceItem objects representing matching files
        """
        if not self.is_available:
            logger.warning("Files adapter not available, skipping search")
            return []

        # Validate query
        safe_query = self._validate_query(query)
        if not safe_query:
            logger.warning("Invalid or empty query")
            return []

        try:
            # Get filter options from context
            path_filter = None
            ext_filter = None
            modified_since = None

            if context:
                path_filter = context.get("path")
                ext_filter = context.get("extension")
                modified_since = context.get("modified_since")

            # Determine search paths (with security validation)
            search_paths = self._search_paths
            if path_filter:
                validated_path = self._validate_path(path_filter)
                if validated_path:
                    search_paths = [validated_path]
                else:
                    # Path validation failed - use default paths instead
                    logger.info("Using default search paths due to invalid path filter")

            # Determine extensions
            extensions = self._extensions
            if ext_filter:
                extensions = [ext_filter] if isinstance(ext_filter, str) else ext_filter

            # Perform search with sanitized query
            if self._use_ripgrep:
                matches = await self._search_ripgrep(
                    query=safe_query,
                    paths=search_paths,
                    extensions=extensions,
                    max_results=max_results * 2,  # Get more to filter
                )
            else:
                matches = await self._search_python(
                    query=safe_query,
                    paths=search_paths,
                    extensions=extensions,
                    max_results=max_results * 2,
                )

            # Filter by modified time if specified
            if modified_since:
                matches = [
                    m for m in matches
                    if m.get("modified", datetime.min.replace(tzinfo=timezone.utc)) >= modified_since
                ]

            # Convert to SourceItems
            results = [
                self._match_to_source_item(match, safe_query)
                for match in matches[:max_results]
            ]

            logger.debug(
                "Files search found %d matches for '%s' (ripgrep=%s)",
                len(results),
                query[:50],
                self._use_ripgrep,
            )

            return results

        except Exception as e:
            logger.error("Files search failed: %s", e)
            return []

    async def _search_ripgrep(
        self,
        query: str,
        paths: list[Path],
        extensions: list[str],
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Search using ripgrep.

        Args:
            query: Search query
            paths: Paths to search
            extensions: File extensions to include
            max_results: Maximum results

        Returns:
            List of match dictionaries
        """
        matches = []

        for search_path in paths:
            if not search_path.exists():
                continue

            # Build ripgrep command
            cmd = [
                "rg",
                "--json",  # JSON output for parsing
                "--max-count", "3",  # Max matches per file
                "--max-filesize", f"{self._max_file_size}",
                "-i",  # Case insensitive
                "-m", str(max_results),  # Limit total matches to avoid OOM
            ]

            # Add extension filters
            for ext in extensions:
                cmd.extend(["--glob", f"*{ext}"])

            # Add exclude patterns
            for exclude in self._exclude_dirs:
                cmd.extend(["--glob", f"!{exclude}/**"])

            cmd.extend([query, str(search_path)])

            try:
                # Run ripgrep
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=30.0,
                )

                # Parse JSON output
                import json
                for line in stdout.decode().strip().split("\n"):
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("type") == "match":
                            match_data = data.get("data", {})
                            path_info = match_data.get("path", {})
                            file_path = path_info.get("text", "")

                            if file_path:
                                matches.append({
                                    "path": Path(file_path),
                                    "line_number": match_data.get("line_number", 0),
                                    "line_text": match_data.get("lines", {}).get("text", "").strip(),
                                    "modified": self._get_mtime(Path(file_path)),
                                })
                    except json.JSONDecodeError:
                        continue

                    if len(matches) >= max_results:
                        break

            except asyncio.TimeoutError:
                logger.warning("Ripgrep search timed out for %s", search_path)
            except Exception as e:
                logger.error("Ripgrep error: %s", e)

        return matches[:max_results]

    async def _search_python(
        self,
        query: str,
        paths: list[Path],
        extensions: list[str],
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Search using Python (fallback when ripgrep unavailable).

        Uses single directory walk for O(N) performance instead of
        O(E*N) where E is number of extensions.

        Args:
            query: Search query
            paths: Paths to search
            extensions: File extensions to include
            max_results: Maximum results

        Returns:
            List of match dictionaries
        """
        matches = []
        query_lower = query.lower()
        # Convert extensions to set for O(1) lookup
        extension_set = {ext.lower() for ext in extensions}

        for search_path in paths:
            if not search_path.exists():
                continue

            # Single directory walk - O(N) instead of O(E*N)
            for file_path in search_path.rglob("*"):
                # Skip if not a file
                if not file_path.is_file():
                    continue

                # Check extension (O(1) lookup)
                if file_path.suffix.lower() not in extension_set:
                    continue

                # Skip excluded directories
                if any(excl in file_path.parts for excl in self._exclude_dirs):
                    continue

                # Skip large files
                try:
                    if file_path.stat().st_size > self._max_file_size:
                        continue
                except OSError:
                    continue

                # Search file content
                match = await self._search_file(file_path, query_lower)
                if match:
                    matches.append(match)

                if len(matches) >= max_results:
                    return matches

        return matches

    async def _search_file(
        self,
        file_path: Path,
        query_lower: str,
    ) -> dict[str, Any] | None:
        """
        Search a single file for query matches.

        Args:
            file_path: Path to file
            query_lower: Lowercase query string

        Returns:
            Match dictionary or None
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            content_lower = content.lower()

            if query_lower in content_lower:
                # Find the matching line
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if query_lower in line.lower():
                        return {
                            "path": file_path,
                            "line_number": i,
                            "line_text": line.strip()[:200],
                            "modified": self._get_mtime(file_path),
                        }
        except (OSError, UnicodeDecodeError):
            pass

        return None

    def _get_mtime(self, path: Path) -> datetime:
        """Get file modification time."""
        try:
            mtime = path.stat().st_mtime
            return datetime.fromtimestamp(mtime, tz=timezone.utc)
        except OSError:
            return datetime.now(timezone.utc)

    def _match_to_source_item(
        self,
        match: dict[str, Any],
        query: str,
    ) -> SourceItem:
        """
        Convert a match dict to SourceItem.

        Args:
            match: Match dictionary
            query: Original search query

        Returns:
            SourceItem representation
        """
        file_path: Path = match["path"]

        # Build title from filename
        title = file_path.name

        # Build content with context
        content_parts = []
        content_parts.append(f"Path: {file_path}")
        content_parts.append(f"Modified: {match['modified'].strftime('%d/%m/%Y %H:%M')}")
        if match.get("line_number"):
            content_parts.append(f"Line {match['line_number']}: {match.get('line_text', '')}")

        # Try to get more context from the file
        try:
            full_content = file_path.read_text(encoding="utf-8", errors="ignore")
            preview = full_content[:500]
            if len(full_content) > 500:
                preview += "..."
            content_parts.append("")
            content_parts.append("Preview:")
            content_parts.append(preview)
        except OSError:
            pass

        content = "\n".join(content_parts)

        # Calculate relevance
        relevance = self._calculate_relevance(match, query)

        return SourceItem(
            source="files",
            type="file",
            title=title,
            content=content,
            timestamp=match["modified"],
            relevance_score=relevance,
            url=f"file://{file_path}",
            metadata={
                "path": str(file_path),
                "extension": file_path.suffix,
                "line_number": match.get("line_number"),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            },
        )

    def _calculate_relevance(
        self,
        match: dict[str, Any],
        query: str,
    ) -> float:
        """
        Calculate relevance score.

        Args:
            match: Match dictionary
            query: Original search query

        Returns:
            Relevance score (0.0 - 1.0)
        """
        base_score = 0.6
        query_lower = query.lower()

        # Filename match bonus
        filename = match["path"].name.lower()
        if query_lower in filename:
            base_score += 0.20

        # Line text match quality
        line_text = match.get("line_text", "").lower()
        if query_lower in line_text:
            base_score += 0.10

        # Recency factor
        now = datetime.now(timezone.utc)
        modified = match.get("modified", now)
        days_diff = abs((now - modified).days)
        if days_diff <= 7:
            base_score += 0.08
        elif days_diff <= 30:
            base_score += 0.04
        elif days_diff > 365:
            base_score -= 0.05

        # Extension bonus (prioritize text documents)
        ext = match["path"].suffix.lower()
        if ext in [".md", ".txt", ".org"]:
            base_score += 0.05

        return min(max(base_score, 0.0), 0.95)
