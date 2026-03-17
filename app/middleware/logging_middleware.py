"""Request logging middleware (pure ASGI — no BaseHTTPMiddleware)"""
import time
from starlette.types import ASGIApp, Receive, Scope, Send
from app.database import SessionLocal
from app.models.request_log import RequestLog


class RequestLoggingMiddleware:
    """Pure ASGI middleware to log HTTP requests.

    BaseHTTPMiddleware is known to corrupt / truncate response bodies
    for synchronous FastAPI endpoints that use dependency injection,
    so we avoid it entirely.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip logging for static files and health checks
        if path.startswith("/static") or path == "/health":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        # Extract client IP
        client = scope.get("client")
        ip_address = client[0] if client else None
        # Extract user-agent from headers
        user_agent = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"user-agent":
                user_agent = header_value.decode("latin-1")
                break

        start_time = time.time()
        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            response_time = (time.time() - start_time) * 1000
            try:
                db = SessionLocal()
                log_entry = RequestLog(
                    endpoint=path,
                    method=method,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    response_status=status_code,
                    response_time=round(response_time, 2),
                )
                db.add(log_entry)
                db.commit()
            except Exception:
                pass
            finally:
                try:
                    db.close()
                except Exception:
                    pass
