"""
Celery application configuration for AI Cine Analyzer
"""
import os
from celery import Celery

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Celery app
app = Celery(
    "aicine_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.tasks.video_tasks"]  # ✅ Bu yeterli
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

if __name__ == "__main__":
    app.start()