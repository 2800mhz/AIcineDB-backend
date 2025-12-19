-- Migration: 003_add_user_id_to_analysis_jobs
-- Description: Add user_id column to analysis_jobs table to track who uploaded the video
-- This enables proper creator attribution and prevents duplicate titles

-- Add user_id column to analysis_jobs
-- Note: We're not adding a foreign key constraint since this references Supabase profiles table
ALTER TABLE analysis_jobs 
ADD COLUMN IF NOT EXISTS user_id TEXT;

-- Add index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_user_id ON analysis_jobs(user_id);

-- Comment
COMMENT ON COLUMN analysis_jobs.user_id IS 'UUID of the user who uploaded the video (from Supabase profiles table)';
