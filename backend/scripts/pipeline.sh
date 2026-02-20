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
