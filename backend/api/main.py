"""
AI Cine Analyzer - Complete FastAPI Application
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List
import logging

from backend.database.connection import database, init_db
from backend.database.database_operations import DatabaseOperations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Cine Analyzer",
    description="Complete AI-powered film analysis platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    logger.info("🚀 AI Cine Analyzer starting...")
    try:
        await init_db()
        logger.info("✓ Database connected")
        logger.info("✓ AI Cine Analyzer ready!")
    except Exception as e:
        logger.error(f"Startup failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down...")
    await database.disconnect()


# ============================================================================
# MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request to analyze a video"""
    url: HttpUrl
    priority: int = 5
    force_reanalyze: bool = False


class JobResponse(BaseModel):
    """Job status response"""
    job_id: int
    status: str
    url: str
    priority: int
    progress: float = 0.0
    current_stage: Optional[str] = None
    film_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime


class FilmSummary(BaseModel):
    """Film summary"""
    id: int
    title: str
    duration: float
    url: str
    analyzed_at: Optional[datetime]
    style_fingerprint: Optional[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API root"""
    return {
        "name": "AI Cine Analyzer API",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "🎬 Shot detection & cinematography",
            "🎨 Visual style classification (CLIP)",
            "🎤 Audio transcription (Whisper)",
            "📖 Narrative analysis (Gemini AI)",
            "🎭 Character tracking & face recognition",
            "🔍 Vector similarity search",
            "💾 Complete database storage"
        ],
        "endpoints": {
            "POST /api/analyze": "Submit video for analysis",
            "GET /api/jobs/{job_id}": "Check job status",
            "GET /api/films": "List all films",
            "GET /api/films/{film_id}": "Get film details",
            "GET /api/films/{film_id}/similar": "Find similar films",
            "GET /health": "Health check",
            "GET /docs": "API documentation"
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


@app.post("/api/analyze", response_model=JobResponse)
async def submit_analysis(request: AnalysisRequest):
    """
    Submit a video URL for complete analysis
    
    This will:
    - Download the video
    - Extract frames and audio
    - Detect shots and classify style
    - Transcribe audio
    - Analyze narrative with Gemini AI
    - Track characters
    - Save everything to database
    """
    try:
        logger.info(f"📥 Analysis request: {request.url}")
        
        db_ops = DatabaseOperations(database)
        
        # Check if already analyzed
        if not request.force_reanalyze:
            existing = await database.fetch_one(
                "SELECT id FROM films WHERE url = :url",
                values={"url": str(request.url)}
            )
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"URL already analyzed. Film ID: {existing['id']}"
                )
        
        # Create job
        job_id = await db_ops.create_job(str(request.url), request.priority)
        
        # Queue Celery task
        from backend.tasks.video_tasks import analyze_film_complete
        
        task = analyze_film_complete.delay(job_id, str(request.url))
        
        # Update job with Celery task ID
        await db_ops.update_job_status(
            job_id,
            status='queued',
            celery_task_id=task.id
        )
        
        logger.info(f"✅ Job {job_id} queued (task: {task.id})")
        
        return JobResponse(
            job_id=job_id,
            status="queued",
            url=str(request.url),
            priority=request.priority,
            progress=0.0,
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: int):
    """
    Get analysis job status
    
    Returns current progress and status of the analysis job.
    """
    try:
        job = await database.fetch_one(
            "SELECT * FROM analysis_jobs WHERE id = :job_id",
            values={"job_id": job_id}
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobResponse(
            job_id=job['id'],
            status=job['status'],
            url=job['url'],
            priority=job['priority'],
            progress=job['progress'],
            current_stage=job['current_stage'],
            film_id=job['film_id'],
            error_message=job['error_message'],
            created_at=job['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/films", response_model=List[FilmSummary])
async def list_films(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List all analyzed films
    """
    try:
        query = """
            SELECT id, title, duration, url, analyzed_at,
                   metadata->>'style_fingerprint' as style_fingerprint
            FROM films
            WHERE analyzed_at IS NOT NULL
            ORDER BY analyzed_at DESC
            LIMIT :limit OFFSET :skip
        """
        
        films = await database.fetch_all(query, values={"limit": limit, "skip": skip})
        
        return [FilmSummary(**dict(film)) for film in films]
        
    except Exception as e:
        logger.error(f"Error listing films: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/films/{film_id}")
async def get_film(film_id: int):
    """
    Get complete film analysis
    
    Returns all analysis data including:
    - Video metadata
    - Shots and cinematography
    - Visual style and colors
    - Narrative analysis
    - Transcript
    - Characters
    - Scenes
    """
    try:
        # Get film
        film = await database.fetch_one(
            "SELECT * FROM films WHERE id = :film_id",
            values={"film_id": film_id}
        )
        
        if not film:
            raise HTTPException(status_code=404, detail="Film not found")
        
        # Get related data
        narrative = await database.fetch_one(
            "SELECT * FROM narratives WHERE film_id = :film_id",
            values={"film_id": film_id}
        )
        
        transcript = await database.fetch_one(
            "SELECT * FROM transcripts WHERE film_id = :film_id",
            values={"film_id": film_id}
        )
        
        audio = await database.fetch_one(
            "SELECT * FROM audio_features WHERE film_id = :film_id",
            values={"film_id": film_id}
        )
        
        shots = await database.fetch_all(
            "SELECT * FROM shots WHERE film_id = :film_id ORDER BY shot_number",
            values={"film_id": film_id}
        )
        
        characters = await database.fetch_all(
            "SELECT * FROM characters WHERE film_id = :film_id ORDER BY screen_time DESC",
            values={"film_id": film_id}
        )
        
        scenes = await database.fetch_all(
            "SELECT * FROM scenes WHERE film_id = :film_id ORDER BY scene_number",
            values={"film_id": film_id}
        )
        
        return {
            **dict(film),
            'narrative': dict(narrative) if narrative else None,
            'transcript': dict(transcript) if transcript else None,
            'audio_features': dict(audio) if audio else None,
            'shots': [dict(s) for s in shots],
            'characters': [dict(c) for c in characters],
            'scenes': [dict(s) for s in scenes],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching film: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/films/{film_id}/similar")
async def find_similar(
    film_id: int,
    similarity_type: str = Query("combined", regex="^(visual|narrative|audio|combined)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Find similar films using vector similarity
    
    Types:
    - visual: Based on visual style (CLIP embeddings)
    - narrative: Based on story/themes (text embeddings)
    - audio: Based on audio features
    - combined: All of the above
    """
    try:
        db_ops = DatabaseOperations(database)
        
        similar = await db_ops.find_similar_films(
            film_id,
            similarity_type,
            limit
        )
        
        return similar
        
    except Exception as e:
        logger.error(f"Error finding similar films: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get platform statistics"""
    try:
        stats = await database.fetch_one("""
            SELECT 
                COUNT(*) as total_films,
                SUM(duration) as total_duration,
                COUNT(*) FILTER (WHERE analyzed_at > NOW() - INTERVAL '7 days') as recent_films,
                (SELECT COUNT(*) FROM analysis_jobs WHERE status = 'pending') as pending_jobs,
                (SELECT COUNT(*) FROM analysis_jobs WHERE status = 'processing') as processing_jobs
            FROM films
        """)
        
        return {
            "total_films": stats['total_films'],
            "total_duration_hours": round(stats['total_duration'] / 3600, 2) if stats['total_duration'] else 0,
            "recent_films": stats['recent_films'],
            "pending_jobs": stats['pending_jobs'],
            "processing_jobs": stats['processing_jobs']
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)