"""
Note Manager with Markdown and Vector Search

Manages notes stored as Markdown files with YAML frontmatter.
Provides semantic search via vector store integration.
"""

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
from src.passepartout.git_versioning import GitVersionManager
from src.passepartout.vector_store import VectorStore

logger = get_logger("passepartout.note_manager")

# LRU Cache configuration
DEFAULT_CACHE_MAX_SIZE = 500  # Maximum notes to keep in memory

# Pre-compiled regex for frontmatter parsing (performance optimization)
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)$', re.DOTALL)


@dataclass(slots=True)
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
            "file_path": str(self.file_path) if self.file_path else None
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

        # Initialize embedder and vector store
        self.embedder = embedder if embedder is not None else EmbeddingGenerator()
        self.vector_store = vector_store if vector_store is not None else VectorStore(
            dimension=self.embedder.get_dimension(),
            embedder=self.embedder
        )

        # Initialize Git versioning if enabled
        self.git: Optional[GitVersionManager] = None
        if git_enabled:
            try:
                self.git = GitVersionManager(self.notes_dir)
                logger.info("Git versioning enabled for notes")
            except Exception as e:
                logger.warning(
                    "Failed to initialize Git versioning",
                    extra={"error": str(e)}
                )
                self.git = None

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
            }
        )

        # Index existing notes
        if auto_index:
            self._index_all_notes()

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

    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        entities: Optional[list[Entity]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Create new note

        Args:
            title: Note title
            content: Note content (Markdown)
            tags: Optional tags
            entities: Optional entities
            metadata: Optional additional metadata

        Returns:
            note_id: Generated note identifier

        Raises:
            ValueError: If title or content is empty
        """
        if not title or not title.strip():
            raise ValueError("Note title cannot be empty")

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
            metadata=metadata or {}
        )

        # Write to file
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
                "entities": [e.value for e in (entities or [])]
            }
        )

        # Cache with LRU eviction (thread-safe)
        with self._cache_lock:
            self._cache_put(note_id, note)

        # Git commit
        if self.git:
            self.git.commit(f"{note_id}.md", "Create note", note_title=title)

        logger.info(
            "Created note",
            extra={
                "note_id": note_id,
                "title": title,
                "tags": tags or [],
                "file_path": str(file_path)
            }
        )

        return note_id

    def get_note(self, note_id: str) -> Optional[Note]:
        """
        Get note by ID (thread-safe with LRU update)

        Args:
            note_id: Note identifier

        Returns:
            Note object or None if not found
        """
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
        metadata: Optional[dict[str, Any]] = None
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
            note.metadata.update(metadata)

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
                "entities": [e.value for e in note.entities]
            }
        )

        # Git commit
        if self.git:
            self.git.commit(f"{note_id}.md", "Update note", note_title=note.title)

        logger.info("Updated note", extra={"note_id": note_id})
        return True

    def delete_note(self, note_id: str) -> bool:
        """
        Delete a note

        Removes note file from disk and from vector store.

        Args:
            note_id: Note identifier

        Returns:
            True if deleted, False if note not found
        """
        note = self.get_note(note_id)
        if not note:
            logger.warning("Note not found for deletion", extra={"note_id": note_id})
            return False

        # Remove from vector store
        self.vector_store.remove(note_id)

        # Remove from cache (thread-safe)
        with self._cache_lock:
            if note_id in self._note_cache:
                del self._note_cache[note_id]

        # Delete file
        file_path = self._get_note_path(note_id)
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted note file", extra={"file_path": str(file_path)})

            # Git commit deletion
            if self.git:
                self.git.commit_delete(f"{note_id}.md", note_title=note.title)

        logger.info("Deleted note", extra={"note_id": note_id})
        return True

    def search_notes(
        self,
        query: str,
        top_k: int = 10,
        tags: Optional[list[str]] = None,
        return_scores: bool = False
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
            query=query,
            top_k=top_k,
            filter_fn=tag_filter if tags else None
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
            extra={
                "query": query[:50],
                "results": len(notes_result),
                "tags": tags
            }
        )

        return notes_result

    def get_notes_by_entity(
        self,
        entity: Entity,
        top_k: int = 10,
        return_scores: bool = False
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

        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            filter_fn=entity_filter
        )

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
            }
        )

        return result

    def get_all_notes(self, limit: int | None = None) -> list[Note]:
        """
        Get all notes with optional pagination

        Args:
            limit: Maximum number of notes to return (None = all)

        Returns:
            List of Note objects
        """
        notes = []
        for file_path in self.notes_dir.glob("*.md"):
            note = self._read_note_file(file_path)
            if note:
                notes.append(note)
                with self._cache_lock:
                    self._cache_put(note.note_id, note)

            # Apply limit if specified
            if limit is not None and len(notes) >= limit:
                break

        return notes

    def _index_all_notes(self) -> int:
        """
        Index all existing notes in directory (thread-safe)

        Uses batch indexing for better performance with large note collections.

        Returns:
            Number of notes indexed
        """
        # Batch size for vector store operations
        BATCH_SIZE = 50

        notes_to_index: list[tuple[Note, str, dict[str, Any]]] = []
        count = 0

        for file_path in self.notes_dir.glob("*.md"):
            try:
                note = self._read_note_file(file_path)
                if note:
                    # Check if already indexed
                    if not self.vector_store.get_document(note.note_id):
                        search_text = f"{note.title}\n\n{note.content}"
                        metadata = {
                            "title": note.title,
                            "tags": note.tags,
                            "created_at": note.created_at.isoformat(),
                            "entities": [e.value for e in note.entities]
                        }
                        notes_to_index.append((note, search_text, metadata))

                    # Always cache the note
                    with self._cache_lock:
                        self._cache_put(note.note_id, note)
                    count += 1

                    # Batch index when we have enough notes
                    if len(notes_to_index) >= BATCH_SIZE:
                        self._batch_add_to_vector_store(notes_to_index)
                        notes_to_index = []

            except Exception as e:
                logger.warning(
                    "Failed to index note",
                    extra={"file_path": str(file_path), "error": str(e)}
                )
                continue

        # Index any remaining notes
        if notes_to_index:
            self._batch_add_to_vector_store(notes_to_index)

        logger.info("Indexed notes", extra={"count": count})
        return count

    def _batch_add_to_vector_store(
        self,
        notes_data: list[tuple[Note, str, dict[str, Any]]]
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
                (note.note_id, search_text, metadata)
                for note, search_text, metadata in notes_data
            ]
            self.vector_store.add_batch(documents)
            logger.debug(
                "Batch added notes to vector store",
                extra={"count": len(documents)}
            )
        except Exception as e:
            # Fallback to individual adds if batch fails
            logger.warning(
                "Batch add failed, falling back to individual adds",
                extra={"error": str(e)}
            )
            for note, search_text, metadata in notes_data:
                try:
                    self.vector_store.add(
                        doc_id=note.note_id,
                        text=search_text,
                        metadata=metadata
                    )
                except Exception as add_error:
                    logger.warning(
                        "Failed to add note to vector store",
                        extra={"note_id": note.note_id, "error": str(add_error)}
                    )

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
        sanitized = re.sub(r'[/\\:*?"<>|\x00-\x1f\x7f]', '-', title)

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')

        # Limit length (file system limits, leave room for hash suffix)
        max_length = 100
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip('-')

        # Ensure not empty after sanitization
        # Also treat strings that are only dashes/dots/spaces as empty
        if not sanitized or not sanitized.strip('-._ '):
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
        slug = re.sub(r'[^a-z0-9]+', '-', safe_title.lower()).strip('-')[:50]

        # Add hash for uniqueness (use original title for hash input)
        # Using SHA256 for consistency with content hashing elsewhere
        hash_input = f"{title}{timestamp}"
        hash_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

        return f"{slug}-{hash_suffix}"

    def _get_note_path(self, note_id: str) -> Path:
        """
        Get file path for note with safety checks

        Ensures the resolved path is within notes_dir to prevent
        directory traversal attacks.

        Args:
            note_id: Note identifier

        Returns:
            Absolute path to note file

        Raises:
            ValueError: If resolved path is outside notes_dir
        """
        # Construct path
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
            ]
        }

        if note.metadata:
            frontmatter["metadata"] = note.metadata

        # Write to temporary file first, then atomically rename
        # This prevents data corruption if write is interrupted
        dir_path = file_path.parent
        fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp", prefix=".note_")
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
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
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter using pre-compiled regex
            match = FRONTMATTER_PATTERN.match(content)
            if not match:
                logger.warning(
                    "No frontmatter in note",
                    extra={"file_path": str(file_path)}
                )
                return None

            frontmatter_str, body = match.groups()
            frontmatter = yaml.safe_load(frontmatter_str)

            # Extract note ID from filename
            note_id = file_path.stem

            # Parse entities
            entities = []
            for e_dict in frontmatter.get("entities", []):
                entities.append(Entity(
                    type=e_dict["type"],
                    value=e_dict["value"],
                    confidence=e_dict.get("confidence", 1.0)
                ))

            # Create Note object
            note = Note(
                note_id=note_id,
                title=frontmatter["title"],
                content=body.strip(),
                created_at=datetime.fromisoformat(frontmatter["created_at"]),
                updated_at=datetime.fromisoformat(frontmatter["updated_at"]),
                tags=frontmatter.get("tags", []),
                entities=entities,
                metadata=frontmatter.get("metadata", {}),
                file_path=file_path
            )

            return note

        except Exception as e:
            logger.error(
                "Failed to read note",
                extra={"file_path": str(file_path), "error": str(e)},
                exc_info=True
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
            raise ValueError(
                f"Invalid folder path: {path} would be outside notes directory"
            ) from e

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
            hit_rate = (
                self._cache_hits / total_requests if total_requests > 0 else 0.0
            )
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


# Singleton instance with thread-safe initialization
_note_manager: Optional[NoteManager] = None
_note_manager_lock = threading.Lock()


def get_note_manager(
    notes_dir: Optional[Path] = None,
    git_enabled: bool = True
) -> NoteManager:
    """
    Get or create singleton NoteManager instance (thread-safe)

    Uses double-check locking pattern for thread-safe lazy initialization.

    Args:
        notes_dir: Directory for notes (default: ~/Documents/Notes)
        git_enabled: Enable Git operations

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
                notes_dir = Path.home() / "Documents" / "Notes"

            _note_manager = NoteManager(notes_dir, git_enabled=git_enabled)

    return _note_manager
