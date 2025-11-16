"""
Database connection and helpers
"""
import os
from contextlib import asynccontextmanager
from databases import Database
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aicine_user:aicine_pass@postgres:5432/aicine")

database = Database(DATABASE_URL)


async def init_db():
    """Initialize database connection"""
    try:
        await database.connect()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


async def close_db():
    """Close database connection"""
    await database.disconnect()
    logger.info("Database disconnected")


@asynccontextmanager
async def get_db():
    """Get database connection context"""
    try:
        yield database
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise