"""
Complete Video Analysis Tasks with Full Integration
"""
import os
import logging
from celery import Task
from backend.tasks.celery_app import app

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with callbacks"""
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"✅ Task {task_id} completed successfully")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"❌ Task {task_id} failed: {exc}")


@app.task(base=CallbackTask, bind=True, name="backend.tasks.video_tasks.analyze_film_complete")
def analyze_film_complete(self, job_id: int, url: str):
    """
    Complete film analysis with all modules
    
    This is the main task that orchestrates the entire analysis pipeline:
    1. Download video
    2. Extract frames & audio
    3. Detect shots & extract keyframes
    4. Classify visual style
    5. Transcribe audio
    6. Analyze narrative with Gemini
    7. Track characters
    8. Detect scenes
    9. Save everything to database
    
    Args:
        job_id: Analysis job ID
        url: Video URL
        
    Returns:
        dict: Complete analysis results with film_id
    """
    try:
        import asyncio
        from backend.core.full_analysis_pipeline import FullAnalysisPipeline
        from backend.database.connection import database
        from backend.database.database_operations import DatabaseOperations
        
        logger.info(f"🎬 Starting complete analysis for job {job_id}")
        
        # Initialize pipeline
        pipeline = FullAnalysisPipeline()
        
        # Progress callback
        def update_progress(progress: float, status: str):
            self.update_state(
                state="PROGRESS",
                meta={
                    'current': int(progress * 100),
                    'total': 100,
                    'status': status,
                    'job_id': job_id
                }
            )
        
        # Update job status to processing
        async def update_job_processing():
            db_ops = DatabaseOperations(database)
            await db_ops.update_job_status(
                job_id,
                status='processing',
                progress=0.0,
                current_stage='Starting analysis...',
                celery_task_id=self.request.id
            )
        
        asyncio.run(update_job_processing())
        
        # Run analysis pipeline
        analysis_result = asyncio.run(
            pipeline.analyze_film(url, job_id, update_progress)
        )
        
        # Save to database
        async def save_to_database():
            db_ops = DatabaseOperations(database)
            
            # Create film record
            film_id = await db_ops.create_film(analysis_result)
            
            # Update job status
            await db_ops.update_job_status(
                job_id,
                status='completed',
                progress=1.0,
                current_stage='Complete',
                film_id=film_id
            )
            
            return film_id
        
        film_id = asyncio.run(save_to_database())
        
        logger.info(f"✅ Analysis complete - Film ID: {film_id}")
        
        return {
            'job_id': job_id,
            'film_id': film_id,
            'status': 'completed',
            'title': analysis_result['title'],
            'duration': analysis_result['duration'],
            'total_shots': analysis_result['total_shots'],
            'total_characters': analysis_result['total_characters'],
            'style': analysis_result.get('style_fingerprint'),
        }
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        
        # Update job status to failed
        async def update_job_failed():
            from backend.database.connection import database
            from backend.database.database_operations import DatabaseOperations
            
            db_ops = DatabaseOperations(database)
            await db_ops.update_job_status(
                job_id,
                status='failed',
                error_message=str(e)
            )
        
        try:
            import asyncio
            asyncio.run(update_job_failed())
        except:
            pass
        
        raise


@app.task(base=CallbackTask, bind=True, name="backend.tasks.video_tasks.analyze_video")
def analyze_video(self, video_id: int, video_path: str):
    """Simple analyze video (legacy compatibility)"""
    try:
        import time
        
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Starting..."}
        )
        
        logger.info(f"Analyzing video {video_id} at {video_path}")
        
        for i in range(1, 6):
            time.sleep(2)
            self.update_state(
                state="PROGRESS",
                meta={"current": i * 20, "total": 100, "status": f"Step {i}/5..."}
            )
        
        return {
            "video_id": video_id,
            "status": "completed",
            "analysis": {
                "duration": "00:02:30",
                "frames_analyzed": 150,
                "scenes_detected": 8,
                "audio_analyzed": True
            }
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


@app.task(base=CallbackTask, bind=True, name="backend.tasks.video_tasks.analyze_video_full")
def analyze_video_full(self, url: str):
    """
    Full video analysis (without database integration)
    For testing purposes
    """
    try:
        import uuid
        import asyncio
        from backend.core.full_analysis_pipeline import FullAnalysisPipeline
        
        job_id = int(uuid.uuid4().int % 1000000)
        
        # Initialize
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Initializing..."}
        )
        
        pipeline = FullAnalysisPipeline()
        
        # Progress callback
        def update_progress(progress: float, status: str):
            self.update_state(
                state="PROGRESS",
                meta={
                    'current': int(progress * 100),
                    'total': 100,
                    'status': status
                }
            )
        
        # Run analysis
        result = asyncio.run(
            pipeline.analyze_film(url, job_id, update_progress)
        )
        
        return {
            'status': 'completed',
            'job_id': job_id,
            'title': result['title'],
            'duration': result['duration'],
            'total_shots': result['total_shots'],
            'style': result.get('style_fingerprint'),
        }
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise


@app.task(name="backend.tasks.video_tasks.test_task")
def test_task(message: str = "Hello from Celery!"):
    """Simple test task"""
    import time
    
    logger.info(f"Test task running: {message}")
    time.sleep(2)
    
    return {
        "status": "success",
        "message": message,
        "timestamp": time.time()
    }


@app.task(name="backend.tasks.video_tasks.cleanup_old_files")
def cleanup_old_files():
    """
    Periodic task to cleanup old analysis files
    Can be scheduled with Celery Beat
    """
    import shutil
    from pathlib import Path
    from datetime import datetime, timedelta
    
    logger.info("🗑️ Running cleanup task...")
    
    try:
        analyses_dir = Path("/app/analyses")
        cutoff_date = datetime.now() - timedelta(days=7)
        
        cleaned = 0
        for job_dir in analyses_dir.glob("job_*"):
            # Check directory age
            if job_dir.stat().st_mtime < cutoff_date.timestamp():
                shutil.rmtree(job_dir)
                cleaned += 1
        
        logger.info(f"✓ Cleaned {cleaned} old analysis directories")
        
        return {"cleaned": cleaned}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"error": str(e)}
