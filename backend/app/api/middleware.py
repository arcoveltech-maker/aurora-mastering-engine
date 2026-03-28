"""
Aurora ASGI middlewares: security headers, request ID, rate limiting.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable, List

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import settings


def get_allowed_origins() -> List[str]:
    origins = [f"https://{settings.DOMAIN}"]
    if settings.ENVIRONMENT == "development":
        origins += ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    return origins


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self' https://api.stripe.com; "
            "worker-src 'self' blob:; "
            "frame-src https://js.stripe.com; "
            "object-src 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Rate limit configuration: path_prefix -> (limit, window_seconds)
_RATE_LIMITS = {
    "/api/analyze": (30, 60),
    "/api/predict": (60, 60),
    "/api/render": (5, 60),
    "/api/chat": (20, 60),
    "/api/extract-stems": (10, 60),
    "/api/auth/login": (10, 60),
}
_AUTH_DEFAULT = (120, 60)
_ANON_DEFAULT = (10, 60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, redis_url: str):
        super().__init__(app)
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            redis = await self._get_redis()
        except Exception:
            return await call_next(request)

        path = request.url.path
        limit, window = _ANON_DEFAULT

        # Check path-specific limit
        matched = False
        for prefix, cfg in _RATE_LIMITS.items():
            if path.startswith(prefix):
                limit, window = cfg
                matched = True
                break

        if not matched:
            # Check if authenticated
            if request.cookies.get("aurora_access_token") or request.headers.get("Authorization"):
                limit, window = _AUTH_DEFAULT

        # Build key
        ip = request.client.host if request.client else "unknown"
        key = f"aurora:rl:{ip}:{path}"
        now = int(time.time())
        window_start = now - window

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(uuid.uuid4()): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()
            count = results[2]
        except Exception:
            return await call_next(request)

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "AURORA-E304", "message": "Rate limit exceeded"}},
                headers={"Retry-After": str(window)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response
