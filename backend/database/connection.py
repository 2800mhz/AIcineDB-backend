"""
Database connection and helpers
"""
import os
from contextlib import asynccontextmanager
from databases import Database
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aicine_user:aicine_pass@localhost:5432/aicine")

# Global database instance for FastAPI app
database = Database(DATABASE_URL)


async def init_db():
    """Initialize database connection for FastAPI app"""
    try:
        await database.connect()
        logger.info("✅ Database connected (FastAPI)")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


async def close_db():
    """Close database connection"""
    try:
        await database.disconnect()
        logger.info("🔌 Database disconnected")
    except Exception as e:
        logger.warning(f"Database disconnect warning: {e}")


@asynccontextmanager
async def get_db():
    """Get database connection context for FastAPI endpoints"""
    try:
        yield database
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise


def get_fresh_database():
    """
    Create a fresh database instance for Celery tasks.
    
    This is crucial for Celery workers because:
    1. Each Celery task runs in its own process/thread
    2. AsyncIO event loops cannot be shared across tasks
    3. Database connection pools must be tied to a single event loop
    
    Usage in Celery tasks:
        db = get_fresh_database()
        try:
            await db.connect()
            # ... use db ...
        finally:
            await db.disconnect()
    
    Returns:
        Database: Fresh database instance with its own connection pool
    """
    logger.info("🔄 Creating fresh database connection for Celery task")
    return Database(DATABASE_URL)


@asynccontextmanager
async def get_task_db():
    """
    Context manager for database connections in Celery tasks.
    Automatically handles connection and disconnection.
    
    Usage:
        async with get_task_db() as db:
            # use db
            await db.execute(...)
    """
    db = get_fresh_database()
    try:
        await db.connect()
        logger.info("✅ Task database connected")
        yield db
    except Exception as e:
        logger.error(f"❌ Task database error: {e}")
        raise
    finally:
        try:
            await db.disconnect()
            logger.info("🔌 Task database disconnected")
        except Exception as e:
            logger.warning(f"Task database disconnect warning: {e}")