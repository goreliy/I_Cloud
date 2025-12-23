"""Request logging middleware"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import SessionLocal
from app.models.request_log import RequestLog


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Get request info
        method = request.method
        endpoint = str(request.url.path)
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Skip logging for static files and health checks
        if endpoint.startswith("/static") or endpoint == "/health":
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # milliseconds
        
        # Log to database (non-blocking)
        try:
            db = SessionLocal()
            log_entry = RequestLog(
                endpoint=endpoint,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
                response_status=response.status_code,
                response_time=round(response_time, 2)
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception:
            # Silently fail if logging fails (don't break the request)
            pass
        
        return response
















