"""
Unit Tests for Timeout Utilities

Tests timeout_context and ThreadSafeTimeout functionality.
"""

import platform
import time

import pytest

from src.utils.timeout import ThreadSafeTimeout, TimeoutError, timeout_context


class TestTimeoutContext:
    """Test timeout_context context manager"""

    @pytest.mark.skipif(platform.system() == "Windows", reason="timeout_context not supported on Windows")
    def test_timeout_context_completes_within_limit(self):
        """Test operation that completes within timeout"""
        with timeout_context(2):
            time.sleep(0.1)
        # Should complete without error

    @pytest.mark.skipif(platform.system() == "Windows", reason="timeout_context not supported on Windows")
    def test_timeout_context_exceeds_limit(self):
        """Test operation that exceeds timeout"""
        with pytest.raises(TimeoutError), timeout_context(1):
            time.sleep(2)

    @pytest.mark.skipif(platform.system() == "Windows", reason="timeout_context not supported on Windows")
    def test_timeout_context_custom_message(self):
        """Test custom error message"""
        with pytest.raises(TimeoutError, match="Custom timeout message"):
            with timeout_context(1, error_message="Custom timeout message"):
                time.sleep(2)

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_timeout_context_windows_warning(self):
        """Test that Windows shows warning instead of timing out"""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with timeout_context(1):
                time.sleep(2)  # Would timeout on Unix, but not on Windows

            # Should have warning
            assert len(w) == 1
            assert "not supported on Windows" in str(w[0].message)


class TestThreadSafeTimeout:
    """Test ThreadSafeTimeout class"""

    def test_timeout_no_expiry(self):
        """Test timeout that doesn't expire"""
        timeout = ThreadSafeTimeout(2)
        timeout.start()

        time.sleep(0.1)
        timeout.check()  # Should not raise

        timeout.cancel()

    def test_timeout_expiry(self):
        """Test timeout that expires"""
        timeout = ThreadSafeTimeout(1)
        timeout.start()

        time.sleep(1.5)

        with pytest.raises(TimeoutError):
            timeout.check()

    def test_timeout_cancel(self):
        """Test canceling timeout"""
        timeout = ThreadSafeTimeout(1)
        timeout.start()
        timeout.cancel()

        time.sleep(1.5)
        timeout.check()  # Should not raise because canceled

    def test_timeout_context_manager(self):
        """Test using ThreadSafeTimeout as context manager"""
        with ThreadSafeTimeout(2) as timeout:
            time.sleep(0.1)
        # Should complete without error

    def test_timeout_context_manager_expiry(self):
        """Test context manager with expired timeout"""
        with pytest.raises(TimeoutError), ThreadSafeTimeout(1):
            time.sleep(1.5)

    def test_timeout_custom_message(self):
        """Test custom error message"""
        timeout = ThreadSafeTimeout(1, error_message="Custom message")
        timeout.start()

        time.sleep(1.5)

        with pytest.raises(TimeoutError, match="Custom message"):
            timeout.check()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
