"""WaitlistEntry model."""

from __future__ import annotations

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.models.base import Base, IDMixin, TimestampMixin


class WaitlistEntry(IDMixin, TimestampMixin, Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        UniqueConstraint("email", name="uq_waitlist_email"),
    )

    email: Mapped[str] = mapped_column(String(320))
    referral_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    referred_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    invited_at: Mapped["datetime | None"]
    converted_user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

