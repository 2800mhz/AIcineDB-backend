"""
Security middleware for AIcineDB Backend
Implements security headers and other security-related middleware
"""
import time
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
    - Strict-Transport-Security: enforce HTTPS
    - Content-Security-Policy: restrict resource loading
    - Removes Server header to hide server information
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
            # Consider using nonces or hashes in production if docs are disabled
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


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request processing time.
    
    Logs slow requests and can be used to enforce timeouts.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold: float = 5.0,
    ):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track request processing time"""
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Add processing time header
        response.headers['X-Process-Time'] = str(round(process_time, 3))
        
        # Log slow requests
        if process_time > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )
        
        return response
