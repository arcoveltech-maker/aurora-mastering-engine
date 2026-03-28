"""Initial schema with RLS policies."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_schema_rls"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("google_oauth_id", sa.String(length=255), nullable=True),
        sa.Column("apple_oauth_id", sa.String(length=255), nullable=True),
        sa.Column("profile_picture_url", sa.String(length=1024), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_2fa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("totp_secret", sa.String(length=255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_oauth_id", name="uq_users_google_oauth_id"),
        sa.UniqueConstraint("apple_oauth_id", name="uq_users_apple_oauth_id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_google_oauth_id", "users", ["google_oauth_id"], unique=False)
    op.create_index("ix_users_apple_oauth_id", "users", ["apple_oauth_id"], unique=False)

    # Subscriptions
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="waitlist"),
        sa.Column("tier", sa.String(length=32), nullable=False, server_default="trial"),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("billing_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tracks_used_this_period", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_used_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("past_due_since", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_state", "subscriptions", ["state"], unique=False)
    op.create_index("ix_subscriptions_tier", "subscriptions", ["tier"], unique=False)
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"], unique=True)
    op.create_index("ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"], unique=True)
    op.create_index("ix_subscriptions_stripe_price_id", "subscriptions", ["stripe_price_id"], unique=False)

    # Sessions
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("source_sample_rate", sa.Integer(), nullable=False),
        sa.Column("source_bit_depth", sa.Integer(), nullable=False),
        sa.Column("source_channels", sa.Integer(), nullable=False),
        sa.Column("source_duration_samples", sa.BigInteger(), nullable=False),
        sa.Column("source_filename", sa.String(length=512), nullable=False),
        sa.Column("source_format", sa.String(length=32), nullable=False),
        sa.Column("source_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("aurora_dsp_version", sa.String(length=32), nullable=True),
        sa.Column("aurora_dsp_wasm_hash", sa.String(length=64), nullable=True),
        sa.Column("auroranet_model", sa.String(length=128), nullable=True),
        sa.Column("macros", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("macro_source", sa.String(length=32), nullable=True),
        sa.Column("macro_confidence", sa.Float(), nullable=True),
        sa.Column("genre", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("style", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("platform_targets", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reference_track", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("stems", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("master_bus", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("repair", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("analog_model", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("analog_drive", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("codec_optimization", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("spatial", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("loudness", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("qc", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("forensics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("render_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_collaborative", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("invited_user_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_rendered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sessions_user_status", "sessions", ["user_id", "status"], unique=False)
    op.create_index("ix_sessions_user_created_at", "sessions", ["user_id", "created_at"], unique=False)
    op.create_index("ix_sessions_macros_gin", "sessions", ["macros"], postgresql_using="gin")

    # Audio files
    op.create_table(
        "audio_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stem_type", sa.String(length=64), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("sample_rate_hz", sa.Integer(), nullable=True),
        sa.Column("channels", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("is_lossy", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audio_files_user_id", "audio_files", ["user_id"], unique=False)
    op.create_index("ix_audio_files_session_id", "audio_files", ["session_id"], unique=False)

    # Session versions
    op.create_table(
        "session_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("manifest_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_session_versions_user_id", "session_versions", ["user_id"], unique=False)
    op.create_index(
        "ix_session_versions_session_id_created_at",
        "session_versions",
        ["session_id", "created_at"],
        unique=False,
    )

    # Render jobs
    op.create_table(
        "render_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("engine_version", sa.String(length=32), nullable=True),
        sa.Column("target_lufs", sa.Float(), nullable=True),
        sa.Column("ceiling_dbtp", sa.Float(), nullable=True),
        sa.Column("preset_name", sa.String(length=128), nullable=True),
        sa.Column("job_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("job_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("output_s3_key", sa.String(length=1024), nullable=True),
        sa.Column("estimated_cost_dollars", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_render_jobs_user_id_status", "render_jobs", ["user_id", "status"], unique=False)
    op.create_index("ix_render_jobs_session_id", "render_jobs", ["session_id"], unique=False)

    # Compliance certificates
    op.create_table(
        "compliance_certificates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("render_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("certificate_number", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["render_job_id"], ["render_jobs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("certificate_number", name="uq_compliance_certificate_number"),
    )
    op.create_index("ix_compliance_certificates_user_id", "compliance_certificates", ["user_id"], unique=False)

    # QC reports
    op.create_table(
        "qc_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pass_"),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_qc_reports_user_id", "qc_reports", ["user_id"], unique=False)
    op.create_index("ix_qc_reports_session_id", "qc_reports", ["session_id"], unique=False)

    # Collaboration events
    op.create_table(
        "collaboration_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_collab_events_session_id_created_at",
        "collaboration_events",
        ["session_id", "created_at"],
        unique=False,
    )

    # Waitlist
    op.create_table(
        "waitlist_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invitation_token", sa.String(length=128), nullable=True),
        sa.UniqueConstraint("email", name="uq_waitlist_email"),
    )

    # Enable RLS and policies
    for table in [
        "sessions",
        "audio_files",
        "render_jobs",
        "session_versions",
        "qc_reports",
        "compliance_certificates",
        "collaboration_events",
        "subscriptions",
    ]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table}
            ON {table}
            USING (user_id = current_setting('app.current_user_id')::uuid)
            """
        )


def downgrade() -> None:
    for table in [
        "sessions",
        "audio_files",
        "render_jobs",
        "session_versions",
        "qc_reports",
        "compliance_certificates",
        "collaboration_events",
        "subscriptions",
    ]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("waitlist_entries")
    op.drop_index("ix_collab_events_session_id_created_at", table_name="collaboration_events")
    op.drop_table("collaboration_events")
    op.drop_index("ix_qc_reports_session_id", table_name="qc_reports")
    op.drop_index("ix_qc_reports_user_id", table_name="qc_reports")
    op.drop_table("qc_reports")
    op.drop_index("ix_compliance_certificates_user_id", table_name="compliance_certificates")
    op.drop_table("compliance_certificates")
    op.drop_index("ix_render_jobs_session_id", table_name="render_jobs")
    op.drop_index("ix_render_jobs_user_id_status", table_name="render_jobs")
    op.drop_table("render_jobs")
    op.drop_index("ix_session_versions_session_id_created_at", table_name="session_versions")
    op.drop_index("ix_session_versions_user_id", table_name="session_versions")
    op.drop_table("session_versions")
    op.drop_index("ix_audio_files_session_id", table_name="audio_files")
    op.drop_index("ix_audio_files_user_id", table_name="audio_files")
    op.drop_table("audio_files")
    op.drop_index("ix_sessions_user_created_at", table_name="sessions")
    op.drop_index("ix_sessions_user_status", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_subscriptions_tier", table_name="subscriptions")
    op.drop_index("ix_subscriptions_state", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

