-- Migration: Content Aggregation Tables
-- Description: Creates tables for festival scraping, news aggregation, and AI filtering
-- Date: 2024-12-24

-- ============================================================================
-- DISCOVERED FESTIVALS TABLE (Scraped festivals pending approval)
-- ============================================================================
CREATE TABLE IF NOT EXISTS discovered_festivals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    external_url TEXT,
    description TEXT,
    
    -- Dates
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    submission_deadline TIMESTAMP,
    
    -- Location
    location VARCHAR(255),
    country VARCHAR(100),
    
    -- Classification
    category TEXT[], -- ['feature', 'short', 'documentary']
    genres TEXT[], -- ['drama', 'documentary', 'sci-fi']
    
    -- Financial
    entry_fee DECIMAL(10,2),
    currency VARCHAR(10),
    
    -- AI Analysis
    ai_relevance_score INTEGER, -- 0-100
    is_ai_film_friendly BOOLEAN DEFAULT false,
    prestige_score INTEGER, -- 0-100
    embedding vector(1536), -- OpenAI text-embedding-3-small
    
    -- Source tracking
    source VARCHAR(100), -- 'filmfreeway', 'withoutabox', 'festhome', 'rss'
    source_url TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'duplicate'
    approved_festival_id UUID REFERENCES festivals(id) ON DELETE SET NULL,
    rejection_reason TEXT,
    
    -- Review
    reviewed_at TIMESTAMP,
    reviewed_by UUID,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_discovered_festivals_status ON discovered_festivals(status);
CREATE INDEX IF NOT EXISTS idx_discovered_festivals_source ON discovered_festivals(source);
CREATE INDEX IF NOT EXISTS idx_discovered_festivals_relevance ON discovered_festivals(ai_relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_discovered_festivals_embedding ON discovered_festivals USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- NEWS SOURCES TABLE (RSS feeds and news sources)
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source info
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) DEFAULT 'rss', -- 'rss', 'api', 'scraper'
    
    -- Configuration
    is_active BOOLEAN DEFAULT true,
    fetch_interval_hours INTEGER DEFAULT 6,
    
    -- Tracking
    last_fetched_at TIMESTAMP,
    last_successful_fetch_at TIMESTAMP,
    total_articles_fetched INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_news_sources_active ON news_sources(is_active);
CREATE INDEX IF NOT EXISTS idx_news_sources_type ON news_sources(source_type);

-- ============================================================================
-- NEWS ARTICLES TABLE (Aggregated news articles)
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Article info
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    external_url TEXT NOT NULL UNIQUE,
    image_url TEXT,
    
    -- Author & source
    author VARCHAR(255),
    source_id UUID REFERENCES news_sources(id) ON DELETE SET NULL,
    source_name VARCHAR(255),
    
    -- Classification
    category TEXT[], -- ['festivals', 'technology', 'awards']
    tags TEXT[], -- ['ai', 'cannes', 'filmmaking']
    
    -- AI Analysis
    ai_relevance_score INTEGER, -- 0-100
    is_ai_cinema_relevant BOOLEAN DEFAULT false,
    embedding vector(1536), -- OpenAI text-embedding-3-small
    
    -- Publication
    published_at TIMESTAMP,
    
    -- Status
    is_archived BOOLEAN DEFAULT false,
    archived_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_relevance ON news_articles(ai_relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_news_articles_archived ON news_articles(is_archived);
CREATE INDEX IF NOT EXISTS idx_news_articles_embedding ON news_articles USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- SCRAPING JOBS TABLE (Track scraping job history)
-- ============================================================================
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Job info
    job_type VARCHAR(50) NOT NULL, -- 'festivals', 'news'
    source VARCHAR(100), -- 'filmfreeway', 'variety', 'all'
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    
    -- Results
    items_found INTEGER DEFAULT 0,
    items_new INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_duplicates INTEGER DEFAULT 0,
    items_filtered INTEGER DEFAULT 0,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB,
    
    -- Performance
    duration_seconds INTEGER,
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scraping_jobs_type ON scraping_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_created ON scraping_jobs(created_at DESC);

-- ============================================================================
-- FESTIVAL SOURCES TABLE (Track festival scraping sources)
-- ============================================================================
CREATE TABLE IF NOT EXISTS festival_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source info
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) DEFAULT 'scraper', -- 'scraper', 'rss', 'api'
    
    -- Configuration
    is_active BOOLEAN DEFAULT true,
    scrape_interval_hours INTEGER DEFAULT 24,
    
    -- Tracking
    last_scraped_at TIMESTAMP,
    last_successful_scrape_at TIMESTAMP,
    total_festivals_found INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_festival_sources_active ON festival_sources(is_active);
CREATE INDEX IF NOT EXISTS idx_festival_sources_type ON festival_sources(source_type);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE discovered_festivals IS 'Festivals discovered through scraping, pending admin approval';
COMMENT ON TABLE news_sources IS 'RSS feeds and news sources for content aggregation';
COMMENT ON TABLE news_articles IS 'Aggregated news articles about AI filmmaking and cinema';
COMMENT ON TABLE scraping_jobs IS 'History and status of scraping jobs';
COMMENT ON TABLE festival_sources IS 'Festival scraping sources and their configuration';

-- ============================================================================
-- INITIAL DATA (Default news sources)
-- ============================================================================

INSERT INTO news_sources (name, url, source_type, is_active) VALUES
    ('Variety', 'https://variety.com/feed/', 'rss', true),
    ('The Hollywood Reporter', 'https://www.hollywoodreporter.com/feed/', 'rss', true),
    ('IndieWire', 'https://www.indiewire.com/feed/', 'rss', true),
    ('Screen Daily', 'https://www.screendaily.com/rss/', 'rss', true),
    ('Deadline', 'https://deadline.com/feed/', 'rss', true)
ON CONFLICT (url) DO NOTHING;

-- ============================================================================
-- INITIAL DATA (Default festival sources)
-- ============================================================================

INSERT INTO festival_sources (name, url, source_type, is_active) VALUES
    ('FilmFreeway', 'https://filmfreeway.com/festivals', 'scraper', true),
    ('Withoutabox', 'https://www.withoutabox.com/festivals', 'scraper', false),
    ('Festhome', 'https://festhome.com/en/festivals', 'scraper', true)
ON CONFLICT (url) DO NOTHING;
