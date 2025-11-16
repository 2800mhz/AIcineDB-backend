# 🎬 AI Cine Analyzer v2.0

Professional AI-powered film analysis platform with comprehensive cinematography, narrative, and audio analysis.

## ✨ Features

- **🎥 Cinematography Analysis**
  - Shot detection & classification
  - Color palette extraction
  - Lighting analysis
  - Visual style classification

- **📖 Narrative Analysis** (Gemini AI)
  - Automated logline & synopsis generation
  - Theme extraction
  - Three-act structure analysis
  - Story beat detection
  - Emotional arc tracing

- **🎭 Character Analysis**
  - Face detection & tracking
  - Screen time calculation
  - Character role classification
  - Emotional profiling

- **🎵 Audio Analysis**
  - Automatic transcription (Whisper)
  - Mood detection
  - Tempo & energy analysis
  - Speech/music ratio

- **🔍 Advanced Search**
  - Vector similarity search
  - Theme-based filtering
  - Style fingerprinting

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Google Gemini API key (free tier available)
- At least 8GB RAM
- (Optional) NVIDIA GPU for faster processing

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/aicine-analyzer.git
cd aicine-analyzer
```

### 2. Setup Environment

```bash
# Copy example .env file
cp .env.example .env

# Edit .env and add your Gemini API key
nano .env
```

**Get a free Gemini API key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Paste it in `.env` file

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f api
```

### 4. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## 📖 Usage

### API Endpoints

#### 1. Submit Video for Analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=VIDEO_ID",
    "priority": 5
  }'
```

Response:
```json
{
  "job_id": 123,
  "status": "pending",
  "url": "https://youtube.com/watch?v=VIDEO_ID",
  "created_at": "2024-01-20T10:30:00Z",
  "celery_task_id": "abc-def-123"
}
```

#### 2. Check Job Status

```bash
curl http://localhost:8000/api/jobs/123
```

#### 3. Get Film Analysis

```bash
curl http://localhost:8000/api/films/456
```

#### 4. Find Similar Films

```bash
curl http://localhost:8000/api/films/456/similar?similarity_type=combined&limit=10
```

#### 5. Search Films

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "isolation",
    "min_duration": 60,
    "mood": "melancholic"
  }'
```

### Python Client Example

```python
import requests

API_URL = "http://localhost:8000"

# Submit analysis
response = requests.post(
    f"{API_URL}/api/analyze",
    json={"url": "https://youtube.com/watch?v=VIDEO_ID"}
)
job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# Wait for completion (poll every 10 seconds)
import time
while True:
    status = requests.get(f"{API_URL}/api/jobs/{job_id}").json()
    print(f"Status: {status['status']} - Progress: {status['progress']:.0%}")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(10)

# Get results
if status['status'] == 'completed':
    film_id = status['film_id']
    film = requests.get(f"{API_URL}/api/films/{film_id}").json()
    
    print(f"\nAnalysis Complete!")
    print(f"Title: {film['title']}")
    print(f"Themes: {', '.join([t['name'] for t in film['narrative']['themes'][:3]])}")
    print(f"Logline: {film['narrative']['logline']}")
```

## 🛠️ Configuration

### Environment Variables

Create `.env` file:

```env
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Database
DATABASE_URL=postgresql://aicine_user:aicine_pass@postgres:5432/aicine

# Redis
REDIS_URL=redis://redis:6379

# Optional: Anthropic (if you want to use Claude too)
# ANTHROPIC_API_KEY=your_anthropic_key

# Optional: Hugging Face (for some models)
# HUGGING_FACE_TOKEN=your_hf_token
```

### Docker Compose Services

- **postgres**: PostgreSQL + pgvector for embeddings
- **redis**: Task queue backend
- **api**: FastAPI REST API (port 8000)
- **worker**: Celery background worker
- **flower**: Task monitoring UI (port 5555)

## 📊 Monitoring

### Flower Dashboard

View task queue and worker status:
```bash
open http://localhost:5555
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U aicine_user -d aicine

# List films
SELECT id, title, duration, analyzed_at FROM films;

# Check job statuses
SELECT id, status, progress, current_stage FROM analysis_jobs ORDER BY created_at DESC LIMIT 10;
```

### Logs

```bash
# API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker

# All logs
docker-compose logs -f
```

## 🔧 Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
createdb aicine
psql aicine < docker/postgres/init.sql

# Run migrations (if using Alembic)
alembic upgrade head

# Start API
uvicorn backend.api.main:app --reload

# Start worker (separate terminal)
celery -A backend.tasks.celery_app worker --loglevel=info
```

### Run Tests

```bash
pytest tests/
```

### Code Formatting

```bash
# Format with black
black backend/

# Lint with ruff
ruff check backend/
```

## 📁 Project Structure

```
aicine-analyzer/
├── docker/
│   ├── docker-compose.yml       # Service orchestration
│   ├── Dockerfile.api           # API container
│   ├── Dockerfile.worker        # Worker container
│   └── postgres/
│       └── init.sql             # Database schema
├── backend/
│   ├── api/
│   │   └── main.py              # FastAPI application
│   ├── analyzers/
│   │   ├── cinematography/
│   │   │   ├── shot_detector.py
│   │   │   └── style_classifier.py
│   │   ├── narrative/
│   │   │   └── gemini_analyzer.py
│   │   ├── audio/
│   │   │   └── audio_analyzer.py
│   │   └── characters/
│   │       └── character_tracker.py
│   ├── core/
│   │   └── video_processor.py
│   ├── models/
│   │   └── schemas.py
│   ├── database/
│   │   └── connection.py
│   └── tasks/
│       └── celery_app.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## 🎯 Roadmap

- [ ] **v2.1** - Web UI (React dashboard)
- [ ] **v2.2** - Advanced character tracking with ReID
- [ ] **v2.3** - Motion analysis & camera movement detection
- [ ] **v2.4** - Multi-language support
- [ ] **v2.5** - AI pipeline detection (ComfyUI, Stable Diffusion)
- [ ] **v3.0** - AI Film Doctor (feedback & recommendations)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini** for narrative AI
- **OpenAI Whisper** for transcription
- **PySceneDetect** for shot detection
- **CLIP** for visual understanding
- **pgvector** for similarity search

## 📧 Contact

Questions? Issues? Suggestions?

- **GitHub Issues**: https://github.com/yourusername/aicine-analyzer/issues
- **Email**: your.email@example.com

---

Made with ❤️ for AI filmmakers
