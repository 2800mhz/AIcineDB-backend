# Fix for Duplicate Title Creation Issue

## Problem
When a creator uploaded a video, **two separate title records** were being created in Supabase:

1. **First title** (during analysis at 97% progress):
   - Created with `title_id=None`
   - Missing `uploaded_by` field (no creator attribution)

2. **Second title** (during sync at 90% progress):
   - Created/updated with proper `title_id` from frontend
   - Has correct `uploaded_by` field

### User Impact
- Creator's profile page showed "0 Films" even though films were analyzed
- "Untitled Video" placeholders appeared in creator's film list
- Duplicate films appeared on the homepage (one with creator attribution, one without)

## Solution

### Changes Made

1. **Removed Duplicate Sync Calls** (`backend/core/full_analysis_pipeline.py`)
   - Removed Supabase sync at 97% progress that created duplicates without `uploaded_by`
   - Removed redundant keyframe upload at 99% progress
   - All syncing now happens in one place with proper `title_id`

2. **Added User ID Tracking** (`backend/database/migrations/003_add_user_id_to_analysis_jobs.sql`)
   - Added `user_id` column to `analysis_jobs` table
   - Stores the uploader's user ID with each analysis job
   - Updated database schema in `docker/postgres/init.sql`

3. **Updated Upload Endpoint** (`backend/api/upload.py`)
   - Now stores authenticated user's ID in the analysis job
   - Passes `user_id` through the entire analysis pipeline

4. **Updated Analysis Pipeline** (`backend/tasks/video_tasks.py`)
   - Fetches `user_id` from job data at the start of analysis
   - Passes `user_id` through to Supabase sync
   - Ensures proper creator attribution

5. **Updated Supabase Sync** (`backend/services/supabase_sync.py`)
   - Includes `uploaded_by` field when creating new titles
   - Does NOT overwrite `uploaded_by` when updating existing titles
   - Preserves creator attribution set by the frontend

## Migration

If you have an existing database, run the migration:

```bash
./scripts/apply_migration_003.sh
```

Or manually apply:

```bash
psql -U aicine_user -d aicine -f backend/database/migrations/003_add_user_id_to_analysis_jobs.sql
```

Or if using Docker:

```bash
docker exec -i aicine_postgres psql -U aicine_user -d aicine < backend/database/migrations/003_add_user_id_to_analysis_jobs.sql
```

## Expected Result

After these changes:
- ✅ Only **ONE** title record created per video upload
- ✅ `uploaded_by` field correctly set to creator's UUID
- ✅ Creator's profile shows correct film count
- ✅ No more "Untitled Video" placeholders
- ✅ No duplicate films on homepage

## Testing Steps

1. Login as a creator account
2. Upload a video via "Upload Content"
3. Wait for analysis to complete
4. Check Supabase `titles` table → should have **only 1** record for the film
5. Check creator's profile page → film count should increment
6. Check homepage → no duplicate films

## Technical Details

### Before
```
[Analysis Pipeline at 97%] → sync_film(title_id=None) → Creates duplicate title ❌
[Video Tasks at 90%]        → sync_film(title_id=UUID) → Updates correct title ✅
```

### After
```
[Analysis Pipeline at 97%] → (NO SYNC - removed)
[Video Tasks at 90%]        → sync_film(title_id=UUID, user_id=UUID) → One title, correct attribution ✅
```

## Files Modified

- `backend/api/upload.py` - Store user_id in analysis job
- `backend/core/full_analysis_pipeline.py` - Remove duplicate sync calls
- `backend/database/migrations/003_add_user_id_to_analysis_jobs.sql` - Add user_id column
- `backend/services/supabase_sync.py` - Handle uploaded_by field correctly
- `backend/tasks/video_tasks.py` - Pass user_id through pipeline
- `docker/postgres/init.sql` - Update schema for new deployments
- `scripts/apply_migration_003.sh` - Migration helper script
