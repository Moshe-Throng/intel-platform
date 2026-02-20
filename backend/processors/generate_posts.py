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
