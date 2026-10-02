"""
Simple in-memory rate limiter middleware.
"""

import time
from typing import Dict, List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimiter:
    """In-memory rate limiter using sliding window log."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}
        
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is under limit for the given IP."""
        current_time = time.time()
        self.cleanup(current_time)
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
            
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
            
        self.requests[client_ip].append(current_time)
        return True
        
    def cleanup(self, current_time: float):
        """Remove expired entries."""
        cutoff_time = current_time - self.window_seconds
        for ip in list(self.requests.keys()):
            self.requests[ip] = [t for t in self.requests[ip] if t > cutoff_time]
            if not self.requests[ip]:
                del self.requests[ip]

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.limiter = RateLimiter(max_requests, window_seconds)
        
    async def dispatch(self, request: Request, call_next):
        """Process each request through rate limiter."""
        # Skip rate limiting for websocket and health endpoints
        if request.url.path.startswith("/ws") or request.url.path == "/health":
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        
        if not self.limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests"}
            )
            
        response = await call_next(request)
        return response
