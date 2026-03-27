"""SessionVersion model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class SessionVersion(IDMixin, TimestampMixin, Base):
    __tablename__ = "session_versions"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "version_number",
            "branch_name",
            name="uq_session_version_branch",
        ),
    )

    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int]
    is_snapshot: Mapped[bool]
    diff_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    full_manifest: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parent_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    branch_name: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(64))

