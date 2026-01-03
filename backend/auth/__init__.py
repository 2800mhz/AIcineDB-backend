"""
Authentication module for AIcineDB Backend
"""
from backend.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    verify_ownership,
    verify_title_ownership,
)

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "verify_ownership",
    "verify_title_ownership",
]
