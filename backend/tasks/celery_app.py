"""
Celery application configuration for AI Cine Analyzer
"""
import os
from celery import Celery
from celery.schedules import crontab

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Celery app
app = Celery(
    "aicine_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "backend.tasks.video_tasks",
        "backend.tasks.content_tasks"  # ✅ Add content tasks
    ]
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,
    task_soft_time_limit=6000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_default_queue='celery',
    task_default_exchange='celery',
    task_default_routing_key='celery',
)

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'scrape-festivals-daily': {
        'task': 'scrape_festivals',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    'aggregate-news-6h': {
        'task': 'aggregate_news',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    'cleanup-old-news-weekly': {
        'task': 'cleanup_old_news',
        'schedule': crontab(day_of_week=0, hour=2),  # Sunday 2 AM
    },
}

if __name__ == "__main__":
    app.start()