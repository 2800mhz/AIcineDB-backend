"""
============================================================================
AIcineDB Backend - Request Timeout Middleware
============================================================================
Tracks request processing time and logs slow requests.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request processing time.
    
    Features:
    - Tracks request duration
    - Logs slow requests (configurable threshold)
    - Adds X-Process-Time header for monitoring
    
    Args:
        app: The ASGI application
        slow_request_threshold: Time in seconds to consider a request slow (default: 5.0)
    
    Example:
        ```python
        app.add_middleware(
            RequestTimeoutMiddleware,
            slow_request_threshold=5.0,
        )
        ```
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
