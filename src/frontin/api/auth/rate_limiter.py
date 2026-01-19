"""
Login Rate Limiter

Simple in-memory rate limiter for login attempts.
Prevents brute-force attacks on PIN authentication.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.auth.rate_limiter")


@dataclass
class AttemptInfo:
    """Tracks login attempts for a client."""

    count: int = 0
    first_attempt: float = field(default_factory=time.time)
    last_attempt: float = field(default_factory=time.time)
    locked_until: Optional[float] = None

    def is_locked(self) -> bool:
        """Check if the client is currently locked out."""
        if self.locked_until is None:
            return False
        if time.time() > self.locked_until:
            # Lock expired
            self.locked_until = None
            return False
        return True

    def remaining_lockout(self) -> int:
        """Get remaining lockout time in seconds."""
        if self.locked_until is None:
            return 0
        remaining = self.locked_until - time.time()
        return max(0, int(remaining))


class LoginRateLimiter:
    """
    Rate limiter for login attempts.

    Features:
    - Tracks failed attempts per client (IP or identifier)
    - Exponential lockout after max_attempts failures
    - Auto-cleanup of old entries
    - Thread-safe operations

    Configuration:
    - max_attempts: Number of attempts before lockout (default: 5)
    - window_seconds: Time window for counting attempts (default: 300s = 5 min)
    - lockout_seconds: Initial lockout duration (default: 60s)
    - lockout_multiplier: Multiplier for repeated lockouts (default: 2.0)
    - max_lockout_seconds: Maximum lockout duration (default: 3600s = 1 hour)
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 300,
        lockout_seconds: int = 60,
        lockout_multiplier: float = 2.0,
        max_lockout_seconds: int = 3600,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self.lockout_multiplier = lockout_multiplier
        self.max_lockout_seconds = max_lockout_seconds

        self._attempts: dict[str, AttemptInfo] = defaultdict(AttemptInfo)
        self._lockout_counts: dict[str, int] = defaultdict(int)
        self._lock = Lock()

        logger.info(
            f"LoginRateLimiter initialized: max_attempts={max_attempts}, "
            f"window={window_seconds}s, lockout={lockout_seconds}s"
        )

    def check_rate_limit(self, client_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if a client is allowed to attempt login.

        Args:
            client_id: Identifier for the client (IP address or other)

        Returns:
            Tuple of (allowed, error_message)
            - (True, None) if attempt is allowed
            - (False, "error message") if rate limited
        """
        with self._lock:
            info = self._attempts[client_id]

            # Check if locked
            if info.is_locked():
                remaining = info.remaining_lockout()
                logger.warning(f"Rate limit: {client_id} is locked for {remaining}s more")
                return False, f"Trop de tentatives. Réessayez dans {remaining} secondes."

            # Clean old attempts if window expired
            now = time.time()
            if now - info.first_attempt > self.window_seconds:
                # Reset window
                info.count = 0
                info.first_attempt = now

            return True, None

    def record_attempt(self, client_id: str, success: bool) -> None:
        """
        Record a login attempt.

        Args:
            client_id: Identifier for the client
            success: Whether the login was successful
        """
        with self._lock:
            info = self._attempts[client_id]
            info.last_attempt = time.time()

            if success:
                # Reset on successful login
                info.count = 0
                self._lockout_counts[client_id] = 0
                logger.debug(f"Rate limit: {client_id} login success, counters reset")
            else:
                # Increment failed attempts
                info.count += 1
                logger.debug(
                    f"Rate limit: {client_id} failed attempt "
                    f"{info.count}/{self.max_attempts}"
                )

                # Check if should lock
                if info.count >= self.max_attempts:
                    self._lockout_counts[client_id] += 1
                    lockout_time = min(
                        self.lockout_seconds
                        * (self.lockout_multiplier ** (self._lockout_counts[client_id] - 1)),
                        self.max_lockout_seconds,
                    )
                    info.locked_until = time.time() + lockout_time
                    info.count = 0  # Reset count after locking

                    logger.warning(
                        f"Rate limit: {client_id} locked for {lockout_time:.0f}s "
                        f"(lockout #{self._lockout_counts[client_id]})"
                    )

    def cleanup(self, max_age_seconds: int = 86400) -> int:
        """
        Remove old entries to prevent memory growth.

        Args:
            max_age_seconds: Remove entries older than this (default: 24 hours)

        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0

        with self._lock:
            clients_to_remove = []
            for client_id, info in self._attempts.items():
                if now - info.last_attempt > max_age_seconds:
                    clients_to_remove.append(client_id)

            for client_id in clients_to_remove:
                del self._attempts[client_id]
                if client_id in self._lockout_counts:
                    del self._lockout_counts[client_id]
                removed += 1

        if removed > 0:
            logger.debug(f"Rate limiter cleanup: removed {removed} old entries")

        return removed

    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        with self._lock:
            locked_count = sum(1 for info in self._attempts.values() if info.is_locked())
            return {
                "total_clients": len(self._attempts),
                "locked_clients": locked_count,
                "max_attempts": self.max_attempts,
                "window_seconds": self.window_seconds,
            }


# Global rate limiter instance
_rate_limiter: Optional[LoginRateLimiter] = None


def get_login_rate_limiter() -> LoginRateLimiter:
    """Get the global login rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = LoginRateLimiter()
    return _rate_limiter


def reset_login_rate_limiter() -> None:
    """Reset the global rate limiter (for testing)."""
    global _rate_limiter
    _rate_limiter = None
