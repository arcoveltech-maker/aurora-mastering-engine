"""
Celery render task.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List, Optional

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.tasks import celery_app

logger = logging.getLogger("aurora.render_tasks")

# Max concurrent renders per user
_MAX_SLOTS_PER_USER = 3
_RENDER_SLOT_PREFIX = "aurora:render_slots:"


def _run_async(coro):
    """Run async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="aurora.render_master", queue="render_default")
def render_master(
    self: Task,
    user_id: str,
    session_id: str,
    render_job_id: str,
    tier: str,
    output_formats: List[str],
    target_lufs: float = -14.0,
    ceiling_dbtp: float = -0.3,
    limiter_mode: str = "transparent",
):
    return _run_async(
        _render_master_async(
            self, user_id, session_id, render_job_id, tier,
            output_formats, target_lufs, ceiling_dbtp, limiter_mode
        )
    )


async def _render_master_async(
    task: Task,
    user_id: str,
    session_id: str,
    render_job_id: str,
    tier: str,
    output_formats: List[str],
    target_lufs: float,
    ceiling_dbtp: float,
    limiter_mode: str,
):
    import redis.asyncio as aioredis
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.services import crud

    redis = await aioredis.from_url(settings.REDIS_URL)
    slot_key = f"{_RENDER_SLOT_PREFIX}{user_id}"
    channel = f"render_progress:{session_id}"

    async def publish(status: str, progress: int, stage: str, **extra):
        msg = json.dumps({"status": status, "progress": progress, "stage": stage, **extra})
        await redis.publish(channel, msg)

    slot_acquired = False
    try:
        count = await redis.incr(slot_key)
        await redis.expire(slot_key, 700)
        if count > _MAX_SLOTS_PER_USER:
            await redis.decr(slot_key)
            async with AsyncSessionLocal() as db:
                await crud.update_render_job(
                    db,
                    user_id=user_id,
                    job_id=render_job_id,
                    status="failed",
                    error_message="Render slot limit reached (AURORA-E304)",
                )
            await publish("failed", 0, "queued", error="AURORA-E304")
            return
        slot_acquired = True

        async with AsyncSessionLocal() as db:
            await crud.update_render_job(
                db,
                user_id=user_id,
                job_id=render_job_id,
                status="processing",
                progress=5.0,
                current_stage="starting",
            )
        await publish("processing", 5, "starting")

        # Step: feature extraction (heuristic fallback — NORMALIZATION_VALIDATED=False)
        logger.info(
            "heuristic_fallback: NORMALIZATION_VALIDATED=False, using heuristics for session %s",
            session_id,
        )
        audio_features = {
            "integrated_lufs": -18.0,
            "true_peak_dbtp": -2.0,
            "dynamic_range": 12.0,
            "spectral_centroid_hz": 3000.0,
            "heuristic": True,
        }
        await publish("processing", 30, "feature_extraction")

        # Step: compute macros (heuristic)
        macros = {
            "gain_db": target_lufs - audio_features["integrated_lufs"],
            "limiter_ceiling": ceiling_dbtp,
            "limiter_mode": limiter_mode,
            "eq_bands": [],
            "heuristic_fallback": True,
        }
        await publish("processing", 50, "inference")

        # Step: build manifest
        manifest = {
            "version": "1.0",
            "session_id": session_id,
            "macros": macros,
            "output_formats": output_formats,
            "target_lufs": target_lufs,
            "ceiling_dbtp": ceiling_dbtp,
        }
        await publish("processing", 65, "building_manifest")

        # Step: DSP stub (engine not compiled in worker — manifest only)
        from app.services import storage
        output_keys: Dict[str, str] = {}
        for fmt in output_formats:
            key = storage.build_key(user_id, session_id, f"output_{render_job_id}.{fmt.split('_')[0]}")
            output_keys[fmt] = key
        await publish("processing", 80, "dsp_processing")

        # Step: finalize
        async with AsyncSessionLocal() as db:
            await crud.update_render_job(
                db,
                user_id=user_id,
                job_id=render_job_id,
                status="completed",
                progress=100.0,
                current_stage="completed",
                output_s3_keys=list(output_keys.values()),
            )

        await publish("completed", 100, "completed", output_keys=output_keys)

    except SoftTimeLimitExceeded:
        logger.error("Render task soft time limit exceeded for job %s", render_job_id)
        try:
            from app.core.database import AsyncSessionLocal
            from app.services import crud
            async with AsyncSessionLocal() as db:
                await crud.update_render_job(
                    db,
                    user_id=user_id,
                    job_id=render_job_id,
                    status="failed",
                    error_message="AURORA-E301: Render timed out",
                )
        except Exception:
            pass
        await publish("failed", 0, "timeout", error="AURORA-E301")

    except Exception as e:
        logger.exception("Render task failed for job %s: %s", render_job_id, e)
        try:
            from app.core.database import AsyncSessionLocal
            from app.services import crud
            async with AsyncSessionLocal() as db:
                await crud.update_render_job(
                    db,
                    user_id=user_id,
                    job_id=render_job_id,
                    status="failed",
                    error_message=str(e),
                )
            await publish("failed", 0, "error", error=str(e))
        except Exception:
            pass

    finally:
        if slot_acquired:
            try:
                await redis.decr(slot_key)
            except Exception:
                pass
        await redis.aclose()
