"""
Aurora observability: structlog JSON logging, request/correlation IDs, Prometheus metrics, health.
"""
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context vars for request_id and correlation_id
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Prometheus metrics (HTTP default via instrumentator; custom below)
aurora_render_queue_depth = Gauge(
    "aurora_render_queue_depth",
    "Current render queue depth",
)
aurora_render_duration_seconds = Histogram(
    "aurora_render_duration_seconds",
    "Render job duration in seconds",
    buckets=[1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)
aurora_render_cost_dollars = Counter(
    "aurora_render_cost_dollars_total",
    "Estimated render cost in dollars",
)
aurora_active_websocket_connections = Gauge(
    "aurora_active_websocket_connections",
    "Active WebSocket connections",
)
aurora_heuristic_fallback_total = Counter(
    "aurora_heuristic_fallback_total",
    "Total heuristic fallback invocations (AuroraNet blocked or unavailable)",
)
aurora_error_total = Counter(
    "aurora_error_total",
    "Total errors by code",
    ["error_code"],
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request_id and correlation_id to context and response headers."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        corr_id = request.headers.get("x-correlation-id") or req_id
        request_id_ctx.set(req_id)
        correlation_id_ctx.set(corr_id)
        response = await call_next(request)
        response.headers["x-request-id"] = req_id
        response.headers["x-correlation-id"] = corr_id
        return response


async def health_shallow() -> dict[str, str]:
    """Shallow health: app is up."""
    return {"status": "ok", "service": "aurora-backend"}


async def health_deep(
    database_url: str | None,
    redis_url: str | None,
    s3_endpoint: str | None,
) -> dict[str, Any]:
    """Deep health: PostgreSQL, Redis, S3 connectivity."""
    result: dict[str, Any] = {"status": "ok", "checks": {}}
    # PostgreSQL
    if database_url:
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

            engine: AsyncEngine = create_async_engine(database_url)
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            result["checks"]["postgres"] = "ok"
        except Exception as e:
            result["checks"]["postgres"] = str(e)
            result["status"] = "degraded"
    # Redis
    if redis_url:
        try:
            import redis.asyncio as redis
            r = redis.from_url(redis_url)
            await r.ping()
            await r.aclose()
            result["checks"]["redis"] = "ok"
        except Exception as e:
            result["checks"]["redis"] = str(e)
            result["status"] = "degraded"
    # S3 (MinIO) - head bucket
    if s3_endpoint:
        result["checks"]["s3"] = "skipped"  # Implement with boto3 if needed
    return result
