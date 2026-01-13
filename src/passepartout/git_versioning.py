"""
Git Version Manager for Notes

Provides version control capabilities for notes using Git.
Each note change is tracked as a commit with meaningful messages.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from git import Actor, InvalidGitRepositoryError, Repo
from git.exc import GitCommandError
from gitdb.exc import BadName

from src.monitoring.logger import get_logger

logger = get_logger("passepartout.git_versioning")

# Global lock for Git operations to prevent concurrent index.lock conflicts
# This is necessary when multiple NoteManager instances run in parallel threads
_git_lock = threading.Lock()


@dataclass
class NoteVersion:
    """
    Represents a version of a note

    Attributes:
        version_id: Git commit hash (short, 7 chars)
        full_hash: Full Git commit hash
        message: Commit message
        timestamp: When the version was created
        author: Who made the change
    """

    version_id: str
    full_hash: str
    message: str
    timestamp: datetime
    author: str

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "version_id": self.version_id,
            "full_hash": self.full_hash,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
        }


@dataclass
class NoteDiff:
    """
    Represents a diff between two versions of a note

    Attributes:
        note_id: The note being compared
        from_version: Source version ID
        to_version: Target version ID
        additions: Number of lines added
        deletions: Number of lines removed
        diff_text: Unified diff text
        changes: List of changed sections
    """

    note_id: str
    from_version: str
    to_version: str
    additions: int
    deletions: int
    diff_text: str
    changes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "note_id": self.note_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "additions": self.additions,
            "deletions": self.deletions,
            "diff_text": self.diff_text,
            "changes": self.changes,
        }


class GitVersionManager:
    """
    Manages Git versioning for notes

    Provides operations for:
    - Initializing/opening Git repository
    - Committing note changes
    - Listing version history
    - Retrieving specific versions
    - Computing diffs between versions
    - Restoring previous versions

    Usage:
        git_manager = GitVersionManager(notes_dir=Path("~/notes"))
        git_manager.commit("note-123.md", "Update meeting notes")
        versions = git_manager.list_versions("note-123.md")
        diff = git_manager.diff("note-123.md", "abc1234", "def5678")
    """

    def __init__(
        self,
        notes_dir: Path,
        author_name: str = "Scapin",
        author_email: str = "scapin@local",
    ):
        """
        Initialize Git version manager

        Args:
            notes_dir: Directory containing notes (will be Git repo root)
            author_name: Name for Git commits
            author_email: Email for Git commits
        """
        self.notes_dir = Path(notes_dir).expanduser().resolve()
        self.author_name = author_name
        self.author_email = author_email
        self.author = Actor(author_name, author_email)
        self.repo: Optional[Repo] = None

        self._init_repo()

    def _init_repo(self) -> None:
        """Initialize or open Git repository"""
        try:
            # Try to open existing repo
            self.repo = Repo(self.notes_dir)
            logger.info(
                "Opened existing Git repository",
                extra={"path": str(self.notes_dir)},
            )
        except InvalidGitRepositoryError:
            # Initialize new repo
            self.repo = Repo.init(self.notes_dir)
            logger.info(
                "Initialized new Git repository",
                extra={"path": str(self.notes_dir)},
            )

            # Create initial commit if repo is empty
            if not self.repo.head.is_valid():
                self._create_initial_commit()

    def _create_initial_commit(self) -> None:
        """Create initial commit with .gitignore"""
        gitignore_path = self.notes_dir / ".gitignore"
        gitignore_content = """# Scapin Notes Git Repository
# Generated files
.DS_Store
*.swp
*.swo
*~

# Vector store index (rebuilt from notes)
.vector_index/
"""
        gitignore_path.write_text(gitignore_content)

        self.repo.index.add([".gitignore"])
        self.repo.index.commit(
            "Initial commit: Setup notes repository",
            author=self.author,
            committer=self.author,
        )
        logger.info("Created initial Git commit")

    def commit(
        self,
        note_filename: str,
        message: str,
        note_title: Optional[str] = None,
    ) -> Optional[str]:
        """
        Commit changes to a note

        Args:
            note_filename: Filename of the note (e.g., "note-123.md")
            message: Commit message (will be prefixed with action)
            note_title: Optional note title for better commit messages

        Returns:
            Commit hash (short) if successful, None if no changes
        """
        if self.repo is None:
            logger.warning("Git repository not initialized")
            return None

        file_path = self.notes_dir / note_filename

        # Check if file exists and has changes
        if not file_path.exists():
            logger.warning(f"Note file not found: {note_filename}")
            return None

        # Use global lock to prevent concurrent Git index operations
        with _git_lock:
            try:
                # Stage the file
                self.repo.index.add([note_filename])

                # Check if there are staged changes
                if not self.repo.index.diff("HEAD"):
                    # Check for untracked files
                    untracked = [
                        f for f in self.repo.untracked_files if f == note_filename
                    ]
                    if not untracked:
                        logger.debug(f"No changes to commit for {note_filename}")
                        return None

                # Build commit message
                title_part = f" ({note_title})" if note_title else ""
                full_message = f"{message}{title_part}"

                # Commit
                commit = self.repo.index.commit(
                    full_message,
                    author=self.author,
                    committer=self.author,
                )

                short_hash = commit.hexsha[:7]
                logger.info(
                    "Committed note changes",
                    extra={
                        "note": note_filename,
                        "commit": short_hash,
                        "commit_message": full_message[:50],
                    },
                )
                return short_hash

            except GitCommandError as e:
                logger.error(f"Git commit failed: {e}")
                return None

    def commit_delete(
        self,
        note_filename: str,
        note_title: Optional[str] = None,
    ) -> Optional[str]:
        """
        Commit deletion of a note

        Args:
            note_filename: Filename of the deleted note
            note_title: Optional note title for commit message

        Returns:
            Commit hash if successful, None otherwise
        """
        if self.repo is None:
            return None

        # Use global lock to prevent concurrent Git index operations
        with _git_lock:
            try:
                # Stage deletion
                self.repo.index.remove([note_filename])

                # Commit
                title_part = f": {note_title}" if note_title else ""
                commit = self.repo.index.commit(
                    f"Delete note{title_part}",
                    author=self.author,
                    committer=self.author,
                )

                short_hash = commit.hexsha[:7]
                logger.info(f"Committed note deletion: {note_filename} ({short_hash})")
                return short_hash

            except GitCommandError as e:
                logger.error(f"Git delete commit failed: {e}")
                return None

    def list_versions(
        self,
        note_filename: str,
        limit: int = 50,
    ) -> list[NoteVersion]:
        """
        List version history for a note

        Args:
            note_filename: Filename of the note
            limit: Maximum number of versions to return

        Returns:
            List of NoteVersion objects, most recent first
        """
        if self.repo is None:
            return []

        versions = []

        try:
            # Get commits that touched this file
            commits = list(
                self.repo.iter_commits(
                    paths=note_filename,
                    max_count=limit,
                )
            )

            for commit in commits:
                versions.append(
                    NoteVersion(
                        version_id=commit.hexsha[:7],
                        full_hash=commit.hexsha,
                        message=commit.message.strip(),
                        timestamp=datetime.fromtimestamp(
                            commit.committed_date, tz=timezone.utc
                        ),
                        author=commit.author.name or self.author_name,
                    )
                )

            logger.debug(
                f"Listed {len(versions)} versions for {note_filename}",
            )

        except GitCommandError as e:
            logger.error(f"Failed to list versions: {e}")

        return versions

    def get_version(
        self,
        note_filename: str,
        version_id: str,
    ) -> Optional[str]:
        """
        Get note content at a specific version

        Args:
            note_filename: Filename of the note
            version_id: Git commit hash (short or full)

        Returns:
            Note content at that version, or None if not found
        """
        if self.repo is None:
            return None

        try:
            # Get the commit
            commit = self.repo.commit(version_id)

            # Get the file content at that commit
            blob = commit.tree / note_filename
            content = blob.data_stream.read().decode("utf-8")

            logger.debug(f"Retrieved version {version_id} of {note_filename}")
            return content

        except (KeyError, GitCommandError, BadName) as e:
            logger.warning(f"Version not found: {version_id} for {note_filename}: {e}")
            return None

    def diff(
        self,
        note_filename: str,
        from_version: str,
        to_version: str,
    ) -> Optional[NoteDiff]:
        """
        Get diff between two versions of a note

        Args:
            note_filename: Filename of the note
            from_version: Source version ID (older)
            to_version: Target version ID (newer)

        Returns:
            NoteDiff object or None if versions not found
        """
        if self.repo is None:
            return None

        try:
            # Get commits
            from_commit = self.repo.commit(from_version)
            to_commit = self.repo.commit(to_version)

            # Generate diff
            diff_index = from_commit.diff(to_commit, paths=[note_filename])

            if not diff_index:
                # No changes between versions for this file
                return NoteDiff(
                    note_id=note_filename.replace(".md", ""),
                    from_version=from_version,
                    to_version=to_version,
                    additions=0,
                    deletions=0,
                    diff_text="",
                    changes=[],
                )

            # Get unified diff text
            diff_text = self.repo.git.diff(
                from_version,
                to_version,
                "--",
                note_filename,
                unified=3,
            )

            # Parse additions/deletions
            additions = 0
            deletions = 0
            changes = []

            for line in diff_text.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

            # Parse change sections
            current_section = None
            for line in diff_text.split("\n"):
                if line.startswith("@@"):
                    if current_section:
                        changes.append(current_section)
                    current_section = {
                        "header": line,
                        "lines": [],
                    }
                elif current_section:
                    current_section["lines"].append(line)

            if current_section:
                changes.append(current_section)

            note_id = note_filename.replace(".md", "")
            return NoteDiff(
                note_id=note_id,
                from_version=from_version,
                to_version=to_version,
                additions=additions,
                deletions=deletions,
                diff_text=diff_text,
                changes=changes,
            )

        except (GitCommandError, BadName) as e:
            logger.error(f"Failed to generate diff: {e}")
            return None

    def restore(
        self,
        note_filename: str,
        version_id: str,
    ) -> bool:
        """
        Restore a note to a previous version

        This creates a new commit with the restored content,
        preserving the full history.

        Args:
            note_filename: Filename of the note
            version_id: Version to restore to

        Returns:
            True if successful, False otherwise
        """
        if self.repo is None:
            return False

        try:
            # Get content at the specified version
            content = self.get_version(note_filename, version_id)
            if content is None:
                logger.warning(f"Cannot restore: version {version_id} not found")
                return False

            # Write the content to the file
            file_path = self.notes_dir / note_filename
            file_path.write_text(content, encoding="utf-8")

            # Commit the restoration
            self.repo.index.add([note_filename])
            commit = self.repo.index.commit(
                f"Restore to version {version_id}",
                author=self.author,
                committer=self.author,
            )

            logger.info(
                f"Restored {note_filename} to version {version_id} "
                f"(new commit: {commit.hexsha[:7]})"
            )
            return True

        except (GitCommandError, BadName) as e:
            logger.error(f"Failed to restore version: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Get repository statistics

        Returns:
            Dictionary with repo stats
        """
        if self.repo is None:
            return {"initialized": False}

        try:
            commit_count = len(list(self.repo.iter_commits()))
            return {
                "initialized": True,
                "path": str(self.notes_dir),
                "commit_count": commit_count,
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": len(self.repo.untracked_files),
            }
        except GitCommandError:
            return {"initialized": True, "path": str(self.notes_dir)}


# Singleton instance
_git_manager: Optional[GitVersionManager] = None


def get_git_manager(notes_dir: Optional[Path] = None) -> GitVersionManager:
    """
    Get or create singleton GitVersionManager instance

    Args:
        notes_dir: Directory for notes (default: ~/Documents/Notes)

    Returns:
        GitVersionManager singleton instance
    """
    global _git_manager

    if _git_manager is None:
        if notes_dir is None:
            notes_dir = Path.home() / "Documents" / "Notes"

        _git_manager = GitVersionManager(notes_dir)

    return _git_manager
