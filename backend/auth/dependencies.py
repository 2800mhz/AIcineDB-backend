"""
Authentication and Authorization Dependencies for FastAPI
Provides reusable dependencies for JWT validation and role-based access control
"""
import os
import logging
from typing import Optional, Callable
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


def get_admin_emails() -> list[str]:
    """
    Get list of admin emails from environment variables.
    
    Checks both ADMIN_EMAIL (single) and ADMIN_EMAILS (comma-separated).
    
    Returns:
        list[str]: List of admin email addresses (lowercase)
    """
    admins = []
    
    # Single admin email
    single = os.getenv('ADMIN_EMAIL', '')
    if single:
        admins.append(single.strip().lower())
    
    # Multiple admin emails (comma-separated)
    multiple = os.getenv('ADMIN_EMAILS', '')
    if multiple:
        admins.extend([email.strip().lower() for email in multiple.split(',') if email.strip()])
    
    if not admins:
        logger.warning("⚠️ No admin emails configured in environment variables")
    
    return list(set(admins))  # Remove duplicates


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Extract and validate JWT token from Authorization header.
    
    Validates the Bearer token and returns user data if valid.
    Raises 401 Unauthorized if token is invalid or missing.
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        
    Returns:
        dict: User data containing:
            - id: User UUID
            - email: User email
            - role: User role from user_metadata
            - is_admin: Boolean indicating admin status
            
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    try:
        supabase = get_supabase_client()
        
        # Extract token from credentials
        token = credentials.credentials
        
        # Validate token and get user
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_response.user
        user_email = user.email
        user_role = user.user_metadata.get('role', 'user')
        
        # Check if user is admin
        admin_emails = get_admin_emails()
        is_admin = (
            user_role == 'admin' or 
            (user_email and user_email.lower() in admin_emails)
        )
        
        # Return user data
        user_data = {
            "id": user.id,
            "email": user_email,
            "role": user_role,
            "is_admin": is_admin
        }
        
        logger.debug(f"✓ User authenticated: {user_email} (role: {user_role})")
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Require user to have admin or moderator role.
    
    Checks if the current user has admin privileges.
    Raises 403 Forbidden if user doesn't have sufficient privileges.
    
    Args:
        current_user: User data from get_current_user dependency
        
    Returns:
        dict: User data (same as get_current_user)
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    if not current_user.get('is_admin', False):
        logger.warning(
            f"⚠️ Non-admin user attempted admin action: "
            f"{current_user.get('email')} (role: {current_user.get('role')})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. You do not have sufficient privileges."
        )
    
    logger.info(f"✓ Admin access granted: {current_user.get('email')}")
    return current_user


def verify_ownership(
    resource_table: str,
    resource_id_param: str = "resource_id",
    owner_field: str = "uploaded_by"
) -> Callable:
    """
    Factory function to create ownership verification dependency.
    
    Creates a dependency that verifies the current user owns the resource
    being accessed. Admins can bypass ownership checks.
    
    Args:
        resource_table: Supabase table name (e.g., "titles", "reviews")
        resource_id_param: Path parameter name for resource ID
        owner_field: Field name in table that stores owner user ID
        
    Returns:
        Callable: FastAPI dependency function
        
    Example:
        @router.delete("/titles/{title_id}")
        async def delete_title(
            title_id: str,
            resource: dict = Depends(verify_ownership("titles", "title_id")),
            supabase: Client = Depends(get_supabase_client)
        ):
            # User owns this title or is admin
            ...
    """
    async def dependency(
        resource_id: str,
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        """
        Verify user owns the resource or is admin.
        
        Args:
            resource_id: ID of the resource to check
            current_user: Current authenticated user
            
        Returns:
            dict: Resource data from database
            
        Raises:
            HTTPException: 403 if user doesn't own resource and isn't admin
            HTTPException: 404 if resource not found
        """
        try:
            supabase = get_supabase_client()
            
            # Fetch resource
            response = supabase.table(resource_table).select("*").eq("id", resource_id).execute()
            
            if not response.data or len(response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{resource_table.capitalize()} not found"
                )
            
            resource = response.data[0]
            resource_owner_id = resource.get(owner_field)
            
            # Allow if user is admin
            if current_user.get('is_admin', False):
                logger.info(
                    f"✓ Admin access to {resource_table}/{resource_id}: "
                    f"{current_user.get('email')}"
                )
                return resource
            
            # Check ownership
            if resource_owner_id != current_user['id']:
                logger.warning(
                    f"⚠️ User {current_user.get('email')} attempted to access "
                    f"{resource_table}/{resource_id} owned by {resource_owner_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this resource"
                )
            
            logger.debug(
                f"✓ Ownership verified: {current_user.get('email')} owns "
                f"{resource_table}/{resource_id}"
            )
            return resource
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Ownership verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify resource ownership"
            )
    
    return dependency


# Convenience function for common use case: verify title ownership
verify_title_ownership = verify_ownership("titles", "title_id", "uploaded_by")


# Optional authentication (doesn't raise 401 if no token)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.
    
    Useful for endpoints that work differently for authenticated vs.
    unauthenticated users but don't require authentication.
    
    Args:
        credentials: Optional HTTP Authorization credentials
        
    Returns:
        Optional[dict]: User data if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None
