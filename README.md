# AIcineDB Backend

Complete AI-powered film analysis platform with Windows-native support.

## 🎬 Features

- **🎥 Video Processing** - Download and analyze films from URLs (YouTube, Vimeo, etc.)
- **🎞️ Cinematography Analysis** - Shot detection, keyframe extraction, visual style classification
- **🎨 Visual Style** - CLIP-based style fingerprinting and color palette analysis
- **🎤 Audio Analysis** - Whisper transcription + Librosa audio feature extraction
- **📖 Narrative AI** - Gemini AI-powered screenplay structure and theme analysis
- **🎭 Character Tracking** - Face detection and character screen time tracking
- **🔍 Vector Similarity** - Find similar films using visual, narrative, and audio embeddings
- **💾 Full Database** - PostgreSQL with pgvector for efficient similarity search

## 🚀 Quick Start (Windows)

### Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **FFmpeg** - Required for video/audio processing
- **Docker Desktop** (recommended) - [Download](https://www.docker.com/products/docker-desktop)
  - *OR manually install PostgreSQL with pgvector + Redis*

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/2800mhz/AIcineDB-backend.git
   cd AIcineDB-backend
   ```

2. **Run the setup script**
   ```powershell
   .\setup-windows.ps1
   ```

   This will:
   - Create a virtual environment
   - Install all Python dependencies
   - Check/install FFmpeg
   - Setup configuration files

3. **Configure environment**
   ```powershell
   # Edit .env and add your API key
   notepad .env
   ```
   
   Required: `GEMINI_API_KEY` - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

4. **Start database services**
   ```powershell
   # Using Docker (recommended)
   scripts\start-docker-services.bat
   
   # OR set up PostgreSQL + Redis manually (see SETUP_WINDOWS.md)
   ```

5. **Start the application**
   
   Open **3 separate terminals**:
   
   **Terminal 1 - API Server:**
   ```powershell
   scripts\start-api.bat
   ```
   
   **Terminal 2 - Worker:**
   ```powershell
   scripts\start-worker.bat
   ```
   
   **Terminal 3 - Flower (optional):**
   ```powershell
   scripts\start-flower.bat
   ```

6. **Access the application**
   - **API Docs:** http://localhost:8000/docs
   - **Flower Dashboard:** http://localhost:5555
   - **Health Check:** http://localhost:8000/health

## 📖 Usage

### Analyze a Film

```bash
# Using the API
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "priority": 5
  }'
```

Or use the interactive API docs at http://localhost:8000/docs

### Check Job Status

```bash
curl http://localhost:8000/api/jobs/1
```

### Get Film Analysis

```bash
curl http://localhost:8000/api/films/1
```

### Find Similar Films

```bash
curl "http://localhost:8000/api/films/1/similar?similarity_type=combined&limit=10"
```

## 🏗️ Architecture

```
AIcineDB-backend/
├── backend/
│   ├── api/                    # FastAPI application
│   │   └── main.py            # API endpoints
│   ├── tasks/                  # Celery background tasks
│   │   ├── celery_app.py      # Celery configuration
│   │   └── video_tasks.py     # Analysis tasks
│   ├── analyzers/              # Analysis modules
│   │   ├── cinematography/    # Shot detection, style classification
│   │   ├── audio/             # Whisper + Librosa
│   │   ├── characters/        # Face detection & tracking
│   │   └── narrative/         # Gemini AI analysis
│   ├── database/              # Database layer
│   │   ├── connection.py      # Database connection
│   │   ├── models.py          # SQLAlchemy models
│   │   └── database_operations.py
│   └── core/                   # Core utilities
│       ├── full_analysis_pipeline.py  # Orchestration
│       └── video_processor.py         # Video download/extraction
├── scripts/                    # Windows batch scripts
│   ├── start-api.bat
│   ├── start-worker.bat
│   ├── start-flower.bat
│   └── start-docker-services.bat
├── docker-compose.yml          # Docker services
├── requirements.txt            # Python dependencies
├── setup-windows.ps1          # Windows setup script
└── .env.example               # Configuration template
```

## 🔧 Configuration

See `.env.example` for all configuration options.

### Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://aicine_user:aicine_pass@localhost:5432/aicine` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `GEMINI_API_KEY` | Google Gemini API key (required) | - |
| `WHISPER_MODEL` | Whisper model size | `base` |
| `FRAME_EXTRACTION_FPS` | Frame extraction rate | `1.0` |
| `SUPABASE_URL` | Supabase project URL for showcase sync (optional) | - |
| `SUPABASE_SERVICE_KEY` | Supabase service role key for showcase sync (optional) | - |

## 📚 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `POST` | `/api/analyze` | Submit video for analysis |
| `GET` | `/api/jobs/{job_id}` | Get job status |
| `GET` | `/api/films` | List all analyzed films |
| `GET` | `/api/films/{film_id}` | Get complete film analysis |
| `GET` | `/api/films/{film_id}/similar` | Find similar films |
| `GET` | `/api/stats` | Platform statistics |

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed API reference.

## 🐛 Troubleshooting

### Common Issues

**"Module cv2 not found"**
- Run: `pip install opencv-python-headless`

**"Cannot connect to Redis"**
- Make sure Redis is running: `docker-compose ps`
- Or start it: `docker-compose up -d redis`

**"FFmpeg not found"**
- Install with Chocolatey: `choco install ffmpeg`
- Or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

**"Database connection failed"**
- Check PostgreSQL is running: `docker-compose ps`
- Verify connection string in `.env`

**"Celery worker not starting on Windows"**
- Use the `--pool=solo` option (already in `start-worker.bat`)
- Make sure Redis is accessible

For more detailed troubleshooting, see [SETUP_WINDOWS.md](SETUP_WINDOWS.md).

## 🧪 Development

### Running Tests
```powershell
# Activate virtual environment
venv\Scripts\Activate.ps1

# Run tests (if test suite exists)
pytest
```

### Database Migrations
```powershell
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Code Style
```powershell
# Format code
black backend/

# Lint
flake8 backend/
```

## 🐳 Docker

### Hybrid Mode (Recommended for Windows)
Run PostgreSQL + Redis in Docker, API + Worker on Windows:

```powershell
# Start only database services
docker-compose up -d postgres redis

# Start API and Worker on Windows
scripts\start-api.bat       # Terminal 1
scripts\start-worker.bat    # Terminal 2
```

### Full Docker Mode
Run everything in Docker:

```bash
docker-compose up -d
```

## 📦 Tech Stack

- **FastAPI** - Modern Python web framework
- **Celery** - Distributed task queue
- **PostgreSQL** - Database with pgvector extension
- **Redis** - Message broker and cache
- **Whisper** - Speech-to-text
- **Librosa** - Audio analysis
- **CLIP** - Visual style classification
- **Gemini AI** - Narrative analysis
- **InsightFace** - Face detection (Windows-compatible)
- **OpenCV** - Video processing
- **yt-dlp** - Video download
- **PySceneDetect** - Shot detection

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation:** [SETUP_WINDOWS.md](SETUP_WINDOWS.md) | [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Issues:** [GitHub Issues](https://github.com/2800mhz/AIcineDB-backend/issues)
- **API Reference:** http://localhost:8000/docs (when running)

## 💡 Tips

- Use **hybrid mode** for best Windows development experience
- Start with **base** Whisper model, upgrade to **medium** for better accuracy
- Monitor tasks with **Flower** at http://localhost:5555
- Check logs with: `docker-compose logs -f` (for Docker services)

---

**Need Help?** Check [SETUP_WINDOWS.md](SETUP_WINDOWS.md) for detailed setup instructions or open an issue on GitHub.