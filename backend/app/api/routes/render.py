"""
Render routes: start, status, SSE progress, cancel.
"""
from __future__ import annotations

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, get_redis
from app.core.errors import AuroraHTTPException
from app.core.feature_gates import require_export_format
from app.models.user import User
from app.services import crud
import redis.asyncio as aioredis

router = APIRouter(prefix="/render", tags=["render"])


class RenderRequest(BaseModel):
    session_id: str
    output_formats: List[str]
    target_lufs: float = -14.0
    ceiling_dbtp: float = -0.3
    limiter_mode: str = "transparent"
    priority: bool = False


@router.post("")
async def start_render(
    body: RenderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.session import Session
    result = await db.execute(select(Session).where(Session.id == body.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise AuroraHTTPException("AURORA-E401")
    if str(session.user_id) != str(current_user.id):
        raise AuroraHTTPException("AURORA-E402")

    sub = await crud.get_subscription(db, user_id=str(current_user.id))
    tier = sub.tier.value if sub and hasattr(sub.tier, "value") else (sub.tier if sub else "trial")
    state = sub.state.value if sub and hasattr(sub.state, "value") else (sub.state if sub else "active")

    for fmt in body.output_formats:
        require_export_format(fmt, tier, state)

    from app.models.enums import RenderStatus, SubscriptionTier as ST
    render_job = await crud.create_render_job(
        db,
        user_id=str(current_user.id),
        session_id=body.session_id,
        tier=ST(tier) if tier in [t.value for t in ST] else ST.TRIAL,
        status=RenderStatus.QUEUED,
        celery_task_id="pending",
        priority=0,
        output_s3_keys=body.output_formats,
    )

    queue = "render_priority" if (body.priority and tier == "enterprise") else "render_default"
    try:
        from app.tasks.render_tasks import render_master
        result = render_master.apply_async(
            kwargs={
                "user_id": str(current_user.id),
                "session_id": body.session_id,
                "render_job_id": str(render_job.id),
                "tier": tier,
                "output_formats": body.output_formats,
                "target_lufs": body.target_lufs,
                "ceiling_dbtp": body.ceiling_dbtp,
                "limiter_mode": body.limiter_mode,
            },
            queue=queue,
        )
        await crud.update_render_job(
            db,
            user_id=str(current_user.id),
            job_id=str(render_job.id),
            celery_task_id=result.id if result else "pending",
        )
    except Exception as e:
        import logging
        logger = logging.getLogger("aurora.render")
        logger.error("Celery dispatch failed for job %s: %s", render_job.id, e)
        await crud.update_render_job(
            db,
            user_id=str(current_user.id),
            job_id=str(render_job.id),
            status="failed",
            error_message=f"Dispatch failed: {e}",
        )
        raise AuroraHTTPException("AURORA-E900", f"Failed to queue render job: {e}")

    return {"job_id": str(render_job.id), "status": "queued"}


@router.get("/status/{job_id}")
async def get_render_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await crud.get_render_job(db, user_id=str(current_user.id), job_id=str(job_id))
    if not job:
        raise AuroraHTTPException("AURORA-E302")

    result = {
        "job_id": str(job.id),
        "status": job.status.value if hasattr(job.status, "value") else job.status,
        "progress": job.progress,
        "stage": job.current_stage,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error_message,
    }
    if job.output_s3_keys:
        from app.services import storage
        result["output_urls"] = {
            key: await storage.generate_presigned_download_url(key)
            for key in (job.output_s3_keys or [])
        }
    return result


@router.get("/progress/{session_id}")
async def stream_progress(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
):
    channel = f"render_progress:{session_id}"

    async def event_generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"data: {data}\n\n"
                    try:
                        parsed = json.loads(data)
                        if parsed.get("status") in ("completed", "failed"):
                            break
                    except Exception:
                        pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/{job_id}", status_code=204)
async def cancel_render(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await crud.get_render_job(db, user_id=str(current_user.id), job_id=str(job_id))
    if not job:
        raise AuroraHTTPException("AURORA-E302")
    job_status = job.status.value if hasattr(job.status, "value") else job.status
    if job_status not in ("queued", "processing"):
        raise AuroraHTTPException("AURORA-E303")
    await crud.update_render_job(db, user_id=str(current_user.id), job_id=str(job_id), status="canceled")
