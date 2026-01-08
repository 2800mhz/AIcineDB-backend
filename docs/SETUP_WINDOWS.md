# Windows Setup Guide - AIcineDB Backend

Complete step-by-step guide for setting up AIcineDB Backend on Windows.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup](#quick-setup)
- [Hybrid Setup (Recommended)](#hybrid-setup-recommended)
- [Pure Windows Setup](#pure-windows-setup)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Prerequisites

### Required Software

1. **Python 3.10 or higher**
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   - Verify: `python --version`

2. **FFmpeg**
   - Option A: Install via Chocolatey (easiest)
     ```powershell
     # Install Chocolatey first (https://chocolatey.org/install)
     choco install ffmpeg -y
     ```
   - Option B: Manual installation
     - Download: https://ffmpeg.org/download.html
     - Extract to `C:\ffmpeg`
     - Add `C:\ffmpeg\bin` to PATH
   - Verify: `ffmpeg -version`

3. **Git**
   - Download: https://git-scm.com/download/win
   - Verify: `git --version`

### Optional (but Recommended)

4. **Docker Desktop** (for database services)
   - Download: https://www.docker.com/products/docker-desktop
   - Requires Windows 10/11 Pro or WSL2
   - Alternative: Manual PostgreSQL + Redis installation

5. **Visual Studio Code** (or any IDE)
   - Download: https://code.visualstudio.com/
   - Recommended extensions:
     - Python
     - Docker
     - PowerShell

---

## Quick Setup

The fastest way to get started:

```powershell
# 1. Clone repository
git clone https://github.com/2800mhz/AIcineDB-backend.git
cd AIcineDB-backend

# 2. Run setup script
.\setup-windows.ps1

# 3. Configure environment
notepad .env
# Add your GEMINI_API_KEY

# 4. Start Docker services (PostgreSQL + Redis)
scripts\start-docker-services.bat

# 5. Start API server (new terminal)
scripts\start-api.bat

# 6. Start worker (new terminal)
scripts\start-worker.bat

# 7. Open browser
start http://localhost:8000/docs
```

Done! You're ready to analyze films.

---

## Hybrid Setup (Recommended)

This setup runs PostgreSQL and Redis in Docker, but API and Worker on Windows. Best for development.

### Step 1: Install Docker Desktop

1. Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Start Docker Desktop
3. Verify Docker is running:
   ```powershell
   docker --version
   docker ps
   ```

### Step 2: Clone and Setup

```powershell
# Clone repository
git clone https://github.com/2800mhz/AIcineDB-backend.git
cd AIcineDB-backend

# Run automated setup
.\setup-windows.ps1
```

The setup script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install Python dependencies
- ✅ Check/install FFmpeg
- ✅ Create .env file
- ✅ Check Docker availability

### Step 3: Configure Environment

Edit `.env` file:

```powershell
notepad .env
```

**Minimal required configuration:**

```ini
# Database (leave as-is for Docker)
DATABASE_URL=postgresql://aicine_user:aicine_pass@localhost:5432/aicine

# Redis (leave as-is for Docker)
REDIS_URL=redis://localhost:6379

# REQUIRED: Add your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here
```

Get your Gemini API key from: https://makersuite.google.com/app/apikey

### Step 4: Start Database Services

```powershell
scripts\start-docker-services.bat
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379

Verify services are running:
```powershell
docker-compose ps
```

### Step 5: Start Application Services

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

### Step 6: Verify Setup

1. **API Health Check:**
   ```powershell
   curl http://localhost:8000/health
   ```

2. **Open API Docs:**
   - Browser: http://localhost:8000/docs

3. **Test Analysis:**
   - Go to http://localhost:8000/docs
   - Try the `POST /api/analyze` endpoint
   - Use a short YouTube video URL

---

## Pure Windows Setup

Run everything natively on Windows (no Docker). Requires more manual setup.

### Step 1: Install PostgreSQL

1. **Download PostgreSQL 15+**
   - https://www.postgresql.org/download/windows/
   - Include pgAdmin during installation

2. **Install pgvector extension**
   ```powershell
   # Download pgvector for Windows
   # https://github.com/pgvector/pgvector/releases
   
   # Or use pre-built binaries:
   # Download from releases page and copy to PostgreSQL extension folder
   ```

3. **Create database**
   ```sql
   -- Open pgAdmin or psql
   CREATE DATABASE aicine;
   CREATE USER aicine_user WITH PASSWORD 'aicine_pass';
   GRANT ALL PRIVILEGES ON DATABASE aicine TO aicine_user;
   
   -- Connect to aicine database and enable pgvector
   \c aicine
   CREATE EXTENSION vector;
   ```

4. **Update .env**
   ```ini
   DATABASE_URL=postgresql://aicine_user:aicine_pass@localhost:5432/aicine
   ```

### Step 2: Install Redis

1. **Download Redis for Windows**
   - Option A: Use Memurai (Redis-compatible)
     - https://www.memurai.com/
   - Option B: Use WSL2 with Redis
     ```powershell
     wsl --install
     wsl sudo apt-get install redis-server
     wsl sudo service redis-server start
     ```

2. **Update .env**
   ```ini
   REDIS_URL=redis://localhost:6379
   ```

### Step 3: Run Setup and Start Services

Same as hybrid setup, but skip the Docker steps:

```powershell
# Setup
.\setup-windows.ps1

# Configure
notepad .env

# Start services (without Docker)
scripts\start-api.bat       # Terminal 1
scripts\start-worker.bat    # Terminal 2
scripts\start-flower.bat    # Terminal 3
```

---

## Configuration

### Environment Variables

See `.env.example` for all options. Key settings:

#### Database
```ini
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

#### Redis
```ini
REDIS_URL=redis://localhost:6379
```

#### API Keys
```ini
# Required for narrative analysis
GEMINI_API_KEY=your_key_here

# Optional
OPENAI_API_KEY=your_key_here
```

#### Analysis Settings
```ini
# Whisper model: tiny, base, small, medium, large
WHISPER_MODEL=base

# Frame extraction rate
FRAME_EXTRACTION_FPS=1.0

# Character detection rate
CHARACTER_DETECTION_FPS=2.0
```

#### Worker Settings
```ini
# Number of concurrent tasks
CELERY_WORKER_CONCURRENCY=2

# Task timeout (seconds)
CELERY_TASK_TIME_LIMIT=7200
```

### Performance Tuning

**Low-end PC (8GB RAM):**
```ini
WHISPER_MODEL=tiny
CELERY_WORKER_CONCURRENCY=1
FRAME_EXTRACTION_FPS=0.5
```

**Mid-range PC (16GB RAM):**
```ini
WHISPER_MODEL=base
CELERY_WORKER_CONCURRENCY=2
FRAME_EXTRACTION_FPS=1.0
```

**High-end PC (32GB+ RAM, GPU):**
```ini
WHISPER_MODEL=medium
CELERY_WORKER_CONCURRENCY=4
FRAME_EXTRACTION_FPS=2.0
```

---

## Troubleshooting

### Common Issues

#### 1. "Python not found"

**Problem:** `python` command not recognized

**Solution:**
```powershell
# Try python3 instead
python3 --version

# Or add Python to PATH manually
# System Properties → Environment Variables → Path → Add Python folder
```

#### 2. "FFmpeg not found"

**Problem:** FFmpeg not installed or not in PATH

**Solution:**
```powershell
# Check if installed
ffmpeg -version

# Install via Chocolatey
choco install ffmpeg -y

# Or add to PATH manually after downloading
```

#### 3. "Cannot connect to Redis"

**Problem:** Redis not running

**Solution:**
```powershell
# If using Docker
docker-compose up -d redis
docker-compose ps

# Check connection
python -c "import redis; r=redis.Redis(); print(r.ping())"
```

#### 4. "Database connection failed"

**Problem:** PostgreSQL not running or wrong credentials

**Solution:**
```powershell
# If using Docker
docker-compose up -d postgres
docker-compose logs postgres

# Check connection
python -c "import psycopg2; conn=psycopg2.connect('postgresql://aicine_user:aicine_pass@localhost:5432/aicine'); print('OK')"

# Verify .env has correct DATABASE_URL
```

#### 5. "Celery worker fails on Windows"

**Problem:** Celery doesn't support standard pool on Windows

**Solution:**
Already fixed in `start-worker.bat` with `--pool=solo` flag.

If running manually:
```powershell
celery -A backend.tasks.celery_app worker --pool=solo --loglevel=info
```

#### 6. "ImportError: No module named 'cv2'"

**Problem:** OpenCV not installed

**Solution:**
```powershell
pip install opencv-python-headless
```

#### 7. "Out of memory during analysis"

**Problem:** Large video or insufficient RAM

**Solution:**
- Use smaller Whisper model: `WHISPER_MODEL=tiny`
- Reduce frame extraction rate: `FRAME_EXTRACTION_FPS=0.5`
- Analyze shorter videos
- Close other applications

#### 8. "Port already in use"

**Problem:** Port 8000 or 6379 or 5432 already taken

**Solution:**
```powershell
# Check what's using the port
netstat -ano | findstr :8000

# Kill the process or change port in .env
API_PORT=8001
```

### Checking Logs

**API Server logs:**
- Console output from `start-api.bat`

**Worker logs:**
- Console output from `start-worker.bat`

**Docker service logs:**
```powershell
docker-compose logs -f postgres
docker-compose logs -f redis
```

**Database logs:**
```powershell
docker-compose logs postgres
```

### Testing Components

**Test Redis:**
```powershell
python -c "import redis; r=redis.Redis(host='localhost', port=6379); print('Redis OK' if r.ping() else 'Redis FAIL')"
```

**Test PostgreSQL:**
```powershell
python -c "from backend.database.connection import database; import asyncio; asyncio.run(database.connect()); print('DB OK')"
```

**Test API:**
```powershell
curl http://localhost:8000/health
```

**Test Celery:**
```powershell
# In Python console
from backend.tasks.video_tasks import test_task
result = test_task.delay("Hello!")
print(result.get())
```

---

## Advanced Topics

### Using GPU Acceleration

If you have an NVIDIA GPU:

1. **Install CUDA Toolkit**
   - https://developer.nvidia.com/cuda-downloads

2. **Install PyTorch with CUDA**
   ```powershell
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Verify GPU**
   ```python
   import torch
   print(torch.cuda.is_available())  # Should be True
   ```

Whisper and CLIP will automatically use GPU.

### Custom Models

**Use larger Whisper model:**
```ini
WHISPER_MODEL=medium  # or large
```

**Use custom CLIP model:**
Edit `backend/analyzers/cinematography/style_classifier.py`

### Database Migrations

```powershell
# Install Alembic
pip install alembic

# Initialize (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head
```

### Custom Task Queues

Edit `backend/tasks/celery_app.py` to add task routing:

```python
app.conf.task_routes = {
    'backend.tasks.video_tasks.analyze_film_complete': {'queue': 'video_analysis'},
    'backend.tasks.video_tasks.cleanup_old_files': {'queue': 'maintenance'},
}
```

Start workers for specific queues:
```powershell
celery -A backend.tasks.celery_app worker -Q video_analysis --pool=solo
celery -A backend.tasks.celery_app worker -Q maintenance --pool=solo
```

### Monitoring and Observability

**Flower - Celery monitoring:**
- UI: http://localhost:5555
- Monitor tasks, workers, queues

**PostgreSQL monitoring:**
```sql
-- Active connections
SELECT * FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('aicine'));

-- Table sizes
SELECT 
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Redis monitoring:**
```powershell
# CLI
redis-cli
> INFO
> DBSIZE
> KEYS *
```

### Production Deployment

For production on Windows Server:

1. **Use production WSGI server:**
   ```powershell
   pip install gunicorn  # If supported on Windows
   # Or use uvicorn with more workers
   uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Setup as Windows Service:**
   - Use NSSM (Non-Sucking Service Manager)
   - https://nssm.cc/

3. **Configure reverse proxy:**
   - Use IIS or nginx for Windows
   - Handle SSL/TLS termination

4. **Setup monitoring:**
   - Prometheus + Grafana
   - Windows Performance Monitor

5. **Backup strategy:**
   - Regular PostgreSQL backups
   - Redis persistence (RDB/AOF)

---

## Getting Help

1. **Check logs** - Most issues show up in console output
2. **Review this guide** - Search for your error message
3. **GitHub Issues** - Search or create new issue
4. **API Documentation** - See API_DOCUMENTATION.md

---

## Next Steps

After successful setup:

1. ✅ Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
2. ✅ Try analyzing a short test video
3. ✅ Explore the API at http://localhost:8000/docs
4. ✅ Monitor tasks in Flower at http://localhost:5555
5. ✅ Start building your film analysis application!

---

**Happy analyzing! 🎬**
