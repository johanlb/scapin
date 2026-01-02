"""
Jeeves - Interface Module

The communication and presentation valet of Scapin's architecture.

Named after Jeeves, P.G. Wodehouse's impeccably competent valet
who handles all matters of presentation and communication.

Jeeves provides:
- CLI interface (Typer-based commands)
- Interactive menus (questionary)
- Display rendering (Rich)
- Future: REST API (FastAPI) and WebSocket support
"""

from src.jeeves.cli import app, run
from src.jeeves.display_manager import DisplayManager, create_display_manager
from src.jeeves.menu import InteractiveMenu, run_interactive_menu
from src.jeeves.review_mode import InteractiveReviewMode

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
