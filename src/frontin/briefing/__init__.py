"""
Briefing Module

Intelligent briefing generation from multiple sources.

Provides:
- Morning briefings: Daily overview of calendar, emails, and Teams
- Pre-meeting briefings: Context for upcoming meetings

Usage:
    from src.frontin.briefing import BriefingGenerator, BriefingDisplay

    generator = BriefingGenerator(config=briefing_config)
    display = BriefingDisplay(console)

    # Morning briefing
    briefing = await generator.generate_morning_briefing()
    display.render_morning_briefing(briefing)

    # Pre-meeting briefing
    pre_meeting = await generator.generate_pre_meeting_briefing(event)
    display.render_pre_meeting_briefing(pre_meeting)
"""

from src.frontin.briefing.display import BriefingDisplay
from src.frontin.briefing.generator import (
    BriefingDataProvider,
    BriefingGenerator,
    DefaultBriefingDataProvider,
)
from src.frontin.briefing.models import (
    AttendeeContext,
    BriefingItem,
    MorningBriefing,
    PreMeetingBriefing,
)

__all__ = [
    # Generator
    "BriefingGenerator",
    "BriefingDataProvider",
    "DefaultBriefingDataProvider",
    # Models
    "MorningBriefing",
    "PreMeetingBriefing",
    "BriefingItem",
    "AttendeeContext",
    # Display
    "BriefingDisplay",
]
