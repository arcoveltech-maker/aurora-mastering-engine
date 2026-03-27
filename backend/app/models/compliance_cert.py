"""ComplianceCertificate model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class ComplianceCertificate(IDMixin, TimestampMixin, Base):
    __tablename__ = "compliance_certificates"

    cert_id: Mapped[str] = mapped_column(String(64), unique=True)
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    cert_schema_version: Mapped[str] = mapped_column(String(16))
    audio_hash: Mapped[str] = mapped_column(String(64))
    audio_fingerprint: Mapped[str] = mapped_column(String(64))
    audio_duration: Mapped[float]
    audio_sample_rate: Mapped[int]
    audio_bit_depth: Mapped[int]
    audio_channels: Mapped[int]
    standards_compliance: Mapped[dict] = mapped_column(JSONB)
    qc_results: Mapped[dict] = mapped_column(JSONB)
    processing_summary: Mapped[dict] = mapped_column(JSONB)
    signature_algorithm: Mapped[str] = mapped_column(String(64))
    public_key_id: Mapped[str] = mapped_column(String(64))
    signature: Mapped[str] = mapped_column(String(512))

