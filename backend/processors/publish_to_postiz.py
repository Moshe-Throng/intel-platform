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
