"""
String Utility Functions

Helper functions for string manipulation.
"""

import re
import unicodedata
from typing import Optional


def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length

    Args:
        text: Text to truncate
        length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= length:
        return text

    # Try to truncate at last space before length
    truncated = text[:length].rsplit(' ', 1)[0]
    return truncated + suffix


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize filename by removing invalid characters

    Args:
        filename: Original filename
        replacement: Character to replace invalid chars with

    Returns:
        Sanitized filename
    """
    # Remove invalid filename characters
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, replacement, filename)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')

    # Limit length
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:max_length - len(ext) - 1] + '.' + ext if ext else sanitized[:max_length]

    return sanitized or "unnamed"


def extract_email(text: str) -> Optional[str]:
    """
    Extract first email address from text

    Args:
        text: Text to search

    Returns:
        Email address or None
    """
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_urls(text: str) -> list[str]:
    """
    Extract all URLs from text

    Args:
        text: Text to search

    Returns:
        List of URLs
    """
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(pattern, text)


def slugify(text: str, separator: str = "-") -> str:
    """
    Convert text to URL-friendly slug

    Args:
        text: Text to slugify
        separator: Separator character

    Returns:
        Slugified text
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Convert to lowercase and replace spaces/special chars
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', separator, text)

    return text.strip(separator)


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text

    - Replace multiple spaces with single space
    - Remove leading/trailing whitespace
    - Replace tabs and newlines with spaces

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Replace tabs and newlines with spaces
    text = re.sub(r'[\t\n\r]+', ' ', text)

    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)

    # Remove leading/trailing whitespace
    return text.strip()


def strip_html(text: str) -> str:
    """
    Strip HTML tags from text

    Args:
        text: HTML text

    Returns:
        Plain text
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    html_entities = {
        '&nbsp;': ' ',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&#39;': "'",
    }
    for entity, char in html_entities.items():
        text = text.replace(entity, char)

    return normalize_whitespace(text)


def camel_to_snake(text: str) -> str:
    """
    Convert camelCase to snake_case

    Args:
        text: CamelCase text

    Returns:
        snake_case text
    """
    # Insert underscore before uppercase letters
    text = re.sub(r'(?<!^)(?=[A-Z])', '_', text)
    return text.lower()


def snake_to_camel(text: str, capitalize_first: bool = False) -> str:
    """
    Convert snake_case to camelCase

    Args:
        text: snake_case text
        capitalize_first: Capitalize first letter (PascalCase)

    Returns:
        camelCase text
    """
    components = text.split('_')
    if capitalize_first:
        return ''.join(x.title() for x in components)
    else:
        return components[0] + ''.join(x.title() for x in components[1:])


def extract_mentions(text: str) -> list[str]:
    """
    Extract @mentions from text

    Args:
        text: Text to search

    Returns:
        List of mentions (without @)
    """
    pattern = r'@([a-zA-Z0-9_]+)'
    return re.findall(pattern, text)


def extract_hashtags(text: str) -> list[str]:
    """
    Extract #hashtags from text

    Args:
        text: Text to search

    Returns:
        List of hashtags (without #)
    """
    pattern = r'#([a-zA-Z0-9_]+)'
    return re.findall(pattern, text)


def word_count(text: str) -> int:
    """
    Count words in text

    Args:
        text: Text to count

    Returns:
        Word count
    """
    return len(text.split())


def char_count(text: str, include_whitespace: bool = True) -> int:
    """
    Count characters in text

    Args:
        text: Text to count
        include_whitespace: Include whitespace in count

    Returns:
        Character count
    """
    if include_whitespace:
        return len(text)
    else:
        return len(text.replace(' ', '').replace('\t', '').replace('\n', ''))
