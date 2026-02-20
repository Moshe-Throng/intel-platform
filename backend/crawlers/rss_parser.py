"""
rss_parser.py - Parse RSS feeds and extract articles

Usage:
    from crawlers.rss_parser import parse_rss_feed
    articles = parse_rss_feed("https://reliefweb.int/updates/rss.xml?country=eth", source_id)
"""

import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.text_utils import normalize_url, clean_html


def parse_rss_feed(feed_url: str, source_id: str) -> list[dict]:
    """
    Parse an RSS feed and return a list of article dicts ready for Supabase insert.

    Returns list of dicts with keys matching the articles table schema.
    """
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        print(f"  [WARN] Feed error for {feed_url}: {feed.bozo_exception}")
        return []

    articles = []
    for entry in feed.entries:
        url = normalize_url(entry.get("link", ""))
        if not url:
            continue

        title = clean_html(entry.get("title", "")).strip()
        if not title:
            continue

        # Extract summary
        summary = clean_html(
            entry.get("summary", "") or entry.get("description", "")
        )

        # Extract full content if available
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = clean_html(entry.content[0].get("value", ""))

        # Parse published date
        published_at = None
        if entry.get("published_parsed"):
            try:
                published_at = datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                pass
        elif entry.get("published"):
            try:
                published_at = parsedate_to_datetime(entry.published).isoformat()
            except Exception:
                pass

        # Extract author
        author = entry.get("author", "") or ""

        articles.append({
            "source_id": source_id,
            "title": title,
            "url": url,
            "summary": summary[:2000] if summary else None,
            "content": content[:50000] if content else None,
            "author": author[:500] if author else None,
            "published_at": published_at,
        })

    return articles
