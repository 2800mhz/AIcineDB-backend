@echo off
REM ============================================================================
REM AIcineDB Backend - Start Celery Worker
REM ============================================================================

echo.
echo ==================================================
echo   Starting AIcineDB Celery Worker
echo ==================================================
echo.

REM Check if virtual environment exists
if not exist venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run setup-windows.ps1 first
    echo.
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo.
    echo Using default configuration...
    echo Please create .env file for custom settings
    echo.
)

REM Check if Redis is running
echo Checking Redis connection...
docker ps | findstr redis >nul
if errorlevel 1 (
    echo [WARNING] Redis container not detected
    echo Make sure Redis is running on localhost:6379
    echo.
)

REM Activate virtual environment and start worker
echo Starting Celery worker...
echo.
echo Press Ctrl+C to stop the worker
echo.

call venv\Scripts\activate.bat
celery -A backend.tasks.celery_app worker --loglevel=info -E --pool=solo
