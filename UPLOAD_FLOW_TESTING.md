# Upload Flow Testing Guide

## Overview
This document provides a comprehensive testing guide for the new upload flow that fixes the duplicate title creation issue.

## Problem Statement
**Before:** Creator film upload created TWO separate rows:
1. Frontend creates title in Supabase (`uploaded_by: user_id`, `status: pending`)
2. Backend creates its own title (`uploaded_by: NULL`, `status: completed`)

**Result:** 47+ duplicate entries, creators page shows 0 films!

## Solution
The new upload flow ensures only ONE title row is created and updated throughout the process.

---

## Test Cases

### Test Case 1: Upload with Pre-Created Title (Preferred Flow)

**Setup:**
1. Ensure you have a creator account
2. Login to frontend
3. Have a valid video URL ready

**Steps:**
1. Frontend creates title in Supabase:
   ```javascript
   const { data: titleData, error } = await supabase
     .from("titles")
     .insert({
       title: "Untitled Video",
       status: "pending",
       type: "movie",
       uploaded_by: user.id
     })
     .select()
     .single();
   ```

2. Send upload request to backend:
   ```bash
   curl -X POST http://localhost:8000/api/upload \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "url": "https://www.youtube.com/watch?v=VIDEO_ID",
       "title_id": "abc-123-456"
     }'
   ```

**Expected Response:**
```json
{
  "job_id": 123,
  "status": "pending",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "created_at": "2024-12-19T16:00:00Z",
  "celery_task_id": "task-uuid",
  "progress": 0.0
}
```

**Verification:**
```sql
-- Check in Supabase
SELECT id, title, status, uploaded_by 
FROM titles 
WHERE id = 'abc-123-456';
```

**Expected Database State:**
- After upload: `status = 'processing'`, `uploaded_by = user-xyz`
- After analysis: `status = 'completed'`, `uploaded_by = user-xyz` (preserved!)
- Count: **EXACTLY ONE ROW**

---

### Test Case 2: Upload without Title ID (Backward Compatibility)

**Steps:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }'
```

**Expected Response:**
Same as Test Case 1

**Verification:**
```sql
-- Check newly created title
SELECT id, title, status, uploaded_by 
FROM titles 
ORDER BY created_at DESC 
LIMIT 1;
```

**Expected Database State:**
- Title created by backend with `uploaded_by = user_id`
- Count: **ONE NEW ROW**

---

### Test Case 3: Unauthorized Access

**Steps:**
1. Try to upload to another user's title:
   ```bash
   curl -X POST http://localhost:8000/api/upload \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "url": "https://www.youtube.com/watch?v=VIDEO_ID",
       "title_id": "another-users-title-id"
     }'
   ```

**Expected Response:**
```json
{
  "detail": "Not authorized to analyze this title"
}
```
**Status Code:** 403

---

### Test Case 4: Missing Title

**Steps:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "title_id": "non-existent-uuid"
  }'
```

**Expected Response:**
```json
{
  "detail": "Title non-existent-uuid not found in database"
}
```
**Status Code:** 404

---

### Test Case 5: Analysis Failure

**Steps:**
1. Upload with invalid video URL
2. Let analysis fail

**Verification:**
```sql
SELECT id, status, moderator_notes 
FROM titles 
WHERE id = 'your-title-id';
```

**Expected Database State:**
- `status = 'failed'`
- `moderator_notes` contains error message (truncated to 500 chars)
- `uploaded_by` still preserved

---

### Test Case 6: Non-Creator User

**Steps:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer REGULAR_USER_TOKEN" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }'
```

**Expected Response:**
```json
{
  "detail": "Creator access required. Please upgrade your account."
}
```
**Status Code:** 403

---

## Integration Points

### Frontend Integration
```typescript
// src/pages/UploadContent.tsx
const handleUpload = async (videoUrl: string) => {
  // 1. Create title
  const { data: titleData, error: titleError } = await supabase
    .from("titles")
    .insert({
      title: "Untitled Video",
      status: "pending",
      type: "movie",
      uploaded_by: user.id,
    })
    .select()
    .single();

  // 2. Send to backend
  const response = await fetch(`${apiUrl}/api/upload`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${session.data.session?.access_token}`,
    },
    body: JSON.stringify({
      url: videoUrl,
      title_id: titleData.id,  // ✅ Include title_id
    }),
  });

  const result = await response.json();
  navigate(`/title/${titleData.id}`);
};
```

### Backend Flow
```
POST /api/upload
    ↓
verify_creator_or_admin (auth)
    ↓
get_supabase_client()
    ↓
if title_id:
    verify_title_exists()
    verify_ownership()
    update_status('processing')
else:
    create_new_title()
    ↓
create_analysis_job()
    ↓
analyze_film_complete.delay(job_id, url, title_id)
    ↓
[Celery Task]
    analyze_video()
    update_title('completed')  # preserves uploaded_by
    ↓
RESULT: ONE title row ✅
```

---

## Success Criteria Checklist

After running all tests, verify:

- [ ] ✅ Upload creates ONE title row (not two)
- [ ] ✅ `uploaded_by` field is preserved throughout
- [ ] ✅ Creators page shows correct film count
- [ ] ✅ Profile page shows user's films
- [ ] ✅ No duplicate titles in Supabase
- [ ] ✅ Failed analysis sets status to 'failed'
- [ ] ✅ Admin can upload to any title
- [ ] ✅ Non-creators are blocked
- [ ] ✅ Authorization checks work correctly

---

## Monitoring & Debugging

### Backend Logs
Look for these log messages:
```
✅ Using existing title_id from frontend: abc-123
📝 Found existing title: Film Name
✅ Updated title abc-123 status to 'processing'
✅ Analysis job created with ID: 123
🎬 Analysis task started: task-uuid
✅ Updated existing title abc-123 with analysis results
```

### Supabase Queries
```sql
-- Check for duplicates
SELECT uploaded_by, COUNT(*) as count
FROM titles
WHERE uploaded_by IS NOT NULL
GROUP BY uploaded_by
HAVING COUNT(*) > 1;

-- Check status distribution
SELECT status, COUNT(*) 
FROM titles 
GROUP BY status;

-- Check orphaned titles (no uploaded_by)
SELECT COUNT(*) 
FROM titles 
WHERE uploaded_by IS NULL;
```

### Common Issues

**Issue:** Title not updating
- Check if title_id is being sent correctly
- Verify auth token is valid
- Check Supabase connection

**Issue:** Duplicate titles still appearing
- Verify frontend is sending title_id
- Check backend logs for "Using existing title_id"
- Ensure old upload code is not being used

**Issue:** uploaded_by is NULL
- Check if using old /api/analyze endpoint
- Verify frontend creates title first
- Confirm title_id is passed to backend

---

## API Documentation

### POST /api/upload

**Description:** Upload video URL for AI analysis

**Authentication:** Required (Creator or Admin)

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "title_id": "abc-123-456",  // Optional, recommended
  "priority": 5  // Optional, default: 5
}
```

**Response:**
```json
{
  "job_id": 123,
  "status": "pending",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "created_at": "2024-12-19T16:00:00Z",
  "celery_task_id": "task-uuid",
  "progress": 0.0
}
```

**Status Codes:**
- `200` - Success
- `401` - Unauthorized (invalid or missing token)
- `403` - Forbidden (not creator/admin or not your title)
- `404` - Title not found
- `500` - Server error

---

### GET /api/upload/status/{task_id}

**Description:** Get status of upload/analysis task

**Authentication:** Not required

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "PROGRESS",
  "progress": 45,
  "message": "Analyzing narrative..."
}
```

**Task States:**
- `PENDING` - Task queued
- `PROGRESS` - Task running
- `SUCCESS` - Task completed
- `FAILURE` - Task failed

---

## Migration Notes

### For Existing Data
If you have duplicate titles from the old flow:

```sql
-- Identify duplicates
WITH duplicates AS (
  SELECT 
    t1.id as keep_id,
    t2.id as delete_id
  FROM titles t1
  JOIN titles t2 ON t1.uploaded_by = t2.uploaded_by
  WHERE t1.id < t2.id
    AND t1.uploaded_by IS NOT NULL
    AND t2.uploaded_by IS NULL
)
SELECT * FROM duplicates;

-- Manual cleanup (review first!)
-- DELETE FROM titles WHERE id IN (SELECT delete_id FROM duplicates);
```

### Deployment Checklist
- [ ] Deploy backend with new upload endpoint
- [ ] Update frontend to use new flow
- [ ] Test with staging environment
- [ ] Monitor for duplicates after deployment
- [ ] Clean up existing duplicates if any

---

## Notes

1. The `title_id` parameter is **optional** but **highly recommended**
2. Backend supports backward compatibility (creating title if no title_id)
3. The `uploaded_by` field is **never** modified by the analysis task
4. Admin users can analyze any title
5. Regular creators can only analyze their own titles
6. Failed analyses set `status = 'failed'` and include error in `moderator_notes`

---

## Version Info
- **Created:** 2024-12-19
- **Backend Version:** 2.0.0
- **Related Files:**
  - `backend/api/upload.py` (new)
  - `backend/tasks/video_tasks.py` (updated)
  - `backend/api/main.py` (updated)
