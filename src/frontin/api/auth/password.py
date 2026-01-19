"""
PIN/Password Hashing Utilities

Uses bcrypt directly for secure PIN/password handling.
Designed for 4-6 digit PIN codes for quick mobile access.
"""

import bcrypt


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """
    Verify a PIN against its hash

    Args:
        plain_pin: Plain text PIN (4-6 digits)
        hashed_pin: Bcrypt hash of the PIN

    Returns:
        True if PIN matches, False otherwise
    """
    if not hashed_pin:
        return False
    try:
        return bcrypt.checkpw(
            plain_pin.encode("utf-8"),
            hashed_pin.encode("utf-8")
        )
    except Exception:
        return False


def get_pin_hash(pin: str) -> str:
    """
    Generate a bcrypt hash for a PIN

    Args:
        pin: Plain text PIN (4-6 digits)

    Returns:
        Bcrypt hash string

    Usage:
        # Generate hash for configuration:
        python -c "from src.frontin.api.auth.password import get_pin_hash; print(get_pin_hash('1234'))"
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pin.encode("utf-8"), salt)
    return hashed.decode("utf-8")
