-- docker/postgres/init.sql
-- ============================================================================
-- AICineDB PostgreSQL Initialization Script
-- ============================================================================

-- Create user if it doesn't exist (PostgreSQL 9.1+)
DO
$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'aicine_user') THEN
    CREATE USER aicine_user WITH PASSWORD 'aicine_pass';
  END IF;
END
$$;

-- Grant CREATEDB privilege to the user
ALTER ROLE aicine_user CREATEDB;

-- Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE aicine TO aicine_user;

-- ============================================================================
-- ✅ CREATE EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- ============================================================================
-- ✅ CREATE analysis_jobs TABLE
-- ============================================================================

-- Create sequence
CREATE SEQUENCE IF NOT EXISTS analysis_jobs_id_seq;

-- Create table
CREATE TABLE IF NOT EXISTS public.analysis_jobs (
  id bigint NOT NULL DEFAULT nextval('analysis_jobs_id_seq':: regclass),
  url text NOT NULL,
  status character varying NOT NULL DEFAULT 'pending',
  priority integer DEFAULT 5,
  progress double precision DEFAULT 0.0,
  current_stage text,
  film_id bigint,
  error_message text,
  created_at timestamp with time zone DEFAULT now(),
  started_at timestamp with time zone,
  completed_at timestamp with time zone,
  updated_at timestamp with time zone DEFAULT now(),
  celery_task_id text,
  user_id uuid,
  title_id uuid,
  CONSTRAINT analysis_jobs_pkey PRIMARY KEY (id)
);

-- Grant permissions
GRANT ALL ON public.analysis_jobs TO aicine_user;
GRANT ALL ON SEQUENCE analysis_jobs_id_seq TO aicine_user;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_title_id ON public.analysis_jobs(title_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON public.analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_user_id ON public.analysis_jobs(user_id);

-- ============================================================================
-- ✅ SUCCESS MESSAGE
-- ============================================================================
DO $$ 
BEGIN
  RAISE NOTICE '================================================';
  RAISE NOTICE '✅ AICineDB Database Initialized Successfully';
  RAISE NOTICE '✅ Extensions:  uuid-ossp, pgvector';
  RAISE NOTICE '✅ Table: analysis_jobs';
  RAISE NOTICE '================================================';
END $$;