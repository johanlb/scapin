"""
Secure Credential Management

Uses macOS Keychain (via keyring) to securely store and retrieve credentials.
Falls back to environment variables if keyring is not available.

Usage:
    from core.secrets import get_secret, set_secret

    # Get credential (from keychain or .env)
    api_key = get_secret("ANTHROPIC_API_KEY")

    # Store credential in keychain
    set_secret("ANTHROPIC_API_KEY", "sk-ant-...")
"""

import os
from pathlib import Path
from typing import Optional

from src.monitoring.logger import get_logger

logger = get_logger("secrets")

# Load .env file for environment variables
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    dotenv_path = Path(__file__).parent.parent.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        logger.debug(f"Loaded environment variables from {dotenv_path}")
except ImportError:
    logger.warning("python-dotenv not installed - environment variables from .env won't be loaded")

# Try to import keyring (optional dependency)
try:
    import keyring
    KEYRING_AVAILABLE = True
    logger.info("Keyring is available for secure credential storage")
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning(
        "Keyring not available - credentials will be read from environment only. "
        "Install with: pip install keyring"
    )

# Keyring service name
SERVICE_NAME = "com.johanlb.pkm"


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get secret from keychain or environment

    Priority:
    1. macOS Keychain (if available)
    2. Environment variables
    3. Default value

    Args:
        key: Secret key name (e.g., "ANTHROPIC_API_KEY")
        default: Default value if not found

    Returns:
        Secret value or default

    Example:
        api_key = get_secret("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
    """
    # Try keychain first (if available)
    if KEYRING_AVAILABLE:
        try:
            value = keyring.get_password(SERVICE_NAME, key)
            if value:
                logger.debug(f"Retrieved {key} from keychain")
                return value
        except Exception as e:
            logger.warning(f"Failed to get {key} from keychain: {e}")

    # Fallback to environment variables
    value = os.getenv(key)
    if value:
        logger.debug(f"Retrieved {key} from environment")
        return value

    # Return default
    if default is not None:
        logger.debug(f"Using default value for {key}")
        return default

    logger.warning(f"Secret {key} not found in keychain or environment")
    return None


def set_secret(key: str, value: str) -> bool:
    """
    Store secret in keychain

    Args:
        key: Secret key name (e.g., "ANTHROPIC_API_KEY")
        value: Secret value

    Returns:
        True if successful, False otherwise

    Example:
        success = set_secret("ANTHROPIC_API_KEY", "sk-ant-...")
        if success:
            print("API key stored securely in keychain")
    """
    if not KEYRING_AVAILABLE:
        logger.error(
            "Cannot store secret - keyring not available. "
            "Install with: pip install keyring"
        )
        return False

    try:
        keyring.set_password(SERVICE_NAME, key, value)
        logger.info(f"Stored {key} in keychain")
        return True
    except Exception as e:
        logger.error(f"Failed to store {key} in keychain: {e}", exc_info=True)
        return False


def delete_secret(key: str) -> bool:
    """
    Delete secret from keychain

    Args:
        key: Secret key name

    Returns:
        True if successful, False otherwise
    """
    if not KEYRING_AVAILABLE:
        logger.warning("Keyring not available - nothing to delete")
        return False

    try:
        keyring.delete_password(SERVICE_NAME, key)
        logger.info(f"Deleted {key} from keychain")
        return True
    except Exception as e:
        logger.warning(f"Failed to delete {key} from keychain: {e}")
        return False


def list_stored_secrets() -> list:
    """
    List all secret keys stored in keychain

    Note: Only works with keyring backends that support list_credentials
    (not all backends support this)

    Returns:
        List of secret key names
    """
    if not KEYRING_AVAILABLE:
        return []

    try:
        # Get all credentials for our service
        credentials = keyring.get_credential(SERVICE_NAME, None)
        if credentials:
            return [credentials.username]
        return []
    except Exception as e:
        logger.debug(f"Could not list credentials: {e}")
        return []


def migrate_from_env_to_keychain(keys: list[str]) -> dict[str, bool]:
    """
    Migrate secrets from environment variables to keychain

    Args:
        keys: List of secret keys to migrate (e.g., ["ANTHROPIC_API_KEY", "IMAP_PASSWORD"])

    Returns:
        Dictionary mapping keys to success status

    Example:
        results = migrate_from_env_to_keychain([
            "ANTHROPIC_API_KEY",
            "IMAP_PASSWORD",
            "OPENAI_API_KEY"
        ])

        for key, success in results.items():
            if success:
                print(f"✓ Migrated {key}")
            else:
                print(f"✗ Failed to migrate {key}")
    """
    if not KEYRING_AVAILABLE:
        logger.error("Keyring not available - cannot migrate")
        return dict.fromkeys(keys, False)

    results = {}
    for key in keys:
        # Get value from environment
        value = os.getenv(key)
        if not value:
            logger.warning(f"Skipping {key} - not found in environment")
            results[key] = False
            continue

        # Store in keychain
        success = set_secret(key, value)
        results[key] = success

        if success:
            logger.info(
                f"✓ Migrated {key} to keychain. "
                f"You can now remove it from .env file for better security."
            )

    return results
