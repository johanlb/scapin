"""
Scapin Configuration Manager

Charge configuration hiérarchique depuis:
1. Defaults (config/defaults.yaml)
2. Environment variables (.env)
3. Overrides optionnels

Utilise Pydantic pour validation type-safe.
"""

import threading
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailAccountConfig(BaseModel):
    """
    Configuration for a single email account

    Supports multiple IMAP accounts with different settings.
    """

    # Account identity
    account_id: str = Field(..., description="Unique account identifier (e.g., 'personal', 'work')")
    account_name: str = Field(..., description="Human-readable name (e.g., 'Personal (iCloud)')")
    enabled: bool = Field(True, description="Whether this account is active")

    # IMAP connection
    imap_host: str = Field(..., description="IMAP server hostname")
    imap_port: int = Field(993, description="IMAP port")
    imap_username: EmailStr = Field(..., description="IMAP username")
    imap_password: str = Field(..., description="IMAP password")

    # Connection timeouts
    imap_timeout: int = Field(30, ge=5, le=300, description="IMAP connection timeout (seconds)")
    imap_read_timeout: int = Field(60, ge=10, le=600, description="IMAP read timeout (seconds)")

    # Folders (can be different per account)
    inbox_folder: str = Field("INBOX", description="Inbox folder name")
    archive_folder: str = Field("Archive", description="Archive folder name")
    reference_folder: str = Field("Référence", description="Reference folder name")
    delete_folder: str = Field("_Scapin/À supprimer", description="Delete folder name")

    # Processing (can be different per account)
    max_workers: int = Field(10, ge=1, le=50, description="Max worker threads")
    batch_size: int = Field(100, ge=1, le=1000, description="Batch size")

    @field_validator("imap_password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        """Validate IMAP password is configured and non-trivial"""
        # Trim whitespace
        v = v.strip()

        # Check for placeholder values
        placeholders = [
            "your_app_specific_password_here",
            "YOUR_PASSWORD",
            "password",
            "changeme",
            "",
        ]
        if v.lower() in [p.lower() for p in placeholders]:
            raise ValueError("IMAP password must be configured with a real password")

        # Check minimum length (app-specific passwords are typically 16+ chars)
        if len(v) < 8:
            raise ValueError("IMAP password too short (minimum 8 characters)")

        return v

    @field_validator("imap_username")
    @classmethod
    def username_valid(cls, v: EmailStr) -> EmailStr:
        """Validate IMAP username is a valid email address"""
        # EmailStr already validates email format, just add extra checks
        v_str = str(v).strip()

        if not v_str or "@" not in v_str:
            raise ValueError("IMAP username must be a valid email address")

        return v

    @field_validator("account_id")
    @classmethod
    def account_id_valid(cls, v: str) -> str:
        """Validate account ID is alphanumeric + underscore/dash"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("account_id must be alphanumeric (can include _ and -)")
        return v

    @field_validator("imap_port")
    @classmethod
    def port_valid(cls, v: int) -> int:
        """Validate IMAP port is in valid range"""
        if not (1 <= v <= 65535):
            raise ValueError(f"Invalid IMAP port {v} (must be 1-65535)")
        # Warn if not using standard ports
        if v not in [143, 993]:
            import warnings

            warnings.warn(
                f"Non-standard IMAP port {v} (standard: 143 or 993)", UserWarning, stacklevel=2
            )
        return v


class EmailConfig(BaseModel):
    """
    Multi-account email configuration

    Supports multiple IMAP accounts with fallback to single-account format
    for backward compatibility.
    """

    # Multi-account configuration
    accounts: list[EmailAccountConfig] = Field(
        default_factory=list, description="List of email accounts"
    )
    default_account_id: Optional[str] = Field(None, description="Default account ID to use")

    # Legacy single-account fields (for backward compatibility)
    # These will be auto-migrated to accounts[0] if accounts is empty
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[EmailStr] = None
    imap_password: Optional[str] = None
    imap_timeout: Optional[int] = None
    imap_read_timeout: Optional[int] = None
    inbox_folder: Optional[str] = None
    archive_folder: Optional[str] = None
    reference_folder: Optional[str] = None
    delete_folder: Optional[str] = None
    max_workers: Optional[int] = None
    batch_size: Optional[int] = None

    @model_validator(mode="after")
    def migrate_legacy_format(self):
        """
        Migrate legacy single-account format to multi-account

        If accounts list is empty but legacy fields are present,
        create a default account from legacy fields.
        """
        # If accounts already configured, validate and return
        if self.accounts:
            # Validate at least one account
            if len(self.accounts) == 0:
                raise ValueError("At least one email account must be configured")

            # Validate unique account IDs
            account_ids = [acc.account_id for acc in self.accounts]
            if len(account_ids) != len(set(account_ids)):
                duplicates = [id for id in account_ids if account_ids.count(id) > 1]
                raise ValueError(
                    f"Account IDs must be unique. Duplicates found: {list(set(duplicates))}"
                )

            # Validate unique IMAP usernames (can't have same account twice)
            usernames = [acc.imap_username for acc in self.accounts]
            if len(usernames) != len(set(usernames)):
                duplicates = [u for u in usernames if usernames.count(u) > 1]
                raise ValueError(
                    f"Duplicate IMAP usernames not allowed. Duplicates: {list(set(duplicates))}"
                )

            # Validate at least one enabled account
            enabled_count = sum(1 for acc in self.accounts if acc.enabled)
            if enabled_count == 0:
                raise ValueError("At least one account must be enabled")

            # Validate default_account_id if set
            if self.default_account_id:
                if self.default_account_id not in account_ids:
                    raise ValueError(
                        f"default_account_id '{self.default_account_id}' not found in accounts"
                    )
            else:
                # Set first enabled account as default
                for acc in self.accounts:
                    if acc.enabled:
                        self.default_account_id = acc.account_id
                        break

            return self

        # Legacy format migration
        if self.imap_host and self.imap_username and self.imap_password:
            # Create default account from legacy fields
            legacy_account = EmailAccountConfig(
                account_id="default",
                account_name="Default Account",
                enabled=True,
                imap_host=self.imap_host,
                imap_port=self.imap_port or 993,
                imap_username=self.imap_username,
                imap_password=self.imap_password,
                imap_timeout=self.imap_timeout or 30,
                imap_read_timeout=self.imap_read_timeout or 60,
                inbox_folder=self.inbox_folder or "INBOX",
                archive_folder=self.archive_folder or "Archive",
                reference_folder=self.reference_folder or "Référence",
                delete_folder=self.delete_folder or "_Scapin/À supprimer",
                max_workers=self.max_workers or 10,
                batch_size=self.batch_size or 100,
            )

            self.accounts = [legacy_account]
            self.default_account_id = "default"

            return self

        # No configuration provided
        raise ValueError(
            "No email account configured. Please configure EMAIL__ACCOUNTS__0__* "
            "or legacy EMAIL__IMAP_HOST format in .env"
        )

    def get_account(self, account_id: str) -> Optional[EmailAccountConfig]:
        """
        Get account by ID

        Args:
            account_id: Account identifier

        Returns:
            EmailAccountConfig or None if not found
        """
        for account in self.accounts:
            if account.account_id == account_id:
                return account
        return None

    def get_enabled_accounts(self) -> list[EmailAccountConfig]:
        """
        Get all enabled accounts

        Returns:
            List of enabled EmailAccountConfig objects
        """
        return [acc for acc in self.accounts if acc.enabled]

    def get_default_account(self) -> EmailAccountConfig:
        """
        Get the default account

        Returns:
            Default EmailAccountConfig

        Raises:
            ValueError: If default account not found
        """
        if not self.default_account_id:
            if self.accounts:
                return self.accounts[0]
            raise ValueError("No accounts configured")

        account = self.get_account(self.default_account_id)
        if not account:
            raise ValueError(f"Default account '{self.default_account_id}' not found")

        return account


class AIConfig(BaseModel):
    """Configuration AI providers"""

    anthropic_api_key: str = Field(..., description="Anthropic API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (optional)")
    mistral_api_key: Optional[str] = Field(None, description="Mistral API key (optional)")

    confidence_threshold: int = Field(
        90, ge=0, le=100, description="Confidence threshold for auto-processing"
    )
    rate_limit_per_minute: int = Field(40, ge=1, le=100, description="API rate limit")

    @field_validator("anthropic_api_key")
    @classmethod
    def anthropic_key_not_placeholder(cls, v: str) -> str:
        if v == "your_anthropic_api_key_here":
            raise ValueError("ANTHROPIC_API_KEY must be configured in .env with your real API key")
        return v


class StorageConfig(BaseModel):
    """Configuration storage (DB, Git, filesystem)"""

    database_path: Path = Field(Path("data/pkm.db"), description="SQLite database path")
    notes_path: Path = Field(
        Path.home() / "Documents/Scapin/Notes",
        description="Notes directory",
        alias="notes_dir",  # Support for older code expecting notes_dir
    )
    github_repo_url: Optional[str] = Field(None, description="GitHub remote repository URL")
    backup_enabled: bool = Field(True, description="Enable automatic backups")
    backup_retention_days: int = Field(30, ge=1, le=365, description="Backup retention")

    @property
    def notes_dir(self) -> Path:
        """Alias for backward compatibility"""
        return self.notes_path


class IntegrationsConfig(BaseModel):
    """Configuration intégrations externes"""

    omnifocus_enabled: bool = Field(True, description="Enable OmniFocus integration")
    apple_notes_sync_enabled: bool = Field(False, description="Enable Apple Notes sync (Phase 6)")
    sync_interval_minutes: int = Field(30, ge=1, le=1440, description="Sync interval in minutes")
    calendar_enabled: bool = Field(False, description="Enable Calendar integration")


class MonitoringConfig(BaseModel):
    """Configuration monitoring & observability"""

    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field("json", description="Log format (json or text)")
    health_check_enabled: bool = Field(True, description="Enable health checks")
    metrics_port: int = Field(8000, ge=1024, le=65535, description="Metrics server port")
    error_reporting_enabled: bool = Field(True, description="Enable error reporting")


class ProcessingConfig(BaseModel):
    """
    Configuration for cognitive processing pipeline

    Controls the multi-pass reasoning system introduced in Phase 1.0.
    When enabled, emails go through Trivelin → Sancho → Planchet → Figaro → Sganarelle.
    When disabled (default), emails use the legacy single-pass AI analysis.
    """

    enable_cognitive_reasoning: bool = Field(
        False, description="Enable multi-pass cognitive reasoning (opt-in, default OFF for safety)"
    )
    cognitive_confidence_threshold: float = Field(
        0.85,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for auto-execution (below = review queue)",
    )
    cognitive_timeout_seconds: int = Field(
        20, ge=5, le=120, description="Maximum time for cognitive processing per email"
    )
    cognitive_max_passes: int = Field(
        5, ge=1, le=10, description="Maximum reasoning passes before forcing decision"
    )
    fallback_on_failure: bool = Field(
        True, description="Fall back to legacy single-pass if cognitive pipeline fails"
    )

    # Context enrichment (Pass 2) - Uses Passepartout knowledge base
    enable_context_enrichment: bool = Field(
        True,
        description="Enable Pass 2 context enrichment from knowledge base (requires NoteManager)",
    )
    context_top_k: int = Field(
        5, ge=1, le=20, description="Number of context items to retrieve from knowledge base"
    )
    context_min_relevance: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum relevance score for context items (0-1)"
    )

    # Background processing (SC-14)
    auto_execute_threshold: float = Field(
        0.85,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for auto-execution without user review",
    )
    batch_size: int = Field(20, ge=1, le=100, description="Number of emails to process per batch")
    max_queue_size: int = Field(
        30, ge=1, le=200, description="Maximum items in review queue before pausing fetch"
    )
    polling_interval_seconds: int = Field(
        300, ge=60, le=3600, description="Interval between email polling (5 minutes default)"
    )


class MicrosoftAccountConfig(BaseModel):
    """
    Configuration for Microsoft account authentication

    Used for Microsoft Graph API access (Teams, Calendar, etc.).
    Requires an Azure AD app registration with appropriate permissions.
    """

    client_id: str = Field(..., description="Azure AD application client ID")
    tenant_id: str = Field(..., description="Azure AD tenant ID")
    client_secret: Optional[str] = Field(
        None, description="Client secret for confidential apps (optional for public apps)"
    )
    redirect_uri: str = Field("http://localhost:8080", description="OAuth redirect URI")
    scopes: tuple[str, ...] = Field(
        (
            "User.Read",
            "Chat.Read",
            "Chat.ReadWrite",
            "ChannelMessage.Read.All",
            "ChannelMessage.Send",
            "Calendars.Read",
            "Calendars.ReadWrite",
        ),
        description="Microsoft Graph API scopes",
    )

    @field_validator("client_id")
    @classmethod
    def client_id_not_placeholder(cls, v: str) -> str:
        """Validate client ID is configured"""
        if not v or v in ("your-client-id", "YOUR_CLIENT_ID", ""):
            raise ValueError(
                "Microsoft client_id must be configured with a real Azure AD app client ID"
            )
        return v

    @field_validator("tenant_id")
    @classmethod
    def tenant_id_not_placeholder(cls, v: str) -> str:
        """Validate tenant ID is configured"""
        if not v or v in ("your-tenant-id", "YOUR_TENANT_ID", "common", ""):
            raise ValueError("Microsoft tenant_id must be configured with your Azure AD tenant ID")
        return v


class TeamsConfig(BaseModel):
    """
    Configuration for Microsoft Teams integration

    Controls Teams message processing via Microsoft Graph API.
    Requires MicrosoftAccountConfig with appropriate Teams permissions.
    """

    enabled: bool = Field(False, description="Enable Teams integration (opt-in, default OFF)")
    account: Optional[MicrosoftAccountConfig] = Field(
        None, description="Microsoft account configuration"
    )
    poll_interval_seconds: int = Field(
        60, ge=10, le=3600, description="Polling interval for new messages (seconds)"
    )
    max_messages_per_poll: int = Field(
        50, ge=1, le=500, description="Maximum messages to fetch per poll"
    )
    process_channels: bool = Field(True, description="Process messages from Teams channels")
    process_chats: bool = Field(True, description="Process messages from 1:1 and group chats")

    @model_validator(mode="after")
    def validate_account_when_enabled(self):
        """Ensure account is configured when Teams is enabled"""
        if self.enabled and self.account is None:
            raise ValueError(
                "Microsoft account must be configured when Teams is enabled. "
                "Set TEAMS__ACCOUNT__CLIENT_ID and TEAMS__ACCOUNT__TENANT_ID in .env"
            )
        return self


class CalendarConfig(BaseModel):
    """
    Configuration for Microsoft Calendar integration

    Controls calendar event processing via Microsoft Graph API.
    Requires MicrosoftAccountConfig with Calendars.Read/ReadWrite permissions.
    """

    enabled: bool = Field(False, description="Enable Calendar integration (opt-in, default OFF)")
    account: Optional[MicrosoftAccountConfig] = Field(
        None, description="Microsoft account configuration (can reuse Teams account)"
    )
    poll_interval_seconds: int = Field(
        300,
        ge=60,
        le=3600,
        description="Polling interval for calendar updates (seconds, default 5 min)",
    )
    days_ahead: int = Field(7, ge=1, le=30, description="Number of days ahead to fetch events")
    days_behind: int = Field(
        1, ge=0, le=7, description="Number of days behind to include (for recent events)"
    )
    include_declined: bool = Field(False, description="Include events the user has declined")
    include_tentative: bool = Field(True, description="Include tentatively accepted events")
    briefing_hours_ahead: int = Field(
        24, ge=1, le=72, description="Hours ahead for briefing (default: next 24 hours)"
    )

    @model_validator(mode="after")
    def validate_account_when_enabled(self):
        """Ensure account is configured when Calendar is enabled"""
        if self.enabled and self.account is None:
            raise ValueError(
                "Microsoft account must be configured when Calendar is enabled. "
                "Set CALENDAR__ACCOUNT__CLIENT_ID and CALENDAR__ACCOUNT__TENANT_ID in .env"
            )
        return self


class ICloudCalendarConfig(BaseModel):
    """
    Configuration for iCloud Calendar integration

    Uses CalDAV protocol to access iCloud Calendar.
    Requires an app-specific password generated from appleid.apple.com.
    """

    enabled: bool = Field(
        False, description="Enable iCloud Calendar integration (opt-in, default OFF)"
    )
    username: str = Field("", description="Apple ID email address")
    app_specific_password: str = Field(
        "", description="App-specific password from appleid.apple.com"
    )
    server_url: str = Field("https://caldav.icloud.com", description="iCloud CalDAV server URL")
    past_days: int = Field(
        365, ge=0, le=730, description="Number of days in the past to search (default: 1 year)"
    )
    future_days: int = Field(
        90, ge=1, le=365, description="Number of days in the future to search (default: 3 months)"
    )
    max_results: int = Field(
        20, ge=1, le=100, description="Maximum number of results to return per search"
    )
    calendar_names: Optional[list[str]] = Field(
        None, description="List of calendar names to include (None = all calendars)"
    )

    @model_validator(mode="after")
    def validate_credentials_when_enabled(self):
        """Ensure credentials are configured when iCloud Calendar is enabled"""
        if self.enabled:
            if not self.username:
                raise ValueError(
                    "iCloud username (Apple ID) must be configured when iCloud Calendar "
                    "is enabled. Set ICLOUD_CALENDAR__USERNAME in .env"
                )
            if not self.app_specific_password:
                raise ValueError(
                    "iCloud app-specific password must be configured. Generate one at "
                    "appleid.apple.com and set ICLOUD_CALENDAR__APP_SPECIFIC_PASSWORD in .env"
                )
        return self


class BriefingConfig(BaseModel):
    """
    Configuration for the intelligent briefing system

    Controls how briefings are generated from multiple sources (Email, Calendar, Teams).
    Supports morning briefings and pre-meeting briefings with contextual information.
    """

    enabled: bool = Field(True, description="Enable briefing system")

    # Morning briefing settings
    morning_hours_behind: int = Field(
        12, ge=1, le=48, description="Hours behind to look for emails/teams messages"
    )
    morning_hours_ahead: int = Field(
        24, ge=1, le=72, description="Hours ahead to look for calendar events"
    )

    # Pre-meeting briefing settings
    pre_meeting_minutes_before: int = Field(
        15, ge=5, le=60, description="Minutes before meeting to generate pre-meeting briefing"
    )
    pre_meeting_context_days: int = Field(
        7, ge=1, le=30, description="Days of context to fetch for attendee communications"
    )

    # Display settings
    max_urgent_items: int = Field(
        5, ge=1, le=20, description="Maximum urgent items to show in briefing"
    )
    max_standard_items: int = Field(
        10, ge=1, le=50, description="Maximum standard items per category"
    )
    show_confidence: bool = Field(True, description="Show confidence scores and AI summaries")

    # Source toggles
    include_emails: bool = Field(True, description="Include emails in briefings")
    include_calendar: bool = Field(True, description="Include calendar events in briefings")
    include_teams: bool = Field(True, description="Include Teams messages in briefings")


class WorkflowV2Config(BaseModel):
    """
    Configuration Workflow v2.1 — Knowledge Extraction

    Controls the new 4-phase knowledge extraction pipeline:
    1. Perception: Event normalization
    2. Context: Note retrieval for enrichment
    3. Analysis: AI extraction with Haiku → Sonnet escalation
    4. Application: PKM enrichment and OmniFocus task creation

    Key features:
    - Model escalation: Haiku first, Sonnet if low confidence
    - Auto-application: High confidence extractions applied automatically
    - OmniFocus integration: Deadlines create tasks automatically
    """

    # Activation
    enabled: bool = Field(
        False, description="Enable Workflow v2.1 knowledge extraction (opt-in, default OFF)"
    )

    # Modèles AI
    default_model: str = Field(
        "haiku", description="Default model for analysis (haiku = fast/cheap)"
    )
    escalation_model: str = Field(
        "sonnet", description="Escalation model for low confidence cases (sonnet = more capable)"
    )
    escalation_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which to escalate to stronger model",
    )

    # Contexte (what context to provide to AI)
    context_notes_count: int = Field(
        3, ge=0, le=10, description="Maximum number of context notes to include in prompt"
    )
    context_note_max_chars: int = Field(
        300, ge=50, le=1000, description="Maximum characters per context note summary"
    )
    event_content_max_chars: int = Field(
        2000, ge=500, le=10000, description="Maximum characters of event content to include"
    )

    # Application automatique
    auto_apply_threshold: float = Field(
        0.85,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for automatic application (no human review)",
    )
    notify_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Confidence threshold below which to notify user"
    )

    # OmniFocus integration
    omnifocus_enabled: bool = Field(
        True, description="Enable OmniFocus task creation for deadlines"
    )
    omnifocus_default_project: str = Field(
        "Inbox", description="Default OmniFocus project for new tasks"
    )

    # Extraction rules
    min_extraction_importance: str = Field(
        "moyenne", description="Minimum importance level to extract (haute or moyenne)"
    )
    extract_decisions: bool = Field(True, description="Extract decisions from events")
    extract_engagements: bool = Field(
        True, description="Extract engagements/commitments from events"
    )
    extract_deadlines: bool = Field(True, description="Extract deadlines from events")
    extract_relations: bool = Field(
        True, description="Extract relationship information from events"
    )
    extract_facts: bool = Field(True, description="Extract important facts from events")

    # v2.2 Multi-pass analysis (v2.3 transparency)
    use_multi_pass: bool = Field(
        True,
        description="Enable multi-pass analysis with transparency metadata (v2.2/v2.3)",
    )


class APIConfig(BaseModel):
    """
    API server configuration.
    """

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )
    cors_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods",
    )
    cors_headers: list[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type", "X-Request-ID"],
        description="Allowed CORS headers",
    )


class AuthConfig(BaseModel):
    """
    Configuration for JWT authentication

    Single-user system using PIN code (4-6 digits) for quick mobile access.
    """

    enabled: bool = Field(True, description="Enable authentication (disable for development)")
    warn_disabled_in_production: bool = Field(
        True, description="Log warning if auth disabled in production environment"
    )
    jwt_secret_key: str = Field(
        ...,  # Required - no default for security
        min_length=32,
        description=(
            "Secret key for JWT signing (min 32 characters). "
            'Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        ),
    )
    jwt_algorithm: str = Field("HS256", description="JWT signing algorithm")
    jwt_expire_minutes: int = Field(
        60 * 24 * 7,  # 7 days
        ge=60,
        le=60 * 24 * 30,
        description="JWT token expiration in minutes (default: 7 days)",
    )
    pin_hash: str = Field("", description="Bcrypt hash of the PIN code (4-6 digits)")


class AutoFetchConfig(BaseModel):
    """
    Configuration AutoFetch (SC-20)

    Controls automatic background fetching of new emails/events
    to keep the review queue populated.
    """

    enabled: bool = Field(True, description="Enable automatic background fetching")
    low_threshold: int = Field(
        5,
        ge=0,
        le=50,
        description="Fetch triggered when queue drops below this count (during runtime)",
    )
    startup_threshold: int = Field(
        20,
        ge=0,
        le=100,
        description="Fetch triggered at startup if queue below this count",
    )
    email_cooldown_minutes: int = Field(
        2,
        ge=1,
        le=60,
        description="Minimum minutes between email fetches",
    )
    teams_cooldown_minutes: int = Field(
        2,
        ge=1,
        le=60,
        description="Minimum minutes between Teams fetches",
    )
    calendar_cooldown_minutes: int = Field(
        5,
        ge=1,
        le=60,
        description="Minimum minutes between calendar fetches",
    )
    fetch_limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum items to fetch per source per trigger",
    )

    # Confidence-based routing (Phase 3)
    auto_apply_threshold: int = Field(
        85,
        ge=50,
        le=100,
        description="Confidence threshold for auto-apply (>= this value = auto-execute)",
    )
    auto_apply_enabled: bool = Field(
        True,
        description="Enable auto-apply for high-confidence items",
    )


class ScapinConfig(BaseSettings):
    """
    Configuration principale Scapin

    Charge depuis:
    1. config/defaults.yaml (defaults)
    2. .env (environment variables)
    3. Overrides programmatiques
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # EMAIL__IMAP_HOST
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )

    # Application
    environment: str = Field("development", description="Environment (dev/prod)")

    # Sub-configs
    email: EmailConfig
    ai: AIConfig
    storage: StorageConfig = Field(default_factory=StorageConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    teams: TeamsConfig = Field(default_factory=TeamsConfig)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    icloud_calendar: ICloudCalendarConfig = Field(default_factory=ICloudCalendarConfig)
    briefing: BriefingConfig = Field(default_factory=BriefingConfig)
    workflow_v2: WorkflowV2Config = Field(default_factory=WorkflowV2Config)
    autofetch: AutoFetchConfig = Field(default_factory=AutoFetchConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    api: APIConfig = Field(default_factory=APIConfig)


class ConfigManager:
    """
    Gestionnaire de configuration centralisé

    Usage:
        config = ConfigManager.load()
        print(config.email.imap_host)
        print(config.ai.anthropic_api_key)
    """

    _instance: Optional[ScapinConfig] = None
    _lock = threading.Lock()

    @classmethod
    def load(
        cls, config_path: Optional[Path] = None, _env_file: Optional[Path] = None
    ) -> ScapinConfig:
        """
        Charge configuration depuis fichiers (thread-safe)

        Args:
            config_path: Path to defaults.yaml (default: config/defaults.yaml)
            env_file: Path to .env (default: .env)

        Returns:
            ScapinConfig instance validée

        Raises:
            ValidationError: Si configuration invalide
            FileNotFoundError: Si fichiers requis manquants
        """
        # Fast path: already loaded
        if cls._instance is not None:
            return cls._instance

        # Double-check locking pattern for thread safety
        with cls._lock:
            # Check again inside lock
            if cls._instance is not None:
                return cls._instance

            # Load defaults from YAML
            defaults = {}
            if config_path is None:
                config_path = Path("config/defaults.yaml")

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    yaml_defaults = yaml.safe_load(f) or {}

                    # Remove nested configs from defaults to let Pydantic Settings
                    # load them from environment variables (EMAIL__, AI__, etc.)
                    # If we pass them as dicts, Pydantic won't check env vars
                    for key in ["email", "ai", "storage", "integrations", "monitoring"]:
                        yaml_defaults.pop(key, None)

                    defaults = yaml_defaults

            # Merge with environment variables
            # Pydantic Settings will automatically load from .env
            try:
                cls._instance = ScapinConfig(**defaults)
            except Exception as e:
                raise ValueError(
                    f"Failed to load configuration. "
                    f"Make sure .env is configured with your API keys. "
                    f"Error: {e}"
                ) from e

        return cls._instance

    @classmethod
    def reload(cls) -> ScapinConfig:
        """Force reload configuration"""
        cls._instance = None
        return cls.load()

    @classmethod
    def get(cls) -> ScapinConfig:
        """
        Get configuration (load if not loaded)

        Returns:
            ScapinConfig instance
        """
        if cls._instance is None:
            return cls.load()
        return cls._instance


# Convenience function
def get_config() -> ScapinConfig:
    """
    Get global configuration instance

    Usage:
        from core.config_manager import get_config

        config = get_config()
        print(config.email.imap_host)
    """
    return ConfigManager.get()
