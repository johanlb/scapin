"""
Note Metadata Store

SQLite storage for note review metadata and spaced repetition data.
Separates revision metadata from note content for performance and flexibility.
"""

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue

from src.monitoring.logger import get_logger
from src.passepartout.note_types import (
    ImportanceLevel,
    NoteType,
    get_review_config,
)

# Connection pool configuration
DEFAULT_POOL_SIZE = 5
CONNECTION_TIMEOUT = 30.0  # seconds

logger = get_logger("passepartout.note_metadata")

# Database schema version for migrations
SCHEMA_VERSION = 1


@dataclass
class EnrichmentRecord:
    """Record of a single enrichment action"""

    timestamp: datetime
    action_type: str  # add, update, remove, link
    target: str  # Section or content target
    content: str | None  # New content if applicable
    confidence: float
    applied: bool  # Whether it was auto-applied
    reasoning: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type,
            "target": self.target,
            "content": self.content,
            "confidence": self.confidence,
            "applied": self.applied,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EnrichmentRecord":
        """Create from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action_type=data["action_type"],
            target=data["target"],
            content=data.get("content"),
            confidence=data["confidence"],
            applied=data["applied"],
            reasoning=data.get("reasoning", ""),
        )


@dataclass
class NoteMetadata:
    """
    Complete metadata for a note's review state

    Stores all information needed for spaced repetition scheduling
    and enrichment tracking, separate from the note content itself.
    """

    note_id: str
    note_type: NoteType = NoteType.AUTRE

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None
    next_review: datetime | None = None

    # SM-2 Algorithm state
    easiness_factor: float = 2.5  # 1.3 - 2.5
    repetition_number: int = 0  # Consecutive successful reviews
    interval_hours: float = 2.0  # Current interval in hours

    # Tracking
    review_count: int = 0
    last_quality: int | None = None  # 0-5, last review quality
    content_hash: str = ""  # SHA256 to detect external changes

    # Configuration
    importance: ImportanceLevel = ImportanceLevel.NORMAL
    auto_enrich: bool = True
    web_search_enabled: bool = False

    # History (stored as JSON)
    enrichment_history: list[EnrichmentRecord] = field(default_factory=list)

    def is_due_for_review(self, now: datetime | None = None) -> bool:
        """Check if note is due for review"""
        if now is None:
            now = datetime.now(timezone.utc)
        # Ensure now is timezone-aware
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if self.next_review is None:
            return True

        # Ensure next_review is timezone-aware
        if self.next_review.tzinfo is None:
            next_review = self.next_review.replace(tzinfo=timezone.utc)
        else:
            next_review = self.next_review

        return now >= next_review

    def days_until_review(self, now: datetime | None = None) -> float:
        """Calculate days until next review (negative if overdue)"""
        if now is None:
            now = datetime.now(timezone.utc)
        # Ensure now is timezone-aware
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if self.next_review is None:
            return -1.0  # Overdue

        # Ensure next_review is timezone-aware
        if self.next_review.tzinfo is None:
            next_review = self.next_review.replace(tzinfo=timezone.utc)
        else:
            next_review = self.next_review

        delta = next_review - now
        return delta.total_seconds() / 86400  # Convert to days


class NoteMetadataStore:
    """
    SQLite-based storage for note metadata with connection pooling

    Provides efficient queries for scheduling and tracking
    without loading note content.

    Features:
    - Connection pooling for better performance
    - Thread-safe connection management
    - Automatic connection recycling

    Usage:
        store = NoteMetadataStore(Path("data/notes_meta.db"))
        store.save(metadata)
        due_notes = store.get_due_for_review(limit=50)
    """

    def __init__(
        self,
        db_path: Path,
        pool_size: int = DEFAULT_POOL_SIZE,
    ):
        """
        Initialize metadata store with connection pool

        Args:
            db_path: Path to SQLite database file
            pool_size: Number of connections to maintain in pool
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._pool_size = pool_size
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._pool_lock = threading.Lock()
        self._active_connections = 0
        self._init_db()
        self._init_pool()

    def _init_pool(self) -> None:
        """Initialize the connection pool with connections"""
        for _ in range(self._pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
            self._active_connections += 1
        logger.debug(
            "Initialized connection pool",
            extra={"pool_size": self._pool_size, "db_path": str(self.db_path)}
        )

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection"""
        conn = sqlite3.connect(str(self.db_path), timeout=CONNECTION_TIMEOUT)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent read performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a connection from the pool (thread-safe)"""
        conn: sqlite3.Connection | None = None
        try:
            # Try to get from pool with timeout
            conn = self._pool.get(timeout=CONNECTION_TIMEOUT)
            yield conn
        except Empty:
            # Pool exhausted, create a temporary connection
            logger.warning("Connection pool exhausted, creating temporary connection")
            conn = self._create_connection()
            yield conn
            # Close temporary connection instead of returning to pool
            conn.close()
            conn = None  # Mark as handled
        finally:
            # Return connection to pool if it came from there
            if conn is not None:
                try:
                    self._pool.put_nowait(conn)
                except Exception:
                    # Pool full (shouldn't happen), close connection
                    conn.close()

    def close(self) -> None:
        """Close all connections in the pool"""
        with self._pool_lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                    self._active_connections -= 1
                except Empty:
                    break
            logger.debug("Closed connection pool")

    def _init_db(self) -> None:
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create main metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_metadata (
                    note_id TEXT PRIMARY KEY,
                    note_type TEXT NOT NULL DEFAULT 'autre',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    next_review TEXT,
                    easiness_factor REAL NOT NULL DEFAULT 2.5,
                    repetition_number INTEGER NOT NULL DEFAULT 0,
                    interval_hours REAL NOT NULL DEFAULT 2.0,
                    review_count INTEGER NOT NULL DEFAULT 0,
                    last_quality INTEGER,
                    content_hash TEXT NOT NULL DEFAULT '',
                    importance TEXT NOT NULL DEFAULT 'normal',
                    auto_enrich INTEGER NOT NULL DEFAULT 1,
                    web_search_enabled INTEGER NOT NULL DEFAULT 0,
                    enrichment_history TEXT NOT NULL DEFAULT '[]'
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_next_review
                ON note_metadata(next_review)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_note_type
                ON note_metadata(note_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance
                ON note_metadata(importance)
            """)

            # Composite index for get_due_for_review query optimization
            # Query filters by importance, next_review, and optionally note_type
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_review_priority
                ON note_metadata(importance, next_review, note_type)
            """)

            # Index for count_reviews_today query optimization
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reviewed_at
                ON note_metadata(reviewed_at)
            """)

            # Schema version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)
            cursor.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )

            conn.commit()
            logger.debug(f"Database initialized at {self.db_path}")

    def _row_to_metadata(self, row: sqlite3.Row) -> NoteMetadata:
        """Convert database row to NoteMetadata"""

        def parse_datetime(val: str | None) -> datetime | None:
            if val is None:
                return None
            return datetime.fromisoformat(val)

        # Parse enrichment history JSON
        history_json = row["enrichment_history"]
        try:
            history_data = json.loads(history_json) if history_json else []
            history = [EnrichmentRecord.from_dict(h) for h in history_data]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                f"Failed to parse enrichment history for note {row['note_id']}: {e}"
            )
            history = []

        return NoteMetadata(
            note_id=row["note_id"],
            note_type=NoteType(row["note_type"]),
            created_at=parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
            reviewed_at=parse_datetime(row["reviewed_at"]),
            next_review=parse_datetime(row["next_review"]),
            easiness_factor=row["easiness_factor"],
            repetition_number=row["repetition_number"],
            interval_hours=row["interval_hours"],
            review_count=row["review_count"],
            last_quality=row["last_quality"],
            content_hash=row["content_hash"],
            importance=ImportanceLevel(row["importance"]),
            auto_enrich=bool(row["auto_enrich"]),
            web_search_enabled=bool(row["web_search_enabled"]),
            enrichment_history=history,
        )

    def save(self, metadata: NoteMetadata) -> None:
        """
        Save or update note metadata

        Args:
            metadata: NoteMetadata to save
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Serialize enrichment history
            history_json = json.dumps([h.to_dict() for h in metadata.enrichment_history])

            cursor.execute(
                """
                INSERT OR REPLACE INTO note_metadata (
                    note_id, note_type, created_at, updated_at,
                    reviewed_at, next_review, easiness_factor,
                    repetition_number, interval_hours, review_count,
                    last_quality, content_hash, importance,
                    auto_enrich, web_search_enabled, enrichment_history
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metadata.note_id,
                    metadata.note_type.value,
                    metadata.created_at.isoformat(),
                    metadata.updated_at.isoformat(),
                    metadata.reviewed_at.isoformat() if metadata.reviewed_at else None,
                    metadata.next_review.isoformat() if metadata.next_review else None,
                    metadata.easiness_factor,
                    metadata.repetition_number,
                    metadata.interval_hours,
                    metadata.review_count,
                    metadata.last_quality,
                    metadata.content_hash,
                    metadata.importance.value,
                    int(metadata.auto_enrich),
                    int(metadata.web_search_enabled),
                    history_json,
                ),
            )

            conn.commit()
            logger.debug(f"Saved metadata for note {metadata.note_id}")

    def get(self, note_id: str) -> NoteMetadata | None:
        """
        Get metadata for a specific note

        Args:
            note_id: Note identifier

        Returns:
            NoteMetadata or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM note_metadata WHERE note_id = ?", (note_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_metadata(row)

    def delete(self, note_id: str) -> bool:
        """
        Delete metadata for a note

        Args:
            note_id: Note identifier

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM note_metadata WHERE note_id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_due_for_review(
        self,
        limit: int = 50,
        note_types: list[NoteType] | None = None,
        importance_min: ImportanceLevel = ImportanceLevel.LOW,  # noqa: ARG002
    ) -> list[NoteMetadata]:
        """
        Get notes due for review

        Args:
            limit: Maximum number of notes to return
            note_types: Filter by note types (None = all)
            importance_min: Minimum importance level

        Returns:
            List of NoteMetadata due for review, ordered by priority
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query with filters
            query = """
                SELECT * FROM note_metadata
                WHERE (next_review IS NULL OR next_review <= ?)
                AND importance != 'archive'
            """
            params: list = [now]

            if note_types:
                placeholders = ",".join("?" * len(note_types))
                query += f" AND note_type IN ({placeholders})"
                params.extend([t.value for t in note_types])

            # Order by importance (critical first) then by how overdue
            query += """
                ORDER BY
                    CASE importance
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    next_review ASC NULLS FIRST
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_by_type(
        self, note_type: NoteType, limit: int = 100
    ) -> list[NoteMetadata]:
        """
        Get metadata for notes of a specific type

        Args:
            note_type: Type of notes to retrieve
            limit: Maximum number to return

        Returns:
            List of NoteMetadata
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM note_metadata
                WHERE note_type = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                (note_type.value, limit),
            )
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_stats(self) -> dict:
        """
        Get statistics about stored metadata

        Returns:
            Dictionary with counts and statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total count
            cursor.execute("SELECT COUNT(*) FROM note_metadata")
            total = cursor.fetchone()[0]

            # Count by type
            cursor.execute(
                """
                SELECT note_type, COUNT(*) as count
                FROM note_metadata
                GROUP BY note_type
            """
            )
            by_type = {row["note_type"]: row["count"] for row in cursor.fetchall()}

            # Count by importance
            cursor.execute(
                """
                SELECT importance, COUNT(*) as count
                FROM note_metadata
                GROUP BY importance
            """
            )
            by_importance = {
                row["importance"]: row["count"] for row in cursor.fetchall()
            }

            # Due for review
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                SELECT COUNT(*) FROM note_metadata
                WHERE (next_review IS NULL OR next_review <= ?)
                AND importance != 'archive'
            """,
                (now,),
            )
            due_count = cursor.fetchone()[0]

            # Average easiness factor
            cursor.execute("SELECT AVG(easiness_factor) FROM note_metadata")
            avg_easiness = cursor.fetchone()[0] or 2.5

            return {
                "total": total,
                "by_type": by_type,
                "by_importance": by_importance,
                "due_for_review": due_count,
                "average_easiness_factor": round(avg_easiness, 2),
            }

    def create_for_note(
        self,
        note_id: str,
        note_type: NoteType,
        content: str,
        importance: ImportanceLevel = ImportanceLevel.NORMAL,
    ) -> NoteMetadata:
        """
        Create and save metadata for a new note

        Args:
            note_id: Note identifier
            note_type: Type of note
            content: Note content (for hashing)
            importance: Importance level

        Returns:
            Created NoteMetadata
        """
        config = get_review_config(note_type)
        now = datetime.now(timezone.utc)

        # Calculate initial next_review
        if config.skip_revision:
            next_review = None
        else:
            from datetime import timedelta

            next_review = now + timedelta(hours=config.base_interval_hours)

        metadata = NoteMetadata(
            note_id=note_id,
            note_type=note_type,
            created_at=now,
            updated_at=now,
            next_review=next_review,
            easiness_factor=config.easiness_factor,
            interval_hours=config.base_interval_hours,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            importance=importance,
            auto_enrich=config.auto_enrich,
            web_search_enabled=config.web_search_default,
        )

        self.save(metadata)
        logger.info(f"Created metadata for note {note_id} (type={note_type.value})")

        return metadata

    def update_content_hash(self, note_id: str, content: str) -> bool:
        """
        Update content hash for a note

        Args:
            note_id: Note identifier
            content: New content

        Returns:
            True if hash changed, False otherwise
        """
        new_hash = hashlib.sha256(content.encode()).hexdigest()

        metadata = self.get(note_id)
        if metadata is None:
            return False

        if metadata.content_hash == new_hash:
            return False

        metadata.content_hash = new_hash
        metadata.updated_at = datetime.now(timezone.utc)
        self.save(metadata)

        return True

    def count_reviews_today(self) -> int:
        """
        Count reviews completed today

        Returns:
            Number of reviews completed today
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM note_metadata
                WHERE reviewed_at >= ?
            """,
                (today_start.isoformat(),),
            )
            return cursor.fetchone()[0]

    def list_all(self, limit: int = 1000) -> list[NoteMetadata]:
        """
        List all stored metadata

        Args:
            limit: Maximum number to return

        Returns:
            List of all NoteMetadata
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM note_metadata
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]
