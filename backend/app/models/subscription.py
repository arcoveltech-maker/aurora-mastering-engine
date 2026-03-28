"""Subscription model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import BIGINT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import SubscriptionState, SubscriptionTier


class Subscription(IDMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    state: Mapped[SubscriptionState] = mapped_column(
        default=SubscriptionState.WAITLIST,
        index=True,
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        default=SubscriptionTier.TRIAL,
        index=True,
    )

    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    billing_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    billing_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    trial_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    trial_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    tracks_used_this_period: Mapped[int] = mapped_column(Integer, default=0)
    storage_used_bytes: Mapped[int] = mapped_column(BIGINT, default=0)

    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    past_due_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["app.models.user.User"] = relationship(
        back_populates="subscription",
    )

    @property
    def tracks_limit(self) -> Optional[int]:
        if self.state == SubscriptionState.TRIAL:
            return 3
        if self.state == SubscriptionState.ACTIVE_ARTIST:
            return 100
        if self.state == SubscriptionState.ACTIVE_PRO:
            return 500
        if self.state == SubscriptionState.ACTIVE_ENTERPRISE:
            return None
        return 0

    @property
    def storage_limit_bytes(self) -> Optional[int]:
        if self.tier == SubscriptionTier.TRIAL:
            return 1 * 1024 * 1024 * 1024  # 1 GB for trial users
        if self.tier == SubscriptionTier.ARTIST:
            return 5 * 1024 * 1024 * 1024
        if self.tier == SubscriptionTier.PRO:
            return 50 * 1024 * 1024 * 1024
        if self.tier == SubscriptionTier.ENTERPRISE:
            return None
        return 0

