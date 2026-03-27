# Aurora AI Mastering Engine v5.0 — Build Execution Blueprint Index

**Purpose:** Run the blueprint **one part at a time** in Cursor to avoid output/context limits. Complete each part, verify tests and build, then continue to the next.

---

## Execution order (strict)

| Step | Part file       | Phases covered | Outcome |
|------|-----------------|----------------|---------|
| 1    | **PART-1**      | .cursorrules, Phase 0, Phase 1 | Repo scaffold, Docker, monorepo layout |
| 2    | **PART-2**      | Phase 2A, 2B, 3A, 3B, 3C | DB schema, RLS, auth, Stripe, feature gates |
| 3    | **PART-3**      | Phase 4A, 4B, 4C, 4D | LUFS, True Peak, LR8 crossover, compressor |
| 4    | **PART-4**      | Phase 4E, 4F, 4G, 4H | Analog fallback, linear-phase EQ, M/S, WASM, CTest |
| 5    | **PART-5**      | Phase 5A, 5B, 5C, 5D | Features, separation, AuroraNet, repair/codec |
| 6    | **PART-6**      | Phase 6A, 6B, 6C | SAIL limiter, Celery render queue, QC engine |
| 7    | **PART-7**      | Phase 7A, 7B, 7C, 7D | React contexts, Web Audio, WebGL, Simple/Advanced UI |
| 8    | **PART-8**      | Phase 8A, 8B, 9A, 9B | WebSocket collab, Claude AI, forensics, DDEX |
| 9    | **PART-9**      | Phase 10, Phase 11 | Spatial/binaural, CI/CD, deployment, release gate |

---

## Immutable notes (apply in every part)

1. **K-weighting (v4.0 Appendix B)**  
   Use **negative** `a1` (and `a2` where applicable).  
   Example 48 kHz Stage 1a: `a = [1.0, -1.69065929318241, 0.73248077421585]`.  
   Biquad: `y = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2`.

2. **AnalogNet v1**  
   Ship fallback only (waveshaper + micro-drift 0–0.3%). UI label: "Analog Warmth Engine". No hardware names.

3. **NORMALIZATION_VALIDATED=false**  
   AuroraNet inference **blocked**; heuristic fallback **mandatory**. Log clearly.

4. **Watermarks**  
   Trial = audible, listener-facing. Forensic = inaudible, provenance-facing, all eligible exports.

5. **Collaboration v1**  
   Numeric params: Last-Writer-Wins. Chat/comments: append-only. Locks: 5 min expiry. No OT library.

6. **WASM reproducibility**  
   Record in session: `aurora_dsp_version`, `aurora_dsp_wasm_hash`, `auroranet_model`. Archive WASM by SHA-256.

7. **Multi-tenant isolation**  
   Enforce at DB (RLS), API (user_id), S3 prefix, render jobs, WebSocket membership. Cross-tenant leak = critical.

---

## Per-part protocol

After each part:

1. **Halt** — do not start the next part.
2. **Compile / build** — run the relevant build and test commands.
3. **Test** — run the tests listed in that part.
4. **Report** — list files created/changed, test results, any deviations.
5. **Continue only** when instructed: "Proceed to Part N."

---

## File layout

- `BLUEPRINT-INDEX.md` — this file.
- `PART-1.md` … `PART-9.md` — one file per execution chunk; each contains the phase prompts and tasks for that chunk.

Use **PART-N.md** as the single prompt for the agent when running Part N (or paste its content into the chat). Do not combine two parts in one run.
