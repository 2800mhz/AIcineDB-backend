@echo off
REM ============================================================================
REM AIcineDB Backend - Start All Development Services
REM ============================================================================
REM This script starts all services for development:
REM - PostgreSQL + Redis (Docker)
REM - FastAPI API server
REM - Celery worker
REM - Flower monitoring UI
REM ============================================================================

echo.
echo ==================================================
echo   AIcineDB Backend - Starting All Services
echo ==================================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo.
    echo Please run setup-windows.ps1 first or copy .env.example to .env
    echo.
    pause
    exit /b 1
)

REM Start Docker services (PostgreSQL + Redis)
echo [1/4] Starting Docker services...
echo.
docker-compose up -d postgres redis

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start Docker services
    echo.
    echo Make sure Docker Desktop is running
    pause
    exit /b 1
)

echo.
echo   [OK] Docker services started
echo   - PostgreSQL: localhost:5432
echo   - Redis: localhost:6379
echo.

REM Wait for services to be ready
echo Waiting for services to initialize...
timeout /t 5 /nobreak >nul
echo.

REM Start API server in new window
echo [2/4] Starting FastAPI server...
start "AIcineDB API" cmd /k "call venv\Scripts\activate.bat && uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload"
echo   [OK] API server starting in new window
echo.

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start Celery worker in new window
echo [3/4] Starting Celery worker...
start "AIcineDB Worker" cmd /k "call venv\Scripts\activate.bat && celery -A backend.tasks.celery_app worker --loglevel=info -E"
echo   [OK] Celery worker starting in new window
echo.

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start Flower in new window
echo [4/4] Starting Flower monitoring...
start "AIcineDB Flower" cmd /k "call venv\Scripts\activate.bat && celery -A backend.tasks.celery_app flower --port=5555"
echo   [OK] Flower monitoring starting in new window
echo.

echo ==================================================
echo   All Services Started!
echo ==================================================
echo.
echo Services:
echo   - API Server:    http://localhost:8000
echo   - API Docs:      http://localhost:8000/docs
echo   - Flower:        http://localhost:5555
echo   - PostgreSQL:    localhost:5432
echo   - Redis:         localhost:6379
echo.
echo Press any key to open API docs in browser...
pause >nul

start http://localhost:8000/docs

echo.
echo Services are running in separate windows.
echo Close those windows to stop the services.
echo.
pause
