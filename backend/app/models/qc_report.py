"""QCReport model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class QCReport(IDMixin, TimestampMixin, Base):
    __tablename__ = "qc_reports"

    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(String(32))
    audio_hash: Mapped[str] = mapped_column(String(64))
    checks: Mapped[dict] = mapped_column(JSONB)
    summary: Mapped[dict] = mapped_column(JSONB)
    sail_mode: Mapped[str] = mapped_column(String(32))
    engineer_signoff: Mapped[str | None] = mapped_column(String(128), nullable=True)
    compliance_cert_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)

