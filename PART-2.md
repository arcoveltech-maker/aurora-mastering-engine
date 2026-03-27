# Part 2: Database, RLS, Auth, Billing, Feature Gates

**Scope:** Phase 2A, 2B, 3A, 3B, 3C.  
**Do not proceed to Part 3 until instructed.**

Apply **BLUEPRINT-INDEX.md** immutable notes (K-weighting, NORMALIZATION_VALIDATED, multi-tenant isolation).

---

## Phase 2A — Database schema and models

**TASK 2A-1 — Enums**  
`backend/app/models/enums.py`: SubscriptionState (waitlist, trial, trial_expired, active_artist, active_pro, active_enterprise, past_due, canceled, expired, suspended), SubscriptionTier, RenderStatus, SessionStatus, UserRole, MacroSource, LimiterMode, QCCheckStatus (pass_, fail, warning, remediated, skipped), StemType (12 values: lead_vocals, backing_vocals, bass, kick, snare, hihats, cymbals, room, guitar, piano, synths_pads, fx_atmosphere).

**TASK 2A-2 — Base**  
`backend/app/models/base.py`: DeclarativeBase, TimestampMixin (created_at, updated_at), UUID PK with server_default gen_random_uuid().

**TASK 2A-3 — User**  
`backend/app/models/user.py`: id, email (unique), display_name, password_hash, google_oauth_id, apple_oauth_id, profile_picture_url, timezone, role, is_email_verified, is_2fa_enabled, totp_secret, last_login_at, timestamps. Relations: subscription (one-to-one), sessions (one-to-many).

**TASK 2A-4 — Subscription**  
`backend/app/models/subscription.py`: user_id (FK, unique), state, tier, stripe_customer_id, stripe_subscription_id, stripe_price_id, billing_period_start/end, trial_start/end, tracks_used_this_period, storage_used_bytes, canceled_at, past_due_since. Properties: tracks_limit (3 trial, 100 artist, 500 pro, None enterprise), storage_limit_bytes (5 GB artist, 50 GB pro, None enterprise).

**TASK 2A-5 — Session**  
`backend/app/models/session.py`: Full v4.0 Section 22.1 manifest as columns + JSONB for macros, genre, stems, master_bus, repair, loudness, qc, forensics, render_settings; source_* fields; aurora_dsp_version, aurora_dsp_wasm_hash, auroranet_model; is_collaborative, invited_user_ids. GIN on macros; composite indexes (user_id, status), (user_id, created_at DESC).

**TASK 2A-6 — AudioFile, Version, RenderJob, ComplianceCertificate, QCReport, CollabEvent, WaitlistEntry**  
Implement per blueprint (Phase 2A task list). AudioFile: s3_key pattern `users/{user_id}/{session_id}/...`. All user-scoped tables with user_id and indexes.

**TASK 2A-7 — Database core**  
`backend/app/core/database.py`: async engine (asyncpg), async_sessionmaker, get_db dependency that sets `app.current_user_id` for RLS and resets in finally; pool settings (pool_size=20, max_overflow=10, pool_recycle=1800, pool_pre_ping=True).

---

## Phase 2B — CRUD, RLS, tests

**TASK 2B-1 — CRUD**  
`backend/app/services/crud.py`: Every function that touches user data takes `user_id` and filters by it. Implement: create/get/update/delete user; get/create/update subscription, increment_track_usage, update_storage_usage; create/get/list/update/delete session; version create/get/list/restore; audio_file create/get/list/delete; render_job create/get/update, get_active_render_count, list; compliance_cert create/get; qc_report create/get; waitlist add/get_position/invite.

**TASK 2B-2 — Pydantic schemas**  
`backend/app/schemas/`: user (UserCreate, UserResponse, UserUpdate), subscription (SubscriptionResponse, SubscriptionStateTransition), session (SessionCreate, SessionResponse, SessionListItem, SessionUpdate), auth (LoginRequest, TokenResponse, GoogleOAuthRequest, RefreshTokenRequest), render (RenderJobCreate, RenderJobResponse), common (AuroraError, PaginatedResponse, HealthResponse). Pydantic v2, from_attributes=True.

**TASK 2B-3 — Alembic**  
Configure `alembic/env.py` with async engine and Base.metadata. Initial migration: create tables then raw SQL to enable RLS and create policy `tenant_isolation_{table}` USING (user_id = current_setting('app.current_user_id')::uuid) for sessions, audio_files, render_jobs, session_versions, qc_reports, compliance_certificates, collaboration_events, subscriptions. Downgrade: drop policy, disable RLS.

**TASK 2B-4 — Isolation tests**  
`backend/tests/test_isolation.py`: test_user_cannot_read_other_sessions, cannot_list_other_sessions, cannot_update_other_session, cannot_delete_other_session; same for audio_files, render_jobs, certificates; test_rls_prevents_direct_query_leakage; test_track_usage_isolation, storage_usage_isolation, subscription_state_isolation.

**TASK 2B-5 — Subscription tests**  
`backend/tests/test_subscription.py`: valid state transitions (waitlist→trial, trial→active_*, past_due→active_*, etc.); invalid transitions raise InvalidStateTransition.

Run: `alembic upgrade head`; `pytest tests/test_isolation.py tests/test_subscription.py -v --tb=short`. Report results.

---

## Phase 3A — Authentication

**TASK 3A-1 — Security core**  
`backend/app/core/security.py`: RS256 key load/generate; create_access_token (1h, claims sub, role, tier, iat, exp, jti), create_refresh_token (7d, type=refresh, device_fp); verify_access_token → TokenPayload; Redis store/verify/revoke refresh tokens; bcrypt hash_password, verify_password.

**TASK 3A-2 — Dependencies**  
`backend/app/api/dependencies.py`: get_current_user (cookie aurora_access_token or Bearer, verify JWT, load user); get_current_user_id; require_role(roles); verify_tier_access(required_tier); verify_email_verified.

**TASK 3A-3 — Auth routes**  
`backend/app/api/routes/auth.py`: POST register (email, password 12+ chars, create user+subscription waitlist, send verification); POST login (set httpOnly, Secure, SameSite=Strict cookies, store refresh in Redis); POST refresh (rotate refresh, new cookies); POST logout, logout-all; POST google (verify ID token, link or create user); POST verify-email/{token}; POST change-password (revoke all refresh); GET me.

**TASK 3A-4 — Middleware**  
`backend/app/api/middleware.py`: CORS (allow_credentials, origins from config), SecurityHeadersMiddleware (all .cursorrules headers), RequestIDMiddleware, RateLimitMiddleware (Redis sliding window; 30/min analyze, 60/min predict, 5/min render, 20/min chat, 10/min stems, 120/min other; unauthenticated 10/min by IP).

**TASK 3A-5 — Auth tests**  
`backend/tests/test_auth.py`: register success/short password/duplicate email; login success/unverified/wrong password; refresh rotation; logout revokes token; change password revokes all sessions; suspended user cannot login.

Run: `pytest tests/test_auth.py -v`. Report.

---

## Phase 3B — Stripe billing

**TASK 3B-1 — Billing service**  
`backend/app/services/billing.py`: get_or_create_stripe_customer; create_checkout_session (subscription, trial if waitlist); create_portal_session; cancel_subscription (at period end). Use env Stripe price IDs.

**TASK 3B-2 — Webhook**  
`backend/app/api/routes/webhooks.py`: POST /api/webhooks/stripe — verify signature (STRIPE_WEBHOOK_SECRET), then handle: customer.subscription.created (set state/tier, billing period), customer.subscription.updated (plan change, past_due), customer.subscription.deleted (canceled), invoice.payment_succeeded (reset usage, clear past_due), invoice.payment_failed (set past_due), customer.subscription.trial_will_end. Idempotency via Redis (event.id, 24h TTL). Return 200 after process; 500 on failure for retry.

**TASK 3B-3 — Billing routes**  
`backend/app/api/routes/billing.py`: POST checkout, POST portal, GET subscription, GET invoices, GET usage.

**TASK 3B-4 — Celery billing tasks**  
`backend/app/tasks/billing_tasks.py`: check_expired_subscriptions (canceled → expired when period_end passed), check_trial_expirations (trial → trial_expired). Beat schedule hourly.

**TASK 3B-5 — Billing tests**  
`backend/tests/test_billing.py`: Mock Stripe. webhook signature invalid → 400; subscription.created → active_artist/active_pro; payment_failed → past_due; payment_succeeded → clear past_due, reset usage; subscription.deleted → canceled; idempotency; upgrade artist→pro.

Run: `pytest tests/test_billing.py -v`. Report.

---

## Phase 3C — Feature gates, S3, errors

**TASK 3C-1 — Feature gates**  
`backend/app/core/feature_gates.py`: TIER_FEATURES dict (trial, artist, pro, enterprise) with tracks_per_period, storage_bytes, export_formats, qc_checks, reference_matching, spatial_rendering, ddp_export, ddex_distribution, collaboration, collaboration_max_users, etc. require_feature(feature_name), require_track_quota(), require_storage_quota(file_size_bytes) as FastAPI dependencies; return AURORA-B001/B002/B003/B005 as appropriate.

**TASK 3C-2 — Errors**  
`backend/app/core/errors.py`: AuroraHTTPException (error_code, message, severity, details); full error code registry (AURORA-E001–E902, AURORA-B001–B005) with default message, severity, http_status; global exception handlers (AuroraHTTPException → JSON, unhandled → 500 AURORA-E300, log, metric).

**TASK 3C-3 — Storage**  
`backend/app/services/storage.py`: StorageService; _build_key(user_id, session_id, filename) → users/{user_id}/{session_id}/safe_name; _validate_key_ownership(key, user_id) → 403 AURORA-E602 if prefix mismatch; upload_file, generate_presigned_download_url (after ownership check), generate_presigned_upload_url, delete_file, delete_user_data, get_user_storage_usage.

**TASK 3C-4 — Upload routes**  
`backend/app/api/routes/upload.py`: POST presign (validate format, size ≤500MB, storage/track quota, lossy warning AURORA-E007); POST confirm (validate file in S3, integrity, duration/channels/sr, SHA-256, create AudioFile, update storage_used).

**TASK 3C-5 — Feature gate tests**  
`backend/tests/test_feature_gates.py`: trial/artist cannot access reference, spatial, ddp, collaboration; pro can access spatial; enterprise can access custom training; track_quota AURORA-B002; storage_quota AURORA-B003; waitlist AURORA-B001; expired/past_due read-only; lossy warning in upload response.

Run: `pytest tests/test_auth.py tests/test_billing.py tests/test_feature_gates.py -v`. Report all created files and test results.

---

## End of Part 2

**Halt.** Report: (1) Files created/modified. (2) Test results for isolation, subscription, auth, billing, feature gates. (3) Any deviations.  
**Do not proceed to Part 3 until instructed.**
