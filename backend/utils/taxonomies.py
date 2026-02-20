"""
taxonomies.py - Tag definitions for GPT-4 auto-tagging

These lists are passed to GPT-4 as the allowed tag vocabulary.
Must match what's seeded in the tags table.
"""

TOPICS = [
    "Humanitarian Aid", "Food Security", "Health", "Education",
    "Climate Change", "Conflict", "Displacement", "Governance",
    "Economic Development", "Gender Equality", "Water & Sanitation",
    "Agriculture", "Infrastructure", "Human Rights", "Elections",
    "Peace & Security", "Refugees", "Child Protection", "Nutrition",
    "Funding & Grants",
]

ACTORS = [
    "UN", "USAID", "World Bank", "African Union", "EU", "WHO",
    "UNICEF", "WFP", "UNHCR", "ICRC", "Government of Ethiopia",
    "African Development Bank", "DFID/FCDO", "Gates Foundation",
    "Save the Children",
]

LOCATIONS = [
    "Addis Ababa", "Tigray", "Amhara", "Oromia", "Somali Region",
    "SNNPR", "Afar", "Sidama", "Benishangul-Gumuz", "Gambella",
    "Dire Dawa", "Harari",
]

SECTORS = [
    "NGO", "Government", "Private Sector", "Multilateral",
    "Bilateral", "Academia", "Media", "Civil Society",
]

ALL_TAGS = TOPICS + ACTORS + LOCATIONS + SECTORS
