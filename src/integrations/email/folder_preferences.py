"""
Folder Preferences Store - Learning System for Archive Destinations

This module learns user preferences for email archiving destinations based on:
- Sender email address (highest weight)
- Sender domain (medium weight)
- Subject keywords (lower weight)

The system uses frequency-based learning with time decay to provide
increasingly accurate folder suggestions over time.
"""

import re
import sqlite3
import threading
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.monitoring.logger import get_logger
from src.utils import get_data_dir

logger = get_logger("folder_preferences")


@dataclass
class FolderSuggestion:
    """A folder suggestion with confidence score."""
    folder: str
    confidence: float  # 0.0 to 1.0
    reason: str  # Why this folder was suggested


@dataclass
class FolderPreference:
    """A learned folder preference."""
    pattern_type: str  # 'sender', 'domain', 'keyword'
    pattern: str  # The actual pattern (email, domain, or keyword)
    folder: str
    count: int
    last_used: datetime
    score: float  # Weighted score considering recency


class FolderPreferencesStore:
    """
    SQLite-based store for learning folder preferences.

    Learning algorithm:
    - Each archive action records mappings with weights:
      - sender_email → folder (weight: 3.0)
      - sender_domain → folder (weight: 1.5)
      - subject_keywords → folder (weight: 1.0)
    - Scores decay over time (half-life: 30 days)
    - Suggestions are ranked by weighted score
    """

    # Weights for different pattern types
    WEIGHT_SENDER = 3.0
    WEIGHT_DOMAIN = 1.5
    WEIGHT_KEYWORD = 1.0

    # Time decay half-life in days
    DECAY_HALF_LIFE_DAYS = 30

    # Minimum confidence to suggest
    MIN_CONFIDENCE = 0.3

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the folder preferences store.

        Args:
            db_path: Path to SQLite database. Defaults to data/folder_preferences.db
        """
        if db_path is None:
            # Use absolute path to ensure correct location regardless of working directory
            data_dir = get_data_dir()
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "folder_preferences.db")

        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

        logger.info(
            "FolderPreferencesStore initialized",
            extra={"db_path": db_path}
        )

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor with auto-commit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_cursor() as cursor:
            # Main preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS folder_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    first_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pattern_type, pattern, folder)
                )
            """)

            # Index for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_preferences_pattern
                ON folder_preferences(pattern_type, pattern)
            """)

            # Recent folders table (for quick access)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recent_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder TEXT UNIQUE NOT NULL,
                    use_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def record_archive(
        self,
        folder: str,
        sender_email: Optional[str] = None,
        sender_domain: Optional[str] = None,
        subject: Optional[str] = None
    ) -> None:
        """
        Record an archive action to learn preferences.

        Args:
            folder: The destination folder used
            sender_email: Full email address of sender
            sender_domain: Domain of sender (extracted from email)
            subject: Email subject for keyword extraction
        """
        now = datetime.now()

        with self._get_cursor() as cursor:
            # Record sender email preference
            if sender_email:
                self._upsert_preference(
                    cursor, 'sender', sender_email.lower(), folder, now
                )

            # Record domain preference
            if sender_domain:
                self._upsert_preference(
                    cursor, 'domain', sender_domain.lower(), folder, now
                )
            elif sender_email and '@' in sender_email:
                domain = sender_email.split('@')[1].lower()
                self._upsert_preference(
                    cursor, 'domain', domain, folder, now
                )

            # Record keyword preferences
            if subject:
                keywords = self._extract_keywords(subject)
                for keyword in keywords:
                    self._upsert_preference(
                        cursor, 'keyword', keyword, folder, now
                    )

            # Update recent folders
            cursor.execute("""
                INSERT INTO recent_folders (folder, use_count, last_used)
                VALUES (?, 1, ?)
                ON CONFLICT(folder) DO UPDATE SET
                    use_count = use_count + 1,
                    last_used = excluded.last_used
            """, (folder, now))

        logger.debug(
            "Recorded archive action",
            extra={
                "folder": folder,
                "sender": sender_email,
                "domain": sender_domain
            }
        )

    def _upsert_preference(
        self,
        cursor: sqlite3.Cursor,
        pattern_type: str,
        pattern: str,
        folder: str,
        timestamp: datetime
    ) -> None:
        """Insert or update a preference record."""
        cursor.execute("""
            INSERT INTO folder_preferences (pattern_type, pattern, folder, count, last_used)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(pattern_type, pattern, folder) DO UPDATE SET
                count = count + 1,
                last_used = excluded.last_used
        """, (pattern_type, pattern, folder, timestamp))

    def _extract_keywords(self, subject: str) -> list[str]:
        """
        Extract meaningful keywords from subject.

        Filters out common words and returns significant terms.
        """
        # Common words to ignore (French and English)
        stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'à', 'au', 'aux',
            'et', 'ou', 'mais', 'donc', 'car', 'ni', 'que', 'qui', 'quoi',
            'ce', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes',
            'son', 'sa', 'ses', 'notre', 'nos', 'votre', 'vos', 'leur', 'leurs',
            'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            're', 'fw', 'fwd', 'tr', 'ref', 'objet', 'subject'
        }

        # Clean and tokenize
        subject = subject.lower()
        subject = re.sub(r'[^\w\s]', ' ', subject)
        words = subject.split()

        # Filter: min 3 chars, not a stopword, not a number
        keywords = [
            w for w in words
            if len(w) >= 3 and w not in stopwords and not w.isdigit()
        ]

        # Return unique keywords (max 5)
        return list(dict.fromkeys(keywords))[:5]

    def get_suggestions(
        self,
        sender_email: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 5
    ) -> list[FolderSuggestion]:
        """
        Get folder suggestions based on sender and subject.

        Uses weighted scoring with time decay to rank suggestions.

        Args:
            sender_email: Sender's email address
            subject: Email subject
            limit: Maximum number of suggestions

        Returns:
            List of FolderSuggestion ordered by confidence
        """
        scores: dict[str, dict] = defaultdict(lambda: {'score': 0.0, 'reasons': []})
        now = datetime.now()

        with self._get_cursor() as cursor:
            patterns_to_check = []

            # Prepare patterns to check
            if sender_email:
                sender_lower = sender_email.lower()
                patterns_to_check.append(('sender', sender_lower, self.WEIGHT_SENDER))

                if '@' in sender_email:
                    domain = sender_email.split('@')[1].lower()
                    patterns_to_check.append(('domain', domain, self.WEIGHT_DOMAIN))

            if subject:
                keywords = self._extract_keywords(subject)
                for keyword in keywords:
                    patterns_to_check.append(('keyword', keyword, self.WEIGHT_KEYWORD))

            # Query preferences for all patterns
            for pattern_type, pattern, weight in patterns_to_check:
                cursor.execute("""
                    SELECT folder, count, last_used
                    FROM folder_preferences
                    WHERE pattern_type = ? AND pattern = ?
                """, (pattern_type, pattern))

                for row in cursor.fetchall():
                    folder = row['folder']
                    count = row['count']
                    last_used = row['last_used']

                    # Calculate time decay
                    if isinstance(last_used, str):
                        last_used = datetime.fromisoformat(last_used)

                    days_ago = (now - last_used).days
                    decay = 0.5 ** (days_ago / self.DECAY_HALF_LIFE_DAYS)

                    # Calculate score
                    pattern_score = count * weight * decay
                    scores[folder]['score'] += pattern_score

                    # Track reason
                    if pattern_type == 'sender':
                        scores[folder]['reasons'].append(f"Sender: {pattern}")
                    elif pattern_type == 'domain':
                        scores[folder]['reasons'].append(f"Domain: {pattern}")
                    else:
                        scores[folder]['reasons'].append(f"Keyword: {pattern}")

        # Normalize scores and create suggestions
        if not scores:
            return []

        max_score = max(s['score'] for s in scores.values())

        suggestions = []
        for folder, data in scores.items():
            confidence = data['score'] / max_score if max_score > 0 else 0

            if confidence >= self.MIN_CONFIDENCE:
                # Pick the most relevant reason
                reason = data['reasons'][0] if data['reasons'] else "Learned preference"
                suggestions.append(FolderSuggestion(
                    folder=folder,
                    confidence=confidence,
                    reason=reason
                ))

        # Sort by confidence and limit
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:limit]

    def get_recent_folders(self, limit: int = 10) -> list[str]:
        """
        Get recently used folders.

        Args:
            limit: Maximum number of folders

        Returns:
            List of folder paths ordered by recency
        """
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT folder FROM recent_folders
                ORDER BY last_used DESC
                LIMIT ?
            """, (limit,))

            return [row['folder'] for row in cursor.fetchall()]

    def get_popular_folders(self, limit: int = 10) -> list[str]:
        """
        Get most frequently used folders.

        Args:
            limit: Maximum number of folders

        Returns:
            List of folder paths ordered by usage count
        """
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT folder FROM recent_folders
                ORDER BY use_count DESC
                LIMIT ?
            """, (limit,))

            return [row['folder'] for row in cursor.fetchall()]

    def clear_old_preferences(self, days: int = 180) -> int:
        """
        Remove old preferences to keep database size manageable.

        Args:
            days: Remove preferences older than this many days

        Returns:
            Number of records deleted
        """
        with self._get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM folder_preferences
                WHERE last_used < datetime('now', ?)
            """, (f'-{days} days',))

            deleted = cursor.rowcount

        if deleted > 0:
            logger.info(f"Cleared {deleted} old folder preferences")

        return deleted


# Singleton instance
_preferences_store: Optional[FolderPreferencesStore] = None
_preferences_lock = threading.Lock()


def get_folder_preferences() -> FolderPreferencesStore:
    """Get the singleton FolderPreferencesStore instance."""
    global _preferences_store

    if _preferences_store is None:
        with _preferences_lock:
            if _preferences_store is None:
                _preferences_store = FolderPreferencesStore()

    return _preferences_store
