"""
text_utils.py - Text normalization and dedup utilities
"""

import re
import hashlib


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication (strip tracking params, trailing slashes)."""
    url = url.strip().rstrip("/")
    # Remove common tracking parameters
    url = re.sub(r"[?&](utm_\w+|fbclid|gclid|ref|source)=[^&]*", "", url)
    url = re.sub(r"\?$", "", url)
    return url


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max_length, breaking at word boundary."""
    if not text or len(text) <= max_length:
        return text
    truncated = text[:max_length].rsplit(" ", 1)[0]
    return truncated + "..."


def clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def content_hash(text: str) -> str:
    """Generate a hash for content deduplication."""
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()
