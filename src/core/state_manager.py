"""
PKM State Manager

Gestionnaire d'état centralisé thread-safe pour:
- État de session (emails traités, stats, etc.)
- Caches temporaires (entités, contextes)
- Flags de contrôle (pause, stop, etc.)

Utilise locks pour thread-safety (batch processing parallèle).
"""

import builtins
import copy
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ProcessingState(str, Enum):
    """États de traitement"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SessionStats:
    """Statistiques de session"""

    # Timestamps
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Volume
    emails_processed: int = 0
    emails_skipped: int = 0
    emails_failed: int = 0

    # Actions
    archived: int = 0
    deleted: int = 0
    referenced: int = 0
    tasks_created: int = 0
    notes_enriched: int = 0

    # AI Performance
    confidence_scores: list[int] = field(default_factory=list)
    ai_calls: int = 0
    multi_ai_verifications: int = 0
    user_overrides: int = 0

    # Efficiency
    api_cost_usd: float = 0.0

    @property
    def confidence_avg(self) -> float:
        """Moyenne de confiance"""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores) / len(self.confidence_scores)

    @property
    def duration_minutes(self) -> int:
        """Durée de session en minutes"""
        end = self.end_time or datetime.now()
        delta = end - self.start_time
        return int(delta.total_seconds() / 60)

    @property
    def emails_per_minute(self) -> float:
        """Vitesse de traitement"""
        if self.duration_minutes == 0:
            return 0.0
        return self.emails_processed / self.duration_minutes


class StateManager:
    """
    Gestionnaire d'état centralisé thread-safe

    Usage:
        state = StateManager()

        # Set state
        state.set("current_email_id", "abc123")
        state.increment("emails_processed")

        # Get state
        email_id = state.get("current_email_id")
        count = state.get("emails_processed", default=0)

        # Session stats
        state.stats.archived += 1
        state.stats.confidence_scores.append(95)
    """

    def __init__(self):
        """Initialize state manager"""
        self._state: dict[str, Any] = {}
        self._lock = threading.RLock()  # Reentrant lock to prevent deadlocks
        self._processing_state = ProcessingState.IDLE
        self._stats = SessionStats()

        # Caches
        self._entity_cache: dict[str, Any] = {}
        self._context_cache: dict[str, Any] = {}

        # Processed tracking (éviter duplicates)
        self._processed_message_ids: set[str] = set()

    @property
    def stats(self) -> SessionStats:
        """
        Get session statistics

        Note: Returns the actual stats object. For thread-safe mutations,
        use the StateManager methods like add_confidence_score().
        """
        return self._stats

    def add_confidence_score(self, score: int) -> None:
        """
        Add confidence score (thread-safe)

        Args:
            score: Confidence score to add
        """
        with self._lock:
            self._stats.confidence_scores.append(score)

    def get_average_confidence(self) -> float:
        """
        Get average confidence score across all processed emails

        Returns:
            Average confidence (0-100) or 0 if no scores
        """
        with self._lock:
            return self._stats.confidence_avg

    @property
    def processing_state(self) -> ProcessingState:
        """Get current processing state"""
        with self._lock:
            return self._processing_state

    @processing_state.setter
    def processing_state(self, value: ProcessingState) -> None:
        """Set processing state"""
        with self._lock:
            self._processing_state = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get state value

        Args:
            key: State key
            default: Default value if key not found

        Returns:
            State value or default
        """
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set state value

        Args:
            key: State key
            value: State value
        """
        with self._lock:
            self._state[key] = value

    def delete(self, key: str) -> None:
        """
        Delete state key

        Args:
            key: State key to delete
        """
        with self._lock:
            self._state.pop(key, None)

    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter (thread-safe)

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New value
        """
        with self._lock:
            current = self._state.get(key, 0)
            new_value = current + amount
            self._state[key] = new_value
            return new_value

    def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement counter (thread-safe)

        Args:
            key: Counter key
            amount: Amount to decrement

        Returns:
            New value
        """
        return self.increment(key, -amount)

    def add_to_list(self, key: str, value: Any) -> list[Any]:
        """
        Add value to list (thread-safe)

        Args:
            key: List key
            value: Value to append

        Returns:
            Updated list
        """
        with self._lock:
            current = self._state.get(key, [])
            if not isinstance(current, list):
                current = []
            current.append(value)
            self._state[key] = current
            return current

    def add_to_set(self, key: str, value: Any) -> builtins.set[Any]:
        """
        Add value to set (thread-safe)

        Args:
            key: Set key
            value: Value to add

        Returns:
            Updated set
        """
        with self._lock:
            current = self._state.get(key, set())
            if not isinstance(current, set):
                current = set()
            current.add(value)
            self._state[key] = current
            return current

    def is_processed(self, message_id: str) -> bool:
        """
        Check if message ID already processed

        Args:
            message_id: Email message ID

        Returns:
            True if already processed
        """
        with self._lock:
            return message_id in self._processed_message_ids

    def mark_processed(self, message_id: str) -> None:
        """
        Mark message ID as processed

        Args:
            message_id: Email message ID
        """
        with self._lock:
            self._processed_message_ids.add(message_id)

    def cache_entity(self, entity_id: str, entity_data: Any) -> None:
        """
        Cache entity data

        Args:
            entity_id: Entity identifier
            entity_data: Entity data to cache
        """
        with self._lock:
            self._entity_cache[entity_id] = entity_data

    def get_cached_entity(self, entity_id: str) -> Optional[Any]:
        """
        Get cached entity

        Args:
            entity_id: Entity identifier

        Returns:
            Cached entity data or None
        """
        with self._lock:
            return self._entity_cache.get(entity_id)

    def clear_caches(self) -> None:
        """Clear all caches"""
        with self._lock:
            self._entity_cache.clear()
            self._context_cache.clear()

    def reset_session(self) -> None:
        """Reset session state and stats"""
        with self._lock:
            self._stats = SessionStats()
            self._processed_message_ids.clear()
            self._processing_state = ProcessingState.IDLE

    def end_session(self) -> SessionStats:
        """
        End current session and return stats

        Returns:
            Final session statistics
        """
        with self._lock:
            self._stats.end_time = datetime.now()
            self._processing_state = ProcessingState.IDLE
            return self._stats

    def to_dict(self) -> dict[str, Any]:
        """
        Export state as dictionary (deep copy for thread safety)

        Returns:
            State dictionary (deep copy)
        """
        with self._lock:
            return {
                "state": copy.deepcopy(self._state),
                "processing_state": self._processing_state.value,
                "stats": {
                    "emails_processed": self._stats.emails_processed,
                    "emails_skipped": self._stats.emails_skipped,
                    "archived": self._stats.archived,
                    "deleted": self._stats.deleted,
                    "referenced": self._stats.referenced,
                    "confidence_avg": self._stats.confidence_avg,
                    "duration_minutes": self._stats.duration_minutes,
                },
                "processed_count": len(self._processed_message_ids),
            }


# Global instance (singleton)
_state_manager: Optional[StateManager] = None
_state_manager_lock = threading.Lock()


def get_state_manager() -> StateManager:
    """
    Get global state manager instance

    Thread-safe singleton with double-check locking pattern.

    Usage:
        from core.state_manager import get_state_manager

        state = get_state_manager()
        state.increment("emails_processed")
    """
    global _state_manager

    # Fast path
    if _state_manager is not None:
        return _state_manager

    # Slow path with lock
    with _state_manager_lock:
        # Double-check inside lock
        if _state_manager is None:
            _state_manager = StateManager()

    return _state_manager
