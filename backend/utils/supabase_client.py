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


def get_unpublished_posts(platform: str = "telegram", limit: int = 10) -> list[dict]:
    """
    Fetch draft posts with enriched article data for image generation.
    Returns posts with: id, title, content, tags (list of topic names).
    """
    # Get draft posts
    posts = (
        get_client()
        .table("published_posts")
        .select("id, article_id, content, hashtags, platform")
        .eq("platform", platform)
        .eq("status", "draft")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )

    if not posts:
        return []

    # Enrich each post with article data and tags
    enriched = []
    for post in posts:
        # Get article title and summary
        article = (
            get_client()
            .table("articles")
            .select("id, title, summary, url")
            .eq("id", post["article_id"])
            .execute()
            .data
        )

        if not article:
            continue  # Skip if article deleted

        article = article[0]

        # Get topic tags (for category colors in image)
        article_tags = (
            get_client()
            .table("article_tags")
            .select("tag_id")
            .eq("article_id", article["id"])
            .execute()
            .data
        )

        tag_names = []
        if article_tags:
            tag_ids = [t["tag_id"] for t in article_tags]
            tags = (
                get_client()
                .table("tags")
                .select("name, category")
                .in_("id", tag_ids)
                .eq("category", "topic")  # Only topic tags (Tax, Investment, etc.)
                .execute()
                .data
            )
            tag_names = [t["name"] for t in tags]

        # Combine post + article data for image template
        enriched.append({
            "id": post["id"],
            "article_id": article["id"],
            "title": article["title"],
            "content": post["content"],
            "summary": article.get("summary", ""),
            "url": article["url"],
            "tags": tag_names,  # For category colors
            "hashtags": post.get("hashtags", []),
            "platform": post["platform"]
        })

    return enriched
