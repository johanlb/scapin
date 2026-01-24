"""
Note Metadata Store

SQLite storage for note review metadata and spaced repetition data.
Separates revision metadata from note content for performance and flexibility.
"""

import contextlib
import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

from src.monitoring.logger import get_logger
from src.passepartout.note_types import (
    ImportanceLevel,
    NoteType,
    get_review_config,
)

# Connection pool configuration
DEFAULT_POOL_SIZE = 5
CONNECTION_TIMEOUT = 30.0  # seconds
WAL_CHECKPOINT_THRESHOLD = 1000  # Checkpoint after this many operations

logger = get_logger("passepartout.note_metadata")

# Database schema version for migrations
SCHEMA_VERSION = 3

# Importance level ordering for priority sorting (lower value = higher priority)
IMPORTANCE_ORDER: dict[ImportanceLevel, int] = {
    ImportanceLevel.CRITICAL: 1,
    ImportanceLevel.HIGH: 2,
    ImportanceLevel.NORMAL: 3,
    ImportanceLevel.LOW: 4,
    ImportanceLevel.ARCHIVE: 5,
}


@dataclass
class EnrichmentRecord:
    """Record of a single enrichment action. Uses slots=True for memory efficiency."""

    timestamp: datetime
    action_type: str  # add, update, remove, link
    target: str  # Section or content target
    content: Optional[str]  # New content if applicable
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
    Uses slots=True for ~30% memory reduction per instance.

    v2: Dual-cycle support (Retouche/Lecture)
    - Retouche (IA): Amélioration automatique des notes
    - Lecture (Humain): Révision espacée pour Johan
    """

    note_id: str
    note_type: NoteType = NoteType.AUTRE

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    next_review: Optional[datetime] = None

    # SM-2 Algorithm state (legacy - kept for backward compatibility)
    easiness_factor: float = 2.5  # 1.3 - 2.5
    repetition_number: int = 0  # Consecutive successful reviews
    interval_hours: float = 2.0  # Current interval in hours

    # Tracking (legacy)
    review_count: int = 0
    last_quality: Optional[int] = None  # 0-5, last review quality
    content_hash: str = ""  # SHA256 to detect external changes

    # Configuration
    importance: ImportanceLevel = ImportanceLevel.NORMAL
    auto_enrich: bool = True
    web_search_enabled: bool = False

    # History (stored as JSON)
    enrichment_history: list[EnrichmentRecord] = field(default_factory=list)

    # === Dual-Cycle Fields (v2) ===

    # Retouche (IA) - Amélioration automatique
    retouche_ef: float = 2.5  # Easiness factor for Retouche cycle
    retouche_rep: int = 0  # Repetition number for Retouche
    retouche_interval: float = 2.0  # Current interval in hours
    retouche_next: Optional[datetime] = None  # Next Retouche due
    retouche_last: Optional[datetime] = None  # Last Retouche done
    retouche_count: int = 0  # Total Retouches performed

    # Lecture (Humain) - Révision espacée pour Johan
    lecture_ef: float = 2.5  # Easiness factor for Lecture cycle
    lecture_rep: int = 0  # Repetition number for Lecture
    lecture_interval: float = 24.0  # Current interval in hours (starts longer)
    lecture_next: Optional[datetime] = None  # Next Lecture due
    lecture_last: Optional[datetime] = None  # Last Lecture done
    lecture_count: int = 0  # Total Lectures performed

    # Qualité & Questions (v2)
    quality_score: Optional[int] = None  # 0-100, overall quality score
    questions_pending: bool = False  # Has unanswered questions for Johan
    questions_count: int = 0  # Number of pending questions

    # === Cycle de vie des notes (v3) ===
    pending_actions: list[dict] = field(default_factory=list)  # Actions en attente de confirmation Filage
    obsolete_flag: bool = False  # Note marquée comme obsolète
    obsolete_reason: str = ""  # Raison de l'obsolescence
    merge_target_id: Optional[str] = None  # ID de la note cible pour fusion

    def is_due_for_review(self, now: Optional[datetime] = None) -> bool:
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

    def days_until_review(self, now: Optional[datetime] = None) -> float:
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
        # Statistics tracking
        self._operations_since_checkpoint = 0
        self._total_operations = 0
        self._pool_wait_count = 0
        self._pool_exhausted_count = 0
        # Initialize pool BEFORE _init_db() which needs a connection
        self._init_pool()
        self._init_db()

    def _init_pool(self) -> None:
        """Initialize the connection pool with connections"""
        for _ in range(self._pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
            self._active_connections += 1
        logger.debug(
            "Initialized connection pool",
            extra={"pool_size": self._pool_size, "db_path": str(self.db_path)},
        )

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection"""
        # check_same_thread=False is safe because we use connection pooling with locks
        conn = sqlite3.connect(
            str(self.db_path), timeout=CONNECTION_TIMEOUT, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent read performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a connection from the pool (thread-safe)"""
        conn: Optional[sqlite3.Connection] = None
        from_pool = False
        try:
            # Try to get from pool with timeout
            conn = self._pool.get(timeout=CONNECTION_TIMEOUT)
            from_pool = True
            self._pool_wait_count += 1
            yield conn
        except Empty:
            # Pool exhausted, create a temporary connection
            self._pool_exhausted_count += 1
            logger.warning(
                "Connection pool exhausted, creating temporary connection",
                extra={"exhausted_count": self._pool_exhausted_count},
            )
            conn = self._create_connection()
            yield conn
            # Close temporary connection instead of returning to pool
            conn.close()
            conn = None  # Mark as handled
        finally:
            # Return connection to pool if it came from there
            if conn is not None and from_pool:
                try:
                    self._pool.put_nowait(conn)
                except Exception:
                    # Pool full (shouldn't happen), close connection
                    conn.close()

            # Track operations and checkpoint WAL if needed
            self._total_operations += 1
            self._operations_since_checkpoint += 1
            if self._operations_since_checkpoint >= WAL_CHECKPOINT_THRESHOLD:
                self._checkpoint_wal()

    def _checkpoint_wal(self) -> None:
        """
        Checkpoint the WAL file to prevent unbounded growth

        WAL (Write-Ahead Logging) files can grow indefinitely without checkpoints.
        This method forces a checkpoint to merge WAL back into the main database.

        Note: Uses direct pool access to avoid recursion through _get_connection.
        """
        conn: Optional[sqlite3.Connection] = None
        try:
            # Get connection directly from pool to avoid recursion
            conn = self._pool.get(timeout=5.0)
            # PRAGMA wal_checkpoint(TRUNCATE) checkpoints and truncates the WAL
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self._operations_since_checkpoint = 0
            logger.debug(
                "WAL checkpoint completed", extra={"total_operations": self._total_operations}
            )
        except Empty:
            logger.warning("WAL checkpoint skipped - pool exhausted")
        except Exception as e:
            logger.warning("WAL checkpoint failed", extra={"error": str(e)})
        finally:
            if conn is not None:
                try:
                    self._pool.put_nowait(conn)
                except Exception:
                    conn.close()

    def get_pool_stats(self) -> dict:
        """
        Get connection pool statistics for monitoring

        Returns:
            Dictionary with pool metrics
        """
        return {
            "pool_size": self._pool_size,
            "active_connections": self._active_connections,
            "available_connections": self._pool.qsize(),
            "total_operations": self._total_operations,
            "operations_since_checkpoint": self._operations_since_checkpoint,
            "pool_wait_count": self._pool_wait_count,
            "pool_exhausted_count": self._pool_exhausted_count,
        }

    def close(self) -> None:
        """Close all connections in the pool"""
        # Final WAL checkpoint before closing
        self._checkpoint_wal()

        with self._pool_lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                    self._active_connections -= 1
                except Empty:
                    break
            logger.debug("Closed connection pool", extra={"final_stats": self.get_pool_stats()})

    def __del__(self) -> None:
        """Ensure connection pool is closed on garbage collection"""
        with contextlib.suppress(Exception):
            self.close()

    def _init_db(self) -> None:
        """Initialize database schema with migration support"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check current schema version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)

            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_version = row[0] if row else 0

            # Create main metadata table if not exists (v1 schema)
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

            # Run migrations if needed
            if current_version < 2:
                self._migrate_v1_to_v2(cursor)
            if current_version < 3:
                self._migrate_v2_to_v3(cursor)

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
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_review_priority
                ON note_metadata(importance, next_review, note_type)
            """)

            # Index for count_reviews_today query optimization
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reviewed_at
                ON note_metadata(reviewed_at)
            """)

            # Update schema version
            cursor.execute("DELETE FROM schema_version")
            cursor.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )

            conn.commit()
            logger.debug(
                "Database initialized",
                extra={"db_path": str(self.db_path), "schema_version": SCHEMA_VERSION},
            )

    def _migrate_v1_to_v2(self, cursor: sqlite3.Cursor) -> None:
        """
        Migrate from schema v1 to v2: Add dual-cycle fields (Retouche/Lecture).

        Migration strategy:
        - Copy existing SM-2 fields to retouche_* fields
        - Initialize lecture_* fields with defaults
        - Add quality_score and questions fields
        """
        logger.info("Migrating database schema from v1 to v2 (dual-cycle support)")

        # Check which columns already exist
        cursor.execute("PRAGMA table_info(note_metadata)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Retouche (IA) columns - copy from existing SM-2 fields
        new_columns_retouche = [
            ("retouche_ef", "REAL", "easiness_factor"),
            ("retouche_rep", "INTEGER", "repetition_number"),
            ("retouche_interval", "REAL", "interval_hours"),
            ("retouche_next", "TEXT", "next_review"),
            ("retouche_last", "TEXT", "reviewed_at"),
            ("retouche_count", "INTEGER", "review_count"),
        ]

        # Lecture (Humain) columns - initialize with defaults
        new_columns_lecture = [
            ("lecture_ef", "REAL NOT NULL DEFAULT 2.5"),
            ("lecture_rep", "INTEGER NOT NULL DEFAULT 0"),
            ("lecture_interval", "REAL NOT NULL DEFAULT 24.0"),
            ("lecture_next", "TEXT"),
            ("lecture_last", "TEXT"),
            ("lecture_count", "INTEGER NOT NULL DEFAULT 0"),
        ]

        # Quality & Questions columns
        new_columns_quality = [
            ("quality_score", "INTEGER"),
            ("questions_pending", "INTEGER NOT NULL DEFAULT 0"),
            ("questions_count", "INTEGER NOT NULL DEFAULT 0"),
        ]

        # Add Retouche columns with data migration
        for col_name, col_type, source_col in new_columns_retouche:
            if col_name not in existing_columns:
                # Add column with default
                if col_type == "REAL":
                    cursor.execute(
                        f"ALTER TABLE note_metadata ADD COLUMN {col_name} {col_type} DEFAULT 2.5"
                    )
                elif col_type == "INTEGER":
                    cursor.execute(
                        f"ALTER TABLE note_metadata ADD COLUMN {col_name} {col_type} DEFAULT 0"
                    )
                else:
                    cursor.execute(
                        f"ALTER TABLE note_metadata ADD COLUMN {col_name} {col_type}"
                    )
                # Copy data from source column
                cursor.execute(
                    f"UPDATE note_metadata SET {col_name} = {source_col}"
                )
                logger.debug(f"Added column {col_name} with data from {source_col}")

        # Add Lecture columns with defaults
        for col_def in new_columns_lecture:
            col_name = col_def[0]
            col_type = col_def[1]
            if col_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE note_metadata ADD COLUMN {col_name} {col_type}"
                )
                logger.debug(f"Added column {col_name}")

        # Add Quality columns
        for col_def in new_columns_quality:
            col_name = col_def[0]
            col_type = col_def[1]
            if col_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE note_metadata ADD COLUMN {col_name} {col_type}"
                )
                logger.debug(f"Added column {col_name}")

        # Create indexes for dual-cycle queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_retouche_next
            ON note_metadata(retouche_next)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lecture_next
            ON note_metadata(lecture_next)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_questions_pending
            ON note_metadata(questions_pending)
        """)

        logger.info("Migration v1 to v2 completed successfully")

    def _migrate_v2_to_v3(self, cursor: sqlite3.Cursor) -> None:
        """
        Migrate from schema v2 to v3: Add lifecycle fields (pending_actions, obsolete).

        Migration strategy:
        - Add pending_actions as JSON text (default '[]')
        - Add obsolete_flag, obsolete_reason, merge_target_id
        """
        logger.info("Migrating database schema from v2 to v3 (lifecycle support)")

        # Check which columns already exist
        cursor.execute("PRAGMA table_info(note_metadata)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Lifecycle columns
        new_columns = [
            ("pending_actions", "TEXT NOT NULL DEFAULT '[]'"),
            ("obsolete_flag", "INTEGER NOT NULL DEFAULT 0"),
            ("obsolete_reason", "TEXT NOT NULL DEFAULT ''"),
            ("merge_target_id", "TEXT"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE note_metadata ADD COLUMN {col_name} {col_type}"
                )
                logger.debug(f"Added column {col_name}")

        # Create index for pending actions queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_actions
            ON note_metadata(pending_actions)
            WHERE pending_actions != '[]'
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_obsolete_flag
            ON note_metadata(obsolete_flag)
            WHERE obsolete_flag = 1
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_merge_target
            ON note_metadata(merge_target_id)
            WHERE merge_target_id IS NOT NULL
        """)

        logger.info("Migration v2 to v3 completed successfully")

    def _parse_datetime_safe(self, val: Optional[str], field_name: str = "") -> Optional[datetime]:
        """
        Safely parse datetime string with error handling

        Args:
            val: ISO format datetime string or None
            field_name: Field name for error logging

        Returns:
            Parsed datetime or None if parsing fails
        """
        if val is None:
            return None
        try:
            dt = datetime.fromisoformat(val)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse datetime",
                extra={"field": field_name, "value": val, "error": str(e)},
            )
            return None

    def _row_to_metadata(self, row: sqlite3.Row) -> NoteMetadata:
        """Convert database row to NoteMetadata"""

        note_id = row["note_id"]

        # Parse enrichment history JSON
        history_json = row["enrichment_history"]
        try:
            history_data = json.loads(history_json) if history_json else []
            history = [EnrichmentRecord.from_dict(h) for h in history_data]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "Failed to parse enrichment history", extra={"note_id": note_id, "error": str(e)}
            )
            history = []

        # Helper to safely get row value with default (for v2 columns that may not exist)
        def get_row_value(key: str, default: any) -> any:
            try:
                return row[key] if row[key] is not None else default
            except (IndexError, KeyError):
                return default

        return NoteMetadata(
            note_id=note_id,
            note_type=NoteType(row["note_type"]),
            created_at=self._parse_datetime_safe(row["created_at"], "created_at")
            or datetime.now(timezone.utc),
            updated_at=self._parse_datetime_safe(row["updated_at"], "updated_at")
            or datetime.now(timezone.utc),
            reviewed_at=self._parse_datetime_safe(row["reviewed_at"], "reviewed_at"),
            next_review=self._parse_datetime_safe(row["next_review"], "next_review"),
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
            # v2: Dual-cycle fields
            retouche_ef=get_row_value("retouche_ef", 2.5),
            retouche_rep=get_row_value("retouche_rep", 0),
            retouche_interval=get_row_value("retouche_interval", 2.0),
            retouche_next=self._parse_datetime_safe(
                get_row_value("retouche_next", None), "retouche_next"
            ),
            retouche_last=self._parse_datetime_safe(
                get_row_value("retouche_last", None), "retouche_last"
            ),
            retouche_count=get_row_value("retouche_count", 0),
            lecture_ef=get_row_value("lecture_ef", 2.5),
            lecture_rep=get_row_value("lecture_rep", 0),
            lecture_interval=get_row_value("lecture_interval", 24.0),
            lecture_next=self._parse_datetime_safe(
                get_row_value("lecture_next", None), "lecture_next"
            ),
            lecture_last=self._parse_datetime_safe(
                get_row_value("lecture_last", None), "lecture_last"
            ),
            lecture_count=get_row_value("lecture_count", 0),
            quality_score=get_row_value("quality_score", None),
            questions_pending=bool(get_row_value("questions_pending", False)),
            questions_count=get_row_value("questions_count", 0),
            # v3: Lifecycle fields
            pending_actions=json.loads(get_row_value("pending_actions", "[]")),
            obsolete_flag=bool(get_row_value("obsolete_flag", False)),
            obsolete_reason=get_row_value("obsolete_reason", ""),
            merge_target_id=get_row_value("merge_target_id", None),
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

            # Serialize pending_actions JSON
            pending_actions_json = json.dumps(metadata.pending_actions)

            cursor.execute(
                """
                INSERT OR REPLACE INTO note_metadata (
                    note_id, note_type, created_at, updated_at,
                    reviewed_at, next_review, easiness_factor,
                    repetition_number, interval_hours, review_count,
                    last_quality, content_hash, importance,
                    auto_enrich, web_search_enabled, enrichment_history,
                    retouche_ef, retouche_rep, retouche_interval,
                    retouche_next, retouche_last, retouche_count,
                    lecture_ef, lecture_rep, lecture_interval,
                    lecture_next, lecture_last, lecture_count,
                    quality_score, questions_pending, questions_count,
                    pending_actions, obsolete_flag, obsolete_reason, merge_target_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    # v2: Dual-cycle fields
                    metadata.retouche_ef,
                    metadata.retouche_rep,
                    metadata.retouche_interval,
                    metadata.retouche_next.isoformat() if metadata.retouche_next else None,
                    metadata.retouche_last.isoformat() if metadata.retouche_last else None,
                    metadata.retouche_count,
                    metadata.lecture_ef,
                    metadata.lecture_rep,
                    metadata.lecture_interval,
                    metadata.lecture_next.isoformat() if metadata.lecture_next else None,
                    metadata.lecture_last.isoformat() if metadata.lecture_last else None,
                    metadata.lecture_count,
                    metadata.quality_score,
                    int(metadata.questions_pending),
                    metadata.questions_count,
                    # v3: Lifecycle fields
                    pending_actions_json,
                    int(metadata.obsolete_flag),
                    metadata.obsolete_reason,
                    metadata.merge_target_id,
                ),
            )

            conn.commit()
            logger.debug("Saved metadata", extra={"note_id": metadata.note_id})

    def save_batch(self, metadata_list: list[NoteMetadata]) -> int:
        """
        Save multiple metadata records in a single transaction

        Uses executemany for better performance with large batches.

        Args:
            metadata_list: List of NoteMetadata to save

        Returns:
            Number of records saved
        """
        if not metadata_list:
            return 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Prepare all data tuples
            data_tuples = []
            for metadata in metadata_list:
                history_json = json.dumps([h.to_dict() for h in metadata.enrichment_history])
                pending_actions_json = json.dumps(metadata.pending_actions)
                data_tuples.append(
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
                        # v2: Dual-cycle fields
                        metadata.retouche_ef,
                        metadata.retouche_rep,
                        metadata.retouche_interval,
                        metadata.retouche_next.isoformat() if metadata.retouche_next else None,
                        metadata.retouche_last.isoformat() if metadata.retouche_last else None,
                        metadata.retouche_count,
                        metadata.lecture_ef,
                        metadata.lecture_rep,
                        metadata.lecture_interval,
                        metadata.lecture_next.isoformat() if metadata.lecture_next else None,
                        metadata.lecture_last.isoformat() if metadata.lecture_last else None,
                        metadata.lecture_count,
                        metadata.quality_score,
                        int(metadata.questions_pending),
                        metadata.questions_count,
                        # v3: Lifecycle fields
                        pending_actions_json,
                        int(metadata.obsolete_flag),
                        metadata.obsolete_reason,
                        metadata.merge_target_id,
                    )
                )

            cursor.executemany(
                """
                INSERT OR REPLACE INTO note_metadata (
                    note_id, note_type, created_at, updated_at,
                    reviewed_at, next_review, easiness_factor,
                    repetition_number, interval_hours, review_count,
                    last_quality, content_hash, importance,
                    auto_enrich, web_search_enabled, enrichment_history,
                    retouche_ef, retouche_rep, retouche_interval,
                    retouche_next, retouche_last, retouche_count,
                    lecture_ef, lecture_rep, lecture_interval,
                    lecture_next, lecture_last, lecture_count,
                    quality_score, questions_pending, questions_count,
                    pending_actions, obsolete_flag, obsolete_reason, merge_target_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                data_tuples,
            )

            conn.commit()
            saved_count = len(data_tuples)
            logger.info("Batch saved metadata", extra={"count": saved_count})
            return saved_count

    def get(self, note_id: str) -> Optional[NoteMetadata]:
        """
        Get metadata for a specific note

        Args:
            note_id: Note identifier

        Returns:
            NoteMetadata or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM note_metadata WHERE note_id = ?", (note_id,))
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
        note_types: Optional[list[NoteType]] = None,
        importance_min: ImportanceLevel = ImportanceLevel.LOW,
    ) -> list[NoteMetadata]:
        """
        Get notes due for review

        Args:
            limit: Maximum number of notes to return
            note_types: Filter by note types (None = all)
            importance_min: Minimum importance level to include

        Returns:
            List of NoteMetadata due for review, ordered by priority
        """
        now = datetime.now(timezone.utc).isoformat()

        # Use module constant for importance ordering
        min_importance_value = IMPORTANCE_ORDER.get(importance_min, 4)

        # Build list of allowed importance levels
        allowed_importance = [
            level.value
            for level, value in IMPORTANCE_ORDER.items()
            if value <= min_importance_value and level != ImportanceLevel.ARCHIVE
        ]

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query with filters
            placeholders_importance = ",".join("?" * len(allowed_importance))
            query = f"""
                SELECT * FROM note_metadata
                WHERE (next_review IS NULL OR next_review <= ?)
                AND importance IN ({placeholders_importance})
            """
            params: list = [now, *allowed_importance]

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

    def get_due_for_retouche(
        self,
        limit: int = 50,
        note_types: Optional[list[NoteType]] = None,
        importance_min: ImportanceLevel = ImportanceLevel.LOW,
    ) -> list[NoteMetadata]:
        """
        Get notes due for Retouche (IA review cycle)

        Args:
            limit: Maximum number of notes to return
            note_types: Filter by note types (None = all)
            importance_min: Minimum importance level to include

        Returns:
            List of NoteMetadata due for Retouche, ordered by priority
        """
        now = datetime.now(timezone.utc).isoformat()

        # Use module constant for importance ordering
        min_importance_value = IMPORTANCE_ORDER.get(importance_min, 4)

        # Build list of allowed importance levels
        allowed_importance = [
            level.value
            for level, value in IMPORTANCE_ORDER.items()
            if value <= min_importance_value and level != ImportanceLevel.ARCHIVE
        ]

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query with filters - use retouche_next field
            placeholders_importance = ",".join("?" * len(allowed_importance))
            query = f"""
                SELECT * FROM note_metadata
                WHERE (retouche_next IS NULL OR retouche_next <= ?)
                AND importance IN ({placeholders_importance})
            """
            params: list = [now, *allowed_importance]

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
                    retouche_next ASC NULLS FIRST
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_due_for_lecture(
        self,
        limit: int = 50,
        note_types: Optional[list[NoteType]] = None,
        importance_min: ImportanceLevel = ImportanceLevel.LOW,
    ) -> list[NoteMetadata]:
        """
        Get notes due for Lecture (human review cycle)

        Args:
            limit: Maximum number of notes to return
            note_types: Filter by note types (None = all)
            importance_min: Minimum importance level to include

        Returns:
            List of NoteMetadata due for Lecture, ordered by priority
        """
        now = datetime.now(timezone.utc).isoformat()

        # Use module constant for importance ordering
        min_importance_value = IMPORTANCE_ORDER.get(importance_min, 4)

        # Build list of allowed importance levels
        allowed_importance = [
            level.value
            for level, value in IMPORTANCE_ORDER.items()
            if value <= min_importance_value and level != ImportanceLevel.ARCHIVE
        ]

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query with filters - use lecture_next field
            # Also filter for notes that have lecture_next set (have been retouched at least once)
            placeholders_importance = ",".join("?" * len(allowed_importance))
            query = f"""
                SELECT * FROM note_metadata
                WHERE lecture_next IS NOT NULL
                AND lecture_next <= ?
                AND importance IN ({placeholders_importance})
            """
            params: list = [now, *allowed_importance]

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
                    lecture_next ASC
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_notes_with_pending_questions(
        self,
        limit: int = 50,
    ) -> list[NoteMetadata]:
        """
        Get notes that have pending questions for Johan

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of NoteMetadata with pending questions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM note_metadata
                WHERE questions_pending = 1
                AND importance != 'archive'
                ORDER BY
                    CASE importance
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    questions_count DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_recently_retouched(
        self,
        hours: int = 48,
        limit: int = 50,
    ) -> list[NoteMetadata]:
        """
        Get notes recently retouched by IA

        Args:
            hours: Look back period in hours
            limit: Maximum number of notes to return

        Returns:
            List of NoteMetadata recently retouched
        """
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM note_metadata
                WHERE retouche_last IS NOT NULL
                AND retouche_last >= ?
                AND importance != 'archive'
                ORDER BY retouche_last DESC
                LIMIT ?
            """,
                (since, limit),
            )
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_by_type(self, note_type: NoteType, limit: int = 100) -> list[NoteMetadata]:
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
            by_importance = {row["importance"]: row["count"] for row in cursor.fetchall()}

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

        # Calculate initial next_review (legacy)
        if config.skip_revision:
            next_review = None
        else:
            next_review = now + timedelta(hours=config.base_interval_hours)

        # v2: Initialize dual-cycle fields
        # Retouche: délai 1h pour laisser le temps à la note de "mûrir"
        retouche_next = now + timedelta(hours=1) if not config.skip_revision else None

        # Lecture: pas de date initiale, sera programmée après première Retouche
        lecture_next = None

        metadata = NoteMetadata(
            note_id=note_id,
            note_type=note_type,
            created_at=now,
            updated_at=now,
            next_review=next_review,
            interval_hours=config.base_interval_hours,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            importance=importance,
            # v2: Dual-cycle initialization
            retouche_ef=2.5,
            retouche_rep=0,
            retouche_interval=config.base_interval_hours,
            retouche_next=retouche_next,
            retouche_last=None,
            retouche_count=0,
            lecture_ef=2.5,
            lecture_rep=0,
            lecture_interval=24.0,  # Lecture starts with 24h interval
            lecture_next=lecture_next,
            lecture_last=None,
            lecture_count=0,
            quality_score=None,
            questions_pending=False,
            questions_count=0,
        )

        self.save(metadata)
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
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

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

    # === v3: Lifecycle queries ===

    def get_notes_with_pending_actions(
        self,
        limit: int = 50,
    ) -> list[NoteMetadata]:
        """
        Get notes that have pending retouche actions awaiting approval (Filage)

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of NoteMetadata with pending actions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM note_metadata
                WHERE pending_actions != '[]'
                AND obsolete_flag = 0
                AND importance != 'archive'
                ORDER BY
                    CASE importance
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    updated_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_obsolete_notes(
        self,
        limit: int = 50,
    ) -> list[NoteMetadata]:
        """
        Get notes flagged as obsolete

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of NoteMetadata flagged as obsolete
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM note_metadata
                WHERE obsolete_flag = 1
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def get_merge_candidates(
        self,
        target_note_id: str,
    ) -> list[NoteMetadata]:
        """
        Get notes that are candidates for merging into a target note

        Args:
            target_note_id: ID of the target note for merge

        Returns:
            List of NoteMetadata that have this note as merge target
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM note_metadata
                WHERE merge_target_id = ?
                ORDER BY updated_at DESC
            """,
                (target_note_id,),
            )
            rows = cursor.fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def clear_pending_action(
        self,
        note_id: str,
        action_id: str,
    ) -> bool:
        """
        Remove a specific pending action from a note

        Args:
            note_id: Note identifier
            action_id: ID of the action to remove

        Returns:
            True if action was removed, False if not found
        """
        metadata = self.get(note_id)
        if metadata is None:
            return False

        original_count = len(metadata.pending_actions)
        metadata.pending_actions = [
            a for a in metadata.pending_actions if a.get("id") != action_id
        ]

        if len(metadata.pending_actions) == original_count:
            return False

        metadata.updated_at = datetime.now(timezone.utc)
        self.save(metadata)
        return True

    def add_pending_action(
        self,
        note_id: str,
        action: dict,
    ) -> bool:
        """
        Add a pending action to a note

        Args:
            note_id: Note identifier
            action: Action dictionary with id, type, confidence, etc.

        Returns:
            True if added, False if note not found
        """
        metadata = self.get(note_id)
        if metadata is None:
            return False

        metadata.pending_actions.append(action)
        metadata.updated_at = datetime.now(timezone.utc)
        self.save(metadata)
        return True
