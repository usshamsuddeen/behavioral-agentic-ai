"""
Rate Limiting Middleware — Zone 7: Security (FR-7.2.5)

Custom in-memory rate limiter for FastAPI.
- Widget endpoints (/widget/*): 60 requests/minute per IP
- Dashboard/API endpoints (/api/*): 120 requests/minute per IP

Uses a sliding window counter stored in-memory.
No external dependencies required.
"""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FR-7.2.5: Rate Limiting
    - Widget routes:    60 req/min per IP
    - Dashboard routes: 120 req/min per IP
    - Other routes:     200 req/min per IP (generous default)
    """

    def __init__(self, app):
        super().__init__(app)
        # { ip: [(timestamp, ...)] }
        self.requests = defaultdict(list)
        self.WINDOW = 60  # 1 minute window

        self.LIMITS = {
            "widget": 60,
            "api": 120,
            "default": 200,
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For for proxied requests."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_route_category(self, path: str) -> str:
        """Determine which rate limit category a path belongs to."""
        if path.startswith("/widget"):
            return "widget"
        elif path.startswith("/api"):
            return "api"
        return "default"

    def _cleanup_old(self, key: str, now: float):
        """Remove timestamps older than the window."""
        cutoff = now - self.WINDOW
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static files, health checks, docs
        path = request.url.path
        if path in ("/", "/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        # Skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        category = self._get_route_category(path)
        limit = self.LIMITS[category]
        key = f"{client_ip}:{category}"

        now = time.time()
        self._cleanup_old(key, now)

        if len(self.requests[key]) >= limit:
            retry_after = int(self.WINDOW - (now - self.requests[key][0]))
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "limit": limit,
                    "window": f"{self.WINDOW}s",
                    "retry_after": max(retry_after, 1),
                    "category": category
                },
                headers={
                    "Retry-After": str(max(retry_after, 1)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + max(retry_after, 1)))
                }
            )

        # Record this request
        self.requests[key].append(now)
        remaining = limit - len(self.requests[key])

        response = await call_next(request)

        # Add rate limit headers to all responses
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.WINDOW))

        return response
