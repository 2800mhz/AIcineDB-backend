"""
Complete Video Analysis Tasks with Full Integration
"""
import os
import logging
import asyncio
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
    
    # Create new event loop for this task
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
    Internal async function that runs the actual analysis.
    This runs in a fresh event loop created by the task.
    """
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
        
        # Progress callback
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
        
        # Run analysis pipeline
        logger.info(f"🎥 Analyzing video: {url}")
        analysis_result = await pipeline.analyze_film(url, job_id, update_progress)
        
        # Create film record
        logger.info(f"💾 Saving analysis results to database...")
        film_id = await db_ops.create_film(analysis_result)
        
        # Update job status to completed
        await db_ops.update_job_status(
            job_id,
            status='completed',
            progress=1.0,
            current_stage='Complete',
            film_id=film_id
        )
        
        logger.info(f"✅ Analysis complete - Film ID: {film_id}")
        
        return {
            'job_id': job_id,
            'film_id': film_id,
            'status': 'completed',
            'title': analysis_result.get('title', 'Unknown'),
            'duration': analysis_result.get('duration', 0),
            'total_shots': analysis_result.get('total_shots', 0),
            'total_characters': analysis_result.get('total_characters', 0),
            'style': analysis_result.get('style_fingerprint'),
        }


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
            # You can test a simple query here if needed
            return f"Async test completed: {message}"
    
    # Create new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_test())
        return result
    finally:
        loop.close()