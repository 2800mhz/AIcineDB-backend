"""
AI Cine Analyzer - Main FastAPI Application
Modern film analysis platform with Gemini AI
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from backend.services.ai_banner_generator import ai_banner_service
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import json

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
# AUTHENTICATION
# ============================================================================

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from Supabase JWT token"""
    try:
        from backend.services.supabase_sync import SupabaseSyncService
        sync = SupabaseSyncService()
        
        # Verify token with Supabase
        user = sync.supabase.auth.get_user(credentials.credentials)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        return user.user.user_metadata
        
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

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
    """Submit a video URL for analysis"""
    try:
        # ✅ DEBUG: Request'i kontrol et
        logger.info(f"🔍 Request received:")
        logger.info(f"   - URL: {request.url}")
        
        # Pydantic modelinde tanımlı değilse getattr kullanıyoruz
        title_id = getattr(request, 'title_id', None)
        logger.info(f"   - title_id: {title_id} (type: {type(title_id)})")
        logger.info(f"   - priority: {request.priority}")
        
        async with get_db() as db:
            priority_map = {
                "low": 1,
                "normal": 5,
                "high": 10
            }
            priority_value = priority_map.get(request.priority, 5)
            
            # Create job
            job = await db.fetch_one(
                query="""
                INSERT INTO analysis_jobs (url, status, priority)
                VALUES (:url, 'pending', :priority)
                RETURNING *
                """,
                values={
                    "url": str(request.url), 
                    "priority": priority_value
                }
            )
            
            # Task'ı çağır
            from backend.tasks.video_tasks import analyze_film_complete
            
            task = analyze_film_complete.delay(
                job['id'], 
                str(request.url),
                title_id=title_id  # ✅ title_id gönder
            )
            
            logger.info(f"📥 Created job {job['id']} (title_id: {title_id}, priority: {priority_value})")
            
            return AnalysisJobResponse(
                job_id=job['id'],
                status=job['status'],
                url=str(request.url),
                created_at=job['created_at'],
                celery_task_id=task.id
            )
            
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_job_status(job_id: int):
    """Get status of an analysis job"""
    try:
        async with get_db() as db:
            job = await db.fetch_one(
                query="SELECT * FROM analysis_jobs WHERE id = :job_id",
                values={"job_id": job_id}
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
                    WHERE status = :status
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :skip
                """
                jobs = await db.fetch_all(query, values={"status": status, "limit": limit, "skip": skip})
            else:
                query = """
                    SELECT * FROM analysis_jobs
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :skip
                """
                jobs = await db.fetch_all(query, values={"limit": limit, "skip": skip})
            
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
                LIMIT :limit OFFSET :skip
            """
            
            films = await db.fetch_all(query, values={"limit": limit, "skip": skip})
            
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
                query="SELECT * FROM films WHERE id = :film_id",
                values={"film_id": film_id}
            )
            
            if not film:
                raise HTTPException(status_code=404, detail="Film not found")
            
            # Get related data
            narrative = await db.fetch_one(
                query="SELECT * FROM narratives WHERE film_id = :film_id",
                values={"film_id": film_id}
            )
            
            transcript = await db.fetch_one(
                query="SELECT * FROM transcripts WHERE film_id = :film_id",
                values={"film_id": film_id}
            )
            
            audio = await db.fetch_one(
                query="SELECT * FROM audio_features WHERE film_id = :film_id",
                values={"film_id": film_id}
            )
            
            shots = await db.fetch_all(
                query="SELECT * FROM shots WHERE film_id = :film_id ORDER BY shot_number",
                values={"film_id": film_id}
            )
            
            characters = await db.fetch_all(
                query="SELECT * FROM characters WHERE film_id = :film_id ORDER BY screen_time DESC",
                values={"film_id": film_id}
            )
            
            scenes = await db.fetch_all(
                query="SELECT * FROM scenes WHERE film_id = :film_id ORDER BY scene_number",
                values={"film_id": film_id}
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
                query="SELECT id FROM films WHERE id = :film_id",
                values={"film_id": film_id}
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
                    CROSS JOIN (SELECT visual_embedding FROM films WHERE id = :film_id) ref
                    WHERE f.id != :film_id AND f.visual_embedding IS NOT NULL
                    ORDER BY f.visual_embedding <=> ref.visual_embedding
                    LIMIT :limit
                """
                similar = await db.fetch_all(query, values={"film_id": film_id, "limit": limit})
            elif similarity_type == "narrative":
                query = """
                    SELECT 
                        f.id as film_id,
                        f.title,
                        1 - (f.text_embedding <=> ref.text_embedding) as similarity,
                        f.metadata->>'style_fingerprint' as style_fingerprint
                    FROM films f
                    CROSS JOIN (SELECT text_embedding FROM films WHERE id = :film_id) ref
                    WHERE f.id != :film_id AND f.text_embedding IS NOT NULL
                    ORDER BY f.text_embedding <=> ref.text_embedding
                    LIMIT :limit
                """
                similar = await db.fetch_all(query, values={"film_id": film_id, "limit": limit})
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
                    CROSS JOIN (SELECT * FROM films WHERE id = :film_id) ref
                    WHERE f.id != :film_id
                        AND f.visual_embedding IS NOT NULL
                        AND f.text_embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT :limit
                """
                similar = await db.fetch_all(query, values={"film_id": film_id, "limit": limit})
            
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
            values = {}
            param_counter = 1
            
            if filters.theme:
                param_name = f"theme"
                conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(metadata->'narrative'->'themes') as theme
                        WHERE theme->>'name' ILIKE :{param_name}
                    )
                """)
                values[param_name] = f"%{filters.theme}%"
                param_counter += 1
            
            if filters.min_duration:
                param_name = f"min_duration"
                conditions.append(f"duration >= :{param_name}")
                values[param_name] = filters.min_duration
                param_counter += 1
            
            if filters.max_duration:
                param_name = f"max_duration"
                conditions.append(f"duration <= :{param_name}")
                values[param_name] = filters.max_duration
                param_counter += 1
            
            if filters.mood:
                param_name = f"mood"
                conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM audio_features
                        WHERE film_id = films.id AND mood = :{param_name}
                    )
                """)
                values[param_name] = filters.mood
                param_counter += 1
            
            values["limit"] = limit
            where_clause = " AND ".join(conditions)
            
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
                LIMIT :limit
            """
            
            films = await db.fetch_all(query, values=values)
            
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
            
            # Handle None values
            if not stats:
                return {
                    "total_films": 0,
                    "total_duration_hours": 0,
                    "films_last_week": 0,
                    "pending_jobs": 0,
                    "processing_jobs": 0
                }
            
            return {
                "total_films": stats['total_films'] or 0,
                "total_duration_hours": round(stats['total_duration'] / 3600, 2) if stats['total_duration'] else 0,
                "films_last_week": stats['films_last_week'] or 0,
                "pending_jobs": stats['pending_jobs'] or 0,
                "processing_jobs": stats['processing_jobs'] or 0
            }
            
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ADMIN - SUPABASE PHOTO MANAGEMENT
# ============================================================================

@app.delete("/api/admin/titles/{title_id}/photos/{frame_id}")
async def admin_delete_photo(
    title_id: str,
    frame_id: str):  # ← credentials parametresini kaldır
    """Delete a photo from Supabase (Admin only)"""
    
    try:
        from backend.services.supabase_sync import SupabaseSyncService
        sync = SupabaseSyncService()
        
        # ❌ Auth kontrolünü kaldır (test için)
        # user = sync.supabase.auth.get_user(credentials.credentials)
        # if not user or user. user.user_metadata.get('role') != 'admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get frame info
        response = sync. supabase.table('title_frames').select('*').eq('id', frame_id).execute()
        
        if not response. data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Frame not found")
        
        frame = response.data[0]
        frame_url = frame.get('frame_url', '')
        
        # Delete from database
        sync.supabase.table('title_frames'). delete().eq('id', frame_id).execute()
        
        # Delete from storage
        if frame_url and '/title-frames/' in frame_url:
            storage_path = frame_url.split('/title-frames/')[-1]. split('?')[0]
            
            try:
                sync.supabase.storage.from_('title-frames').remove([storage_path])
                logger. info(f"✓ Deleted storage file: {storage_path}")
            except Exception as storage_err:
                logger.warning(f"Storage delete failed: {storage_err}")
        
        logger.info(f"🗑️ Deleted photo {frame_id} from title {title_id}")
        
        return {"success": True, "message": "Photo deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete photo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/admin/titles/{title_id}/photos/reorder")
async def admin_reorder_photos(
    title_id: str,
    reorder_data: dict):  # ← credentials parametresini kaldır
    """Reorder photos (Admin only)"""
    
    try:
        from backend.services.supabase_sync import SupabaseSyncService
        sync = SupabaseSyncService()
        
        # ❌ Auth kontrolünü kaldır (test için)
        # user = sync.supabase.auth.get_user(credentials.credentials)
        # if not user or user.user. user_metadata.get('role') != 'admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        frame_ids = reorder_data.get('frame_ids', [])
        
        if not frame_ids:
            raise HTTPException(status_code=400, detail="frame_ids required")
        
        # Update ordering
        for idx, frame_id in enumerate(frame_ids):
            sync.supabase.table('title_frames').update({
                'ordering': idx + 1
            }).eq('id', frame_id).execute()
        
        logger.info(f"📸 Reordered {len(frame_ids)} photos for title {title_id}")
        
        return {
            "success": True,
            "message": f"Reordered {len(frame_ids)} photos",
            "count": len(frame_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reorder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/titles/{title_id}/photos/upload")
async def admin_upload_photo(
    title_id: str,
    file: UploadFile = File(...),
    ordering: int = Form(default=0)):  # ← credentials parametresini kaldır
    """Upload new photo (Admin only)"""
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only images allowed")
    
    try:
        from backend.services.supabase_sync import SupabaseSyncService
        sync = SupabaseSyncService()
        
        # ❌ Auth kontrolünü kaldır (test için)
        # user = sync.supabase.auth.get_user(credentials.credentials)
        # if not user or user.user.user_metadata. get('role') != 'admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        # Generate filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        storage_filename = f"{title_id}/manual_{uuid. uuid4().hex[:8]}. {file_ext}"
        
        # Upload to storage
        file_bytes = await file.read()
        
        sync.supabase.storage.from_('title-frames').upload(
            storage_filename,
            file_bytes,
            file_options={'content-type': file.content_type, 'upsert': 'true'}
        )
        
        # Get public URL
        public_url = sync.supabase.storage.from_('title-frames').get_public_url(storage_filename)
        
        # Create DB record
        frame_data = {
            'title_id': title_id,
            'frame_url': public_url,
            'frame_number': 0,
            'timestamp': 0.0,
            'ordering': ordering
        }
        
        response = sync.supabase.table('title_frames').insert(frame_data).execute()
        
        logger.info(f"📸 Uploaded photo to title {title_id}")
        
        return {
            "success": True,
            "frame": response.data[0] if response.data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger. error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "aicine_main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

# ============================================================
# AI BANNER GENERATION
# ============================================================

from backend.services.ai_banner_generator import ai_banner_service

@app.get("/api/ai-banner/options")
async def get_banner_options():
    """Get available AI models and options"""
    return ai_banner_service.get_options()


@app.post("/api/ai-banner/generate")
def generate_ai_banner(request: dict):  # ← async kaldırıldı
    """Generate AI banner (synchronous)
    
    Body: {
        "category": "cinematic",
        "style": "dramatic",
        "element": "camera",
        "color_palette": "warm",
        "num_variations": 3,
        "preferred_model": "sd-turbo"  // optional
    }
    """
    try:
        from backend.services.supabase_sync import SupabaseSyncService
        import uuid
        
        # Generate banners (synchronous call)
        variations = ai_banner_service.generate_banner(
            category=request. get('category', 'cinematic'),
            style=request.get('style', 'dramatic'),
            element=request.get('element'),
            color_palette=request. get('color_palette', 'vibrant'),
            num_variations=request.get('num_variations', 3),
            preferred_model=request.get('preferred_model')
        )
        
        # Upload to Supabase
        sync = SupabaseSyncService()
        banner_urls = []
        user_id = 'test_user'  # TODO: Get from auth
        
        for idx, image_bytes in enumerate(variations):
            filename = f"banners/{user_id}/ai_{uuid.uuid4().hex[:8]}_{idx}.jpg"
            
            sync.supabase.storage.from_('user-content'). upload(
                filename,
                image_bytes,
                file_options={'content-type': 'image/jpeg', 'upsert': 'true'}
            )
            
            public_url = sync.supabase.storage.from_('user-content').get_public_url(filename)
            banner_urls.append(public_url)
        
        logger.info(f"✅ Generated {len(banner_urls)} AI banners")
        
        return {
            "success": True,
            "variations": banner_urls,
            "count": len(banner_urls)
        }
        
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/banner")
async def update_user_banner(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update user's banner
    
    Body: {
        "banner_url": "https://..."
    }
    """
    try:
        from backend.services.supabase_sync import SupabaseSyncService
        sync = SupabaseSyncService()
        
        user_id = current_user.get('sub')
        banner_url = request.get('banner_url')
        
        # Update user metadata
        sync.supabase. auth.update_user({
            "data": {
                "banner_url": banner_url
            }
        })
        
        logger.info(f"✅ Updated banner for user {user_id}")
        
        return {"success": True, "banner_url": banner_url}
        
    except Exception as e:
        logger.error(f"❌ Failed to update banner: {e}")
        raise HTTPException(status_code=500, detail=str(e))