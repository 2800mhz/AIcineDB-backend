"""
Upload endpoint for video analysis
Handles video URL uploads from frontend with optional pre-created title_id
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import logging
import re

from backend.utils.auth import verify_creator_or_admin
from backend.services.supabase_sync import get_supabase_client
from backend.database.connection import get_db
from backend.tasks.video_tasks import analyze_film_complete
from backend.models.schemas import AnalysisJobResponse

router = APIRouter(prefix="/api", tags=["upload"])
logger = logging.getLogger(__name__)

# Type alias for user dict from auth
# Structure: {"id": str, "email": str, "role": str, "is_admin": bool, "is_creator": bool}
UserDict = Dict[str, Any]


class UploadRequest(BaseModel):
    """Upload request schema"""
    url: HttpUrl
    title_id: Optional[str] = None
    priority: Optional[int] = 5

    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title_id": "abc-123-456",
            }
        }


def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title"""
    if not title:
        return "untitled"
    
    # Convert to lowercase
    slug = title.lower()
    
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    
    # Remove any characters that aren't alphanumeric or hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Ensure we have something
    if not slug:
        slug = "untitled"
    
    return slug


@router.post("/upload", response_model=AnalysisJobResponse)
async def upload_video(
    request: UploadRequest,
    current_user: UserDict = Depends(verify_creator_or_admin)
):
    """
    Upload video URL for AI analysis.
    
    Workflow:
    1. Frontend creates title in Supabase with uploaded_by
    2. Frontend sends { url, title_id } to this endpoint
    3. Backend updates status to 'processing'
    4. Backend starts analysis task
    5. Task updates same title row (not create new one)
    
    Args:
        request: Upload request with url and optional title_id
        current_user: Current authenticated user
        
    Returns:
        AnalysisJobResponse with job_id, title_id and task_id
    """
    try:
        user_id = current_user['id']
        user_role = current_user.get('role', 'user')
        
        logger.info(f"📤 Upload request from user {user_id} ({user_role})")
        logger.info(f"📹 Video URL: {str(request.url)}")
        logger.info(f"🎯 Title ID: {request.title_id}")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        if not supabase:
            logger.error("❌ Supabase client initialization failed - check SUPABASE_URL and SUPABASE_SERVICE_KEY")
            raise HTTPException(
                status_code=500, 
                detail="Supabase client not available. Please check server configuration (SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables)."
            )
        
        # CASE 1: Frontend sent title_id (PREFERRED FLOW)
        if request.title_id:
            title_id = request.title_id
            logger.info(f"✅ Using existing title_id from frontend: {title_id}")
            
            # Verify title exists
            title_result = supabase.table("titles") \
                .select("id, uploaded_by, status, title") \
                .eq("id", title_id) \
                .execute()
            
            if not title_result.data or len(title_result.data) == 0:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Title {title_id} not found in database"
                )
            
            existing_title = title_result.data[0]
            logger.info(f"📝 Found existing title: {existing_title.get('title', 'Untitled')}")
            
            # Verify ownership (if not admin)
            if user_role != "admin":
                if existing_title.get("uploaded_by") != user_id:
                    raise HTTPException(
                        status_code=403, 
                        detail="Not authorized to analyze this title"
                    )
            
            # Update status to processing
            update_result = supabase.table("titles").update({
                "status": "processing",
                "trailer_youtube_url": str(request.url)
            }).eq("id", title_id).execute()
            
            # Note: Supabase update can return empty data if values are identical
            # The title existence was verified above, so we just log for debugging
            if update_result.data:
                logger.info(f"✅ Updated title {title_id} status to 'processing' ({len(update_result.data)} rows)")
            else:
                logger.info(f"✅ Title {title_id} status confirmed (no changes needed)")
            
        # CASE 2: No title_id - Create new one (BACKWARD COMPATIBILITY)
        else:
            logger.warning("⚠️ No title_id provided - creating new title (deprecated flow)")
            
            # Create new title
            title_data = {
                "title": "Untitled Video",
                "status": "processing",
                "type": "movie",
                "uploaded_by": user_id,
                "slug": "untitled-video",
                "trailer_youtube_url": str(request.url)
            }
            
            new_title_result = supabase.table("titles").insert(title_data).execute()
            
            if not new_title_result.data or len(new_title_result.data) == 0:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to create title in database"
                )
            
            title_id = new_title_result.data[0]["id"]
            logger.info(f"✅ Created new title: {title_id}")
        
        # Create analysis job in local database
        async with get_db() as db:
            job = await db.fetch_one(
                query="""
                INSERT INTO analysis_jobs (url, status, priority)
                VALUES (:url, 'pending', :priority)
                RETURNING *
                """,
                values={
                    "url": str(request.url),
                    "priority": request.priority or 5
                }
            )
            
            if not job:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to create analysis job"
                )
            
            job_id = job['id']
            logger.info(f"✅ Analysis job created with ID: {job_id}")
            
            # Start Celery task for analysis
            task = analyze_film_complete.delay(
                job_id,
                str(request.url),
                title_id=title_id  # ✅ Pass title_id to task
            )
            
            logger.info(f"🎬 Analysis task started: {task.id}")
            logger.info(f"📹 Video URL: {str(request.url)}")
            logger.info(f"🎯 Title ID: {title_id}")
            
            return AnalysisJobResponse(
                job_id=job_id,
                status=job['status'],
                url=str(request.url),
                created_at=job['created_at'],
                celery_task_id=task.id,
                progress=0.0  # Initial progress
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/upload/status/{task_id}")
async def get_upload_status(task_id: str):
    """
    Get status of upload/analysis task
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status and progress
    """
    from celery.result import AsyncResult
    
    try:
        task = AsyncResult(task_id)
        
        result = {
            "task_id": task_id,
            "status": task.state,
            "progress": 0,
            "message": "",
        }
        
        if task.info:
            if isinstance(task.info, dict):
                result["progress"] = task.info.get("progress", 0)
                result["message"] = task.info.get("message", "")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get task status: {str(e)}"
        )
