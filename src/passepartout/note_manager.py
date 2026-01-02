"""
Note Manager with Markdown and Vector Search

Manages notes stored as Markdown files with YAML frontmatter.
Provides semantic search via vector store integration.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from src.core.events import Entity
from src.monitoring.logger import get_logger
from src.passepartout.embeddings import EmbeddingGenerator
from src.passepartout.vector_store import VectorStore

logger = get_logger("passepartout.note_manager")


@dataclass
class Note:
    """
    Note data structure

    Represents a single note with metadata and content.
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
        auto_index: bool = True
    ):
        """
        Initialize note manager

        Args:
            notes_dir: Directory to store notes
            vector_store: VectorStore instance (creates new if None)
            embedder: EmbeddingGenerator instance (creates new if None)
            auto_index: Whether to automatically index existing notes on init

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

        # In-memory note cache: note_id → Note
        self._note_cache: dict[str, Note] = {}

        logger.info(
            "Initialized NoteManager",
            extra={
                "notes_dir": str(self.notes_dir),
                "auto_index": auto_index
            }
        )

        # Index existing notes
        if auto_index:
            self._index_all_notes()

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
        timestamp = datetime.now().isoformat()
        note_id = self._generate_note_id(title, timestamp)

        now = datetime.now()
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

        # Cache
        self._note_cache[note_id] = note

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
        Get note by ID

        Args:
            note_id: Note identifier

        Returns:
            Note object or None if not found
        """
        # Check cache first
        if note_id in self._note_cache:
            return self._note_cache[note_id]

        # Try to load from file
        file_path = self._get_note_path(note_id)
        if not file_path.exists():
            return None

        note = self._read_note_file(file_path)
        if note:
            self._note_cache[note_id] = note

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

        note.updated_at = datetime.now()

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

        logger.info(f"Updated note: {note_id}")
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
            logger.warning(f"Note not found for deletion: {note_id}")
            return False

        # Remove from vector store
        self.vector_store.remove(note_id)

        # Remove from cache
        if note_id in self._note_cache:
            del self._note_cache[note_id]

        # Delete file
        file_path = self._get_note_path(note_id)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted note file: {file_path}")

            # Git commit
            if self.git:
                try:
                    self.git.commit(f"Delete note: {note.title}")
                except Exception as e:
                    logger.warning(f"Git commit failed: {e}")

        logger.info(f"Deleted note: {note_id}")
        return True

    def search_notes(
        self,
        query: str,
        top_k: int = 10,
        tags: Optional[list[str]] = None,
        return_scores: bool = False
    ) -> Union[list[Note], list[tuple[Note, float]]]:
        """
        Semantic search for notes

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

        # Convert to Note objects (with scores if requested)
        notes = []
        for doc_id, score, _metadata in results:
            note = self.get_note(doc_id)
            if note:
                if return_scores:
                    notes.append((note, score))
                else:
                    notes.append(note)

        logger.debug(
            "Search completed",
            extra={
                "query": query[:50],
                "results": len(notes),
                "tags": tags
            }
        )

        return notes

    def get_notes_by_entity(
        self,
        entity: Entity,
        top_k: int = 10,
        return_scores: bool = False
    ) -> Union[list[Note], list[tuple[Note, float]]]:
        """
        Get notes mentioning specific entity

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

        notes = []
        for doc_id, score, _metadata in results:
            note = self.get_note(doc_id)
            if note:
                if return_scores:
                    notes.append((note, score))
                else:
                    notes.append(note)

        return notes

    def get_all_notes(self) -> list[Note]:
        """
        Get all notes

        Returns:
            List of all Note objects
        """
        notes = []
        for file_path in self.notes_dir.glob("*.md"):
            note = self._read_note_file(file_path)
            if note:
                notes.append(note)
                self._note_cache[note.note_id] = note

        return notes

    def _index_all_notes(self) -> int:
        """
        Index all existing notes in directory

        Returns:
            Number of notes indexed
        """
        count = 0
        for file_path in self.notes_dir.glob("*.md"):
            try:
                note = self._read_note_file(file_path)
                if note:
                    # Add to vector store if not already there
                    if not self.vector_store.get_document(note.note_id):
                        search_text = f"{note.title}\n\n{note.content}"
                        self.vector_store.add(
                            doc_id=note.note_id,
                            text=search_text,
                            metadata={
                                "title": note.title,
                                "tags": note.tags,
                                "created_at": note.created_at.isoformat(),
                                "entities": [e.value for e in note.entities]
                            }
                        )

                    self._note_cache[note.note_id] = note
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to index note {file_path}: {e}")
                continue

        logger.info(f"Indexed {count} notes")
        return count

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
        hash_input = f"{title}{timestamp}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]

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
        except ValueError:
            # Path is outside notes_dir - possible traversal attack
            raise ValueError(
                f"Invalid note path: {file_path} is outside notes directory {notes_dir_resolved}"
            )

        return file_path

    def _write_note_file(self, note: Note, file_path: Path) -> None:
        """Write note to Markdown file with YAML frontmatter"""
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

        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("---\n")
            yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
            f.write("---\n\n")
            f.write(note.content)

    def _read_note_file(self, file_path: Path) -> Optional[Note]:
        """Read note from Markdown file with YAML frontmatter"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
            if not match:
                logger.warning(f"No frontmatter in note: {file_path}")
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
            logger.error(f"Failed to read note {file_path}: {e}", exc_info=True)
            return None

    def __repr__(self) -> str:
        """String representation"""
        stats = self.vector_store.get_stats()
        return (
            f"NoteManager(dir={self.notes_dir}, "
            f"notes={stats['active_docs']}, "
            f"cached={len(self._note_cache)})"
        )


# Singleton instance
_note_manager: Optional[NoteManager] = None


def get_note_manager(
    notes_dir: Optional[Path] = None,
    git_enabled: bool = True
) -> NoteManager:
    """
    Get or create singleton NoteManager instance

    Args:
        notes_dir: Directory for notes (default: ~/Documents/Notes)
        git_enabled: Enable Git operations

    Returns:
        NoteManager singleton instance
    """
    global _note_manager

    if _note_manager is None:
        if notes_dir is None:
            notes_dir = Path.home() / "Documents" / "Notes"

        _note_manager = NoteManager(notes_dir, git_enabled)

    return _note_manager
