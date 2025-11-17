@echo off
REM Start AIcineDB API Server
REM This script starts the FastAPI development server

echo ========================================
echo   AIcineDB - Starting API Server
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

REM Start the API server
echo Starting FastAPI server on http://localhost:8000...
echo API docs will be available at http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0.."
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

pause
