"""
PKM Health Check System

System health monitoring for:
- IMAP email server connectivity
- Anthropic AI API availability
- File system / storage
- Configuration validation
- Git repository status
"""

import time
import threading
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import logging

from src.core.schemas import HealthCheck, ServiceStatus, SystemHealth
from src.monitoring.logger import get_logger

logger = get_logger("health")


# ============================================================================
# CONSTANTS
# ============================================================================

# Health check constants
# Static fallback models in case API models.list() fails
# Ordered from newest to oldest
HEALTH_CHECK_MODELS_FALLBACK = [
    "claude-opus-4-5-20251101",    # Claude 4.5 Opus (newest known)
    "claude-haiku-4-5-20251001",   # Claude 4.5 Haiku
    "claude-sonnet-4-5-20250929",  # Claude 4.5 Sonnet
    "claude-opus-4-1-20250805",    # Claude 4.1 Opus
    "claude-opus-4-20250514",      # Claude 4 Opus
    "claude-sonnet-4-20250514",    # Claude 4 Sonnet
    "claude-3-5-haiku-20241022",   # Claude 3.5 Haiku
    "claude-3-haiku-20240307",     # Claude 3 Haiku (stable fallback)
]

# Disk space thresholds (percentage used)
DISK_SPACE_CRITICAL_THRESHOLD = 95
DISK_SPACE_WARNING_THRESHOLD = 85

# Queue size thresholds
QUEUE_SIZE_CRITICAL_THRESHOLD = 1000
QUEUE_SIZE_WARNING_THRESHOLD = 100


# ============================================================================
# HEALTH CHECK SERVICE
# ============================================================================


class HealthCheckService:
    """
    Health check service for monitoring system components

    Usage:
        health = HealthCheckService()
        health.register_checker("imap", check_imap_connection)
        health.register_checker("ai", check_anthropic_api)
        system_health = health.check_all()
    """

    def __init__(self):
        self._checkers: Dict[str, Callable[[], HealthCheck]] = {}
        self._cache: Dict[str, HealthCheck] = {}
        self._cache_duration_seconds = 60  # Cache health checks for 1 minute

    def register_checker(self, service: str, checker_func: Callable[[], HealthCheck]) -> None:
        """
        Register a health checker function

        Args:
            service: Service name (e.g., "imap", "ai", "storage")
            checker_func: Function that returns HealthCheck
        """
        self._checkers[service] = checker_func
        logger.debug(f"Registered health checker for {service}")

    def check_service(
        self, service: str, use_cache: bool = True
    ) -> Optional[HealthCheck]:
        """
        Check health of a specific service

        Args:
            service: Service name
            use_cache: Use cached result if available and fresh

        Returns:
            HealthCheck or None if service not registered
        """
        if service not in self._checkers:
            logger.warning(f"No health checker registered for {service}")
            return None

        # Check cache
        if use_cache and service in self._cache:
            cached = self._cache[service]
            # Use timezone-aware datetime for accurate comparison
            now = datetime.now(tz=timezone.utc)
            # Handle both timezone-aware and naive datetimes
            cached_time = cached.checked_at
            if cached_time.tzinfo is None:
                cached_time = cached_time.replace(tzinfo=timezone.utc)
            age_seconds = (now - cached_time).total_seconds()
            if age_seconds < self._cache_duration_seconds:
                logger.debug(f"Using cached health check for {service}")
                return cached

        # Run health check
        logger.debug(f"Running health check for {service}")
        start_time = time.time()

        try:
            health_check = self._checkers[service]()
            elapsed_ms = (time.time() - start_time) * 1000
            health_check.response_time_ms = elapsed_ms

            # Cache result
            self._cache[service] = health_check

            return health_check

        except Exception as e:
            logger.error(f"Health check failed for {service}: {e}", exc_info=True)
            elapsed_ms = (time.time() - start_time) * 1000

            return HealthCheck(
                service=service,
                status=ServiceStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                response_time_ms=elapsed_ms,
                details={"error": str(e), "type": type(e).__name__},
            )

    def check_all(self, use_cache: bool = True) -> SystemHealth:
        """
        Check health of all registered services

        Args:
            use_cache: Use cached results if available

        Returns:
            SystemHealth with all service checks
        """
        logger.info("Running system health check")

        checks: List[HealthCheck] = []
        for service in self._checkers:
            check = self.check_service(service, use_cache=use_cache)
            if check:
                checks.append(check)

        # Determine overall status
        if not checks:
            overall_status = ServiceStatus.UNKNOWN
        elif all(c.status == ServiceStatus.HEALTHY for c in checks):
            overall_status = ServiceStatus.HEALTHY
        elif any(c.status == ServiceStatus.UNHEALTHY for c in checks):
            overall_status = ServiceStatus.UNHEALTHY
        else:
            overall_status = ServiceStatus.DEGRADED

        system_health = SystemHealth(overall_status=overall_status, checks=checks)

        logger.info(
            f"System health: {overall_status.value}",
            extra={
                "healthy": len([c for c in checks if c.status == ServiceStatus.HEALTHY]),
                "degraded": len([c for c in checks if c.status == ServiceStatus.DEGRADED]),
                "unhealthy": len([c for c in checks if c.status == ServiceStatus.UNHEALTHY]),
            },
        )

        return system_health

    def clear_cache(self) -> None:
        """Clear cached health check results"""
        self._cache.clear()
        logger.debug("Cleared health check cache")


# ============================================================================
# BUILT-IN HEALTH CHECKERS
# ============================================================================


def check_filesystem_health(base_path: Path) -> HealthCheck:
    """
    Check filesystem health (read/write)

    Args:
        base_path: Base path to check (e.g., config directory)

    Returns:
        HealthCheck for filesystem
    """
    try:
        base_path = Path(base_path)

        # Check if path exists and is writable
        if not base_path.exists():
            return HealthCheck(
                service="filesystem",
                status=ServiceStatus.UNHEALTHY,
                message=f"Path does not exist: {base_path}",
                details={"path": str(base_path)},
            )

        # Try to create a test file
        test_file = base_path / ".health_check_test"
        try:
            test_file.write_text("health check")
            test_file.unlink()

            return HealthCheck(
                service="filesystem",
                status=ServiceStatus.HEALTHY,
                message="Filesystem is readable and writable",
                details={"path": str(base_path), "writable": True},
            )

        except (PermissionError, IOError) as e:
            return HealthCheck(
                service="filesystem",
                status=ServiceStatus.DEGRADED,
                message=f"Filesystem not writable: {e}",
                details={"path": str(base_path), "writable": False, "error": str(e)},
            )

    except Exception as e:
        return HealthCheck(
            service="filesystem",
            status=ServiceStatus.UNHEALTHY,
            message=f"Filesystem check failed: {e}",
            details={"error": str(e)},
        )


def check_git_health(repo_path: Path) -> HealthCheck:
    """
    Check Git repository health

    Args:
        repo_path: Path to Git repository

    Returns:
        HealthCheck for Git
    """
    try:
        import subprocess

        repo_path = Path(repo_path)
        git_dir = repo_path / ".git"

        if not git_dir.exists():
            return HealthCheck(
                service="git",
                status=ServiceStatus.DEGRADED,
                message="Git repository not initialized",
                details={"path": str(repo_path), "initialized": False},
            )

        # Check git status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return HealthCheck(
                service="git",
                status=ServiceStatus.UNHEALTHY,
                message=f"Git command failed: {result.stderr}",
                details={"error": result.stderr},
            )

        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        return HealthCheck(
            service="git",
            status=ServiceStatus.HEALTHY,
            message="Git repository is healthy",
            details={
                "path": str(repo_path),
                "initialized": True,
                "branch": current_branch,
                "has_changes": bool(result.stdout.strip()),
            },
        )

    except subprocess.TimeoutExpired:
        return HealthCheck(
            service="git",
            status=ServiceStatus.DEGRADED,
            message="Git command timed out",
            details={"error": "timeout"},
        )
    except Exception as e:
        return HealthCheck(
            service="git",
            status=ServiceStatus.UNHEALTHY,
            message=f"Git health check failed: {e}",
            details={"error": str(e)},
        )


def check_config_health(config_path: Path) -> HealthCheck:
    """
    Check configuration files health

    Args:
        config_path: Path to config directory

    Returns:
        HealthCheck for configuration
    """
    try:
        config_path = Path(config_path)

        if not config_path.exists():
            return HealthCheck(
                service="config",
                status=ServiceStatus.UNHEALTHY,
                message=f"Config directory not found: {config_path}",
                details={"path": str(config_path)},
            )

        # Check for required files
        required_files = ["defaults.yaml", "logging.yaml"]
        missing_files = []

        for file in required_files:
            if not (config_path / file).exists():
                missing_files.append(file)

        if missing_files:
            return HealthCheck(
                service="config",
                status=ServiceStatus.DEGRADED,
                message=f"Missing config files: {', '.join(missing_files)}",
                details={"missing_files": missing_files},
            )

        # Try to load config
        try:
            from src.core.config_manager import ConfigManager

            config = ConfigManager.load()

            return HealthCheck(
                service="config",
                status=ServiceStatus.HEALTHY,
                message="Configuration is valid and loaded",
                details={
                    "config_path": str(config_path),
                    "env_file": ".env exists",
                },
            )

        except Exception as e:
            return HealthCheck(
                service="config",
                status=ServiceStatus.DEGRADED,
                message=f"Config validation failed: {e}",
                details={"error": str(e)},
            )

    except Exception as e:
        return HealthCheck(
            service="config",
            status=ServiceStatus.UNHEALTHY,
            message=f"Config health check failed: {e}",
            details={"error": str(e)},
        )


def check_python_dependencies() -> HealthCheck:
    """
    Check Python dependencies are installed

    Returns:
        HealthCheck for Python dependencies
    """
    try:
        required_packages = [
            "pydantic",
            "anthropic",
            "imapclient",
            "rich",
            "typer",
            "pytest",
        ]

        missing = []
        installed = []

        for package in required_packages:
            try:
                __import__(package)
                installed.append(package)
            except ImportError:
                missing.append(package)

        if missing:
            return HealthCheck(
                service="dependencies",
                status=ServiceStatus.DEGRADED,
                message=f"Missing packages: {', '.join(missing)}",
                details={"missing": missing, "installed": installed},
            )

        return HealthCheck(
            service="dependencies",
            status=ServiceStatus.HEALTHY,
            message=f"All {len(installed)} required packages installed",
            details={"installed": installed},
        )

    except Exception as e:
        return HealthCheck(
            service="dependencies",
            status=ServiceStatus.UNHEALTHY,
            message=f"Dependency check failed: {e}",
            details={"error": str(e)},
        )


def check_imap_health() -> HealthCheck:
    """
    Check IMAP server connectivity

    Returns:
        HealthCheck for IMAP connection
    """
    try:
        # Import local to avoid circular dependency
        from src.core.config_manager import get_config
        from src.integrations.email.imap_client import IMAPClient

        config = get_config()

        # Check all enabled accounts
        enabled_accounts = config.email.get_enabled_accounts()

        if not enabled_accounts:
            return HealthCheck(
                service="imap",
                status=ServiceStatus.DEGRADED,
                message="No IMAP accounts configured",
                details={"accounts_count": 0},
            )

        # Test connection to first enabled account
        account = enabled_accounts[0]

        imap_client = None
        try:
            imap_client = IMAPClient(account)
            # Quick connection test (don't fetch emails) with timeout
            # Note: IMAPClient should handle timeouts via account.imap_timeout
            imap_client.connect()

            return HealthCheck(
                service="imap",
                status=ServiceStatus.HEALTHY,
                message=f"IMAP connection successful ({account.account_name})",
                details={
                    "account_id": account.account_id,
                    "account_name": account.account_name,
                    "host": account.imap_host,
                    "port": account.imap_port,
                    "accounts_count": len(enabled_accounts),
                },
            )

        except Exception as e:
            return HealthCheck(
                service="imap",
                status=ServiceStatus.UNHEALTHY,
                message=f"IMAP connection failed: {str(e)}",
                details={
                    "account_id": account.account_id,
                    "host": account.imap_host,
                    "error": str(e),
                },
            )
        finally:
            # Always try to disconnect, even if connect() failed
            if imap_client:
                try:
                    imap_client.disconnect()
                except Exception:
                    # Ignore errors during cleanup
                    pass

    except Exception as e:
        return HealthCheck(
            service="imap",
            status=ServiceStatus.UNHEALTHY,
            message=f"IMAP health check failed: {e}",
            details={"error": str(e)},
        )


def check_ai_api_health() -> HealthCheck:
    """
    Check Anthropic AI API connectivity

    Uses Haiku (fastest, cheapest) for health checks since count_tokens
    is a lightweight operation. Dynamically selects the latest Haiku version.

    Returns:
        HealthCheck for AI API
    """
    try:
        # Import local to avoid circular dependency
        from src.core.config_manager import get_config
        from src.ai.model_selector import ModelSelector, ModelTier

        config = get_config()

        # Use ModelSelector to get best Haiku model
        selector = ModelSelector(api_key=config.ai.anthropic_api_key)
        model = selector.get_best_model(
            tier=ModelTier.HAIKU,
            fallback_tiers=[ModelTier.SONNET, ModelTier.OPUS]
        )

        # Test the selected model
        import anthropic
        client = anthropic.Anthropic(api_key=config.ai.anthropic_api_key)

        try:
            # Minimal API call to test connectivity
            # Use count_tokens which is lightweight and doesn't consume credits
            _ = client.messages.count_tokens(
                model=model,
                messages=[{"role": "user", "content": "test"}]
            )

            # Success!
            return HealthCheck(
                service="ai_api",
                status=ServiceStatus.HEALTHY,
                message=f"Anthropic API connection successful",
                details={
                    "provider": "anthropic",
                    "api_available": True,
                    "model": model,
                    "tier": "haiku",
                },
            )

        except anthropic.AuthenticationError:
            return HealthCheck(
                service="ai_api",
                status=ServiceStatus.UNHEALTHY,
                message="Anthropic API authentication failed (invalid API key)",
                details={"provider": "anthropic", "error": "authentication_failed"},
            )

        except anthropic.RateLimitError:
            return HealthCheck(
                service="ai_api",
                status=ServiceStatus.DEGRADED,
                message="Anthropic API rate limit exceeded",
                details={"provider": "anthropic", "error": "rate_limit"},
            )

        except Exception as e:
            return HealthCheck(
                service="ai_api",
                status=ServiceStatus.UNHEALTHY,
                message=f"Anthropic API error: {str(e)}",
                details={"provider": "anthropic", "error": str(e), "model": model},
            )

    except Exception as e:
        return HealthCheck(
            service="ai_api",
            status=ServiceStatus.UNHEALTHY,
            message=f"AI API health check failed: {e}",
            details={"error": str(e)},
        )


def check_disk_space_health() -> HealthCheck:
    """
    Check available disk space

    Returns:
        HealthCheck for disk space
    """
    try:
        # Import local to avoid circular dependency
        from src.core.config_manager import get_config

        # Check disk space in data directory
        try:
            config = get_config()
            base_path = config.storage.database_path.parent  # data/
        except Exception:
            # Fallback to current directory if config fails
            base_path = Path.cwd()

        stat = shutil.disk_usage(base_path)

        total_gb = stat.total / (1024**3)
        used_gb = stat.used / (1024**3)
        free_gb = stat.free / (1024**3)
        percent_used = (stat.used / stat.total) * 100
        percent_free = 100 - percent_used

        # Check against thresholds
        if percent_used >= DISK_SPACE_CRITICAL_THRESHOLD:
            status = ServiceStatus.UNHEALTHY
            message = f"Disk space critical: {free_gb:.1f} GB free ({percent_free:.1f}%)"
        elif percent_used >= DISK_SPACE_WARNING_THRESHOLD:
            status = ServiceStatus.DEGRADED
            message = f"Disk space low: {free_gb:.1f} GB free ({percent_free:.1f}%)"
        else:
            status = ServiceStatus.HEALTHY
            message = f"Disk space healthy: {free_gb:.1f} GB free ({percent_free:.1f}%)"

        return HealthCheck(
            service="disk_space",
            status=status,
            message=message,
            details={
                "path": str(base_path),
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent_used": round(percent_used, 1),
                "percent_free": round(percent_free, 1),
            },
        )

    except Exception as e:
        return HealthCheck(
            service="disk_space",
            status=ServiceStatus.UNHEALTHY,
            message=f"Disk space check failed: {e}",
            details={"error": str(e)},
        )


def check_queue_health() -> HealthCheck:
    """
    Check review queue status

    Returns:
        HealthCheck for queue
    """
    try:
        # Import local to avoid circular dependency
        from src.integrations.storage.queue_storage import get_queue_storage

        queue_storage = get_queue_storage()
        stats = queue_storage.get_stats()

        total = stats.get("total", 0)
        pending = stats.get("by_status", {}).get("pending", 0)

        # Check against thresholds
        if total >= QUEUE_SIZE_CRITICAL_THRESHOLD:
            status = ServiceStatus.DEGRADED
            message = f"Queue large: {total} items ({pending} pending)"
        elif total >= QUEUE_SIZE_WARNING_THRESHOLD:
            status = ServiceStatus.DEGRADED
            message = f"Queue growing: {total} items ({pending} pending)"
        else:
            status = ServiceStatus.HEALTHY
            message = f"Queue healthy: {total} items ({pending} pending)"

        return HealthCheck(
            service="queue",
            status=status,
            message=message,
            details={
                "total": total,
                "pending": pending,
                "by_status": stats.get("by_status", {}),
                "oldest_item": stats.get("oldest_item"),
            },
        )

    except Exception as e:
        return HealthCheck(
            service="queue",
            status=ServiceStatus.UNHEALTHY,
            message=f"Queue health check failed: {e}",
            details={"error": str(e)},
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global health check service instance (thread-safe singleton)
_health_service: Optional[HealthCheckService] = None
_health_lock = threading.Lock()


def get_health_service() -> HealthCheckService:
    """
    Get global health check service (thread-safe singleton)

    Returns:
        HealthCheckService instance
    """
    global _health_service

    # Fast path: already initialized
    if _health_service is not None:
        return _health_service

    # Double-check locking for thread safety
    with _health_lock:
        if _health_service is not None:
            return _health_service

        _health_service = HealthCheckService()

        # Register built-in checkers
        from pathlib import Path

        base_path = Path.cwd()
        config_path = base_path / "config"

        _health_service.register_checker(
            "filesystem", lambda: check_filesystem_health(base_path)
        )
        _health_service.register_checker("git", lambda: check_git_health(base_path))
        _health_service.register_checker(
            "config", lambda: check_config_health(config_path)
        )
        _health_service.register_checker("dependencies", check_python_dependencies)

        # Register Phase 3 comprehensive health checks
        _health_service.register_checker("imap", check_imap_health)
        _health_service.register_checker("ai_api", check_ai_api_health)
        _health_service.register_checker("disk_space", check_disk_space_health)
        _health_service.register_checker("queue", check_queue_health)

    return _health_service


def quick_health_check() -> SystemHealth:
    """
    Quick health check of all services

    Returns:
        SystemHealth result
    """
    service = get_health_service()
    return service.check_all(use_cache=False)
