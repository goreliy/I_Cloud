"""Simple rate limiting middleware (pure ASGI)"""
import json
import time
from collections import defaultdict
from starlette.types import ASGIApp, Receive, Scope, Send


class InMemoryRateLimiter:
    """In-memory rate limiter (simple implementation)"""

    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            '/update': (1000000, 60),
            '/api/channels': (50, 60),
        }

    def is_allowed(self, key: str, endpoint: str) -> bool:
        now = time.time()
        max_requests, window = self.limits.get(endpoint, (1000, 3600))
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        if len(self.requests[key]) >= max_requests:
            return False
        self.requests[key].append(now)
        return True

    def cleanup(self):
        now = time.time()
        for key in list(self.requests.keys()):
            self.requests[key] = [t for t in self.requests[key] if now - t < 3600]
            if not self.requests[key]:
                del self.requests[key]


rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware:
    """Pure ASGI rate limiting middleware"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        skip_paths = ['/static/', '/docs', '/redoc', '/openapi.json', '/health', '/admin']
        if any(path.startswith(p) for p in skip_paths):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_id = client[0] if client else "unknown"

        if path.startswith('/update'):
            rate_key = '/update'
        elif path.startswith('/api/channels'):
            rate_key = '/api/channels'
        else:
            rate_key = 'default'

        key = f"{client_id}:{rate_key}"
        if not rate_limiter.is_allowed(key, rate_key):
            body = json.dumps({"detail": "Rate limit exceeded. Please try again later."}).encode()
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"retry-after", b"60"],
                    [b"content-length", str(len(body)).encode()],
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
