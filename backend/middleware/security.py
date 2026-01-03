"""
============================================================================
AIcineDB Backend - Security Headers Middleware
============================================================================
Implements comprehensive security headers for all HTTP responses.
"""
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all HTTP responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 1; mode=block (XSS protection)
    - Referrer-Policy: strict-origin-when-cross-origin (referrer policy)
    - Strict-Transport-Security: enforce HTTPS (production only)
    - Content-Security-Policy: restrict resource loading
    - Removes Server header to hide server information
    
    Args:
        app: The ASGI application
        enable_hsts: Enable HTTP Strict Transport Security (default: True)
        enable_csp: Enable Content Security Policy (default: True)
    
    Example:
        ```python
        app.add_middleware(
            SecurityHeadersMiddleware,
            enable_hsts=settings.is_production,
            enable_csp=True,
        )
        ```
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enable_hsts: bool = True,
        enable_csp: bool = True,
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Enforce HTTPS in production
        if self.enable_hsts:
            # max-age=31536000 = 1 year
            # includeSubDomains: apply to all subdomains
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains'
            )
        
        # Content Security Policy
        if self.enable_csp:
            # Restrictive CSP for API
            # Note: 'unsafe-inline' for styles is needed for API docs (Swagger/ReDoc)
            # Note: img-src allows 'https:' to support external images in API responses
            # These can be tightened in production if API docs are disabled
            # Consider using nonces or hashes for inline styles when docs are disabled
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self' 'unsafe-inline'",  # For API docs only
                "img-src 'self' data: https:",  # Allow external images
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",  # Prevent embedding
                "base-uri 'self'",
                "form-action 'self'",
            ]
            response.headers['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Remove Server header to hide server information
        if 'Server' in response.headers:
            del response.headers['Server']
        
        return response
