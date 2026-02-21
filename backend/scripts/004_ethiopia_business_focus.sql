-- 004_ethiopia_business_focus.sql
-- Refocus platform on Ethiopia business & finance intelligence

-- 1. Clear existing sources and tags
DELETE FROM article_tags;
DELETE FROM articles;
DELETE FROM tags;
DELETE FROM news_sources;

-- 2. Insert Ethiopian and African business news sources
INSERT INTO news_sources (name, source_type, url, is_active, created_at) VALUES
-- Ethiopian Sources (RSS)
('The Capital Ethiopia', 'rss', 'https://capitalethiopia.com/feed', true, NOW()),
('Addis Fortune', 'rss', 'https://addisfortune.news/feed', true, NOW()),
('New Business Ethiopia', 'rss', 'https://newbusinessethiopia.com/feed', true, NOW()),

-- African Business Sources (RSS)
('African Business Magazine', 'rss', 'https://african.business/feed', true, NOW()),
('BBC Africa News', 'rss', 'https://feeds.bbci.co.uk/news/world/africa/rss.xml', true, NOW()),
('BBC Business News', 'rss', 'https://feeds.bbci.co.uk/news/business/rss.xml', true, NOW()),

-- Ethiopian Sources (Web Scraping - for future)
('The Ethiopian Reporter', 'web', 'https://thereporterethiopia.com', false, NOW()),
('Fana Broadcasting', 'web', 'https://fanabc.com/english/', false, NOW()),
('Ethiopian News Agency', 'web', 'https://www.ena.et/web/eng', false, NOW()),

-- Government/Official Sources (Web Scraping - for future)
('National Bank of Ethiopia', 'web', 'https://nbe.gov.et', false, NOW()),
('Central Statistics Agency', 'web', 'https://www.statsethiopia.gov.et', false, NOW()),
('Ministry of Finance', 'web', 'https://www.mofed.gov.et', false, NOW());

-- 3. Insert Ethiopia business-focused tags
-- Topic tags (6 key business themes)
INSERT INTO tags (name, category, created_at) VALUES
('Tax Issues', 'topic', NOW()),
('Investment & M&A', 'topic', NOW()),
('Economy', 'topic', NOW()),
('Public Policy', 'topic', NOW()),
('Business Agreements', 'topic', NOW()),
('Bank News', 'topic', NOW()),

-- Sector tags
('Banking & Finance', 'sector', NOW()),
('Agriculture', 'sector', NOW()),
('Manufacturing', 'sector', NOW()),
('Technology', 'sector', NOW()),
('Real Estate', 'sector', NOW()),
('Telecommunications', 'sector', NOW()),
('Energy & Utilities', 'sector', NOW()),
('Transportation', 'sector', NOW()),
('Retail & Trade', 'sector', NOW()),
('Tourism & Hospitality', 'sector', NOW()),
('Construction', 'sector', NOW()),
('Mining', 'sector', NOW()),

-- Actor tags (key players)
('Government', 'actor', NOW()),
('Central Bank', 'actor', NOW()),
('Commercial Banks', 'actor', NOW()),
('Foreign Investors', 'actor', NOW()),
('Private Sector', 'actor', NOW()),
('State-Owned Enterprises', 'actor', NOW()),
('International Organizations', 'actor', NOW()),
('Regulatory Bodies', 'actor', NOW()),

-- Location tags (Ethiopia-focused)
('Addis Ababa', 'location', NOW()),
('Oromia Region', 'location', NOW()),
('Amhara Region', 'location', NOW()),
('Tigray Region', 'location', NOW()),
('SNNPR', 'location', NOW()),
('Ethiopia (National)', 'location', NOW()),
('East Africa (Regional)', 'location', NOW()),
('Africa (Continental)', 'location', NOW());

-- 4. Add comments for clarity
COMMENT ON TABLE news_sources IS 'Ethiopian and African business news sources focused on 6 key themes';
COMMENT ON TABLE tags IS 'Business-focused taxonomy: topics (6 themes), sectors, actors, locations';
