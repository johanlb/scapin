"""
Configuration for CrossSourceEngine.

Defines configuration dataclasses for the cross-source search system
and individual source adapters.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EmailAdapterConfig:
    """Configuration for the email (IMAP) adapter."""

    enabled: bool = True
    search_body: bool = True  # Search in email body
    date_range_days: int | None = None  # None = unlimited
    max_results: int = 20


@dataclass
class CalendarAdapterConfig:
    """Configuration for the Microsoft calendar adapter."""

    enabled: bool = True
    past_days: int = 365  # 1 year back
    future_days: int = 90  # 3 months ahead
    include_description: bool = True
    max_results: int = 20


@dataclass
class ICloudCalendarAdapterConfig:
    """Configuration for the iCloud calendar adapter (CalDAV)."""

    enabled: bool = True
    past_days: int = 365  # 1 year back
    future_days: int = 90  # 3 months ahead
    include_description: bool = True
    max_results: int = 20
    # CalDAV credentials (set via environment)
    username: str = ""  # Apple ID email
    app_specific_password: str = ""  # From appleid.apple.com
    server_url: str = "https://caldav.icloud.com"


@dataclass
class TeamsAdapterConfig:
    """Configuration for the Teams adapter."""

    enabled: bool = True
    include_all_chats: bool = True
    include_files: bool = True
    max_results: int = 20


@dataclass
class WhatsAppAdapterConfig:
    """Configuration for the WhatsApp adapter."""

    enabled: bool = True
    db_path: Path = field(
        default_factory=lambda: Path.home()
        / "Library/Containers/net.whatsapp.WhatsApp/Data"
        / "Library/Application Support/WhatsApp/ChatStorage.sqlite"
    )
    max_results: int = 20


@dataclass
class FilesAdapterConfig:
    """Configuration for the local files adapter."""

    enabled: bool = True
    default_paths: list[Path] = field(
        default_factory=lambda: [Path.home() / "Documents"]
    )
    extensions_tier1: list[str] = field(
        default_factory=lambda: [".md", ".txt", ".json", ".yaml", ".yml"]
    )
    extensions_tier2: list[str] = field(
        default_factory=lambda: [".pdf", ".docx", ".xlsx", ".pptx"]
    )
    max_file_size_mb: int = 10
    max_results: int = 20

    # Security exclusions
    excluded_paths: list[str] = field(
        default_factory=lambda: [
            ".ssh",
            ".gnupg",
            ".aws",
            ".config/gcloud",
            "credentials",
            "secrets",
            ".env",
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
        ]
    )
    excluded_patterns: list[str] = field(
        default_factory=lambda: [
            "*password*",
            "*secret*",
            "*credential*",
            "*.key",
            "*.pem",
            "*.p12",
            "id_rsa*",
            "id_ed25519*",
        ]
    )


@dataclass
class WebAdapterConfig:
    """Configuration for the web search adapter (Tavily)."""

    enabled: bool = True
    provider: str = "tavily"
    api_key: str = ""  # Via env: TAVILY_API_KEY
    trigger: str = "on_request"  # "on_request" | "no_local" | "always"
    max_results: int = 10


@dataclass
class CrossSourceConfig:
    """
    Main configuration for CrossSourceEngine.

    Controls global settings like caching, timeouts, and scoring,
    as well as per-adapter configurations.
    """

    # Feature toggle
    enabled: bool = True

    # Cache settings
    cache_ttl_seconds: int = 900  # 15 minutes
    cache_max_size: int = 100

    # Search limits
    max_results_per_source: int = 20
    max_total_results: int = 50
    adapter_timeout_seconds: float = 10.0

    # Auto-trigger threshold
    auto_trigger_confidence_threshold: float = 0.75  # If confidence < 75%

    # Source weights for scoring
    source_weights: dict[str, float] = field(
        default_factory=lambda: {
            "email": 1.0,
            "calendar": 1.0,
            "icloud_calendar": 1.0,
            "teams": 0.9,
            "whatsapp": 0.9,
            "files": 0.8,
            "web": 0.6,
            "notes": 1.0,
        }
    )

    # Freshness decay (items older than this get penalized)
    freshness_decay_days: int = 30

    # Per-adapter configs
    email: EmailAdapterConfig = field(default_factory=EmailAdapterConfig)
    calendar: CalendarAdapterConfig = field(default_factory=CalendarAdapterConfig)
    icloud_calendar: ICloudCalendarAdapterConfig = field(
        default_factory=ICloudCalendarAdapterConfig
    )
    teams: TeamsAdapterConfig = field(default_factory=TeamsAdapterConfig)
    whatsapp: WhatsAppAdapterConfig = field(default_factory=WhatsAppAdapterConfig)
    files: FilesAdapterConfig = field(default_factory=FilesAdapterConfig)
    web: WebAdapterConfig = field(default_factory=WebAdapterConfig)

    def get_enabled_sources(self) -> list[str]:
        """
        Get list of enabled source names.

        Returns:
            List of source names that are enabled
        """
        sources = []
        if self.email.enabled:
            sources.append("email")
        if self.calendar.enabled:
            sources.append("calendar")
        if self.icloud_calendar.enabled:
            sources.append("icloud_calendar")
        if self.teams.enabled:
            sources.append("teams")
        if self.whatsapp.enabled:
            sources.append("whatsapp")
        if self.files.enabled:
            sources.append("files")
        if self.web.enabled:
            sources.append("web")
        return sources

    def get_source_weight(self, source: str) -> float:
        """
        Get the weight for a source.

        Args:
            source: Source name

        Returns:
            Weight value (0.0 - 1.0)
        """
        return self.source_weights.get(source, 0.5)
