"""
AI Cine Analyzer - Main FastAPI Application
Modern film analysis platform with Gemini AI
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from backend.database.connection import get_db, init_db
from backend.tasks.celery_app import analyze_film_task
from backend.models.schemas import (
    AnalysisRequest,
    AnalysisJobResponse,
    FilmSummary,
    FilmDetail,
    SimilarFilm,
    SearchFilters,
    HealthCheck
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="AI Cine Analyzer",
    description="Professional AI-powered film analysis platform with visual, narrative, and audio analysis",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("🚀 AI Cine Analyzer starting up...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("✓ Database initialized")
        
        # Test Gemini API
        from backend.analyzers.narrative.gemini_analyzer import test_gemini_connection
        if await test_gemini_connection():
            logger.info("✓ Gemini API connected")
        else:
            logger.warning("⚠ Gemini API not configured")
        
        logger.info("✓ AI Cine Analyzer ready!")
        
    except Exception as e:
        logger.error(f"✗ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 AI Cine Analyzer shutting down...")


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


@app.get("/", response_model=Dict[str, Any])
async def root():
    """API root with documentation"""
    return {
        "name": "AI Cine Analyzer API",
        "version": "2.0.0",
        "description": "Professional film analysis platform",
        "features": [
            "🎬 Cinematography analysis (shots, lighting, color)",
            "📖 Narrative breakdown with Gemini AI",
            "🎭 Character tracking & emotion detection",
            "🎵 Audio mood & pacing analysis",
            "🎨 Visual style classification",
            "🔍 Vector-based similarity search",
            "📊 Complete reports (JSON, HTML, TXT)"
        ],
        "endpoints": {
            "POST /api/analyze": "Submit video for analysis",
            "GET /api/jobs/{job_id}": "Get analysis job status",
            "GET /api/films": "List all analyzed films",
            "GET /api/films/{film_id}": "Get detailed film analysis",
            "GET /api/films/{film_id}/similar": "Find similar films",
            "POST /api/search": "Search films by criteria"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@app.post("/api/analyze", response_model=AnalysisJobResponse, status_code=202)
async def submit_analysis(request: AnalysisRequest):
    """
    Submit a video URL for analysis
    
    Returns job ID for tracking progress
    """
    try:
        async with get_db() as db:
            # Check if URL already analyzed
            existing = await db.fetch_one(
                "SELECT id, analyzed_at FROM films WHERE url = $1",
                str(request.url)
            )
            
            if existing and not request.force_reanalyze:
                raise HTTPException(
                    status_code=409,
                    detail=f"URL already analyzed (film_id: {existing['id']}). Use force_reanalyze=true to re-analyze."
                )
            
            # Create analysis job
            job = await db.fetch_one(
                """
                INSERT INTO analysis_jobs (url, status, priority)
                VALUES ($1, 'pending', $2)
                RETURNING *
                """,
                str(request.url),
                request.priority
            )
            
            # Queue background task
            task = analyze_film_task.delay(job['id'], str(request.url))
            
            logger.info(f"📥 Created analysis job {job['id']} for {request.url}")
            
            return AnalysisJobResponse(
                job_id=job['id'],
                status=job['status'],
                url=str(request.url),
                created_at=job['created_at'],
                celery_task_id=task.id
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create analysis job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_job_status(job_id: int):
    """Get status of an analysis job"""
    try:
        async with get_db() as db:
            job = await db.fetch_one(
                "SELECT * FROM analysis_jobs WHERE id = $1",
                job_id
            )
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            return AnalysisJobResponse(**dict(job))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs", response_model=List[AnalysisJobResponse])
async def list_jobs(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """List analysis jobs with optional status filter"""
    try:
        async with get_db() as db:
            if status:
                query = """
                    SELECT * FROM analysis_jobs 
                    WHERE status = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """
                jobs = await db.fetch_all(query, status, limit, skip)
            else:
                query = """
                    SELECT * FROM analysis_jobs
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """
                jobs = await db.fetch_all(query, limit, skip)
            
            return [AnalysisJobResponse(**dict(job)) for job in jobs]
            
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FILM ENDPOINTS
# ============================================================================

@app.get("/api/films", response_model=List[FilmSummary])
async def list_films(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("analyzed_at", regex="^(title|duration|analyzed_at)$")
):
    """List all analyzed films"""
    try:
        async with get_db() as db:
            query = f"""
                SELECT 
                    id,
                    title,
                    duration,
                    url,
                    analyzed_at,
                    metadata->>'style_fingerprint' as style_fingerprint,
                    COALESCE(
                        (SELECT json_agg(theme->>'name')
                         FROM jsonb_array_elements(metadata->'narrative'->'themes') as theme
                         LIMIT 3),
                        '[]'::json
                    ) as themes
                FROM films
                WHERE analyzed_at IS NOT NULL
                ORDER BY {sort_by} DESC
                LIMIT $1 OFFSET $2
            """
            
            films = await db.fetch_all(query, limit, skip)
            
            return [FilmSummary(**dict(film)) for film in films]
            
    except Exception as e:
        logger.error(f"Error listing films: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/films/{film_id}", response_model=FilmDetail)
async def get_film(film_id: int):
    """Get complete analysis for a film"""
    try:
        async with get_db() as db:
            # Get film
            film = await db.fetch_one(
                "SELECT * FROM films WHERE id = $1",
                film_id
            )
            
            if not film:
                raise HTTPException(status_code=404, detail="Film not found")
            
            # Get related data
            narrative = await db.fetch_one(
                "SELECT * FROM narratives WHERE film_id = $1",
                film_id
            )
            
            transcript = await db.fetch_one(
                "SELECT * FROM transcripts WHERE film_id = $1",
                film_id
            )
            
            audio = await db.fetch_one(
                "SELECT * FROM audio_features WHERE film_id = $1",
                film_id
            )
            
            shots = await db.fetch_all(
                "SELECT * FROM shots WHERE film_id = $1 ORDER BY shot_number",
                film_id
            )
            
            characters = await db.fetch_all(
                "SELECT * FROM characters WHERE film_id = $1 ORDER BY screen_time DESC",
                film_id
            )
            
            scenes = await db.fetch_all(
                "SELECT * FROM scenes WHERE film_id = $1 ORDER BY scene_number",
                film_id
            )
            
            return FilmDetail(
                **dict(film),
                narrative=dict(narrative) if narrative else None,
                transcript=dict(transcript) if transcript else None,
                audio_features=dict(audio) if audio else None,
                shots=[dict(s) for s in shots],
                characters=[dict(c) for c in characters],
                scenes=[dict(s) for s in scenes]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching film: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/films/{film_id}/similar", response_model=List[SimilarFilm])
async def find_similar_films(
    film_id: int,
    similarity_type: str = Query("combined", regex="^(visual|narrative|audio|combined)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """Find films similar to the given film"""
    try:
        async with get_db() as db:
            # Check if film exists
            film = await db.fetch_one(
                "SELECT id FROM films WHERE id = $1",
                film_id
            )
            
            if not film:
                raise HTTPException(status_code=404, detail="Film not found")
            
            # Find similar films based on type
            if similarity_type == "visual":
                query = """
                    SELECT 
                        f.id as film_id,
                        f.title,
                        1 - (f.visual_embedding <=> ref.visual_embedding) as similarity,
                        f.metadata->>'style_fingerprint' as style_fingerprint
                    FROM films f
                    CROSS JOIN (SELECT visual_embedding FROM films WHERE id = $1) ref
                    WHERE f.id != $1 AND f.visual_embedding IS NOT NULL
                    ORDER BY f.visual_embedding <=> ref.visual_embedding
                    LIMIT $2
                """
            elif similarity_type == "narrative":
                query = """
                    SELECT 
                        f.id as film_id,
                        f.title,
                        1 - (f.text_embedding <=> ref.text_embedding) as similarity,
                        f.metadata->>'style_fingerprint' as style_fingerprint
                    FROM films f
                    CROSS JOIN (SELECT text_embedding FROM films WHERE id = $1) ref
                    WHERE f.id != $1 AND f.text_embedding IS NOT NULL
                    ORDER BY f.text_embedding <=> ref.text_embedding
                    LIMIT $2
                """
            else:  # combined
                query = """
                    SELECT 
                        f.id as film_id,
                        f.title,
                        (
                            (1 - (f.visual_embedding <=> ref.visual_embedding)) +
                            (1 - (f.text_embedding <=> ref.text_embedding)) +
                            COALESCE(1 - (f.audio_embedding <=> ref.audio_embedding), 0.5)
                        ) / 3.0 as similarity,
                        f.metadata->>'style_fingerprint' as style_fingerprint
                    FROM films f
                    CROSS JOIN (SELECT * FROM films WHERE id = $1) ref
                    WHERE f.id != $1
                        AND f.visual_embedding IS NOT NULL
                        AND f.text_embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT $2
                """
            
            similar = await db.fetch_all(query, film_id, limit)
            
            return [SimilarFilm(**dict(s)) for s in similar]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar films: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", response_model=List[FilmSummary])
async def search_films(
    filters: SearchFilters,
    limit: int = Query(20, ge=1, le=100)
):
    """Search films by various criteria"""
    try:
        async with get_db() as db:
            conditions = ["analyzed_at IS NOT NULL"]
            params = []
            param_idx = 1
            
            if filters.theme:
                conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(metadata->'narrative'->'themes') as theme
                        WHERE theme->>'name' ILIKE ${param_idx}
                    )
                """)
                params.append(f"%{filters.theme}%")
                param_idx += 1
            
            if filters.min_duration:
                conditions.append(f"duration >= ${param_idx}")
                params.append(filters.min_duration)
                param_idx += 1
            
            if filters.max_duration:
                conditions.append(f"duration <= ${param_idx}")
                params.append(filters.max_duration)
                param_idx += 1
            
            if filters.mood:
                conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM audio_features
                        WHERE film_id = films.id AND mood = ${param_idx}
                    )
                """)
                params.append(filters.mood)
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            params.append(limit)
            
            query = f"""
                SELECT 
                    id, title, duration, url, analyzed_at,
                    metadata->>'style_fingerprint' as style_fingerprint,
                    COALESCE(
                        (SELECT json_agg(theme->>'name')
                         FROM jsonb_array_elements(metadata->'narrative'->'themes') as theme
                         LIMIT 3),
                        '[]'::json
                    ) as themes
                FROM films
                WHERE {where_clause}
                ORDER BY analyzed_at DESC
                LIMIT ${param_idx}
            """
            
            films = await db.fetch_all(query, *params)
            
            return [FilmSummary(**dict(f)) for f in films]
            
    except Exception as e:
        logger.error(f"Error searching films: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATS ENDPOINT
# ============================================================================

@app.get("/api/stats")
async def get_stats():
    """Get platform statistics"""
    try:
        async with get_db() as db:
            stats = await db.fetch_one("""
                SELECT 
                    COUNT(*) as total_films,
                    SUM(duration) as total_duration,
                    COUNT(*) FILTER (WHERE analyzed_at > NOW() - INTERVAL '7 days') as films_last_week,
                    (SELECT COUNT(*) FROM analysis_jobs WHERE status = 'pending') as pending_jobs,
                    (SELECT COUNT(*) FROM analysis_jobs WHERE status = 'processing') as processing_jobs
                FROM films
            """)
            
            return {
                "total_films": stats['total_films'],
                "total_duration_hours": round(stats['total_duration'] / 3600, 2) if stats['total_duration'] else 0,
                "films_last_week": stats['films_last_week'],
                "pending_jobs": stats['pending_jobs'],
                "processing_jobs": stats['processing_jobs']
            }
            
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
