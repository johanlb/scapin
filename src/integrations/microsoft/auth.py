"""
Microsoft MSAL Authentication

Handles OAuth 2.0 authentication for Microsoft Graph API using MSAL.

Supports:
- Device code flow (for CLI applications)
- Silent token refresh
- Persistent token cache
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import msal

from src.core.config_manager import MicrosoftAccountConfig
from src.monitoring.logger import get_logger

logger = get_logger("integrations.microsoft.auth")


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


@dataclass
class TokenCache:
    """
    Persistent token cache for MSAL

    Stores tokens on disk to avoid re-authentication on each run.
    Thread-safe for reading, writes are serialized.
    """

    cache_file: Path
    _cache: msal.SerializableTokenCache = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the cache from file if it exists"""
        self._cache = msal.SerializableTokenCache()
        if self.cache_file.exists():
            try:
                cache_data = self.cache_file.read_text()
                self._cache.deserialize(cache_data)
                logger.debug(f"Loaded token cache from {self.cache_file}")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load token cache: {e}")

    @property
    def cache(self) -> msal.SerializableTokenCache:
        """Get the underlying MSAL cache"""
        return self._cache

    def save(self) -> None:
        """Save cache to disk if it has changed"""
        if self._cache.has_state_changed:
            try:
                # Ensure directory exists
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                self.cache_file.write_text(self._cache.serialize())
                logger.debug(f"Saved token cache to {self.cache_file}")
            except OSError as e:
                logger.error(f"Failed to save token cache: {e}")


class MicrosoftAuthenticator:
    """
    OAuth 2.0 authenticator for Microsoft Graph API

    Uses MSAL (Microsoft Authentication Library) for secure token management.

    Usage:
        config = MicrosoftAccountConfig(
            client_id="your-client-id",
            tenant_id="your-tenant-id",
        )
        auth = MicrosoftAuthenticator(config, Path("data"))
        token = await auth.get_token()
    """

    def __init__(
        self,
        config: MicrosoftAccountConfig,
        cache_dir: Path,
    ) -> None:
        """
        Initialize authenticator

        Args:
            config: Microsoft account configuration
            cache_dir: Directory for token cache storage
        """
        self.config = config
        self.token_cache = TokenCache(cache_dir / "ms_token_cache.json")

        # Create MSAL application
        self._app = msal.PublicClientApplication(
            client_id=config.client_id,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}",
            token_cache=self.token_cache.cache,
        )

        logger.info(f"Initialized Microsoft authenticator for tenant {config.tenant_id}")

    def get_token(self) -> str:
        """
        Get a valid access token

        Tries silent acquisition first, falls back to device code flow.
        This is synchronous because MSAL doesn't have async support.

        Returns:
            Valid access token string

        Raises:
            AuthenticationError: If authentication fails
        """
        # Get scopes as list
        scopes = list(self.config.scopes)

        # Try silent acquisition first
        accounts = self._app.get_accounts()
        if accounts:
            logger.debug(f"Found {len(accounts)} cached account(s)")
            result = self._app.acquire_token_silent(
                scopes=scopes,
                account=accounts[0],
            )
            if result and "access_token" in result:
                logger.debug("Acquired token silently")
                return result["access_token"]

        # Need interactive login
        logger.info("Silent token acquisition failed, initiating device code flow")
        return self._interactive_login(scopes)

    def _interactive_login(self, scopes: list[str]) -> str:
        """
        Perform device code flow authentication

        Displays instructions for user to authenticate via browser.

        Args:
            scopes: List of permission scopes to request

        Returns:
            Access token string

        Raises:
            AuthenticationError: If login fails
        """
        # Initiate device code flow
        flow = self._app.initiate_device_flow(scopes=scopes)

        if "error" in flow:
            raise AuthenticationError(
                f"Failed to initiate device flow: {flow.get('error_description', flow['error'])}"
            )

        # Display instructions to user
        print("\n" + "=" * 60)
        print("Microsoft Authentication Required")
        print("=" * 60)
        print(f"\n{flow['message']}\n")
        print("=" * 60 + "\n")

        # Wait for user to complete authentication
        result = self._app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            error_desc = result.get("error_description", result.get("error", "Unknown error"))
            raise AuthenticationError(f"Authentication failed: {error_desc}")

        # Save the cache
        self.token_cache.save()

        logger.info("Successfully authenticated with Microsoft")
        return result["access_token"]

    def logout(self) -> None:
        """
        Clear cached accounts and tokens

        Forces re-authentication on next token request.
        """
        accounts = self._app.get_accounts()
        for account in accounts:
            self._app.remove_account(account)

        # Clear the cache file
        if self.token_cache.cache_file.exists():
            self.token_cache.cache_file.unlink()

        logger.info("Logged out from Microsoft")

    def is_authenticated(self) -> bool:
        """
        Check if there are cached tokens

        Returns:
            True if cached tokens exist
        """
        accounts = self._app.get_accounts()
        return len(accounts) > 0

    def get_user_info(self) -> Optional[dict]:
        """
        Get info about the authenticated user

        Returns:
            User info dict or None if not authenticated
        """
        accounts = self._app.get_accounts()
        if accounts:
            return {
                "username": accounts[0].get("username"),
                "name": accounts[0].get("name"),
                "home_account_id": accounts[0].get("home_account_id"),
            }
        return None
