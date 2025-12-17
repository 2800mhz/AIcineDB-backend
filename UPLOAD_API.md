# Video Upload API Documentation

## Overview

The video upload endpoint allows authenticated creators and admins to upload videos for AI analysis. This endpoint creates a title record in Supabase and initiates the analysis pipeline.

## Endpoint

```
POST /api/upload
```

## Authentication

**Required:** Yes (Bearer token)

**Roles:** `creator` or `admin`

The endpoint uses the `verify_creator_or_admin` dependency to ensure only authorized users can upload videos.

## Request

### Content-Type
```
multipart/form-data
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video_url` | string | Yes | URL of the video to analyze (YouTube, Vimeo, direct link, etc.) |
| `video_title` | string | No | Title for the video (defaults to "Untitled") |
| `priority` | integer | No | Analysis priority 1-10 (default: 5, higher = more priority) |

### Example Request

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "video_url=https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  -F "video_title=Never Gonna Give You Up" \
  -F "priority=7"
```

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('video_url', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
formData.append('video_title', 'Never Gonna Give You Up');
formData.append('priority', '7');

const response = await fetch('http://localhost:8000/api/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${yourJwtToken}`
  },
  body: formData
});

const result = await response.json();
console.log('Job ID:', result.job_id);
console.log('Status:', result.status);
```

## Response

### Success (200 OK)

```json
{
  "job_id": 123,
  "status": "pending",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "created_at": "2024-12-17T15:30:00.000Z",
  "celery_task_id": "abc123-def456-ghi789"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | integer | Analysis job ID - use this to track progress |
| `status` | string | Job status ("pending", "processing", "completed", "failed") |
| `url` | string | The video URL that was submitted |
| `created_at` | string | ISO 8601 timestamp when the job was created |
| `celery_task_id` | string | Celery task ID for tracking the background task |

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Invalid authentication token"
}
```

**Cause:** Missing or invalid JWT token

### 403 Forbidden

```json
{
  "detail": "Creator access required. Please upgrade your account."
}
```

**Cause:** User is not a creator or admin

### 500 Internal Server Error

```json
{
  "detail": "Failed to create title in database"
}
```

**Cause:** Database error or Supabase connection issue

## Process Flow

1. **Authentication Check**
   - Verifies JWT token
   - Checks user has `creator` or `admin` role

2. **Title Creation**
   - Creates title record in Supabase `titles` table
   - Sets `uploaded_by` field to current user's UUID
   - Generates URL-friendly slug from title
   - Sets status to "pending"

3. **Analysis Job Creation**
   - Creates job record in local `analysis_jobs` table
   - Stores video URL and priority

4. **Task Initiation**
   - Starts Celery background task
   - Passes `title_id` to task for linking

5. **Analysis Process**
   - Downloads video
   - Extracts frames
   - Analyzes cinematography, audio, narrative
   - Updates title with results
   - Uploads frames to Supabase storage

## Tracking Progress

After uploading, use the returned `job_id` to track progress:

```bash
curl "http://localhost:8000/api/jobs/123"
```

Response:
```json
{
  "job_id": 123,
  "status": "processing",
  "progress": 0.65,
  "current_stage": "🎨 Analyzing visual style...",
  "film_id": null,
  "created_at": "2024-12-17T15:30:00.000Z"
}
```

## Important Notes

### Database Schema

⚠️ **Critical:** The Supabase `titles` table uses `uploaded_by` field, **NOT** `creator_id`. 

This was the root cause of the original bug. Always use `uploaded_by` when creating or updating titles.

### RLS Policies

The endpoint respects Supabase Row Level Security (RLS) policies:

```sql
-- Example RLS policy for titles table
CREATE POLICY "Creators and admins can insert titles" 
ON public.titles
FOR INSERT 
WITH CHECK (
  auth.uid() = uploaded_by AND
  EXISTS (
    SELECT 1 FROM public.profiles 
    WHERE id = auth.uid() 
    AND role IN ('creator', 'admin')
  )
);
```

### Slug Generation

The endpoint automatically generates URL-friendly slugs from titles:
- Converts to lowercase
- Replaces spaces with hyphens
- Removes special characters
- Handles empty titles (defaults to "untitled")

### Priority Levels

Priority affects job queue ordering:
- **1-3**: Low priority
- **4-6**: Normal priority (default: 5)
- **7-10**: High priority

## Testing

Use the provided test script to verify the endpoint:

```bash
# With authentication token
export JWT_TOKEN="your_jwt_token_here"

curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "video_url=https://www.youtube.com/watch?v=jNQXAC9IVRw" \
  -F "video_title=Test Video" \
  -F "priority=5"
```

## Related Endpoints

- `GET /api/jobs/{job_id}` - Check analysis status
- `GET /api/films/{film_id}` - Get analysis results
- `POST /api/analyze` - Alternative analysis endpoint (no title creation)

## Troubleshooting

### "Failed to create title in database"

**Solutions:**
1. Check Supabase connection (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`)
2. Verify RLS policies allow the user to insert
3. Check that `uploaded_by` field exists in schema

### "Creator access required"

**Solutions:**
1. Verify user's role in Supabase `profiles` table
2. Check JWT token includes role in `user_metadata`
3. Ensure user is authenticated

### Task not starting

**Solutions:**
1. Check Celery worker is running
2. Verify Redis connection
3. Check Celery logs for errors

## See Also

- [API Documentation](API_DOCUMENTATION.md)
- [Main README](README.md)
- [Setup Guide](SETUP_WINDOWS.md)
