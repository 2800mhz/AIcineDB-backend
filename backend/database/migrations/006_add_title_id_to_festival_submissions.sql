-- Migration: Add title_id support to festival_submissions
-- Description: Allow festival_submissions to reference Supabase titles table
-- Date: 2026-01-02

-- Add title_id column (UUID) to reference Supabase titles
-- This allows festival submissions to work with both:
-- 1. Local films table (film_id INTEGER)
-- 2. Supabase titles table (title_id UUID)

ALTER TABLE festival_submissions
ADD COLUMN IF NOT EXISTS title_id UUID;

-- Add is_winner column to mark festival winners
ALTER TABLE festival_submissions
ADD COLUMN IF NOT EXISTS is_winner BOOLEAN DEFAULT false;

-- Create index for title_id lookups
CREATE INDEX IF NOT EXISTS idx_festival_submissions_title ON festival_submissions(title_id);

-- Modify the unique constraint to support both film_id and title_id
-- Drop old constraint
ALTER TABLE festival_submissions 
DROP CONSTRAINT IF EXISTS festival_submissions_festival_id_film_id_key;

-- Add partial unique constraints (only when the ID is not null)
CREATE UNIQUE INDEX IF NOT EXISTS unique_festival_film 
ON festival_submissions(festival_id, film_id) 
WHERE film_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unique_festival_title
ON festival_submissions(festival_id, title_id) 
WHERE title_id IS NOT NULL;

-- Make film_id nullable since we now support title_id as alternative
ALTER TABLE festival_submissions 
ALTER COLUMN film_id DROP NOT NULL;

-- Add check constraint to ensure at least one of film_id or title_id is provided
ALTER TABLE festival_submissions
ADD CONSTRAINT check_film_or_title CHECK (
    (film_id IS NOT NULL AND title_id IS NULL) OR 
    (film_id IS NULL AND title_id IS NOT NULL)
);

COMMENT ON COLUMN festival_submissions.title_id IS 'Reference to Supabase titles table (alternative to film_id)';
COMMENT ON COLUMN festival_submissions.is_winner IS 'Whether this submission won an award/category';
