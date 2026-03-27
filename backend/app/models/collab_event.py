"""CollaborationEvent model."""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.models.base import Base, IDMixin


class CollaborationEvent(IDMixin, Base):
    __tablename__ = "collaboration_events"
    __table_args__ = (
        Index("ix_collab_session_timestamp", "session_id", "timestamp"),
    )

    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    timestamp: Mapped["datetime"] = mapped_column(DateTime(timezone=True))

