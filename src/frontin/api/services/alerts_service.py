"""
Alerts Service

Monitors valet health and generates alerts based on configurable rules.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from src.frontin.api.models.valets import Alert, AlertSeverity, AlertsResponse

logger = logging.getLogger(__name__)


class AlertRule:
    """A rule that can trigger an alert"""

    def __init__(
        self,
        name: str,
        check: Callable[[dict[str, Any]], bool],
        severity: AlertSeverity,
        message_template: str,
        valet: str | None = None,
    ):
        self.name = name
        self.check = check
        self.severity = severity
        self.message_template = message_template
        self.valet = valet


class AlertsService:
    """
    Service that monitors valet health and generates alerts.

    Rules:
    - High error rate (>10%) → Warning
    - Queue growing rapidly → Warning
    - Valet in error state → Critical
    - Learning cycle stale (>24h) → Info
    - Low confidence trend → Warning
    """

    # Alert thresholds
    ERROR_RATE_THRESHOLD = 0.10  # 10%
    QUEUE_GROWTH_THRESHOLD = 5  # items/min
    LEARNING_STALE_HOURS = 24
    LOW_CONFIDENCE_THRESHOLD = 0.70

    def __init__(self) -> None:
        """Initialize the alerts service."""
        self._active_alerts: dict[str, Alert] = {}
        self._last_check = datetime.now(timezone.utc)

    def check_alerts(self, stats: dict[str, Any]) -> AlertsResponse:
        """
        Check all alert rules against current stats.

        Args:
            stats: Dictionary with valet stats from ValetsStatsService

        Returns:
            AlertsResponse with all active alerts
        """
        alerts: list[Alert] = []

        # Check each valet for issues
        for valet_name, valet_stats in stats.items():
            valet_alerts = self._check_valet(valet_name, valet_stats)
            alerts.extend(valet_alerts)

        # Check system-wide alerts
        system_alerts = self._check_system(stats)
        alerts.extend(system_alerts)

        # Sort by severity (critical first) then by time
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.INFO: 2,
        }
        alerts.sort(key=lambda a: (severity_order[a.severity], a.triggered_at))

        return AlertsResponse(
            alerts=alerts,
            total_critical=sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL),
            total_warning=sum(1 for a in alerts if a.severity == AlertSeverity.WARNING),
            total_info=sum(1 for a in alerts if a.severity == AlertSeverity.INFO),
        )

    def _check_valet(self, valet_name: str, stats: dict[str, Any]) -> list[Alert]:
        """Check a single valet for alert conditions."""
        alerts: list[Alert] = []

        # Check if valet is in error state
        if stats.get("status") == "error":
            alerts.append(
                Alert(
                    id=f"valet_error_{valet_name}",
                    severity=AlertSeverity.CRITICAL,
                    valet=valet_name,
                    message=f"{valet_name.capitalize()} est en erreur",
                    details="Le valet a rencontré une erreur et ne traite plus de tâches",
                )
            )

        # Check error rate
        tasks_today = stats.get("tasks_today", 0)
        errors_today = stats.get("errors_today", 0)
        if tasks_today > 0:
            error_rate = errors_today / (tasks_today + errors_today)
            if error_rate > self.ERROR_RATE_THRESHOLD:
                alerts.append(
                    Alert(
                        id=f"high_error_rate_{valet_name}",
                        severity=AlertSeverity.WARNING,
                        valet=valet_name,
                        message=f"Taux d'erreur élevé ({error_rate:.0%})",
                        details=f"{errors_today} erreurs sur {tasks_today + errors_today} tâches",
                    )
                )

        # Check Sganarelle learning staleness
        if valet_name == "sganarelle":
            details = stats.get("details", {})
            last_learning = details.get("last_learning")
            if last_learning:
                try:
                    if isinstance(last_learning, str):
                        last_dt = datetime.fromisoformat(last_learning.replace("Z", "+00:00"))
                    else:
                        last_dt = last_learning
                    hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                    if hours_since > self.LEARNING_STALE_HOURS:
                        alerts.append(
                            Alert(
                                id="learning_stale",
                                severity=AlertSeverity.INFO,
                                valet="sganarelle",
                                message=f"Pas de cycle d'apprentissage depuis {int(hours_since)}h",
                                details="Le système d'apprentissage n'a pas été exécuté récemment",
                            )
                        )
                except (ValueError, TypeError):
                    pass

        # Check Sancho confidence
        if valet_name == "sancho":
            details = stats.get("details", {})
            # This would need actual confidence tracking
            pass

        return alerts

    def _check_system(self, stats: dict[str, Any]) -> list[Alert]:
        """Check system-wide alert conditions."""
        alerts: list[Alert] = []

        # Check if multiple valets are in error
        error_valets = [
            name for name, s in stats.items()
            if s.get("status") == "error"
        ]
        if len(error_valets) >= 2:
            alerts.append(
                Alert(
                    id="multiple_valets_error",
                    severity=AlertSeverity.CRITICAL,
                    valet=None,
                    message=f"{len(error_valets)} valets en erreur",
                    details=f"Valets affectés : {', '.join(error_valets)}",
                )
            )

        # Check overall confidence (from Trivelin stats)
        trivelin_details = stats.get("trivelin", {}).get("details", {})
        confidence_avg = trivelin_details.get("confidence_avg", 0)
        if confidence_avg > 0 and confidence_avg < self.LOW_CONFIDENCE_THRESHOLD * 100:
            alerts.append(
                Alert(
                    id="low_confidence",
                    severity=AlertSeverity.WARNING,
                    valet=None,
                    message=f"Confiance moyenne basse ({confidence_avg:.0f}%)",
                    details="La qualité des analyses pourrait être dégradée",
                )
            )

        return alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].acknowledged = True
            return True
        return False

    def clear_alert(self, alert_id: str) -> bool:
        """Remove an alert from the active list."""
        if alert_id in self._active_alerts:
            del self._active_alerts[alert_id]
            return True
        return False


# Singleton instance
_alerts_service: AlertsService | None = None


def get_alerts_service() -> AlertsService:
    """
    Get the alerts service singleton.

    Returns:
        AlertsService instance
    """
    global _alerts_service
    if _alerts_service is None:
        _alerts_service = AlertsService()
    return _alerts_service
