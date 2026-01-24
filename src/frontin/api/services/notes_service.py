"""
Notes Service

Async wrapper around NoteManager for API use.
Provides CRUD operations, search, and tree navigation.
"""

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.frontin.api.models.notes import HygieneResultResponse

from src.core.config_manager import ScapinConfig
from src.frontin.api.models.notes import (
    DiffChangeSection,
    EnrichmentItemResponse,
    EnrichmentResultResponse,
    EntityResponse,
    FolderCreateResponse,
    FolderListResponse,
    FolderNode,
    NoteDiffResponse,
    NoteLinksResponse,
    NoteMetadataResponse,
    NoteMoveResponse,
    NoteResponse,
    NoteSearchResponse,
    NoteSearchResult,
    NotesTreeResponse,
    NoteSyncStatus,
    NoteVersionContentResponse,
    NoteVersionResponse,
    NoteVersionsResponse,
    RetoucheActionPreview,
    RetouchePreviewResponse,
    RetoucheQueueItem,
    RetoucheQueueResponse,
    RetoucheRollbackResponse,
    WikilinkResponse,
)
from src.monitoring.logger import get_logger
from src.passepartout.git_versioning import GitVersionManager
from src.passepartout.note_manager import Note, NoteManager

logger = get_logger("frontin.api.services.notes")

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
        raise ValueError("Invalid version_id format: must be 7-40 hexadecimal characters")


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


def _note_to_response(note: Note, deleted_at: Optional[str] = None) -> NoteResponse:
    """Convert Note domain model to API response

    Args:
        note: Note domain model
        deleted_at: Optional ISO timestamp of when note was deleted (for trash notes)
    """
    # Generate excerpt from content
    content = note.content.strip()
    excerpt = content[:200] + "..." if len(content) > 200 else content
    # Remove markdown headers for cleaner excerpt
    excerpt = re.sub(r"^#+\s+", "", excerpt)

    # Extract path from metadata or use default
    path = note.metadata.get("path", "")
    pinned = note.metadata.get("pinned", False)

    # Ensure title is a string (YAML can parse numeric-only titles as int)
    title = str(note.title) if note.title is not None else ""

    # Build metadata, adding deleted_at if present
    metadata = dict(note.metadata)
    if deleted_at:
        metadata["deleted_at"] = deleted_at

    return NoteResponse(
        note_id=note.note_id,
        title=title,
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
        metadata=metadata,
    )


def _summary_to_response(summary: dict[str, Any]) -> NoteResponse:
    """Convert lightweight summary to API response (FAST - no file read)

    This creates a NoteResponse from cached summary data without reading
    the full note file. Content is set to excerpt since full content
    should be loaded via get_note() when needed.
    """
    title = str(summary.get("title", "")) if summary.get("title") else ""
    path = summary.get("path", "")
    tags = summary.get("tags", [])
    pinned = summary.get("pinned", False)

    # Parse dates from ISO strings
    created_str = summary.get("created_at", "")
    updated_str = summary.get("updated_at", "")

    try:
        created_at = (
            datetime.fromisoformat(created_str) if created_str else datetime.now(timezone.utc)
        )
    except (ValueError, TypeError):
        created_at = datetime.now(timezone.utc)

    try:
        updated_at = (
            datetime.fromisoformat(updated_str) if updated_str else datetime.now(timezone.utc)
        )
    except (ValueError, TypeError):
        updated_at = datetime.now(timezone.utc)

    # For list views, we don't need full content - excerpt is enough
    # Full content is loaded via get_note() when user selects a note
    excerpt = summary.get("excerpt", "")

    return NoteResponse(
        note_id=summary["note_id"],
        title=title,
        content=excerpt,  # Use excerpt as placeholder content for list views
        excerpt=excerpt,
        path=path,
        tags=tags,
        entities=[],  # Entities loaded with full note
        created_at=created_at,
        updated_at=updated_at,
        pinned=pinned,
        metadata={},  # Minimal metadata for list views
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

    return _build_folder_tree_from_path_counts(path_counts)


def _build_folder_tree_from_summaries(summaries: list[dict[str, Any]]) -> list[FolderNode]:
    """Build hierarchical folder tree from note summaries (optimized version)"""
    # Count notes per path
    path_counts: dict[str, int] = defaultdict(int)
    for summary in summaries:
        path = summary.get("path", "")
        if path:
            # Count for this path and all parent paths
            parts = path.split("/")
            for i in range(len(parts)):
                partial_path = "/".join(parts[: i + 1])
                path_counts[partial_path] += 1

    return _build_folder_tree_from_path_counts(path_counts)


def _build_folder_tree_from_path_counts(path_counts: dict[str, int]) -> list[FolderNode]:
    """Build folder tree structure from path counts"""
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
        sorted_children = sorted(d["children"].values(), key=lambda x: x["name"].lower())
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
    _note_manager: Optional[NoteManager] = field(default=None, init=False)
    _git_manager: Optional[GitVersionManager] = field(default=None, init=False)

    def _get_manager(self) -> NoteManager:
        """Get or create NoteManager instance (uses singleton)"""
        if self._note_manager is None:
            from src.passepartout.note_manager import get_note_manager

            # Use singleton for consistent index across all services
            self._note_manager = get_note_manager()
        return self._note_manager

    def _get_git_manager(self) -> GitVersionManager:
        """Get or create GitVersionManager instance"""
        if self._git_manager is None:
            # Use same notes directory as NoteManager
            notes_dir = self.config.storage.notes_path
            self._git_manager = GitVersionManager(notes_dir)
        return self._git_manager

    async def get_notes_tree(
        self,
        recent_limit: int = 10,
    ) -> NotesTreeResponse:
        """
        Get notes organized in folder tree (ULTRA-FAST)

        Uses lightweight summaries for EVERYTHING (no file reads).
        Full note content is loaded when user selects a note.

        CRITICAL: Notes folder is on iCloud - file reads are ~1.6s each!

        Args:
            recent_limit: Number of recent notes to include

        Returns:
            NotesTreeResponse with folders, pinned, and recent notes
        """
        logger.info("Building notes tree (optimized)")
        manager = self._get_manager()

        # OPTIMIZATION: Use lightweight summaries for everything (no file reads!)
        # Run in thread pool to avoid blocking event loop (iCloud I/O can be slow)
        summaries = await asyncio.to_thread(manager.get_notes_summary)
        total_notes = len(summaries)

        # Build folder tree from summaries (very fast)
        folders = _build_folder_tree_from_summaries(summaries)

        # Get pinned notes from summaries (ULTRA-FAST - no file read!)
        pinned_summaries = [s for s in summaries if s.get("pinned", False)]
        pinned_responses = [_summary_to_response(s) for s in pinned_summaries]

        # Get recent notes from summaries (sorted by updated_at) - ULTRA-FAST!
        def safe_updated_at(summary: dict[str, Any]) -> datetime:
            dt_str = summary.get("updated_at")
            if not dt_str:
                return datetime.min.replace(tzinfo=timezone.utc)
            try:
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                return datetime.min.replace(tzinfo=timezone.utc)

        sorted_summaries = sorted(summaries, key=safe_updated_at, reverse=True)
        recent_summaries = sorted_summaries[:recent_limit]
        recent_responses = [_summary_to_response(s) for s in recent_summaries]

        logger.info(
            f"Notes tree built: {total_notes} total, "
            f"{len(pinned_responses)} pinned, {len(folders)} root folders"
        )

        return NotesTreeResponse(
            folders=folders,
            pinned=pinned_responses,
            recent=recent_responses,
            total_notes=total_notes,
        )

    async def list_notes(
        self,
        path: Optional[str] = None,
        tags: Optional[list[str]] = None,
        pinned_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[NoteResponse], int]:
        """
        List notes with optional filtering (OPTIMIZED)

        Uses lightweight summaries for filtering and pagination,
        only loads full notes for the final result set.

        Args:
            path: Filter by folder path
            tags: Filter by tags
            pinned_only: Only return pinned notes
            limit: Maximum notes to return
            offset: Pagination offset

        Returns:
            Tuple of (notes, total_count)
        """
        logger.info(f"Listing notes (path={path}, tags={tags}, pinned={pinned_only})")
        manager = self._get_manager()

        # OPTIMIZATION: Use lightweight summaries for filtering
        # Run in thread pool to avoid blocking event loop
        summaries = await asyncio.to_thread(manager.get_notes_summary)

        # Apply filters on summaries
        filtered = summaries
        if path:
            filtered = [s for s in filtered if s.get("path", "").startswith(path)]
        if tags:
            tag_set = set(tags)
            filtered = [s for s in filtered if tag_set.intersection(s.get("tags", []))]
        if pinned_only:
            filtered = [s for s in filtered if s.get("pinned", False)]

        # Sort by updated_at descending
        def safe_dt(summary: dict[str, Any]) -> datetime:
            dt_str = summary.get("updated_at")
            if not dt_str:
                return datetime.min.replace(tzinfo=timezone.utc)
            try:
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                return datetime.min.replace(tzinfo=timezone.utc)

        filtered = sorted(filtered, key=safe_dt, reverse=True)

        # Paginate on summaries
        total = len(filtered)
        paginated_summaries = filtered[offset : offset + limit]

        # OPTIMIZATION: Use summaries directly for list views (no file I/O)
        # Full note content is loaded via get_note() when user selects a note
        return [_summary_to_response(s) for s in paginated_summaries], total

    async def get_note(self, note_id: str) -> Optional[NoteResponse]:
        """
        Get a single note by ID

        Args:
            note_id: Note identifier

        Returns:
            NoteResponse or None if not found
        """
        logger.info(f"Getting note: {note_id}")
        manager = self._get_manager()

        # Run in thread pool to avoid blocking event loop (iCloud I/O can be slow)
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        return _note_to_response(note)

    async def create_note(
        self,
        title: str,
        content: str,
        path: str = "",
        tags: Optional[list[str]] = None,
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

        # Create with metadata - run in thread pool for iCloud I/O
        metadata = {"path": path, "pinned": pinned}
        note_id = await asyncio.to_thread(
            manager.create_note,
            title=title,
            content=content,
            tags=tags or [],
            metadata=metadata,
        )

        # Fetch and return
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            raise RuntimeError(f"Failed to retrieve created note: {note_id}")

        logger.info(f"Note created: {note_id}")
        return _note_to_response(note)

    async def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        path: Optional[str] = None,
        tags: Optional[list[str]] = None,
        pinned: Optional[bool] = None,
    ) -> Optional[NoteResponse]:
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

        # Get existing note - run in thread pool for iCloud I/O
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        # Build metadata updates
        metadata_updates: dict[str, Any] = {}
        if path is not None:
            metadata_updates["path"] = path
        if pinned is not None:
            metadata_updates["pinned"] = pinned

        # Update - run in thread pool for iCloud I/O
        success = await asyncio.to_thread(
            manager.update_note,
            note_id=note_id,
            title=title,
            content=content,
            tags=tags,
            metadata=metadata_updates if metadata_updates else None,
        )

        if not success:
            return None

        # Fetch updated note - run in thread pool for iCloud I/O
        updated = await asyncio.to_thread(manager.get_note, note_id)
        if updated is None:
            return None

        logger.info(f"Note updated: {note_id}")
        return _note_to_response(updated)

    async def update_note_metadata(
        self,
        note_id: str,
        note_type: str | None = None,
        importance: str | None = None,
        auto_enrich: bool | None = None,
        web_search_enabled: bool | None = None,
        skip_revision: bool | None = None,
    ) -> NoteMetadataResponse | None:
        """
        Update note metadata fields

        Args:
            note_id: Note identifier
            note_type: New note type
            importance: New importance level
            auto_enrich: Enable/disable auto-enrichment
            web_search_enabled: Enable/disable web search
            skip_revision: Exclude from SM-2 reviews

        Returns:
            Updated NoteMetadataResponse or None if not found
        """
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.note_types import ImportanceLevel, NoteType

        logger.info(f"Updating metadata for note: {note_id}")

        # Get metadata store
        store = NoteMetadataStore(self.config.storage.database_path.parent / "notes_meta.db")
        metadata = store.get(note_id)

        if metadata is None:
            return None

        # Apply updates
        if note_type is not None:
            try:
                metadata.note_type = NoteType(note_type.lower())
            except ValueError:
                metadata.note_type = NoteType.AUTRE

        if importance is not None:
            try:
                metadata.importance = ImportanceLevel(importance.lower())
            except ValueError:
                metadata.importance = ImportanceLevel.NORMAL

        if auto_enrich is not None:
            metadata.auto_enrich = auto_enrich

        if web_search_enabled is not None:
            metadata.web_search_enabled = web_search_enabled

        # skip_revision=True means excluding from SM-2 reviews (set next_review to None)
        # skip_revision=False doesn't change next_review (will be set during next review cycle)
        if skip_revision is not None and skip_revision:
            metadata.next_review = None

        # Save - run in thread pool for I/O
        await asyncio.to_thread(store.save, metadata)

        logger.info(f"Metadata updated for note: {note_id}")

        # Return response
        return NoteMetadataResponse(
            note_id=metadata.note_id,
            note_type=metadata.note_type.value,
            easiness_factor=metadata.easiness_factor,
            repetition_number=metadata.repetition_number,
            interval_hours=metadata.interval_hours,
            next_review=metadata.next_review,
            last_quality=metadata.last_quality,
            review_count=metadata.review_count,
            auto_enrich=metadata.auto_enrich,
            importance=metadata.importance.value,
            quality_score=None,  # Not tracked in metadata directly
            last_synced_at=metadata.last_synced_at,
        )

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

        # Run in thread pool for iCloud I/O
        result = await asyncio.to_thread(manager.delete_note, note_id)
        if result:
            logger.info(f"Note deleted: {note_id}")
        return result

    async def enrich_note(
        self,
        note_id: str,
        sources: list[str] | None = None,
    ) -> Optional[EnrichmentResultResponse]:
        """
        Enrich a note using NoteEnricher

        Args:
            note_id: Note identifier
            sources: Sources to use (ai_analysis, cross_reference, web_search)
                    Default: ["cross_reference"]

        Returns:
            EnrichmentResultResponse or None if note not found
        """
        from src.passepartout.note_enricher import EnrichmentContext, NoteEnricher
        from src.passepartout.note_metadata import NoteMetadataStore

        if sources is None:
            sources = ["cross_reference"]

        logger.info(f"Enriching note: {note_id} with sources: {sources}")

        manager = self._get_manager()

        # Get note
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        # Get metadata
        store = NoteMetadataStore(self.config.storage.database_path.parent / "notes_meta.db")
        metadata = store.get(note_id)
        if metadata is None:
            logger.warning(f"No metadata for note {note_id}, using defaults")
            from src.passepartout.note_metadata import NoteMetadata
            metadata = NoteMetadata(note_id=note_id)

        # Web search is enabled if explicitly requested in sources
        # (metadata.web_search_enabled controls automatic enrichment, not explicit requests)
        web_search_enabled = "web_search" in sources

        # Get linked notes for cross-reference
        linked_notes = []
        if "cross_reference" in sources:
            # Extract wikilinks [[title]] from note content
            wikilink_pattern = re.compile(r"\[\[([^\]]+)\]\]")
            linked_titles = wikilink_pattern.findall(note.content)

            # Try to find notes by title (limit to 10)
            for title in linked_titles[:10]:
                # Search for note by title
                search_results = await asyncio.to_thread(
                    manager.search_notes, title, top_k=1, return_scores=True
                )
                if search_results:
                    linked_note, _ = search_results[0]
                    if linked_note.note_id != note_id:  # Don't include self
                        linked_notes.append(linked_note)

        # Create enricher
        enricher = NoteEnricher(
            ai_router=None,  # TODO: Integrate Sancho if ai_analysis requested
            web_search_enabled=web_search_enabled,
        )

        # Create context
        context = EnrichmentContext(
            note=note,
            metadata=metadata,
            linked_notes=linked_notes,
        )

        # Run enrichment
        result = await enricher.enrich(note, metadata, context)

        logger.info(
            f"Enrichment complete for note {note_id}: {len(result.enrichments)} suggestions"
        )

        # Seuil d'auto-application
        AUTO_APPLY_THRESHOLD = 0.85

        # Séparer les enrichissements par confiance
        auto_applied = []
        suggestions = []

        for idx, e in enumerate(result.enrichments):
            item = EnrichmentItemResponse(
                source=e.source.value,
                section=e.section,
                content=e.content,
                confidence=e.confidence,
                reasoning=e.reasoning,
                metadata=e.metadata,
                applied=False,
                index=idx,
            )

            if e.confidence >= AUTO_APPLY_THRESHOLD:
                # Appliquer automatiquement
                try:
                    await self._apply_enrichment_to_note(
                        manager, note, e.section, e.content, e.metadata
                    )
                    item.applied = True
                    auto_applied.append(item)
                    logger.info(
                        f"Auto-applied enrichment to note {note_id}",
                        extra={"section": e.section, "confidence": e.confidence},
                    )
                except Exception as ex:
                    logger.warning(
                        f"Failed to auto-apply enrichment: {ex}",
                        extra={"note_id": note_id, "section": e.section},
                    )
                    suggestions.append(item)
            else:
                suggestions.append(item)

        # Construire le résumé
        summary = result.analysis_summary
        if auto_applied:
            summary = f"{len(auto_applied)} enrichissements appliqués automatiquement. {summary}"

        return EnrichmentResultResponse(
            note_id=result.note_id,
            enrichments=suggestions,
            auto_applied=auto_applied,
            gaps_identified=result.gaps_identified,
            sources_used=[s.value for s in result.sources_used],
            analysis_summary=summary,
        )

    async def _apply_enrichment_to_note(
        self,
        manager: Any,
        note: Any,
        section: str,
        content: str,
        metadata: dict[str, Any],
    ) -> None:
        """
        Apply an enrichment to a note's content.

        Adds the content to the specified section, or creates a new section
        at the end of the note if it doesn't exist.
        """
        current_content = note.content

        # Chercher la section dans le contenu
        section_pattern = re.compile(
            rf"^(#+\s*{re.escape(section)})\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        match = section_pattern.search(current_content)

        if match:
            # Ajouter après le titre de section
            insert_pos = match.end()
            # Trouver la fin de la section (prochain titre ou fin de fichier)
            next_section = re.search(r"^#+\s+", current_content[insert_pos:], re.MULTILINE)
            if next_section:
                insert_pos = insert_pos + next_section.start()

            # Insérer le contenu avant la prochaine section
            new_content = (
                current_content[:insert_pos].rstrip()
                + "\n\n"
                + content
                + "\n\n"
                + current_content[insert_pos:].lstrip()
            )
        else:
            # Créer une nouvelle section à la fin
            url = metadata.get("url", "")
            source_note = f"\n\n> Source: {url}" if url else ""
            new_content = (
                current_content.rstrip()
                + f"\n\n## {section}\n\n"
                + content
                + source_note
                + "\n"
            )

        # Sauvegarder la note modifiée
        await asyncio.to_thread(
            manager.update_note,
            note.note_id,
            content=new_content,
        )

    async def apply_enrichment(
        self,
        note_id: str,
        section: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Manually apply an enrichment to a note.

        Args:
            note_id: Note identifier
            section: Target section name
            content: Content to add
            metadata: Optional metadata (e.g., source URL)

        Returns:
            True if successful, False if note not found
        """
        manager = self._get_manager()

        # Get note
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return False

        # Apply the enrichment
        await self._apply_enrichment_to_note(
            manager, note, section, content, metadata or {}
        )

        logger.info(
            f"Manually applied enrichment to note {note_id}",
            extra={"section": section},
        )

        return True

    async def run_hygiene(
        self, note_id: str
    ) -> Optional["HygieneResultResponse"]:
        """
        Run hygiene checks on a note.

        This runs rule-based checks (no AI) to identify:
        - Broken/missing links
        - Formatting issues
        - Temporal references (outdated content)
        - Completed tasks

        Args:
            note_id: Note identifier

        Returns:
            HygieneResultResponse or None if note not found
        """
        import time

        from src.frontin.api.models.notes import (
            HygieneIssueResponse,
            HygieneResultResponse,
            HygieneSummaryResponse,
        )
        from src.passepartout.retouche_reviewer import RetoucheReviewer

        start_time = time.time()
        logger.info(f"Running hygiene checks on note: {note_id}")

        manager = self._get_manager()

        # Get the note
        note = await asyncio.to_thread(manager.get_note, note_id)
        if not note:
            logger.warning(f"Note not found for hygiene: {note_id}")
            return None

        # Create reviewer (no AI, just rule-based checks)
        reviewer = RetoucheReviewer(
            notes=manager,
            ai_router=None,  # No AI for hygiene
            notes_dir=manager.notes_dir,
        )

        # Collect issues
        issues: list[HygieneIssueResponse] = []
        auto_fixed = 0

        # 1. Check temporal references
        temporal_issues = reviewer._check_temporal_references(note.content)
        for issue in temporal_issues:
            issues.append(HygieneIssueResponse(
                type="temporal",
                severity="warning",
                detail=issue.get("reason", "Référence temporelle obsolète"),
                suggestion="Mettre à jour ou supprimer cette référence",
                confidence=issue.get("confidence", 0.7),
                auto_applied=False,
                source="rule_based",
            ))

        # 2. Check completed tasks
        completed_tasks = reviewer._check_completed_tasks(note.content)
        for task in completed_tasks:
            issues.append(HygieneIssueResponse(
                type="task",
                severity="info",
                detail=task.get("reason", "Tâche terminée"),
                suggestion="Archiver ou supprimer cette tâche",
                confidence=task.get("confidence", 0.75),
                auto_applied=False,
                source="rule_based",
            ))

        # 3. Check missing links
        linked_notes = await asyncio.to_thread(manager.get_linked_notes, note_id)
        missing_links = reviewer._check_missing_links(note.content, linked_notes)
        for link in missing_links:
            issues.append(HygieneIssueResponse(
                type="missing_link",
                severity="info",
                detail=link.get("reason", "Entité non liée"),
                suggestion=f"Ajouter lien vers [[{link.get('entity', '')}]]",
                confidence=link.get("confidence", 0.7),
                auto_applied=False,
                source="rule_based",
            ))

        # 4. Check formatting issues
        format_issues = reviewer._check_formatting(note.content)
        for fmt in format_issues:
            issues.append(HygieneIssueResponse(
                type="formatting",
                severity="warning" if fmt.get("severity") == "warning" else "info",
                detail=fmt.get("reason", "Problème de formatage"),
                suggestion=fmt.get("fix", "Corriger le formatage"),
                confidence=0.9,
                auto_applied=False,
                source="rule_based",
            ))

        # Calculate health score (1.0 = perfect, decreases with issues)
        error_count = len([i for i in issues if i.severity == "error"])
        warning_count = len([i for i in issues if i.severity == "warning"])
        info_count = len([i for i in issues if i.severity == "info"])

        # Weighted score: errors -0.2, warnings -0.1, info -0.02
        health_score = max(0.0, 1.0 - (error_count * 0.2) - (warning_count * 0.1) - (info_count * 0.02))

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Hygiene complete for {note_id}: {len(issues)} issues, "
            f"health_score={health_score:.2f}, duration={duration_ms}ms"
        )

        return HygieneResultResponse(
            note_id=note_id,
            analyzed_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            model_used="rule-based",
            context_notes_count=len(linked_notes),
            issues=issues,
            summary=HygieneSummaryResponse(
                total_issues=len(issues),
                auto_fixed=auto_fixed,
                pending_review=len(issues) - auto_fixed,
                health_score=health_score,
            ),
        )

    async def move_note(self, note_id: str, target_folder: str) -> Optional[NoteMoveResponse]:
        """
        Move a note to a different folder

        Args:
            note_id: Note identifier
            target_folder: Target folder path (e.g., "Projects/Alpha" or "" for root)

        Returns:
            NoteMoveResponse if moved, None if not found
        """
        logger.info(f"Moving note: {note_id} to folder: {target_folder}")
        manager = self._get_manager()

        # Get current path before moving - run in thread pool for iCloud I/O
        note = await asyncio.to_thread(manager.get_note, note_id)
        if not note:
            return None

        old_path = note.metadata.get("path", "")

        # Run in thread pool for iCloud I/O
        result = await asyncio.to_thread(manager.move_note, note_id, target_folder)
        if not result:
            return None

        logger.info(f"Note moved: {note_id} from '{old_path}' to '{target_folder}'")
        return NoteMoveResponse(
            note_id=note_id,
            old_path=old_path,
            new_path=target_folder,
            moved=True,
        )

    async def search_notes(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> NoteSearchResponse:
        """
        Semantic search for notes with filtering and ranking

        Args:
            query: Search query
            tags: Optional tag filter
            limit: Maximum results

        Returns:
            NoteSearchResponse with ranked results (score >= 40% threshold)
        """
        # Search relevance thresholds
        MIN_SCORE_THRESHOLD = 0.4  # Reject results below 40% similarity
        TITLE_BOOST_FACTOR = 1.5  # +50% boost if query appears in title

        logger.info(f"Searching notes: '{query}' (tags={tags})")
        manager = self._get_manager()

        # Request more results to account for filtering
        search_limit = limit * 3

        # Search with scores - run in thread pool for FAISS + iCloud I/O
        results = await asyncio.to_thread(
            manager.search_notes,
            query=query,
            top_k=search_limit,
            tags=tags,
            return_scores=True,
        )

        # Build and filter response
        query_lower = query.lower().strip()
        search_results = []

        for note, l2_distance in results:  # type: ignore
            # Convert L2 distance to similarity score (higher = better)
            # Using formula: similarity = 1 / (1 + distance)
            similarity_score = 1.0 / (1.0 + float(l2_distance))

            # Apply title boost if query appears in title
            title_lower = note.title.lower() if note.title else ""
            if query_lower and query_lower in title_lower:
                similarity_score = min(1.0, similarity_score * TITLE_BOOST_FACTOR)

            # Skip results below threshold
            if similarity_score < MIN_SCORE_THRESHOLD:
                continue

            response = _note_to_response(note)
            search_results.append(
                NoteSearchResult(
                    note=response,
                    score=similarity_score,
                    highlights=[],
                )
            )

        # Sort by score descending (title-boosted results rise to top)
        search_results.sort(key=lambda r: r.score, reverse=True)

        # Apply limit after sorting
        search_results = search_results[:limit]

        logger.info(
            f"Search returned {len(search_results)} results (filtered from {len(results)})"
        )
        return NoteSearchResponse(
            query=query,
            results=search_results,
            total=len(search_results),
        )

    async def get_note_links(self, note_id: str) -> Optional[NoteLinksResponse]:
        """
        Get bidirectional links for a note

        Args:
            note_id: Note identifier

        Returns:
            NoteLinksResponse with incoming and outgoing links
        """
        logger.info(f"Getting links for note: {note_id}")
        manager = self._get_manager()

        # Run in thread pool for iCloud I/O
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        # Optimization: Use metadata summaries and aliases index instead of reading all files
        # Run in thread pool for iCloud I/O
        summaries = await asyncio.to_thread(manager.get_notes_summary)
        aliases = await asyncio.to_thread(manager.get_aliases_index)

        # Build ID-to-summary map for fast lookup
        id_to_meta = {s["note_id"]: s for s in summaries}

        # Resolve outgoing wikilinks
        outgoing: list[WikilinkResponse] = []
        for text in note.outgoing_links:
            # Match title or alias
            target_id = aliases.get(text.lower())
            target_meta = id_to_meta.get(target_id) if target_id else None

            outgoing.append(
                WikilinkResponse(
                    text=text,
                    target_id=target_id,
                    target_title=target_meta["title"] if target_meta else None,
                    exists=target_id is not None,
                )
            )

        # Find incoming links (notes that link to this one)
        note_title_lower = note.title.lower()
        incoming: list[WikilinkResponse] = []

        for s in summaries:
            # Skip self
            if s["note_id"] == note_id:
                continue

            # Check links if available in summary (new field)
            # Fallback to empty list if not yet indexed
            other_links = s.get("links", [])

            if any(link.lower() == note_title_lower for link in other_links):
                incoming.append(
                    WikilinkResponse(
                        text=s["title"],
                        target_id=s["note_id"],
                        target_title=s["title"],
                        exists=True,
                    )
                )

        return NoteLinksResponse(
            note_id=note_id,
            outgoing=outgoing,
            incoming=incoming,
        )

    async def toggle_pin(self, note_id: str) -> Optional[NoteResponse]:
        """
        Toggle pin status for a note

        Args:
            note_id: Note identifier

        Returns:
            Updated NoteResponse or None if not found
        """
        manager = self._get_manager()
        # Run in thread pool for iCloud I/O
        note = await asyncio.to_thread(manager.get_note, note_id)
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
    ) -> Optional[NoteVersionsResponse]:
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

        # Verify note exists - run in thread pool for iCloud I/O
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        git_manager = self._get_git_manager()
        filename = await asyncio.to_thread(manager.get_relative_path, note_id) or f"{note_id}.md"
        # Run in thread pool for git I/O
        versions = await asyncio.to_thread(git_manager.list_versions, filename, limit)

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
    ) -> Optional[NoteVersionContentResponse]:
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
        manager = self._get_manager()

        # Run in thread pool for iCloud/git I/O
        filename = await asyncio.to_thread(manager.get_relative_path, note_id) or f"{note_id}.md"
        content = await asyncio.to_thread(git_manager.get_version, filename, version_id)

        if content is None:
            return None

        # Get version metadata - run in thread pool for git I/O
        versions = await asyncio.to_thread(git_manager.list_versions, filename, 100)
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
    ) -> Optional[NoteDiffResponse]:
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
        manager = self._get_manager()

        # Run in thread pool for iCloud/git I/O
        filename = await asyncio.to_thread(manager.get_relative_path, note_id) or f"{note_id}.md"
        diff = await asyncio.to_thread(git_manager.diff, filename, from_version, to_version)

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
    ) -> Optional[NoteResponse]:
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

        # Run in thread pool for iCloud/git I/O
        filename = await asyncio.to_thread(manager.get_relative_path, note_id) or f"{note_id}.md"

        # Verify note exists - run in thread pool for iCloud I/O
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        # Run in thread pool for git I/O
        success = await asyncio.to_thread(git_manager.restore, filename, version_id)

        if not success:
            return None

        # Clear cache and reload note
        if note_id in manager._note_cache:
            del manager._note_cache[note_id]

        # Re-index in vector store (content changed) - run in thread pool for iCloud I/O
        updated_note = await asyncio.to_thread(manager.get_note, note_id)
        if updated_note:
            # Update vector store - run in thread pool for FAISS I/O
            await asyncio.to_thread(manager.vector_store.remove, note_id)
            search_text = f"{updated_note.title}\n\n{updated_note.content}"
            await asyncio.to_thread(
                manager.vector_store.add,
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

            # Perform bidirectional sync in thread pool (blocking AppleScript calls)
            result = await asyncio.to_thread(
                sync_service.sync, direction=SyncDirection.BIDIRECTIONAL
            )

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

            # FORCE REFRESH: Rebuild metadata index in thread pool (file I/O)
            indexed_count = await asyncio.to_thread(manager.refresh_index)
            logger.info(f"Refreshed metadata index: {indexed_count} notes")

            # Update last_synced_at for synced notes
            synced_note_names = result.created + result.updated
            if synced_note_names:
                await self._update_sync_timestamps(manager, synced_note_names)

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

    async def _update_sync_timestamps(
        self, manager: "NoteManager", synced_note_names: list[str]
    ) -> None:
        """
        Update last_synced_at for notes that were synced.

        Args:
            manager: NoteManager instance
            synced_note_names: List of note names/titles that were synced
        """
        from src.passepartout.note_metadata import NoteMetadataStore

        now = datetime.now(timezone.utc)
        metadata_store = NoteMetadataStore(self.config.storage.database_path.parent / "notes_meta.db")

        updated_count = 0
        for note_name in synced_note_names:
            # Clean up the name (remove suffixes like "(Apple wins)")
            clean_name = note_name.split(" (")[0].strip()

            # Search for the note by title
            results = manager.search_notes(clean_name, top_k=5, return_scores=True)
            for note, _score in results:
                # Check if title matches closely
                if note.title.lower() == clean_name.lower() or clean_name.lower() in note.title.lower():
                    # Get or create metadata
                    metadata = metadata_store.get(note.note_id)
                    if metadata:
                        metadata.last_synced_at = now
                        metadata_store.save(metadata)
                        updated_count += 1
                        break

        logger.info(f"Updated last_synced_at for {updated_count} notes")

    async def get_deleted_notes(self) -> list[NoteResponse]:
        """
        Get notes from Scapin's trash folder (_Supprimées/)

        Returns:
            List of NoteResponse for deleted notes
        """
        logger.info("Fetching deleted notes from Scapin trash...")

        try:
            manager = self._get_manager()
            deleted_notes = await asyncio.to_thread(manager.get_deleted_notes)
            logger.info(f"Found {len(deleted_notes)} deleted notes in trash")

            # Convert Note to NoteResponse
            responses = []
            for note in deleted_notes:
                deleted_at = manager._notes_metadata.get(note.note_id, {}).get("deleted_at")
                responses.append(_note_to_response(note, deleted_at=deleted_at))

            return responses

        except Exception as e:
            logger.error(f"Failed to get deleted notes: {e}", exc_info=True)
            return []

    async def restore_note(self, note_id: str, target_folder: str = "") -> bool:
        """
        Restore a note from trash to its original or specified folder

        Args:
            note_id: Note identifier
            target_folder: Target folder path (empty string for root)

        Returns:
            True if restored, False if note not found in trash
        """
        logger.info(f"Restoring note {note_id} from trash...")
        manager = self._get_manager()
        result = await asyncio.to_thread(manager.restore_note, note_id, target_folder)
        if result:
            logger.info(f"Restored note {note_id}")
        else:
            logger.warning(f"Failed to restore note {note_id}")
        return result

    async def permanently_delete_note(self, note_id: str) -> bool:
        """
        Permanently delete a note from trash

        Args:
            note_id: Note identifier

        Returns:
            True if permanently deleted, False if note not found
        """
        logger.info(f"Permanently deleting note {note_id}...")
        manager = self._get_manager()
        result = await asyncio.to_thread(manager.permanently_delete_note, note_id)
        if result:
            logger.info(f"Permanently deleted note {note_id}")
        else:
            logger.warning(f"Failed to permanently delete note {note_id}")
        return result

    async def empty_trash(self) -> int:
        """
        Permanently delete all notes in trash

        Returns:
            Number of notes permanently deleted
        """
        logger.info("Emptying trash...")
        manager = self._get_manager()
        count = await asyncio.to_thread(manager.empty_trash)
        logger.info(f"Emptied trash: {count} notes deleted")
        return count

    async def rebuild_index(self) -> dict[str, Any]:
        """
        Rebuild the vector search index from scratch

        Clears existing index and re-indexes all notes.
        Useful when the index is corrupted or out of sync.

        Returns:
            Dictionary with rebuild statistics
        """
        logger.info("Starting index rebuild...")
        manager = self._get_manager()

        # Run in thread pool since it's blocking I/O
        result = await asyncio.to_thread(manager.rebuild_index)

        logger.info(
            f"Index rebuild completed: {result['notes_indexed']} notes in {result['elapsed_seconds']}s"
        )
        return result

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

        # Create folder (will succeed even if exists) - run in thread pool for file I/O
        absolute_path = await asyncio.to_thread(manager.create_folder, path)

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

        # Run in thread pool to avoid blocking event loop
        folders = await asyncio.to_thread(manager.list_folders)
        return FolderListResponse(
            folders=folders,
            total=len(folders),
        )

    # =========================================================================
    # RETOUCHE PREVIEW (Phase 4)
    # =========================================================================

    async def preview_retouche(self, note_id: str) -> Optional[RetouchePreviewResponse]:
        """
        Preview proposed retouche changes for a note

        Analyzes the note with AI and returns proposed improvements
        without applying them.

        Args:
            note_id: Note identifier

        Returns:
            RetouchePreviewResponse with proposed actions, or None if note not found
        """
        logger.info(f"Previewing retouche for note: {note_id}")
        manager = self._get_manager()

        # Get the note
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        # Get retouche reviewer (lazy init to avoid circular imports)
        reviewer = await self._get_retouche_reviewer()
        if reviewer is None:
            # Return empty preview if reviewer not available
            return RetouchePreviewResponse(
                note_id=note_id,
                note_title=note.title,
                quality_before=None,
                quality_after=50,
                model_used="unavailable",
                actions=[],
                diff_preview="",
                reasoning="Retouche service not available",
            )

        # Load context and analyze
        from src.passepartout.note_metadata import NoteMetadataStore
        from src.passepartout.note_types import NoteType, detect_note_type_from_path

        # Get or create metadata
        metadata_store = NoteMetadataStore(self.config.storage.database_path.parent / "notes_meta.db")
        metadata = metadata_store.get(note_id)
        if metadata is None:
            # D'abord essayer avec le metadata.path du frontmatter (chemin logique)
            logical_path = note.metadata.get("path", "") if note.metadata else ""
            note_type = detect_note_type_from_path(logical_path)
            if note_type == NoteType.AUTRE:
                # Fallback sur le chemin physique
                note_type = detect_note_type_from_path(str(note.file_path) if note.file_path else "")
            metadata = metadata_store.create_for_note(
                note_id=note_id,
                note_type=note_type,
                content=note.content,
            )

        # Load context
        context = await reviewer._load_context(note, metadata)

        # Analyze with AI
        analysis = await reviewer._analyze_with_escalation(context)

        # Convert actions to preview format
        actions = []
        for action in analysis.actions:
            actions.append(
                RetoucheActionPreview(
                    action_type=action.action_type.value,
                    target=action.target,
                    content=action.content,
                    confidence=action.confidence,
                    reasoning=action.reasoning,
                    auto_apply=action.confidence >= reviewer.AUTO_APPLY_THRESHOLD,
                )
            )

        # Calculate quality
        quality_after = reviewer._calculate_quality_score(context, analysis)

        return RetouchePreviewResponse(
            note_id=note_id,
            note_title=note.title,
            quality_before=metadata.quality_score,
            quality_after=quality_after,
            model_used=analysis.model_used,
            actions=actions,
            diff_preview="",  # TODO: Generate unified diff
            reasoning=analysis.reasoning,
        )

    async def apply_retouche(
        self,
        note_id: str,
        action_indices: list[int] | None = None,
        apply_all: bool = False,
    ) -> Optional[RetouchePreviewResponse]:
        """
        Apply selected retouche actions to a note

        Args:
            note_id: Note identifier
            action_indices: Indices of actions to apply (None = auto-apply only)
            apply_all: Apply all proposed actions

        Returns:
            RetouchePreviewResponse with applied actions, or None if note not found
        """
        # TODO: Implement selective action application based on action_indices
        # For now, we run the full retouche cycle
        _ = action_indices  # Reserved for future selective application
        _ = apply_all  # Reserved for future "apply all" mode

        logger.info(f"Applying retouche for note: {note_id}")

        # Get the reviewer
        reviewer = await self._get_retouche_reviewer()
        if reviewer is None:
            return None

        # Run full retouche cycle
        result = await reviewer.review_note(note_id)

        if not result.success:
            return None

        # Convert to response format
        actions = []
        for action in result.actions:
            actions.append(
                RetoucheActionPreview(
                    action_type=action.action_type.value,
                    target=action.target,
                    content=action.content,
                    confidence=action.confidence,
                    reasoning=action.reasoning,
                    auto_apply=action.applied,
                )
            )

        return RetouchePreviewResponse(
            note_id=note_id,
            note_title="",  # Not available in result
            quality_before=result.quality_before,
            quality_after=result.quality_after,
            model_used=result.model_used,
            actions=actions,
            diff_preview="",
            reasoning=result.reasoning,
        )

    async def _get_retouche_reviewer(self):
        """Get or create RetoucheReviewer instance"""
        if not hasattr(self, "_retouche_reviewer"):
            try:
                from src.passepartout.note_metadata import NoteMetadataStore
                from src.passepartout.note_scheduler import NoteScheduler
                from src.passepartout.retouche_reviewer import RetoucheReviewer
                from src.sancho.router import AIRouter

                manager = self._get_manager()
                metadata_store = NoteMetadataStore(self.config.storage.database_path.parent / "notes_meta.db")
                scheduler = NoteScheduler(metadata_store)

                # Try to get AI router
                try:
                    ai_router = AIRouter()
                except Exception:
                    ai_router = None

                self._retouche_reviewer = RetoucheReviewer(
                    note_manager=manager,
                    metadata_store=metadata_store,
                    scheduler=scheduler,
                    ai_router=ai_router,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize RetoucheReviewer: {e}")
                self._retouche_reviewer = None

        return self._retouche_reviewer

    # =========================================================================
    # RETOUCHE ROLLBACK (Phase 5)
    # =========================================================================

    async def rollback_retouche(
        self,
        note_id: str,
        record_index: int | None = None,
        git_commit: str | None = None,
    ) -> Optional[RetoucheRollbackResponse]:
        """
        Rollback a retouche action on a note

        Args:
            note_id: Note identifier
            record_index: Index in enrichment_history to rollback (0 = most recent)
            git_commit: Git commit hash to restore (alternative method)

        Returns:
            RetoucheRollbackResponse or None if not found
        """
        logger.info(f"Rolling back retouche for note: {note_id}")

        # Validate at least one method is specified
        if record_index is None and git_commit is None:
            raise ValueError("Must specify either record_index or git_commit")

        # If git_commit is provided, use git restore
        if git_commit is not None:
            _validate_version_id(git_commit)
            result = await self.restore_version(note_id, git_commit)
            if result is None:
                return None

            return RetoucheRollbackResponse(
                note_id=note_id,
                rolled_back=True,
                action_type="git_restore",
                restored_from=f"git:{git_commit[:7]}",
                new_content_preview=result.content[:200] if result else "",
            )

        # Use record_index to find the content_before
        from src.passepartout.note_metadata import NoteMetadataStore

        metadata_store = NoteMetadataStore(self.config.storage.database_path.parent / "notes_meta.db")
        metadata = metadata_store.get(note_id)

        if metadata is None or not metadata.enrichment_history:
            return None

        # Get the record to rollback (records are stored newest first)
        if record_index >= len(metadata.enrichment_history):
            return None

        record = metadata.enrichment_history[record_index]

        # Check if record has content_before (needed for rollback)
        content_before = getattr(record, "content_before", None)
        if not content_before:
            # Fall back to git restore if we have the timestamp
            # Find the git commit just before this record
            git_manager = self._get_git_manager()
            manager = self._get_manager()
            filename = await asyncio.to_thread(manager.get_relative_path, note_id)
            if not filename:
                filename = f"{note_id}.md"

            versions = await asyncio.to_thread(git_manager.list_versions, filename, 100)

            # Find version just before the record timestamp
            target_version = None
            for version in versions:
                if version.timestamp < record.timestamp:
                    target_version = version
                    break

            if target_version:
                result = await self.restore_version(note_id, target_version.version_id)
                if result:
                    return RetoucheRollbackResponse(
                        note_id=note_id,
                        rolled_back=True,
                        action_type=record.action_type,
                        restored_from=f"git:{target_version.version_id}",
                        new_content_preview=result.content[:200] if result else "",
                    )

            return None

        # Restore the content_before
        manager = self._get_manager()
        note = await asyncio.to_thread(manager.get_note, note_id)
        if note is None:
            return None

        # Replace the target section with content_before
        # This is a simplified implementation - for complex cases, use git
        success = await asyncio.to_thread(
            manager.update_note,
            note_id=note_id,
            content=content_before,
        )

        if not success:
            return None

        return RetoucheRollbackResponse(
            note_id=note_id,
            rolled_back=True,
            action_type=record.action_type,
            restored_from=f"record:{record_index}",
            new_content_preview=content_before[:200],
        )

    # =========================================================================
    # RETOUCHE QUEUE (Phase 5)
    # =========================================================================

    async def get_retouche_queue(self) -> RetoucheQueueResponse:
        """
        Get queue of notes with pending retouche actions

        Returns notes that have been analyzed but need user action,
        grouped by confidence level.
        """
        logger.info("Getting retouche queue")

        from src.passepartout.note_metadata import NoteMetadataStore

        metadata_store = NoteMetadataStore(self.config.storage.database_path.parent / "notes_meta.db")
        manager = self._get_manager()

        # Get all notes with metadata
        all_metadata = await asyncio.to_thread(metadata_store.list_all)

        high_confidence: list[RetoucheQueueItem] = []
        pending_review: list[RetoucheQueueItem] = []

        stats = {
            "total": 0,
            "high_confidence": 0,
            "pending_review": 0,
            "auto_applied_today": 0,
        }

        for meta in all_metadata:
            # Check if note has pending actions in recent history
            if not meta.enrichment_history:
                continue

            # Get recent pending actions (not applied)
            pending_actions = [
                r for r in meta.enrichment_history[:10] if not r.applied
            ]

            if not pending_actions:
                continue

            stats["total"] += 1

            # Get note info for display
            note = await asyncio.to_thread(manager.get_note, meta.note_id)
            if note is None:
                continue

            avg_confidence = (
                sum(a.confidence for a in pending_actions) / len(pending_actions)
                if pending_actions
                else 0.0
            )

            all_high_confidence = all(a.confidence >= 0.85 for a in pending_actions)

            item = RetoucheQueueItem(
                note_id=meta.note_id,
                note_title=note.title,
                note_path=note.metadata.get("path", ""),
                action_count=len(pending_actions),
                avg_confidence=avg_confidence,
                quality_score=meta.quality_score,
                last_retouche=(
                    meta.enrichment_history[0].timestamp if meta.enrichment_history else None
                ),
                high_confidence=all_high_confidence,
            )

            if all_high_confidence:
                high_confidence.append(item)
                stats["high_confidence"] += 1
            else:
                pending_review.append(item)
                stats["pending_review"] += 1

        # Sort by avg_confidence descending
        high_confidence.sort(key=lambda x: x.avg_confidence, reverse=True)
        pending_review.sort(key=lambda x: x.avg_confidence, reverse=True)

        logger.info(
            f"Retouche queue: {stats['high_confidence']} high confidence, "
            f"{stats['pending_review']} pending review"
        )

        return RetoucheQueueResponse(
            high_confidence=high_confidence,
            pending_review=pending_review,
            stats=stats,
        )
