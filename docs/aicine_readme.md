# 🎬 AI Cine Analyzer v2.0 - Complete Edition

Professional AI-powered film analysis platform with **FULL** cinematography, narrative, audio, and character analysis.

## ✨ Complete Features

### 🎥 Cinematography Analysis
- ✅ **Shot Detection** with PySceneDetect
- ✅ **Keyframe Extraction** for each shot
- ✅ **Lighting Classification** (low-key, high-key, normal)
- ✅ **Shot Type Detection** (close-up, medium, wide)
- ✅ **Color Palette Extraction**
- ✅ **Shot Statistics** (avg length, count, etc.)

### 🎨 Visual Style Classification
- ✅ **CLIP-based Style Analysis** (anime, noir, cyberpunk, etc.)
- ✅ **Visual Embeddings** for similarity search
- ✅ **Style Fingerprinting**
- ✅ **Dominant Color Analysis**

### 📖 Narrative Analysis (Gemini AI)
- ✅ **Logline Generation** (one-sentence summary)
- ✅ **Synopsis Generation** (full plot summary)
- ✅ **Theme Extraction** (top 5 themes with prevalence)
- ✅ **Genre Classification**
- ✅ **Tone Analysis**
- ✅ **Three-Act Structure Analysis**
- ✅ **Story Beat Detection**
- ✅ **Conflict Type Identification**
- ✅ **Emotional Arc Tracing**

### 🎤 Audio Analysis
- ✅ **Whisper Transcription** (multi-language)
- ✅ **Tempo Detection**
- ✅ **Mood Classification** (calm, energetic, tense, etc.)
- ✅ **Energy & Intensity Analysis**
- ✅ **Pacing Classification**
- ✅ **Speech/Music Ratio**
- ✅ **Audio Embeddings**

### 🎭 Character Analysis
- ✅ **Face Detection & Tracking**
- ✅ **Character Identification**
- ✅ **Screen Time Calculation**
- ✅ **Role Classification** (protagonist, supporting, minor)
- ✅ **Character Arc Tracking**

### 🔍 Advanced Features
- ✅ **Scene Detection** (shot grouping)
- ✅ **Vector Similarity Search** (find similar films)
- ✅ **Complete Database Storage**
- ✅ **Real-time Progress Tracking**
- ✅ **Background Processing with Celery**

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker & Docker Compose
- Google Gemini API key (free)
- 8GB+ RAM recommended

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/aicine-analyzer.git
cd aicine-analyzer
chmod +x setup.sh
./setup.sh
```

### 2. Configure API Key

Edit `.env` file:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

Get free key: https://makersuite.google.com/app/apikey

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify

```bash
# Check health
curl http://localhost:8000/health

# View docs
open http://localhost:8000/docs
```

---

## 📖 Usage Guide

### Submit Video for Analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "priority": 5
  }'
```

Response:
```json
{
  "job_id": 1,
  "status": "queued",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "priority": 5,
  "progress": 0.0,
  "created_at": "2024-01-20T10:30:00Z"
}
```

### Check Progress

```bash
curl http://localhost:8000/api/jobs/1
```

Response shows real-time progress:
```json
{
  "job_id": 1,
  "status": "processing",
  "progress": 0.65,
  "current_stage": "📖 Analyzing narrative with Gemini AI...",
  "film_id": null
}
```

### Get Complete Analysis

Once complete:
```bash
curl http://localhost:8000/api/films/1
```

Returns complete analysis with:
- Video metadata
- All shots with timing & lighting
- Visual style & color palette
- Complete transcript
- Narrative (logline, themes, structure)
- All characters with screen time
- Scene breakdown
- Audio features

### Find Similar Films

```bash
curl http://localhost:8000/api/films/1/similar?similarity_type=combined&limit=10
```

---

## 🐍 Python Client

```python
import requests
import time

API = "http://localhost:8000"

# Submit video
response = requests.post(
    f"{API}/api/analyze",
    json={"url": "https://youtube.com/watch?v=VIDEO_ID"}
)
job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# Poll for completion
while True:
    status = requests.get(f"{API}/api/jobs/{job_id}").json()
    print(f"[{status['progress']:.0%}] {status['current_stage']}")
    
    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        print(f"Error: {status['error_message']}")
        break
    
    time.sleep(5)

# Get results
film_id = status['film_id']
film = requests.get(f"{API}/api/films/{film_id}").json()

print(f"\n✅ Analysis Complete!")
print(f"Title: {film['title']}")
print(f"Duration: {film['duration']:.1f}s")
print(f"Shots: {len(film['shots'])}")
print(f"Characters: {len(film['characters'])}")
print(f"Logline: {film['narrative']['logline']}")
```

---

## 🎯 Analysis Pipeline

The complete pipeline processes videos through these stages:

```
1. Download Video (0-15%)
   ├─ yt-dlp downloads video
   └─ Extract metadata

2. Extract Frames (15-25%)
   ├─ ffmpeg extracts frames at 1 FPS
   └─ Store frames for analysis

3. Detect Shots (25-35%)
   ├─ PySceneDetect finds shot boundaries
   ├─ Extract keyframe for each shot
   └─ Analyze lighting & colors

4. Classify Style (35-45%)
   ├─ CLIP analyzes visual style
   ├─ Generate visual embeddings
   └─ Extract color palette

5. Analyze Audio (45-60%)
   ├─ Extract audio track
   ├─ Whisper transcription
   ├─ Librosa feature extraction
   └─ Generate audio embeddings

6. Analyze Narrative (60-75%)
   ├─ Send transcript to Gemini AI
   ├─ Generate logline & synopsis
   ├─ Extract themes
   ├─ Analyze structure
   └─ Trace emotional arc

7. Track Characters (75-85%)
   ├─ Face detection
   ├─ Character matching
   └─ Calculate screen time

8. Detect Scenes (85-90%)
   └─ Group shots into scenes

9. Save to Database (90-100%)
   ├─ Store all analysis data
   └─ Generate embeddings for search
```

---

## 🗄️ Database Schema

### Tables

**films** - Main film records
- Metadata, duration, URL
- Visual/text/audio embeddings (pgvector)
- Style fingerprint

**shots** - Shot-by-shot breakdown
- Timing, type, lighting
- Keyframe paths

**characters** - Character profiles
- Screen time, role, emotions

**scenes** - Scene structure
- Duration, lighting, pacing

**narratives** - Story analysis
- Logline, synopsis, themes
- Genre, tone, structure

**transcripts** - Audio transcripts
- Full text with segments
- Language detection

**audio_features** - Audio analysis
- Tempo, mood, energy
- Intensity, pacing

**analysis_jobs** - Job tracking
- Status, progress, errors

---

## 🛠️ Configuration

### Environment Variables (.env)

```env
# Required
GEMINI_API_KEY=your_gemini_api_key

# Database (auto-configured)
DATABASE_URL=postgresql://aicine_user:aicine_pass@postgres:5432/aicine

# Redis (auto-configured)
REDIS_URL=redis://redis:6379

# Optional
ENVIRONMENT=development
DEBUG=true
```

### Docker Services

- **postgres** - PostgreSQL 15 + pgvector
- **redis** - Redis 7 for task queue
- **api** - FastAPI server (port 8000)
- **worker** - Celery worker for analysis
- **flower** - Task monitor (port 5555)

---

## 📊 Monitoring

### API Documentation
```
http://localhost:8000/docs
```
Interactive Swagger UI

### Task Monitor (Flower)
```
http://localhost:5555
```
Monitor Celery tasks, workers, queue

### Logs
```bash
# All logs
docker-compose logs -f

# API only
docker-compose logs -f api

# Worker only
docker-compose logs -f worker
```

### Database
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U aicine_user -d aicine

# Check films
SELECT id, title, duration FROM films;

# Check job statuses
SELECT id, status, progress, current_stage 
FROM analysis_jobs 
ORDER BY created_at DESC;
```

---

## 🧪 Testing

### Quick Test
```bash
# Test Celery connection
curl http://localhost:8000/api/test

# Check Celery task status
curl http://localhost:8000/api/jobs/{task_id}
```

### Full Test with Short Video
```bash
# Use a short test video (under 1 min)
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=SHORT_VIDEO_ID"}'
```

---

## 🚨 Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d
```

### Worker not processing jobs
```bash
# Check worker logs
docker-compose logs -f worker

# Check Flower
open http://localhost:5555

# Restart worker
docker-compose restart worker
```

### Gemini API errors
- Verify API key in `.env`
- Check quota: https://makersuite.google.com/
- Analysis will continue without narrative if Gemini fails

### Database connection errors
```bash
# Check PostgreSQL
docker-compose exec postgres psql -U aicine_user -d aicine

# Recreate database
docker-compose down -v
docker-compose up -d
```

---

## 🎓 Architecture

```
┌─────────────┐
│   FastAPI   │ ← REST API
└──────┬──────┘
       │
┌──────▼──────┐
│   Celery    │ ← Background tasks
│   Worker    │
└──────┬──────┘
       │
       ├─► Video Processor (yt-dlp, ffmpeg)
       ├─► Shot Detector (PySceneDetect)
       ├─► Style Classifier (CLIP)
       ├─► Audio Analyzer (Whisper + Librosa)
       ├─► Narrative Analyzer (Gemini AI)
       ├─► Character Tracker (face_recognition)
       └─► Database Operations (PostgreSQL + pgvector)
```

---

## 📈 Performance

- **Short videos (< 5 min)**: 2-5 minutes
- **Medium videos (5-15 min)**: 5-15 minutes
- **Long videos (> 15 min)**: 15-30 minutes

Factors:
- Video length & resolution
- Number of shots
- Transcript length
- Gemini API response time
- Hardware (CPU/GPU)

---

## 🔐 Security Notes

**Development**:
- Default passwords (change for production)
- CORS allows all origins
- No authentication required

**Production**:
- Change all passwords
- Restrict CORS origins
- Add JWT authentication
- Use secrets management
- Enable rate limiting
- Setup HTTPS

---

## 🤝 Contributing

Contributions welcome!

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

---

## 📝 License

Apache License 2.0

---

## 🙏 Credits

- **Google Gemini** - Narrative AI
- **OpenAI Whisper** - Transcription
- **PySceneDetect** - Shot detection
- **CLIP** - Visual understanding
- **pgvector** - Similarity search
- **face_recognition** - Face detection

---

## 📧 Support

- Issues: https://github.com/yourusername/aicine-analyzer/issues
- Email: your.email@example.com

---

Made with ❤️ for AI filmmakers and film analysts
