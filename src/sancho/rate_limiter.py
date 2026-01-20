"""
Rate Limiter

Thread-safe sliding window rate limiter to prevent API rate limit errors.
"""

import threading
import time
from collections import deque
from typing import Any, Optional

from src.monitoring.logger import get_logger

logger = get_logger("rate_limiter")


class RateLimiter:
    """
    Thread-safe rate limiter

    Implements sliding window rate limiting to prevent API rate limit errors.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: deque[float] = deque()
        self._lock = threading.Lock()

        logger.debug(
            "Rate limiter initialized",
            extra={"max_requests": max_requests, "window_seconds": window_seconds},
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        with self._lock:
            return (
                f"RateLimiter(max_requests={self.max_requests}, "
                f"window={self.window_seconds}s, "
                f"current={len(self._requests)})"
            )

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()

        while True:
            with self._lock:
                # Remove old requests outside the window
                now = time.time()
                while self._requests and self._requests[0] < now - self.window_seconds:
                    self._requests.popleft()

                # Check if we can make a request
                if len(self._requests) < self.max_requests:
                    self._requests.append(now)
                    return True

            # Check timeout
            if timeout is not None and (time.time() - start_time) >= timeout:
                logger.warning("Rate limit timeout reached")
                return False

            # Wait before retrying
            time.sleep(0.1)

    def get_current_usage(self) -> dict[str, Any]:
        """
        Get current rate limiter usage

        Returns:
            Dict with usage statistics
        """
        with self._lock:
            now = time.time()
            # Clean old requests
            while self._requests and self._requests[0] < now - self.window_seconds:
                self._requests.popleft()

            return {
                "current_requests": len(self._requests),
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "usage_percent": (len(self._requests) / self.max_requests) * 100,
            }
