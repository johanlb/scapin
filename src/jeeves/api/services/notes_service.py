"""
Notes Service

Async wrapper around NoteManager for API use.
Provides CRUD operations, search, and tree navigation.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config_manager import ScapinConfig
from src.jeeves.api.models.notes import (
    DiffChangeSection,
    EntityResponse,
    FolderCreateResponse,
    FolderListResponse,
    FolderNode,
    NoteDiffResponse,
    NoteLinksResponse,
    NoteResponse,
    NoteSearchResponse,
    NoteSearchResult,
    NotesTreeResponse,
    NoteSyncStatus,
    NoteVersionContentResponse,
    NoteVersionResponse,
    NoteVersionsResponse,
    WikilinkResponse,
)
from src.monitoring.logger import get_logger
from src.passepartout.git_versioning import GitVersionManager
from src.passepartout.note_manager import Note, NoteManager

logger = get_logger("jeeves.api.services.notes")

# Security: Git version_id pattern (7-40 hex chars for short/full commit hashes)
GIT_VERSION_ID_PATTERN = re.compile(r"^[a-fA-F0-9]{7,40}$")


def _validate_version_id(version_id: str) -> None:
    """Validate git version_id to prevent command injection.

    Args:
        version_id: Git commit hash (7-40 hex characters)

    Raises:
        ValueError: If version_id contains invalid characters
    """
    if not GIT_VERSION_ID_PATTERN.match(version_id):
        raise ValueError(
            "Invalid version_id format: must be 7-40 hexadecimal characters"
        )


def _validate_folder_path(path: str, base_dir: Path) -> Path:
    """Validate folder path to prevent path traversal attacks.

    Args:
        path: User-provided folder path
        base_dir: Base directory that path must resolve within

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path attempts to traverse outside base_dir
    """
    # Normalize and resolve the path
    clean_path = path.strip().strip("/")

    # Check for path traversal attempts
    if ".." in clean_path or clean_path.startswith("/"):
        raise ValueError("Invalid path: path traversal not allowed")

    # Resolve to absolute path and verify it's within base_dir
    resolved = (base_dir / clean_path).resolve()
    base_resolved = base_dir.resolve()

    # Ensure resolved path is within base directory
    try:
        resolved.relative_to(base_resolved)
    except ValueError as e:
        raise ValueError("Invalid path: must be within notes directory") from e

    return resolved


def _note_to_response(note: Note) -> NoteResponse:
    """Convert Note domain model to API response"""
    # Generate excerpt from content
    content = note.content.strip()
    excerpt = content[:200] + "..." if len(content) > 200 else content
    # Remove markdown headers for cleaner excerpt
    excerpt = re.sub(r"^#+\s+", "", excerpt)

    # Extract path from metadata or use default
    path = note.metadata.get("path", "")
    pinned = note.metadata.get("pinned", False)

    return NoteResponse(
        note_id=note.note_id,
        title=note.title,
        content=note.content,
        excerpt=excerpt,
        path=path,
        tags=note.tags,
        entities=[
            EntityResponse(type=e.type, value=e.value, confidence=e.confidence)
            for e in note.entities
        ],
        created_at=note.created_at,
        updated_at=note.updated_at,
        pinned=pinned,
        metadata=note.metadata,
    )


def _build_folder_tree(notes: list[Note]) -> list[FolderNode]:
    """Build hierarchical folder tree from notes (sorted alphabetically like Apple Notes)"""
    # Count notes per path
    path_counts: dict[str, int] = defaultdict(int)
    for note in notes:
        path = note.metadata.get("path", "")
        if path:
            # Count for this path and all parent paths
            parts = path.split("/")
            for i in range(len(parts)):
                partial_path = "/".join(parts[: i + 1])
                path_counts[partial_path] += 1

    # Build tree structure
    root_folders: dict[str, dict[str, Any]] = {}

    for path, count in sorted(path_counts.items()):
        parts = path.split("/")
        current = root_folders

        for i, part in enumerate(parts):
            current_path = "/".join(parts[: i + 1])
            if part not in current:
                current[part] = {
                    "name": part,
                    "path": current_path,
                    "note_count": 0,
                    "children": {},
                }
            # Only set count at the deepest level
            if i == len(parts) - 1:
                current[part]["note_count"] = count
            current = current[part]["children"]

    # Convert to FolderNode objects (sorted alphabetically case-insensitive)
    def dict_to_folder(d: dict[str, Any]) -> FolderNode:
        sorted_children = sorted(
            d["children"].values(),
            key=lambda x: x["name"].lower()
        )
        return FolderNode(
            name=d["name"],
            path=d["path"],
            note_count=d["note_count"],
            children=[dict_to_folder(c) for c in sorted_children],
        )

    # Sort root folders alphabetically (case-insensitive)
    sorted_roots = sorted(root_folders.values(), key=lambda x: x["name"].lower())
    return [dict_to_folder(f) for f in sorted_roots]


def _extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilinks]] from content"""
    pattern = r"\[\[([^\]]+)\]\]"
    return re.findall(pattern, content)


@dataclass
class NotesService:
    """
    Notes service for API endpoints

    Wraps NoteManager with API-specific logic.
    Provides CRUD operations, search, and Git versioning.
    """

    config: ScapinConfig
    _note_manager: NoteManager | None = field(default=None, init=False)
    _git_manager: GitVersionManager | None = field(default=None, init=False)

    def _get_manager(self) -> NoteManager:
        """Get or create NoteManager instance"""
        if self._note_manager is None:
            # Use configured notes directory from config or default
            notes_dir = getattr(self.config, "notes_dir", None)
            if notes_dir is None:
                notes_dir = Path.home() / "Documents" / "Notes"
            else:
                notes_dir = Path(notes_dir)
            self._note_manager = NoteManager(notes_dir, auto_index=True)
        return self._note_manager

    def _get_git_manager(self) -> GitVersionManager:
        """Get or create GitVersionManager instance"""
        if self._git_manager is None:
            # Use same notes directory as NoteManager
            notes_dir = getattr(self.config, "notes_dir", None)
            if notes_dir is None:
                notes_dir = Path.home() / "Documents" / "Notes"
            else:
                notes_dir = Path(notes_dir)
            self._git_manager = GitVersionManager(notes_dir)
        return self._git_manager

    async def get_notes_tree(
        self,
        recent_limit: int = 10,
    ) -> NotesTreeResponse:
        """
        Get notes organized in folder tree

        Args:
            recent_limit: Number of recent notes to include

        Returns:
            NotesTreeResponse with folders, pinned, and recent notes
        """
        logger.info("Building notes tree")
        manager = self._get_manager()

        # Get all notes
        all_notes = manager.get_all_notes()

        # Build folder tree
        folders = _build_folder_tree(all_notes)

        # Get pinned notes
        pinned = [n for n in all_notes if n.metadata.get("pinned", False)]
        pinned_responses = [_note_to_response(n) for n in pinned]

        # Get recent notes (sorted by updated_at)
        sorted_notes = sorted(all_notes, key=lambda n: n.updated_at, reverse=True)
        recent = sorted_notes[:recent_limit]
        recent_responses = [_note_to_response(n) for n in recent]

        logger.info(
            f"Notes tree built: {len(all_notes)} total, "
            f"{len(pinned)} pinned, {len(folders)} root folders"
        )

        return NotesTreeResponse(
            folders=folders,
            pinned=pinned_responses,
            recent=recent_responses,
            total_notes=len(all_notes),
        )

    async def list_notes(
        self,
        path: str | None = None,
        tags: list[str] | None = None,
        pinned_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[NoteResponse], int]:
        """
        List notes with optional filtering

        Args:
            path: Filter by folder path
            tags: Filter by tags
            pinned_only: Only return pinned notes
            limit: Maximum notes to return
            offset: Pagination offset

        Returns:
            Tuple of (notes, total_count)
        """
        logger.info(
            f"Listing notes (path={path}, tags={tags}, pinned={pinned_only})"
        )
        manager = self._get_manager()

        # Get all notes
        all_notes = manager.get_all_notes()

        # Apply filters
        filtered = all_notes
        if path:
            filtered = [
                n for n in filtered
                if n.metadata.get("path", "").startswith(path)
            ]
        if tags:
            tag_set = set(tags)
            filtered = [n for n in filtered if tag_set.intersection(n.tags)]
        if pinned_only:
            filtered = [n for n in filtered if n.metadata.get("pinned", False)]

        # Sort by updated_at descending
        filtered = sorted(filtered, key=lambda n: n.updated_at, reverse=True)

        # Paginate
        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        return [_note_to_response(n) for n in paginated], total

    async def get_note(self, note_id: str) -> NoteResponse | None:
        """
        Get a single note by ID

        Args:
            note_id: Note identifier

        Returns:
            NoteResponse or None if not found
        """
        logger.info(f"Getting note: {note_id}")
        manager = self._get_manager()

        note = manager.get_note(note_id)
        if note is None:
            return None

        return _note_to_response(note)

    async def create_note(
        self,
        title: str,
        content: str,
        path: str = "",
        tags: list[str] | None = None,
        pinned: bool = False,
    ) -> NoteResponse:
        """
        Create a new note

        Args:
            title: Note title
            content: Note content (Markdown)
            path: Folder path
            tags: Tags
            pinned: Whether to pin the note

        Returns:
            Created NoteResponse
        """
        logger.info(f"Creating note: {title} (path={path})")
        manager = self._get_manager()

        # Create with metadata
        metadata = {"path": path, "pinned": pinned}
        note_id = manager.create_note(
            title=title,
            content=content,
            tags=tags or [],
            metadata=metadata,
        )

        # Fetch and return
        note = manager.get_note(note_id)
        if note is None:
            raise RuntimeError(f"Failed to retrieve created note: {note_id}")

        logger.info(f"Note created: {note_id}")
        return _note_to_response(note)

    async def update_note(
        self,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        path: str | None = None,
        tags: list[str] | None = None,
        pinned: bool | None = None,
    ) -> NoteResponse | None:
        """
        Update an existing note

        Args:
            note_id: Note identifier
            title: New title
            content: New content
            path: New folder path
            tags: New tags
            pinned: Pin/unpin

        Returns:
            Updated NoteResponse or None if not found
        """
        logger.info(f"Updating note: {note_id}")
        manager = self._get_manager()

        # Get existing note
        note = manager.get_note(note_id)
        if note is None:
            return None

        # Build metadata updates
        metadata_updates: dict[str, Any] = {}
        if path is not None:
            metadata_updates["path"] = path
        if pinned is not None:
            metadata_updates["pinned"] = pinned

        # Update
        success = manager.update_note(
            note_id=note_id,
            title=title,
            content=content,
            tags=tags,
            metadata=metadata_updates if metadata_updates else None,
        )

        if not success:
            return None

        # Fetch updated note
        updated = manager.get_note(note_id)
        if updated is None:
            return None

        logger.info(f"Note updated: {note_id}")
        return _note_to_response(updated)

    async def delete_note(self, note_id: str) -> bool:
        """
        Delete a note

        Args:
            note_id: Note identifier

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting note: {note_id}")
        manager = self._get_manager()

        result = manager.delete_note(note_id)
        if result:
            logger.info(f"Note deleted: {note_id}")
        return result

    async def search_notes(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> NoteSearchResponse:
        """
        Semantic search for notes

        Args:
            query: Search query
            tags: Optional tag filter
            limit: Maximum results

        Returns:
            NoteSearchResponse with ranked results
        """
        logger.info(f"Searching notes: '{query}' (tags={tags})")
        manager = self._get_manager()

        # Search with scores
        results = manager.search_notes(
            query=query,
            top_k=limit,
            tags=tags,
            return_scores=True,
        )

        # Build response
        search_results = []
        for note, score in results:  # type: ignore
            response = _note_to_response(note)
            search_results.append(
                NoteSearchResult(
                    note=response,
                    score=score,
                    highlights=[],  # TODO: Generate highlights from matches
                )
            )

        logger.info(f"Search returned {len(search_results)} results")
        return NoteSearchResponse(
            query=query,
            results=search_results,
            total=len(search_results),
        )

    async def get_note_links(self, note_id: str) -> NoteLinksResponse | None:
        """
        Get bidirectional links for a note

        Args:
            note_id: Note identifier

        Returns:
            NoteLinksResponse with incoming and outgoing links
        """
        logger.info(f"Getting links for note: {note_id}")
        manager = self._get_manager()

        note = manager.get_note(note_id)
        if note is None:
            return None

        # Get all notes once for both operations
        all_notes = manager.get_all_notes()

        # Build title-to-note mapping for outgoing link resolution
        title_to_note = {n.title.lower(): n for n in all_notes}

        # Extract and resolve outgoing wikilinks
        outgoing_texts = _extract_wikilinks(note.content)
        outgoing: list[WikilinkResponse] = []
        for text in outgoing_texts:
            target = title_to_note.get(text.lower())
            outgoing.append(
                WikilinkResponse(
                    text=text,
                    target_id=target.note_id if target else None,
                    target_title=target.title if target else None,
                    exists=target is not None,
                )
            )

        # Find incoming links (notes that link to this one)
        # Pre-compute lowercase title for comparison
        note_title_lower = note.title.lower()
        incoming: list[WikilinkResponse] = []
        for other in all_notes:
            if other.note_id == note_id:
                continue
            other_links = _extract_wikilinks(other.content)
            # Use set for O(1) lookup instead of list comprehension
            if note_title_lower in {link.lower() for link in other_links}:
                incoming.append(
                    WikilinkResponse(
                        text=note.title,
                        target_id=other.note_id,
                        target_title=other.title,
                        exists=True,
                    )
                )

        return NoteLinksResponse(
            note_id=note_id,
            outgoing=outgoing,
            incoming=incoming,
        )

    async def toggle_pin(self, note_id: str) -> NoteResponse | None:
        """
        Toggle pin status for a note

        Args:
            note_id: Note identifier

        Returns:
            Updated NoteResponse or None if not found
        """
        manager = self._get_manager()
        note = manager.get_note(note_id)
        if note is None:
            return None

        current_pinned = note.metadata.get("pinned", False)
        return await self.update_note(note_id, pinned=not current_pinned)

    # =========================================================================
    # Git Versioning Methods
    # =========================================================================

    async def list_versions(
        self,
        note_id: str,
        limit: int = 50,
    ) -> NoteVersionsResponse | None:
        """
        List version history for a note

        Args:
            note_id: Note identifier
            limit: Maximum versions to return

        Returns:
            NoteVersionsResponse or None if note not found
        """
        logger.info(f"Listing versions for note: {note_id}")
        manager = self._get_manager()

        # Verify note exists
        note = manager.get_note(note_id)
        if note is None:
            return None

        git_manager = self._get_git_manager()
        filename = f"{note_id}.md"
        versions = git_manager.list_versions(filename, limit=limit)

        return NoteVersionsResponse(
            note_id=note_id,
            versions=[
                NoteVersionResponse(
                    version_id=v.version_id,
                    full_hash=v.full_hash,
                    message=v.message,
                    timestamp=v.timestamp,
                    author=v.author,
                )
                for v in versions
            ],
            total=len(versions),
        )

    async def get_version(
        self,
        note_id: str,
        version_id: str,
    ) -> NoteVersionContentResponse | None:
        """
        Get note content at a specific version

        Args:
            note_id: Note identifier
            version_id: Git commit hash

        Returns:
            NoteVersionContentResponse or None if not found

        Raises:
            ValueError: If version_id is invalid
        """
        # Security: Validate version_id to prevent command injection
        _validate_version_id(version_id)

        logger.info(f"Getting version {version_id} of note {note_id}")
        git_manager = self._get_git_manager()

        filename = f"{note_id}.md"
        content = git_manager.get_version(filename, version_id)

        if content is None:
            return None

        # Get version metadata
        versions = git_manager.list_versions(filename, limit=100)
        version_info = next(
            (v for v in versions if v.version_id == version_id[:7]),
            None,
        )

        if version_info is None:
            # Fallback timestamp
            from datetime import datetime, timezone

            timestamp = datetime.now(timezone.utc)
        else:
            timestamp = version_info.timestamp

        return NoteVersionContentResponse(
            note_id=note_id,
            version_id=version_id,
            content=content,
            timestamp=timestamp,
        )

    async def diff_versions(
        self,
        note_id: str,
        from_version: str,
        to_version: str,
    ) -> NoteDiffResponse | None:
        """
        Get diff between two versions of a note

        Args:
            note_id: Note identifier
            from_version: Source version (older)
            to_version: Target version (newer)

        Returns:
            NoteDiffResponse or None if versions not found

        Raises:
            ValueError: If version IDs are invalid
        """
        # Security: Validate version IDs to prevent command injection
        _validate_version_id(from_version)
        _validate_version_id(to_version)

        logger.info(f"Diffing note {note_id}: {from_version} -> {to_version}")
        git_manager = self._get_git_manager()

        filename = f"{note_id}.md"
        diff = git_manager.diff(filename, from_version, to_version)

        if diff is None:
            return None

        return NoteDiffResponse(
            note_id=note_id,
            from_version=from_version,
            to_version=to_version,
            additions=diff.additions,
            deletions=diff.deletions,
            diff_text=diff.diff_text,
            changes=[
                DiffChangeSection(
                    header=change["header"],
                    lines=change["lines"],
                )
                for change in diff.changes
            ],
        )

    async def restore_version(
        self,
        note_id: str,
        version_id: str,
    ) -> NoteResponse | None:
        """
        Restore a note to a previous version

        Args:
            note_id: Note identifier
            version_id: Version to restore to

        Returns:
            Updated NoteResponse or None if failed

        Raises:
            ValueError: If version_id is invalid
        """
        # Security: Validate version_id to prevent command injection
        _validate_version_id(version_id)

        logger.info(f"Restoring note {note_id} to version {version_id}")
        manager = self._get_manager()
        git_manager = self._get_git_manager()

        # Verify note exists
        note = manager.get_note(note_id)
        if note is None:
            return None

        filename = f"{note_id}.md"
        success = git_manager.restore(filename, version_id)

        if not success:
            return None

        # Clear cache and reload note
        if note_id in manager._note_cache:
            del manager._note_cache[note_id]

        # Re-index in vector store (content changed)
        updated_note = manager.get_note(note_id)
        if updated_note:
            # Update vector store
            manager.vector_store.remove(note_id)
            search_text = f"{updated_note.title}\n\n{updated_note.content}"
            manager.vector_store.add(
                doc_id=note_id,
                text=search_text,
                metadata={
                    "title": updated_note.title,
                    "tags": updated_note.tags,
                    "updated_at": updated_note.updated_at.isoformat(),
                    "entities": [e.value for e in updated_note.entities],
                },
            )
            return _note_to_response(updated_note)

        return None

    async def get_sync_status(self) -> NoteSyncStatus:
        """
        Get Apple Notes sync status

        Returns:
            NoteSyncStatus with last sync info
        """
        # TODO: Implement Apple Notes sync integration
        return NoteSyncStatus(
            last_sync=None,
            syncing=False,
            notes_synced=0,
            errors=[],
        )

    async def sync_apple_notes(self) -> NoteSyncStatus:
        """
        Trigger Apple Notes sync (bidirectional)

        Returns:
            NoteSyncStatus with sync results
        """

        from src.integrations.apple.notes_models import ConflictResolution
        from src.integrations.apple.notes_sync import AppleNotesSync, SyncDirection

        logger.info("Starting Apple Notes sync...")

        try:
            # Get notes directory from NoteManager
            manager = self._get_manager()
            notes_dir = manager.notes_dir

            # Create sync service
            sync_service = AppleNotesSync(
                notes_dir=notes_dir,
                conflict_resolution=ConflictResolution.NEWER_WINS,
            )

            # Perform bidirectional sync
            result = sync_service.sync(direction=SyncDirection.BIDIRECTIONAL)

            # Convert result to NoteSyncStatus
            errors = result.errors.copy()
            if result.conflicts:
                for conflict in result.conflicts:
                    errors.append(f"Conflict: {conflict.reason}")

            logger.info(
                f"Apple Notes sync completed: "
                f"{result.total_synced} synced, "
                f"{len(result.skipped)} skipped, "
                f"{len(result.errors)} errors"
            )

            return NoteSyncStatus(
                last_sync=result.completed_at or datetime.now(timezone.utc),
                syncing=False,
                notes_synced=result.total_synced,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"Apple Notes sync failed: {e}", exc_info=True)
            return NoteSyncStatus(
                last_sync=None,
                syncing=False,
                notes_synced=0,
                errors=[f"Sync failed: {str(e)}"],
            )

    # =========================================================================
    # Folder Management Methods
    # =========================================================================

    async def create_folder(self, path: str) -> FolderCreateResponse:
        """
        Create a new folder in the notes directory

        Args:
            path: Folder path (e.g., 'Clients/ABC')

        Returns:
            FolderCreateResponse with created folder info

        Raises:
            ValueError: If path is invalid or attempts path traversal
        """
        logger.info(f"Creating folder: {path}")
        manager = self._get_manager()

        # Security: Validate path to prevent path traversal attacks
        folder_path = _validate_folder_path(path, manager.notes_dir)

        # Normalize path for response
        clean_path = path.strip().strip("/")

        # Check if folder already exists
        existed = folder_path.exists()

        # Create folder (will succeed even if exists)
        absolute_path = manager.create_folder(path)

        logger.info(f"Folder {'already existed' if existed else 'created'}: {clean_path}")
        return FolderCreateResponse(
            path=clean_path,
            absolute_path=str(absolute_path),
            created=not existed,
        )

    async def list_folders(self) -> FolderListResponse:
        """
        List all folders in the notes directory

        Returns:
            FolderListResponse with folder paths
        """
        logger.info("Listing folders")
        manager = self._get_manager()

        folders = manager.list_folders()
        return FolderListResponse(
            folders=folders,
            total=len(folders),
        )
