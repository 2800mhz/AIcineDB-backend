-- Migration: 001_create_film_cast
-- Description: Create film_cast table for cast and crew storage
-- Note: This table is already defined in docker/postgres/init.sql for new deployments
-- This migration file is for documentation and manual database updates

-- Create film_cast table (if not exists for backward compatibility)
CREATE TABLE IF NOT EXISTS film_cast (
    id SERIAL PRIMARY KEY,
    film_id INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255),
    type VARCHAR(50) NOT NULL DEFAULT 'actor' CHECK (type IN ('actor', 'crew')),
    department VARCHAR(100),
    screen_time FLOAT,
    appearance_count INTEGER,
    ordering INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_film_cast_film_id ON film_cast(film_id);
CREATE INDEX IF NOT EXISTS idx_film_cast_type ON film_cast(type);
CREATE INDEX IF NOT EXISTS idx_film_cast_ordering ON film_cast(film_id, ordering);

-- Comment
COMMENT ON TABLE film_cast IS 'Stores cast and crew members for analyzed films';
