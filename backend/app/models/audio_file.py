"""AudioFile model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import BIGINT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import StemType


class AudioFile(IDMixin, TimestampMixin, Base):
    __tablename__ = "audio_files"
    __table_args__ = (
        Index("ix_audio_files_user_session", "user_id", "session_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    file_type: Mapped[str] = mapped_column(String(32))
    s3_key: Mapped[str] = mapped_column(String(1024), unique=True)
    filename: Mapped[str] = mapped_column(String(512))
    format: Mapped[str] = mapped_column(String(32))
    sample_rate: Mapped[int]
    bit_depth: Mapped[int]
    channels: Mapped[int]
    duration_seconds: Mapped[float]
    size_bytes: Mapped[int] = mapped_column(BIGINT)
    sha256_hash: Mapped[str] = mapped_column(String(64))
    chromaprint_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aurora_spectral_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stem_type: Mapped[StemType | None] = mapped_column(nullable=True)

