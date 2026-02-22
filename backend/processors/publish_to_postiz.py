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
import base64
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import get_client, update_post_status

# Directory where generated images are stored
IMAGE_DIR = Path(__file__).parent.parent / ".tmp" / "post_images"

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


def upload_image_to_postiz(image_path: Path) -> str | None:
    """Upload an image to Postiz and return the media ID/URL."""
    try:
        # Read image and convert to base64
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode()

        # Upload to Postiz media endpoint
        response = requests.post(
            f"{POSTIZ_BASE_URL}/public/v1/media",
            json={"file": f"data:image/png;base64,{image_data}"},
            headers={
                "Authorization": POSTIZ_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code in (200, 201):
            result = response.json()
            return result.get("id") or result.get("url")
        else:
            print(f"  [WARN] Image upload failed ({response.status_code}), posting text only")
            return None

    except Exception as e:
        print(f"  [WARN] Image upload error: {e}, posting text only")
        return None


def publish_post(post: dict, use_images: bool = True) -> bool:
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

    # Check for generated image
    images = []
    if use_images:
        image_path = IMAGE_DIR / f"post_{post['id']}.png"
        if image_path.exists():
            print(f"    Using image: {image_path.name}")
            # Read and encode image directly (no separate upload)
            try:
                with open(image_path, "rb") as img_file:
                    image_data = base64.b64encode(img_file.read()).decode()
                    # Postiz/Telegram expects raw base64 data, NOT data URI format
                    images = [{
                        "id": image_path.name,
                        "path": image_path.name,
                        "File": image_data  # Just base64, no "data:image/png;base64," prefix
                    }]
            except Exception as e:
                print(f"    [WARN] Image read failed: {e}")

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
                        "value": [{"content": full_content, "image": images}],
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


def publish_drafts(platform: str = None, use_images: bool = True):
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

    mode = "IMAGE" if use_images else "TEXT"
    print(f"[INFO] Publishing {len(posts)} draft posts ({mode} mode)...\n")

    published = 0
    for post in posts:
        platform_name = post["platform"].upper()
        print(f"  [{platform_name}] Publishing post {post['id'][:8]}...")
        if publish_post(post, use_images=use_images):
            published += 1
            print(f"    ✓ Published successfully")
        time.sleep(3)

    print(f"\n[DONE] Published {published}/{len(posts)} posts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["tiktok", "telegram", "linkedin"])
    parser.add_argument("--text-only", action="store_true", help="Post text only (no images)")
    args = parser.parse_args()
    publish_drafts(platform=args.platform, use_images=not args.text_only)
