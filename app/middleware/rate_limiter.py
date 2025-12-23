"""Simple rate limiting middleware"""
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time


class InMemoryRateLimiter:
    """In-memory rate limiter (simple implementation)"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            '/update': (1000000, 60),  # 100000 requests per minute for data write (load testing)
            '/api/channels': (50, 60),  # 50 requests per minute for channel operations
        }
    
    def is_allowed(self, key: str, endpoint: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        
        # Get limit for endpoint (default: 1000 requests per hour)
        max_requests, window = self.limits.get(endpoint, (1000, 3600))
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] 
                              if now - req_time < window]
        
        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True
    
    def cleanup(self):
        """Cleanup old requests (call periodically)"""
        now = time.time()
        for key in list(self.requests.keys()):
            self.requests[key] = [req_time for req_time in self.requests[key] 
                                  if now - req_time < 3600]  # Keep last hour
            if not self.requests[key]:
                del self.requests[key]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        skip_paths = ['/static/', '/docs', '/redoc', '/openapi.json', '/health', '/admin']
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_id = request.client.host if request.client else "unknown"
        
        # Check rate limit for specific endpoint patterns
        endpoint = request.url.path
        
        # Simplify endpoint for rate limiting
        if endpoint.startswith('/update'):
            rate_key = '/update'
        elif endpoint.startswith('/api/channels'):
            rate_key = '/api/channels'
        else:
            rate_key = 'default'
        
        # Check if allowed
        key = f"{client_id}:{rate_key}"
        if not rate_limiter.is_allowed(key, rate_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        return response





