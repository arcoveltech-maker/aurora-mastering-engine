# Part 8: Collaboration, AI assistant, forensics, DDEX

**Scope:** Phase 8A, 8B, 9A, 9B.  
**Do not proceed to Part 9 until instructed.**

---

## Phase 8A — WebSocket collaboration hub

**Security:** Collab only Studio Pro/Enterprise. User must own session or be in session.invited_user_ids. Uninvited → AURORA-E602. Pro max 3 concurrent, Enterprise max 8. Locks 5min expiry.

**TASK 8A-1 — Protocol types**  
`backend/app/schemas/collaboration.py`: CollabEvent(type, user_id, timestamp, payload). ParamChangePayload(param, value, session_version, lock_id). PlaybackSyncPayload(action, position). CursorMovePayload(x, y, component). CommentPayload(text, position). LockAcquirePayload(region). LockGrantedPayload(lock_id, region, user_id, expires_at). LockDeniedPayload(region, holder_id, expires_at). ChatPayload(message). CollabSessionState(session_id, connected_users, active_locks, current_version).

**TASK 8A-2 — Collaboration manager**  
`backend/app/services/collaboration.py`: CollaborationManager(redis). LWW for numeric DSP params; append-only chat/comments. ParameterLock(lock_id, region, user_id, acquired_at, last_activity_at, expires_at). LOCK_TIMEOUT_SECONDS=300. _connections (in-memory per process), _locks, _versions; presence and locks mirrored in Redis. connect(websocket, session_id, user, max_users): check presence count, accept, sadd presence, broadcast user_join. disconnect: srem presence, release user locks, broadcast user_leave. broadcast: local send_json + redis publish collab:channel:{session_id}. handle_param_change: check lock, incr collab:version:{session_id}, return param_change event. acquire_lock: cleanup expired, deny if held by other, else grant and hset collab:locks. release_lock, release_all_user_locks, cleanup_expired_locks.

**TASK 8A-3 — WebSocket route**  
`backend/app/api/routes/collaboration.py`: WebSocket /api/collab/{session_id}. Auth from cookie aurora_access_token; verify JWT; require Pro/Enterprise; get session; is_member = owner or user_id in invited_user_ids; reject if not. max_users 3/8; manager.connect. Send session_state (connected_users, active_locks, current_version). Loop: receive_json → CollabEvent; ping→pong; param_change→handle_param_change, persist, broadcast; playback_sync, comment, chat→persist, broadcast; lock_acquire→acquire_lock, broadcast; lock_release→release, broadcast. On disconnect/error: manager.disconnect.

**TASK 8A-4 — REST collab**  
POST /api/collab/session/{session_id}/invite (owner, Pro+; body email; add to invited_user_ids). GET /api/collab/session/{session_id}/state. GET /api/collab/session/{session_id}/history. POST /api/collab/session/{session_id}/approve (sign-off).

**TASK 8A-5 — Frontend client**  
`frontend/src/services/collaborationClient.ts`: connect(sessionId) wss/ws; credentials via cookie. onmessage → handleMessage (param_change, playback_sync, lock_granted/denied, user_join/leave, chat, error). sendParamChange, acquireLock, releaseLock, sendPlaybackSync, sendChat. Heartbeat 5s; reconnect backoff (skip 4003/4001).

**TASK 8A-6 — Tests**  
`backend/tests/test_collaboration.py`: uninvited user rejected AURORA-E602; artist tier rejected AURORA-B005; Pro limit 3 (4th E601); Enterprise limit 8; param_change LWW, version increment; lock acquire, B denied, expire 5min, B can acquire; disconnect releases locks.

Run pytest. Report.

---

## Phase 8B — Claude AI assistant

**TASK 8B-1 — Prompt builder**  
`backend/app/services/ai_assistant.py`: build_system_prompt(session) with rules: never claim to hear audio; use measurements, features, stems, QC, reference, macros. Inject LUFS, TP, LRA, crest, centroid, stereo width, attack density, current macros, stem confidence, QC warnings. Macro interaction rules (tension/synergy). JSON schema for suggestions: summary, suggestions[{macro, current, suggested, reason}], warnings, confidence. NLP seed rules: brighter→BRIGHTEN+1.5 AIR+1; warmer→WARMTH+1.5 BRIGHTEN-0.5; more glue→GLUE+2; wider→WIDTH+1.5; punchier→PUNCH+2; more depth→DEPTH+2; airy→AIR+2 BRIGHTEN+0.5; less harsh→BRIGHTEN-2 AIR-1; muddy→WARMTH-2 BRIGHTEN+1; too compressed→GLUE-2 PUNCH-1; like reference→reference 70%.

**TASK 8B-2 — Claude service**  
ClaudeAssistantService(anthropic_client). suggest_macros(session, user_message, history): build_system_prompt, messages last 20 + user, client.messages.create claude-sonnet-4-6, parse JSON. stream_chat: messages.stream; yield token; parse final JSON, yield macro_suggestion; yield done (usage).

**TASK 8B-3 — AI routes**  
POST /api/chat (session_id, message, history; rate 20/min; load session, suggest_macros, persist, return JSON). POST /api/chat/stream (SSE; token, macro_suggestion, done). POST /api/chat/analyze-mix (session_id; 2–3 sentence summary). POST /api/chat/suggest-macros (session_id, message; JSON only). Auth required.

**TASK 8B-4 — Frontend chat**  
CollabTab or AIAssistantPanel: history, input, SSE for stream; “Apply suggestions” with diff preview; confidence <0.5 warning; rate limit toast.

**TASK 8B-5 — Tests**  
`backend/tests/test_ai_assistant.py`: prompt contains LUFS, macros; rule “never claim to hear”; NLP seeds (brighter, too compressed); stream events token, macro_suggestion, done; safe_json_parse valid/invalid.

Run pytest. Report.

---

## Phase 9A — Forensics and provenance

**TASK 9A-1 — Trial watermark**  
`backend/app/services/trial_watermark.py`: TrialWatermarkService. Audible: e.g. 1 kHz tone -20 dBFS 500ms every 30s; fade 10ms; stereo; clip [-1,1]. For trial exports only.

**TASK 9A-2 — Fingerprinting**  
`backend/app/services/fingerprinting.py`: FingerprintService. chromaprint(audio_path) pyacoustid/chromaprint. aurora_spectral_hash(audio, sr): mel + temporal envelope + chroma → sha256, "aurora:{hex}".

**TASK 9A-3 — Forensic watermark**  
`backend/app/services/watermarking.py`: WatermarkService(spreading_code). build_payload(artist_id, session_id, timestamp_iso, version)→128 bits. embed(audio, sr, payload, strength_db): DWT db4 level 5, mid channel; spread payload; strength; inverse DWT. detect(audio, sr)→{detected, confidence, payload_bits}. Optional pywt; if missing log and skip.

**TASK 9A-4 — Provenance**  
`backend/app/services/provenance.py`: ProvenanceService(signing_key_path). Ed25519 SigningKey/VerifyKey (nacl). build_manifest(ingest, analysis, process, export) → chain list. sign(manifest): JSON chain sort_keys, sign, add signature (algorithm, public_key_id, signature base64). verify(manifest). export_public_key(path).

**TASK 9A-5 — Tests**  
`backend/tests/test_forensics.py`: trial watermark bursts every 30s, output bounded; spectral_hash stable for same audio; provenance sign then verify true; tamper verify false; payload 16 bytes.

Run pytest. Report.

---

## Phase 9B — DDEX and distribution

**TASK 9B-1 — Metadata validation**  
`backend/app/services/metadata_validation.py`: validate_isrc (CC-XXX-YY-NNNNN), validate_upc_ean (check digit), validate_cover_art (≥3000×3000, JPEG/PNG, sRGB, <10MB), validate_metadata(payload)→list {field, code, message}.

**TASK 9B-2 — DDEX generator**  
`backend/app/services/ddex.py`: DDEXGenerator. generate(metadata, audio_file, cover_art)→ERN 4.3 XML (MessageHeader, ResourceList, ReleaseList, DealList, SHA-256 refs). validate_xsd(xml_str, xsd_path). validate_business_rules(metadata). 9-step pipeline (well-formed, XSD, business, platform, completeness, ISRC, UPC/EAN, cover, hash).

**TASK 9B-3 — Distribution routes**  
POST /api/distribute/validate-metadata (Pro+). POST /api/distribute/generate-ddex (Pro+; AURORA-E700 on validation fail). POST /api/distribute/generate-rin. GET /api/distribute/pre-check. GET /api/distribute/platforms. POST /api/distribute/upc/validate. POST /api/distribute/isrc/request (stub). All Pro+ except platforms.

**TASK 9B-4 — Export gating**  
Artist: wav_48k_24bit, mp3_320, aac_256, ogg_256, flac, stem_archive. Pro: + wav_96k_24bit, alac, opus_128, ms_master, dolby_atmos, ambisonics, binaural, vinyl_premaster, ddp. Enterprise: + sony_360ra, custom. Unavailable format → AURORA-B005.

**TASK 9B-5 — Tests**  
`backend/tests/test_distribution.py`: isrc valid/invalid; upc valid/invalid; cover 3000×3000 ok, small fail; ddex well-formed; missing metadata AURORA-E701; artist cannot generate ddex AURORA-B005; pro can generate ddex.

Run pytest. Report.

---

## End of Part 8

**Halt.** Report: (1) Files created/modified. (2) test_collaboration, test_ai_assistant, test_forensics, test_distribution. (3) Any deviations.  
**Do not proceed to Part 9 until instructed.**
