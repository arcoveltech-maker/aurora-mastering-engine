-- Aurora DB init: application user only (no superuser)
-- RLS will be enabled per-table via Alembic migrations.
GRANT ALL ON SCHEMA public TO aurora_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO aurora_app;
