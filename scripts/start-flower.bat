@echo off
REM Start Flower - Celery Monitoring Dashboard
REM This script starts the Flower web interface for monitoring Celery tasks

echo ========================================
echo   AIcineDB - Starting Flower Dashboard
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "%~dp0..\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%~dp0..\venv\Scripts\activate.bat"
)

REM Check if .env exists
if not exist "%~dp0..\.env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

REM Check if Redis is running
echo Checking Redis connection...
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping()" 2>nul
if errorlevel 1 (
    echo.
    echo WARNING: Cannot connect to Redis on localhost:6379
    echo Please make sure Redis is running:
    echo   - Docker: docker-compose up -d redis
    echo   - Windows: Start Redis service
    echo.
    pause
    exit /b 1
)

echo Redis connection OK
echo.

REM Start Flower
echo Starting Flower dashboard...
echo Dashboard will be available at http://localhost:5555
echo.
echo Press Ctrl+C to stop Flower
echo.

cd /d "%~dp0.."
celery -A backend.tasks.celery_app flower --port=5555

pause
