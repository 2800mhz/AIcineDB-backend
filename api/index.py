"""
Vercel entrypoint for FastAPI application
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.main import app

# Vercel expects 'app' in standard locations
# This file re-exports the app from the actual location
