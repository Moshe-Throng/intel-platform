"""
publish_to_postiz.py - Publish draft posts via Postiz API

Takes draft posts from the database and publishes them through Postiz.

Usage:
    python -m processors.publish_to_postiz                    # Publish all drafts
    python -m processors.publish_to_postiz --platform telegram  # Single platform
"""

import os
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime, timezone
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
POSTIZ_BASE_URL = os.getenv("POSTIZ_BASE_URL", "http://localhost:5000/api")

_integration_cache = {}


def get_integration_id(platform: str) -> str | None:
    """Look up the Postiz integration ID for a given platform."""
    if _integration_cache:
        return _integration_cache.get(platform)

    try:
        resp = requests.get(
            f"{POSTIZ_BASE_URL}/public/v1/integrations",
            headers={"Authorization": POSTIZ_API_KEY},
            timeout=15,
        )
        if resp.status_code == 200:
            for integ in resp.json():
                _integration_cache[integ["identifier"]] = integ["id"]
        return _integration_cache.get(platform)
    except Exception as e:
        print(f"  [ERROR] Failed to fetch integrations: {e}")
        return None


def publish_post(post: dict) -> bool:
    """Publish a single post via Postiz API."""
    if not POSTIZ_API_KEY:
        print("  [SKIP] No POSTIZ_API_KEY configured.")
        return False

    platform = post["platform"]
    integration_id = get_integration_id(platform)
    if not integration_id:
        print(f"  [SKIP] No Postiz integration for '{platform}'. Connect it in Postiz first.")
        return False

    hashtags = post.get("hashtags", [])
    hashtag_str = " ".join(f"#{h.replace(' ', '')}" for h in hashtags) if hashtags else ""
    full_content = f"{post['content']}\n\n{hashtag_str}".strip()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    try:
        response = requests.post(
            f"{POSTIZ_BASE_URL}/public/v1/posts",
            json={
                "type": "now",
                "date": now_iso,
                "shortLink": False,
                "tags": [],
                "posts": [
                    {
                        "integration": {"id": integration_id},
                        "value": [{"content": full_content, "image": []}],
                        "settings": {"__type": platform},
                    }
                ],
            },
            headers={
                "Authorization": POSTIZ_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code in (200, 201):
            result = response.json()
            postiz_id = result[0].get("postId", "") if isinstance(result, list) else result.get("id", "")
            update_post_status(post["id"], "published", str(postiz_id))
            return True
        elif response.status_code == 429:
            print("  [RATE-LIMITED] Waiting 120s...")
            time.sleep(120)
            return False
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

    posts = query.order("created_at").limit(25).execute().data

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
        time.sleep(3)

    print(f"[DONE] Published {published}/{len(posts)} posts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["tiktok", "telegram", "linkedin"])
    args = parser.parse_args()
    publish_drafts(platform=args.platform)
