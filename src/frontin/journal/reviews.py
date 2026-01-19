"""
Review Generator

Generates weekly and monthly reviews from daily journal entries.
Detects patterns, calculates productivity scores, and provides
suggestions for improvement.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from src.frontin.journal.models import JournalEntry
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("frontin.journal.reviews")


# ============================================================================
# ENUMS
# ============================================================================


class ReviewType(str, Enum):
    """Type of review period"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PatternType(str, Enum):
    """Types of detected patterns"""
    HIGH_VOLUME_SENDER = "high_volume_sender"
    RECURRING_CATEGORY = "recurring_category"
    TIME_OF_DAY = "time_of_day"
    LOW_CONFIDENCE_TREND = "low_confidence_trend"
    CORRECTION_PATTERN = "correction_pattern"
    PRODUCTIVITY_PATTERN = "productivity_pattern"


# ============================================================================
# PATTERN MODELS
# ============================================================================


@dataclass(frozen=True)
class DetectedPattern:
    """A detected pattern from journal analysis"""
    pattern_type: PatternType
    description: str
    confidence: float  # 0.0-1.0
    occurrences: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "metadata": self.metadata,
        }


# ============================================================================
# WEEKLY REVIEW
# ============================================================================


@dataclass
class WeeklyReview:
    """
    Weekly review aggregating daily journal entries

    Contains patterns detected, productivity metrics,
    and suggestions for improvement.
    """
    week_start: date
    week_end: date
    created_at: datetime = field(default_factory=now_utc)

    # Daily entries
    daily_entries: list[JournalEntry] = field(default_factory=list)

    # Patterns detected
    patterns_detected: list[DetectedPattern] = field(default_factory=list)

    # Metrics
    productivity_score: float = 0.0  # 0.0-100.0

    # Top categories by count
    top_categories: list[tuple[str, int]] = field(default_factory=list)

    # Source summaries
    total_emails: int = 0
    total_teams: int = 0
    total_calendar: int = 0
    total_omnifocus: int = 0

    # Corrections and feedback
    total_corrections: int = 0
    average_confidence: float = 0.0

    # Suggestions
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "created_at": self.created_at.isoformat(),
            "days_with_entries": len(self.daily_entries),
            "patterns_detected": [p.to_dict() for p in self.patterns_detected],
            "productivity_score": self.productivity_score,
            "top_categories": self.top_categories,
            "total_emails": self.total_emails,
            "total_teams": self.total_teams,
            "total_calendar": self.total_calendar,
            "total_omnifocus": self.total_omnifocus,
            "total_corrections": self.total_corrections,
            "average_confidence": self.average_confidence,
            "suggestions": self.suggestions,
        }

    def to_markdown(self) -> str:
        """Convert to Markdown format"""
        lines = [
            "---",
            f"week_start: {self.week_start.isoformat()}",
            f"week_end: {self.week_end.isoformat()}",
            f"productivity_score: {self.productivity_score:.1f}",
            "---",
            "",
            f"# Revue Hebdomadaire : {self.week_start.strftime('%d/%m')} - {self.week_end.strftime('%d/%m/%Y')}",
            "",
            "## Résumé",
            "",
            f"- **Jours avec entrées** : {len(self.daily_entries)}/7",
            f"- **Score productivité** : {self.productivity_score:.0f}/100",
            f"- **Confiance moyenne** : {self.average_confidence:.0f}%",
            "",
            "## Sources Traitées",
            "",
            "| Source | Nombre |",
            "|--------|--------|",
            f"| Emails | {self.total_emails} |",
            f"| Teams | {self.total_teams} |",
            f"| Calendrier | {self.total_calendar} |",
            f"| OmniFocus | {self.total_omnifocus} |",
            "",
        ]

        if self.top_categories:
            lines.extend([
                "## Top Catégories",
                "",
                "| Catégorie | Nombre |",
                "|-----------|--------|",
            ])
            for cat, count in self.top_categories[:5]:
                lines.append(f"| {cat} | {count} |")
            lines.append("")

        if self.patterns_detected:
            lines.extend([
                "## Patterns Détectés",
                "",
            ])
            for pattern in self.patterns_detected:
                emoji = {
                    PatternType.HIGH_VOLUME_SENDER: "📧",
                    PatternType.RECURRING_CATEGORY: "📂",
                    PatternType.LOW_CONFIDENCE_TREND: "⚠️",
                    PatternType.CORRECTION_PATTERN: "✏️",
                    PatternType.PRODUCTIVITY_PATTERN: "📈",
                }.get(pattern.pattern_type, "•")
                lines.append(f"- {emoji} {pattern.description} ({pattern.occurrences}x)")
            lines.append("")

        if self.suggestions:
            lines.extend([
                "## Suggestions",
                "",
            ])
            for suggestion in self.suggestions:
                lines.append(f"- 💡 {suggestion}")
            lines.append("")

        if self.total_corrections > 0:
            lines.extend([
                "## Feedback",
                "",
                f"- {self.total_corrections} corrections soumises cette semaine",
                "- Feedback envoyé à Sganarelle pour amélioration",
                "",
            ])

        lines.extend([
            "---",
            "*Revue générée par Scapin*",
        ])

        return "\n".join(lines)


# ============================================================================
# MONTHLY REVIEW
# ============================================================================


@dataclass
class MonthlyReview:
    """
    Monthly review aggregating weekly reviews

    Contains trends, goals progress, and calibration summary.
    """
    month: date  # First day of the month
    created_at: datetime = field(default_factory=now_utc)

    # Weekly reviews
    weekly_reviews: list[WeeklyReview] = field(default_factory=list)

    # Trends detected
    trends: list[str] = field(default_factory=list)

    # Goals progress (goal_name -> progress 0.0-1.0)
    goals_progress: dict[str, float] = field(default_factory=dict)

    # Calibration summary
    calibration_summary: dict[str, Any] = field(default_factory=dict)

    # Aggregate metrics
    total_days_tracked: int = 0
    average_productivity: float = 0.0
    total_items_processed: int = 0
    total_corrections: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "month": self.month.isoformat(),
            "created_at": self.created_at.isoformat(),
            "weeks_count": len(self.weekly_reviews),
            "trends": self.trends,
            "goals_progress": self.goals_progress,
            "calibration_summary": self.calibration_summary,
            "total_days_tracked": self.total_days_tracked,
            "average_productivity": self.average_productivity,
            "total_items_processed": self.total_items_processed,
            "total_corrections": self.total_corrections,
        }

    def to_markdown(self) -> str:
        """Convert to Markdown format"""
        month_name = self.month.strftime("%B %Y")
        lines = [
            "---",
            f"month: {self.month.isoformat()}",
            f"weeks_tracked: {len(self.weekly_reviews)}",
            f"average_productivity: {self.average_productivity:.1f}",
            "---",
            "",
            f"# Revue Mensuelle : {month_name}",
            "",
            "## Résumé du Mois",
            "",
            f"- **Jours suivis** : {self.total_days_tracked}",
            f"- **Productivité moyenne** : {self.average_productivity:.0f}/100",
            f"- **Total items traités** : {self.total_items_processed}",
            f"- **Corrections soumises** : {self.total_corrections}",
            "",
        ]

        if self.trends:
            lines.extend([
                "## Tendances",
                "",
            ])
            for trend in self.trends:
                lines.append(f"- 📊 {trend}")
            lines.append("")

        if self.goals_progress:
            lines.extend([
                "## Progression des Objectifs",
                "",
                "| Objectif | Progression |",
                "|----------|-------------|",
            ])
            for goal, progress in self.goals_progress.items():
                bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))
                lines.append(f"| {goal} | {bar} {progress*100:.0f}% |")
            lines.append("")

        if self.calibration_summary:
            lines.extend([
                "## Calibration Sganarelle",
                "",
            ])
            for key, value in self.calibration_summary.items():
                lines.append(f"- **{key}** : {value}")
            lines.append("")

        lines.extend([
            "---",
            "*Revue mensuelle générée par Scapin*",
        ])

        return "\n".join(lines)


# ============================================================================
# REVIEW GENERATOR
# ============================================================================


@dataclass
class ReviewGeneratorConfig:
    """Configuration for review generation"""
    # Pattern detection thresholds
    min_pattern_occurrences: int = 3
    pattern_confidence_threshold: float = 0.6

    # Productivity scoring weights
    weight_emails: float = 1.0
    weight_teams: float = 0.8
    weight_calendar: float = 0.5
    weight_omnifocus: float = 1.2

    # Suggestion generation
    max_suggestions: int = 5


class ReviewGenerator:
    """
    Generates weekly and monthly reviews

    Analyzes daily journal entries to detect patterns,
    calculate productivity metrics, and provide suggestions.

    Usage:
        generator = ReviewGenerator()
        weekly = generator.generate_weekly(week_start)
        monthly = generator.generate_monthly(month)
    """

    def __init__(self, config: Optional[ReviewGeneratorConfig] = None):
        """Initialize review generator"""
        self.config = config or ReviewGeneratorConfig()

    def generate_weekly(
        self,
        week_start: date,
        daily_entries: list[JournalEntry],
    ) -> WeeklyReview:
        """
        Generate weekly review from daily entries

        Args:
            week_start: Start date of the week (Monday)
            daily_entries: List of daily journal entries for the week

        Returns:
            WeeklyReview with patterns, metrics, and suggestions
        """
        logger.info(f"Generating weekly review for week starting {week_start}")

        week_end = week_start + timedelta(days=6)

        # Filter entries for the week
        week_entries = [
            e for e in daily_entries
            if week_start <= e.journal_date <= week_end
        ]

        # Calculate aggregate metrics
        total_emails = sum(len(e.emails_processed) for e in week_entries)
        total_teams = sum(len(e.teams_messages) for e in week_entries)
        total_calendar = sum(len(e.calendar_events) for e in week_entries)
        total_omnifocus = sum(len(e.omnifocus_items) for e in week_entries)
        total_corrections = sum(len(e.corrections) for e in week_entries)

        # Calculate average confidence
        all_confidences = [
            e.confidence for entry in week_entries
            for e in entry.emails_processed
        ]
        avg_confidence = (
            sum(all_confidences) / len(all_confidences)
            if all_confidences else 0.0
        )

        # Calculate productivity score
        productivity = self._calculate_productivity(
            total_emails, total_teams, total_calendar, total_omnifocus
        )

        # Detect patterns
        patterns = self._detect_patterns(week_entries)

        # Get top categories
        top_categories = self._get_top_categories(week_entries)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            patterns, avg_confidence, total_corrections
        )

        review = WeeklyReview(
            week_start=week_start,
            week_end=week_end,
            daily_entries=week_entries,
            patterns_detected=patterns,
            productivity_score=productivity,
            top_categories=top_categories,
            total_emails=total_emails,
            total_teams=total_teams,
            total_calendar=total_calendar,
            total_omnifocus=total_omnifocus,
            total_corrections=total_corrections,
            average_confidence=avg_confidence,
            suggestions=suggestions,
        )

        logger.info(
            f"Weekly review generated: {len(patterns)} patterns, "
            f"productivity={productivity:.1f}"
        )
        return review

    def generate_monthly(
        self,
        month: date,
        weekly_reviews: list[WeeklyReview],
    ) -> MonthlyReview:
        """
        Generate monthly review from weekly reviews

        Args:
            month: First day of the month
            weekly_reviews: List of weekly reviews for the month

        Returns:
            MonthlyReview with trends, goals progress, and calibration
        """
        logger.info(f"Generating monthly review for {month.strftime('%B %Y')}")

        # Filter reviews for the month
        month_end = (month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        month_reviews = [
            r for r in weekly_reviews
            if month <= r.week_start <= month_end
        ]

        # Calculate aggregate metrics
        total_days = sum(len(r.daily_entries) for r in month_reviews)
        avg_productivity = (
            sum(r.productivity_score for r in month_reviews) / len(month_reviews)
            if month_reviews else 0.0
        )
        total_items = sum(
            r.total_emails + r.total_teams + r.total_calendar + r.total_omnifocus
            for r in month_reviews
        )
        total_corrections = sum(r.total_corrections for r in month_reviews)

        # Detect trends across weeks
        trends = self._detect_trends(month_reviews)

        # Calculate goals progress (placeholder - would integrate with goal tracking)
        goals_progress = self._calculate_goals_progress(month_reviews)

        # Build calibration summary
        calibration_summary = self._build_calibration_summary(month_reviews)

        review = MonthlyReview(
            month=month,
            weekly_reviews=month_reviews,
            trends=trends,
            goals_progress=goals_progress,
            calibration_summary=calibration_summary,
            total_days_tracked=total_days,
            average_productivity=avg_productivity,
            total_items_processed=total_items,
            total_corrections=total_corrections,
        )

        logger.info(
            f"Monthly review generated: {len(trends)} trends, "
            f"avg_productivity={avg_productivity:.1f}"
        )
        return review

    def _calculate_productivity(
        self,
        emails: int,
        teams: int,
        calendar: int,
        omnifocus: int,
    ) -> float:
        """
        Calculate productivity score (0-100)

        Uses weighted sum normalized to 100.
        """
        weighted_sum = (
            emails * self.config.weight_emails +
            teams * self.config.weight_teams +
            calendar * self.config.weight_calendar +
            omnifocus * self.config.weight_omnifocus
        )

        # Normalize: assume ~50 items/week is average (score 50)
        # Scale so 100 items = 100 score
        normalized = min(100.0, weighted_sum * 2.0)
        return normalized

    def _detect_patterns(
        self,
        entries: list[JournalEntry],
    ) -> list[DetectedPattern]:
        """Detect patterns from journal entries"""
        patterns: list[DetectedPattern] = []

        if not entries:
            return patterns

        # Pattern 1: High volume senders
        sender_counts: dict[str, int] = {}
        for entry in entries:
            for email in entry.emails_processed:
                sender = email.from_address
                sender_counts[sender] = sender_counts.get(sender, 0) + 1

        for sender, count in sender_counts.items():
            if count >= self.config.min_pattern_occurrences:
                patterns.append(DetectedPattern(
                    pattern_type=PatternType.HIGH_VOLUME_SENDER,
                    description=f"Expéditeur fréquent: {sender}",
                    confidence=min(0.9, count / 10.0),
                    occurrences=count,
                    metadata={"sender": sender},
                ))

        # Pattern 2: Recurring categories
        category_counts: dict[str, int] = {}
        for entry in entries:
            for email in entry.emails_processed:
                cat = email.category
                category_counts[cat] = category_counts.get(cat, 0) + 1

        for cat, count in category_counts.items():
            if count >= self.config.min_pattern_occurrences:
                patterns.append(DetectedPattern(
                    pattern_type=PatternType.RECURRING_CATEGORY,
                    description=f"Catégorie fréquente: {cat}",
                    confidence=min(0.85, count / 15.0),
                    occurrences=count,
                    metadata={"category": cat},
                ))

        # Pattern 3: Low confidence trend
        low_conf_count = sum(
            1 for entry in entries
            for email in entry.emails_processed
            if email.confidence < 70
        )
        if low_conf_count >= self.config.min_pattern_occurrences:
            patterns.append(DetectedPattern(
                pattern_type=PatternType.LOW_CONFIDENCE_TREND,
                description="Nombreuses décisions à faible confiance",
                confidence=0.8,
                occurrences=low_conf_count,
            ))

        # Pattern 4: Correction patterns
        correction_count = sum(len(entry.corrections) for entry in entries)
        if correction_count >= 2:
            patterns.append(DetectedPattern(
                pattern_type=PatternType.CORRECTION_PATTERN,
                description=f"Corrections fréquentes ({correction_count} cette semaine)",
                confidence=0.75,
                occurrences=correction_count,
            ))

        return patterns

    def _get_top_categories(
        self,
        entries: list[JournalEntry],
    ) -> list[tuple[str, int]]:
        """Get top categories by count"""
        category_counts: dict[str, int] = {}
        for entry in entries:
            for email in entry.emails_processed:
                cat = email.category
                category_counts[cat] = category_counts.get(cat, 0) + 1

        sorted_cats = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_cats[:5]

    def _generate_suggestions(
        self,
        patterns: list[DetectedPattern],
        avg_confidence: float,
        total_corrections: int,
    ) -> list[str]:
        """Generate actionable suggestions"""
        suggestions: list[str] = []

        # Suggestion based on low confidence
        if avg_confidence < 75:
            suggestions.append(
                "La confiance moyenne est basse. "
                "Considérez ajouter des exemples pour les nouveaux expéditeurs."
            )

        # Suggestion based on corrections
        if total_corrections > 3:
            suggestions.append(
                "Plusieurs corrections cette semaine. "
                "Scapin apprend de vos retours pour s'améliorer."
            )

        # Suggestion based on patterns
        for pattern in patterns:
            if pattern.pattern_type == PatternType.HIGH_VOLUME_SENDER:
                sender = pattern.metadata.get("sender", "inconnu")
                suggestions.append(
                    f"Créer une règle automatique pour {sender}?"
                )
            elif pattern.pattern_type == PatternType.LOW_CONFIDENCE_TREND:
                suggestions.append(
                    "Revoyez les décisions à faible confiance "
                    "pour améliorer la calibration."
                )

        return suggestions[:self.config.max_suggestions]

    def _detect_trends(
        self,
        weekly_reviews: list[WeeklyReview],
    ) -> list[str]:
        """Detect trends across weekly reviews"""
        trends: list[str] = []

        if len(weekly_reviews) < 2:
            return trends

        # Trend 1: Productivity trend
        productivities = [r.productivity_score for r in weekly_reviews]
        if productivities[-1] > productivities[0] * 1.2:
            trends.append("📈 Productivité en hausse ce mois-ci")
        elif productivities[-1] < productivities[0] * 0.8:
            trends.append("📉 Productivité en baisse - prenez du recul")

        # Trend 2: Confidence trend
        confidences = [r.average_confidence for r in weekly_reviews]
        if confidences[-1] > confidences[0] + 10:
            trends.append("✅ Amélioration de la confiance des décisions")

        # Trend 3: Volume trend
        volumes = [
            r.total_emails + r.total_teams + r.total_calendar + r.total_omnifocus
            for r in weekly_reviews
        ]
        avg_volume = sum(volumes) / len(volumes)
        if max(volumes) > avg_volume * 1.5:
            trends.append("⚡ Semaine(s) avec volume élevé détectée(s)")

        return trends

    def _calculate_goals_progress(
        self,
        weekly_reviews: list[WeeklyReview],  # noqa: ARG002
    ) -> dict[str, float]:
        """
        Calculate goals progress

        Note: This is a placeholder. Real implementation would
        integrate with a goal tracking system.
        """
        # Placeholder goals
        return {
            "Inbox Zero": 0.75,
            "Réponse < 24h": 0.60,
            "Tâches complétées": 0.85,
        }

    def _build_calibration_summary(
        self,
        weekly_reviews: list[WeeklyReview],
    ) -> dict[str, Any]:
        """Build calibration summary for Sganarelle"""
        total_corrections = sum(r.total_corrections for r in weekly_reviews)
        avg_confidence = (
            sum(r.average_confidence for r in weekly_reviews) / len(weekly_reviews)
            if weekly_reviews else 0.0
        )

        return {
            "corrections_ce_mois": total_corrections,
            "confiance_moyenne": f"{avg_confidence:.0f}%",
            "sources_actives": 4,  # Email, Teams, Calendar, OmniFocus
            "amélioration_suggérée": total_corrections > 5,
        }
