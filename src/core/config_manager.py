"""
PKM Configuration Manager

Charge configuration hiérarchique depuis:
1. Defaults (config/defaults.yaml)
2. Environment variables (.env)
3. Overrides optionnels

Utilise Pydantic pour validation type-safe.
"""

from pathlib import Path
from typing import Optional, List
import threading
import yaml
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
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
    delete_folder: str = Field("_PKM/À supprimer", description="Delete folder name")

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
            ""
        ]
        if v.lower() in [p.lower() for p in placeholders]:
            raise ValueError(
                "IMAP password must be configured with a real password"
            )

        # Check minimum length (app-specific passwords are typically 16+ chars)
        if len(v) < 8:
            raise ValueError(
                "IMAP password too short (minimum 8 characters)"
            )

        return v

    @field_validator("imap_username")
    @classmethod
    def username_valid(cls, v: EmailStr) -> EmailStr:
        """Validate IMAP username is a valid email address"""
        # EmailStr already validates email format, just add extra checks
        v_str = str(v).strip()

        if not v_str or "@" not in v_str:
            raise ValueError(
                "IMAP username must be a valid email address"
            )

        return v

    @field_validator("account_id")
    @classmethod
    def account_id_valid(cls, v: str) -> str:
        """Validate account ID is alphanumeric + underscore/dash"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "account_id must be alphanumeric (can include _ and -)"
            )
        return v

    @field_validator("imap_port")
    @classmethod
    def port_valid(cls, v: int) -> int:
        """Validate IMAP port is in valid range"""
        if not (1 <= v <= 65535):
            raise ValueError(
                f"Invalid IMAP port {v} (must be 1-65535)"
            )
        # Warn if not using standard ports
        if v not in [143, 993]:
            import warnings
            warnings.warn(
                f"Non-standard IMAP port {v} (standard: 143 or 993)",
                UserWarning
            )
        return v


class EmailConfig(BaseModel):
    """
    Multi-account email configuration

    Supports multiple IMAP accounts with fallback to single-account format
    for backward compatibility.
    """

    # Multi-account configuration
    accounts: List[EmailAccountConfig] = Field(
        default_factory=list,
        description="List of email accounts"
    )
    default_account_id: Optional[str] = Field(
        None,
        description="Default account ID to use"
    )

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

    @model_validator(mode='after')
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
                raise ValueError(
                    "At least one account must be enabled"
                )

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
                delete_folder=self.delete_folder or "_PKM/À supprimer",
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

    def get_enabled_accounts(self) -> List[EmailAccountConfig]:
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
            raise ValueError(
                "ANTHROPIC_API_KEY must be configured in .env with your real API key"
            )
        return v


class StorageConfig(BaseModel):
    """Configuration storage (DB, Git, filesystem)"""

    database_path: Path = Field(Path("data/pkm.db"), description="SQLite database path")
    notes_path: Path = Field(
        Path.home() / "Documents/PKM/Notes", description="Notes directory"
    )
    github_repo_url: Optional[str] = Field(
        None, description="GitHub remote repository URL"
    )
    backup_enabled: bool = Field(True, description="Enable automatic backups")
    backup_retention_days: int = Field(30, ge=1, le=365, description="Backup retention")


class IntegrationsConfig(BaseModel):
    """Configuration intégrations externes"""

    omnifocus_enabled: bool = Field(True, description="Enable OmniFocus integration")
    apple_notes_sync_enabled: bool = Field(
        False, description="Enable Apple Notes sync (Phase 6)"
    )
    sync_interval_minutes: int = Field(
        30, ge=1, le=1440, description="Sync interval in minutes"
    )
    calendar_enabled: bool = Field(False, description="Enable Calendar integration")


class MonitoringConfig(BaseModel):
    """Configuration monitoring & observability"""

    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field("json", description="Log format (json or text)")
    health_check_enabled: bool = Field(True, description="Enable health checks")
    metrics_port: int = Field(8000, ge=1024, le=65535, description="Metrics server port")
    error_reporting_enabled: bool = Field(True, description="Enable error reporting")


class PKMConfig(BaseSettings):
    """
    Configuration principale PKM

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


class ConfigManager:
    """
    Gestionnaire de configuration centralisé

    Usage:
        config = ConfigManager.load()
        print(config.email.imap_host)
        print(config.ai.anthropic_api_key)
    """

    _instance: Optional[PKMConfig] = None
    _lock = threading.Lock()

    @classmethod
    def load(
        cls, config_path: Optional[Path] = None, env_file: Optional[Path] = None
    ) -> PKMConfig:
        """
        Charge configuration depuis fichiers (thread-safe)

        Args:
            config_path: Path to defaults.yaml (default: config/defaults.yaml)
            env_file: Path to .env (default: .env)

        Returns:
            PKMConfig instance validée

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
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_defaults = yaml.safe_load(f) or {}

                    # Remove nested configs from defaults to let Pydantic Settings
                    # load them from environment variables (EMAIL__, AI__, etc.)
                    # If we pass them as dicts, Pydantic won't check env vars
                    for key in ['email', 'ai', 'storage', 'integrations', 'monitoring']:
                        yaml_defaults.pop(key, None)

                    defaults = yaml_defaults

            # Merge with environment variables
            # Pydantic Settings will automatically load from .env
            try:
                cls._instance = PKMConfig(**defaults)
            except Exception as e:
                raise ValueError(
                    f"Failed to load configuration. "
                    f"Make sure .env is configured with your API keys. "
                    f"Error: {e}"
                ) from e

        return cls._instance

    @classmethod
    def reload(cls) -> PKMConfig:
        """Force reload configuration"""
        cls._instance = None
        return cls.load()

    @classmethod
    def get(cls) -> PKMConfig:
        """
        Get configuration (load if not loaded)

        Returns:
            PKMConfig instance
        """
        if cls._instance is None:
            return cls.load()
        return cls._instance


# Convenience function
def get_config() -> PKMConfig:
    """
    Get global configuration instance

    Usage:
        from core.config_manager import get_config

        config = get_config()
        print(config.email.imap_host)
    """
    return ConfigManager.get()
