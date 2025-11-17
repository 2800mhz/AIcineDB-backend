@echo off
REM ============================================================================
REM AIcineDB Backend - Start Docker Services Only
REM ============================================================================
REM This script starts only the Docker containers (PostgreSQL + Redis)
REM Use this for hybrid Windows development
REM ============================================================================

echo.
echo ==================================================
echo   Starting Docker Services
echo ==================================================
echo.

docker-compose up -d postgres redis

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start Docker services
    echo.
    echo Make sure Docker Desktop is running
    echo.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo   Docker Services Started!
echo ==================================================
echo.
echo Services:
echo   - PostgreSQL: localhost:5432
echo   - Redis:      localhost:6379
echo.
echo Database:
echo   - Name:     aicine
echo   - User:     aicine_user
echo   - Password: aicine_pass
echo.
echo To view logs:
echo   docker-compose logs -f postgres
echo   docker-compose logs -f redis
echo.
echo To stop services:
echo   docker-compose down
echo.
pause
