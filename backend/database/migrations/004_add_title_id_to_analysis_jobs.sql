-- Migration: 004_add_title_id_to_analysis_jobs
-- Description: Add title_id column to analysis_jobs table to link with Supabase titles
-- This prevents duplicate title creation by preserving the frontend-created title UUID

-- Add title_id column to analysis_jobs
-- This stores the Supabase title UUID created by the frontend
ALTER TABLE analysis_jobs 
ADD COLUMN IF NOT EXISTS title_id TEXT;

-- Add index for title_id lookups
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_title_id ON analysis_jobs(title_id);

-- Comment
COMMENT ON COLUMN analysis_jobs.title_id IS 'UUID of the title in Supabase (from frontend upload or backend creation)';
