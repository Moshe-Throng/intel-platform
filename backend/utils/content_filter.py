"""
content_filter.py - Ethiopia content relevance filter

Filters articles to ensure they're relevant to Ethiopian business intelligence.
"""

# Keywords that indicate Ethiopia relevance
ETHIOPIA_KEYWORDS = [
    "ethiopia", "ethiopian", "addis ababa", "ababa", "oromia", "amhara",
    "tigray", "snnpr", "dire dawa", "harari", "afar", "somali region",
    "sidama", "benishangul", "gambella",
    "birr", "nbe", "national bank of ethiopia",
    "ethiopian airlines", "ethio telecom", "ethiopian electric",
    "ministry of finance ethiopia", "ethiopian investment commission"
]

# Global business topics that are relevant to Ethiopia
GLOBAL_BUSINESS_KEYWORDS = [
    # Only keep if directly mentions Ethiopia
    # These alone won't trigger relevance, but combined with Ethiopia keywords they reinforce it
]

def is_ethiopia_relevant(article: dict) -> bool:
    """
    Check if an article is relevant to Ethiopian business intelligence.

    Args:
        article: Dict with 'title' and optionally 'summary' or 'content'

    Returns:
        True if article contains Ethiopia keywords, False otherwise
    """
    # Combine all searchable text
    searchable_text = " ".join([
        article.get("title", ""),
        article.get("summary", ""),
        article.get("content", "")[:500],  # First 500 chars of content
    ]).lower()

    # Check if any Ethiopia keyword is present
    for keyword in ETHIOPIA_KEYWORDS:
        if keyword in searchable_text:
            return True

    return False


def filter_articles(articles: list[dict]) -> list[dict]:
    """
    Filter a list of articles to keep only Ethiopia-relevant ones.

    Args:
        articles: List of article dicts

    Returns:
        Filtered list of articles
    """
    filtered = [article for article in articles if is_ethiopia_relevant(article)]
    return filtered
