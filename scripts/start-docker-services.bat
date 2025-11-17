@echo off
REM Start Docker Services (PostgreSQL + Redis)
REM This script starts the database and Redis containers

echo ========================================
echo   AIcineDB - Starting Docker Services
echo ========================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo Docker is running
echo.

REM Check if docker-compose.yml exists
if not exist "%~dp0..\docker-compose.yml" (
    echo ERROR: docker-compose.yml not found!
    pause
    exit /b 1
)

echo Starting PostgreSQL and Redis containers...
echo.

cd /d "%~dp0.."

REM Start only database services (not API/Worker which run on Windows)
docker-compose up -d postgres redis

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start Docker services
    echo Check the error messages above
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Docker Services Started!
echo ========================================
echo.
echo PostgreSQL: localhost:5432
echo   Database: aicine
echo   User:     aicine_user
echo   Password: aicine_pass
echo.
echo Redis: localhost:6379
echo.
echo To check status: docker-compose ps
echo To view logs:    docker-compose logs -f
echo To stop:         docker-compose down
echo.

pause
