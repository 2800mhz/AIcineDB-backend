# ============================================================================
# AIcineDB Backend - Windows Setup Script
# ============================================================================
# Complete environment setup for Windows development
# Usage: .\setup-windows.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AIcineDB Backend - Windows Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will set up your Windows development environment." -ForegroundColor White
Write-Host ""

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow
Write-Host ""

# Check Python
Write-Host "  Checking Python..." -ForegroundColor Gray
try {
    $pythonVersion = python --version 2>&1
    Write-Host "    ✓ $pythonVersion" -ForegroundColor Green
    
    # Check if Python 3.8+
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
    if ($versionMatch) {
        $majorVersion = [int]$Matches[1]
        $minorVersion = [int]$Matches[2]
        if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
            Write-Host "    ✗ Python 3.8+ required" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "    ✗ Python not found" -ForegroundColor Red
    Write-Host "    Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Check Docker (optional for hybrid mode)
Write-Host "  Checking Docker..." -ForegroundColor Gray
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "    ✓ $dockerVersion" -ForegroundColor Green
    $dockerInstalled = $true
} catch {
    Write-Host "    ⚠ Docker not found (optional for hybrid mode)" -ForegroundColor Yellow
    $dockerInstalled = $false
}

# Check FFmpeg
Write-Host "  Checking FFmpeg..." -ForegroundColor Gray
try {
    $ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host "    ✓ FFmpeg installed" -ForegroundColor Green
} catch {
    Write-Host "    ⚠ FFmpeg not found (required for video processing)" -ForegroundColor Yellow
    Write-Host "    Download from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  [OK] Prerequisites checked" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 2: Choose Deployment Mode
# ============================================================================
Write-Host "[2/7] Choose deployment mode..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Hybrid Mode (Docker for DB/Redis, Windows for API/Worker)" -ForegroundColor White
Write-Host "     - Easiest setup" -ForegroundColor Gray
Write-Host "     - PostgreSQL + Redis in Docker" -ForegroundColor Gray
Write-Host "     - FastAPI + Celery on Windows" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Pure Windows (All services on Windows)" -ForegroundColor White
Write-Host "     - Full Windows native" -ForegroundColor Gray
Write-Host "     - Requires PostgreSQL + Redis installation" -ForegroundColor Gray
Write-Host "     - More control, better performance" -ForegroundColor Gray
Write-Host ""

$mode = Read-Host "Select mode (1 or 2)"

if ($mode -eq "1") {
    $useDocker = $true
    Write-Host "  ✓ Selected: Hybrid Mode" -ForegroundColor Green
    
    if (-not $dockerInstalled) {
        Write-Host ""
        Write-Host "  ✗ Docker not found but required for hybrid mode" -ForegroundColor Red
        Write-Host "    Please install Docker Desktop from https://docker.com" -ForegroundColor Yellow
        exit 1
    }
} elseif ($mode -eq "2") {
    $useDocker = $false
    Write-Host "  ✓ Selected: Pure Windows Mode" -ForegroundColor Green
} else {
    Write-Host "  ✗ Invalid selection" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# Step 3: Create Virtual Environment
# ============================================================================
Write-Host "[3/7] Setting up Python virtual environment..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path "venv") {
    Write-Host "  Virtual environment already exists" -ForegroundColor Gray
    $recreate = Read-Host "  Recreate? (y/n)"
    if ($recreate -eq "y" -or $recreate -eq "Y") {
        Write-Host "  Removing old virtual environment..." -ForegroundColor Gray
        Remove-Item -Recurse -Force venv
        Write-Host "  Creating new virtual environment..." -ForegroundColor Gray
        python -m venv venv
    }
} else {
    Write-Host "  Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

Write-Host "  ✓ Virtual environment ready" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 4: Install Dependencies
# ============================================================================
Write-Host "[4/7] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  This may take several minutes..." -ForegroundColor Gray
Write-Host ""

# Activate virtual environment and install
& "venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "  ✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# Step 5: Setup Environment Configuration
# ============================================================================
Write-Host "[5/7] Setting up environment configuration..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path ".env") {
    Write-Host "  .env file already exists" -ForegroundColor Gray
    $overwrite = Read-Host "  Overwrite? (y/n)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "  Keeping existing .env file" -ForegroundColor Gray
    } else {
        Copy-Item ".env.example" ".env" -Force
        Write-Host "  ✓ Created .env from template" -ForegroundColor Green
        Write-Host ""
        Write-Host "  ⚠ IMPORTANT: Edit .env and set your GEMINI_API_KEY" -ForegroundColor Yellow
    }
} else {
    Copy-Item ".env.example" ".env" -Force
    Write-Host "  ✓ Created .env from template" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ⚠ IMPORTANT: Edit .env and set your GEMINI_API_KEY" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 6: Setup Docker Services (if hybrid mode)
# ============================================================================
if ($useDocker) {
    Write-Host "[6/7] Setting up Docker services..." -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "  Starting PostgreSQL + Redis containers..." -ForegroundColor Gray
    Write-Host ""
    
    # Start only postgres and redis services
    docker-compose up -d postgres redis
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "  ✓ Docker services started" -ForegroundColor Green
        Write-Host "    - PostgreSQL: localhost:5432" -ForegroundColor Gray
        Write-Host "    - Redis: localhost:6379" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "  ✗ Failed to start Docker services" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[6/7] Pure Windows mode - Database setup" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Please ensure PostgreSQL and Redis are installed and running:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  PostgreSQL:" -ForegroundColor White
    Write-Host "    - Download: https://www.postgresql.org/download/windows/" -ForegroundColor Gray
    Write-Host "    - Default port: 5432" -ForegroundColor Gray
    Write-Host "    - Create database: aicine" -ForegroundColor Gray
    Write-Host "    - Create user: aicine_user" -ForegroundColor Gray
    Write-Host "    - Enable pgvector extension" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Redis:" -ForegroundColor White
    Write-Host "    - Download: https://github.com/microsoftarchive/redis/releases" -ForegroundColor Gray
    Write-Host "    - Default port: 6379" -ForegroundColor Gray
    Write-Host ""
    Read-Host "  Press Enter when ready to continue..."
}

Write-Host ""

# ============================================================================
# Step 7: Create Directories
# ============================================================================
Write-Host "[7/7] Creating required directories..." -ForegroundColor Yellow
Write-Host ""

$directories = @("data", "analyses", "frames", "temp")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "  ✓ Created $dir/" -ForegroundColor Green
    } else {
        Write-Host "  ✓ $dir/ already exists" -ForegroundColor Gray
    }
}

Write-Host ""

# ============================================================================
# Setup Complete
# ============================================================================
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""

if ($useDocker) {
    Write-Host "  1. Edit .env and set your GEMINI_API_KEY" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  2. Start the services:" -ForegroundColor Yellow
    Write-Host "     .\run-dev-services.bat" -ForegroundColor White
    Write-Host ""
    Write-Host "  Or start individually:" -ForegroundColor Yellow
    Write-Host "     .\start-api.bat        # Start FastAPI server" -ForegroundColor White
    Write-Host "     .\start-worker.bat     # Start Celery worker" -ForegroundColor White
    Write-Host "     .\start-flower.bat     # Start Flower monitoring" -ForegroundColor White
} else {
    Write-Host "  1. Edit .env and update database/redis connection settings" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  2. Set your GEMINI_API_KEY in .env" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  3. Initialize the database:" -ForegroundColor Yellow
    Write-Host "     (Run the SQL scripts in docker/postgres/init.sql)" -ForegroundColor White
    Write-Host ""
    Write-Host "  4. Start the services:" -ForegroundColor Yellow
    Write-Host "     .\start-api.bat        # Start FastAPI server" -ForegroundColor White
    Write-Host "     .\start-worker.bat     # Start Celery worker" -ForegroundColor White
    Write-Host "     .\start-flower.bat     # Start Flower monitoring" -ForegroundColor White
}

Write-Host ""
Write-Host "  API Documentation: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Flower Dashboard: http://localhost:5555" -ForegroundColor White
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
