"""
Celery tasks package
"""
from backend.tasks.celery_app import app

__all__ = ["app"]