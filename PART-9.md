# Part 9: Spatial audio, CI/CD, deployment, production gates

**Scope:** Phase 10, Phase 11.  
**End of blueprint.**

---

## Phase 10 — Spatial audio and binaural

**Code:** C++ in `aurora-dsp/` (render DSP); Python in `backend/app/services/` (packaging). Spatial = Studio Pro+ only (v5.0 §5.1).

**TASK 10-1 — Spatial renderer core**  
`aurora-dsp/include/aurora/spatial.h`, `aurora-dsp/src/spatial.cpp`. Bed channels: L,R,C,LFE,Ls,Rs,Lss,Rss,Ltf,Rtf,Ltr,Rtr (12 for 7.1.4). Default stem-to-bed (v4.0 §15.2): Lead C 80% L/R 10%; Backing L/R 35% Ls/Rs 15%; Kick C 40% L/R 20%; Snare C 50% L/R 25%; HiHats L/R 30% Ltf/Rtf 20%; Bass C 60% L/R 20%; Guitar L or R 50% Ls/Rs 25%; Piano L/R 40% Ltf/Rtf 10%; Synths/pads bed+height; Ambience rear. LFE: bass/kick to bed only by default; direct LFE option cinema/broadcast only. SpatialObject (stemType, azimuth -180..180, elevation -90..90, distance, size, diffuse, gainDB). SpatialConfig (Format: DolbyAtmos714, AmbisonicsFOA/SOA/TOA, BinauralStereo; directLFE, binauralFoldDown). SpatialRenderer(sampleRate, config): render(stems, numSamples)→channels; setObjectMetadata(objects). Atmos 12ch; Ambisonics FOA 4 (W,X,Y,Z), SOA 9, TOA 16, SN3D ACN; BinauralStereo 2ch via HRTF.

**TASK 10-2 — Binaural**  
`aurora-dsp/include/aurora/binaural.h`, `aurora-dsp/src/binaural.cpp`. HRTFPosition(azimuth, elevation, leftIR, rightIR) 256-tap. BinauralRenderer(sampleRate). loadHRTFSet(path). renderObject(monoInput, numSamples, azimuth, elevation, distance, outLeft, outRight): nearest HRTF (or interpolate), convolve 256-tap FIR, distance gain = 1/max(distance,0.1)^2 + near-field, sum to stereo. Bundled generic 256-tap dataset for v1.

**TASK 10-3 — Spatial packaging**  
`backend/app/services/spatial_packaging.py`: generate_adm_metadata(session, objects, channels)→dict (ADM BWF manifest; v1 can be JSON + multichannel WAV if no BW64). write_ambix_header(...). validate_atmos_constraints(audio, metadata)→list[str]: object count ≤118, 12 bed ch, 48kHz, ≥24bit, LUFS ≤-18, TP ≤-1 dBTP, binaural metadata.

**TASK 10-4 — Spatial UI stub**  
`frontend/src/components/tabs/SpatialTab.tsx`: visible Pro/Enterprise only; 7.1.4 bed diagram; object placement azimuth/elevation grid; format select (Atmos 7.1.4, Ambisonics FOA/SOA/TOA, Binaural); wire to SessionContext.spatial and save.

**TASK 10-5 — Tests**  
`backend/tests/test_spatial.py`: artist cannot access spatial; pro can request spatial; atmos_metadata_validation. `aurora-dsp/tests/test_spatial.cpp`: bed 12ch; binaural 2ch; ambisonics FOA 4ch; default vocal routing center-weighted. Run both. Report.

---

## Phase 11 — CI/CD, integration, deployment, gates

**TASK 11-1 — E2E test**  
`backend/tests/test_e2e_pipeline.py`: (1) create user, (2) verify email, (3) activate Pro, (4) upload audio, (5) confirm upload, (6) create session, (7) extract features, (8) predict macros, (9) start render, (10) poll to completion, (11) fetch QC report, (12) download output URL, (13) verify provenance manifest, (14) output in S3, (15) tenant isolation. Mocks OK: Stripe webhook, Claude, codecs, DDEX XSD. Assert: render completed; QC 10 or 18 checks; presigned namespaced URLs; manifest has aurora_dsp_wasm_hash; model source heuristic when NORMALIZATION_VALIDATED=false; no cross-tenant leak.

**TASK 11-2 — CI workflow**  
`.github/workflows/ci.yml`: jobs lint-frontend, lint-backend, lint-cpp, test-frontend, test-backend, test-dsp, build-wasm, integration-e2e, security-audit, docker-build. Frontend: npm ci, build, vitest run, tsc --noEmit. Backend: pip install, pytest --cov, ruff, mypy --strict. DSP: cmake -DAURORA_BUILD_WASM=OFF -DAURORA_BUILD_TESTS=ON, make, ctest. WASM: ./build_wasm.sh. Integration: docker compose up -d, pytest test_e2e_pipeline. Security: npm audit, pip-audit, optional bandit -r app.

**TASK 11-3 — Docker**  
`docker/Dockerfile.frontend`: Node 20 multi-stage, Vite build, nginx serve, COOP/COEP headers, copy wasm to static. `docker/Dockerfile.backend`: Python 3.12 slim, audio deps, uvicorn, /metrics. `docker/Dockerfile.worker`: same deps, Celery worker; optional Dockerfile.worker.gpu.

**TASK 11-4 — Deployment**  
Templates: prod env vars, nginx reverse proxy, systemd/entrypoint, S3 bucket policy, CDN signed URL note. `docs/deployment/production.md`: DNS, TLS, Stripe webhook URL, Anthropic key, Ed25519 signing key, Redis persistence/backup, PostgreSQL backup, model artifact retention, WASM archive by hash for reproduction.

**TASK 11-5 — Admin**  
`backend/app/api/routes/admin.py`: admin role only; 2FA required for admin. GET /api/admin/users, /metrics, /errors, /queue, /waitlist. POST /api/admin/subscription/{user_id}/override, /api/admin/feature-flags, /api/admin/waitlist/invite. Metrics: tracks_processed_per_day, queue_depth, p95_render_time, mrr/arr/churn placeholders, heuristic_fallback_rate, model_confidence_distribution, recent AURORA-E*.

**TASK 11-6 — Feature flags**  
`backend/app/core/feature_flags.py`: Category A (UI only), B (feature access), C (DSP/ML). Category C must be recorded in session manifest; require env or DB; C changes break reproducibility unless recorded.

**TASK 11-7 — Security tests**  
`backend/tests/test_security.py`: presigned_url_ownership_enforced; jwt_cookie_flags; refresh_token_revocation; rls_blocks_cross_tenant; collab_permission_rejection; admin_route_requires_admin; artist_cannot_access_pro_feature; s3_key_namespace_validation. `docs/deployment/security-checklist.md`: cross-tenant API, WebSocket auth bypass, presigned tampering, JWT replay after password change, refresh reuse after rotation, Stripe webhook spoofing, upload path traversal.

**TASK 11-8 — Release gate script**  
`scripts/release_gate.sh`: [1/9] frontend tsc --noEmit, [2/9] frontend vitest, [3/9] backend pytest, [4/9] DSP ctest, [5/9] WASM build_wasm.sh, [6/9] e2e test_e2e_pipeline, [7/9] security test_security, [8/9] frontend build, [9/9] check NORMALIZATION_VALIDATED (warn if false). set -euo pipefail; echo “Release Gate Passed”.

**TASK 11-9 — Acceptance matrix**  
`docs/specification/acceptance-matrix.md`: LUFS ±0.1 LU, True Peak ±0.05 dBTP, LR8 sum ±0.01 dB, RIAA ±0.01 dB, SAIL zero ISP above ceiling, multi-tenancy zero findings, Stripe sync ≤30s, render p95 <3min (4min track), DDEX steps, watermark targets, NORMALIZATION_VALIDATED gate.

**TASK 11-10 — Run full gate**  
chmod +x scripts/release_gate.sh; ./scripts/release_gate.sh. Fix any failure and re-run until pass. Report: all created files, CI summary, gate output, remaining manual actions.

---

## End of blueprint

**Halt.** Report: (1) All Part 9 files created/modified. (2) Phase 10 and 11 test results. (3) Release gate output. (4) Remaining manual steps before production.  
**This concludes the corrected build execution blueprint.**
