"""RenderJob model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import FLOAT, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import RenderStatus, SubscriptionTier


class RenderJob(IDMixin, TimestampMixin, Base):
    __tablename__ = "render_jobs"
    __table_args__ = (
        Index("ix_render_jobs_user_status", "user_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    celery_task_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[RenderStatus]
    tier: Mapped[SubscriptionTier]
    priority: Mapped[int]
    progress: Mapped[float] = mapped_column(FLOAT, default=0.0)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_s3_keys: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    render_duration_seconds: Mapped[float | None] = mapped_column(FLOAT, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def set_priority_from_tier(self) -> None:
        if self.tier == SubscriptionTier.ENTERPRISE:
            self.priority = 10
        elif self.tier == SubscriptionTier.PRO:
            self.priority = 5
        elif self.tier == SubscriptionTier.ARTIST:
            self.priority = 1
        else:
            self.priority = 0

