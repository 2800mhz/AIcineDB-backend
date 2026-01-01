"""
Content Aggregation API - PRODUCTION VERSION
REST endpoints for managing news, festivals, sources, and scraping jobs
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import logging
import httpx

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
# PYDANTIC UPDATE MODELS
# ============================================================================

class NewsSourceUpdate(BaseModel):
    """Partial update model for news sources"""
    name: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[List[str]] = None
    is_active: Optional[bool] = None
    fetch_interval: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class FestivalSourceUpdate(BaseModel):
    """Partial update model for festival sources"""
    name: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    is_active: Optional[bool] = None
    fetch_interval: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_supabase_service() -> SupabaseSyncService:
    """Get Supabase service instance with validation"""
    service = SupabaseSyncService()
    
    if not service.enabled:
        raise HTTPException(
            status_code=503,
            detail="Content aggregation service is currently unavailable. Please try again later."
        )
    return service


async def make_supabase_request(
    supabase_service: SupabaseSyncService,
    table: str,
    params: dict,
    method: str = "GET",
    json_data: dict = None
) -> Any:
    """Make a request to Supabase REST API with centralized error handling"""
    url = f"{supabase_service.rest_url}/{table}"
    
    # Prefer header for returning data on mutations
    headers = {**supabase_service.headers}
    if method in ["POST", "PATCH", "PUT"]:
        headers["Prefer"] = "return=representation"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, params=params, json=json_data)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, params=params, json=json_data)
            elif method == "PUT":
                response = await client.patch(url, headers=headers, params=params, json=json_data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Log specific errors for debugging
            if response.status_code >= 400:
                logger.error(f"Supabase Error [{method} {table}]: {response.status_code} - {response.text}")

            # Handle specific errors
            if response.status_code == 404:
                return [] if method == "GET" and "limit" in params else None
            
            # For DELETE, return success without parsing JSON
            if method == "DELETE" and response.status_code in [200, 204]:
                return {"success": True}
            
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204 or not response.text:
                return []
            
            return response.json()
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Database error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to content service. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SCRAPING JOBS ENDPOINTS
# ============================================================================

@router.get("/scraping-jobs", response_model=Dict[str, Any])
async def list_scraping_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job type (festivals, news)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List recent scraping jobs"""
    supabase_service = await get_supabase_service()
    
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
    
    jobs = await make_supabase_request(supabase_service, "scraping_jobs", params)
    
    return {
        "items": [ScrapingJobResponse(**job) for job in jobs] if jobs else [],
        "total": len(jobs) if jobs else 0
    }


@router.get("/scraping-jobs/{job_id}", response_model=ScrapingJobResponse)
async def get_scraping_job(job_id: str):
    """Get details of a specific scraping job"""
    supabase_service = await get_supabase_service()
    
    jobs = await make_supabase_request(
        supabase_service,
        "scraping_jobs",
        {"id": f"eq.{job_id}", "select": "*"}
    )
    
    if not jobs:
        raise HTTPException(status_code=404, detail="Scraping job not found")
    
    return ScrapingJobResponse(**jobs[0])


# ============================================================================
# DISCOVERED FESTIVALS ENDPOINTS
# ============================================================================

@router.get("/festivals/discovered", response_model=Dict[str, Any])
async def list_discovered_festivals(
    status: str = Query("pending", description="Filter by status (pending, approved, rejected)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List discovered festivals (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    festivals = await make_supabase_request(
        supabase_service,
        "discovered_festivals",
        {
            "select": "*",
            "status": f"eq.{status}",
            "order": "ai_relevance_score.desc.nullslast,created_at.desc",
            "limit": limit,
            "offset": skip
        }
    )
    
    return {
        "items": [DiscoveredFestivalResponse(**fest) for fest in festivals] if festivals else [],
        "total": len(festivals) if festivals else 0
    }


@router.get("/festivals/discovered/{festival_id}", response_model=DiscoveredFestivalResponse)
async def get_discovered_festival(
    festival_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get details of a discovered festival (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    festivals = await make_supabase_request(
        supabase_service,
        "discovered_festivals",
        {"id": f"eq.{festival_id}", "select": "*"}
    )
    
    if not festivals:
        raise HTTPException(status_code=404, detail="Festival not found")
    
    return DiscoveredFestivalResponse(**festivals[0])


@router.post("/festivals/discovered/{festival_id}/approve")
async def approve_discovered_festival(
    festival_id: str,
    approval: DiscoveredFestivalApproval,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Approve or reject a discovered festival (admin only)
    """
    user = await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    logger.info(f"📋 Processing approval for festival: {festival_id}, action: {approval.action}")
    
    if approval.action == "approve":
        # ✅ DÜZELTME: approve_festival fonksiyonunu çağır
        try:
            logger.info(f"🎬 Calling approve_festival for: {festival_id}")
            new_festival_id = await supabase_service.approve_festival(festival_id)
            
            if not new_festival_id:
                logger.error(f"❌ approve_festival returned None for: {festival_id}")
                raise HTTPException(status_code=500, detail="Failed to migrate festival data")
            
            logger.info(f"✅ Festival approved successfully: {festival_id} → {new_festival_id}")
            
            return {
                "success": True,
                "message": "Festival approved and moved to main catalog",
                "festival_id": new_festival_id
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Approval failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")

    elif approval.action == "reject":
        if not approval.rejection_reason:
            raise HTTPException(
                status_code=400,
                detail="rejection_reason is required when rejecting"
            )
        
        user_id = getattr(user, 'id', None) or getattr(getattr(user, 'user', None), 'id', None)
        
        await make_supabase_request(
            supabase_service,
            "discovered_festivals",
            {"id": f"eq.{festival_id}"},
            method="PATCH",
            json_data={
                "status": "rejected",
                "rejection_reason": approval.rejection_reason,
                "admin_notes": approval.admin_notes,
                "reviewed_at": datetime.now().isoformat(),
                "reviewed_by": str(user_id) if user_id else None
            }
        )
        
        return {
            "success": True,
            "message": "Festival rejected"
        }
    else:
        # ✅ DÜZELTME: Bilinmeyen action için log ekle ve hata fırlat
        logger.warning(f"⚠️ Unknown action received: '{approval.action}' for festival {festival_id}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: '{approval.action}'. Must be 'approve' or 'reject'"
        )


@router.post("/festivals/refresh", response_model=ManualTriggerResponse)
async def trigger_festival_scraping(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually trigger festival scraping for all sources (admin only)"""
    await verify_admin(credentials)
    
    try:
        from backend.tasks.content_tasks import scrape_festivals_task
        
        task = scrape_festivals_task.delay()
        logger.info(f"✅ Festival scraping triggered: {task.id}")
        
        return ManualTriggerResponse(
            task_id=task.id,
            message="Festival scraping task started successfully"
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Scraping tasks not configured")
    except Exception as e:
        logger.error(f"Failed to trigger festival scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEWS SOURCES ENDPOINTS
# ============================================================================

@router.get("/sources/news", response_model=Dict[str, Any])
async def list_news_sources(
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all configured news sources"""
    supabase_service = await get_supabase_service()
    
    params = {"select": "*", "order": "name.asc"}
    if is_active is not None:
        params["is_active"] = f"eq.{str(is_active).lower()}"
    
    sources = await make_supabase_request(supabase_service, "news_sources", params)
    
    return {
        "items": [NewsSourceResponse(**source) for source in sources] if sources else [],
        "total": len(sources) if sources else 0
    }


@router.post("/sources/news", response_model=NewsSourceResponse, status_code=201)
async def create_news_source(
    source: NewsSourceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add a new news source (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    source_data = source.dict()
    if source_data.get('url'):
        source_data['url'] = str(source_data['url'])
    
    result = await make_supabase_request(
        supabase_service,
        "news_sources",
        {},
        method="POST",
        json_data=source_data
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create news source")
    
    return NewsSourceResponse(**result[0])


@router.get("/sources/news/{source_id}", response_model=NewsSourceResponse)
async def get_news_source(
    source_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single news source by ID (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    sources = await make_supabase_request(
        supabase_service,
        "news_sources",
        {"id": f"eq.{source_id}", "select": "*"}
    )
    
    if not sources:
        raise HTTPException(status_code=404, detail="News source not found")
    
    return NewsSourceResponse(**sources[0])


@router.put("/sources/news/{source_id}", response_model=NewsSourceResponse)
@router.patch("/sources/news/{source_id}", response_model=NewsSourceResponse)
async def update_news_source(
    source_id: str,
    source: NewsSourceUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update news source configuration (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    update_data = {k: v for k, v in source.dict(exclude_unset=True).items()}
    
    if update_data.get('url'):
        update_data['url'] = str(update_data['url'])
    
    update_data["updated_at"] = datetime.now().isoformat()
    
    result = await make_supabase_request(
        supabase_service,
        "news_sources",
        {"id": f"eq.{source_id}"},
        method="PATCH",
        json_data=update_data
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="News source not found")
    
    return NewsSourceResponse(**result[0])


@router.delete("/sources/news/{source_id}")
async def delete_news_source(
    source_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a news source (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    await make_supabase_request(
        supabase_service,
        "news_sources",
        {"id": f"eq.{source_id}"},
        method="DELETE"
    )
    
    return {"success": True, "message": "News source deleted successfully"}


@router.post("/sources/news/{source_id}/fetch")
async def trigger_news_source_fetch(
    source_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually trigger a news source fetch (admin only)"""
    await verify_admin(credentials)
    
    try:
        logger.info(f"🔄 Manually triggering news fetch for: {source_id}")
        
        from celery import current_app
        task = current_app.send_task('aggregate_news', kwargs={'source_id': source_id})
        
        logger.info(f"✅ News fetch task started: {task.id}")
        
        return {
            "success": True,
            "message": "News fetch triggered",
            "task_id": task.id,
            "source_id": source_id
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger news fetch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FESTIVAL SOURCES ENDPOINTS
# ============================================================================

@router.get("/sources/festivals", response_model=Dict[str, Any])
async def list_festival_sources(
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all festival sources"""
    supabase_service = await get_supabase_service()
    
    params = {"select": "*", "order": "name.asc"}
    if is_active is not None:
        params["is_active"] = f"eq.{str(is_active).lower()}"
    
    sources = await make_supabase_request(supabase_service, "festival_sources", params)
    
    return {
        "items": [FestivalSourceResponse(**source) for source in sources] if sources else [],
        "total": len(sources) if sources else 0
    }


@router.post("/sources/festivals", response_model=FestivalSourceResponse, status_code=201)
async def create_festival_source(
    source: FestivalSourceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add a new festival source (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    source_data = source.dict()
    if source_data.get('url'):
        source_data['url'] = str(source_data['url'])
    
    result = await make_supabase_request(
        supabase_service,
        "festival_sources",
        {},
        method="POST",
        json_data=source_data
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create festival source")
    
    return FestivalSourceResponse(**result[0])


@router.get("/sources/festivals/{source_id}", response_model=FestivalSourceResponse)
async def get_festival_source(
    source_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single festival source by ID (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    sources = await make_supabase_request(
        supabase_service,
        "festival_sources",
        {"id": f"eq.{source_id}", "select": "*"}
    )
    
    if not sources:
        raise HTTPException(status_code=404, detail="Festival source not found")
    
    return FestivalSourceResponse(**sources[0])


@router.put("/sources/festivals/{source_id}", response_model=FestivalSourceResponse)
@router.patch("/sources/festivals/{source_id}", response_model=FestivalSourceResponse)
async def update_festival_source(
    source_id: str,
    source: FestivalSourceUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update festival source configuration (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    update_data = {k: v for k, v in source.dict(exclude_unset=True).items()}
    
    if update_data.get('url'):
        update_data['url'] = str(update_data['url'])
    
    update_data["updated_at"] = datetime.now().isoformat()
    
    result = await make_supabase_request(
        supabase_service,
        "festival_sources",
        {"id": f"eq.{source_id}"},
        method="PATCH",
        json_data=update_data
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Festival source not found")
    
    return FestivalSourceResponse(**result[0])


@router.delete("/sources/festivals/{source_id}")
async def delete_festival_source(
    source_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a festival source (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    await make_supabase_request(
        supabase_service,
        "festival_sources",
        {"id": f"eq.{source_id}"},
        method="DELETE"
    )
    
    return {"success": True, "message": "Festival source deleted successfully"}


@router.post("/sources/festivals/{source_id}/fetch")
async def trigger_festival_source_fetch(
    source_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually trigger a festival source fetch (admin only)"""
    await verify_admin(credentials)
    
    try:
        logger.info(f"🔄 Manually triggering festival fetch for: {source_id}")
        
        from celery import current_app
        task = current_app.send_task('scrape_festivals', kwargs={'source_id': source_id})
        
        logger.info(f"✅ Triggered festival fetch task: {task.id}")
        
        return {
            "success": True, 
            "message": "Festival fetch triggered successfully", 
            "task_id": task.id, 
            "source_id": source_id
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger festival fetch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEWS ARTICLES ENDPOINTS
# ============================================================================

@router.get("/news", response_model=Dict[str, Any])
async def list_news_articles(
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List all news articles (paginated, filtered)"""
    supabase_service = await get_supabase_service()
    
    params = {
        "select": "*",
        "order": "published_at.desc.nullslast,created_at.desc",
        "limit": limit,
        "offset": skip
    }
    
    if category:
        params["category"] = f"cs.{{{category}}}"
    
    articles = await make_supabase_request(supabase_service, "news_articles", params)
    
    return {
        "items": [NewsArticleResponse(**article) for article in articles] if articles else [],
        "total": len(articles) if articles else 0
    }


@router.get("/news/{article_id}", response_model=NewsArticleResponse)
async def get_news_article(article_id: str):
    """Get a single news article by ID"""
    supabase_service = await get_supabase_service()
    
    articles = await make_supabase_request(
        supabase_service,
        "news_articles",
        {"id": f"eq.{article_id}", "select": "*"}
    )
    
    if not articles:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return NewsArticleResponse(**articles[0])


@router.post("/news/refresh", response_model=ManualTriggerResponse)
async def trigger_news_aggregation(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually trigger news aggregation for all sources (admin only)"""
    await verify_admin(credentials)
    
    try:
        from backend.tasks.content_tasks import aggregate_news_task
        
        task = aggregate_news_task.delay()
        logger.info(f"✅ News aggregation triggered: {task.id}")
        
        return ManualTriggerResponse(
            task_id=task.id,
            message="News aggregation task started successfully"
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="News tasks not configured")
    except Exception as e:
        logger.error(f"Failed to trigger news aggregation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/news/{article_id}")
async def delete_news_article(
    article_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a news article (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    await make_supabase_request(
        supabase_service,
        "news_articles",
        {"id": f"eq.{article_id}"},
        method="DELETE"
    )
    
    return {"success": True, "message": "News article deleted successfully"}


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================

@router.get("/stats")
async def get_content_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get content aggregation statistics (admin only)"""
    await verify_admin(credentials)
    supabase_service = await get_supabase_service()
    
    try:
        # Get counts from each table
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {**supabase_service.headers, "Prefer": "count=exact"}
            
            # News articles count
            news_resp = await client.get(
                f"{supabase_service.rest_url}/news_articles",
                headers=headers,
                params={"select": "id", "limit": 1}
            )
            news_count = int(news_resp.headers.get('content-range', '0/0').split('/')[-1])
            
            # Discovered festivals count
            festivals_resp = await client.get(
                f"{supabase_service.rest_url}/discovered_festivals",
                headers=headers,
                params={"select": "id", "limit": 1}
            )
            festivals_count = int(festivals_resp.headers.get('content-range', '0/0').split('/')[-1])
            
            # Pending festivals count
            pending_resp = await client.get(
                f"{supabase_service.rest_url}/discovered_festivals",
                headers=headers,
                params={"select": "id", "status": "eq.pending", "limit": 1}
            )
            pending_count = int(pending_resp.headers.get('content-range', '0/0').split('/')[-1])
            
            # News sources count
            news_sources_resp = await client.get(
                f"{supabase_service.rest_url}/news_sources",
                headers=headers,
                params={"select": "id", "limit": 1}
            )
            news_sources_count = int(news_sources_resp.headers.get('content-range', '0/0').split('/')[-1])
            
            # Festival sources count
            festival_sources_resp = await client.get(
                f"{supabase_service.rest_url}/festival_sources",
                headers=headers,
                params={"select": "id", "limit": 1}
            )
            festival_sources_count = int(festival_sources_resp.headers.get('content-range', '0/0').split('/')[-1])
        
        return {
            "news_articles": news_count,
            "discovered_festivals": festivals_count,
            "pending_festivals": pending_count,
            "news_sources": news_sources_count,
            "festival_sources": festival_sources_count,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get content stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ============================================================================
# PUBLIC FESTIVALS ENDPOINTS (Ana sayfa için)
# ============================================================================

@router.get("/festivals/public", response_model=Dict[str, Any])
async def list_public_festivals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    country: Optional[str] = Query(None, description="Filter by country"),
    is_ai_friendly: Optional[bool] = Query(None, description="Filter AI-friendly festivals")
):
    """
    List all PUBLIC and ACTIVE festivals.
    This is what regular users see on the website.
    No authentication required.
    """
    supabase_service = await get_supabase_service()
    
    params = {
        "select": "*",
        "status": "eq.active",
        "visibility": "eq.public",
        "order": "submission_deadline.asc.nullslast,created_at.desc",
        "limit": limit,
        "offset": skip
    }
    
    if country:
        params["country"] = f"ilike.%{country}%"
    
    if is_ai_friendly is not None:
        params["is_ai_friendly"] = f"eq.{str(is_ai_friendly).lower()}"
    
    festivals = await make_supabase_request(supabase_service, "festivals", params)
    
    return {
        "items": festivals if festivals else [],
        "total": len(festivals) if festivals else 0
    }


@router.get("/festivals/public/{festival_id}")
async def get_public_festival(festival_id: str):
    """Get a single public festival by ID or slug"""
    supabase_service = await get_supabase_service()
    
    # Try by ID first
    festivals = await make_supabase_request(
        supabase_service,
        "festivals",
        {
            "or": f"(id.eq.{festival_id},slug.eq.{festival_id})",
            "status": "eq.active",
            "visibility": "eq.public",
            "select": "*"
        }
    )
    
    if not festivals:
        raise HTTPException(status_code=404, detail="Festival not found")
    
    return festivals[0]