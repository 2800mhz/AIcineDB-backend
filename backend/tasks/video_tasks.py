"""
Complete Video Analysis Tasks with Full Integration
Includes Cast & Crew extraction from credits and descriptions
"""
import os
import logging
import asyncio
from celery import Task
from backend.tasks.celery_app import app

# Setup logging
logger = logging.getLogger(__name__)

# --- Base Task ---

class CallbackTask(Task):
    """Base task with callbacks"""
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"✅ Task {task_id} completed successfully")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"❌ Task {task_id} failed: {exc}")

# --- Main Analysis Task ---

@app.task(base=CallbackTask, bind=True, name="backend.tasks.video_tasks.analyze_film_complete")
def analyze_film_complete(self, job_id: int, url: str):
    """
    Complete film analysis with all modules including Cast & Crew
    
    This is the main task that orchestrates the entire analysis pipeline.
    
    Args:
        job_id: Analysis job ID
        url: Video URL
        
    Returns:
        dict: Complete analysis results with film_id
    """
    
    # Create new event loop for this task to run async code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_run_analysis(self, job_id, url))
        return result
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        
        # Try to update job status to failed
        try:
            loop.run_until_complete(_update_job_failed(job_id, str(e)))
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
        
        raise e
    finally:
        # Clean up event loop
        try:
            loop.close()
            logger.info("🔄 Event loop closed")
        except Exception as e:
            logger.warning(f"Event loop close warning: {e}")


async def _run_analysis(task_self, job_id: int, url: str):
    """
    Internal async function that runs the actual analysis pipeline.
    """
    # Imports should be inside async function if they rely on certain environments/settings
    from backend.core.full_analysis_pipeline import FullAnalysisPipeline
    from backend.database.connection import get_task_db
    from backend.database.database_operations import DatabaseOperations
    
    logger.info(f"🎬 Starting complete analysis for job {job_id}")
    
    # Use context manager for database connection
    async with get_task_db() as db:
        db_ops = DatabaseOperations(db)
        
        # Update job status to processing
        await db_ops.update_job_status(
            job_id,
            status='processing',
            progress=0.0,
            current_stage='Starting analysis...',
            celery_task_id=task_self.request.id
        )
        
        # Initialize pipeline
        pipeline = FullAnalysisPipeline()
        
        # Progress callback function for Celery status updates
        def update_progress(progress: float, status: str):
            task_self.update_state(
                state="PROGRESS",
                meta={
                    'current': int(progress * 100),
                    'total': 100,
                    'status': status,
                    'job_id': job_id
                }
            )
            logger.info(f"📊 Progress: {int(progress * 100)}% - {status}")
        
        # Run main analysis pipeline (0-70%)
        logger.info(f"🎥 Analyzing video: {url}")
        analysis_result = await pipeline.analyze_film(
            url, 
            job_id, 
            progress_callback=update_progress
        )
        
        # Attempt to get film_id from analysis result or database
        film_id = analysis_result.get('film_id')
        if not film_id or film_id == 'Unknown':
            # Assuming db_ops has a method to retrieve film_id associated with the job
            film_id = await db_ops.get_film_id_from_job(job_id)
        
        film_id_int = film_id if isinstance(film_id, int) else None

        # ============================================================
        # FRAME EXTRACTION (70-76%)
        # ============================================================
        update_progress(0.70, "📸 Extracting key frames...")
        
        frames = []
        try:
            from backend.analyzers.visual.frame_extractor import FrameExtractor
            
            video_path = analysis_result.get('video_path')
            frames_dir = analysis_result.get('frames_dir', f'./analyses/job_{job_id}/extracted_frames')
            
            if video_path:
                frame_extractor = FrameExtractor()
                frames = await frame_extractor.extract_frames(
                    video_path=video_path,
                    output_dir=frames_dir,
                    interval_seconds=10,
                    max_frames=20,
                    generate_thumbnails=True
                )
                
                analysis_result['extracted_frames'] = frames
                logger.info(f"📸 Extracted {len(frames)} key frames")
            else:
                logger.warning("⚠️ No video path available for frame extraction")
                
        except Exception as e:
            logger.warning(f"⚠️ Frame extraction failed: {e}")
            analysis_result['extracted_frames'] = []
        
        update_progress(0.76, f"✓ Extracted {len(frames)} frames")

        # ============================================================
        # CAST & CREW EXTRACTION (77-85%)
        # ============================================================
        update_progress(0.77, "🎭 Extracting cast & crew...")
        
        try:
            cast_crew_result = await _extract_cast_crew(
                analysis_result=analysis_result,
                url=url
            )
            
            # Merge cast & crew into analysis result
            analysis_result['cast'] = cast_crew_result.get('cast', [])
            analysis_result['crew'] = cast_crew_result.get('crew', [])
            analysis_result['cast_crew_sources'] = cast_crew_result.get('sources', [])
            analysis_result['cast_crew_confidence'] = cast_crew_result.get('confidence', 0.0)
            
            logger.info(f"🎭 Found {len(analysis_result['cast'])} cast, {len(analysis_result['crew'])} crew")
            
        except Exception as e:
            logger.warning(f"⚠️ Cast & crew extraction failed: {e}")
            analysis_result['cast'] = analysis_result.get('cast', []) # Keep existing if any
            analysis_result['crew'] = analysis_result.get('crew', []) # Keep existing if any

        # ============================================================
        # SAVE CAST & CREW TO RELATIONAL DB (85-90%)
        # This step was missing in the original logic.
        # ============================================================
        if film_id_int:
            update_progress(0.85, "💾 Saving cast & crew to relational DB...")
            try:
                await _save_cast_crew(db_ops, film_id_int, analysis_result)
            except Exception as e:
                logger.error(f"❌ Failed to save cast/crew to DB: {e}", exc_info=True)
        else:
            logger.warning("Skipping relational DB save: Film ID not available.")
            
        update_progress(0.90, "☁️ Syncing to cloud...")

        # ============================================================
        # SYNC TO SUPABASE (90-100%)
        # ============================================================
        try:
            from backend.services.supabase_sync import SupabaseSyncService
            
            sync = SupabaseSyncService()
            
            if sync.enabled:
                logger.info(f"🔄 Supabase sync enabled - Starting sync...")
                
                # Prepare complete film data
                film_data = {
                    'job_id': str(job_id),
                    'title': analysis_result.get('title', 'Unknown'),
                    'url': url,
                    'duration': analysis_result.get('duration', 0),
                    'uploader': analysis_result.get('uploader', 'Unknown'),
                    'description': analysis_result.get('description', ''),
                    'year': analysis_result.get('year'),
                    'thumbnail': analysis_result.get('thumbnail'),
                    
                    # Analysis data
                    'narrative': analysis_result.get('narrative', {}),
                    'audio_features': analysis_result.get('audio_features', {}),
                    'style': analysis_result.get('style', {}),
                    'shots': analysis_result.get('shots', []),
                    'characters': analysis_result.get('characters', []),
                    'scenes': analysis_result.get('scenes', []),
                    'color_palette': analysis_result.get('color_palette', {}),
                    'style_fingerprint': analysis_result.get('style_fingerprint'),
                    
                    # Cast & crew
                    'cast': analysis_result.get('cast', []),
                    'crew': analysis_result.get('crew', []),
                }
                
                # ✅ CRITICAL FIX: Await must be added here!
                result = await sync.sync_film(film_data)
                
                supabase_id = None
                if result:
                    supabase_id = result.get('id', 'unknown')
                    logger.info(f"✅ Synced to Supabase - Title ID: {supabase_id}")
                    
                    # Upload extracted frames to Supabase Storage
                    if frames and supabase_id:
                        update_progress(0.95, "📤 Uploading frames to cloud storage...")
                        try:
                            frame_urls = await sync.upload_frames(supabase_id, frames)
                            logger.info(f"✅ Uploaded {len(frame_urls)} frames to Supabase Storage")
                        except Exception as upload_err:
                            logger.warning(f"⚠️ Frame upload failed: {upload_err}")
                else:
                    logger.warning("⚠️ Supabase sync returned None - check logs")
            else:
                logger.info("ℹ️ Supabase sync disabled (SUPABASE_URL or SUPABASE_SERVICE_KEY not set)")
                
        except Exception as e:
            logger.error(f"⚠️ Supabase sync failed: {e}", exc_info=True)
        
        update_progress(1.0, "✅ Analysis complete!")
        logger.info(f"✅ Analysis complete - Film ID: {film_id}")
        
        return {
            'job_id': job_id,
            'film_id': film_id,
            'status': 'completed',
            'title': analysis_result.get('title', 'Unknown'),
            'duration': analysis_result.get('duration', 0),
            'total_shots': analysis_result.get('total_shots', 0),
            'total_characters': analysis_result.get('total_characters', 0),
            'total_cast': len(analysis_result.get('cast', [])),
            'total_crew': len(analysis_result.get('crew', [])),
            'total_frames': len(frames),
            'style': analysis_result.get('style_fingerprint'),
        }


async def _extract_cast_crew(analysis_result: dict, url: str) -> dict:
    """
    Extract cast & crew from video description and end credits using the Extractor.
    
    Args:
        analysis_result: Current analysis results
        url: Original video URL
        
    Returns:
        Dict with cast and crew lists
    """
    from backend.analyzers.cast_crew_extractor import CastCrewExtractor
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logger.warning("⚠️ GEMINI_API_KEY not set, skipping cast & crew extraction")
        return {'cast': [], 'crew': [], 'sources': [], 'confidence': 0.0}
    
    extractor = CastCrewExtractor(gemini_api_key)
    
    # Get data from analysis result
    video_path = analysis_result.get('video_path', '')
    description = analysis_result.get('description', '')
    duration = analysis_result.get('duration', 0)
    frames_dir = analysis_result.get('frames_dir', '')
    characters = analysis_result.get('characters', [])
    
    # Run extraction
    result = await extractor.extract_all(
        video_path=video_path,
        description=description,
        duration=duration,
        frames_dir=frames_dir,
        characters=characters
    )
    
    return result


async def _save_cast_crew(db_ops, film_id: int, analysis_result: dict):
    """
    Save cast & crew to relational database (film_cast table).
    
    Args:
        db_ops: Database operations instance
        film_id: Film ID
        analysis_result: Analysis results with cast/crew
    """
    cast = analysis_result.get('cast', [])
    crew = analysis_result.get('crew', [])
    
    # 1. Clear existing cast & crew to prevent duplicates on rerun
    try:
        await db_ops.db.execute(
            "DELETE FROM film_cast WHERE film_id = :film_id",
            {'film_id': film_id}
        )
        logger.info(f"Cleared existing cast/crew for film {film_id}")
    except Exception as e:
        logger.warning(f"Failed to clear existing cast/crew: {e}")

    # 2. Save cast members
    for i, member in enumerate(cast):
        try:
            # Assuming 'film_cast' table is used for both cast and crew
            await db_ops.db.execute(
                """
                INSERT INTO film_cast (
                    film_id, name, role, type, department, 
                    screen_time, appearance_count, ordering
                ) VALUES (
                    :film_id, :name, :role, :type, :department,
                    :screen_time, :appearance_count, :ordering
                )
                """,
                {
                    'film_id': film_id,
                    'name': member.get('name', 'Unknown'),
                    'role': member.get('role', 'Actor'),
                    'type': member.get('type', 'actor'),
                    'department': 'acting', # Assuming all cast members are acting department
                    'screen_time': member.get('screen_time'),
                    'appearance_count': member.get('appearance_count'),
                    'ordering': i + 1
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save cast member {member.get('name')}: {e}")
    
    # 3. Save crew members
    for i, member in enumerate(crew):
        try:
            await db_ops.db.execute(
                """
                INSERT INTO film_cast (
                    film_id, name, role, type, department, ordering
                ) VALUES (
                    :film_id, :name, :role, :type, :department, :ordering
                )
                """,
                {
                    'film_id': film_id,
                    'name': member.get('name', 'Unknown'),
                    # Use provided role, default to 'Crew'
                    'role': member.get('role', 'Crew'),
                    # Set type as a standard 'crew' value
                    'type': 'crew', 
                    # Use provided department, default to 'production'
                    'department': member.get('department', 'production'),
                    'ordering': i + 1
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save crew member {member.get('name')}: {e}")
    
    logger.info(f"💾 Saved {len(cast)} cast, {len(crew)} crew members to film_cast table")


async def _update_job_failed(job_id: int, error_message: str):
    """
    Update job status to failed. 
    Runs in its own database context. 
    """
    from backend.database.connection import get_task_db
    from backend.database.database_operations import DatabaseOperations
    
    async with get_task_db() as db:
        db_ops = DatabaseOperations(db)
        await db_ops.update_job_status(
            job_id,
            status='failed',
            progress=0.0,
            current_stage='Failed',
            error_message=error_message
        )
        logger.info(f"📝 Job {job_id} marked as failed")


# ============================================================
# UTILITY TASKS
# ============================================================

@app.task(name="backend.tasks.video_tasks.extract_cast_crew_only")
def extract_cast_crew_only(film_id: int, url: str, description: str = ""):
    """
    Extract cast & crew for an existing film
    Useful for re-processing or updating cast info
    
    Args:
        film_id: Existing film ID
        url: Video URL
        description: Video description
        
    Returns:
        dict: Cast & crew results
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            _extract_cast_crew_standalone(film_id, url, description)
        )
        return result
    finally:
        loop.close()


async def _extract_cast_crew_standalone(film_id: int, url: str, description: str):
    """Standalone cast & crew extraction and save to DB"""
    from backend.database.connection import get_task_db
    from backend.database.database_operations import DatabaseOperations
    from backend.analyzers.cast_crew_extractor import CastCrewExtractor
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        return {'error': 'GEMINI_API_KEY not set'}
    
    async with get_task_db() as db:
        db_ops = DatabaseOperations(db)
        
        # Get existing film data
        film = await db.fetch_one(
            "SELECT * FROM films WHERE id = :film_id",
            {'film_id': film_id}
        )
        
        if not film:
            return {'error': 'Film not found'}
        
        # Get characters (needed for character mapping)
        characters = await db.fetch_all(
            "SELECT * FROM characters WHERE film_id = :film_id",
            {'film_id': film_id}
        )
        
        # Extract cast & crew
        extractor = CastCrewExtractor(gemini_api_key)
        result = await extractor.extract_all(
            video_path='', # Not available in standalone mode
            description=description or film.get('description', ''),
            duration=film.get('duration', 0),
            frames_dir='', # Not available in standalone mode
            characters=[dict(c) for c in characters]
        )
        
        # Save to database
        analysis_result = {
            'cast': result.get('cast', []),
            'crew': result.get('crew', [])
        }
        
        # Save new cast & crew
        await _save_cast_crew(db_ops, film_id, analysis_result)
        
        return {
            'film_id': film_id,
            'cast_count': len(result.get('cast', [])),
            'crew_count': len(result.get('crew', [])),
            'sources': result.get('sources', []),
            'confidence': result.get('confidence', 0.0)
        }


@app.task(name="backend.tasks.video_tasks.test_task")
def test_task(message: str):
    """Test task for debugging"""
    logger.info(f"🧪 Test task received: {message}")
    return f"Test completed: {message}"


@app.task(name="backend.tasks.video_tasks.test_async_task")
def test_async_task(message: str):
    """Test async task with database connection"""
    
    async def _test():
        from backend.database.connection import get_task_db
        
        async with get_task_db() as db:
            logger.info(f"🧪 Test async task - DB connected")
            return f"Async test completed: {message}"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_test())
        return result
    finally:
        loop.close()