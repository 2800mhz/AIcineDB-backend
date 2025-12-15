"""
Authentication and Authorization Utilities
"""
import os
from typing import Optional, List
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_admin_emails() -> List[str]:
    """Get list of admin emails from environment"""
    # Single admin
    single = os.getenv('ADMIN_EMAIL', '')
    if single:
        return [single. strip().lower()]
    
    # Multiple admins
    multiple = os.getenv('ADMIN_EMAILS', '')
    if multiple:
        return [email.strip().lower() for email in multiple. split(',') if email.strip()]
    
    # Fallback (development only)
    logger. warning("⚠️ No admin emails configured in environment")
    return []


def is_admin_email(email: str) -> bool:
    """Check if email is in admin list"""
    if not email:
        return False
    
    admin_emails = get_admin_emails()
    return email.strip().lower() in admin_emails


async def verify_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify user is admin (FastAPI dependency)"""
    try:
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        # Get user from JWT token
        user_response = supabase.auth.get_user(credentials.credentials)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        user = user_response.user
        user_email = user.email
        user_role = user.user_metadata.get('role', '')
        
        # Check admin status
        is_admin = (
            user_role == 'admin' or 
            is_admin_email(user_email)
        )
        
        if not is_admin:
            logger.warning(f"⚠️ Non-admin user attempted admin action: {user_email}")
            raise HTTPException(
                status_code=403, 
                detail="Admin access required. Contact system administrator."
            )
        
        logger.info(f"✅ Admin verified: {user_email}")
        
        return {
            "id": user.id,
            "email": user_email,
            "role": user_role,
            "is_admin": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Admin verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[dict]:
    """Get current user (optional admin check)"""
    try:
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        user_response = supabase.auth.get_user(credentials.credentials)
        
        if not user_response or not user_response.user:
            return None
        
        user = user_response.user
        
        return {
            "id": user.id,
            "email": user.email,
            "role": user.user_metadata.get('role', ''),
            "is_admin": is_admin_email(user.email)
        }
        
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        return None


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """Get current user without requiring authentication"""
    if not credentials:
        return None
    
    try:
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        user_response = supabase.auth.get_user(credentials.credentials)
        
        if not user_response or not user_response.user:
            return None
        
        user = user_response.user
        
        return {
            "id": user.id,
            "email": user.email,
            "role": user.user_metadata.get('role', ''),
            "is_admin": is_admin_email(user.email)
        }
        
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        return None


async def verify_creator(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify user is a creator (FastAPI dependency)"""
    try:
        from backend.services.supabase_sync import get_supabase_client
        supabase = get_supabase_client()
        
        # Get user from JWT token
        user_response = supabase.auth.get_user(credentials.credentials)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        user = user_response.user
        user_email = user.email
        user_role = user.user_metadata.get('role', '')
        
        # Check creator status (creator or admin)
        is_creator = user_role in ['creator', 'admin'] or is_admin_email(user_email)
        
        if not is_creator:
            logger.warning(f"⚠️ Non-creator user attempted creator action: {user_email}")
            raise HTTPException(
                status_code=403, 
                detail="Creator access required. Please upgrade your account."
            )
        
        logger.info(f"✅ Creator verified: {user_email}")
        
        return {
            "id": user.id,
            "email": user_email,
            "role": user_role,
            "is_admin": is_admin_email(user_email),
            "is_creator": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Creator verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def verify_creator_or_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify user is either a creator or admin (FastAPI dependency)
    Alias for verify_creator() - kept for semantic clarity in endpoints
    """
    return await verify_creator(credentials)