"""
Frontin - Interface Module

The communication and presentation valet of Scapin's architecture.

Named after Frontin, the clever valet from Molière's "Les Fourberies de Scapin"
who handles all matters of presentation and communication.

Frontin provides:
- CLI interface (Typer-based commands)
- Interactive menus (questionary)
- Display rendering (Rich)
- Future: REST API (FastAPI) and WebSocket support
"""

from src.frontin.cli import app, run
from src.frontin.display_manager import DisplayManager, create_display_manager
from src.frontin.menu import InteractiveMenu, run_interactive_menu
from src.frontin.review_mode import InteractiveReviewMode

__all__ = [
    # CLI
    "app",
    "run",
    # Display
    "DisplayManager",
    "create_display_manager",
    # Menu
    "InteractiveMenu",
    "run_interactive_menu",
    # Review
    "InteractiveReviewMode",
]
