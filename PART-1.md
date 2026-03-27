# Part 1: Foundation — .cursorrules, Phase 0, Phase 1

**Scope:** Persistent agent rules, infrastructure, monorepo scaffolding.  
**Do not proceed to Part 2 until instructed.**

---

## 1. Create `.cursorrules`

Create `.cursorrules` in the **workspace root** with the full payload from the Aurora v5.0 blueprint (Part 1 document). It must include:

- Role: Lead Principal Software Architect, expert in React 18, TypeScript 5, Python 3.12+, FastAPI, C++20, WASM, DSP.
- Global rules: production-ready code, separation of concerns, deterministic reproducibility via AuroraDSP 64-bit, dual-path (Preview = Web Audio, Render = WASM), multi-tenant isolation.
- Frontend: React 18 + Vite 6 + TS 5 + Tailwind 4; Contexts (Audio, Processing, Session, Auth, Reference, Theme, Toast); WebGL2 for viz; &lt;4 ms frame time, no React re-renders during playback.
- Backend: FastAPI async, SQLAlchemy 2.0, RLS/user_id on every query, S3 prefix `users/{user_id}/{session_id}/`, Redis + Celery, 1 worker per 4 vCPUs.
- C++/WASM: C++20, Emscripten, LUFS/TP/LR8/Analog fallback; LR8 sum-to-unity ±0.01 dB 20 Hz–20 kHz.
- Infrastructure: ONNX Runtime, Demucs v4, Stripe webhooks &lt;30 s, NORMALIZATION_VALIDATED gate.
- Security headers: COOP, COEP, CSP, HSTS, etc. (as in spec).
- Sub-phase protocol: after each sub-phase, halt, report files/tests/deviations, do not continue until instructed.

---

## 2. Phase 0 — Infrastructure

**TASK 0A — Docker Compose**  
Create `docker-compose.yml` in repo root:

- PostgreSQL 15: DB `aurora`, RLS, init script for `aurora_app` (no superuser), health check `pg_isready`.
- Redis 7: appendonly, maxmemory 512mb, allkeys-lru, health check `redis-cli ping`.
- MinIO: bucket `aurora-audio`, block public access, console 9001.
- Prometheus: scrape 15s, targets backend:8000/metrics, redis-exporter:9121.
- Grafana: port 3000, default Aurora dashboard (queue depth, render latency, errors).
- Redis Exporter (oliver006/redis_exporter).
- Shared network: `aurora-net`.

Create `.env.development` with variables pointing at these services.

**TASK 0B — Observability**  
Create `backend/app/core/observability.py`:

- Structlog JSON logging, request_id and correlation ID middleware.
- Prometheus metrics: HTTP default + `aurora_render_queue_depth`, `aurora_render_duration_seconds`, `aurora_render_cost_dollars`, `aurora_active_websocket_connections`, `aurora_heuristic_fallback_total`, `aurora_error_total` (label: error_code).
- Health: `GET /api/health` (shallow), `GET /api/health/deep` (PostgreSQL, Redis, S3).

**TASK 0C — Nginx**  
Create `nginx/nginx.conf`:

- Frontend on 80, proxy `/api/*` to backend 8000, `/ws/*` to backend WebSocket.
- Add all security headers from .cursorrules, **including** `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: credentialless`.
- `client_max_body_size 500m`; gzip/brotli for text, not for audio.

Add nginx service to docker-compose, port 80.

**TASK 0D — CI scaffold**  
Create `.github/workflows/ci.yml` with stages: lint (frontend, backend, dsp), test (frontend, backend, dsp), build (frontend, wasm, backend), security (npm audit, pip-audit, optional bandit).

**Verify:** `docker compose up -d`; confirm PostgreSQL, Redis, MinIO healthy. Report health output.

---

## 3. Phase 1 — Monorepo scaffolding

**TASK 1A — Frontend**  
- `npm create vite@latest frontend -- --template react-ts`.
- Install: react, react-dom, tailwindcss@4, lucide-react, @tanstack/react-query, zustand. Dev: vitest, @testing-library/react, eslint, typescript-eslint.
- tsconfig: strict, noUncheckedIndexedAccess, paths `@/*` → `./src/*`.
- Tailwind v4 + Aurora dark (slate-950, blue-500).
- Directories: `src/components/tabs`, `controls`, `visualizers`, `common`; `contexts`; `hooks`; `utils`; `types`; `stores`; `public`.
- Create `src/types/aurora.ts`: interfaces for AudioContextState, ProcessingContextState, SessionContextState, ReferenceContextState, ThemeContextState, ToastContextState, AuthContextState, AuroraErrorCode, SubscriptionTier, SessionManifest (v4.0 Section 22.1, including `aurora_dsp_wasm_hash`).

**TASK 1B — Backend**  
- Python 3.12 venv; `requirements.txt` with pinned: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, redis, celery, stripe, boto3, pyjwt, passlib, cryptography, onnxruntime, librosa, soundfile, numpy, scipy, anthropic, pydantic, structlog, prometheus-fastapi-instrumentator, httpx, lxml, mutagen, Pillow, ruff, mypy, pytest, pytest-asyncio, pytest-cov.
- Layout: `app/api/routes`, `dependencies.py`, `middleware.py`; `app/core/config.py`, `security.py`, `database.py`, `observability.py`; `app/services/` (analysis, inference, separation, render, collaboration, distribution, storage); `app/models/`, `app/schemas/`, `app/tasks/`; `tests/conftest.py`, `test_*.py`; `alembic/`.
- `app/core/config.py`: Pydantic BaseSettings, AURORA_ENV, DATABASE_URL, REDIS_URL, S3_*, JWT_*, ANTHROPIC_API_KEY, STRIPE_*, NORMALIZATION_VALIDATED (default False), COLLAB_MAX_USERS_PER_SESSION, AURORA_CERT_SIGNING_KEY_PATH.
- `app/main.py`: FastAPI app, observability middleware, Prometheus, health routes, security headers, CORS with AURORA_ALLOWED_ORIGINS.

**TASK 1C — Aurora-DSP**  
- Directories: `include/aurora/` (lufs.h, true_peak.h, multiband.h, biquad.h, limiter.h, ms_processing.h, saturation.h, linear_phase_eq.h, dynamic_eq.h, transient_designer.h, dither.h, engine.h), `src/` (same names .cpp + bindings.cpp), `data/` (tp_fir_generator.cpp, coefficients/), `tests/`.
- `CMakeLists.txt`: dual target — native (C++20, Eigen, FFTW, libauroradsp.a + tests) and WASM (Emscripten, KissFFT, flags: INITIAL_MEMORY=256MB, MAXIMUM_MEMORY=4GB, ALLOW_MEMORY_GROWTH, MODULARIZE, EXPORT_ES6, ENVIRONMENT=web,worker, USE_PTHREADS=0, simd128, --bind, -O3). CTest for tests.
- `build_wasm.sh`: emcmake/cmake, make, sha256 of aurora_dsp.wasm, copy to frontend/public/wasm.

**TASK 1D — ML**  
- Directories: `auroranet/` (model.py, train.py, dataset.py, export.py), `spectral_repair/`, `analog_net/`, `codec_net/`, `genre_classifier/`, `reference_encoder/` (with placeholder files if needed).

**TASK 1E — Supporting**  
- `models/` (.gitkeep), `docker/` (Dockerfile.frontend, .backend, .worker), `scripts/setup.sh`, `test.sh`, `docs/` with placeholder README.

**TASK 1F — Build verification**  
- `cd frontend && npm install && npx tsc --noEmit` → zero errors.
- `cd backend && pip install -r requirements.txt && python -c "from app.main import app; print('FastAPI OK')"`.
- `cd aurora-dsp && mkdir build-native && cd build-native && cmake .. && make` — CMake must succeed (compile may fail on stubs; report CMake output).

---

## End of Part 1

**Halt.** Report: (1) All files created or modified. (2) Build/output summary for frontend, backend, CMake. (3) Any deviations.  
**Do not proceed to Part 2 until instructed.**
