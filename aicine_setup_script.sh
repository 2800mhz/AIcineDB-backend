#!/bin/bash

# AI Cine Analyzer - Complete Setup Script
# Sets up the entire project with all modules

set -e

echo "🎬 AI Cine Analyzer - Complete Setup"
echo "===================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed. Install: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not installed"
    exit 1
fi

echo "✓ Docker and Docker Compose installed"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p backend/api
mkdir -p backend/analyzers/cinematography
mkdir -p backend/analyzers/narrative
mkdir -p backend/analyzers/audio
mkdir -p backend/analyzers/characters
mkdir -p backend/core
mkdir -p backend/models
mkdir -p backend/database
mkdir -p backend/tasks
mkdir -p docker/postgres
mkdir -p tests
mkdir -p data/{videos,frames,audio}
mkdir -p analyses
mkdir -p logs

# Create __init__.py files
echo "📝 Creating Python package files..."
touch backend/__init__.py
touch backend/api/__init__.py
touch backend/analyzers/__init__.py
touch backend/analyzers/cinematography/__init__.py
touch backend/analyzers/narrative/__init__.py
touch backend/analyzers/audio/__init__.py
touch backend/analyzers/characters/__init__.py
touch backend/core/__init__.py
touch backend/models/__init__.py
touch backend/database/__init__.py
touch backend/tasks/__init__.py
touch tests/__init__.py

echo "✓ Directory structure created"
echo ""

# Setup .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ .env created from .env.example"
    else
        echo "Creating basic .env file..."
        cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://aicine_user:aicine_pass@postgres:5432/aicine

# Redis
REDIS_URL=redis://redis:6379

# Gemini API (REQUIRED)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Other AI APIs
# ANTHROPIC_API_KEY=
# HUGGING_FACE_TOKEN=

# Environment
ENVIRONMENT=development
DEBUG=true
EOF
        echo "✓ Basic .env created"
    fi
    echo ""
fi

# Check Gemini API key
if grep -q "GEMINI_API_KEY=your_gemini_api_key_here" .env 2>/dev/null || \
   grep -q "GEMINI_API_KEY=$" .env 2>/dev/null; then
    echo "⚠️  WARNING: Gemini API key not configured!"
    echo ""
    echo "Narrative analysis requires Gemini API."
    echo "Get free key: https://makersuite.google.com/app/apikey"
    echo ""
    read -p "Enter your Gemini API key now (or press Enter to skip): " api_key
    
    if [ ! -z "$api_key" ]; then
        sed -i.bak "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=$api_key/" .env
        rm .env.bak 2>/dev/null || true
        echo "✓ API key saved"
    else
        echo "⚠️  Skipping API key - narrative analysis will be disabled"
    fi
    echo ""
fi

# Build Docker images
echo "🐳 Building Docker images..."
echo "(This may take 5-10 minutes on first run)"
echo ""
docker-compose build

echo ""
echo "✅ Setup Complete!"
echo ""
echo "======================================"
echo "📋 NEXT STEPS:"
echo "======================================"
echo ""
echo "1. Start all services:"
echo "   $ docker-compose up -d"
echo ""
echo "2. Check logs:"
echo "   $ docker-compose logs -f api"
echo ""
echo "3. Test the API:"
echo "   $ curl http://localhost:8000/health"
echo ""
echo "4. View API docs:"
echo "   Open: http://localhost:8000/docs"
echo ""
echo "5. Monitor tasks (Flower):"
echo "   Open: http://localhost:5555"
echo ""
echo "======================================"
echo "🎥 EXAMPLE USAGE:"
echo "======================================"
echo ""
echo "# Submit a video for analysis"
echo 'curl -X POST http://localhost:8000/api/analyze \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'"'"
echo ""
echo "# Check job status"
echo 'curl http://localhost:8000/api/jobs/1'
echo ""
echo "# List all films"
echo 'curl http://localhost:8000/api/films'
echo ""
echo "======================================"
echo ""

# Optional: Start services
read -p "Start services now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting services..."
    docker-compose up -d
    echo ""
    echo "✓ Services started!"
    echo ""
    echo "Waiting for services to be ready..."
    sleep 5
    echo ""
    docker-compose ps
    echo ""
    echo "✅ All services running!"
    echo ""
    echo "API: http://localhost:8000/docs"
    echo "Flower: http://localhost:5555"
fi

echo ""
echo "🎬 Happy analyzing!"
