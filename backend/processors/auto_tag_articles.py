"""
auto_tag_articles.py - GPT-4 powered article tagger

Reads untagged articles from Supabase, sends them to GPT-4 for classification,
and writes tags + urgency back to the database.

Focus: Ethiopia business & finance intelligence with 6 key themes

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

SYSTEM_PROMPT = """You are an article classifier for an Ethiopia business & finance intelligence platform.

Given an article title and summary, classify it by selecting the most relevant tags from each category and assigning an urgency level.

FOCUS: Ethiopian business news covering these 6 key topics:
1. Tax Issues - tax policy, reforms, compliance, revenue collection
2. Investment & M&A - foreign/domestic investment, mergers, acquisitions, privatization
3. Economy - GDP, inflation, trade, economic policy, macroeconomic indicators
4. Public Policy - regulations, government reforms, business environment, licensing
5. Business Agreements - partnerships, treaties, trade deals, contracts
6. Bank News - banking sector news, NBE policy, financial services, lending

RULES:
- Select 1-3 tags from Topics (the 6 key business topics above)
- Select 0-2 tags from Actors (government, central bank, banks, investors, etc.)
- Select 0-2 tags from Locations (Ethiopian regions or broader geographic scope)
- Select 0-2 tags from Sectors (industries involved)
- Assign urgency: "critical" (major policy change, financial crisis, market shock), "high" (significant business impact, major deals), "normal" (routine business news), "low" (background info, opinion)

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

Classify this business article."""
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
