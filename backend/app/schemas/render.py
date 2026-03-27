"""Render job schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RenderStatus


class RenderJobCreate(BaseModel):
    session_id: str
    target_lufs: float | None = None
    ceiling_dbtp: float | None = None
    preset_name: str | None = None


class RenderJobResponse(BaseModel):
    id: str
    session_id: str
    status: RenderStatus
    job_started_at: datetime | None
    job_finished_at: datetime | None
    output_s3_key: str | None

    model_config = {"from_attributes": True}

