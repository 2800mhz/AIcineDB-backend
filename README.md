# AIcineDB Backend

> AI-powered film analysis platform with comprehensive cinematography, narrative, and character analysis

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Windows](https://img.shields.io/badge/Windows-Native-blue.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎬 Overview

AIcineDB Backend is a comprehensive AI-powered film analysis system that provides deep insights into cinematic content through:

- **🎥 Shot Detection & Cinematography Analysis** - Automated scene segmentation and composition analysis
- **🎨 Visual Style Classification** - CLIP-based style fingerprinting and similarity matching
- **🎤 Audio Transcription** - Whisper-powered speech-to-text with mood detection
- **📖 Narrative Analysis** - Gemini AI-powered story structure and thematic analysis
- **🎭 Character Tracking** - Face detection and character arc analysis
- **🔍 Vector Similarity Search** - Find visually and narratively similar films
- **💾 Complete PostgreSQL Storage** - pgvector-enabled embeddings database

## 🏗️ Architecture

```
AIcineDB-Backend/
├── backend/
│   ├── api/              # FastAPI application & routes
│   ├── tasks/            # Celery task definitions
│   ├── database/         # PostgreSQL + pgvector operations
│   ├── analyzers/        # Analysis modules
│   │   ├── cinematography/  # Shot detection, style classification
│   │   ├── audio/          # Whisper transcription, mood analysis
│   │   ├── characters/     # Face detection & tracking
│   │   └── narrative/      # Gemini AI analysis
│   └── core/             # Video processing pipeline
├── docker/               # Docker configuration files
├── .env.example          # Environment configuration template
├── setup-windows.ps1     # Windows setup script
├── run-dev-services.bat  # Start all services
└── requirements.txt      # Python dependencies (Windows-optimized)
```

## ✨ Features

### Video Analysis Pipeline
- Automatic video download from URLs (YouTube, Vimeo, etc.)
- Frame extraction and preprocessing
- Shot boundary detection with PySceneDetect
- Keyframe extraction for representative frames

### Cinematography Analysis
- Shot composition and framing analysis
- Camera movement detection
- Lighting and color palette extraction
- Visual style classification using CLIP
- Shot duration and rhythm analysis

### Audio Processing
- High-quality audio extraction
- Speech transcription with OpenAI Whisper
- Speaker diarization
- Mood and sentiment analysis
- Music vs. dialogue detection

### Narrative Analysis
- Story structure detection (acts, sequences)
- Theme and motif identification
- Character arc analysis
- Scene relationship mapping
- Powered by Google Gemini AI

### Character Tracking
- Face detection in frames
- Character appearance tracking
- Screen time calculation
- Character relationship mapping

### Database & Search
- PostgreSQL with pgvector for embeddings
- Vector similarity search
- Full-text search capabilities
- Comprehensive metadata storage

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** ([Download](https://www.python.org/downloads/))
- **FFmpeg** ([Download](https://ffmpeg.org/download.html))
- **Docker Desktop** ([Download](https://www.docker.com/products/docker-desktop)) - For hybrid mode
- **Git** ([Download](https://git-scm.com/downloads))

### Installation

#### Option 1: Automated Setup (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/2800mhz/AIcineDB-backend.git
cd AIcineDB-backend
```

2. **Run the Windows setup script:**
```powershell
.\setup-windows.ps1
```

The script will:
- Check prerequisites
- Let you choose between Hybrid or Pure Windows mode
- Create a Python virtual environment
- Install all dependencies
- Configure environment variables
- Set up Docker services (if hybrid mode)
- Create required directories

3. **Configure your API keys:**

Edit `.env` and set your API key:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

Get your Gemini API key: https://makersuite.google.com/app/apikey

#### Option 2: Manual Setup

<details>
<summary>Click to expand manual setup instructions</summary>

1. **Clone and enter directory:**
```bash
git clone https://github.com/2800mhz/AIcineDB-backend.git
cd AIcineDB-backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment:**
```bash
copy .env.example .env
# Edit .env with your configuration
```

5. **Start Docker services (Hybrid mode):**
```bash
docker-compose up -d postgres redis
```

Or install PostgreSQL and Redis on Windows (Pure Windows mode).

6. **Create required directories:**
```bash
mkdir data analyses frames temp
```

</details>

### Running the Application

#### All Services at Once (Recommended)
```bash
.\run-dev-services.bat
```

This starts:
- PostgreSQL + Redis (Docker)
- FastAPI server (http://localhost:8000)
- Celery worker
- Flower monitoring UI (http://localhost:5555)

#### Individual Services

**Start Docker services only:**
```bash
.\start-docker-services.bat
```

**Start API server:**
```bash
.\start-api.bat
```

**Start Celery worker:**
```bash
.\start-worker.bat
```

**Start Flower monitoring:**
```bash
.\start-flower.bat
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

#### Required Settings
```bash
# Database (adjust for your setup)
DATABASE_URL=postgresql://aicine_user:aicine_pass@localhost:5432/aicine

# Redis
REDIS_URL=redis://localhost:6379

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
```

#### Optional Settings
```bash
# Application
ENVIRONMENT=development
API_PORT=8000
DEBUG=True
LOG_LEVEL=INFO

# Storage
DATA_DIR=./data
ANALYSES_DIR=./analyses
FRAMES_DIR=./frames

# Video Processing
MAX_VIDEO_DURATION=3600
MAX_VIDEO_SIZE=1000
FRAME_EXTRACTION_FPS=1

# Celery
CELERY_WORKER_CONCURRENCY=4
CELERY_TASK_TIME_LIMIT=7200
```

### Deployment Modes

#### 🔀 Hybrid Mode (Recommended)
- **PostgreSQL + Redis**: Docker containers
- **FastAPI + Celery**: Native Windows processes
- **Pros**: Easy setup, isolated services, good performance
- **Cons**: Requires Docker Desktop

#### 💻 Pure Windows Mode
- **All services**: Native Windows installation
- **Pros**: Full native performance, no Docker overhead
- **Cons**: More complex setup, manual service management

**PostgreSQL Setup (Pure Windows):**
1. Install PostgreSQL from https://www.postgresql.org/download/windows/
2. Create database: `createdb -U postgres aicine`
3. Create user: `createuser -U postgres aicine_user`
4. Run init script: `psql -U postgres -d aicine -f docker/postgres/init.sql`

**Redis Setup (Pure Windows):**
1. Download from https://github.com/microsoftarchive/redis/releases
2. Extract and run: `redis-server.exe`

## 📊 API Usage

### Starting an Analysis

```bash
POST http://localhost:8000/api/analyze
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "priority": 5,
  "force_reanalyze": false
}
```

Response:
```json
{
  "job_id": 123,
  "status": "queued",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "priority": 5,
  "progress": 0.0,
  "created_at": "2024-01-01T12:00:00"
}
```

### Checking Job Status

```bash
GET http://localhost:8000/api/jobs/123
```

Response:
```json
{
  "job_id": 123,
  "status": "processing",
  "progress": 45.5,
  "current_stage": "Audio transcription",
  "film_id": 456
}
```

### Getting Film Analysis

```bash
GET http://localhost:8000/api/films/456
```

Returns complete analysis including:
- Video metadata
- Shot-by-shot breakdown
- Visual style classification
- Full transcript
- Narrative analysis
- Character information
- Scene structure

### Finding Similar Films

```bash
GET http://localhost:8000/api/films/456/similar?similarity_type=combined&limit=10
```

Similarity types:
- `visual` - Based on visual style (CLIP embeddings)
- `narrative` - Based on story/themes
- `audio` - Based on audio features
- `combined` - Multi-modal similarity

## 📚 API Documentation

Once running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## 🎯 Analysis Workflow

1. **Submit Video URL** → API creates analysis job
2. **Download Video** → yt-dlp downloads content
3. **Extract Media** → FFmpeg extracts frames & audio
4. **Shot Detection** → PySceneDetect finds shot boundaries
5. **Visual Analysis** → CLIP classifies style & extracts features
6. **Audio Processing** → Whisper transcribes dialogue
7. **Narrative Analysis** → Gemini AI analyzes story structure
8. **Character Tracking** → Face detection & recognition
9. **Database Storage** → Save all results with embeddings
10. **Similarity Indexing** → pgvector enables search

## 🛠️ Development

### Project Structure

```
backend/
├── api/
│   ├── main.py              # FastAPI application
│   └── __init__.py
├── tasks/
│   ├── celery_app.py        # Celery configuration
│   ├── video_tasks.py       # Analysis tasks
│   └── __init__.py
├── database/
│   ├── connection.py        # Database connection
│   ├── database_operations.py  # CRUD operations
│   └── __init__.py
├── analyzers/
│   ├── cinematography/
│   │   ├── shot_detector.py
│   │   └── style_classifier.py
│   ├── audio/
│   │   └── audio_analyzer_complete.py
│   ├── characters/
│   │   └── character_tracker.py
│   └── narrative/
│       └── (future implementation)
└── core/
    ├── video_processor.py
    └── full_analysis_pipeline.py
```

### Adding New Analysis Modules

1. Create new analyzer in `backend/analyzers/`
2. Implement the analysis logic
3. Add to `full_analysis_pipeline.py`
4. Update database schema if needed
5. Add API endpoints in `backend/api/main.py`

### Database Schema

The system uses PostgreSQL with pgvector extension for:
- `films` - Video metadata and embeddings
- `shots` - Shot-by-shot analysis
- `scenes` - Scene structure
- `characters` - Character tracking
- `narratives` - Story analysis
- `transcripts` - Speech transcription
- `audio_features` - Audio analysis
- `analysis_jobs` - Job tracking

## 🔍 Monitoring

### Flower Dashboard
Monitor Celery tasks at: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status
- Task history
- Performance metrics

### Docker Logs
```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Application Logs
Check console output in the service windows or configure logging in `.env`:
```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## ❗ Troubleshooting

### Common Issues

**"Docker services failed to start"**
- Ensure Docker Desktop is running
- Check if ports 5432 and 6379 are available
- Try: `docker-compose down -v` then restart

**"Module not found" errors**
- Activate virtual environment: `venv\Scripts\activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**"Database connection failed"**
- Check DATABASE_URL in `.env`
- Verify PostgreSQL is running: `docker-compose ps`
- Check logs: `docker-compose logs postgres`

**"Celery worker not processing tasks"**
- Verify Redis is running: `docker-compose ps`
- Check REDIS_URL in `.env`
- Restart worker: Stop and run `.\start-worker.bat`

**"FFmpeg not found"**
- Install FFmpeg from https://ffmpeg.org/download.html
- Add to PATH or place in project directory
- Restart command prompt after installation

**"API Key errors"**
- Check GEMINI_API_KEY in `.env`
- Verify key is valid at https://makersuite.google.com/
- Ensure no extra spaces or quotes

### Performance Issues

**Slow analysis:**
- Reduce FRAME_EXTRACTION_FPS in `.env`
- Increase CELERY_WORKER_CONCURRENCY
- Check CPU/RAM usage
- Consider using GPU for faster processing

**High memory usage:**
- Reduce worker concurrency
- Process shorter videos
- Increase system RAM
- Clear temporary files in `temp/`

### Getting Help

1. Check the [troubleshooting](#troubleshooting) section
2. Review API documentation at http://localhost:8000/docs
3. Check Flower dashboard for task errors
4. Review logs in Docker and service windows
5. Open an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - System information
   - Relevant log output

## 🧪 Testing

Currently, the project does not have automated tests. For manual testing:

1. **Health Check:**
```bash
curl http://localhost:8000/health
```

2. **Test Analysis:**
Submit a short video URL (under 1 minute) for testing.

3. **Monitor Progress:**
Use Flower dashboard to track task execution.

## 📦 Dependencies

### Core Framework
- **FastAPI** - Modern web framework
- **Celery** - Distributed task queue
- **PostgreSQL** - Primary database
- **Redis** - Message broker & cache

### Video Processing
- **yt-dlp** - Video download
- **FFmpeg** - Media processing
- **OpenCV** - Computer vision
- **PySceneDetect** - Shot detection

### AI/ML
- **OpenAI Whisper** - Speech recognition
- **Transformers** - CLIP embeddings
- **Google Gemini** - Narrative analysis
- **sentence-transformers** - Text embeddings
- **PyTorch** - Deep learning

### Audio
- **librosa** - Audio analysis
- **pydub** - Audio manipulation
- **soundfile** - Audio I/O

See `requirements.txt` for complete list with versions.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI Whisper** - Speech recognition
- **Google Gemini** - Narrative AI
- **CLIP** - Visual understanding
- **PySceneDetect** - Shot detection
- **FastAPI** - Web framework
- **Celery** - Task queue

## 🔮 Roadmap

- [ ] Real-time analysis progress streaming
- [ ] Batch video processing
- [ ] Custom analysis pipelines
- [ ] Export to various formats (JSON, CSV, PDF)
- [ ] Advanced search and filtering
- [ ] User authentication and multi-tenancy
- [ ] Frontend web application
- [ ] GPU acceleration support
- [ ] Distributed worker scaling
- [ ] Cloud deployment guides (Azure, AWS, GCP)

## 📞 Support

For questions, issues, or contributions:
- **GitHub Issues**: [Report a bug or request a feature](https://github.com/2800mhz/AIcineDB-backend/issues)
- **Documentation**: http://localhost:8000/docs (when running)

---

Made with ❤️ for film analysis and AI research
