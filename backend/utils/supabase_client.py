"""
Singleton Supabase Client for AIcineDB Backend
Implements connection pooling and proper error handling
"""
import os
import logging
from functools import lru_cache
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get singleton Supabase client instance with proper configuration.
    
    Uses @lru_cache() decorator to ensure single instance across application.
    Configured for backend use:
    - auto_refresh_token=False (backend doesn't need token refresh)
    - persist_session=False (backend doesn't persist sessions)
    
    Returns:
        Client: Configured Supabase client instance
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_SERVICE_KEY not configured
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url:
        raise ValueError(
            "SUPABASE_URL environment variable not set. "
            "Please configure it in your .env file."
        )
    
    if not supabase_key:
        raise ValueError(
            "SUPABASE_SERVICE_KEY environment variable not set. "
            "Please configure it in your .env file."
        )
    
    try:
        # Configure client for backend use
        client = create_client(
            supabase_url,
            supabase_key,
            options={
                "auto_refresh_token": False,  # Backend doesn't need token refresh
                "persist_session": False,      # Backend doesn't persist sessions
            }
        )
        
        logger.info("✓ Supabase client initialized (singleton)")
        return client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        raise


def get_supabase_client_optional() -> Optional[Client]:
    """
    Get Supabase client if configured, None otherwise.
    
    Useful for optional Supabase features where the service can
    continue without Supabase connectivity.
    
    Returns:
        Optional[Client]: Supabase client or None if not configured
    """
    try:
        return get_supabase_client()
    except ValueError as e:
        logger.warning(f"⚠ Supabase not configured: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Supabase client error: {e}")
        return None
