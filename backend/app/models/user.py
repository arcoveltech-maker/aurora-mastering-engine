"""User model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:  # pragma: no cover
    from app.models.session import Session  # noqa: F401
    from app.models.subscription import Subscription  # noqa: F401


class User(IDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("google_oauth_id", name="uq_users_google_oauth_id"),
        UniqueConstraint("apple_oauth_id", name="uq_users_apple_oauth_id"),
        Index("ix_users_email", "email"),
        Index("ix_users_google_oauth_id", "google_oauth_id"),
        Index("ix_users_apple_oauth_id", "apple_oauth_id"),
    )

    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    google_oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apple_oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    subscription: Mapped["Subscription"] = relationship(
        back_populates="user",
        uselist=False,
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

