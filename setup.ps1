# AI Cine Analyzer - Setup Script
# Usage: .\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  AI Cine Analyzer - Full Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Backup
Write-Host "[1/5] Backing up existing files..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    Copy-Item "requirements.txt" "requirements.txt.backup" -Force
    Write-Host "  - requirements.txt backed up" -ForegroundColor Gray
}
if (Test-Path "docker\Dockerfile.api") {
    Copy-Item "docker\Dockerfile.api" "docker\Dockerfile.api.backup" -Force
    Write-Host "  - Dockerfile.api backed up" -ForegroundColor Gray
}
if (Test-Path "docker\Dockerfile.worker") {
    Copy-Item "docker\Dockerfile.worker" "docker\Dockerfile.worker.backup" -Force
    Write-Host "  - Dockerfile.worker backed up" -ForegroundColor Gray
}
Write-Host "  [OK] Backup complete" -ForegroundColor Green
Write-Host ""

# Step 2: Check requirements.txt
Write-Host "[2/5] Checking requirements.txt..." -ForegroundColor Yellow
Write-Host "  ✓ requirements.txt already Windows-optimized (no dlib/face-recognition)" -ForegroundColor Green
Write-Host ""

# Step 3: Update Dockerfile.api
Write-Host "[3/5] Updating Dockerfile.api..." -ForegroundColor Yellow
$dockerfileApi = @'
FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    ffmpeg \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    libboost-thread-dev \
    && rm -rf /var/lib/apt/lists/*
COPY ./backend /app/backend
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
'@

$dockerfileApi | Out-File -FilePath "docker\Dockerfile.api" -Encoding ASCII -NoNewline
Write-Host "  [OK] Dockerfile.api updated" -ForegroundColor Green
Write-Host ""

# Step 4: Update Dockerfile.worker
Write-Host "[4/5] Updating Dockerfile.worker..." -ForegroundColor Yellow
$dockerfileWorker = @'
FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    ffmpeg \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    libboost-thread-dev \
    && rm -rf /var/lib/apt/lists/*
COPY ./backend /app/backend
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
CMD ["celery", "-A", "backend.tasks.celery_app", "worker", "--loglevel=info"]
'@

$dockerfileWorker | Out-File -FilePath "docker\Dockerfile.worker" -Encoding ASCII -NoNewline
Write-Host "  [OK] Dockerfile.worker updated" -ForegroundColor Green
Write-Host ""

# Step 5: Build
Write-Host "[5/5] Ready to build!" -ForegroundColor Yellow
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Files Updated Successfully!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Docker build will take 15-20 minutes" -ForegroundColor Yellow
Write-Host "           (dlib compilation is slow)" -ForegroundColor Yellow
Write-Host ""

$buildNow = Read-Host "Start Docker build now? (y/n)"

if ($buildNow -eq "y" -or $buildNow -eq "Y") {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host "  Starting Docker Build" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Clean old containers
    Write-Host "Cleaning old containers..." -ForegroundColor Yellow
    docker-compose down -v
    Write-Host ""
    
    # Build
    Write-Host "Starting build (15-20 minutes)..." -ForegroundColor Cyan
    Write-Host "TIP: Open another terminal and run 'docker stats' to monitor" -ForegroundColor Gray
    Write-Host ""
    
    $buildStart = Get-Date
    docker-compose build --no-cache
    $buildEnd = Get-Date
    $buildDuration = ($buildEnd - $buildStart).TotalMinutes
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=====================================" -ForegroundColor Green
        Write-Host "  Build Successful!" -ForegroundColor Green
        Write-Host "  Time: $([math]::Round($buildDuration, 1)) minutes" -ForegroundColor Green
        Write-Host "=====================================" -ForegroundColor Green
        Write-Host ""
        
        # Start containers
        Write-Host "Starting containers..." -ForegroundColor Cyan
        docker-compose up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "=====================================" -ForegroundColor Green
            Write-Host "  Setup Complete!" -ForegroundColor Green
            Write-Host "=====================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "Next Steps:" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "1. Check logs:" -ForegroundColor Yellow
            Write-Host "   docker-compose logs -f api" -ForegroundColor White
            Write-Host ""
            Write-Host "2. Health check:" -ForegroundColor Yellow
            Write-Host "   curl http://localhost:8000/health" -ForegroundColor White
            Write-Host ""
            Write-Host "3. Open API docs:" -ForegroundColor Yellow
            Write-Host "   http://localhost:8000/docs" -ForegroundColor White
            Write-Host ""
            Write-Host "4. Open Flower (task monitor):" -ForegroundColor Yellow
            Write-Host "   http://localhost:5555" -ForegroundColor White
            Write-Host ""
            
            # Show logs
            Write-Host "Press Ctrl+C to stop watching logs..." -ForegroundColor Gray
            Start-Sleep -Seconds 2
            docker-compose logs -f
            
        } else {
            Write-Host ""
            Write-Host "ERROR: Failed to start containers" -ForegroundColor Red
            Write-Host "Check logs: docker-compose logs" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host ""
        Write-Host "=====================================" -ForegroundColor Red
        Write-Host "  Build Failed!" -ForegroundColor Red
        Write-Host "=====================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please check the error messages above" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "- Not enough RAM (need 8GB+)" -ForegroundColor Gray
        Write-Host "- Not enough disk space (need 10GB+)" -ForegroundColor Gray
        Write-Host "- Network issues downloading packages" -ForegroundColor Gray
        Write-Host ""
        Write-Host "To retry:" -ForegroundColor Cyan
        Write-Host "  docker-compose build --no-cache" -ForegroundColor White
        Write-Host "  docker-compose up -d" -ForegroundColor White
    }
    
} else {
    Write-Host ""
    Write-Host "Build skipped." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To build manually, run:" -ForegroundColor Cyan
    Write-Host "  docker-compose build --no-cache" -ForegroundColor White
    Write-Host "  docker-compose up -d" -ForegroundColor White
    Write-Host ""
}

Write-Host ""
Write-Host "Setup script completed!" -ForegroundColor Cyan
Write-Host ""