#!/bin/bash

# AI Cine Analyzer - Setup Script
# This script helps you set up the project quickly

set -e

echo "🎬 AI Cine Analyzer - Setup Script"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p backend/{api,analyzers/{cinematography,narrative,audio,characters},core,models,database,tasks}
mkdir -p docker/postgres
mkdir -p tests
mkdir -p data/{videos,frames,audio}
mkdir -p analyses
mkdir -p logs

# Create __init__.py files
echo "📝 Creating __init__.py files..."
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

echo "✓ Directory structure created"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    
    if [ -f .env.example ]; then
        echo "📄 Copying .env.example to .env..."
        cp .env.example .env
        echo "✓ .env file created"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your GEMINI_API_KEY"
        echo "   Get a free key at: https://makersuite.google.com/app/apikey"
        echo ""
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
else
    echo "✓ .env file exists"
fi

# Check if GEMINI_API_KEY is set
if grep -q "GEMINI_API_KEY=your_gemini_api_key_here" .env 2>/dev/null; then
    echo ""
    echo "⚠️  WARNING: GEMINI_API_KEY is not configured in .env"
    echo "   The analyzer will not work without a valid API key."
    echo "   Get a free key at: https://makersuite.google.com/app/apikey"
    echo ""
    read -p "Do you want to enter your Gemini API key now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Gemini API key: " api_key
        sed -i "s/GEMINI_API_KEY=your_gemini_api_key_here/GEMINI_API_KEY=$api_key/" .env
        echo "✓ API key saved to .env"
    fi
fi

echo ""
echo "🐳 Building Docker images..."
docker-compose build

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the services, run:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo "API Documentation will be available at:"
echo "  http://localhost:8000/docs"
echo ""
echo "Flower (Task Monitor) will be available at:"
echo "  http://localhost:5555"
echo ""
