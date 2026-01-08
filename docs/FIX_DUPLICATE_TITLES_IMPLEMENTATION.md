# Fix for Duplicate Title Creation Issue

## Problem Statement

When a user uploads a video:
1. **Frontend creates** a title record with UUID (e.g., `d4e7f2de`) with `uploaded_by=NULL`
2. **Backend analysis completes** and creates a **NEW** title record (e.g., `66feeb47`) with `uploaded_by={user_id}`

This causes **duplicate entries** for the same video.

## Root Cause

The `title_id` created by the frontend was being passed to the Celery task but was **not being stored** in the `analysis_jobs` table. This meant:

1. The `title_id` was passed as a Celery task parameter
2. If the task was restarted or retrieved from the database, the `title_id` was lost
3. Without persistent storage, the backend couldn't reliably update the existing title

## Solution

### Changes Made

#### 1. Database Migration (004_add_title_id_to_analysis_jobs.sql)

Added `title_id` column to the `analysis_jobs` table:

```sql
ALTER TABLE analysis_jobs 
ADD COLUMN IF NOT EXISTS title_id TEXT;

CREATE INDEX IF NOT EXISTS idx_analysis_jobs_title_id ON analysis_jobs(title_id);

COMMENT ON COLUMN analysis_jobs.title_id IS 'UUID of the title in Supabase (from frontend upload or backend creation)';
```

#### 2. Upload API Update (backend/api/upload.py)

Modified the job creation to store the `title_id`:

```python
job = await db.fetch_one(
    query="""
    INSERT INTO analysis_jobs (url, status, priority, user_id, title_id)
    VALUES (:url, 'pending', :priority, :user_id, :title_id)
    RETURNING *
    """,
    values={
        "url": str(request.url),
        "priority": request.priority or 5,
        "user_id": user_id,
        "title_id": title_id  # ✅ Now storing title_id
    }
)
```

#### 3. Video Tasks Fallback Logic (backend/tasks/video_tasks.py)

Added fallback to retrieve `title_id` from database if not provided as parameter:

```python
# If title_id not provided as parameter, try to get it from job data
if not title_id:
    title_id = job_data.get('title_id')
    if title_id:
        logger.info(f"📋 Retrieved title_id from job: {title_id}")
    else:
        logger.warning("⚠️ No title_id found - a new title will be created in Supabase")
else:
    logger.info(f"📋 Using title_id from task parameter: {title_id}")
```

#### 4. Schema Updates (docker/postgres/init.sql)

Updated the initial schema for new installations:

```sql
CREATE TABLE IF NOT EXISTS analysis_jobs (
    ...
    user_id TEXT,  -- UUID of uploader from Supabase profiles table
    title_id TEXT,  -- UUID of title in Supabase (from frontend upload or backend creation)
    ...
);

CREATE INDEX idx_jobs_title_id ON analysis_jobs(title_id);
```

#### 5. Migration Script (scripts/apply_migration_004.sh)

Created a bash script to apply the migration to existing databases:

```bash
#!/bin/bash
# Apply migration 004_add_title_id_to_analysis_jobs.sql
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"
```

## Expected Behavior After Fix

1. Frontend creates title `abc-123` with `uploaded_by=user123`
2. Frontend sends upload request with `title_id='abc-123'`
3. Backend creates `analysis_jobs` record with `title_id='abc-123'`
4. Backend analyzes video
5. Backend retrieves `title_id` from job data (or uses task parameter)
6. Backend calls `sync_film(title_id='abc-123')`
7. Supabase **UPDATES** existing record instead of creating new one
8. Result: **One title** with proper `uploaded_by` field

## Migration Instructions

### For Existing Databases

Run the migration script:

```bash
# Set database connection environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=aicine
export DB_USER=aicine_user
export DB_PASSWORD=your_password

# Run the migration
./scripts/apply_migration_004.sh
```

### For New Installations

The `title_id` column will be created automatically when running the `init.sql` script.

### For Docker Deployments

If using Docker, the migration will need to be applied to the running container:

```bash
docker exec -it postgres_container psql -U aicine_user -d aicine -f /path/to/004_add_title_id_to_analysis_jobs.sql
```

## Testing Checklist

- [ ] Apply migration to development database
- [ ] Upload a video as a creator user
- [ ] Verify `analysis_jobs` table has `title_id` populated
- [ ] Wait for analysis to complete
- [ ] Verify only ONE title exists in Supabase for that video
- [ ] Verify `uploaded_by` field contains the creator's user ID
- [ ] Verify "by [username]" attribution appears on frontend

## Files Modified

1. `backend/database/migrations/004_add_title_id_to_analysis_jobs.sql` (new)
2. `backend/api/upload.py` (modified)
3. `backend/tasks/video_tasks.py` (modified)
4. `docker/postgres/init.sql` (modified)
5. `scripts/apply_migration_004.sh` (new)

## Security Review

✅ **Code Review**: Passed with no issues
✅ **CodeQL Security Scan**: Passed with 0 vulnerabilities

## Notes

- The change is backward compatible - existing jobs without `title_id` will continue to work (new titles will be created)
- The migration uses `ADD COLUMN IF NOT EXISTS` to be idempotent
- The index on `title_id` improves lookup performance
- Proper logging has been added to track `title_id` flow through the system
