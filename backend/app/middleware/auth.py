"""
API Authentication Middleware for Behavioral Agentic AI
Provides optional API key authentication for production use

Features:
- API key validation
- Rate limiting per client
- Request logging
- Security headers

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import os
import time
import logging
from typing import Optional, Dict
from collections import defaultdict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Configuration
API_KEY_HEADER = "X-API-Key"
API_KEY_ENABLED = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/health",
}


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed and record it."""
        now = time.time()
        
        # Clean old requests
        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if now - ts < self.window_seconds
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[client_id].append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        current = len([
            ts for ts in self.requests.get(client_id, [])
            if now - ts < self.window_seconds
        ])
        return max(0, self.max_requests - current)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication and rate limiting middleware.
    
    Features:
    - API key validation (when enabled)
    - Rate limiting per client IP
    - Security headers
    - Request logging
    """
    
    def __init__(self, app, api_key: Optional[str] = None):
        super().__init__(app)
        self.api_key = api_key or API_KEY
        self.rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier (IP or API key)
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if path requires auth
        path = request.url.path
        requires_auth = API_KEY_ENABLED and path not in PUBLIC_PATHS and not path.startswith("/docs")
        
        # Validate API key if required
        if requires_auth and self.api_key:
            provided_key = request.headers.get(API_KEY_HEADER)
            
            if not provided_key:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "API key required",
                        "message": f"Please provide API key in {API_KEY_HEADER} header"
                    }
                )
            
            if provided_key != self.api_key:
                logger.warning(f"[AUTH] Invalid API key from {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "Invalid API key"}
                )
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": RATE_LIMIT_WINDOW
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-RateLimit-Remaining"] = str(
            self.rate_limiter.get_remaining(client_ip)
        )
        
        return response


def validate_api_key(api_key: str) -> bool:
    """Validate an API key."""
    if not API_KEY:
        return True  # No key configured, allow all
    return api_key == API_KEY


def generate_api_key() -> str:
    """Generate a secure API key."""
    import secrets
    return f"bai_{secrets.token_urlsafe(32)}"
