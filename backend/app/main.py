"""Aurora backend FastAPI application."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AuroraHTTPException, aurora_exception_handler, unhandled_exception_handler
from app.core.observability import health_deep, health_shallow
from app.api.middleware import SecurityHeadersMiddleware, RequestIDMiddleware, RateLimitMiddleware

# Import all routers
from app.api.routes.auth import router as auth_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.upload import router as upload_router
from app.api.routes.render import router as render_router
from app.api.routes.billing import router as billing_router
from app.api.routes.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown: close pools, etc.


app = FastAPI(title="Aurora API", version="5.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
app.add_exception_handler(AuroraHTTPException, aurora_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ---------------------------------------------------------------------------
# Middleware (last added = outermost wrapper)
# ---------------------------------------------------------------------------
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.REDIS_URL,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.AURORA_ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(sessions_router, prefix=API_PREFIX)
app.include_router(upload_router, prefix=API_PREFIX)
app.include_router(render_router, prefix=API_PREFIX)
app.include_router(billing_router, prefix=API_PREFIX)
app.include_router(webhooks_router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
async def get_health():
    return await health_shallow()


@app.get("/api/health/deep", tags=["health"])
async def get_health_deep():
    return await health_deep(
        database_url=settings.DATABASE_URL,
        redis_url=settings.REDIS_URL,
        s3_endpoint=settings.S3_ENDPOINT_URL,
    )


# ---------------------------------------------------------------------------
# Prometheus metrics (optional)
# ---------------------------------------------------------------------------
try:
    from prometheus_client import make_asgi_app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
except ImportError:
    pass
