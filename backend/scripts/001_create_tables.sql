-- ============================================================
-- Intel Platform MVP - Database Schema
-- Single-tenant, no RLS, no multi-tenancy
-- Run this in Supabase SQL Editor (supabase.com/dashboard)
-- ============================================================

-- 1. NEWS SOURCES
-- Tracks RSS feeds and websites we crawl
CREATE TABLE IF NOT EXISTS news_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,                          -- e.g. "ReliefWeb", "Devex"
    url TEXT NOT NULL UNIQUE,                    -- RSS feed or website URL
    source_type TEXT NOT NULL DEFAULT 'rss'      -- 'rss' or 'web'
        CHECK (source_type IN ('rss', 'web')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    crawl_frequency_hours INT NOT NULL DEFAULT 12,
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. ARTICLES
-- Main content table - every crawled article lands here
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES news_sources(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,                    -- Dedup key
    summary TEXT,                                -- GPT-generated or extracted
    content TEXT,                                -- Full article text
    author TEXT,
    published_at TIMESTAMPTZ,
    crawled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_tagged BOOLEAN NOT NULL DEFAULT false,    -- Has GPT processed it?
    urgency TEXT DEFAULT 'normal'                -- 'critical', 'high', 'normal', 'low'
        CHECK (urgency IN ('critical', 'high', 'normal', 'low')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. TAGS
-- Taxonomy of topics, actors, locations
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'topic'       -- 'topic', 'actor', 'location', 'sector'
        CHECK (category IN ('topic', 'actor', 'location', 'sector')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. ARTICLE_TAGS (junction table)
CREATE TABLE IF NOT EXISTS article_tags (
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,               -- GPT confidence score (0-1)
    PRIMARY KEY (article_id, tag_id)
);

-- 5. PUBLISHED POSTS
-- Tracks social media posts generated and published via Postiz
CREATE TABLE IF NOT EXISTS published_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    platform TEXT NOT NULL                       -- 'tiktok', 'telegram', 'linkedin'
        CHECK (platform IN ('tiktok', 'telegram', 'linkedin')),
    content TEXT NOT NULL,                       -- The generated post text
    hashtags TEXT[],                             -- Array of hashtags
    status TEXT NOT NULL DEFAULT 'draft'         -- 'draft', 'scheduled', 'published', 'failed'
        CHECK (status IN ('draft', 'scheduled', 'published', 'failed')),
    postiz_post_id TEXT,                         -- ID from Postiz API
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- INDEXES for performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_crawled_at ON articles(crawled_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_urgency ON articles(urgency);
CREATE INDEX IF NOT EXISTS idx_articles_is_tagged ON articles(is_tagged);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_article_tags_article ON article_tags(article_id);
CREATE INDEX IF NOT EXISTS idx_article_tags_tag ON article_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category);
CREATE INDEX IF NOT EXISTS idx_published_posts_article ON published_posts(article_id);
CREATE INDEX IF NOT EXISTS idx_published_posts_platform ON published_posts(platform);
CREATE INDEX IF NOT EXISTS idx_published_posts_status ON published_posts(status);
CREATE INDEX IF NOT EXISTS idx_news_sources_active ON news_sources(is_active);


-- ============================================================
-- FULL-TEXT SEARCH on articles (for the search page)
-- ============================================================

ALTER TABLE articles ADD COLUMN IF NOT EXISTS fts tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_articles_fts ON articles USING GIN(fts);
