"""
Session management routes.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.errors import AuroraHTTPException
from app.models.user import User
from app.services import crud

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: str
    genre: Optional[dict] = None
    platform_targets: Optional[dict] = None
    # Minimal required fields for the model
    source_hash: str = "pending"
    source_sample_rate: int = 44100
    source_bit_depth: int = 24
    source_channels: int = 2
    source_duration_samples: int = 0
    source_filename: str = "pending"
    source_format: str = "wav"
    source_size_bytes: int = 0


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    genre: Optional[dict] = None
    platform_targets: Optional[dict] = None


@router.post("", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.session import Session
    from app.models.enums import SessionStatus
    session = Session(
        user_id=current_user.id,
        status=SessionStatus.ACTIVE,
        title=body.title,
        genre=body.genre,
        platform_targets=body.platform_targets,
        source_hash=body.source_hash,
        source_sample_rate=body.source_sample_rate,
        source_bit_depth=body.source_bit_depth,
        source_channels=body.source_channels,
        source_duration_samples=body.source_duration_samples,
        source_filename=body.source_filename,
        source_format=body.source_format,
        source_size_bytes=body.source_size_bytes,
    )
    db.add(session)
    await db.flush()
    return {
        "id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat(),
    }


@router.get("")
async def list_sessions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.session import Session
    from app.models.enums import SessionStatus
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id, Session.status != SessionStatus.DELETED)
        .order_by(Session.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    sessions = result.scalars().all()
    return {
        "items": [
            {"id": str(s.id), "title": s.title, "created_at": s.created_at.isoformat()}
            for s in sessions
        ]
    }


@router.get("/{session_id}")
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.session import Session
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise AuroraHTTPException("AURORA-E401")
    if str(session.user_id) != str(current_user.id):
        raise AuroraHTTPException("AURORA-E402")
    return {
        "id": str(session.id),
        "title": session.title,
        "genre": session.genre,
        "platform_targets": session.platform_targets,
        "status": session.status.value if hasattr(session.status, "value") else session.status,
        "created_at": session.created_at.isoformat(),
        "macros": session.macros,
    }


@router.patch("/{session_id}")
async def update_session(
    session_id: UUID,
    body: UpdateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.session import Session
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise AuroraHTTPException("AURORA-E401")
    if str(session.user_id) != str(current_user.id):
        raise AuroraHTTPException("AURORA-E402")
    if body.title is not None:
        session.title = body.title
    if body.genre is not None:
        session.genre = body.genre
    if body.platform_targets is not None:
        session.platform_targets = body.platform_targets
    await db.flush()
    return {"id": str(session.id), "title": session.title}


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.session import Session
    from app.models.enums import SessionStatus
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise AuroraHTTPException("AURORA-E401")
    if str(session.user_id) != str(current_user.id):
        raise AuroraHTTPException("AURORA-E402")
    session.status = SessionStatus.DELETED
    await db.flush()


@router.post("/{session_id}/versions", status_code=201)
async def create_version(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, func
    from app.models.session import Session
    from app.models.version import SessionVersion
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise AuroraHTTPException("AURORA-E401")
    if str(session.user_id) != str(current_user.id):
        raise AuroraHTTPException("AURORA-E402")

    # Get next version number
    count_result = await db.execute(
        select(func.count()).select_from(SessionVersion).where(SessionVersion.session_id == session_id)
    )
    next_num = (count_result.scalar_one() or 0) + 1

    version = SessionVersion(
        session_id=session_id,
        user_id=current_user.id,
        version_number=next_num,
        is_snapshot=True,
        branch_name="main",
        created_by=current_user.id,
        full_manifest=session.macros,
    )
    db.add(version)
    await db.flush()
    return {"id": str(version.id), "version_number": version.version_number}


@router.get("/{session_id}/versions")
async def list_versions(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.session import Session
    from app.models.version import SessionVersion
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise AuroraHTTPException("AURORA-E401")
    if str(session.user_id) != str(current_user.id):
        raise AuroraHTTPException("AURORA-E402")
    v_result = await db.execute(
        select(SessionVersion)
        .where(SessionVersion.session_id == session_id)
        .order_by(SessionVersion.version_number)
    )
    versions = v_result.scalars().all()
    return {
        "items": [{"id": str(v.id), "version_number": v.version_number} for v in versions]
    }
