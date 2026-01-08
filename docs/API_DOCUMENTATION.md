# API Documentation - AIcineDB Backend

Complete API reference for the AIcineDB film analysis platform.

## Base URL

```
http://localhost:8000
```

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Root & Health](#root--health)
  - [Film Analysis](#film-analysis)
  - [Jobs](#jobs)
  - [Films](#films)
  - [Statistics](#statistics)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

---

## Overview

The AIcineDB API provides RESTful endpoints for:
- Submitting videos for AI analysis
- Tracking analysis job progress
- Retrieving film analysis data
- Finding similar films using vector similarity
- Getting platform statistics

All responses are in JSON format.

---

## Authentication

Currently, the API does not require authentication. In production, you may want to implement:
- API key authentication
- JWT tokens
- OAuth2

---

## Endpoints

### Root & Health

#### `GET /`

Get API information and available features.

**Response:**
```json
{
  "name": "AI Cine Analyzer API",
  "version": "2.0.0",
  "status": "running",
  "features": [
    "🎬 Shot detection & cinematography",
    "🎨 Visual style classification (CLIP)",
    "🎤 Audio transcription (Whisper)",
    "📖 Narrative analysis (Gemini AI)",
    "🎭 Character tracking & face recognition",
    "🔍 Vector similarity search",
    "💾 Complete database storage"
  ],
  "endpoints": {
    "POST /api/analyze": "Submit video for analysis",
    "GET /api/jobs/{job_id}": "Check job status",
    "GET /api/films": "List all films",
    "GET /api/films/{film_id}": "Get film details",
    "GET /api/films/{film_id}/similar": "Find similar films",
    "GET /health": "Health check",
    "GET /docs": "API documentation"
  }
}
```

---

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "2.0.0"
}
```

---

### Film Analysis

#### `POST /api/analyze`

Submit a video URL for complete AI analysis.

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "priority": 5,
  "force_reanalyze": false
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string (URL) | Yes | Video URL (YouTube, Vimeo, direct link, etc.) |
| `priority` | integer | No | Job priority (1-10, default: 5, higher = more priority) |
| `force_reanalyze` | boolean | No | Re-analyze even if already processed (default: false) |

**Response (200 OK):**
```json
{
  "job_id": 123,
  "status": "queued",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "priority": 5,
  "progress": 0.0,
  "current_stage": null,
  "film_id": null,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00.000Z"
}
```

**Error Responses:**

**409 Conflict** - URL already analyzed:
```json
{
  "detail": "URL already analyzed. Film ID: 42"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Error message"
}
```

**What happens during analysis:**
1. 📥 Download video (0-15%)
2. 🎞️ Extract frames (15-25%)
3. 🎬 Detect shots (25-35%)
4. 🎨 Classify visual style (35-45%)
5. 🎵 Extract & analyze audio (45-60%)
6. 📖 Analyze narrative with AI (60-75%)
7. 🎭 Track characters (75-85%)
8. 🎞️ Detect scenes (85-90%)
9. 💾 Save to database (90-100%)

---

### Jobs

#### `GET /api/jobs/{job_id}`

Get analysis job status and progress.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | integer | Job ID returned from `/api/analyze` |

**Response (200 OK):**
```json
{
  "job_id": 123,
  "status": "processing",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "priority": 5,
  "progress": 0.65,
  "current_stage": "🎨 Classifying visual style...",
  "film_id": null,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00.000Z"
}
```

**Status Values:**
- `pending` - Job created but not yet queued
- `queued` - Job queued for processing
- `processing` - Analysis in progress
- `completed` - Analysis finished successfully
- `failed` - Analysis failed with error

**Progress:** Float from 0.0 to 1.0 (0% to 100%)

**Error Response (404):**
```json
{
  "detail": "Job not found"
}
```

---

### Films

#### `GET /api/films`

List all analyzed films.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip (pagination) |
| `limit` | integer | 20 | Maximum records to return (1-100) |

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "title": "Never Gonna Give You Up",
    "duration": 213.5,
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "analyzed_at": "2024-01-15T10:45:00.000Z",
    "style_fingerprint": "vintage|vibrant|dance|80s"
  },
  {
    "id": 2,
    "title": "Another Film",
    "duration": 450.2,
    "url": "https://example.com/video.mp4",
    "analyzed_at": "2024-01-15T11:00:00.000Z",
    "style_fingerprint": "dark|cinematic|moody|thriller"
  }
]
```

---

#### `GET /api/films/{film_id}`

Get complete analysis for a specific film.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `film_id` | integer | Film ID |

**Response (200 OK):**
```json
{
  "id": 1,
  "title": "Never Gonna Give You Up",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "duration": 213.5,
  "uploader": "RickAstleyVEVO",
  "resolution": "1920x1080",
  "fps": 30.0,
  "style_fingerprint": "vintage|vibrant|dance|80s",
  "analyzed_at": "2024-01-15T10:45:00.000Z",
  "created_at": "2024-01-15T10:30:00.000Z",
  
  "narrative": {
    "summary": "A vibrant 1980s music video featuring...",
    "genre": "Music Video",
    "themes": ["love", "commitment", "dance"],
    "tone": "Upbeat and energetic",
    "story_beats": [...]
  },
  
  "transcript": {
    "text": "We're no strangers to love...",
    "word_count": 342,
    "language": "en",
    "segments": [
      {
        "start": 0.0,
        "end": 3.5,
        "text": "We're no strangers to love"
      }
    ]
  },
  
  "audio_features": {
    "tempo": 113.0,
    "key": "F",
    "mode": "major",
    "energy": 0.87,
    "valence": 0.92
  },
  
  "shots": [
    {
      "shot_number": 1,
      "start_time": 0.0,
      "end_time": 2.5,
      "duration": 2.5,
      "shot_type": "medium",
      "lighting": "high-key",
      "dominant_colors": ["#FF5733", "#3498DB"]
    }
  ],
  
  "characters": [
    {
      "character_number": 1,
      "first_appearance": 1.2,
      "last_appearance": 210.3,
      "screen_time": 185.7,
      "total_detections": 1247
    }
  ],
  
  "scenes": [
    {
      "scene_number": 1,
      "start_time": 0.0,
      "end_time": 45.2,
      "duration": 45.2,
      "num_shots": 12,
      "lighting": "high-key"
    }
  ]
}
```

**Error Response (404):**
```json
{
  "detail": "Film not found"
}
```

---

#### `GET /api/films/{film_id}/similar`

Find films similar to the specified film using vector similarity.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `film_id` | integer | Film ID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `similarity_type` | string | `combined` | Type of similarity: `visual`, `narrative`, `audio`, `combined` |
| `limit` | integer | 10 | Maximum results (1-50) |

**Similarity Types:**
- `visual` - Based on visual style (CLIP embeddings)
- `narrative` - Based on story/themes (text embeddings)
- `audio` - Based on audio features
- `combined` - Weighted combination of all three

**Response (200 OK):**
```json
[
  {
    "film_id": 42,
    "title": "Similar Film Title",
    "similarity_score": 0.89,
    "url": "https://example.com/similar.mp4",
    "style_fingerprint": "vintage|vibrant|dance|retro"
  },
  {
    "film_id": 17,
    "title": "Another Similar Film",
    "similarity_score": 0.82,
    "url": "https://example.com/another.mp4",
    "style_fingerprint": "colorful|energetic|music|pop"
  }
]
```

**Similarity Score:** Float from 0.0 to 1.0 (higher = more similar)

---

### Statistics

#### `GET /api/stats`

Get platform statistics.

**Response (200 OK):**
```json
{
  "total_films": 127,
  "total_duration_hours": 342.5,
  "recent_films": 15,
  "pending_jobs": 3,
  "processing_jobs": 2
}
```

---

## Data Models

### AnalysisRequest

```typescript
{
  url: string (URL),        // Required
  priority?: number,        // Optional, 1-10, default: 5
  force_reanalyze?: boolean // Optional, default: false
}
```

### JobResponse

```typescript
{
  job_id: number,
  status: "pending" | "queued" | "processing" | "completed" | "failed",
  url: string,
  priority: number,
  progress: number,         // 0.0 to 1.0
  current_stage?: string,
  film_id?: number,
  error_message?: string,
  created_at: string        // ISO 8601 datetime
}
```

### FilmSummary

```typescript
{
  id: number,
  title: string,
  duration: number,         // seconds
  url: string,
  analyzed_at?: string,     // ISO 8601 datetime
  style_fingerprint?: string
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently not implemented. In production, consider:
- Per-IP rate limiting
- API key quotas
- Queue priority based on user tier

---

## Examples

### Python

```python
import requests

# Analyze a video
response = requests.post(
    "http://localhost:8000/api/analyze",
    json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "priority": 7
    }
)
job = response.json()
job_id = job["job_id"]

# Check status
import time
while True:
    response = requests.get(f"http://localhost:8000/api/jobs/{job_id}")
    job = response.json()
    print(f"Progress: {job['progress']*100:.1f}% - {job['current_stage']}")
    
    if job["status"] in ["completed", "failed"]:
        break
    
    time.sleep(5)

# Get results
if job["status"] == "completed":
    film_id = job["film_id"]
    response = requests.get(f"http://localhost:8000/api/films/{film_id}")
    film = response.json()
    print(f"Title: {film['title']}")
    print(f"Genre: {film['narrative']['genre']}")
    print(f"Themes: {', '.join(film['narrative']['themes'])}")
```

### JavaScript

```javascript
// Analyze a video
const analyzeVideo = async (url) => {
  const response = await fetch('http://localhost:8000/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, priority: 5 })
  });
  return response.json();
};

// Check job status
const checkJob = async (jobId) => {
  const response = await fetch(`http://localhost:8000/api/jobs/${jobId}`);
  return response.json();
};

// Get film
const getFilm = async (filmId) => {
  const response = await fetch(`http://localhost:8000/api/films/${filmId}`);
  return response.json();
};

// Usage
(async () => {
  const job = await analyzeVideo('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  console.log('Job created:', job.job_id);
  
  // Poll for completion
  while (true) {
    const status = await checkJob(job.job_id);
    console.log(`${status.progress * 100}% - ${status.current_stage}`);
    
    if (status.status === 'completed') {
      const film = await getFilm(status.film_id);
      console.log('Analysis complete:', film.title);
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
})();
```

### cURL

```bash
# Analyze video
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "priority": 5
  }'

# Check job status
curl "http://localhost:8000/api/jobs/1"

# Get film
curl "http://localhost:8000/api/films/1"

# Find similar films
curl "http://localhost:8000/api/films/1/similar?similarity_type=combined&limit=10"

# Get statistics
curl "http://localhost:8000/api/stats"
```

---

## Interactive Documentation

The API includes interactive Swagger/OpenAPI documentation:

**Swagger UI:** http://localhost:8000/docs
**ReDoc:** http://localhost:8000/redoc

Features:
- Try out endpoints directly in the browser
- See request/response schemas
- Download OpenAPI spec

---

## Webhooks (Future)

Coming soon: Webhook support for job completion notifications.

```json
{
  "event": "job.completed",
  "job_id": 123,
  "film_id": 42,
  "timestamp": "2024-01-15T10:45:00.000Z"
}
```

---

## WebSocket Support (Future)

Coming soon: Real-time job progress via WebSocket.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/jobs/123');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Progress: ${update.progress * 100}%`);
};
```

---

## Support

- **API Issues:** GitHub Issues
- **Documentation:** README.md, SETUP_WINDOWS.md
- **Interactive Docs:** http://localhost:8000/docs

---

**Happy building! 🎬**
