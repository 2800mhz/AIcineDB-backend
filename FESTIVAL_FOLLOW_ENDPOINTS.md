# Festival Follow Endpoints Documentation

## Overview
This document describes the festival follow/unfollow functionality endpoints.

## Endpoints

### 1. Follow a Festival
Follow a festival to receive updates.

**Endpoint:** `POST /api/festivals/{festival_id}/follow`

**Authentication:** Required (Bearer token)

**Parameters:**
- `festival_id` (path): UUID of the festival

**Response:**
```json
{
  "message": "Festival followed successfully",
  "follow": {
    "festival_id": "uuid",
    "user_id": "uuid",
    "followed_at": "2024-01-20T10:00:00Z"
  }
}
```

**Error Cases:**
- `400 Bad Request`: Already following this festival
- `401 Unauthorized`: Not authenticated
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X POST https://api.example.com/api/festivals/abc-123/follow \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2. Unfollow a Festival
Stop following a festival.

**Endpoint:** `DELETE /api/festivals/{festival_id}/follow`

**Authentication:** Required (Bearer token)

**Parameters:**
- `festival_id` (path): UUID of the festival

**Response:**
```json
{
  "message": "Festival unfollowed successfully"
}
```

**Error Cases:**
- `401 Unauthorized`: Not authenticated
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X DELETE https://api.example.com/api/festivals/abc-123/follow \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3. Check Following Status (NEW)
Check if the current user is following a specific festival.

**Endpoint:** `GET /api/festivals/{festival_id}/following`

**Authentication:** Optional (returns false if not authenticated)

**Parameters:**
- `festival_id` (path): UUID of the festival

**Response:**
```json
{
  "is_following": true
}
```

**Error Cases:**
- `500 Internal Server Error`: Server error

**Example:**
```bash
# Authenticated request
curl https://api.example.com/api/festivals/abc-123/following \
  -H "Authorization: Bearer YOUR_TOKEN"

# Unauthenticated request (returns is_following: false)
curl https://api.example.com/api/festivals/abc-123/following
```

**Notes:**
- If no authentication token is provided, returns `{"is_following": false}`
- This endpoint is useful for UI components to show the current follow state

---

### 4. List Festival Followers
Get a list of users following a festival.

**Endpoint:** `GET /api/festivals/{festival_id}/followers`

**Authentication:** Not required

**Parameters:**
- `festival_id` (path): UUID of the festival
- `skip` (query, optional): Number of records to skip (default: 0)
- `limit` (query, optional): Number of records to return (default: 50, max: 100)

**Response:**
```json
{
  "followers": [
    {
      "festival_id": "uuid",
      "user_id": "uuid",
      "followed_at": "2024-01-20T10:00:00Z"
    }
  ],
  "count": 1,
  "skip": 0,
  "limit": 50
}
```

**Example:**
```bash
curl https://api.example.com/api/festivals/abc-123/followers?limit=20
```

---

## Date Validation

### Creating a Festival
When creating a festival, the following date validations are enforced:

1. **Festival dates:**
   - `end_date` must be after `start_date`

2. **Submission dates (if provided):**
   - `submission_end_date` must be after `submission_start_date`
   - `submission_end_date` must be before or equal to `start_date`

**Example of valid dates:**
```json
{
  "name": "AI Cinema Festival 2024",
  "slug": "ai-cinema-2024",
  "start_date": "2024-06-01T00:00:00Z",
  "end_date": "2024-06-07T00:00:00Z",
  "submission_start_date": "2024-03-01T00:00:00Z",
  "submission_end_date": "2024-05-31T00:00:00Z"
}
```

**Error Response (invalid dates):**
```json
{
  "detail": "End date must be after start date"
}
```

or

```json
{
  "detail": "Submission deadline must be before festival start date"
}
```

---

## Frontend Integration Examples

### React/Vue Example
```javascript
// Check if user is following
const checkFollowingStatus = async (festivalId) => {
  const response = await fetch(
    `/api/festivals/${festivalId}/following`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  const data = await response.json();
  return data.is_following;
};

// Follow festival
const followFestival = async (festivalId) => {
  const response = await fetch(
    `/api/festivals/${festivalId}/follow`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    if (response.status === 400) {
      console.log('Already following');
    } else {
      throw new Error(error.detail);
    }
  }
  
  return await response.json();
};

// Unfollow festival
const unfollowFestival = async (festivalId) => {
  const response = await fetch(
    `/api/festivals/${festivalId}/follow`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
};
```

---

## Database Constraints

The following CHECK constraints are enforced at the database level:

```sql
-- Festival dates
CONSTRAINT festivals_date_check 
  CHECK (end_date > start_date)

-- Submission dates
CONSTRAINT festivals_submission_date_check 
  CHECK (
    submission_start_date IS NULL OR 
    submission_end_date IS NULL OR 
    submission_end_date > submission_start_date
  )

-- Submission deadline before festival
CONSTRAINT festivals_submission_before_start_check 
  CHECK (
    submission_end_date IS NULL OR 
    start_date IS NULL OR 
    submission_end_date <= start_date
  )
```

These constraints ensure data integrity even if application-level validation is bypassed.
