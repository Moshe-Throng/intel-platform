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
