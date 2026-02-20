-- ============================================================
-- Intel Platform MVP - Seed Data
-- Initial news sources and tag taxonomy
-- Run AFTER 001_create_tables.sql
-- ============================================================

-- ============================================================
-- NEWS SOURCES (Ethiopia / Development / Humanitarian)
-- ============================================================

INSERT INTO news_sources (name, url, source_type) VALUES
    -- RSS Feeds (verified working)
    ('ReliefWeb - Ethiopia', 'https://reliefweb.int/updates/rss.xml?advanced-search=%28PC87%29', 'rss'),
    ('UN OCHA Ethiopia (SitReps)', 'https://reliefweb.int/updates/rss.xml?advanced-search=%28PC87%29_%28F10%29', 'rss'),
    ('WHO Africa', 'https://www.afro.who.int/rss/featured-news.xml', 'rss'),
    ('WHO Africa Emergencies', 'https://www.afro.who.int/rss/emergencies.xml', 'rss'),
    ('Devex', 'https://www.devex.com/news/feed.rss', 'rss'),
    ('The New Humanitarian', 'https://www.thenewhumanitarian.org/feed', 'rss'),
    ('IRIN News', 'https://www.irinnews.org/rss.xml', 'rss'),
    ('Addis Standard', 'https://addisstandard.com/feed/', 'rss'),
    ('Ethiopian Monitor', 'https://ethiopianmonitor.com/feed/', 'rss'),
    -- Web scraping targets (Borkena, World Bank have no working RSS)
    ('Ethiopian Reporter', 'https://www.ethiopianreporter.com/english/', 'web'),
    ('Capital Ethiopia', 'https://www.capitalethiopia.com/', 'web'),
    ('Borkena', 'https://borkena.com/', 'web')
ON CONFLICT (url) DO NOTHING;


-- ============================================================
-- TAGS - Topics
-- ============================================================

INSERT INTO tags (name, category) VALUES
    -- Topics
    ('Humanitarian Aid', 'topic'),
    ('Food Security', 'topic'),
    ('Health', 'topic'),
    ('Education', 'topic'),
    ('Climate Change', 'topic'),
    ('Conflict', 'topic'),
    ('Displacement', 'topic'),
    ('Governance', 'topic'),
    ('Economic Development', 'topic'),
    ('Gender Equality', 'topic'),
    ('Water & Sanitation', 'topic'),
    ('Agriculture', 'topic'),
    ('Infrastructure', 'topic'),
    ('Human Rights', 'topic'),
    ('Elections', 'topic'),
    ('Peace & Security', 'topic'),
    ('Refugees', 'topic'),
    ('Child Protection', 'topic'),
    ('Nutrition', 'topic'),
    ('Funding & Grants', 'topic'),

    -- Actors
    ('UN', 'actor'),
    ('USAID', 'actor'),
    ('World Bank', 'actor'),
    ('African Union', 'actor'),
    ('EU', 'actor'),
    ('WHO', 'actor'),
    ('UNICEF', 'actor'),
    ('WFP', 'actor'),
    ('UNHCR', 'actor'),
    ('ICRC', 'actor'),
    ('Government of Ethiopia', 'actor'),
    ('African Development Bank', 'actor'),
    ('DFID/FCDO', 'actor'),
    ('Gates Foundation', 'actor'),
    ('Save the Children', 'actor'),

    -- Locations
    ('Addis Ababa', 'location'),
    ('Tigray', 'location'),
    ('Amhara', 'location'),
    ('Oromia', 'location'),
    ('Somali Region', 'location'),
    ('SNNPR', 'location'),
    ('Afar', 'location'),
    ('Sidama', 'location'),
    ('Benishangul-Gumuz', 'location'),
    ('Gambella', 'location'),
    ('Dire Dawa', 'location'),
    ('Harari', 'location'),

    -- Sectors
    ('NGO', 'sector'),
    ('Government', 'sector'),
    ('Private Sector', 'sector'),
    ('Multilateral', 'sector'),
    ('Bilateral', 'sector'),
    ('Academia', 'sector'),
    ('Media', 'sector'),
    ('Civil Society', 'sector')
ON CONFLICT (name) DO NOTHING;
