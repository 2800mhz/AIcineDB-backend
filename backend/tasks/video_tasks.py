"""
Complete Video Analysis Tasks with Full Integration
Includes Cast & Crew extraction from credits and descriptions
With Auto-Cleanup for old frames before uploading new ones
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
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_run_analysis(self, job_id, url))
        return result
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        try:
            loop.run_until_complete(_update_job_failed(job_id, str(e)))
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
        raise e
    finally:
        try:
            loop.close()
            logger.info("🔄 Event loop closed")
        except Exception as e:
            logger.warning(f"Event loop close warning: {e}")


async def _cleanup_old_frames(sync, supabase_id: str):
    """
    Clean up old frames from Supabase before uploading new ones.
    
    Args:
        sync: SupabaseSyncService instance
        supabase_id: Title UUID in Supabase
    """
    import httpx
    
    if not sync.enabled or not supabase_id:
        return
    
    logger.info(f"🧹 Cleaning up old frames for title: {supabase_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Delete old frame records from database
            delete_url = f"{sync.rest_url}/title_frames"
            response = await client.delete(
                delete_url,
                headers=sync.headers,
                params={"title_id": f"eq.{supabase_id}"}
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"✓ Deleted old frame records from database")
            else:
                logger.warning(f"Frame record deletion returned: {response.status_code}")
            
            # 2. List and delete old storage files
            list_url = f"{sync.supabase_url}/storage/v1/object/list/title-frames"
            list_response = await client.post(
                list_url,
                headers={
                    "apikey": sync.supabase_key,
                    "Authorization": f"Bearer {sync.supabase_key}",
                    "Content-Type": "application/json"
                },
                json={"prefix": f"{supabase_id}/"}
            )
            
            if list_response.status_code == 200:
                files = list_response.json()
                
                if files and len(files) > 0:
                    # Build list of file paths to delete
                    paths_to_delete = [f"{supabase_id}/{f['name']}" for f in files if f.get('name')]
                    
                    if paths_to_delete:
                        # Delete files from storage
                        delete_storage_url = f"{sync.supabase_url}/storage/v1/object/title-frames"
                        delete_response = await client.delete(
                            delete_storage_url,
                            headers={
                                "apikey": sync.supabase_key,
                                "Authorization": f"Bearer {sync.supabase_key}",
                                "Content-Type": "application/json"
                            },
                            json={"prefixes": paths_to_delete}
                        )
                        
                        logger.info(f"✓ Deleted {len(paths_to_delete)} old storage files")
                else:
                    logger.info("ℹ️ No old storage files to delete")
            else:
                logger.warning(f"Could not list storage files: {list_response.status_code}")
                
    except Exception as e:
        logger.warning(f"⚠️ Cleanup warning (non-fatal): {e}")


async def _run_analysis(task_self, job_id: int, url: str):
    """
    Internal async function that runs the actual analysis pipeline.
    """
    from backend.core.full_analysis_pipeline import FullAnalysisPipeline
    from backend.database.connection import get_task_db
    from backend.database.database_operations import DatabaseOperations
    
    logger.info(f"🎬 Starting complete analysis for job {job_id}")
    
    async with get_task_db() as db:
        db_ops = DatabaseOperations(db)
        
        await db_ops.update_job_status(
            job_id,
            status='processing',
            progress=0.0,
            current_stage='Starting analysis...',
            celery_task_id=task_self.request.id
        )
        
        pipeline = FullAnalysisPipeline()
        
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
        
        film_id = analysis_result.get('film_id')
        if not film_id or film_id == 'Unknown':
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
            analysis_result['cast'] = cast_crew_result.get('cast', [])
            analysis_result['crew'] = cast_crew_result.get('crew', [])
            analysis_result['cast_crew_sources'] = cast_crew_result.get('sources', [])
            analysis_result['cast_crew_confidence'] = cast_crew_result.get('confidence', 0.0)
            logger.info(f"🎭 Found {len(analysis_result['cast'])} cast, {len(analysis_result['crew'])} crew")
        except Exception as e:
            logger.warning(f"⚠️ Cast & crew extraction failed: {e}")
            analysis_result['cast'] = analysis_result.get('cast', [])
            analysis_result['crew'] = analysis_result.get('crew', [])

        # ============================================================
        # SAVE CAST & CREW TO RELATIONAL DB (85-90%)
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
                
                film_data = {
                    'job_id': str(job_id),
                    'title': analysis_result.get('title', 'Unknown'),
                    'url': url,
                    'duration': analysis_result.get('duration', 0),
                    'uploader': analysis_result.get('uploader', 'Unknown'),
                    'description': analysis_result.get('description', ''),
                    'year': analysis_result.get('year'),
                    'thumbnail': analysis_result.get('thumbnail'),
                    'narrative': analysis_result.get('narrative', {}),
                    'audio_features': analysis_result.get('audio_features', {}),
                    'style': analysis_result.get('style', {}),
                    'shots': analysis_result.get('shots', []),
                    'characters': analysis_result.get('characters', []),
                    'scenes': analysis_result.get('scenes', []),
                    'color_palette': analysis_result.get('color_palette', {}),
                    'style_fingerprint': analysis_result.get('style_fingerprint'),
                    'cast': analysis_result.get('cast', []),
                    'crew': analysis_result.get('crew', []),
                }
                
                result = await sync.sync_film(film_data)
                
                if result and result.get('id'):
                    supabase_id = result['id']
                    logger.info(f"✅ Synced to Supabase - Title ID: {supabase_id}")
                    
                    # ✅ CLEANUP OLD FRAMES BEFORE UPLOADING NEW ONES
                    update_progress(0.93, "🧹 Cleaning up old frames...")
                    await _cleanup_old_frames(sync, supabase_id)
                    
                    update_progress(0.95, "📤 Uploading frames to cloud storage...")
                    
                    uploaded_frame_count = 0
                    total_duration = analysis_result.get('duration', 0)
                    
                    # First, try uploading from frames list
                    if frames:
                        try:
                            frame_urls = await sync.upload_frames(supabase_id, frames)
                            uploaded_frame_count = len(frame_urls)
                            logger.info(f"✅ Uploaded {uploaded_frame_count} frames to Supabase Storage")
                        except Exception as upload_err:
                            logger.warning(f"⚠️ Frame upload failed: {upload_err}")
                    
                    # If no frames from list, try from keyframes directory
                    if uploaded_frame_count == 0:
                        keyframes_dir = analysis_result.get('keyframes_dir')
                        
                        if not keyframes_dir:
                            keyframes_dir = f"analyses/job_{job_id}/keyframes"
                        
                        keyframes_dir = os.path.abspath(keyframes_dir)
                        logger.info(f"📁 Looking for keyframes in: {keyframes_dir}")
                        
                        if os.path.exists(keyframes_dir) and os.listdir(keyframes_dir):
                            logger.info(f"📤 Uploading keyframes from directory: {keyframes_dir}")
                            try:
                                uploaded_frame_count = await sync.upload_keyframes(
                                    supabase_id, 
                                    keyframes_dir,
                                    total_duration=total_duration
                                )
                                logger.info(f"✅ Uploaded {uploaded_frame_count} keyframes")
                            except Exception as upload_err:
                                logger.warning(f"⚠️ Keyframe upload failed: {upload_err}")
                        else:
                            logger.warning(f"⚠️ No keyframes found in {keyframes_dir}")
                            
                            # Try alternative paths
                            alt_paths = [
                                os.path.join(os.getcwd(), f"analyses/job_{job_id}/keyframes"),
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), f"analyses/job_{job_id}/keyframes"),
                            ]
                            
                            for alt_path in alt_paths:
                                if os.path.exists(alt_path) and os.listdir(alt_path):
                                    logger.info(f"📤 Found keyframes at alternative path: {alt_path}")
                                    try:
                                        uploaded_frame_count = await sync.upload_keyframes(
                                            supabase_id, 
                                            alt_path,
                                            total_duration=total_duration
                                        )
                                        logger.info(f"✅ Uploaded {uploaded_frame_count} keyframes from alt path")
                                        break
                                    except Exception as upload_err:
                                        logger.warning(f"⚠️ Alt path upload failed: {upload_err}")
                else:
                    logger.warning("⚠️ Supabase sync returned no title_id - keyframes will not be uploaded")
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
    """Extract cast & crew from video description and end credits."""
    from backend.analyzers.cast_crew_extractor import CastCrewExtractor
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logger.warning("⚠️ GEMINI_API_KEY not set, skipping cast & crew extraction")
        return {'cast': [], 'crew': [], 'sources': [], 'confidence': 0.0}
    
    extractor = CastCrewExtractor(gemini_api_key)
    
    result = await extractor.extract_all(
        video_path=analysis_result.get('video_path', ''),
        description=analysis_result.get('description', ''),
        duration=analysis_result.get('duration', 0),
        frames_dir=analysis_result.get('frames_dir', ''),
        characters=analysis_result.get('characters', [])
    )
    
    return result


async def _save_cast_crew(db_ops, film_id: int, analysis_result: dict):
    """Save cast & crew to relational database."""
    cast = analysis_result.get('cast', [])
    crew = analysis_result.get('crew', [])
    
    try:
        await db_ops.db.execute(
            "DELETE FROM film_cast WHERE film_id = :film_id",
            {'film_id': film_id}
        )
        logger.info(f"Cleared existing cast/crew for film {film_id}")
    except Exception as e:
        logger.warning(f"Failed to clear existing cast/crew: {e}")

    for i, member in enumerate(cast):
        try:
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
                    'department': 'acting',
                    'screen_time': member.get('screen_time'),
                    'appearance_count': member.get('appearance_count'),
                    'ordering': i + 1
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save cast member {member.get('name')}: {e}")
    
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
                    'role': member.get('role', 'Crew'),
                    'type': 'crew',
                    'department': member.get('department', 'production'),
                    'ordering': i + 1
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save crew member {member.get('name')}: {e}")
    
    logger.info(f"💾 Saved {len(cast)} cast, {len(crew)} crew members to film_cast table")


async def _update_job_failed(job_id: int, error_message: str):
    """Update job status to failed."""
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
    """Extract cast & crew for an existing film"""
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
        
        film = await db.fetch_one(
            "SELECT * FROM films WHERE id = :film_id",
            {'film_id': film_id}
        )
        
        if not film:
            return {'error': 'Film not found'}
        
        characters = await db.fetch_all(
            "SELECT * FROM characters WHERE film_id = :film_id",
            {'film_id': film_id}
        )
        
        extractor = CastCrewExtractor(gemini_api_key)
        result = await extractor.extract_all(
            video_path='',
            description=description or film.get('description', ''),
            duration=film.get('duration', 0),
            frames_dir='',
            characters=[dict(c) for c in characters]
        )
        
        analysis_result = {
            'cast': result.get('cast', []),
            'crew': result.get('crew', [])
        }
        
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