"""
Circuit Breaker Pattern

Prevents repeated calls to failing services by "opening" the circuit
after a threshold of failures.
"""

import threading
import time
from typing import Any, Callable, Optional

from src.monitoring.logger import get_logger

logger = get_logger("circuit_breaker")


class CircuitBreakerOpenError(Exception):
    """
    Raised when circuit breaker is open (service unavailable)

    This exception indicates that the circuit breaker has detected
    repeated failures and is blocking requests to prevent cascading failures.
    """

    pass


class CircuitBreaker:
    """
    Circuit breaker pattern for API calls

    Prevents repeated calls to failing services by "opening" the circuit
    after a threshold of failures. After a timeout period, allows a test
    request through ("half-open" state).

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Failure threshold exceeded, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery (half-open)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function raises
        """
        with self._lock:
            # Check if circuit should transition to half-open
            if self.state == "open":
                if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                    self.state = "half-open"
                    logger.info("Circuit breaker entering half-open state (testing recovery)")
                else:
                    remaining = int(self.timeout - (time.time() - (self.last_failure_time or 0)))
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN - service unavailable "
                        f"(timeout: {self.timeout}s, remaining: {remaining}s)"
                    )

        # Attempt the call
        try:
            result = func(*args, **kwargs)

            # Success - reset or close circuit
            with self._lock:
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                    logger.info("Circuit breaker CLOSED - service recovered")

            return result

        except Exception:
            # Failure - increment counter and potentially open circuit
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(
                        f"Circuit breaker OPENED after {self.failure_count} failures",
                        extra={"failure_threshold": self.failure_threshold},
                    )

            raise
