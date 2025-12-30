"""
Event Normalizers

Converters that transform source-specific data into universal PerceivedEvent format.
"""

from src.core.events.normalizers.email_normalizer import EmailNormalizer

__all__ = [
    "EmailNormalizer",
]
