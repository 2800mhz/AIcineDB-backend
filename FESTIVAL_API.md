# Festival API Documentation

## Overview

The Festival API provides endpoints for creating and managing film festivals, submitting films to festivals, and managing festival events.

## Authentication

All festival endpoints require authentication via JWT token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

### User Roles

- **Admin**: Full access to all features, can approve/reject festival applications
- **Creator**: Can create festivals (requires approval), submit films, and manage their own festivals
- **Regular User**: Cannot access festival creation features

## Endpoints

### Festival CRUD

#### Create Festival

**POST** `/api/festivals`

**Auth Required**: Creator or Admin

**Request Body**:
```json
{
  "name": "AI Cinema International Festival 2024",
  "slug": "ai-cinema-2024",
  "description": "Annual festival celebrating AI-generated films",
  "tagline": "The Future of Cinema",
  "start_date": "2024-06-01T00:00:00Z",
  "end_date": "2024-06-07T00:00:00Z",
  "location": "Istanbul, Turkey",
  "venue": "Digital Arts Center",
  "categories": ["short", "feature", "experimental"],
  "genres": ["sci-fi", "drama", "documentary"],
  "submission_end_date": "2024-05-01T00:00:00Z",
  "website": "https://aicinemafest.com",
  "contact_email": "info@aicinemafest.com"
}
```

**Response**:
- Admin: Creates festival with `status: "approved"` immediately
- Creator: Creates festival with `status: "pending"` (requires admin approval)

#### List Festivals

**GET** `/api/festivals?filter=active&skip=0&limit=20`

**Auth Required**: No

**Query Parameters**:
- `filter`: `active`, `upcoming`, `past`, `approved`, `pending` (default: `approved`)
- `skip`: Pagination offset (default: 0)
- `limit`: Results per page (default: 20, max: 100)

**Response**:
```json
{
  "festivals": [...],
  "count": 10,
  "skip": 0,
  "limit": 20
}
```

#### Get Festival Details

**GET** `/api/festivals/{festival_id}`

**Auth Required**: No

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "AI Cinema International Festival 2024",
  "slug": "ai-cinema-2024",
  "status": "approved",
  "is_creator_festival": false,
  "created_by": "user-uuid",
  "created_at": "2024-01-20T10:00:00Z",
  "total_submissions": 42,
  "total_followers": 128,
  ...
}
```

#### Update Festival

**PUT** `/api/festivals/{festival_id}`

**Auth Required**: Festival owner, organizer, or admin

**Request Body**: Partial update (only include fields to update)
```json
{
  "description": "Updated description",
  "submission_end_date": "2024-05-15T00:00:00Z"
}
```

#### Delete Festival

**DELETE** `/api/festivals/{festival_id}`

**Auth Required**: Admin only

### Festival Applications (Creator → Admin)

#### List Applications

**GET** `/api/festivals/applications`

**Auth Required**: Creator or Admin
- Creator: See only their own applications
- Admin: See all applications

#### Get Application Details

**GET** `/api/festivals/applications/{application_id}`

**Auth Required**: Application owner or admin

#### Approve Application

**POST** `/api/festivals/applications/{application_id}/approve`

**Auth Required**: Admin only

**Query Parameter**:
- `admin_notes`: Optional feedback for creator

**Response**: Creates the festival and updates application status

#### Reject Application

**POST** `/api/festivals/applications/{application_id}/reject`

**Auth Required**: Admin only

**Query Parameter**:
- `admin_notes`: Reason for rejection

### Film Submissions

#### Submit Film to Festival

**POST** `/api/festivals/{festival_id}/submissions`

**Auth Required**: Creator

**Request Body**:
```json
{
  "film_id": 123,
  "category": "short",
  "notes": "This is my debut AI-generated film"
}
```

#### List Festival Submissions

**GET** `/api/festivals/{festival_id}/submissions?skip=0&limit=50`

**Auth Required**: Festival organizer or admin

#### Get Submission Details

**GET** `/api/festivals/submissions/{submission_id}`

**Auth Required**: Submitter, festival organizer, or admin

#### Accept Submission

**POST** `/api/festivals/submissions/{submission_id}/accept`

**Auth Required**: Festival organizer or admin

**Query Parameter**:
- `feedback`: Optional feedback for submitter

#### Reject Submission

**POST** `/api/festivals/submissions/{submission_id}/reject`

**Auth Required**: Festival organizer or admin

**Query Parameter**:
- `feedback`: Reason for rejection

### Festival Management

#### Add Organizer

**POST** `/api/festivals/{festival_id}/organizers`

**Auth Required**: Festival owner or admin

**Request Body**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "organizer"
}
```

#### List Organizers

**GET** `/api/festivals/{festival_id}/organizers`

**Auth Required**: No

#### Remove Organizer

**DELETE** `/api/festivals/{festival_id}/organizers/{user_id}`

**Auth Required**: Festival owner or admin

#### Follow Festival

**POST** `/api/festivals/{festival_id}/follow`

**Auth Required**: Any authenticated user

#### Unfollow Festival

**DELETE** `/api/festivals/{festival_id}/follow`

**Auth Required**: Any authenticated user

#### List Followers

**GET** `/api/festivals/{festival_id}/followers?skip=0&limit=50`

**Auth Required**: No

### Festival Events

#### Create Event

**POST** `/api/festivals/{festival_id}/events`

**Auth Required**: Festival organizer or admin

**Request Body**:
```json
{
  "title": "Opening Ceremony",
  "description": "Festival opening with keynote speech",
  "event_date": "2024-06-01T19:00:00Z",
  "location": "Main Hall",
  "event_type": "ceremony"
}
```

#### List Events

**GET** `/api/festivals/{festival_id}/events`

**Auth Required**: No

#### Update Event

**PUT** `/api/festivals/events/{event_id}`

**Auth Required**: Festival organizer or admin

#### Delete Event

**DELETE** `/api/festivals/events/{event_id}`

**Auth Required**: Festival organizer or admin

## Database Schema

The festival system uses the following tables:

- **festivals**: Main festival data
- **festival_applications**: Creator applications for festival creation
- **festival_submissions**: Film submissions to festivals
- **festival_organizers**: Festival organizers with management permissions
- **festival_followers**: Users following festivals
- **festival_events**: Festival events (screenings, ceremonies, etc.)

See `backend/database/migrations/002_create_festivals.sql` for the complete schema.

## Status Flows

### Festival Creation Flow

1. **Creator Creates Festival**:
   - POST `/api/festivals` → Status: `pending`
   - Admin reviews application
   - Admin approves → Status: `approved` (festival is now public)
   - OR Admin rejects → Status: `rejected`

2. **Admin Creates Festival**:
   - POST `/api/festivals` → Status: `approved` (immediately public)

### Film Submission Flow

1. Creator submits film → Status: `pending`
2. Festival organizer reviews
3. Accept → Status: `accepted`
   OR Reject → Status: `rejected`

## Error Responses

All endpoints return standard HTTP status codes:

- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized (missing or invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

Error response format:
```json
{
  "detail": "Error message"
}
```

## Testing

You can test the API using the Swagger UI at `/docs` or programmatically using curl/httpx:

```bash
# Example: List festivals
curl http://localhost:8000/api/festivals

# Example: Create festival (with auth)
curl -X POST http://localhost:8000/api/festivals \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Festival", "slug": "my-fest", ...}'
```
