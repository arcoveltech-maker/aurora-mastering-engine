# Part 6: SAIL limiter, render queue, QC engine

**Scope:** Phase 6A, 6B, 6C.  
**Do not proceed to Part 7 until instructed.**

---

## Phase 6A — SAIL limiter and psychoacoustics

**TASK 6A-1 — Psychoacoustic engine**  
`aurora-dsp/include/aurora/psychoacoustic.h`, `aurora-dsp/src/psychoacoustic.cpp`: ZwickerLoudness (Config: sampleRate, temporalResolutionMs=2). Bark band boundaries (24 bands per Appendix M). Stationary: bark filter bank → excitation → specific loudness → total N. TimeVarying: 2ms frames, loudness contour, peak/mean, transientFrames (N≥mean+2 sone). Sharpness from specific loudness (DIN 45692). Roughness: envelope modulation 15–300 Hz (simplified).

**TASK 6A-2 — SAIL limiter**  
`aurora-dsp/include/aurora/limiter.h`, `aurora-dsp/src/limiter.cpp`: LimiterMode (Transparent, Punchy, Dense, Broadcast, Vinyl). StemEnvelope (stemType, priority, weight, confidence, currentLevel, transientRatio, isVocal). SAILConfig (mode, ceilingDBTP=-1, releaseMs, lookaheadMs, stemAwareEnabled, psychoacousticRelease). SAILLimiter: setStemEnvelopes, setZwickerLoudness; processBlock → allocateGainReduction (sustained first, vocal protection ≤30% of proportional GR), apply GR, enforceTruePeakCeiling (4× oversample, micro-correction). Fallback: no stems or all low confidence → conventional wideband limiter, log fallback reason. getStemGainAllocation, getOutputTruePeakDBTP.

**TASK 6A-3 — Dither**  
`aurora-dsp/include/aurora/dither.h`, `aurora-dsp/src/dither.cpp`: Dither(Type, targetBitDepth, seed). Deterministic PRNG (e.g. xoshiro256**). TPDF: (nextRandom()+nextRandom())*0.5*quantizationStep; add to input, quantize. process/processBlock. Session seed for reproducibility.

**TASK 6A-4 — Tests**  
`aurora-dsp/tests/test_limiter.cpp`: true peak ≤ ceiling on varied signals (noise, sweeps, impulses, square); stem-aware: pad GR > vocal GR, vocal ≤30% of pad; no stems → conventional, ceiling met; all low confidence → conventional; mode behavior (Transparent/Punchy/Dense/Broadcast/Vinyl); psychoacoustic release follows loudness decay when Zwicker provided; dither same seed → bit-identical; dither 24-bit silence within ±1 LSB; micro-correction on known ISP.

Run CTest. Report.

---

## Phase 6B — Render job queue (Celery + Redis)

**TASK 6B-1 — Celery config**  
`backend/app/tasks/__init__.py`: Celery('aurora', broker/backend=REDIS_URL). task_routes (render_master→render_default, render_master_priority→render_priority, billing→billing, cleanup→cleanup). worker_prefetch_multiplier=1, task_soft_time_limit=600, task_time_limit=660, result_expires=86400, task_acks_late, task_reject_on_worker_lost. beat_schedule: check_expired_subscriptions, check_trial_expirations, cleanup_expired_render_jobs (hourly).

**TASK 6B-2 — Render slots**  
`backend/app/services/render_slots.py`: RenderSlotManager(redis). MAX_USER_CONCURRENT=3, MAX_COLLAB_RENDERS_PER_WINDOW=10, COLLAB_WINDOW_SECONDS=600. acquire_slot(user_id, session_id, is_collaborative): incr user key, check ≤3; if collab incr session quota, check ≤10; expire keys. release_slot(user_id). get_user_slot_count, get_queue_depth.

**TASK 6B-3 — Render task**  
`backend/app/tasks/render_tasks.py`: render_master(user_id, session_id, render_job_id, tier, output_formats, is_collaborative). Acquire slot; load session and audio from S3; feature extraction; inference (AuroraNet or heuristic); separation if needed; spectral repair if session.repair; build manifest; call AuroraDSP (native or stub returning processed audio); codec optimization; loudness targeting; QC run_full_check; forensics (stub); export formats; upload to S3; update_render_job completed; increment track usage; release slot in finally. publish_progress via Redis (render_progress:{session_id}). On SoftTimeLimitExceeded/exception: fail job, release slot.

**TASK 6B-4 — Render routes**  
`backend/app/api/routes/render.py`: POST /api/render (session_id, output_formats; validate tier formats; create RenderJob; route Enterprise→priority; dispatch Celery; return job_id). GET /api/render/status/{job_id} (owner only; presigned URLs if completed). GET /api/render/progress/{session_id} (SSE; subscribe Redis render_progress:{session_id}). DELETE /api/render/{job_id} (cancel). Require auth, email verified, require_track_quota; rate limit 5/min.

**TASK 6B-5 — Export service**  
`backend/app/services/export.py`: ExportService. FORMATS (wav_48k_24bit, wav_96k_24bit, mp3_320, aac_256, ogg_256, flac, alac, opus_128, stem_archive, etc.). export(audio, sr, formats, session, tier) → list {filename, data, content_type}; filter by tier.

**TASK 6B-6 — Tests**  
`backend/tests/test_render.py`: slot acquire/release (3 then 4th fails); slot TTL; collab quota 10/10min; priority queue for Enterprise; progress events order; timeout → AURORA-E301, slot released; failure releases slot; track usage incremented on success.

Run pytest. Report.

---

## Phase 6C — QC engine (18 checks + remediation)

**TASK 6C-1 — QC engine**  
`backend/app/services/qc_engine.py`: QCCheckResult(id, name, status, measurement, threshold, remediation_applied, severity). QCReport(version, timestamp, audio_hash, checks, summary, sail_mode, has_critical_failure, critical_error_code/message, remediated_audio). QCEngine(sample_rate). run_full_check(audio, sr, target_lufs, ceiling_dbtp, lra_target, auto_remediate, enabled_checks, tier): Artist 10-check subset [1,2,3,7,8,11,12,14,16,18], Pro/Enterprise all 18. check_functions map 1–18 to _check_*; on FAIL and auto_remediate call _try_remediate; append result; set has_critical_failure for critical severity. _check_digital_clipping, _check_inter_sample_peaks, _check_phase_cancellation, _check_codec_pre_ring, _check_pops_clicks, _check_bad_edits, _check_dc_offset, _check_head_tail_silence, _check_sample_rate_mismatch, _check_bit_depth_truncation, _check_loudness_compliance (±0.5 LU), _check_true_peak_compliance, _check_lra_compliance, _check_mono_compatibility, _check_excessive_sibilance, _check_low_frequency_rumble, _check_stereo_balance, _check_perceptual_quality (advisory PASS). _try_remediate: map check_id to _remediate_*; return remediated audio or None. Implement remediations (gain reduction, ISP limiter, M/S, crossfade, HPF, trim, dither, etc.).

**TASK 6C-2 — QC routes**  
GET /api/qc/{session_id} (latest report). POST /api/qc/{session_id}/recheck (re-run on last output).

**TASK 6C-3 — Tests**  
`backend/tests/test_qc.py`: clean audio all pass (or advisory); clipping detection and remediation; true peak fail and remediate; loudness pass/fail; DC offset; mono compatibility warning/critical; artist 10 checks only; pro 18; report schema; PEAQ advisory never blocks; remediation no new artifacts.

Run pytest. Report.

---

## End of Part 6

**Halt.** Report: (1) Files created/modified. (2) CTest (limiter/dither). (3) pytest test_render, test_qc. (4) Any deviations.  
**Do not proceed to Part 7 until instructed.**
