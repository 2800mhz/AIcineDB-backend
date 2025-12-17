"""
AI Cine Analyzer - Main FastAPI Application - FIXED
Modern film analysis platform with Gemini AI
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, UploadFile, File, Form
from backend.utils.auth import verify_admin, get_admin_emails, verify_creator_or_admin, get_current_user

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
import json

from backend.database.connection import get_db, init_db
from backend.tasks.video_tasks import analyze_film_complete
from backend.models.schemas import (
    AnalysisRequest,
    AnalysisJobResponse,
    FilmSummary,
    FilmDetail,
    SimilarFilm,
    SearchFilters,
    HealthCheck
)
from backend.api.festivals import router as festivals_router

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
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8080",
        "https://aicinedb.com",
        "https://www.aicinedb.com",
        "https://*.railway.app",  # Railway deployments
        "*"  # Allow all origins for development (remove for production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(festivals_router, prefix="/api", tags=["festivals"])


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
            "POST /api/upload": "Upload video (creators/admins only)",
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
        async with get_db() as db:
            # ✅ Priority mapping (string → integer)
            priority_map = {
                "low": 1,
                "normal": 5,
                "high": 10
            }
            
            # ✅ Eğer integer gelirse direkt kullan, değilse map'le
            if isinstance(request.priority, int):
                priority_value = request.priority
            else:
                priority_value = priority_map.get(request.priority.lower(), 5)
            
            # Create analysis job
            job = await db.fetch_one(
                query="""
                INSERT INTO analysis_jobs (url, status, priority)
                VALUES (:url, 'pending', :priority)
                RETURNING *
                """,
                values={
                    "url": str(request.url), 
                    "priority": priority_value  # ✅ Integer olarak gönder
                }
            )
            
            # ✅ Don't pass title_id from request - let Supabase sync generate it
            # This ensures each analysis gets unique storage
            task = analyze_film_complete.delay(
                job['id'], 
                str(request.url)
            )
            
            logger.info(f"🔥 Created job {job['id']} (priority: {priority_value})")
            
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


@app.get("/api/jobs/{job_id}")
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
            
            return dict(job)
            
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
# FILM ENDPOINTS - FIXED JSON PARSING
# ============================================================================

@app.get("/api/films", response_model=List[FilmSummary])
async def list_films(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("analyzed_at", regex="^(title|duration|analyzed_at)$")
):
    """List all analyzed films - FIXED"""
    try:
        async with get_db() as db:
            # FIXED: Don't try to extract themes from metadata in SQL
            # We'll handle it in Python instead
            query = f"""
                SELECT 
                    id,
                    title,
                    duration,
                    url,
                    analyzed_at,
                    metadata->>'style_fingerprint' as style_fingerprint
                FROM films
                WHERE analyzed_at IS NOT NULL
                ORDER BY {sort_by} DESC
                LIMIT :limit OFFSET :skip
            """
            
            films = await db.fetch_all(query, values={"limit": limit, "skip": skip})
            
            # Parse each film and extract themes from metadata
            result = []
            for film in films:
                film_dict = dict(film)
                
                # Extract themes from metadata if it exists
                # Get full metadata
                full_film = await db.fetch_one(
                    "SELECT metadata FROM films WHERE id = :id",
                    values={"id": film_dict['id']}
                )
                
                themes = []
                if full_film and full_film['metadata']:
                    try:
                        metadata = json.loads(full_film['metadata']) if isinstance(full_film['metadata'], str) else full_film['metadata']
                        # Try to get themes from narrative section
                        if 'narrative' in metadata and 'themes' in metadata['narrative']:
                            themes_data = metadata['narrative']['themes']
                            if isinstance(themes_data, list):
                                themes = [t.get('name', t) if isinstance(t, dict) else str(t) for t in themes_data[:3]]
                    except:
                        pass
                
                film_dict['themes'] = themes
                result.append(FilmSummary(**film_dict))
            
            return result
            
    except Exception as e:
        logger.error(f"Error listing films: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/films/{film_id}", response_model=FilmDetail)
async def get_film(film_id: int):
    """Get complete analysis for a film - FIXED"""
    try:
        async with get_db() as db:
            # Get film
            film = await db.fetch_one(
                query="SELECT * FROM films WHERE id = :film_id",
                values={"film_id": film_id}
            )
            
            if not film:
                raise HTTPException(status_code=404, detail="Film not found")
            
            film_dict = dict(film)
            
            # FIXED: Parse metadata if it's a string
            if film_dict.get('metadata') and isinstance(film_dict['metadata'], str):
                try:
                    film_dict['metadata'] = json.loads(film_dict['metadata'])
                except json.JSONDecodeError:
                    film_dict['metadata'] = {}
            
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
                **film_dict,
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
            
            if filters.theme:
                conditions.append("""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(metadata->'narrative'->'themes') as theme
                        WHERE theme->>'name' ILIKE :theme
                    )
                """)
                values["theme"] = f"%{filters.theme}%"
            
            if filters.min_duration:
                conditions.append("duration >= :min_duration")
                values["min_duration"] = filters.min_duration
            
            if filters.max_duration:
                conditions.append("duration <= :max_duration")
                values["max_duration"] = filters.max_duration
            
            if filters.mood:
                conditions.append("""
                    EXISTS (
                        SELECT 1 FROM audio_features
                        WHERE film_id = films.id AND mood = :mood
                    )
                """)
                values["mood"] = filters.mood
            
            values["limit"] = limit
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT 
                    id, title, duration, url, analyzed_at,
                    metadata->>'style_fingerprint' as style_fingerprint
                FROM films
                WHERE {where_clause}
                ORDER BY analyzed_at DESC
                LIMIT :limit
            """
            
            films = await db.fetch_all(query, values=values)
            
            # Parse themes like in list_films
            result = []
            for film in films:
                film_dict = dict(film)
                
                # Get metadata for themes
                full_film = await db.fetch_one(
                    "SELECT metadata FROM films WHERE id = :id",
                    values={"id": film_dict['id']}
                )
                
                themes = []
                if full_film and full_film['metadata']:
                    try:
                        metadata = json.loads(full_film['metadata']) if isinstance(full_film['metadata'], str) else full_film['metadata']
                        if 'narrative' in metadata and 'themes' in metadata['narrative']:
                            themes_data = metadata['narrative']['themes']
                            if isinstance(themes_data, list):
                                themes = [t.get('name', t) if isinstance(t, dict) else str(t) for t in themes_data[:3]]
                    except:
                        pass
                
                film_dict['themes'] = themes
                result.append(FilmSummary(**film_dict))
            
            return result
            
    except Exception as e:
        logger.error(f"Error searching films: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UPLOAD ENDPOINT
# ============================================================================

def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title"""
    import re
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


@app.post("/api/upload", response_model=AnalysisJobResponse)
async def upload_video(
    video_url: str = Form(...),
    video_title: Optional[str] = Form(None),
    priority: int = Form(5),
    current_user: dict = Depends(verify_creator_or_admin)
):
    """
    Video upload and analysis endpoint
    
    Only creators and admins can upload videos.
    Creates a title in Supabase and starts analysis job.
    """
    try:
        user_id = current_user['id']
        user_role = current_user['role']
        
        logger.info(f"📤 Upload request from user {user_id} ({user_role})")
        
        # Get Supabase client
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        if not supabase:
            raise HTTPException(status_code=500, detail="Supabase client not available")
        
        # Create title data
        title_text = video_title or "Untitled"
        slug = generate_slug(title_text)
        
        title_data = {
            "title": title_text,
            "status": "pending",
            "type": "movie",
            "uploaded_by": user_id,  # Use uploaded_by, NOT creator_id!
            "slug": slug,
            "trailer_youtube_url": video_url
        }
        
        # Insert title into Supabase
        logger.info(f"📝 Creating title: {title_text}")
        title_result = supabase.table('titles').insert(title_data).execute()
        
        if not title_result.data or len(title_result.data) == 0:
            logger.error("Failed to create title in database")
            raise HTTPException(status_code=500, detail="Failed to create title in database")
        
        title_id = title_result.data[0]['id']
        logger.info(f"✅ Title created with ID: {title_id}")
        
        # Create analysis job in local database
        async with get_db() as db:
            job = await db.fetch_one(
                query="""
                INSERT INTO analysis_jobs (url, status, priority)
                VALUES (:url, 'pending', :priority)
                RETURNING *
                """,
                values={
                    "url": video_url,
                    "priority": priority
                }
            )
            
            if not job:
                raise HTTPException(status_code=500, detail="Failed to create analysis job")
            
            job_id = job['id']
            logger.info(f"✅ Analysis job created with ID: {job_id}")
            
            # Start Celery task for analysis
            from backend.tasks.video_tasks import analyze_film_complete
            task = analyze_film_complete.delay(
                job_id,
                video_url,
                title_id=title_id  # Pass title_id to task
            )
            
            logger.info(f"🔥 Started analysis task: {task.id}")
            
            return AnalysisJobResponse(
                job_id=job_id,
                status=job['status'],
                url=video_url,
                created_at=job['created_at'],
                celery_task_id=task.id
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading video: {str(e)}")


# ============================================================================
# STATS ENDPOINT
# ============================================================================

security = HTTPBearer()

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


# ============================================================
# ADMIN - PHOTO MANAGEMENT (REVISED)
# ============================================================

async def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify user is admin"""
    try:
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        # Get user from token
        user = supabase. auth.get_user(credentials. credentials)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if admin
        user_email = user.user.email
        user_role = user.user.user_metadata.get('role')
        
        is_admin = (
            user_role == 'admin' or 
            user_email == 'hamburg31cisi@gmail.com'
        )
        
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return user. user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.delete("/api/admin/titles/{title_id}/photos/{frame_id}")
async def admin_delete_photo(
    title_id: str, 
    frame_id: str,
    current_user = Depends(verify_admin)  # ← Auth kontrolü eklendi
):
    
    """Delete photo from Supabase"""
    try:
        # ✅ YENİ: Doğru import
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        logger.info(f"🗑️ DELETE: title={title_id}, frame={frame_id}")
        
        # Get frame
        response = supabase.table('title_frames').select('*').eq('id', frame_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Frame not found")
        
        frame = response.data[0]
        frame_url = frame.get('frame_url', '')
        
        # Delete from DB
        supabase.table('title_frames').delete().eq('id', frame_id).execute()
        
        # Delete from storage
        if '/title-frames/' in frame_url:
            path = frame_url.split('/title-frames/')[-1].split('?')[0]
            try:
                supabase.storage.from_('title-frames').remove([path])
                logger.info(f"✓ Deleted storage: {path}")
            except Exception as e:
                logger.warning(f"Storage delete failed: {e}")
        
        logger.info(f"✅ Deleted {frame_id}")
        return {"success": True, "message": "Photo deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/admin/titles/{title_id}/photos/reorder")
async def admin_reorder_photos(
    title_id: str, 
    reorder_data: dict,
    current_user = Depends(verify_admin)  # ← Auth kontrolü eklendi
):
    """Reorder photos"""
    try:
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        frame_ids = reorder_data.get('frame_ids', [])
        if not frame_ids:
            raise HTTPException(status_code=400, detail="frame_ids required")
        
        logger.info(f"📸 Reorder {len(frame_ids)} photos for title {title_id}")
        
        for idx, frame_id in enumerate(frame_ids):
            supabase.table('title_frames').update({'ordering': idx + 1}).eq('id', frame_id).execute()
        
        logger.info(f"✅ Reordered {len(frame_ids)} photos")
        return {"success": True, "message": f"Reordered {len(frame_ids)} photos", "count": len(frame_ids)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Reorder failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/titles/{title_id}/photos/upload")
async def admin_upload_photo(
    title_id: str, 
    file: UploadFile = File(...), 
    ordering: int = Form(0),
    current_user = Depends(verify_admin)  # ← Auth kontrolü eklendi
):

    """Upload new photo"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only images allowed")
    
    try:
        from backend.services.supabase_sync import get_supabase_client
        import uuid
        
        supabase = get_supabase_client()
        
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"{title_id}/manual_{uuid.uuid4().hex[:8]}.{ext}"
        
        file_bytes = await file.read()
        
        supabase.storage.from_('title-frames').upload(
            filename, file_bytes,
            file_options={'content-type': file.content_type, 'upsert': 'true'}
        )
        
        url = supabase.storage.from_('title-frames').get_public_url(filename)
        
        data = {
            'title_id': title_id,
            'frame_url': url,
            'frame_number': 0,
            'timestamp': 0.0,
            'ordering': ordering
        }
        
        response = supabase.table('title_frames').insert(data).execute()
        
        logger.info(f"📸 Uploaded photo to title {title_id}")
        return {"success": True, "frame": response.data[0] if response.data else None}
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )