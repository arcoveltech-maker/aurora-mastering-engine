"""Aurora backend FastAPI application."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.observability import (
    RequestIDMiddleware,
    health_deep,
    health_shallow,
)

metrics_app = make_asgi_app()
# Mount Prometheus metrics at /api/metrics for consistency with nginx proxy
# We'll mount at /metrics and nginx can proxy /api/metrics -> backend:8000/metrics if needed


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown: close pools, etc.


app = FastAPI(title="Aurora API", version="5.0.0", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.AURORA_ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


app.mount("/metrics", metrics_app)
