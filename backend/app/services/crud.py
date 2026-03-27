"""CRUD services enforcing user_id scoping."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AudioFile,
    CollaborationEvent,
    ComplianceCertificate,
    QCReport,
    RenderJob,
    Session,
    SessionStatus,
    SessionVersion,
    Subscription,
    SubscriptionState,
    User,
    WaitlistEntry,
)


# User operations
async def create_user(
    db: AsyncSession,
    *,
    email: str,
    display_name: str,
    password_hash: str,
) -> User:
    user = User(email=email, display_name=display_name, password_hash=password_hash)
    db.add(user)
    await db.flush()
    return user


async def get_user_by_id(db: AsyncSession, *, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, *, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_google_id(db: AsyncSession, *, google_oauth_id: str) -> User | None:
    result = await db.execute(select(User).where(User.google_oauth_id == google_oauth_id))
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    *,
    user_id: str,
    display_name: str | None = None,
    timezone: str | None = None,
) -> User | None:
    user = await get_user_by_id(db, user_id=user_id)
    if not user:
        return None
    if display_name is not None:
        user.display_name = display_name
    if timezone is not None:
        user.timezone = timezone
    await db.flush()
    return user


async def delete_user(db: AsyncSession, *, user_id: str) -> int:
    user = await get_user_by_id(db, user_id=user_id)
    if not user:
        return 0
    await db.delete(user)
    await db.flush()
    return 1


# Subscription operations
async def get_subscription(db: AsyncSession, *, user_id: str) -> Subscription | None:
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    return result.scalar_one_or_none()


async def create_subscription(db: AsyncSession, *, user_id: str) -> Subscription:
    sub = Subscription(user_id=user_id)
    db.add(sub)
    await db.flush()
    return sub


async def update_subscription_state(
    db: AsyncSession,
    *,
    user_id: str,
    new_state: SubscriptionState,
) -> Subscription | None:
    sub = await get_subscription(db, user_id=user_id)
    if not sub:
        return None
    sub.state = new_state
    await db.flush()
    return sub


async def increment_track_usage(db: AsyncSession, *, user_id: str, delta: int = 1) -> None:
    sub = await get_subscription(db, user_id=user_id)
    if not sub:
        return
    sub.tracks_used_this_period += delta
    await db.flush()


async def reset_track_usage(db: AsyncSession, *, user_id: str) -> None:
    sub = await get_subscription(db, user_id=user_id)
    if not sub:
        return
    sub.tracks_used_this_period = 0
    await db.flush()


async def update_storage_usage(db: AsyncSession, *, user_id: str, delta_bytes: int) -> None:
    sub = await get_subscription(db, user_id=user_id)
    if not sub:
        return
    sub.storage_used_bytes = int(
        await db.scalar(
            select(func.greatest(sub.storage_used_bytes + delta_bytes, 0))
        )
    )
    await db.flush()


# Session operations
async def create_session(
    db: AsyncSession,
    *,
    user_id: str,
    status: SessionStatus,
    version_id: str | None,
    title: str,
    source_hash: str,
    source_sample_rate: int,
    source_bit_depth: int,
    source_channels: int,
    source_duration_samples: int,
    source_filename: str,
    source_format: str,
    source_size_bytes: int,
) -> Session:
    session = Session(
        user_id=user_id,
        status=status,
        version_id=version_id,
        title=title,
        source_hash=source_hash,
        source_sample_rate=source_sample_rate,
        source_bit_depth=source_bit_depth,
        source_channels=source_channels,
        source_duration_samples=source_duration_samples,
        source_filename=source_filename,
        source_format=source_format,
        source_size_bytes=source_size_bytes,
    )
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, *, user_id: str, session_id: str) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_sessions(db: AsyncSession, *, user_id: str, limit: int = 50) -> Sequence[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def update_session(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    **fields,
) -> Session | None:
    session = await get_session(db, user_id=user_id, session_id=session_id)
    if not session:
        return None
    for key, value in fields.items():
        if hasattr(session, key) and value is not None:
            setattr(session, key, value)
    await db.flush()
    return session


async def delete_session(db: AsyncSession, *, user_id: str, session_id: str) -> int:
    session = await get_session(db, user_id=user_id, session_id=session_id)
    if not session:
        return 0
    await db.delete(session)
    await db.flush()
    return 1


# Session version operations
async def create_version(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    version_number: int,
    is_snapshot: bool,
    diff_data: dict | None,
    full_manifest: dict | None,
    parent_version_id: str | None,
    branch_name: str,
    created_by: str,
) -> SessionVersion:
    version = SessionVersion(
        user_id=user_id,
        session_id=session_id,
        version_number=version_number,
        is_snapshot=is_snapshot,
        diff_data=diff_data,
        full_manifest=full_manifest,
        parent_version_id=parent_version_id,
        branch_name=branch_name,
        created_by=created_by,
    )
    db.add(version)
    await db.flush()
    return version


async def get_version(
    db: AsyncSession,
    *,
    user_id: str,
    version_id: str,
) -> SessionVersion | None:
    result = await db.execute(
        select(SessionVersion).where(SessionVersion.id == version_id, SessionVersion.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_versions(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
) -> Sequence[SessionVersion]:
    result = await db.execute(
        select(SessionVersion)
        .where(SessionVersion.user_id == user_id, SessionVersion.session_id == session_id)
        .order_by(SessionVersion.created_at.desc())
    )
    return result.scalars().all()


async def restore_version(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    version_id: str,
) -> Session | None:
    version = await get_version(db, user_id=user_id, version_id=version_id)
    if not version or str(version.session_id) != session_id:
        return None
    session = await get_session(db, user_id=user_id, session_id=session_id)
    if not session:
        return None
    if version.full_manifest:
        session.render_settings = version.full_manifest
    await db.flush()
    return session


# Audio file operations
async def create_audio_file(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str | None,
    **fields,
) -> AudioFile:
    audio = AudioFile(
        user_id=user_id,
        session_id=session_id,
        **fields,
    )
    db.add(audio)
    await db.flush()
    return audio


async def get_audio_file(
    db: AsyncSession,
    *,
    user_id: str,
    audio_file_id: str,
) -> AudioFile | None:
    result = await db.execute(
        select(AudioFile).where(AudioFile.id == audio_file_id, AudioFile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_audio_files(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
) -> Sequence[AudioFile]:
    result = await db.execute(
        select(AudioFile).where(AudioFile.user_id == user_id, AudioFile.session_id == session_id)
    )
    return result.scalars().all()


async def delete_audio_file(
    db: AsyncSession,
    *,
    user_id: str,
    audio_file_id: str,
) -> int:
    audio = await get_audio_file(db, user_id=user_id, audio_file_id=audio_file_id)
    if not audio:
        return 0
    await db.delete(audio)
    await db.flush()
    return 1


# Render job operations
async def create_render_job(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    **fields,
) -> RenderJob:
    job = RenderJob(user_id=user_id, session_id=session_id, **fields)
    job.set_priority_from_tier()
    db.add(job)
    await db.flush()
    return job


async def get_render_job(
    db: AsyncSession,
    *,
    user_id: str,
    job_id: str,
) -> RenderJob | None:
    result = await db.execute(
        select(RenderJob).where(RenderJob.id == job_id, RenderJob.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_render_job(
    db: AsyncSession,
    *,
    user_id: str,
    job_id: str,
    **fields,
) -> RenderJob | None:
    job = await get_render_job(db, user_id=user_id, job_id=job_id)
    if not job:
        return None
    for key, value in fields.items():
        if hasattr(job, key) and value is not None:
            setattr(job, key, value)
    await db.flush()
    return job


async def get_active_render_count(db: AsyncSession, *, user_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(RenderJob)
        .where(RenderJob.user_id == user_id)
    )
    return int(result.scalar_one() or 0)


async def list_render_jobs(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str | None = None,
) -> Sequence[RenderJob]:
    stmt = select(RenderJob).where(RenderJob.user_id == user_id)
    if session_id is not None:
        stmt = stmt.where(RenderJob.session_id == session_id)
    result = await db.execute(stmt)
    return result.scalars().all()


# Certificate operations
async def create_certificate(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    **fields,
) -> ComplianceCertificate:
    cert = ComplianceCertificate(user_id=user_id, session_id=session_id, **fields)
    db.add(cert)
    await db.flush()
    return cert


async def get_certificate(
    db: AsyncSession,
    *,
    user_id: str,
    cert_id: str,
) -> ComplianceCertificate | None:
    result = await db.execute(
        select(ComplianceCertificate).where(
            ComplianceCertificate.cert_id == cert_id,
            ComplianceCertificate.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


# QC report operations
async def create_qc_report(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    **fields,
) -> QCReport:
    report = QCReport(user_id=user_id, session_id=session_id, **fields)
    db.add(report)
    await db.flush()
    return report


async def get_qc_report(
    db: AsyncSession,
    *,
    user_id: str,
    report_id: str,
) -> QCReport | None:
    result = await db.execute(
        select(QCReport).where(QCReport.id == report_id, QCReport.user_id == user_id)
    )
    return result.scalar_one_or_none()


# Waitlist operations (no user_id)
async def add_to_waitlist(
    db: AsyncSession,
    *,
    email: str,
    referral_code: str | None,
    referred_by: str | None,
) -> WaitlistEntry:
    entry = WaitlistEntry(
        email=email,
        referral_code=referral_code,
        referred_by=referred_by,
        position=0,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_waitlist_position(db: AsyncSession, *, email: str) -> int | None:
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
    entry = result.scalar_one_or_none()
    return entry.position if entry else None


async def invite_from_waitlist(db: AsyncSession, *, email: str) -> WaitlistEntry | None:
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
    entry = result.scalar_one_or_none()
    if not entry:
        return None
    entry.invited_at = func.now()
    await db.flush()
    return entry


