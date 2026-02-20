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
