"""
Celery tasks package
"""
from backend.tasks.celery_app import app
from backend.tasks.video_tasks import (
    analyze_video,
    extract_frames,
    analyze_audio,
    test_task,
)

__all__ = [
    "app",
    "analyze_video",
    "extract_frames",
    "analyze_audio",
    "test_task",
]