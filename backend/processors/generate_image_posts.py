"""
generate_image_posts.py - Generate professional image posts for Telegram

Creates branded news graphics with templates for each category.

Usage:
    python -m processors.generate_image_posts --limit 5
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import get_unpublished_posts

# Load env
env_paths = [Path(__file__).parent.parent / ".env", Path(__file__).parent.parent.parent / ".env"]
for p in env_paths:
    if p.exists():
        load_dotenv(p)
        break

# Color schemes by category
CATEGORY_COLORS = {
    "Tax Issues": {"primary": "#1B4B8C", "accent": "#D4AF37"},
    "Investment & M&A": {"primary": "#0D3B66", "accent": "#00B4D8"},
    "Economy": {"primary": "#003049", "accent": "#F77F00"},
    "Public Policy": {"primary": "#2C3E50", "accent": "#E74C3C"},
    "Business Agreements": {"primary": "#16423C", "accent": "#6A9C89"},
    "Bank News": {"primary": "#1A1A2E", "accent": "#16C79A"},
    "default": {"primary": "#1B3A52", "accent": "#4A90E2"}
}

# Output directory for generated images
OUTPUT_DIR = Path(__file__).parent.parent / ".tmp" / "post_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines


def create_news_graphic(post: dict, output_path: Path):
    """
    Generate a professional news graphic similar to the bskilled format.

    Args:
        post: Dict with 'title', 'content', 'tags', etc.
        output_path: Where to save the PNG
    """
    # Canvas size (optimized for Telegram)
    width, height = 1200, 1600

    # Determine color scheme from primary tag
    primary_tag = post.get("tags", ["default"])[0] if post.get("tags") else "default"
    colors = CATEGORY_COLORS.get(primary_tag, CATEGORY_COLORS["default"])

    # Create image
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Try to load fonts (fallback to default if not available)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_date = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_date = ImageFont.load_default()

    # Header bar
    draw.rectangle([(0, 0), (width, 120)], fill=colors["primary"])

    # Brand name (top left)
    draw.text((50, 35), "intel", fill="white", font=font_header)

    # "TODAY'S NEWS" section
    draw.rectangle([(30, 150), (width - 30, 240)], outline=colors["primary"], width=5)
    draw.text((50, 165), "TODAY'S NEWS", fill=colors["primary"], font=font_header)

    # Category badge (if available)
    if post.get("tags"):
        category = post["tags"][0]
        badge_y = 280
        draw.rectangle([(30, badge_y), (width - 30, badge_y + 100)], fill=colors["accent"])

        # Wrap category name if needed
        category_lines = wrap_text(category.upper(), font_body, width - 100, draw)
        category_text = "\n".join(category_lines[:2])  # Max 2 lines
        draw.text((50, badge_y + 20), category_text, fill="white", font=font_body)

    # Title section
    title_y = 420
    title_text = post.get("title", "No title")[:200]  # Limit length
    title_lines = wrap_text(title_text, font_title, width - 100, draw)

    for i, line in enumerate(title_lines[:3]):  # Max 3 lines
        draw.text((50, title_y + i * 70), line, fill=colors["primary"], font=font_title)

    # Body section (two columns like the example)
    body_y = title_y + 250
    body_text = post.get("content", "")[:600]  # Limit to ~600 chars

    # Split into two columns
    col_width = (width - 120) // 2
    col1_x = 50
    col2_x = col1_x + col_width + 20

    # Column 1
    col1_lines = wrap_text(body_text[:300], font_body, col_width, draw)
    for i, line in enumerate(col1_lines[:15]):  # Max 15 lines
        draw.text((col1_x, body_y + i * 45), line, fill="#333333", font=font_body)

    # Column 2
    col2_lines = wrap_text(body_text[300:], font_body, col_width, draw)
    for i, line in enumerate(col2_lines[:15]):  # Max 15 lines
        draw.text((col2_x, body_y + i * 45), line, fill="#333333", font=font_body)

    # Footer section
    footer_y = height - 150
    draw.rectangle([(0, footer_y), (width, height)], fill=colors["primary"])

    # Source/Country
    draw.text((50, footer_y + 30), "ethiopia", fill="white", font=font_body)

    # Date
    date_str = datetime.now().strftime("%d/%m/%Y")
    draw.text((width - 300, footer_y + 30), date_str, fill="white", font=font_body)

    # Hashtags (if available)
    hashtags = " ".join([f"#{tag.replace(' ', '')}" for tag in post.get("tags", [])[:3]])
    draw.text((50, footer_y + 85), hashtags, fill=colors["accent"], font=font_date)

    # Save image
    img.save(output_path, "PNG", quality=95)
    print(f"  Generated: {output_path.name}")


def generate_images(limit: int = 10):
    """Generate image posts for unpublished articles."""
    posts = get_unpublished_posts(platform="telegram", limit=limit)

    if not posts:
        print("[INFO] No unpublished posts found.")
        return

    print(f"[INFO] Generating {len(posts)} image posts...\n")

    generated_count = 0
    for i, post in enumerate(posts):
        title_safe = post['title'][:60].encode('ascii', 'replace').decode()
        print(f"  [{i+1}/{len(posts)}] {title_safe}...")

        # Generate filename
        filename = f"post_{post['id']}.png"
        output_path = OUTPUT_DIR / filename

        try:
            create_news_graphic(post, output_path)
            generated_count += 1
        except Exception as e:
            print(f"    [ERROR] Failed to generate image: {e}")

    print(f"\n[DONE] Generated {generated_count} images in {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Max posts to generate")
    args = parser.parse_args()

    generate_images(limit=args.limit)
