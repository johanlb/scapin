#!/usr/bin/env python3
"""
Script pour consulter les erreurs accumulées dans Scapin.

Usage:
    python scripts/view_errors.py                    # Affiche les 20 dernières erreurs
    python scripts/view_errors.py --limit 50        # Affiche les 50 dernières
    python scripts/view_errors.py --unresolved      # Erreurs non résolues uniquement
    python scripts/view_errors.py --stats           # Statistiques globales
    python scripts/view_errors.py --category API    # Filtrer par catégorie
    python scripts/view_errors.py --severity HIGH   # Filtrer par sévérité
    python scripts/view_errors.py --detail ERROR_ID # Détail d'une erreur spécifique
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.error_store import get_error_store


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    now = datetime.now()
    delta = now - dt.replace(tzinfo=None)

    if delta.days == 0:
        if delta.seconds < 60:
            return "il y a quelques secondes"
        elif delta.seconds < 3600:
            minutes = delta.seconds // 60
            return f"il y a {minutes} min"
        else:
            hours = delta.seconds // 3600
            return f"il y a {hours}h"
    elif delta.days == 1:
        return "hier"
    elif delta.days < 7:
        return f"il y a {delta.days} jours"
    else:
        return dt.strftime("%Y-%m-%d %H:%M")


def severity_color(severity: str) -> str:
    """Get ANSI color code for severity."""
    colors = {
        "CRITICAL": "\033[91m",  # Red
        "HIGH": "\033[93m",      # Yellow
        "MEDIUM": "\033[94m",    # Blue
        "LOW": "\033[90m",       # Gray
    }
    return colors.get(severity, "")


def reset_color() -> str:
    """Reset ANSI color."""
    return "\033[0m"


def print_error_summary(error, show_traceback: bool = False) -> None:
    """Print a single error summary."""
    color = severity_color(error.severity.value)
    reset = reset_color()

    resolved_marker = "✓" if error.resolved else "✗"
    recovery_marker = ""
    if error.recovery_attempted:
        if error.recovery_successful:
            recovery_marker = " [recovered]"
        else:
            recovery_marker = f" [recovery failed: {error.recovery_attempts}/{error.max_recovery_attempts}]"

    print(f"\n{color}[{error.severity.value}]{reset} {error.exception_type}")
    print(f"  ID: {error.id[:8]}... | {format_timestamp(error.timestamp)} | {resolved_marker} {error.category.value}{recovery_marker}")
    print(f"  Component: {error.component} → {error.operation}")
    print(f"  Message: {error.exception_message[:100]}{'...' if len(error.exception_message) > 100 else ''}")

    if show_traceback and error.traceback:
        print(f"\n  Traceback:")
        for line in error.traceback.split('\n')[-10:]:  # Last 10 lines
            print(f"    {line}")


def print_error_detail(error) -> None:
    """Print full error details."""
    color = severity_color(error.severity.value)
    reset = reset_color()

    print(f"\n{'='*60}")
    print(f"{color}[{error.severity.value}] {error.exception_type}{reset}")
    print(f"{'='*60}")

    print(f"\n📋 Metadata:")
    print(f"  ID:        {error.id}")
    print(f"  Timestamp: {error.timestamp.isoformat()}")
    print(f"  Category:  {error.category.value}")
    print(f"  Severity:  {error.severity.value}")
    print(f"  Component: {error.component}")
    print(f"  Operation: {error.operation}")

    print(f"\n💬 Message:")
    print(f"  {error.exception_message}")

    print(f"\n🔄 Recovery:")
    print(f"  Strategy:  {error.recovery_strategy.value}")
    print(f"  Attempted: {'Yes' if error.recovery_attempted else 'No'}")
    if error.recovery_attempted:
        print(f"  Successful: {'Yes' if error.recovery_successful else 'No'}")
        print(f"  Attempts:   {error.recovery_attempts}/{error.max_recovery_attempts}")

    print(f"\n✅ Resolution:")
    print(f"  Resolved: {'Yes' if error.resolved else 'No'}")
    if error.resolved_at:
        print(f"  Resolved at: {error.resolved_at.isoformat()}")
    if error.notes:
        print(f"  Notes: {error.notes}")

    if error.context:
        print(f"\n📦 Context:")
        for key, value in error.context.items():
            print(f"  {key}: {value}")

    if error.traceback:
        print(f"\n🔍 Traceback:")
        print("-" * 60)
        print(error.traceback)
        print("-" * 60)


def print_stats(stats: dict) -> None:
    """Print error statistics."""
    print("\n" + "=" * 50)
    print("📊 STATISTIQUES DES ERREURS")
    print("=" * 50)

    print(f"\n📈 Vue d'ensemble:")
    print(f"  Total erreurs:     {stats.get('total_errors', 0)}")
    print(f"  Résolues:          {stats.get('resolved', 0)}")
    print(f"  Non résolues:      {stats.get('unresolved', 0)}")

    print(f"\n🔄 Recovery:")
    print(f"  Tentées:           {stats.get('recovery_attempted', 0)}")
    print(f"  Réussies:          {stats.get('recovery_successful', 0)}")

    if stats.get('by_category'):
        print(f"\n📂 Par catégorie:")
        for cat, count in stats['by_category'].items():
            print(f"  {cat}: {count}")

    if stats.get('by_severity'):
        print(f"\n⚠️  Par sévérité:")
        for sev, count in stats['by_severity'].items():
            color = severity_color(sev)
            reset = reset_color()
            print(f"  {color}{sev}{reset}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description="Consulter les erreurs accumulées dans Scapin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s                          # 20 dernières erreurs
  %(prog)s --limit 50               # 50 dernières erreurs
  %(prog)s --unresolved             # Erreurs non résolues
  %(prog)s --stats                  # Statistiques globales
  %(prog)s --category API           # Filtrer par catégorie
  %(prog)s --detail abc123          # Détail d'une erreur
        """
    )

    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=20,
        help="Nombre d'erreurs à afficher (défaut: 20)"
    )
    parser.add_argument(
        "--unresolved", "-u",
        action="store_true",
        help="Afficher uniquement les erreurs non résolues"
    )
    parser.add_argument(
        "--resolved", "-r",
        action="store_true",
        help="Afficher uniquement les erreurs résolues"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Afficher les statistiques globales"
    )
    parser.add_argument(
        "--category", "-c",
        type=str,
        help="Filtrer par catégorie (API, DATABASE, AI, EMAIL, etc.)"
    )
    parser.add_argument(
        "--severity",
        type=str,
        help="Filtrer par sévérité (CRITICAL, HIGH, MEDIUM, LOW)"
    )
    parser.add_argument(
        "--detail", "-d",
        type=str,
        help="Afficher le détail d'une erreur par son ID"
    )
    parser.add_argument(
        "--traceback", "-t",
        action="store_true",
        help="Inclure les tracebacks dans le résumé"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Chemin vers la base de données errors.db"
    )

    args = parser.parse_args()

    # Initialize error store
    try:
        if args.db_path:
            from src.core.error_store import ErrorStore
            store = ErrorStore(Path(args.db_path))
        else:
            store = get_error_store()
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        print("\nAssurez-vous que le chemin vers errors.db est correct.")
        print("Utilisez --db-path pour spécifier un chemin personnalisé.")
        sys.exit(1)

    # Show stats
    if args.stats:
        stats = store.get_error_stats()
        if stats.get('total_errors', 0) == 0:
            print("\n✨ Aucune erreur enregistrée dans la base de données.")
        else:
            print_stats(stats)
        return

    # Show single error detail
    if args.detail:
        error = store.get_error(args.detail)
        if error:
            print_error_detail(error)
        else:
            # Try partial match
            errors = store.get_recent_errors(limit=1000)
            matches = [e for e in errors if e.id.startswith(args.detail)]
            if matches:
                print_error_detail(matches[0])
            else:
                print(f"❌ Erreur non trouvée: {args.detail}")
        return

    # Prepare filters
    from src.core.error_manager import ErrorCategory, ErrorSeverity

    category = None
    if args.category:
        try:
            category = ErrorCategory(args.category.upper())
        except ValueError:
            print(f"❌ Catégorie invalide: {args.category}")
            print(f"   Catégories valides: {[c.value for c in ErrorCategory]}")
            sys.exit(1)

    severity = None
    if args.severity:
        try:
            severity = ErrorSeverity(args.severity.upper())
        except ValueError:
            print(f"❌ Sévérité invalide: {args.severity}")
            print(f"   Sévérités valides: {[s.value for s in ErrorSeverity]}")
            sys.exit(1)

    resolved = None
    if args.unresolved:
        resolved = False
    elif args.resolved:
        resolved = True

    # Get errors
    errors = store.get_recent_errors(
        limit=args.limit,
        category=category,
        severity=severity,
        resolved=resolved,
    )

    if not errors:
        print("\n✨ Aucune erreur trouvée avec ces critères.")
        return

    # Display header
    filter_desc = []
    if category:
        filter_desc.append(f"catégorie={category.value}")
    if severity:
        filter_desc.append(f"sévérité={severity.value}")
    if resolved is not None:
        filter_desc.append("résolues" if resolved else "non résolues")

    filter_str = f" ({', '.join(filter_desc)})" if filter_desc else ""
    print(f"\n📋 {len(errors)} dernières erreurs{filter_str}:")
    print("-" * 60)

    # Display errors
    for error in errors:
        print_error_summary(error, show_traceback=args.traceback)

    print("\n" + "-" * 60)
    print(f"💡 Utilisez --detail <ID> pour voir le détail d'une erreur")
    print(f"💡 Utilisez --stats pour voir les statistiques globales")


if __name__ == "__main__":
    main()
