#!/bin/bash
# ============================================================
# Intel Platform Backend - VPS Deployment Script
#
# This script recreates the entire backend directory structure
# and all Python files at /root/intel-platform/backend/
#
# Usage:
#   bash deploy_to_vps.sh
# ============================================================

set -e

BASE="/root/intel-platform/backend"

echo "============================================================"
echo "Intel Platform Backend - File Deployment"
echo "Target: $BASE"
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

# Create directory structure
echo ""
echo ">>> Creating directory structure..."
mkdir -p "$BASE/utils"
mkdir -p "$BASE/crawlers"
mkdir -p "$BASE/processors"
mkdir -p "$BASE/scripts"

# ──────────────────────────────────────────────────────────────
# .env
# ──────────────────────────────────────────────────────────────
echo ">>> Creating .env..."
cat << 'PYEOF' > "$BASE/.env"
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key
OPENAI_API_KEY=your-openai-key
CRAWL4AI_BASE_URL=http://localhost:11235
POSTIZ_API_KEY=
POSTIZ_BASE_URL=http://localhost:5000/api
PYEOF

# ──────────────────────────────────────────────────────────────
# utils/__init__.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating utils/__init__.py..."
touch "$BASE/utils/__init__.py"

# ──────────────────────────────────────────────────────────────
# utils/supabase_client.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating utils/supabase_client.py..."
cat << 'PYEOF' > "$BASE/utils/supabase_client.py"
"""
supabase_client.py - Database helper functions for Intel Platform

All Supabase interactions go through this module.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env
env_paths = [
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
]
for p in env_paths:
    if p.exists():
        load_dotenv(p)
        break

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

_client: Client = None


def get_client() -> Client:
    """Get or create Supabase client (singleton)."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ── News Sources ──

def get_active_sources(source_type: str = None) -> list[dict]:
    """Fetch active news sources, optionally filtered by type."""
    query = get_client().table("news_sources").select("*").eq("is_active", True)
    if source_type:
        query = query.eq("source_type", source_type)
    return query.execute().data


def update_source_last_crawled(source_id: str):
    """Mark a source as just crawled."""
    get_client().table("news_sources").update(
        {"last_crawled_at": "now()"}
    ).eq("id", source_id).execute()


# ── Articles ──

def insert_article(article: dict) -> dict | None:
    """Insert an article. Returns None if URL already exists (dedup)."""
    try:
        result = get_client().table("articles").insert(article).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        if "duplicate key" in str(e) or "23505" in str(e):
            return None  # URL already exists, skip
        raise


def insert_articles_batch(articles: list[dict]) -> list[dict]:
    """Insert multiple articles, skipping duplicates."""
    inserted = []
    for article in articles:
        result = insert_article(article)
        if result:
            inserted.append(result)
    return inserted


def get_untagged_articles(limit: int = 50) -> list[dict]:
    """Fetch articles that haven't been tagged yet."""
    return (
        get_client()
        .table("articles")
        .select("id, title, summary, content, url")
        .eq("is_tagged", False)
        .order("crawled_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def mark_article_tagged(article_id: str, urgency: str = "normal"):
    """Mark an article as tagged and set urgency."""
    get_client().table("articles").update(
        {"is_tagged": True, "urgency": urgency}
    ).eq("id", article_id).execute()


def get_articles_without_posts(platform: str, limit: int = 20) -> list[dict]:
    """Fetch tagged articles that don't have a post for the given platform."""
    # Get article IDs that already have posts for this platform
    existing = (
        get_client()
        .table("published_posts")
        .select("article_id")
        .eq("platform", platform)
        .execute()
        .data
    )
    existing_ids = [r["article_id"] for r in existing]

    query = (
        get_client()
        .table("articles")
        .select("id, title, summary, urgency, url")
        .eq("is_tagged", True)
        .order("published_at", desc=True)
        .limit(limit)
    )

    articles = query.execute().data

    # Filter out articles that already have posts
    if existing_ids:
        articles = [a for a in articles if a["id"] not in existing_ids]

    return articles


# ── Tags ──

def get_all_tags() -> list[dict]:
    """Fetch all tags."""
    return get_client().table("tags").select("*").execute().data


def get_tags_by_names(names: list[str]) -> list[dict]:
    """Fetch tags by their names."""
    return (
        get_client()
        .table("tags")
        .select("id, name, category")
        .in_("name", names)
        .execute()
        .data
    )


def insert_article_tags(article_id: str, tag_ids: list[str], confidence: float = 1.0):
    """Link tags to an article."""
    rows = [
        {"article_id": article_id, "tag_id": tid, "confidence": confidence}
        for tid in tag_ids
    ]
    try:
        get_client().table("article_tags").upsert(rows).execute()
    except Exception:
        # If some already exist, insert one by one
        for row in rows:
            try:
                get_client().table("article_tags").upsert(row).execute()
            except Exception:
                pass


# ── Published Posts ──

def insert_post(post: dict) -> dict | None:
    """Insert a social media post record."""
    result = get_client().table("published_posts").insert(post).execute()
    return result.data[0] if result.data else None


def update_post_status(post_id: str, status: str, postiz_post_id: str = None):
    """Update post status after publishing."""
    update = {"status": status}
    if postiz_post_id:
        update["postiz_post_id"] = postiz_post_id
    if status == "published":
        update["published_at"] = "now()"
    get_client().table("published_posts").update(update).eq("id", post_id).execute()
PYEOF

# ──────────────────────────────────────────────────────────────
# utils/text_utils.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating utils/text_utils.py..."
cat << 'PYEOF' > "$BASE/utils/text_utils.py"
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
PYEOF

# ──────────────────────────────────────────────────────────────
# utils/taxonomies.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating utils/taxonomies.py..."
cat << 'PYEOF' > "$BASE/utils/taxonomies.py"
"""
taxonomies.py - Tag definitions for GPT-4 auto-tagging

These lists are passed to GPT-4 as the allowed tag vocabulary.
Must match what's seeded in the tags table.
"""

TOPICS = [
    "Humanitarian Aid", "Food Security", "Health", "Education",
    "Climate Change", "Conflict", "Displacement", "Governance",
    "Economic Development", "Gender Equality", "Water & Sanitation",
    "Agriculture", "Infrastructure", "Human Rights", "Elections",
    "Peace & Security", "Refugees", "Child Protection", "Nutrition",
    "Funding & Grants",
]

ACTORS = [
    "UN", "USAID", "World Bank", "African Union", "EU", "WHO",
    "UNICEF", "WFP", "UNHCR", "ICRC", "Government of Ethiopia",
    "African Development Bank", "DFID/FCDO", "Gates Foundation",
    "Save the Children",
]

LOCATIONS = [
    "Addis Ababa", "Tigray", "Amhara", "Oromia", "Somali Region",
    "SNNPR", "Afar", "Sidama", "Benishangul-Gumuz", "Gambella",
    "Dire Dawa", "Harari",
]

SECTORS = [
    "NGO", "Government", "Private Sector", "Multilateral",
    "Bilateral", "Academia", "Media", "Civil Society",
]

ALL_TAGS = TOPICS + ACTORS + LOCATIONS + SECTORS
PYEOF

# ──────────────────────────────────────────────────────────────
# crawlers/__init__.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating crawlers/__init__.py..."
touch "$BASE/crawlers/__init__.py"

# ──────────────────────────────────────────────────────────────
# crawlers/rss_parser.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating crawlers/rss_parser.py..."
cat << 'PYEOF' > "$BASE/crawlers/rss_parser.py"
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
PYEOF

# ──────────────────────────────────────────────────────────────
# crawlers/web_scraper.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating crawlers/web_scraper.py..."
cat << 'PYEOF' > "$BASE/crawlers/web_scraper.py"
"""
web_scraper.py - Scrape websites via Crawl4AI API

Sends URLs to your Crawl4AI VPS instance and extracts article data.

Usage:
    from crawlers.web_scraper import scrape_website
    articles = scrape_website("https://ethiopianreporter.com/english/", source_id)
"""

import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.text_utils import normalize_url

# Load env
env_paths = [Path(__file__).parent.parent / ".env", Path(__file__).parent.parent.parent / ".env"]
for p in env_paths:
    if p.exists():
        load_dotenv(p)
        break

CRAWL4AI_BASE_URL = os.getenv("CRAWL4AI_BASE_URL", "http://localhost:11235")


def scrape_website(site_url: str, source_id: str) -> list[dict]:
    """
    Scrape a website using Crawl4AI and extract article links + content.

    Step 1: Crawl the main page to find article links
    Step 2: Crawl each article page for full content
    """
    # Step 1: Get article links from the main page
    links = _crawl_for_links(site_url)
    if not links:
        print(f"  [WARN] No article links found on {site_url}")
        return []

    print(f"  Found {len(links)} article links on {site_url}")

    # Step 2: Scrape each article (limit to 20 per run to avoid overloading)
    articles = []
    for link in links[:20]:
        article = _crawl_article(link, source_id)
        if article:
            articles.append(article)

    return articles


def _crawl_for_links(url: str) -> list[str]:
    """Crawl a page and extract article links."""
    try:
        response = requests.post(
            f"{CRAWL4AI_BASE_URL}/crawl",
            json={
                "urls": [url],
                "word_count_threshold": 0,
                "extract_links": True,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        # Extract links from the crawl result
        links = []
        if isinstance(data, dict) and data.get("results"):
            result = data["results"][0] if data["results"] else {}
            # Get links from the page
            page_links = result.get("links", {}).get("internal", [])
            for link_info in page_links:
                href = link_info if isinstance(link_info, str) else link_info.get("href", "")
                if _is_article_link(href, url):
                    links.append(normalize_url(href))

        return list(set(links))  # Deduplicate

    except Exception as e:
        print(f"  [ERROR] Crawl4AI failed for {url}: {e}")
        return []


def _crawl_article(url: str, source_id: str) -> dict | None:
    """Crawl a single article page and extract content."""
    try:
        response = requests.post(
            f"{CRAWL4AI_BASE_URL}/crawl",
            json={
                "urls": [url],
                "word_count_threshold": 50,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict) or not data.get("results"):
            return None

        result = data["results"][0]
        markdown = result.get("markdown", "")
        metadata = result.get("metadata", {})

        title = metadata.get("title", "")
        if not title:
            # Try to extract from first heading in markdown
            match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
            title = match.group(1) if match else ""

        if not title:
            return None

        return {
            "source_id": source_id,
            "title": title[:500],
            "url": url,
            "summary": markdown[:2000] if markdown else None,
            "content": markdown[:50000] if markdown else None,
            "author": metadata.get("author", None),
            "published_at": metadata.get("published_time", None),
        }

    except Exception as e:
        print(f"  [ERROR] Failed to scrape {url}: {e}")
        return None


def _is_article_link(href: str, base_url: str) -> bool:
    """Heuristic to determine if a link is likely an article."""
    if not href or href == base_url:
        return False
    # Must be from the same domain
    if not href.startswith(base_url.rstrip("/")):
        return False
    # Skip common non-article paths
    skip_patterns = [
        "/tag/", "/category/", "/author/", "/page/",
        "/about", "/contact", "/privacy", "/terms",
        "/wp-content/", "/wp-admin/", "/feed",
        ".jpg", ".png", ".pdf", ".xml",
    ]
    href_lower = href.lower()
    if any(p in href_lower for p in skip_patterns):
        return False
    # Article URLs typically have more path segments
    path = href.replace(base_url.rstrip("/"), "")
    if path.count("/") < 1:
        return False
    return True
PYEOF

# ──────────────────────────────────────────────────────────────
# crawlers/crawl_news.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating crawlers/crawl_news.py..."
cat << 'PYEOF' > "$BASE/crawlers/crawl_news.py"
"""
crawl_news.py - Main crawl orchestrator

Fetches all active sources from Supabase, crawls them (RSS or web),
and inserts new articles into the database.

Usage:
    python -m crawlers.crawl_news              # Crawl all active sources
    python -m crawlers.crawl_news --rss-only   # RSS feeds only
    python -m crawlers.crawl_news --web-only   # Web scraping only
"""

import argparse
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import get_active_sources, insert_articles_batch, update_source_last_crawled
from crawlers.rss_parser import parse_rss_feed
from crawlers.web_scraper import scrape_website


def crawl_all(rss_only: bool = False, web_only: bool = False):
    """Crawl all active news sources and insert articles."""
    print("=" * 60)
    print(f"Intel Platform - News Crawler")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    total_new = 0

    # Crawl RSS feeds
    if not web_only:
        rss_sources = get_active_sources(source_type="rss")
        print(f"\n[RSS] {len(rss_sources)} active feeds")

        for source in rss_sources:
            print(f"\n  Crawling: {source['name']} ({source['url'][:60]}...)")
            try:
                articles = parse_rss_feed(source["url"], source["id"])
                print(f"  Parsed: {len(articles)} articles")

                if articles:
                    inserted = insert_articles_batch(articles)
                    new_count = len(inserted)
                    total_new += new_count
                    print(f"  New: {new_count} (skipped {len(articles) - new_count} duplicates)")

                update_source_last_crawled(source["id"])

            except Exception as e:
                print(f"  [ERROR] {source['name']}: {e}")

    # Crawl websites
    if not rss_only:
        web_sources = get_active_sources(source_type="web")
        print(f"\n[WEB] {len(web_sources)} active websites")

        for source in web_sources:
            print(f"\n  Scraping: {source['name']} ({source['url'][:60]}...)")
            try:
                articles = scrape_website(source["url"], source["id"])
                print(f"  Extracted: {len(articles)} articles")

                if articles:
                    inserted = insert_articles_batch(articles)
                    new_count = len(inserted)
                    total_new += new_count
                    print(f"  New: {new_count} (skipped {len(articles) - new_count} duplicates)")

                update_source_last_crawled(source["id"])

            except Exception as e:
                print(f"  [ERROR] {source['name']}: {e}")

    print(f"\n{'=' * 60}")
    print(f"[DONE] Total new articles: {total_new}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rss-only", action="store_true", help="Only crawl RSS feeds")
    parser.add_argument("--web-only", action="store_true", help="Only scrape websites")
    args = parser.parse_args()
    crawl_all(rss_only=args.rss_only, web_only=args.web_only)
PYEOF

# ──────────────────────────────────────────────────────────────
# processors/__init__.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating processors/__init__.py..."
touch "$BASE/processors/__init__.py"

# ──────────────────────────────────────────────────────────────
# processors/auto_tag_articles.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating processors/auto_tag_articles.py..."
cat << 'PYEOF' > "$BASE/processors/auto_tag_articles.py"
"""
auto_tag_articles.py - GPT-4 powered article tagger

Reads untagged articles from Supabase, sends them to GPT-4 for classification,
and writes tags + urgency back to the database.

Usage:
    python -m processors.auto_tag_articles          # Tag up to 50 articles
    python -m processors.auto_tag_articles --limit 10  # Tag up to 10
"""

import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import get_untagged_articles, mark_article_tagged, get_tags_by_names, insert_article_tags
from utils.taxonomies import TOPICS, ACTORS, LOCATIONS, SECTORS

# Load env
env_paths = [Path(__file__).parent.parent / ".env", Path(__file__).parent.parent.parent / ".env"]
for p in env_paths:
    if p.exists():
        load_dotenv(p)
        break

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an article classifier for an Ethiopia-focused news intelligence platform.

Given an article title and summary, classify it by selecting the most relevant tags from each category and assigning an urgency level.

RULES:
- Select 1-5 tags from Topics
- Select 0-3 tags from Actors (only if explicitly mentioned or clearly involved)
- Select 0-3 tags from Locations (only if explicitly mentioned)
- Select 0-2 tags from Sectors
- Assign urgency: "critical" (immediate humanitarian crisis, active conflict), "high" (significant policy change, major funding), "normal" (routine updates), "low" (background info, opinion pieces)

RESPOND ONLY WITH VALID JSON in this exact format:
{
    "topics": ["tag1", "tag2"],
    "actors": ["tag1"],
    "locations": ["tag1"],
    "sectors": ["tag1"],
    "urgency": "normal"
}"""


def build_user_prompt(article: dict) -> str:
    """Build the prompt for GPT-4 with the article and allowed tags."""
    text = f"TITLE: {article['title']}\n"
    if article.get("summary"):
        text += f"SUMMARY: {article['summary'][:1500]}\n"

    text += f"""
ALLOWED TAGS:
Topics: {', '.join(TOPICS)}
Actors: {', '.join(ACTORS)}
Locations: {', '.join(LOCATIONS)}
Sectors: {', '.join(SECTORS)}

Classify this article."""
    return text


def tag_article(article: dict) -> dict | None:
    """Send one article to GPT-4 for tagging. Returns parsed tags or None."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cheaper and fast enough for classification
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(article)},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"  [ERROR] GPT-4 failed for article {article['id']}: {e}")
        return None


def process_untagged(limit: int = 50):
    """Main function: fetch untagged articles, tag them, save results."""
    articles = get_untagged_articles(limit=limit)
    if not articles:
        print("[INFO] No untagged articles found.")
        return

    print(f"[INFO] Tagging {len(articles)} articles...")

    tagged_count = 0
    for i, article in enumerate(articles):
        title_safe = article['title'][:80].encode('ascii', 'replace').decode()
        print(f"  [{i+1}/{len(articles)}] {title_safe}...")

        result = tag_article(article)
        if not result:
            continue

        # Collect all tag names from the result
        all_tag_names = (
            result.get("topics", [])
            + result.get("actors", [])
            + result.get("locations", [])
            + result.get("sectors", [])
        )

        # Look up tag IDs from database
        if all_tag_names:
            tags = get_tags_by_names(all_tag_names)
            tag_ids = [t["id"] for t in tags]
            if tag_ids:
                insert_article_tags(article["id"], tag_ids)

        # Update article urgency and mark as tagged
        urgency = result.get("urgency", "normal")
        if urgency not in ("critical", "high", "normal", "low"):
            urgency = "normal"
        mark_article_tagged(article["id"], urgency)

        tagged_count += 1

    print(f"[DONE] Tagged {tagged_count}/{len(articles)} articles.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    process_untagged(limit=args.limit)
PYEOF

# ──────────────────────────────────────────────────────────────
# processors/generate_posts.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating processors/generate_posts.py..."
cat << 'PYEOF' > "$BASE/processors/generate_posts.py"
"""
generate_posts.py - Generate social media posts from tagged articles

Creates platform-specific posts for TikTok, Telegram, and LinkedIn.
Uses GPT-4 to generate engaging copy.

Usage:
    python -m processors.generate_posts                    # All platforms
    python -m processors.generate_posts --platform telegram  # Single platform
"""

import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import get_articles_without_posts, insert_post, get_client

# Load env
env_paths = [Path(__file__).parent.parent / ".env", Path(__file__).parent.parent.parent / ".env"]
for p in env_paths:
    if p.exists():
        load_dotenv(p)
        break

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PLATFORM_SPECS = {
    "tiktok": {
        "max_chars": 150,
        "max_hashtags": 5,
        "style": "Short, punchy, attention-grabbing. Use emojis. Designed for TikTok caption overlay. Must be under 150 characters (excluding hashtags).",
    },
    "telegram": {
        "max_chars": 1000,
        "max_hashtags": 5,
        "style": "Informative, professional but accessible. Include a brief analysis or key takeaway. Can use bullet points. Include the article link at the end.",
    },
    "linkedin": {
        "max_chars": 700,
        "max_hashtags": 5,
        "style": "Professional, analytical. Start with a hook. Provide context on why this matters for the development/humanitarian sector. Include a call to action or question.",
    },
}

SYSTEM_PROMPT = """You are a social media content creator for an Ethiopia-focused development and humanitarian news platform called "Devidends Intel".

Generate a social media post for the given article and platform. Follow the platform-specific guidelines exactly.

RESPOND ONLY WITH VALID JSON:
{
    "content": "the post text (WITHOUT hashtags)",
    "hashtags": ["tag1", "tag2", "tag3"]
}"""


def generate_post(article: dict, platform: str) -> dict | None:
    """Generate a single post for an article + platform combo."""
    spec = PLATFORM_SPECS[platform]

    user_prompt = f"""ARTICLE:
Title: {article['title']}
Summary: {article.get('summary', 'N/A')[:500]}
Urgency: {article.get('urgency', 'normal')}
URL: {article['url']}

PLATFORM: {platform.upper()}
MAX CHARACTERS: {spec['max_chars']}
MAX HASHTAGS: {spec['max_hashtags']}
STYLE: {spec['style']}

Generate the post."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        content = result.get("content", "")[:spec["max_chars"]]
        hashtags = result.get("hashtags", [])[:spec["max_hashtags"]]

        return {
            "article_id": article["id"],
            "platform": platform,
            "content": content,
            "hashtags": hashtags,
            "status": "draft",
        }

    except Exception as e:
        print(f"  [ERROR] Post generation failed: {e}")
        return None


def generate_for_platform(platform: str, limit: int = 20):
    """Generate posts for all unposted articles on a platform."""
    articles = get_articles_without_posts(platform, limit=limit)
    if not articles:
        print(f"  [{platform.upper()}] No new articles to post about.")
        return

    print(f"  [{platform.upper()}] Generating posts for {len(articles)} articles...")

    created = 0
    for article in articles:
        post = generate_post(article, platform)
        if post:
            insert_post(post)
            created += 1

    print(f"  [{platform.upper()}] Created {created} draft posts.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["tiktok", "telegram", "linkedin"],
                        help="Generate for specific platform only")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    platforms = [args.platform] if args.platform else ["tiktok", "telegram", "linkedin"]

    print("[INFO] Generating social media posts...")
    for platform in platforms:
        generate_for_platform(platform, limit=args.limit)
    print("[DONE]")


if __name__ == "__main__":
    main()
PYEOF

# ──────────────────────────────────────────────────────────────
# processors/publish_to_postiz.py
# ──────────────────────────────────────────────────────────────
echo ">>> Creating processors/publish_to_postiz.py..."
cat << 'PYEOF' > "$BASE/processors/publish_to_postiz.py"
"""
publish_to_postiz.py - Publish draft posts via Postiz API

Takes draft posts from the database and publishes them through Postiz.

Usage:
    python -m processors.publish_to_postiz                    # Publish all drafts
    python -m processors.publish_to_postiz --platform telegram  # Single platform
"""

import os
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import get_client, update_post_status

# Load env
env_paths = [Path(__file__).parent.parent / ".env", Path(__file__).parent.parent.parent / ".env"]
for p in env_paths:
    if p.exists():
        load_dotenv(p)
        break

POSTIZ_API_KEY = os.getenv("POSTIZ_API_KEY")
POSTIZ_BASE_URL = os.getenv("POSTIZ_BASE_URL", "http://31.97.47.190:5000/api")


def publish_post(post: dict) -> bool:
    """Publish a single post via Postiz API."""
    if not POSTIZ_API_KEY:
        print("  [SKIP] No POSTIZ_API_KEY configured. Skipping publish.")
        return False

    # Build hashtag string
    hashtags = post.get("hashtags", [])
    hashtag_str = " ".join(f"#{h.replace(' ', '')}" for h in hashtags) if hashtags else ""

    full_content = f"{post['content']}\n\n{hashtag_str}".strip()

    try:
        response = requests.post(
            f"{POSTIZ_BASE_URL}/posts",
            json={
                "content": full_content,
                "platform": post["platform"],
                "schedule": "now",
            },
            headers={
                "Authorization": f"Bearer {POSTIZ_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code in (200, 201):
            result = response.json()
            postiz_id = result.get("id", "")
            update_post_status(post["id"], "published", str(postiz_id))
            return True
        else:
            print(f"  [ERROR] Postiz returned {response.status_code}: {response.text[:200]}")
            update_post_status(post["id"], "failed")
            return False

    except Exception as e:
        print(f"  [ERROR] Postiz publish failed: {e}")
        update_post_status(post["id"], "failed")
        return False


def publish_drafts(platform: str = None):
    """Publish all draft posts, optionally filtered by platform."""
    query = (
        get_client()
        .table("published_posts")
        .select("*")
        .eq("status", "draft")
    )
    if platform:
        query = query.eq("platform", platform)

    posts = query.order("created_at").limit(50).execute().data

    if not posts:
        print("[INFO] No draft posts to publish.")
        return

    print(f"[INFO] Publishing {len(posts)} draft posts...")

    published = 0
    for post in posts:
        platform_name = post["platform"].upper()
        print(f"  [{platform_name}] Publishing post {post['id'][:8]}...")
        if publish_post(post):
            published += 1

    print(f"[DONE] Published {published}/{len(posts)} posts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["tiktok", "telegram", "linkedin"])
    args = parser.parse_args()
    publish_drafts(platform=args.platform)
PYEOF

# ──────────────────────────────────────────────────────────────
# scripts/pipeline.sh
# ──────────────────────────────────────────────────────────────
echo ">>> Creating scripts/pipeline.sh..."
cat << 'PYEOF' > "$BASE/scripts/pipeline.sh"
#!/bin/bash
# ============================================================
# Intel Platform MVP - Pipeline Orchestrator
#
# Runs the full pipeline: Crawl → Tag → Generate Posts → Publish
#
# Usage:
#   bash scripts/pipeline.sh          # Full pipeline
#   bash scripts/pipeline.sh crawl    # Only crawl
#   bash scripts/pipeline.sh tag      # Only tag
#   bash scripts/pipeline.sh posts    # Only generate posts
#   bash scripts/pipeline.sh publish  # Only publish
#
# Cron (run 2x daily at 6am and 6pm):
#   0 6,18 * * * cd /path/to/intel-platform/backend && bash scripts/pipeline.sh >> /var/log/intel-pipeline.log 2>&1
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

STEP="${1:-all}"

echo "============================================================"
echo "Intel Platform Pipeline - $(date '+%Y-%m-%d %H:%M:%S')"
echo "Step: $STEP"
echo "============================================================"

# Step 1: Crawl news sources
if [ "$STEP" = "all" ] || [ "$STEP" = "crawl" ]; then
    echo ""
    echo ">>> STEP 1: Crawling news sources..."
    python -m crawlers.crawl_news
fi

# Step 2: Auto-tag articles with GPT-4
if [ "$STEP" = "all" ] || [ "$STEP" = "tag" ]; then
    echo ""
    echo ">>> STEP 2: Auto-tagging articles..."
    python -m processors.auto_tag_articles --limit 50
fi

# Step 3: Generate social media posts
if [ "$STEP" = "all" ] || [ "$STEP" = "posts" ]; then
    echo ""
    echo ">>> STEP 3: Generating social posts..."
    python -m processors.generate_posts --limit 20
fi

# Step 4: Publish via Postiz
if [ "$STEP" = "all" ] || [ "$STEP" = "publish" ]; then
    echo ""
    echo ">>> STEP 4: Publishing to social media..."
    python -m processors.publish_to_postiz
fi

echo ""
echo "============================================================"
echo "Pipeline complete - $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
PYEOF
chmod +x "$BASE/scripts/pipeline.sh"

# ──────────────────────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "All files created successfully!"
echo "============================================================"
echo ""
echo "Directory structure:"
echo "  $BASE/"
echo "  ├── .env"
echo "  ├── utils/"
echo "  │   ├── __init__.py"
echo "  │   ├── supabase_client.py"
echo "  │   ├── text_utils.py"
echo "  │   └── taxonomies.py"
echo "  ├── crawlers/"
echo "  │   ├── __init__.py"
echo "  │   ├── rss_parser.py"
echo "  │   ├── web_scraper.py"
echo "  │   └── crawl_news.py"
echo "  ├── processors/"
echo "  │   ├── __init__.py"
echo "  │   ├── auto_tag_articles.py"
echo "  │   ├── generate_posts.py"
echo "  │   └── publish_to_postiz.py"
echo "  └── scripts/"
echo "      └── pipeline.sh"
echo ""
echo "Next steps:"
echo "  1. Install Python dependencies:"
echo "     cd $BASE && pip install python-dotenv supabase openai feedparser requests"
echo "  2. Test the pipeline:"
echo "     cd $BASE && bash scripts/pipeline.sh crawl"
echo ""
