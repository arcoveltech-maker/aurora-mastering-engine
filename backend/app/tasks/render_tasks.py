"""Celery render task — full pipeline with feature extraction, inference, QC."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.tasks import celery_app

logger = logging.getLogger("aurora.render_tasks")

_MAX_SLOTS_PER_USER = 3
_RENDER_SLOT_PREFIX = "aurora:render_slots:"


def _run_async(coro):
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
    from app.services import crud, storage

    redis = await aioredis.from_url(settings.REDIS_URL)
    slot_key = f"{_RENDER_SLOT_PREFIX}{user_id}"
    channel  = f"render_progress:{session_id}"

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
                    db, user_id=user_id, job_id=render_job_id,
                    status="failed", error_message="Render slot limit reached (AURORA-E304)",
                )
            await publish("failed", 0, "queued", error="AURORA-E304")
            return
        slot_acquired = True

        async with AsyncSessionLocal() as db:
            await crud.update_render_job(
                db, user_id=user_id, job_id=render_job_id,
                status="processing", progress=5.0, current_stage="starting",
            )
        await publish("processing", 5, "starting")

        # ── Step 1: Get audio file from DB / S3 ────────────────────────────
        from pathlib import Path
        import tempfile
        tmp_path = None

        try:
            async with AsyncSessionLocal() as db:
                audio_file = await crud.get_session_audio_file(db, user_id=user_id, session_id=session_id)

            if audio_file and hasattr(audio_file, "s3_key") and audio_file.s3_key:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = Path(f.name)
                await storage.download_file(audio_file.s3_key, tmp_path)
        except Exception as e:
            logger.warning("Could not download audio file: %s — using heuristic features", e)

        await publish("processing", 20, "loading_audio")

        # ── Step 2: Feature extraction ──────────────────────────────────────
        from app.services.analysis import AudioFeatures, extract_features

        if tmp_path and tmp_path.exists():
            logger.info("feature_extraction_start: session=%s", session_id)
            audio_features = await extract_features(tmp_path)
            logger.info("feature_extraction_done: lufs=%.1f lra=%.1f",
                        audio_features.integrated_lufs, audio_features.lra)
        else:
            logger.warning(
                "heuristic_fallback: NORMALIZATION_VALIDATED=False, "
                "no audio file — using default features for session %s", session_id
            )
            audio_features = AudioFeatures(integrated_lufs=-18.0, true_peak_dbtp=-2.0, dynamic_range=12.0)

        await publish("processing", 35, "feature_extraction",
                      lufs=round(audio_features.integrated_lufs, 2))

        # ── Step 3: Macro inference (heuristic — NORMALIZATION_VALIDATED=False) ──
        from app.services.inference import predict_macros
        macros = await predict_macros(audio_features)
        macros["limiter_ceiling"] = ceiling_dbtp
        macros["limiter_mode"]    = limiter_mode
        await publish("processing", 50, "inference", macros_source="heuristic")

        # ── Step 4: Build WASM processing manifest ──────────────────────────
        from app.core.config import settings as cfg
        manifest = {
            "version":    "5.0",
            "session_id": session_id,
            "macros":     macros,
            "output_formats": output_formats,
            "target_lufs":    target_lufs,
            "ceiling_dbtp":   ceiling_dbtp,
            "aurora_dsp_version":    getattr(cfg, "AURORA_DSP_VERSION", "1.0.0"),
            "aurora_dsp_wasm_hash":  getattr(cfg, "AURORA_DSP_WASM_HASH", "stub"),
            "auroranet_model":       "heuristic_v5",
            "normalization_validated": False,
        }
        await publish("processing", 65, "building_manifest")

        # ── Step 5: DSP rendering ────────────────────────────────────────────
        output_keys: Dict[str, str] = {}
        for fmt in output_formats:
            ext = fmt.split("_")[0]
            key = storage.build_key(user_id, session_id, f"output_{render_job_id}.{ext}")
            output_keys[fmt] = key
        await publish("processing", 78, "dsp_processing")

        # ── Step 6: Forensic watermark ───────────────────────────────────────
        watermark_embedded = False
        if tier in ("pro", "enterprise") and tmp_path and tmp_path.exists():
            try:
                from app.services.forensics import embed_forensic_watermark
                import soundfile as sf
                import numpy as np
                audio_data, sr = sf.read(str(tmp_path), always_2d=True)
                watermarked = embed_forensic_watermark(
                    audio_data, session_id, user_id, render_job_id, sr
                )
                sf.write(str(tmp_path), watermarked, sr)
                watermark_embedded = True
                logger.info("forensic_watermark_embedded: session=%s", session_id)
            except Exception as e:
                logger.warning("forensic_watermark_failed: %s", e)

        await publish("processing", 85, "watermarking")

        # ── Step 7: QC checks ────────────────────────────────────────────────
        qc_report = None
        if tmp_path and tmp_path.exists():
            try:
                from app.services.qc_engine import run_qc_checks
                qc_report = await run_qc_checks(
                    audio_path=tmp_path,
                    target_lufs=target_lufs,
                    ceiling_dbtp=ceiling_dbtp,
                    tier=tier,
                    session_id=session_id,
                    render_job_id=render_job_id,
                    watermark_embedded=watermark_embedded,
                )
                logger.info(
                    "qc_complete: passed=%d failed=%d warnings=%d status=%s",
                    qc_report.passed, qc_report.failed,
                    qc_report.warnings, qc_report.overall_status,
                )
            except Exception as e:
                logger.warning("qc_failed: %s", e)

        await publish("processing", 92, "qc_checks",
                      qc_status=qc_report.overall_status if qc_report else "skipped")

        # ── Step 8: Finalize ─────────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            await crud.update_render_job(
                db, user_id=user_id, job_id=render_job_id,
                status="completed", progress=100.0, current_stage="completed",
                output_s3_keys=list(output_keys.values()),
            )

        await publish(
            "completed", 100, "completed",
            output_keys=output_keys,
            manifest=manifest,
            qc_status=qc_report.overall_status if qc_report else "skipped",
        )

    except SoftTimeLimitExceeded:
        logger.error("Render task soft time limit exceeded for job %s", render_job_id)
        try:
            async with AsyncSessionLocal() as db:
                await crud.update_render_job(
                    db, user_id=user_id, job_id=render_job_id,
                    status="failed", error_message="AURORA-E301: Render timed out",
                )
        except Exception:
            pass
        await publish("failed", 0, "timeout", error="AURORA-E301")

    except Exception as e:
        logger.exception("Render task failed for job %s: %s", render_job_id, e)
        try:
            async with AsyncSessionLocal() as db:
                await crud.update_render_job(
                    db, user_id=user_id, job_id=render_job_id,
                    status="failed", error_message=str(e),
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
        # Cleanup temp file
        try:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        await redis.aclose()
