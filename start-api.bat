@echo off
REM ============================================================================
REM AIcineDB Backend - Start FastAPI Server
REM ============================================================================

echo.
echo ==================================================
echo   Starting AIcineDB FastAPI Server
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

REM Activate virtual environment and start server
echo Starting server on http://localhost:8000
echo API documentation: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

call venv\Scripts\activate.bat
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
