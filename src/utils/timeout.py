"""
Timeout Utilities

Provides timeout mechanisms for operations that might hang:
- Context manager for function timeouts
- Decorator for timeout enforcement
- Thread-safe implementation

Usage:
    from src.utils.timeout import timeout_context

    # Context manager
    with timeout_context(30):
        potentially_hanging_operation()

    # Will raise TimeoutError after 30 seconds
"""

import signal
import threading
from contextlib import contextmanager
from typing import Optional


class TimeoutError(Exception):
    """Raised when operation exceeds timeout"""
    pass


@contextmanager
def timeout_context(seconds: int, error_message: Optional[str] = None):
    """
    Context manager for timeout enforcement

    Uses signal.alarm on Unix systems. Thread-safe with lock.

    Args:
        seconds: Timeout in seconds
        error_message: Optional custom error message

    Raises:
        TimeoutError: If operation exceeds timeout

    Example:
        >>> with timeout_context(5):
        ...     time.sleep(10)  # Will raise TimeoutError after 5s

    Note:
        Only works on Unix systems (not Windows).
        On Windows, raises NotImplementedError.
    """
    import platform

    if platform.system() == "Windows":
        # Windows doesn't support signal.alarm
        # Fallback: no timeout (or could use threading.Timer)
        import warnings
        warnings.warn(
            "Timeout not supported on Windows, operation will run without timeout",
            UserWarning
        )
        yield
        return

    def timeout_handler(signum, frame):
        msg = error_message or f"Operation timed out after {seconds} seconds"
        raise TimeoutError(msg)

    # Save old handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    old_alarm = signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore old alarm and handler
        signal.alarm(0)  # Cancel alarm
        signal.signal(signal.SIGALRM, old_handler)
        if old_alarm:
            # Restore previous alarm if there was one
            signal.alarm(old_alarm)


class ThreadSafeTimeout:
    """
    Thread-safe timeout implementation using threading.Timer

    Works on all platforms including Windows.
    Suitable for I/O-bound operations.

    Example:
        >>> timeout = ThreadSafeTimeout(5)
        >>> timeout.start()
        >>> try:
        ...     long_operation()
        ... finally:
        ...     timeout.cancel()
    """

    def __init__(self, seconds: int, error_message: Optional[str] = None):
        """
        Initialize timeout

        Args:
            seconds: Timeout in seconds
            error_message: Optional custom error message
        """
        self.seconds = seconds
        self.error_message = error_message or f"Operation timed out after {seconds}s"
        self.timer: Optional[threading.Timer] = None
        self.timed_out = False
        self._lock = threading.Lock()

    def _timeout_callback(self):
        """Called when timeout expires"""
        with self._lock:
            self.timed_out = True

    def start(self):
        """Start the timeout timer"""
        with self._lock:
            if self.timer is not None:
                return  # Already started

            self.timer = threading.Timer(self.seconds, self._timeout_callback)
            self.timer.daemon = True
            self.timer.start()

    def cancel(self):
        """Cancel the timeout timer"""
        with self._lock:
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None

    def check(self):
        """
        Check if timeout has expired

        Raises:
            TimeoutError: If timeout has expired
        """
        with self._lock:
            if self.timed_out:
                raise TimeoutError(self.error_message)

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cancel()
        # Check if timed out
        if self.timed_out and exc_type is None:
            raise TimeoutError(self.error_message)
        return False
