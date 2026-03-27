# Part 5: Feature extraction, separation, AuroraNet, repair/codec

**Scope:** Phase 5A, 5B, 5C, 5D.  
**Do not proceed to Part 6 until instructed.**

Apply BLUEPRINT-INDEX: NORMALIZATION_VALIDATED=false → heuristic only; normalization stats synthetic-baseline for dev only.

---

## Phase 5A — Feature extraction (43 dimensions)

**TASK 5A-1 — Analysis service**  
`backend/app/services/analysis.py`: AudioFeatures dataclass (all 43 fields per v4.0 Section 7.2). to_vector() with key encoded 0–23; to_dict(). FeatureExtractor(lufs_backend). extract(audio_path, target_sr=48000): load with soundfile, resample if needed, mono for spectral. _extract_loudness (integrated LUFS, true peak, short/momentary variance, LRA); _extract_dynamics (crest factor, DR, PSR, PLR, rms_variance, peak_density); _extract_spectral (10 bands, centroid, spread, flux, rolloff, flatness); _extract_stereo (ms_ratio, stereo_width IACC, correlation, side_energy_ratio, freq_width 3 bands); _extract_transient (attack_density, strength mean/std, drum_transient_strength, transient_sustain); _extract_tonal (librosa key, bpm, confidences). Raise AURORA-E100 on failure.

**TASK 5A-2 — Normalization**  
`backend/app/services/normalization.py`: NORMALIZATION_STATS dict (mean/std per feature from Appendix C). FeatureNormalizer; is_validated from settings.NORMALIZATION_VALIDATED. normalize(features) → z-score, clip ±3σ; denormalize(). Log warning when using synthetic baseline.

**TASK 5A-3 — Analysis routes**  
`backend/app/api/routes/analysis.py`: POST /api/analyze (session_id; load audio from S3, extract, store in session.features; return AudioFeatures). POST /api/analyze/psychoacoustic (session_id; optional Zwicker/sharpness/roughness approximation). Rate limit 30/min; require auth + email verified.

**TASK 5A-4 — Tests**  
`backend/tests/test_analysis.py`: 43 dimensions present, to_vector().shape (43,), no NaN/Inf; ranges within Appendix C; normalize bounded [-3,3]; round-trip; mono → stereo_width≈0, correlation≈1; silent audio no crash; key encoding (C major→0, A minor→21).

Run pytest. Report.

---

## Phase 5B — Source separation (6-pass, 12-stem)

**TASK 5B-1 — Pipeline**  
`backend/app/services/separation.py`: SeparationPipeline. Pass 1: Demucs htdemucs_ft → Vocals, Bass, Drums, Other. Pass 2: htdemucs_6s on Other → Guitar, Piano, Residual (or spectral split fallback). Pass 3: vocal split → Lead Vocals, Backing Vocals (spectral-centroid fallback if no fine-tuned model). Pass 4: drum DSP decomposition → Kick, Snare, HiHats, Cymbals, Room. Pass 5: residual → Synths/Pads, FX/Atmosphere. Pass 6: sum verification, reconstruction_error_db. StemResult(stem_type, audio, sample_rate, confidence, srr, spectral_overlap, temporal_consistency). MIN_CONFIDENCE per stem type; warnings when below. _run_demucs, _split_vocals, _decompose_drums, _split_residual, _compute_confidence (0.5*SRR + 0.3*(1-overlap) + 0.2*temporal), _verify_reconstruction.

**TASK 5B-2 — Stems API**  
`backend/app/api/routes/stems.py`: POST /api/extract-stems (session_id; async Celery), POST /api/extract-stems/preview (2-pass), GET /api/extract-stems/status/{job_id}. Rate limit 10/min.

**TASK 5B-3 — Celery task**  
`backend/app/tasks/separation_tasks.py`: run_separation(user_id, session_id, mode); acquire render slot; download from S3; SeparationPipeline.separate(); upload stems to S3; release slot in finally; publish progress.

**TASK 5B-4 — Tests**  
`backend/tests/test_separation.py`: pass1 → 4 stems; confidence scoring (overlap high/low); reconstruction error; drum decomposition (kick low, hihat high); min_confidence warning; slot enforcement.

Run pytest. Report.

---

## Phase 5C — AuroraNet inference and heuristic fallback

**TASK 5C-1 — Model architecture**  
`aurora/ml/auroranet/model.py`: AuroraNetConfig (input_dim=43, num_genres=16, num_styles=5, num_platforms=12, num_macros=7; nano/tiny/base/large/xl). FeatureEncoder (group sub-encoders). AuroraNetV2: feature_encoder, genre/style/platform embeddings, context_fusion, transformer encoder, macro_head (sigmoid×10), emotion_head, style_head. forward(features, genre_dist, style_id, platform_id, mc_dropout). predict_with_uncertainty (N=10 MC dropout).

**TASK 5C-2 — Inference service**  
`backend/app/services/inference.py`: AuroraNetInference. _load_model (ONNX from settings.ONNX_MODEL_PATH). predict(): if not settings.NORMALIZATION_VALIDATED → log warning, return _heuristic_predict(); if no session → heuristic; else normalize, run ONNX, clamp macros [0,10], return MacroPrediction (macros, confidence, uncertainty, source='model'|'heuristic', model_version, emotions, style). _heuristic_predict per v4.0 Section 7.8 (genre_dr_targets, formula for brighten/warmth/punch/glue/width/depth/air). _encode_genre, _encode_platform.

**TASK 5C-3 — Export**  
`aurora/ml/auroranet/export.py`: export_to_onnx(model, config, output_path, opset_version=17); dummy inputs; torch.onnx.export; verify with onnxruntime.

**TASK 5C-4 — Prediction routes**  
`backend/app/api/routes/prediction.py`: POST /api/predict-macros (session_id, genre, style?, platform?; load features, inference.predict(); store in session; return MacroPrediction; AURORA-E104 if heuristic). POST /api/predict-macros/batch (Pro/Enterprise; list session_ids). Rate limit 60/min.

**TASK 5C-5 — Tests**  
`backend/tests/test_inference.py`: NORMALIZATION_VALIDATED=false → source heuristic, AURORA-E104; model unavailable → heuristic; heuristic valid [0,10]; genre sensitivity (e.g. Classical vs EDM punch); genre encoding sums to 1; model variants instantiate and forward shapes; ONNX export roundtrip; determinism (same input → same output).

Run pytest. Report.

---

## Phase 5D — SpectralRepairNet and CodecNet

**TASK 5D-1 — Spectral repair**  
`backend/app/services/spectral_repair.py`: SpectralRepairService. SUPPORTED_TASKS: de_clip, de_noise, de_click, de_ess, de_reverb, hole_fill. analyze() → _detect_clipping, _detect_noise, _detect_clicks, _detect_sibilance. repair(audio, sr, tasks, stem_confidence): de_reverb only if stem_confidence≥0.60; _neural_repair or _dsp_fallback_repair. _dsp_denoise, _dsp_declick, _dsp_deess, _dsp_declip stubs/simple implementations.

**TASK 5D-2 — Codec optimization**  
`backend/app/services/codec_optimization.py`: CodecOptimizationService. SUPPORTED_CODECS (aac_128–opus_128 with bitrate, odg_target). optimize(audio, sr, target_codecs): pick most constrained codec; _neural_optimize or _dsp_fallback_optimize (e.g. HF shelf for low bitrate).

**TASK 5D-3 — Repair routes**  
`backend/app/api/routes/repair.py`: POST /api/repair/plan (session_id; analyze only). POST /api/repair/execute (session_id, tasks). POST /api/codec/optimize (Pro/Enterprise; session_id, target_codecs).

**TASK 5D-4 — Tests**  
`backend/tests/test_repair.py`: clipping detection (regions, duration); no clipping on clean; noise floor detection; click count; sibilance detection; de_reverb skipped when confidence < 0.60; codec optimization selects lowest bitrate when multiple.

Run pytest. Report.

---

## End of Part 5

**Halt.** Report: (1) Files created/modified. (2) All Phase 5 test results (analysis, separation, inference, repair). (3) Any deviations.  
**Do not proceed to Part 6 until instructed.**
