"""
Valets Stats Service

Aggregates real statistics from all valet workers (Trivelin, Sancho, etc.)
by querying the actual singletons and storage.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ValetsStatsService:
    """
    Service that aggregates real statistics from all valet workers.

    Queries the existing singletons:
    - StateManager for session/email stats (Trivelin)
    - AIRouter for AI metrics (Sancho)
    - LearningEngine for learning stats (Sganarelle)
    - ContextEngine for knowledge base stats (Passepartout)
    - etc.
    """

    def __init__(self) -> None:
        """Initialize the service."""
        self._last_refresh = datetime.now(timezone.utc)

    def get_trivelin_stats(self) -> dict[str, Any]:
        """
        Get Trivelin (email processor) statistics.

        Returns:
            Dict with processing stats
        """
        try:
            from src.core.state_manager import get_state_manager
            state = get_state_manager()
            stats = state.stats

            return {
                "status": "running" if state.processing_state.value == "running" else "idle",
                "current_task": None,
                "tasks_today": stats.emails_processed,
                "errors_today": stats.emails_failed,
                "details": {
                    "emails_processed": stats.emails_processed,
                    "emails_skipped": stats.emails_skipped,
                    "emails_archived": stats.archived,
                    "emails_deleted": stats.deleted,
                    "tasks_created": stats.tasks_created,
                    "notes_enriched": stats.notes_enriched,
                    "confidence_avg": stats.confidence_avg,
                    "duration_minutes": stats.duration_minutes,
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get Trivelin stats: {e}")
            return self._empty_stats()

    def get_sancho_stats(self) -> dict[str, Any]:
        """
        Get Sancho (AI reasoning) statistics.

        Returns:
            Dict with AI metrics
        """
        try:
            from src.sancho.router import get_ai_router
            router = get_ai_router()
            metrics = router.get_ai_metrics()

            return {
                "status": "idle",
                "current_task": None,
                "tasks_today": metrics.get("total_requests", 0),
                "errors_today": sum(metrics.get("errors_by_type", {}).values()),
                "details": {
                    "total_requests": metrics.get("total_requests", 0),
                    "total_tokens": metrics.get("total_tokens", 0),
                    "total_cost_usd": metrics.get("total_cost_usd", 0),
                    "avg_duration_ms": metrics.get("avg_duration_ms", 0),
                    "p95_duration_ms": metrics.get("p95_duration_ms", 0),
                    "errors_by_type": metrics.get("errors_by_type", {}),
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get Sancho stats: {e}")
            return self._empty_stats()

    def get_passepartout_stats(self) -> dict[str, Any]:
        """
        Get Passepartout (knowledge base) statistics.

        Returns:
            Dict with context engine stats
        """
        try:
            from src.passepartout.context_engine import get_context_engine
            engine = get_context_engine()
            stats = engine.get_stats()

            # Also get note manager stats if available
            note_stats = {}
            try:
                from src.passepartout.note_manager import get_note_manager
                note_manager = get_note_manager()
                note_stats = note_manager.get_cache_stats()
            except Exception:
                pass

            return {
                "status": "idle",
                "current_task": None,
                "tasks_today": stats.get("total_queries", 0),
                "errors_today": 0,
                "details": {
                    "total_queries": stats.get("total_queries", 0),
                    "cache_hits": stats.get("cache_hits", 0),
                    "cache_misses": stats.get("cache_misses", 0),
                    "avg_query_time_ms": stats.get("avg_query_time_ms", 0),
                    "notes_indexed": note_stats.get("indexed_notes", 0),
                    "notes_cached": note_stats.get("cached_notes", 0),
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get Passepartout stats: {e}")
            return self._empty_stats()

    def get_planchet_stats(self) -> dict[str, Any]:
        """
        Get Planchet (planning) statistics.

        Note: Planchet doesn't have a persistent singleton yet,
        so we return minimal stats from action history.
        """
        try:
            from src.integrations.storage.action_history import get_action_history
            history = get_action_history()
            stats = history.get_stats()

            return {
                "status": "idle",
                "current_task": None,
                "tasks_today": stats.get("total_actions", 0),
                "errors_today": 0,
                "details": {
                    "plans_created": stats.get("total_actions", 0),
                    "rollbacks": stats.get("rollbacks", 0),
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get Planchet stats: {e}")
            return self._empty_stats()

    def get_figaro_stats(self) -> dict[str, Any]:
        """
        Get Figaro (execution) statistics.

        Returns:
            Dict with action execution stats
        """
        try:
            from src.integrations.storage.action_history import get_action_history
            history = get_action_history()
            stats = history.get_stats()

            return {
                "status": "idle",
                "current_task": None,
                "tasks_today": stats.get("total_actions", 0),
                "errors_today": stats.get("failed_actions", 0),
                "details": {
                    "total_actions": stats.get("total_actions", 0),
                    "successful_actions": stats.get("successful_actions", 0),
                    "failed_actions": stats.get("failed_actions", 0),
                    "pending_actions": stats.get("pending_actions", 0),
                    "rollbacks": stats.get("rollbacks", 0),
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get Figaro stats: {e}")
            return self._empty_stats()

    def get_sganarelle_stats(self) -> dict[str, Any]:
        """
        Get Sganarelle (learning) statistics.

        Returns:
            Dict with learning engine stats
        """
        try:
            from src.sganarelle.learning_engine import get_learning_engine
            engine = get_learning_engine()
            stats = engine.get_stats()

            # Get calibrator stats for confidence info
            calibrator_stats = stats.get("confidence_calibrator", {})

            return {
                "status": "idle",
                "current_task": None,
                "tasks_today": stats.get("learning_cycles", 0),
                "errors_today": 0,
                "details": {
                    "learning_cycles": stats.get("learning_cycles", 0),
                    "total_learning_time": stats.get("total_learning_time", 0),
                    "avg_learning_time": stats.get("avg_learning_time", 0),
                    "last_learning": stats.get("last_learning"),
                    "patterns_stored": stats.get("pattern_store", {}).get("total_patterns", 0),
                    "avg_confidence": calibrator_stats.get("avg_confidence", 0.85),
                    "calibration_accuracy": calibrator_stats.get("accuracy", 0.0),
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get Sganarelle stats: {e}")
            return self._empty_stats()

    def get_frontin_stats(self) -> dict[str, Any]:
        """
        Get Frontin (API) statistics.

        Returns:
            Dict with API stats
        """
        try:
            from src.frontin.api.auth.rate_limiter import get_rate_limiter
            limiter = get_rate_limiter()
            limiter_stats = limiter.get_stats()

            return {
                "status": "running",
                "current_task": "Serving API requests",
                "tasks_today": limiter_stats.get("total_requests", 0),
                "errors_today": limiter_stats.get("blocked_requests", 0),
                "details": {
                    "total_requests": limiter_stats.get("total_requests", 0),
                    "blocked_requests": limiter_stats.get("blocked_requests", 0),
                    "active_rate_limits": limiter_stats.get("active_limits", 0),
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get Frontin stats: {e}")
            # Frontin is always running if we can respond
            return {
                "status": "running",
                "current_task": "Serving API requests",
                "tasks_today": 0,
                "errors_today": 0,
                "details": {}
            }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all valets.

        Returns:
            Dict mapping valet name to stats
        """
        return {
            "trivelin": self.get_trivelin_stats(),
            "sancho": self.get_sancho_stats(),
            "passepartout": self.get_passepartout_stats(),
            "planchet": self.get_planchet_stats(),
            "figaro": self.get_figaro_stats(),
            "sganarelle": self.get_sganarelle_stats(),
            "frontin": self.get_frontin_stats(),
        }

    def get_aggregate_metrics(self) -> dict[str, Any]:
        """
        Get aggregated metrics across all valets.

        Returns:
            Dict with aggregate metrics
        """
        all_stats = self.get_all_stats()

        total_tasks = sum(s.get("tasks_today", 0) for s in all_stats.values())
        total_errors = sum(s.get("errors_today", 0) for s in all_stats.values())
        active_workers = sum(
            1 for s in all_stats.values()
            if s.get("status") == "running"
        )

        # Get confidence from Sganarelle
        sganarelle_details = all_stats.get("sganarelle", {}).get("details", {})
        avg_confidence = sganarelle_details.get("avg_confidence", 0.85)

        # Or from Trivelin if available
        trivelin_details = all_stats.get("trivelin", {}).get("details", {})
        if trivelin_details.get("confidence_avg", 0) > 0:
            avg_confidence = trivelin_details.get("confidence_avg", 0) / 100.0

        return {
            "total_tasks_today": total_tasks,
            "total_errors_today": total_errors,
            "active_workers": active_workers,
            "avg_confidence": avg_confidence,
            "timestamp": datetime.now(timezone.utc),
        }

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty stats structure."""
        return {
            "status": "idle",
            "current_task": None,
            "tasks_today": 0,
            "errors_today": 0,
            "details": {}
        }


# Singleton instance
_stats_service: ValetsStatsService | None = None


def get_valets_stats_service() -> ValetsStatsService:
    """
    Get the valets stats service singleton.

    Returns:
        ValetsStatsService instance
    """
    global _stats_service
    if _stats_service is None:
        _stats_service = ValetsStatsService()
    return _stats_service
