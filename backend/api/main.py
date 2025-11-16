"""
AI Cine Analyzer - Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Cine Analyzer",
    description="AI-powered film analysis platform",
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
# MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request to analyze a video"""
    url: HttpUrl
    priority: int = 5
    force_reanalyze: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "priority": 5,
                "force_reanalyze": False
            }
        }


class JobResponse(BaseModel):
    """Job status response"""
    job_id: str
    status: str
    url: str
    priority: int
    created_at: str
    message: Optional[str] = None


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
        "description": "Professional film analysis platform",
        "endpoints": {
            "GET /health": "Health check",
            "POST /api/analyze": "Submit video for analysis",
            "GET /api/jobs/{job_id}": "Get job status",
            "GET /docs": "API documentation",
            "GET /": "This page"
        },
        "features": [
            "🎬 Cinematography analysis",
            "📖 Narrative breakdown with AI",
            "🎭 Character tracking",
            "🎵 Audio mood analysis",
            "🔍 Similarity search"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


@app.post("/api/analyze", response_model=JobResponse)
async def submit_analysis(request: AnalysisRequest):
    """
    Submit a video URL for analysis
    
    This endpoint queues a video for background processing using Celery.
    Returns a job_id that can be used to track progress.
    
    - **url**: Video URL (YouTube, Vimeo, etc.)
    - **priority**: Priority level 1-10 (higher = more priority)
    - **force_reanalyze**: Re-analyze even if already processed
    """
    try:
        logger.info(f"📥 Received analysis request for: {request.url}")
        
        # Import Celery task
        from backend.tasks.video_tasks import analyze_video
        
        # Queue the task (placeholder - will be replaced with real analysis)
        task = analyze_video.delay(
            video_id=0,  # Will be replaced with actual DB ID
            video_path=str(request.url)
        )
        
        logger.info(f"✅ Task queued with ID: {task.id}")
        
        return JobResponse(
            job_id=task.id,
            status="queued",
            url=str(request.url),
            priority=request.priority,
            created_at=datetime.now().isoformat(),
            message="Video analysis queued successfully. Use job_id to track progress."
        )
        
    except ImportError as e:
        logger.error(f"❌ Celery import error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Background task system not available. Check worker logs."
        )
    except Exception as e:
        logger.error(f"❌ Error queuing task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue analysis: {str(e)}")

@app.post("/api/analyze/full")
async def submit_full_analysis(request: AnalysisRequest):
    """
    Submit video for FULL analysis (download + frames + audio + AI)
    """
    try:
        logger.info(f"📥 Full analysis request for: {request.url}")
        
        from backend.tasks.video_tasks import analyze_video_full
        
        task = analyze_video_full.delay(str(request.url))
        
        logger.info(f"✅ Full analysis queued: {task.id}")
        
        return {
            "job_id": task.id,
            "status": "queued",
            "url": str(request.url),
            "priority": request.priority,
            "created_at": datetime.now().isoformat(),
            "message": "Full video analysis started. This may take several minutes.",
            "check_status": f"/api/jobs/{task.id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of an analysis job
    
    Returns the current status and results (if completed) of a background task.
    
    **Possible statuses:**
    - PENDING: Task is waiting to be executed
    - PROGRESS: Task is currently running
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed with error
    """
    try:
        from celery.result import AsyncResult
        
        task = AsyncResult(job_id)
        
        response = {
            "job_id": job_id,
            "status": task.state,
        }
        
        if task.state == "PENDING":
            response["message"] = "Task is waiting in queue"
        elif task.state == "PROGRESS":
            response["progress"] = task.info
            response["message"] = "Task is processing"
        elif task.state == "SUCCESS":
            response["result"] = task.result
            response["message"] = "Task completed successfully"
        elif task.state == "FAILURE":
            response["error"] = str(task.info)
            response["message"] = "Task failed"
        else:
            response["info"] = str(task.info) if task.info else None
        
        return response
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Background task system not available"
        )
    except Exception as e:
        logger.error(f"❌ Error fetching job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test")
async def test_celery():
    """
    Test endpoint to verify Celery is working
    
    Runs a simple test task and returns the result.
    """
    try:
        from backend.tasks.video_tasks import test_task
        
        task = test_task.delay("Hello from API!")
        
        return {
            "status": "success",
            "message": "Test task queued",
            "task_id": task.id,
            "instructions": f"Check status at: /api/jobs/{task.id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)