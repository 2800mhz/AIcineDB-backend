-- Migration: Add festival film fields to Supabase titles table
-- Description: Fields to support festival film scraping and display
-- Date: 2026-01-02
-- NOTE: This migration should be run in Supabase SQL Editor

-- Add festival-related fields to titles table
ALTER TABLE titles
ADD COLUMN IF NOT EXISTS festival_source_url TEXT,
ADD COLUMN IF NOT EXISTS festival_category VARCHAR(100),
ADD COLUMN IF NOT EXISTS is_festival_film BOOLEAN DEFAULT false;

-- Create indexes for filtering festival films
CREATE INDEX IF NOT EXISTS idx_titles_is_festival_film ON titles(is_festival_film);
CREATE INDEX IF NOT EXISTS idx_titles_festival_source_url ON titles(festival_source_url);

-- Comments
COMMENT ON COLUMN titles.festival_source_url IS 'Source URL of the festival showcase page (e.g., https://aiff.runwayml.com/2024)';
COMMENT ON COLUMN titles.festival_category IS 'Award category (e.g., Grand Prix, Gold, Silver, Merit, Honoree)';
COMMENT ON COLUMN titles.is_festival_film IS 'Flag indicating if this is a festival-selected film';
