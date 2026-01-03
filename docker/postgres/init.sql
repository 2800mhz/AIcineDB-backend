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

-- Create database if it doesn't exist (will be created by POSTGRES_DB env var)
-- But grant privileges on it
GRANT ALL PRIVILEGES ON DATABASE aicine TO aicine_user;