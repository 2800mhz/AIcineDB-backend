# Docker Setup Guide

This guide explains how to run the AIcineDB backend using Docker and docker-compose.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0 or higher
- At least 4GB of free disk space for images
- Environment variables configured (see below)

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your API keys and configuration:
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_SERVICE_KEY`: Your Supabase service key

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Check service status:**
   ```bash
   docker-compose ps
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f worker
   ```

## Services

The Docker Compose setup includes:

### PostgreSQL (with pgvector)
- **Container**: `aicine_postgres`
- **Port**: 5432
- **Purpose**: Main database with vector search capabilities
- **Volume**: `postgres_data` for data persistence

### Redis
- **Container**: `aicine_redis`
- **Port**: 6379
- **Purpose**: Message broker for Celery task queue

### FastAPI API
- **Container**: `aicine_api`
- **Port**: 8000
- **Purpose**: REST API server
- **Health Check**: `http://localhost:8000/health`
- **API Docs**: `http://localhost:8000/docs`

### Celery Worker
- **Container**: `aicine_worker`
- **Purpose**: Background task processor for video analysis
- **Features**: 
  - Playwright browser for web scraping
  - FFmpeg for video/audio processing
  - Whisper for audio transcription
  - AI models for analysis

### Flower (Celery Monitoring)
- **Container**: `aicine_flower`
- **Port**: 5555
- **Purpose**: Monitor Celery tasks
- **Dashboard**: `http://localhost:5555`

## Architecture

### Dockerfiles

1. **`Dockerfile`** - Main production Dockerfile for Railway deployment
   - Includes all dependencies (Playwright, FFmpeg, etc.)
   - Optimized for cloud deployment

2. **`docker/Dockerfile.api`** - API service specific
   - FastAPI application
   - Includes entrypoint for initialization
   - Health checks enabled

3. **`docker/Dockerfile.worker`** - Celery worker specific
   - Background task processing
   - Same dependencies as API
   - Optimized for long-running tasks

### Key Features

- **Playwright Support**: Chromium browser installed for web scraping
- **FFmpeg**: Video/audio processing capabilities
- **System Dependencies**: All required libraries for OpenCV, audio processing, etc.
- **Health Checks**: All services have health checks for reliability
- **Auto-restart**: Services restart automatically on failure
- **Environment Variables**: Comprehensive configuration via environment

## Environment Variables

### Required Variables

```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# Database (defaults work for docker-compose)
DATABASE_URL=postgresql://aicine_user:aicine_pass@postgres:5432/aicine

# Redis (defaults work for docker-compose)
REDIS_URL=redis://redis:6379
```

### Optional Variables

```bash
# Application
APP_ENV=development
DEBUG=true
API_PORT=8000

# Analysis Settings
WHISPER_MODEL=base
FRAME_EXTRACTION_FPS=1.0
CHARACTER_DETECTION_FPS=2.0

# Celery Worker
CELERY_WORKER_CONCURRENCY=2
CELERY_TASK_TIME_LIMIT=7200

# Content Aggregation
AI_FILTER_ENABLED=true
AI_RELEVANCE_THRESHOLD_FESTIVALS=60
AI_RELEVANCE_THRESHOLD_NEWS=70
```

## Common Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d api
docker-compose up -d worker
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes database data)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f postgres
```

### Rebuild Images
```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build api
docker-compose build worker

# Rebuild with no cache (clean build)
docker-compose build --no-cache
```

### Execute Commands in Container
```bash
# Open shell in API container
docker-compose exec api bash

# Run Python script
docker-compose exec api python -m backend.scripts.your_script

# Access PostgreSQL
docker-compose exec postgres psql -U aicine_user -d aicine
```

### Database Operations
```bash
# View database logs
docker-compose logs -f postgres

# Backup database
docker-compose exec postgres pg_dump -U aicine_user aicine > backup.sql

# Restore database
docker-compose exec -T postgres psql -U aicine_user aicine < backup.sql

# Access psql shell
docker-compose exec postgres psql -U aicine_user -d aicine
```

## Development Workflow

### Hot Reload Development

The docker-compose setup includes volume mounts for hot reloading:

```yaml
volumes:
  - ./backend:/app/backend
  - ./data:/app/data
  - ./analyses:/app/analyses
```

Changes to Python files in `./backend` will automatically reload the API and worker services.

### Running Tests

```bash
# Run tests in API container
docker-compose exec api pytest

# Run specific test file
docker-compose exec api pytest tests/test_api.py

# Run with coverage
docker-compose exec api pytest --cov=backend
```

## Troubleshooting

### Services Not Starting

1. **Check service status:**
   ```bash
   docker-compose ps
   ```

2. **View service logs:**
   ```bash
   docker-compose logs api
   docker-compose logs worker
   ```

3. **Check health:**
   ```bash
   docker-compose exec api curl http://localhost:8000/health
   ```

### Database Connection Issues

1. **Verify PostgreSQL is running:**
   ```bash
   docker-compose ps postgres
   ```

2. **Check PostgreSQL logs:**
   ```bash
   docker-compose logs postgres
   ```

3. **Test connection:**
   ```bash
   docker-compose exec postgres pg_isready -U aicine_user
   ```

### Redis Connection Issues

1. **Check Redis:**
   ```bash
   docker-compose exec redis redis-cli ping
   ```

2. **View Redis logs:**
   ```bash
   docker-compose logs redis
   ```

### Worker Not Processing Tasks

1. **Check worker logs:**
   ```bash
   docker-compose logs -f worker
   ```

2. **Check Flower dashboard:**
   - Open `http://localhost:5555`
   - View active workers and tasks

3. **Restart worker:**
   ```bash
   docker-compose restart worker
   ```

### Playwright Issues

If you encounter Playwright-related errors:

1. **Verify Chromium is installed:**
   ```bash
   docker-compose exec worker playwright install chromium
   ```

2. **Check browser dependencies:**
   ```bash
   docker-compose exec worker playwright install-deps chromium
   ```

### Port Conflicts

If ports are already in use:

1. **Change ports in docker-compose.yml:**
   ```yaml
   ports:
     - "8001:8000"  # Map to different host port
   ```

2. **Or set in .env file:**
   ```bash
   API_PORT=8001
   POSTGRES_PORT=5433
   REDIS_PORT=6380
   ```

## Performance Optimization

### Production Deployment

For production, consider:

1. **Increase worker concurrency:**
   ```bash
   CELERY_WORKER_CONCURRENCY=4
   ```

2. **Adjust task time limits:**
   ```bash
   CELERY_TASK_TIME_LIMIT=10800  # 3 hours
   ```

3. **Use external database:**
   - Comment out postgres service
   - Set DATABASE_URL to external PostgreSQL

4. **Use external Redis:**
   - Comment out redis service
   - Set REDIS_URL to external Redis

### Resource Limits

Add resource limits in docker-compose.yml:

```yaml
services:
  worker:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Security Considerations

1. **Never commit `.env` file** - Contains sensitive API keys
2. **Use secrets management** in production (Docker secrets, vault, etc.)
3. **Change default passwords** in .env file
4. **Use SSL/TLS** for external database connections
5. **Regularly update Docker images** for security patches

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Playwright Documentation](https://playwright.dev/python/)
