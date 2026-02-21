"""
taxonomies.py - Tag definitions for GPT-4 auto-tagging

These lists are passed to GPT-4 as the allowed tag vocabulary.
Must match what's seeded in the tags table.

Focus: Ethiopia business & finance intelligence
"""

# Primary business topics (6 key themes)
TOPICS = [
    "Tax Issues",
    "Investment & M&A",
    "Economy",
    "Public Policy",
    "Business Agreements",
    "Bank News",
]

# Business sectors
SECTORS = [
    "Banking & Finance",
    "Agriculture",
    "Manufacturing",
    "Technology",
    "Real Estate",
    "Telecommunications",
    "Energy & Utilities",
    "Transportation",
    "Retail & Trade",
    "Tourism & Hospitality",
    "Construction",
    "Mining",
]

# Key actors in Ethiopian business
ACTORS = [
    "Government",
    "Central Bank",
    "Commercial Banks",
    "Foreign Investors",
    "Private Sector",
    "State-Owned Enterprises",
    "International Organizations",
    "Regulatory Bodies",
]

# Locations (Ethiopia-focused)
LOCATIONS = [
    "Addis Ababa",
    "Oromia Region",
    "Amhara Region",
    "Tigray Region",
    "SNNPR",
    "Ethiopia (National)",
    "East Africa (Regional)",
    "Africa (Continental)",
]

ALL_TAGS = TOPICS + SECTORS + ACTORS + LOCATIONS
