"""
Upload routes: presign + confirm.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.errors import AuroraHTTPException
from app.core.feature_gates import require_storage_quota, require_track_quota
from app.models.user import User
from app.services import crud, storage

router = APIRouter(prefix="/upload", tags=["upload"])

SUPPORTED_FORMATS = {"wav", "flac", "aiff", "aif", "mp3", "aac", "ogg", "m4a"}
LOSSY_FORMATS = {"mp3", "aac", "ogg", "m4a"}
MAX_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB


class PresignRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    session_id: str


class ConfirmRequest(BaseModel):
    key: str
    session_id: str
    duration_seconds: float
    sample_rate: int
    channels: int


@router.post("/presign")
async def presign(
    body: PresignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(body.filename)[1].lstrip(".").lower()
    if ext not in SUPPORTED_FORMATS:
        raise AuroraHTTPException("AURORA-E008", f"Format '{ext}' is not supported")

    if body.size_bytes > MAX_SIZE_BYTES:
        raise AuroraHTTPException("AURORA-E009")

    sub = await crud.get_subscription(db, user_id=str(current_user.id))
    tier = sub.tier.value if sub and hasattr(sub.tier, "value") else (sub.tier if sub else "trial")
    state = sub.state.value if sub and hasattr(sub.state, "value") else (sub.state if sub else "active")

    # Use subscription's track_count if available; fallback to 0
    tracks_used = getattr(sub, "track_count", 0) or 0
    storage_used = getattr(sub, "storage_used_bytes", 0) or 0

    require_storage_quota(storage_used, body.size_bytes, tier, state)
    require_track_quota(tracks_used, tier, state)

    key = storage.build_key(str(current_user.id), body.session_id, body.filename)
    url = await storage.generate_presigned_upload_url(key, body.content_type)

    response_data = {"upload_url": url, "key": key}
    if ext in LOSSY_FORMATS:
        response_data["warning"] = {
            "code": "AURORA-E007",
            "message": "Lossy format detected — quality may be reduced. Consider using WAV or FLAC.",
        }
    return response_data


@router.post("/confirm")
async def confirm(
    body: ConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    storage.validate_key_ownership(body.key, str(current_user.id))

    if not await storage.object_exists(body.key):
        raise AuroraHTTPException("AURORA-E603", "File not found in storage")

    if body.duration_seconds < 2.0:
        raise AuroraHTTPException("AURORA-E010")

    if body.sample_rate not in (44100, 48000, 88200, 96000, 176400, 192000):
        raise AuroraHTTPException("AURORA-E011", f"Unsupported sample rate: {body.sample_rate}")

    if body.channels not in (1, 2):
        raise AuroraHTTPException("AURORA-E012", f"Unsupported channel count: {body.channels}")

    size_bytes = await storage.get_object_size(body.key)

    audio_file = await crud.create_audio_file(
        db,
        user_id=str(current_user.id),
        session_id=body.session_id,
        source_filename=os.path.basename(body.key),
        source_format=os.path.splitext(body.key)[1].lstrip(".").lower(),
        source_size_bytes=size_bytes,
        source_duration_samples=int(body.duration_seconds * body.sample_rate),
        source_sample_rate=body.sample_rate,
        source_channels=body.channels,
        source_bit_depth=24,
        source_hash="pending",
        source_fingerprint=None,
    )
    return {"id": str(audio_file.id), "key": body.key, "size_bytes": size_bytes}
