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
