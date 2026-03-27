"""Session-related schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import SessionStatus


class SessionBase(BaseModel):
    title: str = Field(..., max_length=255)

    model_config = {"from_attributes": True}


class SessionCreate(SessionBase):
    source_file: str | None = None
    macros: dict[str, float] | None = None


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    status: SessionStatus | None = None
    macros: dict[str, float] | None = None


class SessionResponse(SessionBase):
    id: str
    session_id: str
    version_id: str | None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime


class SessionListItem(BaseModel):
    id: str
    session_id: str
    title: str
    status: SessionStatus
    created_at: datetime

    model_config = {"from_attributes": True}

