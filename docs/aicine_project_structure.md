# 📁 Project Structure

Complete directory structure of AI Cine Analyzer v2.0

```
aicine-analyzer/
│
├── 📄 README.md                          # Main documentation
├── 📄 QUICKSTART.md                      # Quick start guide
├── 📄 PROJECT_STRUCTURE.md               # This file
├── 📄 .env.example                       # Environment variables template
├── 📄 .env                               # Your environment variables (create this)
├── 📄 requirements.txt                   # Python dependencies
├── 📄 setup.sh                           # Setup script
├── 📄 .gitignore                         # Git ignore rules
│
├── 🐳 docker/                            # Docker configuration
│   ├── docker-compose.yml                # Service orchestration
│   ├── Dockerfile.api                    # API container
│   ├── Dockerfile.worker                 # Worker container
│   └── postgres/
│       └── init.sql                      # Database schema
│
├── 🔧 backend/                           # Backend application
│   ├── __init__.py
│   │
│   ├── 🌐 api/                           # FastAPI application
│   │   ├── __init__.py
│   │   └── main.py                       # Main API routes & app
│   │
│   ├── 🔍 analyzers/                     # Analysis modules
│   │   ├── __init__.py
│   │   │
│   │   ├── 🎬 cinematography/           # Visual analysis
│   │   │   ├── __init__.py
│   │   │   ├── shot_detector.py          # Shot detection & keyframes
│   │   │   └── style_classifier.py       # CLIP-based style classification
│   │   │
│   │   ├── 📖 narrative/                 # Story analysis
│   │   │   ├── __init__.py
│   │   │   └── gemini_analyzer.py        # Gemini AI narrative analysis
│   │   │
│   │   ├── 🎵 audio/                     # Audio analysis
│   │   │   ├── __init__.py
│   │   │   └── audio_analyzer.py         # Whisper transcription & mood
│   │   │
│   │   └── 🎭 characters/                # Character analysis
│   │       ├── __init__.py
│   │       └── character_tracker.py      # Face tracking & profiling
│   │
│   ├── 🎥 core/                          # Core processing
│   │   ├── __init__.py
│   │   └── video_processor.py            # Video download & extraction
│   │
│   ├── 📊 models/                        # Data models
│   │   ├── __init__.py
│   │   └── schemas.py                    # Pydantic models
│   │
│   ├── 🗄️ database/                      # Database operations
│   │   ├── __init__.py
│   │   └── connection.py                 # DB connection & helpers
│   │
│   └── ⚙️ tasks/                         # Background tasks
│       ├── __init__.py
│       └── celery_app.py                 # Celery tasks & worker
│
├── 🧪 tests/                             # Test suite
│   ├── __init__.py
│   ├── test_api.py                       # API tests
│   ├── test_analyzers.py                # Analyzer tests
│   └── test_database.py                 # Database tests
│
├── 📁 data/                              # Data storage (gitignored)
│   ├── videos/                           # Downloaded videos
│   ├── frames/                           # Extracted frames
│   └── audio/                            # Extracted audio
│
├── 📁 analyses/                          # Analysis outputs (gitignored)
│   ├── job_1/
│   │   ├── video/
│   │   ├── frames/
│   │   ├── keyframes/
│   │   └── audio/
│   └── job_2/
│       └── ...
│
└── 📁 logs/                              # Application logs (gitignored)
    ├── api.log
    ├── worker.log
    └── analysis.log
```

## 📦 File Descriptions

### Root Files

- **README.md** - Complete documentation, features, usage
- **QUICKSTART.md** - 5-minute setup guide
- **.env.example** - Template for environment variables
- **.env** - Your actual environment variables (not committed)
- **requirements.txt** - Python package dependencies
- **setup.sh** - Automated setup script

### Docker Configuration

- **docker-compose.yml** - Defines all services (postgres, redis, api, worker, flower)
- **Dockerfile.api** - Container for FastAPI server
- **Dockerfile.worker** - Container for Celery workers
- **init.sql** - PostgreSQL schema with pgvector

### Backend Application

#### API Layer (`backend/api/`)
- Handles HTTP requests
- Route definitions
- Request/response validation
- Authentication (future)

#### Analyzers (`backend/analyzers/`)

**Cinematography** - Visual analysis
- Shot detection using PySceneDetect
- Keyframe extraction
- Style classification using CLIP
- Color palette extraction
- Lighting analysis

**Narrative** - Story analysis
- Gemini AI integration
- Logline & synopsis generation
- Theme extraction
- Act structure analysis
- Emotional arc tracing
- Conflict identification

**Audio** - Sound analysis
- Whisper transcription
- Tempo & beat detection
- Mood classification
- Speech/music ratio
- Energy analysis

**Characters** - Character analysis
- Face detection & tracking
- Character identification
- Screen time calculation
- Role classification
- Emotional profiling

#### Core (`backend/core/`)
- Video download (yt-dlp)
- Frame extraction (ffmpeg)
- Audio extraction (ffmpeg)
- File management

#### Models (`backend/models/`)
- Pydantic schemas for validation
- Request/response models
- Data transfer objects

#### Database (`backend/database/`)
- PostgreSQL connection pool
- CRUD operations
- Vector similarity search
- Helper functions

#### Tasks (`backend/tasks/`)
- Celery worker configuration
- Background job processing
- Task queue management
- Periodic cleanup tasks

## 🗄️ Database Schema

### Tables

1. **films** - Main film records
   - Metadata, duration, URL
   - Visual/text/audio embeddings (pgvector)
   - Style fingerprint

2. **analysis_jobs** - Job tracking
   - Status, progress, errors
   - Links to films

3. **shots** - Shot information
   - Timestamps, types, lighting
   - Keyframe paths

4. **characters** - Character profiles
   - Screen time, role, emotions
   - Character arcs

5. **scenes** - Scene breakdown
   - Duration, lighting, pacing
   - Emotional tone

6. **narratives** - Story analysis
   - Logline, synopsis, themes
   - Genre, tone, conflict type

7. **transcripts** - Audio transcripts
   - Full text, segments
   - Language

8. **audio_features** - Audio analysis
   - Tempo, energy, mood
   - Intensity, pacing

## 🔄 Data Flow

```
1. User submits URL
   ↓
2. API creates job → Celery task queued
   ↓
3. Worker picks up task
   ↓
4. Video Download (yt-dlp)
   ↓
5. Parallel Processing:
   - Frame extraction → Shot detection → Style analysis
   - Audio extraction → Transcription → Audio features
   ↓
6. Advanced Analysis:
   - Gemini narrative analysis
   - Character tracking
   - Scene detection
   ↓
7. Save to Database
   ↓
8. Generate embeddings
   ↓
9. Update job status → Complete
   ↓
10. User retrieves results via API
```

## 🔧 Configuration Files

### Environment Variables (.env)

```env
GEMINI_API_KEY=xxx              # Required
DATABASE_URL=postgres://...     # Auto-configured
REDIS_URL=redis://...           # Auto-configured
ENVIRONMENT=development
DEBUG=true
```

### Docker Compose Services

1. **postgres** - PostgreSQL + pgvector
2. **redis** - Task queue backend
3. **api** - FastAPI server (port 8000)
4. **worker** - Celery worker
5. **flower** - Task monitoring (port 5555)

## 📝 Key Dependencies

### AI/ML Models
- **Google Gemini** - Narrative analysis
- **OpenAI CLIP** - Visual style classification
- **Whisper** - Audio transcription
- **FaceNet** - Face detection/tracking

### Processing
- **PySceneDetect** - Shot detection
- **ffmpeg** - Video/audio processing
- **librosa** - Audio feature extraction
- **OpenCV** - Image processing

### Backend
- **FastAPI** - Web framework
- **Celery** - Task queue
- **PostgreSQL** - Database
- **pgvector** - Similarity search
- **Redis** - Cache/queue

## 🚀 Deployment

### Development
```bash
docker-compose up -d
```

### Production Considerations
1. Use external managed databases
2. Setup load balancer
3. Configure SSL/HTTPS
4. Enable authentication
5. Setup monitoring (Sentry, Datadog)
6. Use production-grade Redis
7. Scale workers horizontally

## 📊 Monitoring

- **API**: http://localhost:8000/docs
- **Flower**: http://localhost:5555
- **Logs**: `docker-compose logs -f`
- **Database**: `docker-compose exec postgres psql`

## 🔐 Security Notes

**Development**:
- Default passwords are weak
- CORS allows all origins
- No authentication

**Production**:
- Change all default passwords
- Restrict CORS origins
- Enable JWT authentication
- Use secrets management
- Setup rate limiting
- Enable HTTPS only

---

This structure supports:
- ✅ Scalability (microservices-ready)
- ✅ Maintainability (clear separation)
- ✅ Testability (isolated modules)
- ✅ Extensibility (easy to add analyzers)
