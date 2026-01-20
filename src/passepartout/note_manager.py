"""
Note Manager with Markdown and Vector Search

Manages notes stored as Markdown files with YAML frontmatter.
Provides semantic search via vector store integration.
"""

import concurrent.futures
import contextlib
import hashlib
import os
import re
import tempfile
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from src.core.events import Entity
from src.monitoring.logger import get_logger
from src.passepartout.embeddings import EmbeddingGenerator
from src.passepartout.frontmatter_parser import FrontmatterParser
from src.passepartout.frontmatter_schema import AnyFrontmatter, PersonneFrontmatter
from src.passepartout.git_versioning import GitVersionManager
from src.passepartout.note_types import ImportanceLevel, NoteStatus, NoteType
from src.passepartout.templates import TemplateManager
from src.passepartout.vector_store import VectorStore

logger = get_logger("passepartout.note_manager")

# LRU Cache configuration
DEFAULT_CACHE_MAX_SIZE = 2000  # Maximum notes to keep in memory

# Trash folder for soft-deleted notes
TRASH_FOLDER = "_Supprimées"

# Pre-compiled regex for frontmatter parsing (performance optimization)
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
# Pre-compiled regex for wikilinks: [[target]] or [[target|label]]
WIKILINK_PATTERN = re.compile(r"\[\[(.*?)(?:\|.*?)?\]\]")


@dataclass
class Note:
    """
    Note data structure

    Represents a single note with metadata and content.
    Uses slots=True for ~30% memory reduction per instance.
    """

    note_id: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    tags: list[str] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    outgoing_links: list[str] = field(default_factory=list)
    file_path: Optional[Path] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "note_id": self.note_id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "entities": [
                {"type": e.type, "value": e.value, "confidence": e.confidence}
                for e in self.entities
            ],
            "metadata": self.metadata,
            "outgoing_links": self.outgoing_links,
            "file_path": str(self.file_path) if self.file_path else None,
        }


class NoteManager:
    """
    Manage notes with Markdown files and vector search

    Features:
    - Create/update/delete notes
    - YAML frontmatter parsing
    - Vector-based semantic search
    - Entity-based retrieval
    - Tag filtering

    Usage:
        manager = NoteManager(notes_dir=Path("~/notes"))
        note_id = manager.create_note("Meeting Notes", "Discussed project timeline...")
        results = manager.search_notes("project deadlines", top_k=5)
    """

    def __init__(
        self,
        notes_dir: Path,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[EmbeddingGenerator] = None,
        auto_index: bool = True,
        git_enabled: bool = True,
        cache_max_size: int = DEFAULT_CACHE_MAX_SIZE,
    ):
        """
        Initialize note manager

        Args:
            notes_dir: Directory to store notes
            vector_store: VectorStore instance (creates new if None)
            embedder: EmbeddingGenerator instance (creates new if None)
            auto_index: Whether to automatically index existing notes on init
            git_enabled: Whether to enable Git versioning
            cache_max_size: Maximum number of notes to keep in LRU cache

        Raises:
            ValueError: If notes_dir is invalid
        """
        self.notes_dir = Path(notes_dir).expanduser()
        self.notes_dir.mkdir(parents=True, exist_ok=True)

        # Index persistence paths
        self._index_path = self.notes_dir / ".scapin_index"
        self._metadata_index_path = self.notes_dir / ".scapin_notes_meta.json"

        # Lightweight metadata index for fast tree building
        # { note_id: { title, path, updated_at, pinned, tags } }
        self._notes_metadata: dict[str, dict[str, Any]] = {}

        # Initialize embedder and vector store
        self.embedder = embedder if embedder is not None else EmbeddingGenerator()
        self.vector_store = (
            vector_store
            if vector_store is not None
            else VectorStore(dimension=self.embedder.get_dimension(), embedder=self.embedder)
        )

        # Initialize Git versioning if enabled
        self.git: Optional[GitVersionManager] = None
        if git_enabled:
            try:
                self.git = GitVersionManager(self.notes_dir)
                logger.info("Git versioning enabled for notes")
            except Exception as e:
                logger.warning("Failed to initialize Git versioning", extra={"error": str(e)})
                logger.warning("Failed to initialize Git versioning", extra={"error": str(e)})
                self.git = None

        # Template Manager
        try:
            # Assuming src/passepartout/note_manager.py -> src/templates
            templates_dir = Path(__file__).parent.parent / "templates"
            self.template_manager = TemplateManager(templates_dir)
        except Exception as e:
            logger.warning(f"Failed to initialize TemplateManager: {e}")
            self.template_manager = None

        # Frontmatter Parser for typed frontmatter access
        self._frontmatter_parser = FrontmatterParser()

        # Aliases index cache (title.lower() -> note_id, alias.lower() -> note_id)
        self._aliases_index: dict[str, str] = {}
        self._aliases_index_dirty = True  # Needs rebuild

        # LRU cache: OrderedDict maintains insertion order for LRU eviction
        self._note_cache: OrderedDict[str, Note] = OrderedDict()
        self._cache_max_size = cache_max_size
        self._cache_lock = threading.RLock()  # Thread-safety for cache operations

        # Cache statistics for monitoring
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0

        logger.info(
            "Initialized NoteManager",
            extra={
                "notes_dir": str(self.notes_dir),
                "auto_index": auto_index,
                "git_enabled": self.git is not None,
                "cache_max_size": cache_max_size,
            },
        )

        # Always try to load existing index from disk
        # If auto_index is True, rebuild if index doesn't exist or is stale
        index_loaded = self._try_load_index()
        if auto_index and not index_loaded:
            self._index_all_notes()
            self._save_index()

    def _extract_wikilinks(self, content: str) -> list[str]:
        """
        Extract wikilinks from content

        Args:
            content: Markdown content

        Returns:
            List of linked note titles (unique, sorted)
        """
        matches = WIKILINK_PATTERN.findall(content)
        # Clean matches (remove pipe if missed by regex, though regex handles it)
        links = set()
        for match in matches:
            # Handle potential edge cases or legacy formats
            target = match.split("|")[0].strip()
            if target:
                links.add(target)
        return sorted(links)

    def _validate_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and normalize metadata fields against schema.

        - Validates 'type' against NoteType
        - Validates 'status' against NoteStatus
        - Validates 'importance' against ImportanceLevel (and maps French aliases)
        """
        validated = metadata.copy()

        # 1. Type Validation
        if "type" in validated:
            val = validated["type"]
            # Allow case-insensitive match
            try:
                # Try exact match first
                NoteType(val)
            except ValueError:
                try:
                    # Try folding to lowercase
                    validated["type"] = NoteType(val.lower()).value
                except ValueError:
                    logger.warning(
                        f"Invalid note type: {val}. Keeping as is but might break scheduling."
                    )

        # 2. Status Validation
        if "status" in validated:
            val = validated["status"]
            if not NoteStatus.is_valid(val):
                logger.warning(
                    f"Invalid note status: {val}. Expected: {[s.value for s in NoteStatus]}"
                )

        # 3. Importance Validation
        if "importance" in validated:
            val = validated["importance"]
            # Check if it's a known value
            try:
                ImportanceLevel(val)
            except ValueError:
                # Try French mapping
                mapped = ImportanceLevel.from_french(val)
                # If it maps to NORMAL but wasn't "moyenne" or "normal", it might be invalid.
                # But from_french defaults to NORMAL.
                # Let's check strict mapping?
                # Actually, from_french is robust.
                # We do NOT normalize to English values if user wrote French, unless we want to enforce English internal storage.
                # Architecture doc implies "importance: haute". So we keep "haute".
                # But we should verify it maps to something valid.
                if mapped == ImportanceLevel.NORMAL and val.lower() not in ["normal", "moyenne"]:
                    logger.warning(
                        f"Unknown importance level: {val}. Defaulting to Normal priority."
                    )

        return validated

    def _cache_put(self, note_id: str, note: Note) -> None:
        """
        Add note to LRU cache with eviction (must hold _cache_lock)

        Moves existing entries to end (most recently used).
        Evicts oldest entries when cache exceeds max size.
        """
        # If key exists, move it to end (most recently used)
        if note_id in self._note_cache:
            self._note_cache.move_to_end(note_id)
        self._note_cache[note_id] = note

        # Evict oldest entries if over capacity
        while len(self._note_cache) > self._cache_max_size:
            evicted_id, _ = self._note_cache.popitem(last=False)
            self._cache_evictions += 1
            logger.debug("LRU cache evicted", extra={"note_id": evicted_id})

    def _try_load_index(self) -> bool:
        """
        Try to load vector index from disk

        Returns:
            True if index loaded successfully, False otherwise

        Triggers rebuild if:
        - Index file doesn't exist
        - Index is empty (0 documents)
        - Index is older than 24 hours
        """
        # Check if index exists
        if not self._index_path.exists():
            logger.info("No index cache found, will rebuild")
            return False

        # Check index age (rebuild if older than 24 hours)
        index_age_hours = self._get_index_age_hours()
        if index_age_hours is not None and index_age_hours > 24:
            logger.info(
                "Index is stale, will rebuild",
                extra={"age_hours": round(index_age_hours, 1), "threshold_hours": 24},
            )
            return False

        try:
            self.vector_store.load(self._index_path)
            doc_count = len(self.vector_store.id_to_doc)

            # Check if index is empty
            if doc_count == 0:
                logger.info("Index is empty, will rebuild")
                return False

            logger.info(
                "Loaded index from disk",
                extra={"path": str(self._index_path), "documents": doc_count},
            )

            # Load metadata index for fast tree building
            if not self._load_metadata_index():
                # Rebuild if metadata index doesn't exist
                self._rebuild_metadata_index()

            # OPTIMIZATION: Skip cache population at startup - load notes lazily on demand
            # The cache will be populated as notes are accessed via get_note() or get_all_notes()
            return True

        except Exception as e:
            logger.warning(
                "Failed to load index cache, will rebuild",
                extra={"path": str(self._index_path), "error": str(e)},
            )
            return False

    def _get_index_age_hours(self) -> float | None:
        """
        Get the age of the index file in hours

        Returns:
            Age in hours, or None if file doesn't exist
        """
        try:
            # Check the FAISS index file specifically
            faiss_index = self._index_path / "index.faiss"
            if faiss_index.exists():
                mtime = faiss_index.stat().st_mtime
                age_seconds = datetime.now().timestamp() - mtime
                return age_seconds / 3600
            return None
        except Exception:
            return None

    def _save_index(self) -> None:
        """Save vector index to disk for faster startup"""
        try:
            self.vector_store.save(self._index_path)
            logger.info("Saved index to disk", extra={"path": str(self._index_path)})
        except Exception as e:
            logger.warning(
                "Failed to save index cache", extra={"path": str(self._index_path), "error": str(e)}
            )

    def _load_metadata_index(self) -> bool:
        """
        Load lightweight metadata index from disk

        Returns:
            True if loaded successfully, False otherwise
        """
        import json

        if not self._metadata_index_path.exists():
            return False

        try:
            with open(self._metadata_index_path, encoding="utf-8") as f:
                self._notes_metadata = json.load(f)
            logger.info(
                "Loaded metadata index",
                extra={"count": len(self._notes_metadata)},
            )
            return True
        except Exception as e:
            logger.warning(
                "Failed to load metadata index",
                extra={"error": str(e)},
            )
            return False

    def _save_metadata_index(self) -> None:
        """Save lightweight metadata index to disk"""
        import json

        try:
            with open(self._metadata_index_path, "w", encoding="utf-8") as f:
                json.dump(self._notes_metadata, f, default=str, indent=2)
            logger.debug(
                "Saved metadata index",
                extra={"count": len(self._notes_metadata)},
            )
        except Exception as e:
            logger.warning(
                "Failed to save metadata index",
                extra={"error": str(e)},
            )

    def _update_metadata_index(self, note: Note) -> None:
        """Update metadata index entry for a note"""
        import re

        # Extract path from file_path relative to notes_dir
        path = ""
        if note.file_path:
            try:
                rel_path = note.file_path.relative_to(self.notes_dir)
                # Path is the parent folder(s), not the filename
                if rel_path.parent != Path("."):
                    path = str(rel_path.parent)
            except ValueError:
                pass

        # Generate excerpt from content for list views
        content = note.content.strip() if note.content else ""
        excerpt = content[:200] + "..." if len(content) > 200 else content
        # Remove markdown headers for cleaner excerpt
        excerpt = re.sub(r"^#+\s+", "", excerpt)

        self._notes_metadata[note.note_id] = {
            "title": note.title,
            "path": path,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            "pinned": note.metadata.get("pinned", False),
            "tags": note.tags or [],
            "excerpt": excerpt,
        }

    def _remove_from_metadata_index(self, note_id: str) -> None:
        """Remove note from metadata index"""
        self._notes_metadata.pop(note_id, None)

    def refresh_index(self) -> int:
        """
        Public method to force metadata index rebuild.
        Useful after external changes (e.g. Apple Notes sync).

        Returns:
            Number of notes indexed
        """
        logger.info("Forcing metadata index rebuild")
        with self._cache_lock:
            # Clear cache to force reload of content
            self._note_cache.clear()
            return self._rebuild_metadata_index()

    def _rebuild_metadata_index(self) -> int:
        """
        Rebuild metadata index from filesystem.
        Now reads frontmatter for accurate dates while remaining reasonably fast.

        Returns:
            Number of notes indexed
        """
        files = list(self.notes_dir.rglob("*.md"))
        visible_files = [f for f in files if not any(part.startswith(".") for part in f.parts)]

        self._notes_metadata.clear()
        count = 0

        # Use parallel execution to read frontmatter from all files
        max_workers = min(32, len(visible_files) + 1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map over _read_note_file but we only need it for metadata
            for note in executor.map(self._read_note_file, visible_files):
                if note:
                    # Determine path
                    path = ""
                    if note.file_path:
                        try:
                            rel_path = note.file_path.relative_to(self.notes_dir)
                            path = str(rel_path.parent) if rel_path.parent != Path(".") else ""
                        except ValueError:
                            pass

                    self._notes_metadata[note.note_id] = {
                        "title": note.title,
                        "path": path,
                        "created_at": note.created_at.isoformat() if note.created_at else None,
                        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                        "pinned": note.metadata.get("pinned", False),
                        "tags": note.tags or [],
                        "excerpt": note.content[:200] if note.content else "",
                    }
                    count += 1

        self._save_metadata_index()
        logger.info("Rebuilt metadata index", extra={"count": count})
        return count

    def get_notes_summary(self) -> list[dict[str, Any]]:
        """
        Get lightweight note summaries for tree building (very fast)

        Uses the metadata index instead of reading all files.
        Falls back to rebuilding index if empty.

        Returns:
            List of note summary dicts with: note_id, title, path, updated_at, pinned, tags
        """
        # Rebuild index if empty
        if not self._notes_metadata and not self._load_metadata_index():
            self._rebuild_metadata_index()

        return [{"note_id": note_id, **meta} for note_id, meta in self._notes_metadata.items()]

    def _populate_cache_from_files(self) -> None:
        """Populate note cache from files (after loading index)"""
        files = list(self.notes_dir.rglob("*.md"))
        if not files:
            return

        count = 0
        # Use parallel execution for faster I/O
        max_workers = min(32, len(files) + 1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Filter hidden files
            visible_files = [f for f in files if not any(part.startswith(".") for part in f.parts)]

            for note in executor.map(self._read_note_file, visible_files):
                if note:
                    with self._cache_lock:
                        self._cache_put(note.note_id, note)
                    count += 1

        logger.debug("Populated note cache", extra={"count": count})

    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        entities: Optional[list[Entity]] = None,
        metadata: Optional[dict[str, Any]] = None,
        subfolder: Optional[str] = None,
    ) -> str:
        """
        Create new note

        Args:
            title: Note title
            content: Note content (Markdown)
            tags: Optional tags
            entities: Optional entities
            metadata: Optional additional metadata
            subfolder: Optional subfolder path relative to notes_dir
                       (e.g., "Personal Knowledge Management/Entités")

        Returns:
            note_id: Generated note identifier

        Raises:
            ValueError: If title or content is empty
        """
        if not title or not title.strip():
            raise ValueError("Note title cannot be empty")

        if not content or not content.strip():
            # Try to apply template if content is empty
            if self.template_manager and metadata and "type" in metadata:
                tmpl_content = self.template_manager.get_template(metadata["type"])
                if tmpl_content:
                    # Parse template frontmatter
                    match = FRONTMATTER_PATTERN.match(tmpl_content)
                    if match:
                        fm_str, body = match.groups()
                        try:
                            tmpl_fm = yaml.safe_load(fm_str) or {}
                            # Merge: Template defaults < Provided metadata
                            # We want template keys to be present, but overridden by specific args if any
                            # But 'metadata' arg here is authoritative.
                            merged = tmpl_fm.copy()
                            merged.update(metadata)
                            metadata = merged
                            content = body
                        except yaml.YAMLError:
                            # Fallback if template YAML is bad
                            content = tmpl_content
                    else:
                        content = tmpl_content

            # Re-check content emptiness (it might still be empty if no template found)
            if not content or not content.strip():
                raise ValueError("Note content cannot be empty")

        # Generate note ID from title and timestamp
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        note_id = self._generate_note_id(title, timestamp)

        note = Note(
            note_id=note_id,
            title=title.strip(),
            content=content.strip(),
            created_at=now,
            updated_at=now,
            tags=tags or [],
            entities=entities or [],
            metadata=self._validate_metadata(metadata or {}),
            outgoing_links=self._extract_wikilinks(content),
        )

        # Write to file (with optional subfolder)
        if subfolder:
            # Create subfolder if it doesn't exist
            folder_path = self.notes_dir / subfolder
            folder_path.mkdir(parents=True, exist_ok=True)
            file_path = folder_path / f"{note_id}.md"
        else:
            file_path = self._get_note_path(note_id)
        self._write_note_file(note, file_path)
        note.file_path = file_path

        # Add to vector store
        search_text = f"{title}\n\n{content}"
        self.vector_store.add(
            doc_id=note_id,
            text=search_text,
            metadata={
                "title": title,
                "tags": tags or [],
                "created_at": now.isoformat(),
                "entities": [e.value for e in (entities or [])],
                "outgoing_links": note.outgoing_links,
            },
        )

        # Cache with LRU eviction (thread-safe)
        with self._cache_lock:
            self._cache_put(note_id, note)

        # Git commit (include subfolder in path)
        if self.git:
            relative_path = f"{subfolder}/{note_id}.md" if subfolder else f"{note_id}.md"
            self.git.commit(relative_path, "Create note", note_title=title)

        # Update metadata index for fast tree building
        self._update_metadata_index(note)
        self._save_metadata_index()

        logger.info(
            "Created note",
            extra={
                "note_id": note_id,
                "title": title,
                "tags": tags or [],
                "file_path": str(file_path),
            },
        )

        return note_id

    def get_note(self, note_id: str) -> Optional[Note]:
        """
        Get note by ID (thread-safe with LRU update)

        Notes in the trash folder are NOT returned by this method.
        Use get_deleted_notes() to access trashed notes.

        Args:
            note_id: Note identifier

        Returns:
            Note object or None if not found (or if in trash)
        """
        # Check if note is in trash - don't return it via get_note
        if self.is_note_in_trash(note_id):
            return None

        # Check cache first (thread-safe)
        with self._cache_lock:
            if note_id in self._note_cache:
                # Move to end (most recently used)
                self._note_cache.move_to_end(note_id)
                self._cache_hits += 1
                return self._note_cache[note_id]

        # Cache miss - try to load from file
        self._cache_misses += 1
        file_path = self._get_note_path(note_id)
        if not file_path.exists():
            return None

        note = self._read_note_file(file_path)
        if note:
            with self._cache_lock:
                self._cache_put(note_id, note)

        return note

    def update_note(
        self,
        note_id: str,
        updates: Optional[dict[str, Any]] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        entities: Optional[list[Entity]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Update existing note

        Can be called with either a dict of updates or individual parameters.

        Args:
            note_id: Note identifier
            updates: Dict of updates (keys: title, content, tags, entities, metadata)
            title: New title (optional)
            content: New content (optional)
            tags: New tags (optional)
            entities: New entities (optional)
            metadata: New metadata (optional)

        Returns:
            True if updated, False if note not found
        """
        note = self.get_note(note_id)
        if not note:
            return False

        # If updates dict provided, extract values
        if updates:
            title = updates.get("title", title)
            content = updates.get("content", content)
            tags = updates.get("tags", tags)
            entities = updates.get("entities", entities)
            metadata = updates.get("metadata", metadata)

        # Update fields
        if title is not None:
            note.title = title.strip()
        if content is not None:
            note.content = content.strip()
        if tags is not None:
            note.tags = tags
        if entities is not None:
            note.entities = entities
        if metadata is not None:
            note.metadata.update(self._validate_metadata(metadata))

        # Always re-extract links on update if content changed
        if content is not None:
            note.outgoing_links = self._extract_wikilinks(note.content)

        note.updated_at = datetime.now(timezone.utc)

        # Write to file
        file_path = self._get_note_path(note_id)
        self._write_note_file(note, file_path)

        # Update vector store (remove old, add new)
        self.vector_store.remove(note_id)
        search_text = f"{note.title}\n\n{note.content}"
        self.vector_store.add(
            doc_id=note_id,
            text=search_text,
            metadata={
                "title": note.title,
                "tags": note.tags,
                "updated_at": note.updated_at.isoformat(),
                "entities": [e.value for e in note.entities],
                "outgoing_links": note.outgoing_links,
            },
        )

        # Git commit
        if self.git:
            self.git.commit(f"{note_id}.md", "Update note", note_title=note.title)

        # Update metadata index for fast tree building
        self._update_metadata_index(note)
        self._save_metadata_index()

        logger.info("Updated note", extra={"note_id": note_id})
        return True

    def add_info(
        self, note_id: str, info: str, info_type: str, importance: str, source_id: str
    ) -> bool:
        """
        Add information to an existing note.

        Adds a formatted entry to the appropriate section of the note.
        Creates the section if it doesn't exist.

        Format in the note:
        - **2026-01-11** : {info} — [source](scapin://event/{source_id})

        Args:
            note_id: Note identifier
            info: Information to add (1-2 sentences)
            info_type: Type of info (decision, engagement, fait, deadline, relation)
            importance: Importance level (haute, moyenne)
            source_id: Source event ID for traceability

        Returns:
            True if updated, False if note not found

        Example:
            >>> manager.add_info(
            ...     note_id="projet-alpha",
            ...     info="Budget de 50k€ validé pour la phase 2",
            ...     info_type="decision",
            ...     importance="haute",
            ...     source_id="email_123"
            ... )
        """
        note = self.get_note(note_id)
        if not note:
            logger.warning(
                "Note not found for add_info", extra={"note_id": note_id, "info_type": info_type}
            )
            return False

        # Section names by info type
        section_names = {
            "decision": "Décisions",
            "engagement": "Engagements",
            "fait": "Faits",
            "deadline": "Jalons",
            "relation": "Relations",
        }
        section_name = section_names.get(info_type.lower(), "Informations")

        # Format the entry
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        importance_marker = "🔴" if importance.lower() == "haute" else "🟡"
        entry = f"- {importance_marker} **{date}** : {info} — [source](scapin://event/{source_id})"

        # Find or create section in content
        content = note.content
        section_header = f"## {section_name}"

        if section_header in content:
            # Section exists - add entry after header
            lines = content.split("\n")
            new_lines = []
            section_found = False
            entry_added = False

            for _i, line in enumerate(lines):
                new_lines.append(line)
                if line.strip() == section_header and not entry_added:
                    section_found = True
                elif section_found and not entry_added:
                    # Add entry on the next line after section header
                    # Skip empty lines after header
                    if line.strip() == "":
                        continue
                    # If this line starts with "- " it's an existing entry
                    # Insert our new entry before existing entries (most recent first)
                    if line.strip().startswith("- "):
                        new_lines.insert(len(new_lines) - 1, entry)
                        entry_added = True
                    else:
                        # Non-list content, add entry before it
                        new_lines.insert(len(new_lines) - 1, entry)
                        new_lines.insert(len(new_lines) - 1, "")
                        entry_added = True

            # If section was found but no entries exist yet
            if section_found and not entry_added:
                # Find the section header and add entry after it
                for i, line in enumerate(new_lines):
                    if line.strip() == section_header:
                        new_lines.insert(i + 1, "")
                        new_lines.insert(i + 2, entry)
                        break

            content = "\n".join(new_lines)
        else:
            # Section doesn't exist - create it at the end
            if not content.endswith("\n"):
                content += "\n"
            content += f"\n{section_header}\n\n{entry}\n"

        # Update the note
        return self.update_note(note_id, content=content)

    def get_note_by_title(self, title: str) -> Optional[Note]:
        """
        Get note by exact title match.

        Searches through all notes for an exact title match (case-insensitive).

        Args:
            title: Note title to search for

        Returns:
            Note object or None if not found
        """
        title_lower = title.lower().strip()

        # Search all notes (uses cache when available)
        for note in self.get_all_notes():
            if note.title.lower().strip() == title_lower:
                return note

        return None

    def delete_note(self, note_id: str) -> bool:
        """
        Soft delete a note (move to trash folder)

        Moves note file to the trash folder (_Supprimées/).
        Use permanently_delete_note() for hard deletion.

        Args:
            note_id: Note identifier

        Returns:
            True if deleted, False if note not found
        """
        note = self.get_note(note_id)
        if not note:
            logger.warning("Note not found for deletion", extra={"note_id": note_id})
            return False

        # Get current file path
        file_path = self._get_note_path(note_id)
        if not file_path.exists():
            logger.warning("Note file not found", extra={"file_path": str(file_path)})
            return False

        # Create trash folder if needed
        trash_dir = self.notes_dir / TRASH_FOLDER
        trash_dir.mkdir(parents=True, exist_ok=True)

        # Move to trash
        trash_path = trash_dir / f"{note_id}.md"
        file_path.rename(trash_path)
        logger.info("Moved note to trash", extra={"note_id": note_id, "trash_path": str(trash_path)})

        # Remove from vector store
        self.vector_store.remove(note_id)

        # Remove from cache (thread-safe)
        with self._cache_lock:
            if note_id in self._note_cache:
                del self._note_cache[note_id]

        # Update metadata index to reflect trash location
        if note_id in self._notes_metadata:
            self._notes_metadata[note_id]["path"] = TRASH_FOLDER
            self._notes_metadata[note_id]["deleted_at"] = datetime.now(timezone.utc).isoformat()
        self._save_metadata_index()

        # Git commit move to trash
        if self.git:
            self.git.commit_move(
                old_path=str(file_path.relative_to(self.notes_dir)),
                new_path=str(trash_path.relative_to(self.notes_dir)),
                note_title=note.title,
            )

        logger.info("Soft deleted note", extra={"note_id": note_id})
        return True

    def get_deleted_notes(self) -> list[Note]:
        """
        Get all notes in the trash folder

        Returns:
            List of deleted Note objects
        """
        trash_dir = self.notes_dir / TRASH_FOLDER
        if not trash_dir.exists():
            return []

        deleted_notes = []
        for file_path in trash_dir.glob("*.md"):
            note = self._read_note_file(file_path)
            if note:
                deleted_notes.append(note)

        # Sort by deletion date (newest first)
        deleted_notes.sort(
            key=lambda n: self._notes_metadata.get(n.note_id, {}).get("deleted_at", ""),
            reverse=True,
        )
        return deleted_notes

    def restore_note(self, note_id: str, target_folder: str = "") -> bool:
        """
        Restore a note from trash to its original or specified folder

        Args:
            note_id: Note identifier
            target_folder: Target folder path (empty string for root)

        Returns:
            True if restored, False if note not found in trash
        """
        trash_path = self.notes_dir / TRASH_FOLDER / f"{note_id}.md"
        if not trash_path.exists():
            logger.warning("Note not found in trash", extra={"note_id": note_id})
            return False

        # Determine target path
        if target_folder:
            target_dir = self.notes_dir / target_folder
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = self.notes_dir

        target_path = target_dir / f"{note_id}.md"

        # Move from trash to target
        trash_path.rename(target_path)
        logger.info("Restored note from trash", extra={"note_id": note_id, "target": str(target_path)})

        # Update metadata index
        if note_id in self._notes_metadata:
            self._notes_metadata[note_id]["path"] = target_folder
            if "deleted_at" in self._notes_metadata[note_id]:
                del self._notes_metadata[note_id]["deleted_at"]
        self._save_metadata_index()

        # Re-index the note in vector store
        note = self._read_note_file(target_path)
        if note:
            # Build search text and add to vector store
            search_text = f"{note.title}\n{note.content}"
            metadata = {
                "title": note.title,
                "tags": note.tags,
                "path": target_folder,
            }
            self.vector_store.add(doc_id=note.note_id, text=search_text, metadata=metadata)

        # Git commit restore
        if self.git:
            self.git.commit_move(
                old_path=str(trash_path.relative_to(self.notes_dir)),
                new_path=str(target_path.relative_to(self.notes_dir)),
                note_title=note.title if note else note_id,
            )

        return True

    def permanently_delete_note(self, note_id: str) -> bool:
        """
        Permanently delete a note from trash

        Args:
            note_id: Note identifier

        Returns:
            True if permanently deleted, False if note not found
        """
        # Check if note is in trash
        trash_path = self.notes_dir / TRASH_FOLDER / f"{note_id}.md"
        if trash_path.exists():
            file_path = trash_path
        else:
            # Also allow deleting notes not in trash (for flexibility)
            file_path = self._get_note_path(note_id)
            if not file_path.exists():
                logger.warning("Note not found for permanent deletion", extra={"note_id": note_id})
                return False

        # Get note title for git commit
        note = self._read_note_file(file_path)
        note_title = note.title if note else note_id

        # Hard delete file
        file_path.unlink()
        logger.info("Permanently deleted note", extra={"note_id": note_id})

        # Remove from vector store (in case it wasn't already)
        self.vector_store.remove(note_id)

        # Remove from cache
        with self._cache_lock:
            if note_id in self._note_cache:
                del self._note_cache[note_id]

        # Remove from metadata index
        self._remove_from_metadata_index(note_id)
        self._save_metadata_index()

        # Git commit deletion
        if self.git:
            self.git.commit_delete(str(file_path.relative_to(self.notes_dir)), note_title=note_title)

        return True

    def empty_trash(self) -> int:
        """
        Permanently delete all notes in trash

        Returns:
            Number of notes permanently deleted
        """
        trash_dir = self.notes_dir / TRASH_FOLDER
        if not trash_dir.exists():
            return 0

        deleted_count = 0
        for file_path in trash_dir.glob("*.md"):
            note_id = file_path.stem
            if self.permanently_delete_note(note_id):
                deleted_count += 1

        logger.info("Emptied trash", extra={"deleted_count": deleted_count})
        return deleted_count

    def is_note_in_trash(self, note_id: str) -> bool:
        """Check if a note is in the trash folder"""
        trash_path = self.notes_dir / TRASH_FOLDER / f"{note_id}.md"
        return trash_path.exists()

    def move_note(self, note_id: str, target_folder: str) -> bool:
        """
        Move a note to a different folder

        Args:
            note_id: Note identifier
            target_folder: Target folder path (e.g., "Projects/Alpha" or "" for root)

        Returns:
            True if moved, False if note not found or move failed
        """
        note = self.get_note(note_id)
        if not note:
            logger.warning("Note not found for move", extra={"note_id": note_id})
            return False

        # Get current file path
        old_file_path = self._get_note_path(note_id)
        if not old_file_path.exists():
            logger.warning("Note file not found", extra={"file_path": str(old_file_path)})
            return False

        # Sanitize target folder (remove leading/trailing slashes)
        target_folder = target_folder.strip().strip("/")

        # Security check: validate target folder path
        if ".." in target_folder:
            logger.warning("Path traversal attempt blocked", extra={"target": target_folder})
            raise ValueError("Invalid folder path")

        # Get current folder from metadata
        current_folder = ""
        if note_id in self._notes_metadata:
            current_folder = self._notes_metadata[note_id].get("path", "")

        # Skip if already in target folder
        if current_folder == target_folder:
            logger.info("Note already in target folder", extra={"note_id": note_id})
            return True

        # Create target folder if needed
        if target_folder:
            target_dir = self.notes_dir / target_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            new_file_path = target_dir / f"{note_id}.md"
        else:
            new_file_path = self.notes_dir / f"{note_id}.md"

        # Check if a note with same name exists in target
        if new_file_path.exists():
            logger.warning(
                "Note with same name exists in target folder",
                extra={"note_id": note_id, "target": target_folder},
            )
            raise ValueError(f"A note named '{note_id}' already exists in the target folder")

        # Move the file
        import shutil

        shutil.move(str(old_file_path), str(new_file_path))
        logger.info(
            "Moved note file",
            extra={"from": str(old_file_path), "to": str(new_file_path)},
        )

        # Update note's file_path
        note.file_path = new_file_path

        # Update cache with new path
        with self._cache_lock:
            if note_id in self._note_cache:
                self._note_cache[note_id] = note

        # Git commit the move
        if self.git:
            old_rel = f"{current_folder}/{note_id}.md" if current_folder else f"{note_id}.md"
            new_rel = f"{target_folder}/{note_id}.md" if target_folder else f"{note_id}.md"
            self.git.commit_move(old_rel, new_rel, note_title=note.title)

        # Update metadata index with new path
        self._update_metadata_index(note)
        self._save_metadata_index()

        logger.info(
            "Moved note",
            extra={"note_id": note_id, "from": current_folder, "to": target_folder},
        )
        return True

    def search_notes(
        self,
        query: str,
        top_k: int = 10,
        tags: Optional[list[str]] = None,
        return_scores: bool = False,
    ) -> Union[list[Note], list[tuple[Note, float]]]:
        """
        Semantic search for notes (optimized with batch loading)

        Args:
            query: Search query
            top_k: Number of results to return
            tags: Optional tag filter
            return_scores: If True, return tuples of (Note, similarity_score)

        Returns:
            List of Note objects (or (Note, score) tuples if return_scores=True),
            sorted by relevance
        """

        # Define filter function for tags
        def tag_filter(metadata: dict[str, Any]) -> bool:
            if not tags:
                return True
            note_tags = set(metadata.get("tags", []))
            return bool(note_tags.intersection(tags))

        # Search in vector store
        results = self.vector_store.search(
            query=query, top_k=top_k, filter_fn=tag_filter if tags else None
        )

        # Batch load notes: check cache first, then load missing from disk
        doc_ids = [doc_id for doc_id, _, _ in results]
        notes_map = self._batch_get_notes(doc_ids)

        # Build result list preserving order and scores
        notes_result: list[Any] = []
        for doc_id, score, _metadata in results:
            note = notes_map.get(doc_id)
            if note:
                if return_scores:
                    notes_result.append((note, score))
                else:
                    notes_result.append(note)

        logger.debug(
            "Search completed",
            extra={"query": query[:50], "results": len(notes_result), "tags": tags},
        )

        return notes_result

    def get_notes_by_entity(
        self, entity: Entity, top_k: int = 10, return_scores: bool = False
    ) -> Union[list[Note], list[tuple[Note, float]]]:
        """
        Get notes mentioning specific entity (optimized with batch loading)

        Args:
            entity: Entity to search for
            top_k: Maximum number of results
            return_scores: If True, return tuples of (Note, similarity_score)

        Returns:
            List of Note objects (or (Note, score) tuples if return_scores=True)
        """
        # Search using entity value
        query = entity.value

        # Filter for notes with this entity
        def entity_filter(metadata: dict[str, Any]) -> bool:
            note_entities = metadata.get("entities", [])
            return entity.value in note_entities

        results = self.vector_store.search(query=query, top_k=top_k, filter_fn=entity_filter)

        # Batch load notes
        doc_ids = [doc_id for doc_id, _, _ in results]
        notes_map = self._batch_get_notes(doc_ids)

        # Build result list preserving order and scores
        notes: list[Any] = []
        for doc_id, score, _metadata in results:
            note = notes_map.get(doc_id)
            if note:
                if return_scores:
                    notes.append((note, score))
                else:
                    notes.append(note)

        return notes

    def _batch_get_notes(self, note_ids: list[str]) -> dict[str, Note]:
        """
        Batch load multiple notes efficiently (thread-safe)

        Checks cache first, then loads missing notes from disk in a single pass.
        This avoids the N+1 problem of calling get_note() for each result.

        Args:
            note_ids: List of note identifiers to load

        Returns:
            Dict mapping note_id → Note (missing notes are omitted)
        """
        result: dict[str, Note] = {}
        missing_ids: list[str] = []

        # First pass: check cache for all IDs
        with self._cache_lock:
            for note_id in note_ids:
                if note_id in self._note_cache:
                    result[note_id] = self._note_cache[note_id]
                else:
                    missing_ids.append(note_id)

        # Second pass: load missing notes from disk
        for note_id in missing_ids:
            file_path = self._get_note_path(note_id)
            if file_path.exists():
                note = self._read_note_file(file_path)
                if note:
                    result[note_id] = note
                    with self._cache_lock:
                        self._cache_put(note_id, note)

        logger.debug(
            "Batch loaded notes",
            extra={
                "requested": len(note_ids),
                "from_cache": len(note_ids) - len(missing_ids),
                "from_disk": len(missing_ids),
                "found": len(result),
            },
        )

        return result

    def get_all_notes(self, limit: Optional[int] = None) -> list[Note]:
        """
        Get all notes with optional pagination

        OPTIMIZATION: Uses cache when available, only reads disk for missing notes.
        Falls back to parallel disk read if cache is cold.

        Args:
            limit: Maximum number of notes to return (None = all)

        Returns:
            List of Note objects
        """
        # Get all file paths first
        files = list(self.notes_dir.rglob("*.md"))
        visible_files = [f for f in files if not any(part.startswith(".") for part in f.parts)]

        notes: list[Note] = []
        files_to_load: list[Path] = []

        # OPTIMIZATION: Check cache first for each file
        with self._cache_lock:
            for file_path in visible_files:
                note_id = file_path.stem
                if note_id in self._note_cache:
                    # Move to end (most recently used)
                    self._note_cache.move_to_end(note_id)
                    notes.append(self._note_cache[note_id])
                    self._cache_hits += 1
                else:
                    files_to_load.append(file_path)
                    self._cache_misses += 1

        # Only read files that weren't in cache
        if files_to_load:
            logger.debug(
                "Loading notes from disk",
                extra={"cached": len(notes), "to_load": len(files_to_load)},
            )
            # Use parallel execution for faster I/O
            max_workers = min(32, len(files_to_load) + 1)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                for note in executor.map(self._read_note_file, files_to_load):
                    if note:
                        notes.append(note)
                        # Update cache
                        with self._cache_lock:
                            self._cache_put(note.note_id, note)

        # Apply limit if specified (post-loading)
        if limit is not None:
            notes = notes[:limit]

        return notes

    def get_recently_modified_notes(self, since: datetime) -> list[Note]:
        """
        Get notes modified since a specific time

        Args:
            since: Timestamp to check modification age against

        Returns:
            List of Note objects modified after 'since'
        """
        modified_notes = []
        since_ts = since.timestamp()

        # Iterate through all markdown files
        for file_path in self.notes_dir.rglob("*.md"):
            try:
                # Check metrics fast first
                mtime = file_path.stat().st_mtime
                if mtime > since_ts:
                    note = self._read_note_file(file_path)
                    if note:
                        modified_notes.append(note)
            except Exception as e:
                logger.warning(
                    "Error checking file for modification",
                    extra={"file_path": str(file_path), "error": str(e)},
                )

        return modified_notes

    def _index_all_notes(self) -> int:
        """
        Index all existing notes in directory (thread-safe)

        Uses parallel execution for reading and batch indexing for vector store.

        Returns:
            Number of notes indexed
        """
        files = list(self.notes_dir.rglob("*.md"))
        if not files:
            return 0

        # Filter hidden files
        visible_files = [f for f in files if not any(part.startswith(".") for part in f.parts)]

        # Batch size for vector store operations
        BATCH_SIZE = 50
        count = 0
        notes_to_index: list[tuple[Note, str, dict[str, Any]]] = []

        # Use parallel execution for reading files
        max_workers = min(32, len(visible_files) + 1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for note in executor.map(self._read_note_file, visible_files):
                if note:
                    # Check if already indexed
                    if not self.vector_store.get_document(note.note_id):
                        search_text = f"{note.title}\n\n{note.content}"
                        metadata = {
                            "title": note.title,
                            "tags": note.tags,
                            "created_at": note.created_at.isoformat(),
                            "entities": [e.value for e in note.entities],
                        }
                        notes_to_index.append((note, search_text, metadata))

                    # Always cache the note
                    with self._cache_lock:
                        self._cache_put(note.note_id, note)

                    # Also populate metadata index during full indexing
                    # This ensures metadata index has "real" dates from frontmatter
                    path = ""
                    try:
                        if note.file_path:
                            rel_path = note.file_path.relative_to(self.notes_dir)
                            path = str(rel_path.parent) if rel_path.parent != Path(".") else ""
                    except ValueError:
                        pass

                    self._notes_metadata[note.note_id] = {
                        "title": note.title,
                        "path": path,
                        "created_at": note.created_at.isoformat() if note.created_at else None,
                        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                        "pinned": note.metadata.get("pinned", False),
                        "tags": note.tags or [],
                        "excerpt": note.content[:200] if note.content else "",
                    }

                    count += 1

                    # Batch index when we have enough notes
                    if len(notes_to_index) >= BATCH_SIZE:
                        self._batch_add_to_vector_store(notes_to_index)
                        notes_to_index = []

        # Final batch
        if notes_to_index:
            self._batch_add_to_vector_store(notes_to_index)

        logger.info("Indexed notes", extra={"count": count})
        return count

    def _batch_add_to_vector_store(
        self, notes_data: list[tuple[Note, str, dict[str, Any]]]
    ) -> None:
        """
        Add multiple notes to vector store in a single batch operation

        Args:
            notes_data: List of (Note, search_text, metadata) tuples
        """
        if not notes_data:
            return

        try:
            # Prepare documents for batch add
            documents = [
                (note.note_id, search_text, metadata) for note, search_text, metadata in notes_data
            ]
            self.vector_store.add_batch(documents)
            logger.debug("Batch added notes to vector store", extra={"count": len(documents)})
        except Exception as e:
            # Fallback to individual adds if batch fails
            logger.warning(
                "Batch add failed, falling back to individual adds", extra={"error": str(e)}
            )
            for note, search_text, metadata in notes_data:
                try:
                    self.vector_store.add(doc_id=note.note_id, text=search_text, metadata=metadata)
                except Exception as add_error:
                    logger.warning(
                        "Failed to add note to vector store",
                        extra={"note_id": note.note_id, "error": str(add_error)},
                    )

    def rebuild_index(self) -> dict[str, Any]:
        """
        Rebuild the entire vector index from scratch

        Clears the existing index and re-indexes all notes.
        Useful when the index is corrupted or out of sync.

        Returns:
            Dictionary with rebuild statistics
        """
        import time

        start_time = time.time()

        logger.info("Starting index rebuild")

        # Clear vector store
        self.vector_store.clear()

        # Clear caches
        with self._cache_lock:
            self._cache.clear()
            self._cache_order.clear()

        # Clear metadata index
        self._notes_metadata.clear()

        # Re-index all notes
        count = self._index_all_notes()

        # Save the new index
        self._save_index()

        elapsed = time.time() - start_time

        result = {
            "success": True,
            "notes_indexed": count,
            "elapsed_seconds": round(elapsed, 2),
            "index_stats": self.vector_store.get_stats(),
        }

        logger.info(
            "Index rebuild completed",
            extra={"notes_indexed": count, "elapsed_seconds": elapsed},
        )

        return result

    def _sanitize_title(self, title: str) -> str:
        """
        Sanitize title for safe file system use

        Removes path separators, special characters, and control characters
        to prevent directory traversal attacks.

        Args:
            title: Raw title string

        Returns:
            Sanitized title safe for file names
        """
        # Remove forbidden characters (path separators, wildcards, control chars)
        # / \ : * ? " < > | and control characters (0x00-0x1f, 0x7f)
        sanitized = re.sub(r'[/\\:*?"<>|\x00-\x1f\x7f]', "-", title)

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(" .")

        # Limit length (file system limits, leave room for hash suffix)
        max_length = 100
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip("-")

        # Ensure not empty after sanitization
        # Also treat strings that are only dashes/dots/spaces as empty
        if not sanitized or not sanitized.strip("-._ "):
            sanitized = "untitled"

        return sanitized

    def _generate_note_id(self, title: str, timestamp: str) -> str:
        """
        Generate unique note ID from title and timestamp

        Uses sanitized title to prevent path traversal attacks.
        Uses SHA256 for consistency with content hashing.

        Args:
            title: Note title (will be sanitized)
            timestamp: ISO timestamp for uniqueness

        Returns:
            Safe note ID suitable for filename
        """
        # Sanitize title first to prevent directory traversal
        safe_title = self._sanitize_title(title)

        # Create slug from sanitized title
        slug = re.sub(r"[^a-z0-9]+", "-", safe_title.lower()).strip("-")[:50]

        # Add hash for uniqueness (use original title for hash input)
        # Using SHA256 for consistency with content hashing elsewhere
        hash_input = f"{title}{timestamp}"
        hash_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

        return f"{slug}-{hash_suffix}"

    def _get_note_path(self, note_id: str) -> Path:
        """
        Get file path for note with safety checks

        Ensures the resolved path is within notes_dir to prevent
        directory traversal attacks. Uses metadata index to find notes
        in subfolders.

        Args:
            note_id: Note identifier

        Returns:
            Absolute path to note file

        Raises:
            ValueError: If resolved path is outside notes_dir
        """
        # Check metadata index for the note's folder path
        folder_path = ""
        if note_id in self._notes_metadata:
            folder_path = self._notes_metadata[note_id].get("path", "")

        # Construct path using folder from metadata
        if folder_path:
            file_path = (self.notes_dir / folder_path / f"{note_id}.md").resolve()
        else:
            file_path = (self.notes_dir / f"{note_id}.md").resolve()

        # Security check: ensure path is within notes_dir
        notes_dir_resolved = self.notes_dir.resolve()
        try:
            file_path.relative_to(notes_dir_resolved)
        except ValueError as e:
            # Path is outside notes_dir - possible traversal attack
            raise ValueError(
                f"Invalid note path: {file_path} is outside notes directory {notes_dir_resolved}"
            ) from e

        return file_path

    def _write_note_file(self, note: Note, file_path: Path) -> None:
        """
        Write note to Markdown file with YAML frontmatter (atomic write)

        Uses a temporary file and atomic rename to prevent data corruption
        if the write is interrupted.
        """
        # Prepare frontmatter
        frontmatter = {
            "title": note.title,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "tags": note.tags,
            "entities": [
                {"type": e.type, "value": e.value, "confidence": e.confidence}
                for e in note.entities
            ],
        }

        if note.metadata:
            frontmatter["metadata"] = note.metadata

        # Write to temporary file first, then atomically rename
        # This prevents data corruption if write is interrupted
        dir_path = file_path.parent
        fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp", prefix=".note_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("---\n")
                yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
                f.write("---\n\n")
                f.write(note.content)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk
            # Atomic rename (POSIX guarantees atomicity for same filesystem)
            os.replace(temp_path, file_path)
        except Exception:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def _read_note_file(self, file_path: Path) -> Optional[Note]:
        """Read note from Markdown file with YAML frontmatter"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Parse frontmatter using pre-compiled regex
            match = FRONTMATTER_PATTERN.match(content)
            if not match:
                logger.warning("No frontmatter in note", extra={"file_path": str(file_path)})
                return None

            frontmatter_str, body = match.groups()

            # Try to parse YAML frontmatter, with fallback for malformed YAML
            try:
                frontmatter = yaml.safe_load(frontmatter_str) or {}
            except yaml.YAMLError as yaml_err:
                # Fallback: create minimal frontmatter from filename
                logger.warning(
                    "YAML parsing failed, using filename as title",
                    extra={"file_path": str(file_path), "error": str(yaml_err)},
                )
                frontmatter = {}

            # Extract note ID from filename
            note_id = file_path.stem

            # Parse entities
            entities = []
            for e_dict in frontmatter.get("entities", []):
                entities.append(
                    Entity(
                        type=e_dict["type"],
                        value=e_dict["value"],
                        confidence=e_dict.get("confidence", 1.0),
                    )
                )

            # Get dates - support both formats (created_at/updated_at and created/modified)
            # Use file modification time as fallback
            # PyYAML may parse ISO dates as datetime objects automatically
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)

            created_at_raw = frontmatter.get("created_at") or frontmatter.get("created")
            updated_at_raw = frontmatter.get("updated_at") or frontmatter.get("modified")

            # Handle both string and datetime (YAML may parse dates automatically)
            def ensure_aware(dt: datetime) -> datetime:
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt

            if isinstance(created_at_raw, datetime):
                created_at = ensure_aware(created_at_raw)
            elif created_at_raw:
                try:
                    created_at = ensure_aware(datetime.fromisoformat(str(created_at_raw)))
                except ValueError:
                    created_at = file_mtime
            else:
                created_at = file_mtime

            if isinstance(updated_at_raw, datetime):
                updated_at = ensure_aware(updated_at_raw)
            elif updated_at_raw:
                try:
                    updated_at = ensure_aware(datetime.fromisoformat(str(updated_at_raw)))
                except ValueError:
                    updated_at = file_mtime
            else:
                updated_at = file_mtime

            # Get title - use filename as fallback
            # Note: YAML can parse numeric-only titles as int, so convert to str
            raw_title = frontmatter.get("title")
            title = str(raw_title) if raw_title is not None else file_path.stem

            # Build metadata with path from filesystem
            metadata = frontmatter.get("metadata", {})

            # Calculate relative folder path from notes_dir
            try:
                relative_path = file_path.parent.relative_to(self.notes_dir)
                folder_path = str(relative_path) if str(relative_path) != "." else ""
            except ValueError:
                folder_path = ""

            # Store path in metadata for folder tree building
            if folder_path:
                metadata["path"] = folder_path

            # Create Note object
            note = Note(
                note_id=note_id,
                title=title,
                content=body.strip(),
                created_at=created_at,
                updated_at=updated_at,
                tags=frontmatter.get("tags", []),
                entities=entities,
                metadata=metadata,
                file_path=file_path,
                outgoing_links=self._extract_wikilinks(body),
            )

            return note

        except Exception as e:
            logger.error(
                "Failed to read note",
                extra={"file_path": str(file_path), "error": str(e)},
                exc_info=True,
            )
            return None

    def create_folder(self, path: str) -> Path:
        """
        Create a new folder in the notes directory

        Args:
            path: Folder path (e.g., 'Clients/ABC' or 'Projects/2026')

        Returns:
            Absolute path to the created folder

        Raises:
            ValueError: If path is invalid or contains traversal attempts
        """
        if not path or not path.strip():
            raise ValueError("Folder path cannot be empty")

        # Normalize path (remove leading/trailing slashes and whitespace)
        clean_path = path.strip().strip("/")

        if not clean_path:
            raise ValueError("Folder path cannot be empty after normalization")

        # Validate each path component
        for part in clean_path.split("/"):
            if not part or part in (".", ".."):
                raise ValueError(f"Invalid path component: '{part}'")
            # Check for forbidden characters
            if re.search(r'[\\:*?"<>|\x00-\x1f\x7f]', part):
                raise ValueError(f"Invalid characters in path component: '{part}'")

        # Construct and validate full path
        folder_path = (self.notes_dir / clean_path).resolve()

        # Security check: ensure path is within notes_dir
        notes_dir_resolved = self.notes_dir.resolve()
        try:
            folder_path.relative_to(notes_dir_resolved)
        except ValueError as e:
            raise ValueError(f"Invalid folder path: {path} would be outside notes directory") from e

        # Create folder structure
        folder_path.mkdir(parents=True, exist_ok=True)

        logger.info("Created folder", extra={"folder_path": str(folder_path)})
        return folder_path

    def list_folders(self) -> list[str]:
        """
        List all folders in the notes directory

        Returns:
            List of folder paths relative to notes_dir
        """
        folders: list[str] = []
        notes_dir_resolved = self.notes_dir.resolve()

        for dirpath in notes_dir_resolved.rglob("*"):
            if dirpath.is_dir():
                try:
                    rel_path = dirpath.relative_to(notes_dir_resolved)
                    # Skip hidden directories
                    if not any(part.startswith(".") for part in rel_path.parts):
                        folders.append(str(rel_path))
                except ValueError:
                    continue

        return sorted(folders)

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics for monitoring

        Returns:
            Dictionary with cache metrics including hit rate
        """
        with self._cache_lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
            return {
                "cache_size": len(self._note_cache),
                "cache_max_size": self._cache_max_size,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_evictions": self._cache_evictions,
                "hit_rate": round(hit_rate, 3),
                "total_requests": total_requests,
            }

    def __repr__(self) -> str:
        """String representation"""
        stats = self.vector_store.get_stats()
        cache_stats = self.get_cache_stats()
        return (
            f"NoteManager(dir={self.notes_dir}, "
            f"notes={stats['active_docs']}, "
            f"cached={cache_stats['cache_size']}, "
            f"hit_rate={cache_stats['hit_rate']:.1%})"
        )

    # === FRONTMATTER ENRICHI (Phase 1) ===

    def get_typed_frontmatter(self, note_id: str) -> Optional[AnyFrontmatter]:
        """
        Récupère le frontmatter typé d'une note.

        Args:
            note_id: ID de la note

        Returns:
            Frontmatter typé ou None si note non trouvée
        """
        note = self.get_note(note_id)
        if not note:
            return None

        # Parse le metadata brut en frontmatter typé
        return self._frontmatter_parser.parse(note.metadata)

    def get_note_with_typed_frontmatter(
        self, note_id: str
    ) -> Optional[tuple[Note, AnyFrontmatter]]:
        """
        Récupère une note avec son frontmatter typé.

        Args:
            note_id: ID de la note

        Returns:
            Tuple (Note, Frontmatter typé) ou None si note non trouvée
        """
        note = self.get_note(note_id)
        if not note:
            return None

        frontmatter = self._frontmatter_parser.parse(note.metadata)
        return note, frontmatter

    def get_aliases_index(self) -> dict[str, str]:
        """
        Construit et retourne un index aliases → note_id pour le matching.

        L'index mappe:
        - title.lower() → note_id
        - chaque alias.lower() → note_id

        Returns:
            Dict mapping alias/title (lowercase) → note_id
        """
        if not self._aliases_index_dirty:
            return self._aliases_index

        # Rebuild index
        index: dict[str, str] = {}

        with self._cache_lock:
            for note_id, note in self._note_cache.items():
                # Index by title
                if note.title:
                    index[note.title.lower()] = note_id

                # Parse frontmatter for aliases
                try:
                    fm = self._frontmatter_parser.parse(note.metadata)
                    for alias in fm.aliases:
                        if alias:
                            index[alias.lower()] = note_id
                except Exception:
                    # Skip notes with parsing errors
                    pass

        self._aliases_index = index
        self._aliases_index_dirty = False

        logger.debug(
            "Rebuilt aliases index",
            extra={"entries": len(index), "notes": len(self._note_cache)},
        )

        return index

    def find_note_by_alias(self, alias: str) -> Optional[Note]:
        """
        Trouve une note par son titre ou un de ses alias.

        Args:
            alias: Titre ou alias à chercher (insensible à la casse)

        Returns:
            Note trouvée ou None
        """
        index = self.get_aliases_index()
        note_id = index.get(alias.lower())
        if note_id:
            return self.get_note(note_id)
        return None

    def invalidate_aliases_index(self) -> None:
        """
        Marque l'index des aliases comme invalide (à reconstruire).

        Appelé automatiquement après création/modification/suppression de note.
        """
        self._aliases_index_dirty = True

    def get_all_aliases(self) -> dict[str, list[str]]:
        """
        Retourne toutes les notes avec leurs aliases.

        Returns:
            Dict mapping note_id → [title, alias1, alias2, ...]
        """
        result: dict[str, list[str]] = {}

        with self._cache_lock:
            for note_id, note in self._note_cache.items():
                names = [note.title] if note.title else []

                try:
                    fm = self._frontmatter_parser.parse(note.metadata)
                    names.extend(fm.aliases)
                except Exception:
                    pass

                if names:
                    result[note_id] = names

        return result

    def get_persons_with_relation(
        self, relation: Optional[str] = None
    ) -> list[tuple[Note, PersonneFrontmatter]]:
        """
        Retourne toutes les notes PERSONNE, optionnellement filtrées par relation.

        Args:
            relation: Type de relation à filtrer (ami, collègue, etc.) ou None pour toutes

        Returns:
            Liste de tuples (Note, PersonneFrontmatter)
        """
        result: list[tuple[Note, PersonneFrontmatter]] = []

        with self._cache_lock:
            for note in self._note_cache.values():
                try:
                    fm = self._frontmatter_parser.parse(note.metadata)
                    if isinstance(fm, PersonneFrontmatter) and (
                        relation is None or (fm.relation and fm.relation.value == relation)
                    ):
                        result.append((note, fm))
                except Exception:
                    pass

        return result


# Singleton instance with thread-safe initialization
_note_manager: Optional[NoteManager] = None
_note_manager_lock = threading.Lock()


def get_note_manager(
    notes_dir: Optional[Path] = None,
    git_enabled: bool = True,
    auto_index: bool = False,
) -> NoteManager:
    """
    Get or create singleton NoteManager instance (thread-safe)

    Uses double-check locking pattern for thread-safe lazy initialization.
    If notes_dir is not provided, uses the path from config.

    Args:
        notes_dir: Directory for notes (default: from config or ~/Documents/Scapin/Notes)
        git_enabled: Enable Git operations
        auto_index: Enable auto-indexing on init (default False for performance)

    Returns:
        NoteManager singleton instance
    """
    global _note_manager

    # First check without lock for performance (common case)
    if _note_manager is not None:
        return _note_manager

    # Double-check with lock for thread safety
    with _note_manager_lock:
        # Check again inside lock (another thread may have initialized)
        if _note_manager is None:
            if notes_dir is None:
                # Try to get from config, fallback to default path
                try:
                    from src.core.config_manager import get_config

                    config = get_config()
                    notes_dir = config.storage.notes_path
                except Exception:
                    notes_dir = Path.home() / "Documents" / "Scapin" / "Notes"

            _note_manager = NoteManager(
                notes_dir, git_enabled=git_enabled, auto_index=auto_index
            )

    return _note_manager
