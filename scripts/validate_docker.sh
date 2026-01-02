#!/bin/bash
# Docker Configuration Validation Script
# This script validates the Docker setup without building images

set -e

echo "========================================"
echo "Docker Configuration Validation"
echo "========================================"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi
echo "✅ Docker is installed"

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose v2 is not available"
    exit 1
fi
echo "✅ Docker Compose v2 is available"

# Validate docker-compose.yml syntax
echo ""
echo "Validating docker-compose.yml..."
if docker compose config --quiet; then
    echo "✅ docker-compose.yml syntax is valid"
else
    echo "❌ docker-compose.yml has syntax errors"
    exit 1
fi

# Validate Dockerfiles syntax
echo ""
echo "Validating Dockerfiles..."

# Check main Dockerfile
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile exists"
else
    echo "❌ Dockerfile not found"
    exit 1
fi

# Check docker/Dockerfile.api
if [ -f "docker/Dockerfile.api" ]; then
    echo "✅ docker/Dockerfile.api exists"
else
    echo "❌ docker/Dockerfile.api not found"
    exit 1
fi

# Check docker/Dockerfile.worker
if [ -f "docker/Dockerfile.worker" ]; then
    echo "✅ docker/Dockerfile.worker exists"
else
    echo "❌ docker/Dockerfile.worker not found"
    exit 1
fi

# Check entrypoint script
echo ""
echo "Validating entrypoint script..."
if [ -f "docker/entrypoint.sh" ]; then
    if bash -n docker/entrypoint.sh; then
        echo "✅ docker/entrypoint.sh syntax is valid"
    else
        echo "❌ docker/entrypoint.sh has syntax errors"
        exit 1
    fi
    
    # Check if it's executable
    if [ -x "docker/entrypoint.sh" ]; then
        echo "✅ docker/entrypoint.sh is executable"
    else
        echo "⚠️  docker/entrypoint.sh is not executable (will be fixed in Dockerfile)"
    fi
else
    echo "❌ docker/entrypoint.sh not found"
    exit 1
fi

# Check .dockerignore
echo ""
echo "Validating .dockerignore..."
if [ -f ".dockerignore" ]; then
    echo "✅ .dockerignore exists"
else
    echo "⚠️  .dockerignore not found (recommended)"
fi

# Check .env.example
echo ""
echo "Validating environment configuration..."
if [ -f ".env.example" ]; then
    echo "✅ .env.example exists"
else
    echo "⚠️  .env.example not found"
fi

# Check if .env exists
if [ -f ".env" ]; then
    echo "✅ .env file exists"
else
    echo "⚠️  .env file not found (copy from .env.example)"
fi

# Check required directories
echo ""
echo "Checking directories..."
for dir in "backend" "docker"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir/ exists"
    else
        echo "❌ $dir/ not found"
        exit 1
    fi
done

# Check optional postgres init directory
if [ -d "docker/postgres" ]; then
    echo "✅ docker/postgres/ exists"
else
    echo "⚠️  docker/postgres/ not found (optional, but recommended for database init)"
fi

# Check requirements.txt
echo ""
echo "Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt exists"
    
    # Check for key dependencies
    if grep -q "playwright" requirements.txt; then
        echo "✅ Playwright dependency found"
    else
        echo "❌ Playwright not found in requirements.txt (required for worker)"
        exit 1
    fi
    
    if grep -q "fastapi" requirements.txt; then
        echo "✅ FastAPI dependency found"
    else
        echo "❌ FastAPI not found in requirements.txt"
        exit 1
    fi
    
    if grep -q "celery" requirements.txt; then
        echo "✅ Celery dependency found"
    else
        echo "❌ Celery not found in requirements.txt"
        exit 1
    fi
else
    echo "❌ requirements.txt not found"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ All validation checks passed!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your API keys"
echo "2. Run: docker compose build"
echo "3. Run: docker compose up -d"
echo "4. Check: docker compose ps"
echo "5. View API docs at: http://localhost:8000/docs"
echo ""
