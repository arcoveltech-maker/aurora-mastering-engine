"""Session model capturing the Aurora manifest."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import MacroSource, SessionStatus


class Session(IDMixin, TimestampMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
        Index("ix_sessions_user_created_at_desc", "user_id", "created_at"),
        Index("ix_sessions_macros_gin", "macros", postgresql_using="gin"),
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    status: Mapped[SessionStatus] = mapped_column(index=True)

    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(255))

    # Source metadata
    source_hash: Mapped[str] = mapped_column(String(64))
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sample_rate: Mapped[int]
    source_bit_depth: Mapped[int]
    source_channels: Mapped[int]
    source_duration_samples: Mapped[int]
    source_filename: Mapped[str] = mapped_column(String(512))
    source_format: Mapped[str] = mapped_column(String(32))
    source_size_bytes: Mapped[int]

    # Deterministic reproduction
    aurora_dsp_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    aurora_dsp_wasm_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auroranet_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Manifest-backed JSONB
    macros: Mapped[dict[str, float] | None] = mapped_column(JSONB, nullable=True)
    macro_source: Mapped[MacroSource | None] = mapped_column(nullable=True)
    macro_confidence: Mapped[float | None] = mapped_column(nullable=True)
    genre: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    style: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    platform_targets: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reference_track: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    stems: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    master_bus: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    repair: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    analog_model: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    analog_drive: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    codec_optimization: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    spatial: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    loudness: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    qc: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    forensics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    render_settings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    is_collaborative: Mapped[bool] = mapped_column(default=False)
    invited_user_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    last_rendered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["app.models.user.User"] = relationship(
        back_populates="sessions",
    )

