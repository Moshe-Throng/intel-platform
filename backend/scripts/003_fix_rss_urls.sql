-- ============================================================
-- Fix broken RSS feed URLs + add new working sources
-- Run in Supabase SQL Editor
-- ============================================================

-- Fix ReliefWeb URL
UPDATE news_sources SET url = 'https://reliefweb.int/updates/rss.xml?advanced-search=%28PC87%29'
WHERE name = 'ReliefWeb - Ethiopia';

-- Fix UN OCHA → use ReliefWeb SitReps filter
UPDATE news_sources SET url = 'https://reliefweb.int/updates/rss.xml?advanced-search=%28PC87%29_%28F10%29',
    name = 'UN OCHA Ethiopia (SitReps)'
WHERE name = 'UN OCHA Ethiopia';

-- Fix WHO → use regional feed
UPDATE news_sources SET url = 'https://www.afro.who.int/rss/featured-news.xml',
    name = 'WHO Africa'
WHERE name = 'WHO Ethiopia';

-- Fix Devex URL
UPDATE news_sources SET url = 'https://www.devex.com/news/feed.rss'
WHERE name = 'Devex';

-- Remove World Bank (no working RSS) and Borkena RSS (broken)
UPDATE news_sources SET is_active = false
WHERE name IN ('World Bank - Ethiopia', 'Borkena');

-- Add new working sources
INSERT INTO news_sources (name, url, source_type) VALUES
    ('WHO Africa Emergencies', 'https://www.afro.who.int/rss/emergencies.xml', 'rss'),
    ('Borkena', 'https://borkena.com/', 'web')
ON CONFLICT (url) DO NOTHING;
