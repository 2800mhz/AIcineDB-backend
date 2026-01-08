"""
Authentication and Authorization Utilities
"""
import os
import jwt
from typing import Optional, List
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Supabase JWT Secret - Dashboard > Settings > API > JWT Settings
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')

def get_admin_emails() -> List[str]:
    """Get list of admin emails from environment"""
    admins = []
    
    single = os.getenv('ADMIN_EMAIL', '')
    if single:
        admins.append(single.strip().lower())
    
    multiple = os.getenv('ADMIN_EMAILS', '')
    if multiple:
        admins.extend([email.strip().lower() for email in multiple.split(',') if email.strip()])
    
    MY_ADMIN_EMAILS = [
        "aicinedb@gmail.com",
        "hamburg31cisi@gmail.com", 
        "gcmsx@gmail.com",
        "stapeliagames@gmail.com",
    ]
    
    admins.extend([email.lower() for email in MY_ADMIN_EMAILS])
    
    if not admins:
        logger.warning("⚠️ No admin emails configured in environment")
        return []
        
    return list(set(admins))


def is_admin_email(email: str) -> bool:
    """Check if email is in admin list"""
    if not email:
        return False
    
    admin_emails = get_admin_emails()
    return email.strip().lower() in admin_emails


def verify_jwt_token(token: str) -> dict:
    """
    Verify Supabase JWT token and return payload.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        Decoded JWT payload with user info
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    if not SUPABASE_JWT_SECRET:
        logger.error("❌ SUPABASE_JWT_SECRET not configured!")
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: JWT secret not set"
        )
    
    try:
        # Decode JWT with Supabase secret
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("⚠️ JWT token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        logger.warning("⚠️ JWT invalid audience")
        raise HTTPException(status_code=401, detail="Invalid token audience")
    except jwt.InvalidTokenError as e:
        logger.warning(f"⚠️ JWT invalid: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current user from JWT token.
    
    Returns dict with: id, email, role, is_admin
    """
    try:
        token = credentials.credentials
        payload = verify_jwt_token(token)
        
        user_id = payload.get('sub')
        user_email = payload.get('email', '')
        
        # Get role from profiles table
        user_role = 'user'
        try:
            from backend.services.supabase_sync import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                profile_result = supabase.table("profiles") \
                    .select("role") \
                    .eq("id", user_id) \
                    .single() \
                    .execute()
                
                if profile_result.data:
                    user_role = profile_result.data.get("role", "user")
        except Exception as e:
            logger.warning(f"Could not fetch role from profiles: {e}")
        
        return {
            "id": user_id,
            "email": user_email,
            "role": user_role,
            "is_admin": is_admin_email(user_email) or user_role == 'admin'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def verify_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify user is admin"""
    user = await get_current_user(credentials)
    
    if not user.get('is_admin'):
        logger.warning(f"⚠️ Non-admin user attempted admin action: {user.get('email')}")
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )
    
    logger.info(f"✅ Admin verified: {user.get('email')}")
    return user


async def verify_creator(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify user is creator or admin"""
    user = await get_current_user(credentials)
    
    is_creator = user.get('role') in ['creator', 'admin'] or user.get('is_admin')
    
    if not is_creator:
        logger.warning(f"⚠️ Non-creator attempted creator action: {user.get('email')} (role: {user.get('role')})")
        raise HTTPException(
            status_code=403, 
            detail="Creator access required"
        )
    
    logger.info(f"✅ Creator verified: {user.get('email')} (role: {user.get('role')})")
    return {**user, "is_creator": True}


async def verify_creator_or_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Alias for verify_creator"""
    return await verify_creator(credentials)