"""
CrossSourceEngine - Unified search across all data sources.

This module provides intelligent cross-source searching capabilities for Scapin,
allowing retrieval of relevant information from emails, calendar, Teams,
WhatsApp, files, and web search.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.passepartout.cross_source.cache import CrossSourceCache
from src.passepartout.cross_source.config import CrossSourceConfig
from src.passepartout.cross_source.engine import CrossSourceEngine
from src.passepartout.cross_source.models import (
    CrossSourceRequest,
    CrossSourceResult,
    LinkedSource,
    SourceItem,
)

if TYPE_CHECKING:
    from src.core.config_manager import ScapinConfig

logger = logging.getLogger("scapin.cross_source")

__all__ = [
    "CrossSourceCache",
    "CrossSourceConfig",
    "CrossSourceEngine",
    "CrossSourceRequest",
    "CrossSourceResult",
    "LinkedSource",
    "SourceItem",
    "create_cross_source_engine",
]


def create_cross_source_engine(
    config: ScapinConfig | None = None,
) -> CrossSourceEngine:
    """
    Factory function to create a fully initialized CrossSourceEngine.

    Creates and registers all available adapters based on configuration:
    - iCloud Calendar (if enabled and configured)
    - Microsoft Calendar (if enabled and configured)
    - Microsoft Teams (if enabled and configured)
    - Email (always available if IMAP configured)

    Args:
        config: ScapinConfig instance. If None, loads from ConfigManager.

    Returns:
        CrossSourceEngine with all available adapters registered.

    Example:
        ```python
        from src.passepartout.cross_source import create_cross_source_engine

        engine = create_cross_source_engine()
        result = await engine.search("project meeting")
        ```
    """
    # Load config if not provided
    if config is None:
        from src.core.config_manager import get_config
        config = get_config()

    # Create engine with default cross-source config
    cs_config = CrossSourceConfig()
    engine = CrossSourceEngine(cs_config)

    # Register iCloud Calendar adapter
    _register_icloud_calendar_adapter(engine, config)

    # Register Microsoft Calendar adapter (if configured)
    _register_ms_calendar_adapter(engine, config)

    # Register Teams adapter (if configured)
    _register_teams_adapter(engine, config)

    # Register Email adapter (if configured)
    _register_email_adapter(engine, config)

    # Register WhatsApp adapter
    _register_whatsapp_adapter(engine)

    # Register Files adapter
    _register_files_adapter(engine)

    # Register Web adapter (Tavily or DuckDuckGo)
    _register_web_adapter(engine)

    logger.info(
        "CrossSourceEngine created with %d adapters: %s",
        len(engine.available_sources),
        ", ".join(engine.available_sources) or "none",
    )

    return engine


def _register_icloud_calendar_adapter(
    engine: CrossSourceEngine,
    config: ScapinConfig,
) -> None:
    """Register iCloud Calendar adapter if configured."""
    icloud_config = config.icloud_calendar

    if not icloud_config.enabled:
        logger.debug("iCloud Calendar adapter disabled")
        return

    if not icloud_config.username or not icloud_config.app_specific_password:
        logger.warning(
            "iCloud Calendar enabled but credentials not configured. "
            "Set ICLOUD_CALENDAR__USERNAME and ICLOUD_CALENDAR__APP_SPECIFIC_PASSWORD"
        )
        return

    try:
        from src.integrations.apple.calendar_client import (
            ICloudCalendarClient,
            ICloudCalendarConfig,
        )
        from src.passepartout.cross_source.adapters.icloud_calendar_adapter import (
            ICloudCalendarAdapter,
        )
        from src.passepartout.cross_source.config import ICloudCalendarAdapterConfig

        # Create client config
        client_config = ICloudCalendarConfig(
            username=icloud_config.username,
            app_specific_password=icloud_config.app_specific_password,
            server_url=icloud_config.server_url,
        )

        # Create client
        client = ICloudCalendarClient(client_config)

        # Create adapter config
        adapter_config = ICloudCalendarAdapterConfig(
            enabled=True,
            past_days=icloud_config.past_days,
            future_days=icloud_config.future_days,
            max_results=icloud_config.max_results,
        )

        # Create and register adapter
        adapter = ICloudCalendarAdapter(client, adapter_config)
        engine.register_adapter(adapter)

        logger.info("Registered iCloud Calendar adapter")

    except Exception as e:
        logger.error("Failed to register iCloud Calendar adapter: %s", e)


def _register_ms_calendar_adapter(
    engine: CrossSourceEngine,
    config: ScapinConfig,
) -> None:
    """Register Microsoft Calendar adapter if configured."""
    calendar_config = config.calendar

    if not calendar_config.enabled:
        logger.debug("Microsoft Calendar adapter disabled")
        return

    if calendar_config.account is None:
        logger.warning(
            "Microsoft Calendar enabled but account not configured. "
            "Set CALENDAR__ACCOUNT__CLIENT_ID and CALENDAR__ACCOUNT__TENANT_ID"
        )
        return

    try:
        from src.integrations.microsoft.auth import MicrosoftAuthenticator
        from src.integrations.microsoft.calendar_client import CalendarClient
        from src.integrations.microsoft.graph_client import GraphClient
        from src.passepartout.cross_source.adapters.calendar_adapter import (
            CalendarAdapter,
        )
        from src.passepartout.cross_source.config import CalendarAdapterConfig

        # Create auth and clients
        auth = MicrosoftAuthenticator(calendar_config.account)
        graph_client = GraphClient(auth)
        calendar_client = CalendarClient(graph_client)

        # Create adapter config
        adapter_config = CalendarAdapterConfig(
            enabled=True,
            past_days=calendar_config.days_behind,
            future_days=calendar_config.days_ahead,
        )

        # Create and register adapter
        adapter = CalendarAdapter(calendar_client, adapter_config)
        engine.register_adapter(adapter)

        logger.info("Registered Microsoft Calendar adapter")

    except Exception as e:
        logger.error("Failed to register Microsoft Calendar adapter: %s", e)


def _register_teams_adapter(
    engine: CrossSourceEngine,
    config: ScapinConfig,
) -> None:
    """Register Teams adapter if configured."""
    teams_config = config.teams

    if not teams_config.enabled:
        logger.debug("Teams adapter disabled")
        return

    if teams_config.account is None:
        logger.warning(
            "Teams enabled but account not configured. "
            "Set TEAMS__ACCOUNT__CLIENT_ID and TEAMS__ACCOUNT__TENANT_ID"
        )
        return

    try:
        from src.integrations.microsoft.auth import MicrosoftAuthenticator
        from src.integrations.microsoft.graph_client import GraphClient
        from src.integrations.microsoft.teams_client import TeamsClient
        from src.passepartout.cross_source.adapters.teams_adapter import TeamsAdapter
        from src.passepartout.cross_source.config import TeamsAdapterConfig

        # Create auth and clients
        auth = MicrosoftAuthenticator(teams_config.account)
        graph_client = GraphClient(auth)
        teams_client = TeamsClient(graph_client)

        # Create adapter config
        adapter_config = TeamsAdapterConfig(enabled=True)

        # Create and register adapter
        adapter = TeamsAdapter(teams_client, adapter_config)
        engine.register_adapter(adapter)

        logger.info("Registered Teams adapter")

    except Exception as e:
        logger.error("Failed to register Teams adapter: %s", e)


def _register_email_adapter(
    engine: CrossSourceEngine,
    config: ScapinConfig,
) -> None:
    """Register Email adapter if configured."""
    email_config = config.email

    if email_config is None:
        logger.debug("Email adapter disabled (no email config)")
        return

    try:
        from src.core.config_manager import EmailAccountConfig
        from src.passepartout.cross_source.adapters.email_adapter import EmailAdapter
        from src.passepartout.cross_source.config import EmailAdapterConfig

        # Get account config - prefer accounts list, fallback to legacy fields
        account_config: EmailAccountConfig | None = None

        if email_config.accounts:
            # Use first enabled account (or default if specified)
            default_id = email_config.default_account_id
            for account in email_config.accounts:
                if account.enabled and (default_id is None or account.account_id == default_id):
                    account_config = account
                    break
        elif email_config.imap_host and email_config.imap_username:
            # Legacy single-account format
            account_config = EmailAccountConfig(
                account_id="default",
                account_name="Default Email",
                enabled=True,
                imap_host=email_config.imap_host,
                imap_port=email_config.imap_port or 993,
                imap_username=email_config.imap_username,
                imap_password=email_config.imap_password or "",
            )

        if account_config is None:
            logger.debug("Email adapter disabled (no valid account)")
            return

        # Create adapter config with defaults
        adapter_config = EmailAdapterConfig(enabled=True)

        # Create and register adapter
        adapter = EmailAdapter(account_config, adapter_config)
        engine.register_adapter(adapter)

        logger.info("Registered Email adapter for account: %s", account_config.account_name)

    except Exception as e:
        logger.error("Failed to register Email adapter: %s", e)


def _register_whatsapp_adapter(engine: CrossSourceEngine) -> None:
    """Register WhatsApp adapter if database is accessible."""
    try:
        from src.passepartout.cross_source.adapters.whatsapp_adapter import (
            WhatsAppAdapter,
        )

        # Create adapter with default settings
        # It will auto-detect the database path
        adapter = WhatsAppAdapter()

        if adapter.is_available:
            engine.register_adapter(adapter)
            logger.info("Registered WhatsApp adapter")
        else:
            logger.debug("WhatsApp adapter not available (database not found)")

    except Exception as e:
        logger.error("Failed to register WhatsApp adapter: %s", e)


def _register_files_adapter(engine: CrossSourceEngine) -> None:
    """Register Files adapter for local file search."""
    try:
        from src.passepartout.cross_source.adapters.files_adapter import FilesAdapter

        # Create adapter with default settings (Documents, Desktop, Downloads)
        adapter = FilesAdapter()

        if adapter.is_available:
            engine.register_adapter(adapter)
            logger.info("Registered Files adapter")
        else:
            logger.debug("Files adapter not available")

    except Exception as e:
        logger.error("Failed to register Files adapter: %s", e)


def _register_web_adapter(engine: CrossSourceEngine) -> None:
    """Register Web adapter (Tavily or DuckDuckGo fallback)."""
    try:
        from src.passepartout.cross_source.adapters.web_adapter import (
            create_web_adapter,
        )

        # Create best available web adapter
        adapter = create_web_adapter()

        if adapter.is_available:
            engine.register_adapter(adapter)
            logger.info("Registered Web adapter (%s)", adapter.source_name)
        else:
            logger.debug("Web adapter not available (no API keys)")

    except Exception as e:
        logger.error("Failed to register Web adapter: %s", e)
