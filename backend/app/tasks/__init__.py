"""
Celery application configuration.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery("aurora")

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_routes={
        "aurora.render_master": {"queue": "render_default"},
    },
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    task_time_limit=660,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
)
