"""
Notes Service

Async wrapper around NoteManager for API use.
Provides CRUD operations, search, and tree navigation.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.config_manager import ScapinConfig
from src.jeeves.api.models.notes import (
    EntityResponse,
    FolderNode,
    NoteLinksResponse,
    NoteResponse,
    NoteSearchResponse,
    NoteSearchResult,
    NotesTreeResponse,
    NoteSyncStatus,
    WikilinkResponse,
)
from src.monitoring.logger import get_logger
from src.passepartout.note_manager import Note, NoteManager

logger = get_logger("jeeves.api.services.notes")


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
    """Build hierarchical folder tree from notes"""
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

    # Convert to FolderNode objects
    def dict_to_folder(d: dict[str, Any]) -> FolderNode:
        return FolderNode(
            name=d["name"],
            path=d["path"],
            note_count=d["note_count"],
            children=[dict_to_folder(c) for c in d["children"].values()],
        )

    return [dict_to_folder(f) for f in root_folders.values()]


def _extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilinks]] from content"""
    pattern = r"\[\[([^\]]+)\]\]"
    return re.findall(pattern, content)


@dataclass
class NotesService:
    """
    Notes service for API endpoints

    Wraps NoteManager with API-specific logic.
    """

    config: ScapinConfig
    _note_manager: NoteManager | None = field(default=None, init=False)

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
        Trigger Apple Notes sync

        Returns:
            NoteSyncStatus with sync results
        """
        # TODO: Implement Apple Notes sync
        logger.info("Apple Notes sync requested (not yet implemented)")
        return NoteSyncStatus(
            last_sync=None,
            syncing=False,
            notes_synced=0,
            errors=["Apple Notes sync not yet implemented"],
        )
