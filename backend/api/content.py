"""
Content Aggregation API
REST endpoints for managing news, discovered festivals, sources, and scraping jobs
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime
import logging

from backend.models.schemas import (
    DiscoveredFestivalResponse,
    DiscoveredFestivalApproval,
    NewsArticleResponse,
    NewsSourceResponse,
    NewsSourceCreate,
    FestivalSourceResponse,
    FestivalSourceCreate,
    ScrapingJobResponse,
    ManualTriggerResponse
)
from backend.utils.auth import verify_admin
from backend.services.supabase_sync import SupabaseSyncService

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


# ============================================================================
# NEWS ENDPOINTS
# ============================================================================

@router.get("/news", response_model=List[NewsArticleResponse])
async def list_news_articles(
    is_archived: bool = Query(False, description="Show archived articles"),
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List all news articles (paginated, filtered)
    
    Returns up to 50 articles per page, sorted by publication date
    """
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build query parameters
            params = {
                "select": "*",
                "is_archived": f"eq.{is_archived}",
                "order": "published_at.desc",
                "limit": limit,
                "offset": skip
            }
            
            # Add category filter if provided
            if category:
                params["category"] = f"cs.{{{category}}}"  # Contains
            
            response = await client.get(
                f"{supabase_service.rest_url}/news_articles",
                headers=supabase_service.headers,
                params=params
            )
            response.raise_for_status()
            articles = response.json()
            
            return [NewsArticleResponse(**article) for article in articles]
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching news: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/{id}", response_model=NewsArticleResponse)
async def get_news_article(id: str):
    """Get a single news article by ID"""
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{supabase_service.rest_url}/news_articles",
                headers=supabase_service.headers,
                params={"id": f"eq.{id}", "select": "*"}
            )
            response.raise_for_status()
            articles = response.json()
            
            if not articles:
                raise HTTPException(status_code=404, detail="Article not found")
            
            return NewsArticleResponse(**articles[0])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching article: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/news/refresh", response_model=ManualTriggerResponse)
async def trigger_news_aggregation(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Manually trigger news aggregation (admin only)
    
    Requires admin authentication
    """
    # Verify admin
    await verify_admin(credentials)
    
    try:
        from backend.tasks.content_tasks import aggregate_news_task
        
        # Trigger the task
        task = aggregate_news_task.delay()
        
        logger.info(f"✅ News aggregation triggered: {task.id}")
        
        return ManualTriggerResponse(
            task_id=task.id,
            message="News aggregation task started"
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger news aggregation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DISCOVERED FESTIVALS ENDPOINTS
# ============================================================================

@router.get("/festivals/discovered", response_model=List[DiscoveredFestivalResponse])
async def list_discovered_festivals(
    status: str = Query("pending", description="Filter by status (pending, approved, rejected)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    List pending discovered festivals (admin only)
    
    Requires admin authentication
    """
    # Verify admin
    await verify_admin(credentials)
    
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{supabase_service.rest_url}/discovered_festivals",
                headers=supabase_service.headers,
                params={
                    "select": "*",
                    "status": f"eq.{status}",
                    "order": "ai_relevance_score.desc,created_at.desc",
                    "limit": limit,
                    "offset": skip
                }
            )
            response.raise_for_status()
            festivals = response.json()
            
            return [DiscoveredFestivalResponse(**fest) for fest in festivals]
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching festivals: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching festivals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/discovered/{id}", response_model=DiscoveredFestivalResponse)
async def get_discovered_festival(
    id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get details of a discovered festival (admin only)
    
    Requires admin authentication
    """
    # Verify admin
    await verify_admin(credentials)
    
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{supabase_service.rest_url}/discovered_festivals",
                headers=supabase_service.headers,
                params={"id": f"eq.{id}", "select": "*"}
            )
            response.raise_for_status()
            festivals = response.json()
            
            if not festivals:
                raise HTTPException(status_code=404, detail="Festival not found")
            
            return DiscoveredFestivalResponse(**festivals[0])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching festival: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/festivals/discovered/{id}/approve")
async def approve_discovered_festival(
    id: str,
    approval: DiscoveredFestivalApproval,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Approve or reject a discovered festival (admin only)
    
    If approved, moves the festival to the main festivals table
    """
    # Verify admin
    user = await verify_admin(credentials)
    
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        if approval.action == "approve":
            # Move to main festivals table
            festival_id = await supabase_service.approve_festival(id)
            
            if not festival_id:
                raise HTTPException(status_code=500, detail="Failed to approve festival")
            
            return {
                "success": True,
                "message": "Festival approved",
                "festival_id": festival_id
            }
            
        elif approval.action == "reject":
            if not approval.rejection_reason:
                raise HTTPException(
                    status_code=400,
                    detail="rejection_reason is required when rejecting"
                )
            
            # Update status to rejected
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    f"{supabase_service.rest_url}/discovered_festivals",
                    headers=supabase_service.headers,
                    params={"id": f"eq.{id}"},
                    json={
                        "status": "rejected",
                        "rejection_reason": approval.rejection_reason,
                        "reviewed_at": datetime.now().isoformat(),
                        "reviewed_by": user.id if hasattr(user, 'id') else None
                    }
                )
                response.raise_for_status()
            
            return {
                "success": True,
                "message": "Festival rejected"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid action. Must be 'approve' or 'reject'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing festival approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/festivals/refresh", response_model=ManualTriggerResponse)
async def trigger_festival_scraping(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Manually trigger festival scraping (admin only)
    
    Requires admin authentication
    """
    # Verify admin
    await verify_admin(credentials)
    
    try:
        from backend.tasks.content_tasks import scrape_festivals_task
        
        # Trigger the task
        task = scrape_festivals_task.delay()
        
        logger.info(f"✅ Festival scraping triggered: {task.id}")
        
        return ManualTriggerResponse(
            task_id=task.id,
            message="Festival scraping task started"
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger festival scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEWS SOURCES ENDPOINTS
# ============================================================================

@router.get("/sources/news", response_model=List[NewsSourceResponse])
async def list_news_sources(
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all news sources"""
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"select": "*", "order": "name.asc"}
            
            if is_active is not None:
                params["is_active"] = f"eq.{is_active}"
            
            response = await client.get(
                f"{supabase_service.rest_url}/news_sources",
                headers=supabase_service.headers,
                params=params
            )
            response.raise_for_status()
            sources = response.json()
            
            return [NewsSourceResponse(**source) for source in sources]
            
    except Exception as e:
        logger.error(f"Error fetching news sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/news", response_model=NewsSourceResponse, status_code=201)
async def create_news_source(
    source: NewsSourceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Add a new news source (admin only)
    
    Requires admin authentication
    """
    # Verify admin
    await verify_admin(credentials)
    
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{supabase_service.rest_url}/news_sources",
                headers=supabase_service.headers,
                json=source.dict()
            )
            response.raise_for_status()
            result = response.json()
            
            if result and len(result) > 0:
                return NewsSourceResponse(**result[0])
            
            raise HTTPException(status_code=500, detail="Failed to create source")
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(status_code=409, detail="Source URL already exists")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating news source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sources/news/{id}", response_model=NewsSourceResponse)
async def update_news_source(
    id: str,
    source: NewsSourceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Update news source configuration (admin only)
    
    Requires admin authentication
    """
    # Verify admin
    await verify_admin(credentials)
    
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{supabase_service.rest_url}/news_sources",
                headers=supabase_service.headers,
                params={"id": f"eq.{id}"},
                json={**source.dict(), "updated_at": datetime.now().isoformat()}
            )
            response.raise_for_status()
            result = response.json()
            
            if not result:
                raise HTTPException(status_code=404, detail="Source not found")
            
            return NewsSourceResponse(**result[0])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating news source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FESTIVAL SOURCES ENDPOINTS
# ============================================================================

@router.get("/sources/festivals", response_model=List[FestivalSourceResponse])
async def list_festival_sources(
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all festival sources"""
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"select": "*", "order": "name.asc"}
            
            if is_active is not None:
                params["is_active"] = f"eq.{is_active}"
            
            response = await client.get(
                f"{supabase_service.rest_url}/festival_sources",
                headers=supabase_service.headers,
                params=params
            )
            response.raise_for_status()
            sources = response.json()
            
            return [FestivalSourceResponse(**source) for source in sources]
            
    except Exception as e:
        logger.error(f"Error fetching festival sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/festivals", response_model=FestivalSourceResponse, status_code=201)
async def create_festival_source(
    source: FestivalSourceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Add a new festival source (admin only)
    
    Requires admin authentication
    """
    # Verify admin
    await verify_admin(credentials)
    
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{supabase_service.rest_url}/festival_sources",
                headers=supabase_service.headers,
                json=source.dict()
            )
            response.raise_for_status()
            result = response.json()
            
            if result and len(result) > 0:
                return FestivalSourceResponse(**result[0])
            
            raise HTTPException(status_code=500, detail="Failed to create source")
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(status_code=409, detail="Source URL already exists")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating festival source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SCRAPING JOBS ENDPOINTS
# ============================================================================

@router.get("/scraping-jobs", response_model=List[ScrapingJobResponse])
async def list_scraping_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job type (festivals, news)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List recent scraping jobs"""
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "select": "*",
                "order": "created_at.desc",
                "limit": limit,
                "offset": skip
            }
            
            if job_type:
                params["job_type"] = f"eq.{job_type}"
            
            if status:
                params["status"] = f"eq.{status}"
            
            response = await client.get(
                f"{supabase_service.rest_url}/scraping_jobs",
                headers=supabase_service.headers,
                params=params
            )
            response.raise_for_status()
            jobs = response.json()
            
            return [ScrapingJobResponse(**job) for job in jobs]
            
    except Exception as e:
        logger.error(f"Error fetching scraping jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scraping-jobs/{id}", response_model=ScrapingJobResponse)
async def get_scraping_job(id: str):
    """Get details of a specific scraping job"""
    try:
        supabase_service = SupabaseSyncService()
        
        if not supabase_service.enabled:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{supabase_service.rest_url}/scraping_jobs",
                headers=supabase_service.headers,
                params={"id": f"eq.{id}", "select": "*"}
            )
            response.raise_for_status()
            jobs = response.json()
            
            if not jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            
            return ScrapingJobResponse(**jobs[0])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
