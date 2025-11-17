# AIcineDB Backend - Windows Setup Script (FIXED)
# Complete automated setup for Windows development

param(
    [switch]$SkipDocker,
    [switch]$SkipFFmpeg,
    [switch]$SkipVenv
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  AIcineDB Backend - Windows Setup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================
Write-Host "[1/8] Checking prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  OK Python found: $pythonVersion" -ForegroundColor Green
    
    # Check if Python 3.10 or higher
    if ($pythonVersion -match "Python 3\.(\d+)") {
        $minorVersion = [int]$Matches[1]
        if ($minorVersion -lt 10) {
            Write-Host "  X Python 3.10 or higher required" -ForegroundColor Red
            exit 1
        }
    }
}
catch {
    Write-Host "  X Python not found. Please install Python 3.10+" -ForegroundColor Red
    Write-Host "    Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check PowerShell version
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host "  X PowerShell 5.0 or higher required" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# Step 2: Create Virtual Environment
# ============================================================================
if (-not $SkipVenv) {
    Write-Host "[2/8] Creating virtual environment..." -ForegroundColor Yellow
    
    if (Test-Path "venv") {
        Write-Host "  ! Virtual environment already exists, skipping..." -ForegroundColor Yellow
    }
    else {
        python -m venv venv
        Write-Host "  OK Virtual environment created" -ForegroundColor Green
    }
}
else {
    Write-Host "[2/8] Skipping virtual environment creation..." -ForegroundColor Gray
}

Write-Host ""

# ============================================================================
# Step 3: Activate Virtual Environment
# ============================================================================
Write-Host "[3/8] Activating virtual environment..." -ForegroundColor Yellow

$venvActivate = "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
    Write-Host "  OK Virtual environment activated" -ForegroundColor Green
}
else {
    Write-Host "  ! Virtual environment not found, continuing without it..." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 4: Upgrade pip
# ============================================================================
Write-Host "[4/8] Upgrading pip..." -ForegroundColor Yellow

try {
    python -m pip install --upgrade pip --quiet
    Write-Host "  OK pip upgraded" -ForegroundColor Green
}
catch {
    Write-Host "  ! Failed to upgrade pip, continuing..." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 5: Install Python Dependencies
# ============================================================================
Write-Host "[5/8] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "  This may take 10-15 minutes on first install..." -ForegroundColor Gray

try {
    pip install -r requirements.txt
    Write-Host "  OK Python dependencies installed" -ForegroundColor Green
}
catch {
    Write-Host "  X Failed to install Python dependencies" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try installing manually:" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

Write-Host ""

# ============================================================================
# Step 6: Install FFmpeg
# ============================================================================
if (-not $SkipFFmpeg) {
    Write-Host "[6/8] Checking FFmpeg..." -ForegroundColor Yellow
    
    try {
        $ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
        Write-Host "  OK FFmpeg already installed" -ForegroundColor Green
    }
    catch {
        Write-Host "  ! FFmpeg not found" -ForegroundColor Yellow
        Write-Host "  Attempting to install via Chocolatey..." -ForegroundColor Gray
        
        # Check if Chocolatey is installed
        try {
            choco --version | Out-Null
            Write-Host "  OK Chocolatey found" -ForegroundColor Green
            
            # Install FFmpeg
            choco install ffmpeg -y
            Write-Host "  OK FFmpeg installed via Chocolatey" -ForegroundColor Green
        }
        catch {
            Write-Host "  ! Chocolatey not found" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "  Please install FFmpeg manually:" -ForegroundColor Cyan
            Write-Host "  1. Download from: https://ffmpeg.org/download.html" -ForegroundColor White
            Write-Host "  2. Extract and add to PATH" -ForegroundColor White
            Write-Host "  OR install Chocolatey: https://chocolatey.org/install" -ForegroundColor White
            Write-Host "     Then run: choco install ffmpeg" -ForegroundColor White
        }
    }
}
else {
    Write-Host "[6/8] Skipping FFmpeg check..." -ForegroundColor Gray
}

Write-Host ""

# ============================================================================
# Step 7: Setup Environment File
# ============================================================================
Write-Host "[7/8] Setting up environment configuration..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "  OK Created .env from .env.example" -ForegroundColor Green
        Write-Host "  ! Please edit .env and add your API keys!" -ForegroundColor Yellow
    }
    else {
        Write-Host "  ! .env.example not found" -ForegroundColor Yellow
    }
}
else {
    Write-Host "  ! .env already exists, skipping..." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 8: Check Docker (Optional)
# ============================================================================
if (-not $SkipDocker) {
    Write-Host "[8/8] Checking Docker..." -ForegroundColor Yellow
    
    try {
        $dockerVersion = docker --version 2>&1
        Write-Host "  OK Docker found: $dockerVersion" -ForegroundColor Green
        
        # Check if Docker is running
        try {
            docker ps | Out-Null
            Write-Host "  OK Docker is running" -ForegroundColor Green
        }
        catch {
            Write-Host "  ! Docker is installed but not running" -ForegroundColor Yellow
            Write-Host "  Please start Docker Desktop" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "  ! Docker not found (optional)" -ForegroundColor Yellow
        Write-Host "  Install from: https://www.docker.com/products/docker-desktop" -ForegroundColor Gray
    }
}
else {
    Write-Host "[8/8] Skipping Docker check..." -ForegroundColor Gray
}

Write-Host ""

# ============================================================================
# Create scripts directory if needed
# ============================================================================
if (-not (Test-Path "scripts")) {
    New-Item -ItemType Directory -Path "scripts" | Out-Null
    Write-Host "OK Created scripts directory" -ForegroundColor Green
}

# ============================================================================
# Setup Complete
# ============================================================================
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Configure your environment:" -ForegroundColor Yellow
Write-Host "   Edit .env and add your GEMINI_API_KEY" -ForegroundColor White
Write-Host ""

Write-Host "2. Start database and Redis:" -ForegroundColor Yellow
Write-Host "   Option A - Docker (recommended):" -ForegroundColor Gray
Write-Host "     docker-compose up -d postgres redis" -ForegroundColor White
Write-Host "   Option B - Local installation:" -ForegroundColor Gray
Write-Host "     Install PostgreSQL with pgvector and Redis locally" -ForegroundColor White
Write-Host ""

Write-Host "3. Start the services:" -ForegroundColor Yellow
Write-Host "   API Server:    scripts\start-api.bat" -ForegroundColor White
Write-Host "   Worker:        scripts\start-worker.bat" -ForegroundColor White
Write-Host "   Flower UI:     scripts\start-flower.bat" -ForegroundColor White
Write-Host ""

Write-Host "4. Open the API documentation:" -ForegroundColor Yellow
Write-Host "   http://localhost:8000/docs" -ForegroundColor White
Write-Host ""

Write-Host "For detailed instructions, see:" -ForegroundColor Cyan
Write-Host "  SETUP_WINDOWS.md - Complete Windows setup guide" -ForegroundColor White
Write-Host "  README.md - Project overview and quick start" -ForegroundColor White
Write-Host ""

Write-Host "Setup complete! Happy coding!" -ForegroundColor Green
Write-Host ""