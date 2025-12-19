# Pull Request Summary: Fix Duplicate Title Creation

## Overview
This PR fixes a critical bug where video uploads were creating duplicate title records in Supabase - one without creator attribution and one with proper attribution.

## Problem Statement
When a creator uploaded a video, **two separate title records** were created:
1. First title at 97% progress: Created with `title_id=None`, missing `uploaded_by` field
2. Second title at 90% progress: Created/updated with proper `title_id` and `uploaded_by`

This caused:
- Creator profiles showing "0 Films" despite successful uploads
- "Untitled Video" placeholders in film lists
- Duplicate films on the homepage
- Lost creator attribution

## Root Cause
The `full_analysis_pipeline.py` was calling `sync_film()` at 97% progress **without** the `title_id` parameter, causing it to create a new title record. Then, `video_tasks.py` would sync again at 90% progress **with** the correct `title_id`.

## Solution

### 1. Removed Duplicate Sync Calls
**File:** `backend/core/full_analysis_pipeline.py`
- ❌ Removed sync at 97% progress (STAGE 11)
- ❌ Removed keyframe upload at 99% progress (STAGE 11.5)
- **Impact:** 52 lines removed, 13 lines added

### 2. Added User ID Tracking
**Files:** 
- `backend/database/migrations/003_add_user_id_to_analysis_jobs.sql`
- `docker/postgres/init.sql`

Added `user_id TEXT` column to `analysis_jobs` table to track who uploaded each video.

### 3. Updated Upload Flow
**File:** `backend/api/upload.py`

Changed:
```python
INSERT INTO analysis_jobs (url, status, priority)
VALUES (:url, 'pending', :priority)
```

To:
```python
INSERT INTO analysis_jobs (url, status, priority, user_id)
VALUES (:url, 'pending', :priority, :user_id)
```

### 4. Updated Analysis Pipeline
**File:** `backend/tasks/video_tasks.py`

- Fetches `user_id` from job data at start of analysis
- Passes `user_id` to Supabase sync
- Ensures proper creator attribution

### 5. Updated Supabase Sync
**File:** `backend/services/supabase_sync.py`

- Includes `uploaded_by` field when creating NEW titles (from `user_id`)
- Does NOT overwrite `uploaded_by` when UPDATING existing titles
- Preserves frontend-set creator attribution

## Changes Summary

### Files Modified (8 files)
```
 FIX_DUPLICATE_TITLES.md                                          | 112 ++++++++++++++++
 backend/api/upload.py                                            |   7 +-
 backend/core/full_analysis_pipeline.py                           |  76 ++--------
 backend/database/migrations/003_add_user_id_to_analysis_jobs.sql |  14 ++
 backend/services/supabase_sync.py                                |  15 ++
 backend/tasks/video_tasks.py                                     |  15 ++
 docker/postgres/init.sql                                         |   1 +
 scripts/apply_migration_003.sh                                   |  43 ++++++
 
 8 files changed, 216 insertions(+), 68 deletions(-)
```

### Commits (5 commits)
1. `6c332a1` - Add user_id tracking and proper uploaded_by handling
2. `e3ad958` - Remove duplicate Supabase sync calls from pipeline
3. `693f66c` - Add migration script and documentation
4. `5c2ac5e` - Address code review feedback
5. `dd6ce28` - Final code review fixes

## Deployment Instructions

### 1. Apply Database Migration
```bash
# Option A: Using migration script
./scripts/apply_migration_003.sh

# Option B: Direct psql
psql -U aicine_user -d aicine -f backend/database/migrations/003_add_user_id_to_analysis_jobs.sql

# Option C: Using Docker
docker exec -i aicine_postgres psql -U aicine_user -d aicine < backend/database/migrations/003_add_user_id_to_analysis_jobs.sql
```

### 2. Restart Services
```bash
docker-compose restart api worker
```

### 3. Verify
```bash
# Check that column was added
psql -U aicine_user -d aicine -c "\d analysis_jobs"

# Should show:
# user_id | text | | |
```

## Testing Checklist

- [ ] Apply database migration
- [ ] Restart services
- [ ] Login as creator
- [ ] Upload a test video
- [ ] Wait for analysis to complete
- [ ] Check Supabase `titles` table - verify only 1 record exists
- [ ] Verify `uploaded_by` field is set to creator's UUID
- [ ] Check creator's profile - verify film count incremented
- [ ] Check homepage - verify no duplicate films
- [ ] Verify no "Untitled Video" placeholders

## Expected Results

After deployment:
- ✅ Only **ONE** title record created per video upload
- ✅ `uploaded_by` field correctly set to creator's UUID
- ✅ Creator's profile shows accurate film count
- ✅ No "Untitled Video" placeholders
- ✅ No duplicate films on homepage
- ✅ Proper creator attribution throughout the system

## Risk Assessment

**Risk Level:** Low
- Changes are surgical and focused
- Only modifies sync behavior, doesn't change core analysis logic
- Database migration is idempotent (uses `IF NOT EXISTS`)
- Backward compatible (missing `user_id` will be NULL, not cause errors)

## Rollback Plan

If issues occur:
1. Revert code changes: `git revert dd6ce28^..dd6ce28`
2. Migration rollback is optional - the `user_id` column can remain without causing issues

## Documentation

- `FIX_DUPLICATE_TITLES.md` - Detailed problem description and solution
- `backend/database/migrations/003_add_user_id_to_analysis_jobs.sql` - Migration SQL
- `scripts/apply_migration_003.sh` - Migration helper script
- Inline code comments explaining logic

## Related Issues

Closes: Issue about duplicate titles and missing creator attribution
